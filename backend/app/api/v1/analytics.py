from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.rbac import get_current_active_user
from app.models import Declaration, Product, Scan, User
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    AttentionInspectionItem,
    BatchAlertItem,
    CategoryViolationStat,
    OfficerActivityItem,
    OfficerPerformanceItem,
    ProductRiskItem,
    RegionHeatmapItem,
    RuleViolationStat,
    TrendDataPoint,
    ViolationFindingItem,
)
from app.schemas.common import APIResponse

router = APIRouter(prefix="/analytics", tags=["Enforcement Intelligence & Analytics"])


# Standardized statutory rule and field naming helper
FIELD_STATUTORY_NAMES: Dict[str, str] = {
    "mrp": "MRP Declaration & Tax Inclusivity [Rule 6(1)(f)]",
    "net_quantity": "Net Quantity & Standard Units [Rule 6(1)(d) & Rule 8]",
    "manufacturer_details": "Manufacturer / Packer Details [Rule 6(1)(b)]",
    "mfg_date": "Date of Manufacture / Packing [Rule 6(1)(e)]",
    "consumer_care": "Consumer Care Contact Details [Rule 6(1)(h)]",
    "country_of_origin": "Country of Origin [Rule 6(1)(a)]",
    "unit_sale_price": "Unit Sale Price (USP) [Rule 6(1)(k)]",
    "common_name": "Generic or Common Commodity Name [Rule 6(1)(a)]",
    "expiry_date": "Best Before / Expiry Declaration [Rule 6(1)(e)]",
    "font_size": "Mandatory Font Height Verification [Second Schedule]",
    "other": "Other Statutory Requirement",
}


def _classify_scan_verdict(scan: Scan) -> str:
    """
    Determines statutory compliance status for a scan.
    Precedence order:
    1. Explicit human final_decision in metadata ('compliant', 'non_compliant', 'needs_review')
    2. Inspection status: 'needs_review', 'under_review', 'processing', 'failed' -> 'needs_review'
    3. Finalized/closed scans evaluated against declarations:
       - Any non-compliant declaration -> 'non_compliant'
       - All declarations compliant (with at least 1 declaration) -> 'compliant'
       - Otherwise -> 'needs_review'
    """
    meta = scan.metadata_json or {}
    final_dec = meta.get("final_decision")
    if final_dec:
        d = str(final_dec).lower().strip()
        if d in ["compliant", "non_compliant", "needs_review"]:
            return d

    if scan.status in ["needs_review", "under_review", "processing", "failed"]:
        return "needs_review"

    if scan.status in ["closed", "finalized", "reviewed", "verified"]:
        decls = scan.declarations or []
        if not decls:
            return "needs_review"
        has_violation = any(not d.is_compliant for d in decls)
        return "non_compliant" if has_violation else "compliant"

    return "needs_review"


async def _fetch_filtered_scans(
    db: AsyncSession,
    days: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
) -> List[Scan]:
    """Helper to query scans with eager-loaded relationships according to filters."""
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

    if days is not None and isinstance(days, int) and days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(Scan.created_at >= cutoff)

    if category is not None and isinstance(category, str) and category.strip() and category.lower() != "all":
        query = query.where(Product.category.ilike(f"%{category.strip()}%"))

    if region is not None and isinstance(region, str) and region.strip() and region.lower() != "all":
        reg_val = region.strip()
        query = query.where(
            or_(
                User.region.ilike(f"%{reg_val}%"),
                Scan.location_name.ilike(f"%{reg_val}%"),
            )
        )

    result = await db.execute(query.order_by(Scan.created_at.desc()))
    all_scans = result.scalars().all()

    # Status filtering based on effective statutory verdict
    if status is not None and isinstance(status, str) and status.strip() and status.lower() != "all":
        target_status = status.lower().strip()
        all_scans = [s for s in all_scans if _classify_scan_verdict(s) == target_status]

    return all_scans


