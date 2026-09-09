from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import AuditService
from app.core.database import get_db
from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import get_current_active_user, require_can_review
from app.models import AuditLog, Declaration, Product, Scan, ScanImage, User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.scan import (
    BatchDetailResponse,
    BatchFindingSummary,
    BatchInspectionItem,
    BatchStatusUpdateRequest,
    BatchSummaryResponse,
)

router = APIRouter(prefix="/batches", tags=["Batch Intelligence"])


@router.get("", response_model=APIResponse[List[BatchSummaryResponse]])
async def list_batches(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lists all distinct product batches recorded across inspection scans."""
    stmt = (
        select(Scan)
        .where(Scan.batch_number.isnot(None), Scan.batch_number != "")
        .options(
            selectinload(Scan.product),
            selectinload(Scan.declarations),
        )
        .order_by(Scan.created_at.desc())
    )
    result = await db.execute(stmt)
    scans = result.scalars().all()

    # Group by batch_number
    batch_map = {}
    for s in scans:
        b_num = s.batch_number.strip()
        if not b_num:
            continue
        if b_num not in batch_map:
            batch_map[b_num] = []
        batch_map[b_num].append(s)

    summaries: List[BatchSummaryResponse] = []
    for b_num, b_scans in batch_map.items():
        total_insp = len(b_scans)
        non_compliant_count = 0
        latest_date = None
        p_name = None
        p_brand = None
        b_status = "normal"

        for s in b_scans:
            if not latest_date or (s.created_at and s.created_at > latest_date):
                latest_date = s.created_at
            if s.product:
                p_name = p_name or s.product.name
                p_brand = p_brand or s.product.brand
            
            # Check if any declarations are non-compliant
            has_fail = any(not d.is_compliant for d in s.declarations)
            meta = s.metadata_json or {}
            final_dec = meta.get("final_decision")
            if has_fail or final_dec == "non_compliant":
                non_compliant_count += 1
            
            if s.batch_status in ["under_investigation", "attention_required"]:
                b_status = s.batch_status

        if non_compliant_count > 0 and b_status == "normal":
            b_status = "attention_required"

        if status_filter and b_status.lower() != status_filter.lower():
            continue

        summaries.append(
            BatchSummaryResponse(
                batch_number=b_num,
                status=b_status,
                product_name=p_name or "Packaged Product",
                product_brand=p_brand or "Standard",
                total_inspections=total_insp,
                non_compliant_count=non_compliant_count,
                attention_required=(b_status in ["attention_required", "under_investigation"]),
                latest_inspection_date=latest_date,
            )
        )

    return APIResponse(
        success=True,
        data=summaries,
    )


@router.get("/{batch_number}", response_model=APIResponse[BatchDetailResponse])
async def get_batch_detail(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves full investigation details, aggregated findings, and inspection history for a batch."""
    stmt = (
        select(Scan)
        .where(
            func.lower(Scan.batch_number) == batch_number.strip().lower()
        )
        .options(
            selectinload(Scan.inspector),
            selectinload(Scan.product),
            selectinload(Scan.images),
            selectinload(Scan.declarations),
        )
        .order_by(Scan.created_at.desc())
    )
    result = await db.execute(stmt)
    scans = result.scalars().all()

    if not scans:
        raise NotFoundException(f"No inspections found for batch number '{batch_number}'")

    total_inspections = len(scans)
    compliant_count = 0
    non_compliant_count = 0
    manual_review_count = 0
    first_date = None
    latest_date = None
    batch_status = scans[0].batch_status or "normal"

    products_map = {}
    findings_counter = {}
    inspection_items: List[BatchInspectionItem] = []

    for s in scans:
        if not first_date or (s.created_at and s.created_at < first_date):
            first_date = s.created_at
        if not latest_date or (s.created_at and s.created_at > latest_date):
            latest_date = s.created_at

        # Track products
        if s.product:
            products_map[s.product.id] = {
                "id": s.product.id,
                "name": s.product.name,
                "brand": s.product.brand,
                "category": s.product.category,
                "manufacturer_name": s.product.manufacturer_name,
            }

        # Count declaration findings & compliance
        s_findings = 0
        s_non_comp = 0
        for d in s.declarations:
            s_findings += 1
            if not d.is_compliant:
                s_non_comp += 1
                key = (d.field_type, d.rule_reference or "LMPC Rules 2011", d.severity or "major")
                findings_counter[key] = findings_counter.get(key, 0) + 1

        meta = s.metadata_json or {}
        final_dec = meta.get("final_decision")

        if final_dec == "compliant" or (not final_dec and s_non_comp == 0):
            comp_st = "Compliant"
            compliant_count += 1
        elif final_dec == "non_compliant" or s_non_comp > 0:
            comp_st = "Non-Compliant"
            non_compliant_count += 1
        else:
            comp_st = "Needs Review"
            manual_review_count += 1

        img_url = s.images[0].image_url if s.images else None

        inspection_items.append(
            BatchInspectionItem(
                id=s.id,
                created_at=s.created_at,
                status=s.status,
                product_id=s.product_id,
                product_name=s.product.name if s.product else "Packaged Product",
                product_brand=s.product.brand if s.product else "Standard",
                product_category=s.product.category if s.product else None,
                inspector_id=s.inspector_id,
                inspector_name=s.inspector.name if s.inspector else None,
                location_name=s.location_name,
                region=s.inspector.region if s.inspector else None,
                compliance_status=comp_st,
                findings_count=s_findings,
                non_compliant_count=s_non_comp,
                human_decision=final_dec,
                image_url=img_url,
            )
        )

        if s.batch_status in ["under_investigation", "attention_required"]:
            batch_status = s.batch_status

    if non_compliant_count > 0 and batch_status == "normal":
        batch_status = "attention_required"

    # Build findings summary
    findings_summary: List[BatchFindingSummary] = []
    for (f_type, r_ref, sev), count in findings_counter.items():
        findings_summary.append(
            BatchFindingSummary(
                field_type=f_type,
                rule_reference=r_ref,
                count=count,
                severity=sev,
            )
        )

    return APIResponse(
        success=True,
        data=BatchDetailResponse(
            batch_number=batch_number,
            status=batch_status,
            total_inspections=total_inspections,
            compliant_inspections=compliant_count,
            non_compliant_inspections=non_compliant_count,
            manual_review_inspections=manual_review_count,
            first_inspection_date=first_date,
            latest_inspection_date=latest_date,
            products=list(products_map.values()),
            findings_summary=findings_summary,
            inspections=inspection_items,
        ),
    )


@router.get("/{batch_number}/inspections", response_model=APIResponse[List[BatchInspectionItem]])
async def get_batch_inspections(
    batch_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lists all inspection scans belonging to a batch."""
    detail_res = await get_batch_detail(batch_number=batch_number, db=db, current_user=current_user)
    return APIResponse(
        success=True,
        data=detail_res.data.inspections,
    )


@router.patch("/{batch_number}/status", response_model=APIResponse[BatchDetailResponse])
async def update_batch_status(
    batch_number: str,
    payload: BatchStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """Updates batch investigation status (e.g. Under Investigation, Attention Required, Resolved)."""
    valid_statuses = ["normal", "attention_required", "under_investigation", "resolved"]
    new_status = payload.status.lower().strip()
    if new_status not in valid_statuses:
        raise ValidationException(f"Invalid status '{payload.status}'. Allowed: {valid_statuses}")

    stmt = select(Scan).where(
        func.lower(Scan.batch_number) == batch_number.strip().lower()
    )
    result = await db.execute(stmt)
    scans = result.scalars().all()

    if not scans:
        raise NotFoundException(f"No inspections found for batch number '{batch_number}'")

    for s in scans:
        s.batch_status = new_status
        meta = dict(s.metadata_json or {})
        meta["batch_status_updated_by"] = current_user.name
        meta["batch_status_notes"] = payload.notes
        meta["batch_status_updated_at"] = datetime.now(timezone.utc).isoformat()
        s.metadata_json = meta

    await AuditService.log_action(
        db=db,
        action="BATCH_STATUS_UPDATED",
        entity_type="batch",
        entity_id=batch_number,
        user_id=current_user.id,
        metadata={
            "new_status": new_status,
            "notes": payload.notes,
            "affected_scans_count": len(scans),
        },
    )

    await db.commit()

    return await get_batch_detail(batch_number=batch_number, db=db, current_user=current_user)
