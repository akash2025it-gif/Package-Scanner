import asyncio
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.pipeline import AIPipeline
from app.core.audit import AuditService
from app.core.database import AsyncSessionLocal
from app.models import Declaration, Scan, ScanImage
from app.services.storage import get_storage_service
from app.workers.celery_app import celery_app


async def _execute_analysis(db: AsyncSession, scan_id: str) -> Dict[str, Any]:
    from sqlalchemy.orm import selectinload

    storage_service = get_storage_service()
    pipeline = AIPipeline()

    result = await db.execute(
        select(Scan).where(Scan.id == scan_id).options(selectinload(Scan.product))
    )
    scan = result.scalar_one_or_none()
    if not scan:
        return {"status": "error", "message": f"Scan {scan_id} not found"}

    try:
        # Fetch images for this scan ordered by upload time
        img_result = await db.execute(select(ScanImage).where(ScanImage.scan_id == scan_id).order_by(ScanImage.uploaded_at.asc()))
        images = img_result.scalars().all()

        # Group by image_type to get active latest images
        latest_by_type = {}
        for img in images:
            latest_by_type[img.image_type] = img
        active_images = list(latest_by_type.values())

        # Quality Gate Defense: Block background execution if active images failed quality validation
        blurry_imgs = [img for img in active_images if not img.analysis_allowed or img.image_quality != "CLEAR"]
        if blurry_imgs:
            scan.status = "failed"
            meta = dict(scan.metadata_json or {})
            meta["analysis_blocked_reason"] = "IMAGE_TOO_BLURRY"
            meta["quality_validation_error"] = "The uploaded image is too blurry for reliable text extraction and compliance analysis."
            scan.metadata_json = meta
            await AuditService.log_action(
                db=db,
                action="AI_ANALYSIS_BLOCKED",
                entity_type="scan",
                entity_id=scan.id,
                user_id=scan.inspector_id,
                metadata={"reason": "IMAGE_TOO_BLURRY", "blurry_count": len(blurry_imgs)},
            )
            await db.commit()
            return {
                "status": "error",
                "message": "Analysis blocked: The uploaded image is too blurry for reliable text extraction and compliance analysis. Please re-upload a clearer image or rescan the product.",
                "scan_id": scan_id,
            }

        image_bytes = b""
        if active_images:
            primary_image = active_images[0]
            try:
                image_bytes = await storage_service.get_file_bytes(primary_image.storage_key)
            except Exception:
                image_bytes = b""

        # Prepare product info
        product_info = {}
        if scan.product:
            product_info = {
                "name": scan.product.name,
                "brand": scan.product.brand,
                "category": scan.product.category,
                "manufacturer_name": scan.product.manufacturer_name,
                "manufacturer_address": scan.product.manufacturer_address,
                "country_of_origin": scan.product.country_of_origin,
                "barcode": scan.product.barcode,
            }
        meta = scan.metadata_json or {}
        if "ocr_mock_batch" in meta:
            product_info["batch_number"] = meta["ocr_mock_batch"]
        elif scan.batch_number:
            product_info["batch_number"] = scan.batch_number

        # Run AI Pipeline
        analysis_result = await pipeline.analyze_image_bytes(
            image_bytes=image_bytes,
            scan_metadata=scan.metadata_json or {},
            product_info=product_info,
        )

        # Fetch current automatic confirmation threshold
        from app.api.v1.automation_config import get_current_auto_confirm_threshold
        threshold = get_current_auto_confirm_threshold()

        # Map prior human decisions by field_type before deleting to preserve human overrides across reanalysis
        existing_human_decisions = {}
        existing_decls = await db.execute(select(Declaration).where(Declaration.scan_id == scan_id))
        for d in existing_decls.scalars().all():
            if d.human_decision:
                existing_human_decisions[d.field_type.lower()] = {
                    "human_decision": d.human_decision,
                    "reviewer_override": d.reviewer_override,
                    "reviewed_by": d.reviewed_by,
                    "reviewed_at": d.reviewed_at,
                    "reviewer_notes": d.reviewer_notes,
                    "is_compliant": d.is_compliant,
                    "severity": d.severity,
                    "workflow_decision": d.workflow_decision or "FINALIZED",
                    "decision_method": d.decision_method or "MANUAL",
                }
            await db.delete(d)

        auto_confirmed_count = 0
        manual_review_count = 0

        # Persist new declaration rows
        for item in analysis_result.get("declarations", []):
            is_pass = item.get("is_compliant", False)
            conf = item.get("confidence_score")
            sev = item.get("severity", "none")
            field_key = item["field_type"].lower()
            
            # Compute standardized confidence score (0.0 to 1.0)
            clean_conf = 0.0
            if conf is not None and isinstance(conf, (int, float)):
                try:
                    c_float = float(conf)
                    if not (c_float != c_float):  # check not NaN
                        if 0.0 <= c_float <= 1.0:
                            clean_conf = c_float
                        elif 0.0 <= c_float <= 100.0:
                            clean_conf = c_float / 100.0
                        else:
                            clean_conf = -1.0  # Invalid out-of-range flag
                    else:
                        clean_conf = -1.0
                except Exception:
                    clean_conf = -1.0
            else:
                clean_conf = -1.0

            # Determine initial AI status
            if is_pass:
                ai_st = "compliant"
            elif sev == "needs_review" or (0.0 < clean_conf < 0.70):
                ai_st = "needs_review"
            else:
                ai_st = "non_compliant"

            # Individual Declaration Auto-Confirmation Decision Logic
            bbox = item.get("bounding_box", {})
            has_evidence = bool((bbox.get("w", 0) > 0 or bbox.get("width", 0) > 0) and (bbox.get("h", 0) > 0 or bbox.get("height", 0) > 0))
            is_extracted = bool(item.get("is_present") and item.get("extracted_text"))
            has_conflict = bool(
                item.get("has_conflict")
                or item.get("data_conflict")
                or item.get("requires_manual_verification")
                or (sev == "needs_review" and not is_pass)
                or (not has_evidence and is_pass)
            )

            decl_rate = round(clean_conf * 100.0, 1) if (clean_conf >= 0.0 and conf is not None) else None

            if clean_conf < 0.0 or conf is None:
                # Missing or invalid percentage outside 0-100%
                workflow_dec = "MANUAL_REVIEW_REQUIRED"
                dec_method = "MANUAL"
                dec_reason = "Declaration confidence is missing or invalid. Inspector verification is required."
                verif_status = "MANUAL_REVIEW_REQUIRED"
                verif_source = "MANUAL"
            elif has_conflict or not is_extracted or not has_evidence:
                workflow_dec = "MANUAL_REVIEW_REQUIRED"
                dec_method = "MANUAL"
                if has_conflict:
                    dec_reason = item.get("conflict_details") or "Extraction conflict or inconsistency with package evidence detected. Inspector verification is required."
                elif not has_evidence:
                    dec_reason = "No verifiable visual evidence bounding box located for this declaration. Inspector verification is required."
                else:
                    dec_reason = "Declaration was not reliably extracted from the package image. Inspector verification is required."
                verif_status = "MANUAL_REVIEW_REQUIRED"
                verif_source = "MANUAL"
            elif threshold is not None and decl_rate is not None and decl_rate >= threshold:
                workflow_dec = "AUTO_CONFIRMED"
                dec_method = "SYSTEM_THRESHOLD"
                if is_pass:
                    dec_reason = f"Declaration confidence ({decl_rate:.0f}%) meets the configured automatic-confirmation threshold ({threshold:.0f}%). The finding was automatically confirmed for the inspection workflow."
                else:
                    dec_reason = f"Declaration confidence ({decl_rate:.0f}%) meets the configured automatic-confirmation threshold ({threshold:.0f}%). The non-compliance finding was automatically confirmed for the inspection workflow."
                verif_status = "AUTO_CONFIRMED"
                verif_source = "SYSTEM_THRESHOLD"
            else:
                decl_rate = round(clean_conf * 100.0, 1)
                workflow_dec = "MANUAL_REVIEW_REQUIRED"
                dec_method = "MANUAL"
                dec_reason = f"Declaration confidence ({decl_rate:.0f}%) is below the configured automatic-confirmation threshold ({threshold:.0f}%). Inspector verification is required."
                verif_status = "MANUAL_REVIEW_REQUIRED"
                verif_source = "MANUAL"

            # Check if prior human decision exists for this field
            prior = existing_human_decisions.get(field_key)
            if prior:
                h_decision = prior["human_decision"]
                rev_override = prior["reviewer_override"]
                rev_by = prior["reviewed_by"]
                rev_at = prior["reviewed_at"]
                rev_notes = prior["reviewer_notes"]
                final_is_pass = prior["is_compliant"]
                final_sev = prior["severity"]
                workflow_dec = "FINALIZED"
                dec_method = "MANUAL"
                verif_status = f"INSPECTOR_{h_decision.upper()}" if h_decision else "FINALIZED"
                verif_source = "INSPECTOR"
            else:
                h_decision = None
                rev_override = False
                rev_by = None
                rev_at = None
                rev_notes = item.get("reviewer_notes")
                final_is_pass = is_pass
                final_sev = sev
                if workflow_dec == "AUTO_CONFIRMED":
                    auto_confirmed_count += 1
                else:
                    manual_review_count += 1

            decl = Declaration(
                id=str(uuid.uuid4()),
                scan_id=scan.id,
                field_type=item["field_type"],
                extracted_text=item.get("extracted_text"),
                raw_extracted_value=item.get("raw_extracted_value") or item.get("extracted_text"),
                normalized_numeric_value=item.get("normalized_numeric_value"),
                normalized_unit=item.get("normalized_unit"),
                has_conflict=has_conflict,
                conflict_details=item.get("conflict_details"),
                bounding_box=bbox,
                confidence_score=max(0.0, clean_conf) if clean_conf >= 0.0 else 0.0,
                font_size_mm=item.get("font_size_mm"),
                is_present=item.get("is_present", False),
                is_compliant=final_is_pass,
                rule_reference=item.get("rule_reference", "LMPC Rules 2011"),
                severity=final_sev,
                reviewer_override=rev_override,
                reviewer_notes=rev_notes,
                original_ai_status=ai_st,
                original_ai_confidence=max(0.0, clean_conf) if clean_conf >= 0.0 else 0.0,
                violation_detection_rate=decl_rate,
                auto_confirm_threshold=threshold,
                workflow_decision=workflow_dec,
                decision_method=dec_method,
                decision_reason=dec_reason,
                verification_status=verif_status,
                verification_source=verif_source,
                human_decision=h_decision,
                reviewed_by=rev_by,
                reviewed_at=rev_at,
            )
            db.add(decl)

        # Update scan status and metadata
        scan.status = "needs_review"
        meta = dict(scan.metadata_json or {})
        meta["ai_preliminary_verdict"] = analysis_result.get("overall_status", "needs_review")
        meta["auto_confirm_threshold"] = threshold
        meta["auto_confirmed_findings_count"] = auto_confirmed_count
        meta["manual_review_findings_count"] = manual_review_count
        meta["total_declarations_count"] = len(analysis_result.get("declarations", []))

        # OCR Batch Extraction & Discrepancy Detection
        import re
        ocr_full_text = analysis_result.get("ocr_full_text", "")
        batch_match = re.search(
            r"\b(?:batch(?:\s*(?:no\.?|num(?:ber)?|code))?|lot(?:\s*(?:no\.?|num(?:ber)?|code))?|b\.?\s*no\.?|l\.?\s*no\.?)\s*[:\-\.]?\s*([A-Za-z0-9\-\/]+)",
            ocr_full_text,
            re.IGNORECASE,
        )

        extracted_batch = None
        extracted_conf = 0.0
        if batch_match:
            extracted_batch = batch_match.group(1).strip()
            extracted_conf = 0.95
            scan.batch_number_extracted = extracted_batch
            scan.batch_number_confidence = extracted_conf

        if not scan.batch_number and extracted_batch:
            scan.batch_number = extracted_batch
            scan.batch_number_source = "ocr"
        elif scan.batch_number and not scan.batch_number_source:
            scan.batch_number_source = "manual"

        # Check for batch discrepancy
        if scan.batch_number and extracted_batch:
            if scan.batch_number.strip().upper() != extracted_batch.strip().upper():
                meta["batch_discrepancy"] = True
                meta["manual_batch_number"] = scan.batch_number
                meta["extracted_batch_number"] = extracted_batch
                meta["extracted_batch_confidence"] = extracted_conf
            else:
                meta["batch_discrepancy"] = False

        # Batch Level Intelligence Alert check
        has_violations = any(not d.get("is_compliant", False) for d in analysis_result.get("declarations", []))
        if scan.batch_number:
            if has_violations:
                scan.batch_status = "attention_required"
                # Propagate attention_required status to other scans in the same batch if they were normal
                batch_scans_stmt = select(Scan).where(
                    func.lower(Scan.batch_number) == scan.batch_number.strip().lower(),
                    Scan.id != scan.id,
                    Scan.batch_status == "normal",
                )
                batch_scans_res = await db.execute(batch_scans_stmt)
                for b_scan in batch_scans_res.scalars().all():
                    b_scan.batch_status = "attention_required"
            elif scan.batch_status == "normal":
                exist_st = await db.execute(
                    select(Scan.batch_status).where(
                        func.lower(Scan.batch_number) == scan.batch_number.strip().lower(),
                        Scan.batch_status.in_(["attention_required", "under_investigation"]),
                    ).limit(1)
                )
                found_st = exist_st.scalar_one_or_none()
                if found_st:
                    scan.batch_status = found_st

        scan.metadata_json = meta
        
        # Log to AuditLog
        await AuditService.log_action(
            db=db,
            action="AI_ANALYSIS_COMPLETED",
            entity_type="scan",
            entity_id=scan.id,
            user_id=scan.inspector_id,
            metadata={
                "declarations_count": len(analysis_result.get("declarations", [])),
                "overall_status": analysis_result.get("overall_status"),
                "auto_confirm_threshold": threshold,
                "auto_confirmed_count": auto_confirmed_count,
                "manual_review_count": manual_review_count,
                "batch_number": scan.batch_number,
                "batch_number_source": scan.batch_number_source,
                "batch_status": scan.batch_status,
            },
        )

        await db.commit()
        return {
            "status": "success",
            "scan_id": scan_id,
            "overall_status": analysis_result.get("overall_status"),
        }
    except Exception as exc:
        scan.status = "failed"
        await AuditService.log_action(
            db=db,
            action="AI_ANALYSIS_FAILED",
            entity_type="scan",
            entity_id=scan.id,
            user_id=scan.inspector_id,
            metadata={"error": str(exc)},
        )
        await db.commit()
        return {"status": "error", "message": str(exc), "scan_id": scan_id}


async def run_scan_analysis_pipeline_async(scan_id: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
    """Asynchronous core logic to analyze a scan's images and persist declaration verdicts."""
    if db is not None:
        return await _execute_analysis(db, scan_id)
    else:
        async with AsyncSessionLocal() as session:
            return await _execute_analysis(session, scan_id)


@celery_app.task(name="tasks.analyze_scan_task")
def analyze_scan_task(scan_id: str):
    """Celery task wrapper."""
    return asyncio.run(run_scan_analysis_pipeline_async(scan_id))