async def _compute_analytics_summary(
    db: AsyncSession,
    days: Optional[int] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
) -> AnalyticsSummaryResponse:
    """Core calculation engine computing all metrics from database records."""
    scans = await _fetch_filtered_scans(db, days=days, status=status, category=category, region=region)
    total_products = (await db.execute(select(func.count(Product.id)))).scalar_one()

    # Collect available filter values from the full database for dropdowns
    cat_query = await db.execute(select(Product.category).where(Product.category.is_not(None)).distinct())
    available_categories = sorted([c for c in cat_query.scalars().all() if c])

    reg_query = await db.execute(select(User.region).where(User.region.is_not(None)).distinct())
    user_regions = [r for r in reg_query.scalars().all() if r]
    available_regions = sorted(list(set(user_regions)))

    # Pre-populate regions from system users
    region_map = defaultdict(lambda: {"total": 0, "comp": 0, "non_comp": 0, "needs_rev": 0, "rules": defaultdict(int)})
    for reg in available_regions:
        _ = region_map[reg]

    # Pre-populate officers from system users
    officer_map = defaultdict(lambda: {"name": "", "dept": "", "region": "", "total": 0, "comp": 0, "non_comp": 0, "needs_rev": 0, "finalized": 0})
    all_users = (await db.execute(select(User))).scalars().all()
    for u in all_users:
        officer_map[u.id]["name"] = u.name
        officer_map[u.id]["dept"] = u.department or "Field Inspection"
        officer_map[u.id]["region"] = u.region or "National"

    total_inspections = len(scans)
    compliant_count = 0
    non_compliant_count = 0
    needs_review_count = 0
    total_violations = 0
    total_declarations = 0

    finding_map = defaultdict(lambda: {"count": 0, "scans": set(), "rule": "LMPC Rules 2011", "severity": "major"})
    category_map = defaultdict(lambda: {"total": 0, "non_comp": 0, "comp": 0, "needs_rev": 0})
    attention_list: List[AttentionInspectionItem] = []

    for s in scans:
        verdict = _classify_scan_verdict(s)
        decls = s.declarations or []
        total_declarations += len(decls)

        if verdict == "compliant":
            compliant_count += 1
        elif verdict == "non_compliant":
            non_compliant_count += 1
        else:
            needs_review_count += 1

        # Track Category Risk
        cat_name = (s.product.category if s.product and s.product.category else "General / Uncategorized")
        category_map[cat_name]["total"] += 1
        if verdict == "non_compliant":
            category_map[cat_name]["non_comp"] += 1
        elif verdict == "compliant":
            category_map[cat_name]["comp"] += 1
        else:
            category_map[cat_name]["needs_rev"] += 1

        # Track Officer Activity
        officer_id = s.inspector_id or "system"
        if s.inspector:
            officer_map[officer_id]["name"] = s.inspector.name
            officer_map[officer_id]["dept"] = s.inspector.department or "Field Inspection"
            officer_map[officer_id]["region"] = s.inspector.region or "National"

        officer_map[officer_id]["total"] += 1
        if verdict == "compliant":
            officer_map[officer_id]["comp"] += 1
            officer_map[officer_id]["finalized"] += 1
        elif verdict == "non_compliant":
            officer_map[officer_id]["non_comp"] += 1
            officer_map[officer_id]["finalized"] += 1
        else:
            officer_map[officer_id]["needs_rev"] += 1

        # Track Regional Overview
        reg_name = (s.inspector.region if s.inspector and s.inspector.region else (s.location_name or "National Jurisdiction"))
        region_map[reg_name]["total"] += 1
        if verdict == "compliant":
            region_map[reg_name]["comp"] += 1
        elif verdict == "non_compliant":
            region_map[reg_name]["non_comp"] += 1
        else:
            region_map[reg_name]["needs_rev"] += 1

        # Track Findings / Declarations
        s_violations = 0
        s_needs_review = 0
        min_conf = 1.0 if decls else None

        for d in decls:
            conf = d.confidence_score if d.confidence_score is not None else 0.0
            if min_conf is not None and conf < min_conf:
                min_conf = conf

            if not d.is_compliant:
                total_violations += 1
                s_violations += 1
                ftype = d.field_type or "other"
                finding_map[ftype]["count"] += 1
                finding_map[ftype]["scans"].add(s.id)
                finding_map[ftype]["rule"] = d.rule_reference or finding_map[ftype]["rule"]
                finding_map[ftype]["severity"] = d.severity or "major"
                region_map[reg_name]["rules"][d.rule_reference or ftype] += 1
            elif d.severity == "needs_review" or (0.0 < conf < 0.70 and not d.reviewer_override):
                s_needs_review += 1

        # High-Attention Inspections Qualification
        needs_attention = False
        reasons: List[str] = []

        if verdict == "non_compliant":
            needs_attention = True
            reasons.append(f"{s_violations} statutory violation(s)")
        if verdict == "needs_review" or s.status in ["needs_review", "under_review", "processing", "failed"]:
            needs_attention = True
            reasons.append("Pending officer verification")
        if min_conf is not None and min_conf < 0.70:
            needs_attention = True
            reasons.append(f"Low AI confidence ({int(min_conf * 100)}%)")

        if needs_attention:
            attention_list.append(
                AttentionInspectionItem(
                    id=s.id,
                    product_name=s.product.name if s.product else (s.location_name or "Unlinked Commodity"),
                    product_brand=s.product.brand if s.product else None,
                    product_category=s.product.category if s.product else "General",
                    inspector_name=s.inspector.name if s.inspector else "Inspector",
                    location_name=s.location_name or "Field Inspection",
                    status=s.status,
                    final_decision=s.metadata_json.get("final_decision") if s.metadata_json else None,
                    created_at=s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                    findings_count=len(decls),
                    violations_count=s_violations,
                    needs_review_count=s_needs_review,
                    min_confidence=round(min_conf, 2) if min_conf is not None else None,
                    attention_reason=" • ".join(reasons) if reasons else "Requires Review",
                )
            )

    # Calculate compliance rates strictly on finalized inspections
    finalized_count = compliant_count + non_compliant_count
    compliance_rate = round((compliant_count / finalized_count) * 100.0, 1) if finalized_count > 0 else None
    violation_rate = round((non_compliant_count / finalized_count) * 100.0, 1) if finalized_count > 0 else None

    # Overall declaration compliance percentage for backward compatibility
    overall_decl_compliance_pct = (
        round(((total_declarations - total_violations) / total_declarations) * 100.0, 1)
        if total_declarations > 0 else 100.0
    )

    # Format Most Common Findings
    most_common_findings: List[ViolationFindingItem] = []
    for ftype, info in sorted(finding_map.items(), key=lambda x: len(x[1]["scans"]), reverse=True):
        affected_s = len(info["scans"])
        pct_non_comp = round((affected_s / max(1, non_compliant_count)) * 100.0, 1) if non_compliant_count > 0 else 0.0
        most_common_findings.append(
            ViolationFindingItem(
                finding_name=FIELD_STATUTORY_NAMES.get(ftype, ftype.replace("_", " ").title()),
                field_type=ftype,
                rule_reference=info["rule"],
                affected_inspections=affected_s,
                total_violations=info["count"],
                percentage_of_non_compliant=min(100.0, pct_non_comp),
                severity=info["severity"],
            )
        )

    # Format Product Risk Overview
    product_risk_overview: List[ProductRiskItem] = []
    for cat_name, c_data in sorted(category_map.items(), key=lambda x: x[1]["total"], reverse=True):
        c_tot = c_data["total"]
        c_non = c_data["non_comp"]
        c_comp = c_data["comp"]
        c_needs = c_data["needs_rev"]
        c_fin = c_comp + c_non

        c_comp_rate = round((c_comp / c_fin) * 100.0, 1) if c_fin > 0 else None
        c_viol_rate = round((c_non / c_fin) * 100.0, 1) if c_fin > 0 else (round((c_non / c_tot) * 100.0, 1) if c_tot > 0 else None)

        if c_tot < 1:
            r_level = "INSUFFICIENT_DATA"
        elif c_viol_rate is not None and c_viol_rate >= 30.0:
            r_level = "HIGH"
        elif c_viol_rate is not None and c_viol_rate >= 10.0:
            r_level = "MEDIUM"
        else:
            r_level = "LOW"

        product_risk_overview.append(
            ProductRiskItem(
                category=cat_name,
                total_inspections=c_tot,
                non_compliant_count=c_non,
                compliant_count=c_comp,
                needs_review_count=c_needs,
                compliance_rate=c_comp_rate,
                violation_rate=c_viol_rate,
                risk_level=r_level,
            )
        )

    # Format Officer Activity
    officer_activity: List[OfficerActivityItem] = []
    for o_id, o_data in sorted(officer_map.items(), key=lambda x: x[1]["total"], reverse=True):
        officer_activity.append(
            OfficerActivityItem(
                officer_id=o_id,
                officer_name=o_data["name"] or "Officer",
                department=o_data["dept"],
                region=o_data["region"],
                total_inspections=o_data["total"],
                compliant_count=o_data["comp"],
                non_compliant_count=o_data["non_comp"],
                needs_review_count=o_data["needs_rev"],
                finalized_count=o_data["finalized"],
            )
        )

    # Format Regional Overview
    state_code_map = {
        "Maharashtra": "MH", "Delhi": "DL", "Delhi NCR": "DL", "Karnataka": "KA",
        "Tamil Nadu": "TN", "Gujarat": "GJ", "West Bengal": "WB", "Uttar Pradesh": "UP",
        "Rajasthan": "RJ", "Telangana": "TS", "National HQ": "HQ", "National Jurisdiction": "NJ", "HQ": "HQ", "National": "NT"
    }
    regional_overview: List[RegionHeatmapItem] = []
    for reg_name, r_data in sorted(region_map.items(), key=lambda x: x[1]["total"], reverse=True):
        r_tot = r_data["total"]
        r_non = r_data["non_comp"]
        r_comp = r_data["comp"]
        r_needs = r_data["needs_rev"]
        r_fin = r_comp + r_non
        r_viol_rate = round((r_non / r_fin) * 100.0, 1) if r_fin > 0 else (round((r_non / r_tot) * 100.0, 1) if r_tot > 0 else 0.0)

        # Top violated rule in region
        top_rule = None
        if r_data["rules"]:
            top_rule = max(r_data["rules"].items(), key=lambda x: x[1])[0]

        regional_overview.append(
            RegionHeatmapItem(
                region=reg_name,
                state_code=state_code_map.get(reg_name, reg_name[:2].upper()),
                total_inspections=r_tot,
                compliant_count=r_comp,
                non_compliant_count=r_non,
                needs_review_count=r_needs,
                violation_rate=min(100.0, r_viol_rate),
                top_violated_rule=top_rule or "Rule 6 - Statutory Declarations",
            )
        )

    # Format Time Series Trend
    num_days = days if (days and days > 0) else 30
    now = datetime.now(timezone.utc)
    trend: List[TrendDataPoint] = []
    for i in range(num_days - 1, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_str = day_date.strftime("%Y-%m-%d")

        day_scans = [s for s in scans if s.created_at and s.created_at.date() == day_date]
        d_tot = len(day_scans)
        d_comp = sum(1 for s in day_scans if _classify_scan_verdict(s) == "compliant")
        d_non = sum(1 for s in day_scans if _classify_scan_verdict(s) == "non_compliant")
        d_needs = sum(1 for s in day_scans if _classify_scan_verdict(s) == "needs_review")

        trend.append(
            TrendDataPoint(
                date=day_str,
                total_scans=d_tot,
                compliant_scans=d_comp,
                non_compliant_scans=d_non,
                needs_review_scans=d_needs,
            )
        )

    # Generate Dynamic Data-Driven Insights
    dynamic_insights: List[str] = []
    if total_inspections == 0:
        dynamic_insights.append("No inspection records found for the selected filter period.")
    else:
        if most_common_findings:
            top_f = most_common_findings[0]
            dynamic_insights.append(
                f"{top_f.finding_name} is currently the most frequently detected issue ({top_f.affected_inspections} inspection(s) affected)."
            )
        if needs_review_count > 0:
            dynamic_insights.append(
                f"{needs_review_count} inspection(s) currently require manual officer verification or physical check."
            )
        if finalized_count > 0 and violation_rate is not None:
            dynamic_insights.append(
                f"Observed non-compliance is {violation_rate}% across {finalized_count} finalized inspection(s)."
            )
        elif finalized_count == 0:
            dynamic_insights.append(
                f"All {total_inspections} inspection(s) are currently undergoing verification; no finalized determinations yet."
            )
        if product_risk_overview:
            high_risk_cats = [c for c in product_risk_overview if c.risk_level == "HIGH"]
            if high_risk_cats:
                dynamic_insights.append(
                    f"Commodity category '{high_risk_cats[0].category}' exhibits elevated observed non-compliance ({high_risk_cats[0].violation_rate}%)."
                )

    # Legacy compatibility structures
    violations_by_category_compat = [
        CategoryViolationStat(
            category=item.category,
            total_scans=item.total_inspections,
            violations_count=item.non_compliant_count,
            compliance_rate=item.compliance_rate if item.compliance_rate is not None else 100.0,
        )
        for item in product_risk_overview
    ]

    violations_by_rule_compat = [
        RuleViolationStat(
            rule_reference=f.rule_reference,
            field_type=f.field_type,
            severity=f.severity,
            count=f.total_violations,
        )
        for f in most_common_findings[:10]
    ]

    # Batch Intelligence Calculation (from real database records)
    batch_map = defaultdict(lambda: {
        "total": 0,
        "non_comp": 0,
        "comp": 0,
        "needs_rev": 0,
        "status": "normal",
        "p_name": "Packaged Product",
        "p_brand": "Standard",
        "latest_date": None,
    })

    for s in scans:
        if s.batch_number and s.batch_number.strip():
            b_num = s.batch_number.strip()
            b_entry = batch_map[b_num]
            b_entry["total"] += 1
            if s.product:
                b_entry["p_name"] = s.product.name
                b_entry["p_brand"] = s.product.brand
            if not b_entry["latest_date"] or (s.created_at and s.created_at > b_entry["latest_date"]):
                b_entry["latest_date"] = s.created_at
            
            verdict = _classify_scan_verdict(s)
            if verdict == "non_compliant":
                b_entry["non_comp"] += 1
            elif verdict == "compliant":
                b_entry["comp"] += 1
            else:
                b_entry["needs_rev"] += 1

            if s.batch_status in ["under_investigation", "attention_required"]:
                b_entry["status"] = s.batch_status

    batches_inspected = len(batch_map)
    batches_attention_required = 0
    batches_under_investigation = 0
    batch_alerts: List[BatchAlertItem] = []
    frequently_flagged: List[BatchAlertItem] = []

    for b_num, b_data in batch_map.items():
        st = b_data["status"]
        if b_data["non_comp"] > 0 and st == "normal":
            st = "attention_required"
        
        if st == "under_investigation":
            batches_under_investigation += 1
        elif st == "attention_required":
            batches_attention_required += 1

        alert_item = BatchAlertItem(
            batch_number=b_num,
            product_name=b_data["p_name"],
            product_brand=b_data["p_brand"],
            reason=f"{b_data['non_comp']} non-compliant inspection(s) recorded" if b_data["non_comp"] > 0 else "Under batch review",
            related_inspections=b_data["total"],
            non_compliant_inspections=b_data["non_comp"],
            status=st,
            latest_inspection_date=b_data["latest_date"].strftime("%d %b %Y") if b_data["latest_date"] else None,
        )

        if st in ["attention_required", "under_investigation"] or b_data["non_comp"] > 0:
            batch_alerts.append(alert_item)

        if b_data["non_comp"] > 0:
            frequently_flagged.append(alert_item)

    frequently_flagged.sort(key=lambda x: x.non_compliant_inspections, reverse=True)
    # Compliance Automation Findings Calculation (strictly from real declaration records)
    auto_confirmed_findings = 0
    manual_review_findings = 0
    for s in scans:
        for d in (s.declarations or []):
            if not d.is_compliant:
                if d.workflow_decision == "AUTO_CONFIRMED" or (
                    d.violation_detection_rate is not None
                    and d.auto_confirm_threshold is not None
                    and d.violation_detection_rate >= d.auto_confirm_threshold
                ):
                    auto_confirmed_findings += 1
                else:
                    manual_review_findings += 1

    total_viol_findings = auto_confirmed_findings + manual_review_findings
    auto_confirm_rate = round((auto_confirmed_findings / total_viol_findings) * 100.0, 1) if total_viol_findings > 0 else None

    return AnalyticsSummaryResponse(
        # Backward compatibility fields
        total_scans=total_inspections,
        total_products=total_products,
        total_violations=total_violations,
        overall_compliance_percentage=overall_decl_compliance_pct,
        scans_needing_review=needs_review_count,
        scans_closed=compliant_count + non_compliant_count,
        violations_by_category=violations_by_category_compat,
        violations_by_rule=violations_by_rule_compat,
        trend_over_time=trend,
        # Enforcement Intelligence Dashboard Fields
        total_inspections=total_inspections,
        compliant_count=compliant_count,
        non_compliant_count=non_compliant_count,
        needs_review_count=needs_review_count,
        finalized_count=finalized_count,
        compliance_rate=compliance_rate,
        violation_rate=violation_rate,
        compliance_distribution={
            "compliant": compliant_count,
            "non_compliant": non_compliant_count,
            "needs_review": needs_review_count,
        },
        dynamic_insights=dynamic_insights,
        available_categories=available_categories,
        available_regions=available_regions,
        most_common_findings=most_common_findings,
        product_risk_overview=product_risk_overview,
        attention_inspections=attention_list[:25],  # top 25 high-attention items
        officer_activity=officer_activity,
        regional_overview=regional_overview,
        # Batch Intelligence Fields
        batches_inspected=batches_inspected,
        batches_attention_required=batches_attention_required,
        batches_under_investigation=batches_under_investigation,
        frequently_flagged_batches=frequently_flagged[:10],
        batch_investigation_alerts=batch_alerts,
        # Compliance Automation Finding Fields
        automatically_confirmed_findings_count=auto_confirmed_findings,
        manual_review_findings_count=manual_review_findings,
        automatic_confirmation_rate=auto_confirm_rate,
    )


@router.get("/summary", response_model=APIResponse[AnalyticsSummaryResponse])
async def get_analytics_summary(
    days: Optional[int] = Query(None, description="Filter by past N days (e.g. 7, 30, 90). Omit for all-time."),
    status: Optional[str] = Query(None, description="Filter by status: 'all', 'compliant', 'non_compliant', 'needs_review'"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    region: Optional[str] = Query(None, description="Filter by state or region"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Calculates high-level compliance KPI metrics, violation breakdowns, and trend."""
    data = await _compute_analytics_summary(
        db=db, days=days, status=status, category=category, region=region
    )
    return APIResponse(success=True, data=data)


@router.get("/inspection-trends", response_model=APIResponse[List[TrendDataPoint]])
async def get_inspection_trends(
    days: Optional[int] = Query(30, ge=1, le=365),
    status: Optional[str] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns inspection volume time-series trends over the specified period."""
    summary = await _compute_analytics_summary(
        db=db, days=days, status=status, category=category, region=region
    )
    return APIResponse(success=True, data=summary.trend_over_time)


@router.get("/violations", response_model=APIResponse[List[ViolationFindingItem]])
async def get_violations_ranking(
    days: Optional[int] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns ranked list of most common statutory violations / compliance findings."""
    summary = await _compute_analytics_summary(
        db=db, days=days, category=category, region=region
    )
    return APIResponse(success=True, data=summary.most_common_findings)


@router.get("/product-risk", response_model=APIResponse[List[ProductRiskItem]])
async def get_product_risk_overview(
    days: Optional[int] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns observed compliance risk breakdown grouped by product category."""
    summary = await _compute_analytics_summary(
        db=db, days=days, region=region
    )
    return APIResponse(success=True, data=summary.product_risk_overview)


@router.get("/attention", response_model=APIResponse[List[AttentionInspectionItem]])
async def get_attention_inspections(
    days: Optional[int] = None,
    category: Optional[str] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns queue of inspections requiring immediate officer review or enforcement attention."""
    summary = await _compute_analytics_summary(
        db=db, days=days, category=category, region=region
    )
    return APIResponse(success=True, data=summary.attention_inspections)


@router.get("/officer-activity", response_model=APIResponse[List[OfficerActivityItem]])
async def get_officer_activity(
    days: Optional[int] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Returns objective officer inspection counts and finalized records without subjective rankings."""
    summary = await _compute_analytics_summary(
        db=db, days=days, region=region
    )
    return APIResponse(success=True, data=summary.officer_activity)


@router.get("/region-heatmap", response_model=APIResponse[List[RegionHeatmapItem]])
async def get_region_heatmap(
    days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Aggregates inspection and violation rates by geographic region from actual database records."""
    summary = await _compute_analytics_summary(
        db=db, days=days
    )
    return APIResponse(success=True, data=summary.regional_overview)


@router.get("/officer-performance", response_model=APIResponse[List[OfficerPerformanceItem]])
async def get_officer_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Backward-compatible endpoint for officer throughput metrics."""
    stmt = (
        select(
            User.id,
            User.name,
            User.region,
            func.count(Scan.id).label("total_scans"),
            func.sum(case((Scan.status == "closed", 1), else_=0)).label("reviewed_count"),
            func.sum(case((Scan.status == "needs_review", 1), else_=0)).label("pending_count"),
        )
        .outerjoin(Scan, Scan.inspector_id == User.id)
        .group_by(User.id, User.name, User.region)
    )
    result = await db.execute(stmt)

    items: List[OfficerPerformanceItem] = []
    for uid, uname, ureg, tot_s, rev_c, pend_c in result.all():
        viol_stmt = (
            select(func.count(Declaration.id))
            .join(Scan, Declaration.scan_id == Scan.id)
            .where(Scan.inspector_id == uid, Declaration.is_compliant == False)
        )
        viols = (await db.execute(viol_stmt)).scalar_one()

        items.append(
            OfficerPerformanceItem(
                officer_id=uid,
                officer_name=uname,
                region=ureg or "Central",
                total_scans=tot_s or 0,
                reviewed_count=rev_c or 0,
                pending_review_count=pend_c or 0,
                average_review_time_hours=1.5,
                violations_detected=viols or 0,
            )
        )

    return APIResponse(success=True, data=items)
