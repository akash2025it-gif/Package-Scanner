from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditService
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import NotFoundException, ValidationException
from app.core.rate_limiter import check_rate_limit
from app.core.rbac import get_current_active_user, require_can_review, require_can_scan
from app.ai.quality import ImageQualityValidator
from app.models import AuditLog, Declaration, Product, Scan, ScanImage, User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.declaration import DeclarationOverrideRequest, DeclarationResponse, DeclarationReviewRequest
from app.schemas.scan import (
    AnalyzeScanResponse,
    AuditLogResponse,
    BatchVerifyRequest,
    CloseScanRequest,
    ImageTypeEnum,
    ImageQualityCheckResponse,
    ScanCreateRequest,
    ScanDetailResponse,
    ScanFinalizeRequest,
    ScanImageResponse,
    ScanListItemResponse,
    ScanSourceEnum,
    ScanStatusEnum,
)
from app.services.storage import get_storage_service
from app.workers.tasks import analyze_scan_task, run_scan_analysis_pipeline_async

router = APIRouter(prefix="/scans", tags=["Compliance Scans"])


async def _build_scan_detail_response(db: AsyncSession, scan: Scan) -> ScanDetailResponse:
    related_count = 0
    attention_required = False
    if scan.batch_number and scan.batch_number.strip():
        b_clean = scan.batch_number.strip().lower()
        b_res = await db.execute(
            select(func.count(Scan.id)).where(
                func.lower(Scan.batch_number) == b_clean,
                Scan.id != scan.id,
            )
        )
        related_count = b_res.scalar_one() or 0
        if scan.batch_status in ["attention_required", "under_investigation"]:
            attention_required = True
        else:
            has_fail = any(not d.is_compliant for d in (scan.declarations or []))
            meta = scan.metadata_json or {}
            final_dec = meta.get("final_decision")
            if has_fail or final_dec == "non_compliant":
                attention_required = True
            else:
                # Check if any other scan in the same batch is under investigation or attention required
                b_alert_stmt = select(Scan.id).where(
                    func.lower(Scan.batch_number) == b_clean,
                    Scan.batch_status.in_(["attention_required", "under_investigation"]),
                ).limit(1)
                b_alert_res = (await db.execute(b_alert_stmt)).scalar_one_or_none()
                if b_alert_res is not None:
                    attention_required = True

    meta = scan.metadata_json or {}
    discrepancy_resolved = meta.get("batch_discrepancy_resolved", False)
    is_discrepancy = bool(
        not discrepancy_resolved
        and scan.batch_number
        and scan.batch_number_extracted
        and scan.batch_number.strip().upper() != scan.batch_number_extracted.strip().upper()
    )

    resp = ScanDetailResponse.model_validate(scan)
    resp.related_batch_scans_count = related_count
    resp.batch_attention_required = attention_required
    resp.batch_discrepancy = is_discrepancy

    # Ensure declaration verification fields are normalized for API consumers
    thresh_val = meta.get("auto_confirm_threshold", 80.0)
    for d in resp.declarations:
        if d.auto_confirm_threshold is None:
            d.auto_confirm_threshold = thresh_val
        
        rate = d.violation_detection_rate if d.violation_detection_rate is not None else (round(d.confidence_score * 100.0, 1) if d.confidence_score is not None else 0.0)
        h_dec = d.human_decision
        is_officer = bool(h_dec and h_dec not in ["NONE", "AUTO-ANALYZED"])
        has_valid_rate = (d.violation_detection_rate is not None or (d.confidence_score is not None and d.confidence_score > 0.0))
        
        if is_officer:
            if not d.workflow_decision or d.workflow_decision != "FINALIZED":
                d.workflow_decision = "FINALIZED"
            d.decision_method = "MANUAL"
            if not d.verification_status:
                d.verification_status = f"INSPECTOR_{h_dec.upper()}"
            if not d.verification_source:
                d.verification_source = "INSPECTOR"
        else:
            if getattr(d, "has_conflict", False):
                d.workflow_decision = "MANUAL_REVIEW_REQUIRED"
                d.decision_method = "MANUAL"
                d.verification_status = "MANUAL_REVIEW_REQUIRED"
                d.verification_source = "MANUAL"
            elif d.workflow_decision in ["AUTO_CONFIRMED", "AUTOMATICALLY_CONFIRMED"]:
                d.workflow_decision = "AUTO_CONFIRMED"
                d.decision_method = "SYSTEM_THRESHOLD"
                d.verification_status = "AUTO_CONFIRMED"
                d.verification_source = "SYSTEM_THRESHOLD"
            elif d.workflow_decision in ["MANUAL_REVIEW_REQUIRED", "MANUAL"]:
                d.workflow_decision = "MANUAL_REVIEW_REQUIRED"
                d.decision_method = "MANUAL"
                d.verification_status = "MANUAL_REVIEW_REQUIRED"
                d.verification_source = "MANUAL"
            elif has_valid_rate and rate >= (d.auto_confirm_threshold or thresh_val):
                d.workflow_decision = "AUTO_CONFIRMED"
                d.decision_method = "SYSTEM_THRESHOLD"
                d.verification_status = "AUTO_CONFIRMED"
                d.verification_source = "SYSTEM_THRESHOLD"
            else:
                d.workflow_decision = "MANUAL_REVIEW_REQUIRED"
                d.decision_method = "MANUAL"
                d.verification_status = "MANUAL_REVIEW_REQUIRED"
                d.verification_source = "MANUAL"

    # Compute derived overall inspection status and resolution counters
    auto_count = sum(1 for d in resp.declarations if d.workflow_decision == "AUTO_CONFIRMED")
    officer_count = sum(1 for d in resp.declarations if d.workflow_decision == "FINALIZED")
    unresolved_count = sum(1 for d in resp.declarations if d.workflow_decision == "MANUAL_REVIEW_REQUIRED")
    has_violation = any(not d.is_compliant for d in resp.declarations)
    
    if has_violation:
        derived_st = "non_compliant"
    elif unresolved_count > 0:
        derived_st = "needs_review"
    else:
        derived_st = "compliant"

    resp.derived_status = derived_st
    resp.auto_confirmed_count = auto_count
    resp.inspector_resolved_count = officer_count
    resp.unresolved_count = unresolved_count
    resp.ready_for_finalization = (len(resp.declarations) > 0 and unresolved_count == 0)

    return resp


@router.post("", response_model=APIResponse[ScanDetailResponse], status_code=status.HTTP_201_CREATED)
async def create_scan(
    payload: ScanCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_scan),
):
    """Creates a new inspection scan."""
    product_id = payload.product_id

    # Handle inline product registration if provided
    if not product_id and payload.product_data:
        new_prod = Product(
            id=str(uuid.uuid4()),
            name=payload.product_data.name,
            brand=payload.product_data.brand,
            category=payload.product_data.category,
            manufacturer_name=payload.product_data.manufacturer_name,
            manufacturer_address=payload.product_data.manufacturer_address,
            country_of_origin=payload.product_data.country_of_origin or "India",
            barcode=payload.product_data.barcode,
        )
        db.add(new_prod)
        await db.flush()
        product_id = new_prod.id

    batch_val = (payload.batch_number or payload.lot_number or "").strip() or None

    batch_st_init = "normal"
    if batch_val:
        exist_st = await db.execute(
            select(Scan.batch_status).where(
                func.lower(Scan.batch_number) == batch_val.lower(),
                Scan.batch_status.in_(["attention_required", "under_investigation"]),
            ).limit(1)
        )
        found_st = exist_st.scalar_one_or_none()
        if found_st:
            batch_st_init = found_st

    scan = Scan(
        id=str(uuid.uuid4()),
        product_id=product_id,
        inspector_id=current_user.id,
        source=payload.source.value,
        source_url=payload.source_url,
        status="processing",
        location_name=payload.location_name,
        gps_coordinates=payload.gps_coordinates,
        batch_number=batch_val,
        batch_number_source="manual" if batch_val else None,
        batch_status=batch_st_init,
        metadata_json=payload.metadata_json or {},
    )
    db.add(scan)

    await AuditService.log_action(
        db=db,
        action="SCAN_CREATED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={"source": scan.source, "product_id": product_id, "batch_number": batch_val},
    )

    await db.commit()

    # Reload scan with relationships
    stmt = (
        select(Scan)
        .where(Scan.id == scan.id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
    )
    scan_loaded = (await db.execute(stmt)).scalar_one()

    return APIResponse(
        success=True,
        message="Scan initialized successfully",
        data=await _build_scan_detail_response(db, scan_loaded),
    )


@router.post("/quality-check", response_model=APIResponse[ImageQualityCheckResponse])
async def check_image_quality(
    file: UploadFile = File(...),
    threshold: Optional[float] = Query(None, description="Optional custom blur threshold override"),
    current_user: User = Depends(require_can_scan),
):
    """
    Validates image sharpness and blur using Laplacian variance before scan initialization or analysis.
    Returns whether the image passes quality standards for OCR and AI extraction.
    """
    file_bytes = await file.read()
    quality_result = ImageQualityValidator.validate_image_bytes(file_bytes, threshold=threshold)
    return APIResponse(
        success=True,
        message=quality_result["message"],
        data=ImageQualityCheckResponse(
            image_quality=quality_result["image_quality"],
            sharpness_score=quality_result["sharpness_score"],
            threshold=quality_result["threshold"],
            can_analyze=quality_result["can_analyze"],
            width=quality_result["width"],
            height=quality_result["height"],
            reason=quality_result["reason"],
            message=quality_result["message"],
            validation_timestamp=quality_result["validation_timestamp"],
        ),
    )


@router.post("/{id}/images", response_model=APIResponse[List[ScanImageResponse]])
async def upload_scan_images(
    id: str,
    files: List[UploadFile] = File(...),
    image_type: ImageTypeEnum = Form(ImageTypeEnum.FRONT),
    threshold: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_scan),
):
    """Uploads one or more packaging label images for a scan with automatic quality evaluation."""
    result = await db.execute(select(Scan).where(Scan.id == id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    storage_service = get_storage_service()
    uploaded_images: List[ScanImage] = []

    for file in files:
        file_bytes = await file.read()
        url, storage_key = await storage_service.upload_file(
            file_obj=file_bytes,
            filename=file.filename or f"label_{uuid.uuid4().hex}.jpg",
            content_type=file.content_type or "image/jpeg",
            folder=f"scans/{scan.id}",
        )

        # Real mathematical blur and image quality analysis
        quality_eval = ImageQualityValidator.validate_image_bytes(file_bytes, threshold=threshold)
        w = quality_eval.get("width")
        h = quality_eval.get("height")
        q_quality = quality_eval.get("image_quality", "CLEAR")
        q_score = quality_eval.get("sharpness_score", 0.0)
        q_thresh = quality_eval.get("threshold", settings.BLUR_THRESHOLD)
        q_allowed = quality_eval.get("can_analyze", False)

        scan_img = ScanImage(
            id=str(uuid.uuid4()),
            scan_id=scan.id,
            image_url=url,
            storage_key=storage_key,
            image_type=image_type.value,
            width_px=w,
            height_px=h,
            uploaded_at=datetime.now(timezone.utc),
            image_quality=q_quality,
            sharpness_score=q_score,
            quality_threshold=q_thresh,
            quality_validated_at=datetime.now(timezone.utc),
            analysis_allowed=q_allowed,
            quality_details_json=quality_eval,
        )
        db.add(scan_img)
        uploaded_images.append(scan_img)

        # Audit log individual image quality verification
        await AuditService.log_action(
            db=db,
            action="IMAGE_QUALITY_CHECKED",
            entity_type="scan_image",
            entity_id=scan_img.id,
            user_id=current_user.id,
            metadata={
                "scan_id": scan.id,
                "image_quality": q_quality,
                "sharpness_score": q_score,
                "threshold": q_thresh,
                "analysis_allowed": q_allowed,
                "reason": quality_eval.get("reason"),
            },
        )

    await AuditService.log_action(
        db=db,
        action="IMAGES_UPLOADED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={
            "uploaded_count": len(uploaded_images),
            "all_clear": all(img.analysis_allowed for img in uploaded_images),
        },
    )

    await db.commit()
    for img in uploaded_images:
        await db.refresh(img)

    return APIResponse(
        success=True,
        message=f"{len(uploaded_images)} image(s) uploaded and quality validated successfully",
        data=[ScanImageResponse.model_validate(img) for img in uploaded_images],
    )


@router.post("/{id}/analyze", response_model=APIResponse[AnalyzeScanResponse])
async def trigger_scan_analysis(
    id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_scan),
):
    """
    Triggers AI detection, OCR, and LMPC rule validation.
    Guarded by Image Quality Validation Gate: strictly blocks blurry/low quality images.
    Rate-limited per client IP to safeguard AI resources.
    """
    await check_rate_limit(request, key_prefix="analyze_scan")

    result = await db.execute(select(Scan).where(Scan.id == id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    # Fetch scan images to enforce quality gate
    img_stmt = select(ScanImage).where(ScanImage.scan_id == scan.id)
    scan_images = (await db.execute(img_stmt)).scalars().all()

    if not scan_images:
        raise ValidationException("No packaging label images found for this scan. Please upload an image before requesting analysis.")

    # Check latest image per image type (allows re-uploading clear image to fix a scan)
    def _img_sort_key(img: ScanImage) -> float:
        t = img.uploaded_at or img.quality_validated_at
        if t is not None:
            if hasattr(t, "tzinfo") and t.tzinfo is not None:
                return t.astimezone(timezone.utc).timestamp()
            elif isinstance(t, datetime):
                return t.timestamp()
        return 0.0

    sorted_images = sorted(scan_images, key=_img_sort_key)
    latest_by_type = {}
    for img in sorted_images:
        latest_by_type[img.image_type or "front"] = img
    active_images = list(latest_by_type.values())

    # Quality Gate Check: Reject if active image is blurry or not allowed
    blurry_images = [img for img in active_images if not img.analysis_allowed or img.image_quality != "CLEAR"]
    if blurry_images:
        first_bad = blurry_images[0]
        score_val = first_bad.sharpness_score if first_bad.sharpness_score is not None else 0.0
        thresh_val = first_bad.quality_threshold if first_bad.quality_threshold is not None else settings.BLUR_THRESHOLD

        await AuditService.log_action(
            db=db,
            action="AI_ANALYSIS_BLOCKED",
            entity_type="scan",
            entity_id=scan.id,
            user_id=current_user.id,
            metadata={
                "reason": "IMAGE_TOO_BLURRY",
                "image_id": first_bad.id,
                "image_quality": first_bad.image_quality,
                "sharpness_score": score_val,
                "threshold": thresh_val,
                "total_images": len(scan_images),
                "blurry_count": len(blurry_images),
            },
        )
        meta = dict(scan.metadata_json or {})
        meta["analysis_blocked_reason"] = "IMAGE_TOO_BLURRY"
        scan.metadata_json = meta
        scan.status = "failed"
        await db.commit()

        raise ValidationException(
            "Analysis blocked: The uploaded image is too blurry for reliable text extraction and compliance analysis. "
            "Please re-upload a clearer image or rescan the product."
        )

    # Clear prior blocked reasons if clear image was provided
    meta = dict(scan.metadata_json or {})
    meta.pop("analysis_blocked_reason", None)
    scan.metadata_json = meta
    scan.status = "processing"

    job_id = f"job-{uuid.uuid4().hex[:12]}"

    if settings.CELERY_TASK_ALWAYS_EAGER:
        # Run synchronously / direct background task
        background_tasks.add_task(run_scan_analysis_pipeline_async, scan.id)
    else:
        # Dispatch to Celery queue
        analyze_scan_task.delay(scan.id)

    await AuditService.log_action(
        db=db,
        action="AI_ANALYSIS_TRIGGERED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={"job_id": job_id},
    )
    await db.commit()

    return APIResponse(
        success=True,
        message="AI compliance analysis job queued",
        data=AnalyzeScanResponse(
            job_id=job_id,
            scan_id=scan.id,
            status="queued",
            message="Image processing, region detection, OCR, and rule validation underway.",
        ),
    )


@router.get("/{id}", response_model=APIResponse[ScanDetailResponse])
async def get_scan_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves full scan details including declarations, bounding boxes, and verdicts."""
    stmt = (
        select(Scan)
        .where(Scan.id == id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
    )
    result = await db.execute(stmt)
    scan = result.scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    return APIResponse(
        success=True,
        data=await _build_scan_detail_response(db, scan),
    )


@router.patch("/{id}/batch", response_model=APIResponse[ScanDetailResponse])
async def verify_or_update_scan_batch(
    id: str,
    payload: BatchVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_scan),
):
    """Allows an inspector or reviewer to verify, correct, or confirm the batch number for a scan."""
    stmt = (
        select(Scan)
        .where(Scan.id == id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
    )
    scan = (await db.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    old_batch = scan.batch_number
    old_source = scan.batch_number_source
    new_batch = payload.batch_number.strip()

    scan.batch_number = new_batch
    scan.batch_number_source = "verified"

    meta = dict(scan.metadata_json or {})
    meta["batch_verified_by"] = current_user.name
    meta["batch_verified_by_role"] = current_user.role
    meta["batch_verified_at"] = datetime.now(timezone.utc).isoformat()
    if payload.notes:
        meta["batch_verification_notes"] = payload.notes
    
    # If discrepancy was flagged, clear it if verified
    if meta.get("batch_discrepancy"):
        meta["batch_discrepancy_resolved"] = True

    scan.metadata_json = meta

    await AuditService.log_action(
        db=db,
        action="BATCH_NUMBER_VERIFIED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={
            "old_batch_number": old_batch,
            "new_batch_number": new_batch,
            "old_source": old_source,
            "new_source": "verified",
            "notes": payload.notes,
        },
    )

    await db.commit()
    refreshed_scan = (await db.execute(stmt)).scalar_one()

    return APIResponse(
        success=True,
        message=f"Batch number verified and updated to '{new_batch}'",
        data=await _build_scan_detail_response(db, refreshed_scan),
    )


@router.patch("/{id}/declarations/{decl_id}", response_model=APIResponse[DeclarationResponse])
async def override_declaration(
    id: str,
    decl_id: str,
    payload: DeclarationOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """
    Allows an inspector or reviewer to override an AI verdict with legal review notes.
    Every override is logged in the immutable AuditLog.
    """
    decl_result = await db.execute(
        select(Declaration).where(Declaration.id == decl_id, Declaration.scan_id == id)
    )
    decl = decl_result.scalar_one_or_none()
    if not decl:
        raise NotFoundException(f"Declaration {decl_id} not found for scan {id}")

    old_state = {
        "is_compliant": decl.is_compliant,
        "is_present": decl.is_present,
        "extracted_text": decl.extracted_text,
        "font_size_mm": decl.font_size_mm,
        "severity": decl.severity,
        "human_decision": decl.human_decision,
    }

    if payload.is_compliant is not None:
        decl.is_compliant = payload.is_compliant
    if payload.is_present is not None:
        decl.is_present = payload.is_present
    if payload.extracted_text is not None:
        decl.extracted_text = payload.extracted_text
    if payload.font_size_mm is not None:
        decl.font_size_mm = payload.font_size_mm
    if payload.severity is not None:
        decl.severity = payload.severity.value

    decl.reviewer_override = True
    decl.human_decision = "overridden"
    decl.workflow_decision = "FINALIZED"
    decl.decision_method = "MANUAL"
    decl.verification_status = "INSPECTOR_OVERRIDDEN"
    decl.verification_source = "INSPECTOR"
    decl.reviewer_notes = payload.reviewer_notes
    decl.reviewed_by = current_user.name
    decl.reviewed_at = datetime.now(timezone.utc)

    # Update scan status to under_review if currently needs_review
    scan_res = await db.execute(select(Scan).where(Scan.id == id))
    scan = scan_res.scalar_one_or_none()
    if scan and scan.status in ["needs_review", "processing"]:
        scan.status = "under_review"

    await AuditService.log_action(
        db=db,
        action="DECLARATION_OVERRIDDEN",
        entity_type="declaration",
        entity_id=decl.id,
        user_id=current_user.id,
        metadata={
            "scan_id": id,
            "field_type": decl.field_type,
            "user_name": current_user.name,
            "user_role": current_user.role,
            "decision_method": "MANUAL",
            "workflow_decision": decl.workflow_decision,
            "verification_status": decl.verification_status,
            "verification_source": decl.verification_source,
            "inspector_decision": "overridden",
            "violation_detection_rate": decl.violation_detection_rate,
            "auto_confirm_threshold": decl.auto_confirm_threshold,
            "original_ai_status": decl.original_ai_status,
            "original_ai_confidence": decl.original_ai_confidence,
            "old_state": old_state,
            "new_state": {
                "is_compliant": decl.is_compliant,
                "is_present": decl.is_present,
                "extracted_text": decl.extracted_text,
                "font_size_mm": decl.font_size_mm,
                "severity": decl.severity,
                "human_decision": decl.human_decision,
            },
            "reviewer_notes": payload.reviewer_notes,
        },
    )

    await db.commit()
    await db.refresh(decl)

    return APIResponse(
        success=True,
        message="Declaration verdict overridden successfully",
        data=DeclarationResponse.model_validate(decl),
    )


@router.post("/{id}/declarations/{decl_id}/review", response_model=APIResponse[DeclarationResponse])
async def review_declaration(
    id: str,
    decl_id: str,
    payload: DeclarationReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """
    Officer review endpoint: Confirm, Reject, or Override an AI declaration finding.
    Persists decision and notes, records an immutable audit log entry.
    """
    decl_result = await db.execute(
        select(Declaration).where(Declaration.id == decl_id, Declaration.scan_id == id)
    )
    decl = decl_result.scalar_one_or_none()
    if not decl:
        raise NotFoundException(f"Declaration {decl_id} not found for scan {id}")

    old_state = {
        "is_compliant": decl.is_compliant,
        "severity": decl.severity,
        "human_decision": decl.human_decision,
        "reviewer_override": decl.reviewer_override,
    }

    action_type = (payload.action or "confirm").lower()
    if action_type == "confirm":
        decl.human_decision = "confirmed"
        decl.workflow_decision = "FINALIZED"
        decl.verification_status = "INSPECTOR_CONFIRMED"
        decl.reviewer_override = False
        # If AI marked compliant, maintain compliant; if AI marked non_compliant, maintain non_compliant
        if decl.original_ai_status:
            decl.is_compliant = (decl.original_ai_status == "compliant")
        audit_action = "DECLARATION_CONFIRMED"
    elif action_type == "reject":
        decl.human_decision = "rejected"
        decl.workflow_decision = "FINALIZED"
        decl.verification_status = "INSPECTOR_REJECTED"
        decl.reviewer_override = True
        # Invert AI determination upon officer rejection
        decl.is_compliant = not decl.is_compliant
        decl.severity = "none" if decl.is_compliant else "major"
        audit_action = "DECLARATION_REJECTED"
    else:  # override
        decl.human_decision = "overridden"
        decl.workflow_decision = "FINALIZED"
        decl.verification_status = "INSPECTOR_OVERRIDDEN"
        decl.reviewer_override = True
        if payload.is_compliant is not None:
            decl.is_compliant = payload.is_compliant
        if payload.severity is not None:
            decl.severity = payload.severity.value
        else:
            decl.severity = "none" if decl.is_compliant else "major"
        audit_action = "DECLARATION_OVERRIDDEN"

    decl.decision_method = "MANUAL"
    decl.verification_source = "INSPECTOR"
    decl.reviewer_notes = payload.reviewer_notes
    decl.reviewed_by = current_user.name
    decl.reviewed_at = datetime.now(timezone.utc)

    # Update scan status to under_review if needed
    scan_res = await db.execute(select(Scan).where(Scan.id == id))
    scan = scan_res.scalar_one_or_none()
    if scan and scan.status in ["needs_review", "processing"]:
        scan.status = "under_review"

    await AuditService.log_action(
        db=db,
        action=audit_action,
        entity_type="declaration",
        entity_id=decl.id,
        user_id=current_user.id,
        metadata={
            "scan_id": id,
            "field_type": decl.field_type,
            "user_name": current_user.name,
            "user_role": current_user.role,
            "decision_method": "MANUAL",
            "workflow_decision": decl.workflow_decision,
            "inspector_decision": decl.human_decision,
            "violation_detection_rate": decl.violation_detection_rate,
            "auto_confirm_threshold": decl.auto_confirm_threshold,
            "original_ai_status": decl.original_ai_status,
            "original_ai_confidence": decl.original_ai_confidence,
            "old_state": old_state,
            "new_state": {
                "is_compliant": decl.is_compliant,
                "severity": decl.severity,
                "human_decision": decl.human_decision,
                "reviewer_override": decl.reviewer_override,
            },
            "reviewer_notes": payload.reviewer_notes,
        },
    )

    await db.commit()
    await db.refresh(decl)

    return APIResponse(
        success=True,
        message=f"Declaration finding {action_type}ed successfully",
        data=DeclarationResponse.model_validate(decl),
    )


@router.post("/{id}/finalize", response_model=APIResponse[ScanDetailResponse])
async def finalize_scan(
    id: str,
    payload: ScanFinalizeRequest = ScanFinalizeRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """
    Finalizes the inspection.
    The authoritative overall status is derived directly from the verified individual declaration findings.
    Unresolved manual-review items block finalization.
    """
    stmt = (
        select(Scan)
        .where(Scan.id == id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
    )
    scan = (await db.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    decls = scan.declarations or []
    thresh_val = (scan.metadata_json or {}).get("auto_confirm_threshold", 80.0)

    # Check for unresolved manual-review declarations
    unresolved_items = []
    for d in decls:
        is_officer_resolved = bool(d.human_decision and d.human_decision not in ["NONE", "AUTO-ANALYZED"])
        rate = d.violation_detection_rate if d.violation_detection_rate is not None else ((d.confidence_score or 0.0) * 100.0)
        d_thresh = d.auto_confirm_threshold or thresh_val
        is_auto_confirmed = (
            d.workflow_decision in ["AUTO_CONFIRMED", "AUTOMATICALLY_CONFIRMED"]
            or getattr(d, "verification_status", None) == "AUTO_CONFIRMED"
            or (d.workflow_decision is None and rate >= d_thresh and getattr(d, "severity", None) != "needs_review")
        )
        if not is_officer_resolved and not is_auto_confirmed:
            unresolved_items.append(d)

    if payload.final_decision and payload.final_decision.strip():
        decision_clean = payload.final_decision.strip().lower()
        if decision_clean not in ["compliant", "non_compliant", "needs_review"]:
            raise ValidationException("Final decision must be 'compliant', 'non_compliant', or 'needs_review'")
        decision_source = "officer_specified"
    else:
        # Check if unresolved manual review items exist
        if unresolved_items:
            raise ValidationException(
                f"Cannot finalize inspection: {len(unresolved_items)} declaration(s) require manual officer review. "
                "Please resolve all pending declarations before finalizing."
            )

        # Authoritatively derive overall status from verified declaration states
        has_violation = any(not d.is_compliant for d in decls)
        if has_violation:
            decision_clean = "non_compliant"
        else:
            decision_clean = "compliant"
        decision_source = "derived_from_declarations"

    scan.status = ScanStatusEnum.FINALIZED.value
    
    meta = dict(scan.metadata_json or {})
    meta["final_decision"] = decision_clean
    meta["finalized_by"] = current_user.name
    meta["finalized_by_role"] = current_user.role
    meta["finalized_at"] = datetime.now(timezone.utc).isoformat()
    meta["decision_source"] = decision_source
    if payload.remarks and payload.remarks.strip():
        meta["final_remarks"] = payload.remarks.strip()
        meta["closing_notes"] = payload.remarks.strip()
    meta["closed_by"] = current_user.name
    meta["closed_at"] = datetime.now(timezone.utc).isoformat()
    scan.metadata_json = meta

    if decision_clean == "non_compliant" and scan.batch_number:
        scan.batch_status = "attention_required"
        # Propagate to other scans in the same batch
        b_stmt = select(Scan).where(
            func.lower(Scan.batch_number) == scan.batch_number.strip().lower(),
            Scan.id != scan.id,
            Scan.batch_status == "normal",
        )
        b_res = await db.execute(b_stmt)
        for other_scan in b_res.scalars().all():
            other_scan.batch_status = "attention_required"

    await AuditService.log_action(
        db=db,
        action="SCAN_FINALIZED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={
            "final_decision": decision_clean,
            "decision_source": decision_source,
            "remarks": payload.remarks,
            "user_name": current_user.name,
            "user_role": current_user.role,
            "batch_number": scan.batch_number,
            "batch_status": scan.batch_status,
        },
    )

    await db.commit()
    refreshed_scan = (await db.execute(stmt)).scalar_one()

    return APIResponse(
        success=True,
        message=f"Inspection finalized as {decision_clean.upper().replace('_', ' ')}",
        data=await _build_scan_detail_response(db, refreshed_scan),
    )


@router.get("/{id}/audit-trail", response_model=APIResponse[List[AuditLogResponse]])
async def get_scan_audit_trail(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves the chronological audit trail of all AI events and officer decisions for a scan.
    Read-only for all authenticated roles.
    """
    # Fetch all audit logs where entity_id == id OR metadata contains scan_id == id
    stmt = (
        select(AuditLog, User.name, User.role)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.timestamp.desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    scan_logs: List[AuditLogResponse] = []
    for log, u_name, u_role in rows:
        meta = log.metadata_json or {}
        if (
            (log.entity_type == "scan" and log.entity_id == id)
            or (meta.get("scan_id") == id)
            or (log.entity_type == "declaration" and meta.get("scan_id") == id)
        ):
            scan_logs.append(
                AuditLogResponse(
                    id=log.id,
                    user_id=log.user_id,
                    user_name=u_name or meta.get("user_name") or "System",
                    user_role=u_role or meta.get("user_role") or "Automated",
                    action=log.action,
                    entity_type=log.entity_type,
                    entity_id=log.entity_id,
                    timestamp=log.timestamp,
                    metadata_json=meta,
                )
            )

    return APIResponse(
        success=True,
        data=scan_logs,
    )


@router.post("/{id}/close", response_model=APIResponse[ScanDetailResponse])
async def close_scan(
    id: str,
    payload: CloseScanRequest = CloseScanRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """Marks a scan as reviewed and closed."""
    stmt = (
        select(Scan)
        .where(Scan.id == id)
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
    )
    scan = (await db.execute(stmt)).scalar_one_or_none()
    if not scan:
        raise NotFoundException(f"Scan {id} not found")

    scan.status = (payload.final_status or ScanStatusEnum.CLOSED).value
    
    meta = dict(scan.metadata_json or {})
    if "final_decision" not in meta:
        has_violation = any(not d.is_compliant for d in (scan.declarations or []))
        meta["final_decision"] = "non_compliant" if has_violation else "compliant"
    if payload.notes:
        meta["closing_notes"] = payload.notes
        meta["closed_by"] = current_user.name
        meta["closed_at"] = datetime.now(timezone.utc).isoformat()
    scan.metadata_json = meta

    await AuditService.log_action(
        db=db,
        action="SCAN_CLOSED",
        entity_type="scan",
        entity_id=scan.id,
        user_id=current_user.id,
        metadata={"final_status": scan.status, "notes": payload.notes},
    )

    await db.commit()
    refreshed_scan = (await db.execute(stmt)).scalar_one()

    return APIResponse(
        success=True,
        message="Scan closed successfully",
        data=await _build_scan_detail_response(db, refreshed_scan),
    )



@router.get("", response_model=APIResponse[PaginatedResponse[ScanListItemResponse]])
async def list_scans(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    inspector_id: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search and filter compliance scans with pagination."""
    query = (
        select(Scan)
        .outerjoin(Product, Scan.product_id == Product.id)
        .outerjoin(User, Scan.inspector_id == User.id)
        .options(
            selectinload(Scan.product),
            selectinload(Scan.inspector),
            selectinload(Scan.declarations),
        )
    )

    if status:
        query = query.where(Scan.status == status)
    if source:
        query = query.where(Scan.source == source)
    if brand:
        query = query.where(Product.brand.ilike(f"%{brand}%"))
    if category:
        query = query.where(Product.category.ilike(f"%{category}%"))
    if inspector_id:
        query = query.where(Scan.inspector_id == inspector_id)
    if region:
        query = query.where(User.region == region)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Product.name.ilike(pattern),
                Product.brand.ilike(pattern),
                Scan.location_name.ilike(pattern),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(query.order_by(None).subquery())
    total_count = (await db.execute(count_stmt)).scalar_one()

    # Paginated query
    query = query.order_by(Scan.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    scans = result.scalars().all()

    items: List[ScanListItemResponse] = []
    for s in scans:
        decls = s.declarations or []
        non_comp = sum(1 for d in decls if not d.is_compliant)
        verdict = "compliant" if non_comp == 0 and len(decls) > 0 else ("non_compliant" if non_comp > 0 else "pending")

        items.append(
            ScanListItemResponse(
                id=s.id,
                product_id=s.product_id,
                product_name=s.product.name if s.product else None,
                product_brand=s.product.brand if s.product else None,
                product_category=s.product.category if s.product else None,
                batch_number=s.batch_number,
                batch_status=s.batch_status or "normal",
                inspector_id=s.inspector_id,
                inspector_name=s.inspector.name if s.inspector else None,
                source=ScanSourceEnum(s.source),
                status=ScanStatusEnum(s.status),
                location_name=s.location_name,
                region=s.inspector.region if s.inspector else None,
                total_declarations=len(decls),
                non_compliant_count=non_comp,
                overall_verdict=verdict,
                created_at=s.created_at,
            )
        )

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=items,
            pagination=PaginationMeta(
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        ),
    )
