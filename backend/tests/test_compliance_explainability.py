import io
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.rules.config_loader import RuleConfigLoader
from app.rules.engine import RuleEngine
from app.rules.validators.common_name import CommonNameValidator
from app.rules.validators.font_size import FontSizeValidator
from app.rules.validators.mrp import MRPValidator
from app.rules.validators.net_quantity import NetQuantityValidator
from app.workers.tasks import run_scan_analysis_pipeline_async
from app.services.reports.generator import ReportCoordinator


@pytest.mark.asyncio
async def test_deduplication_and_normalized_keys(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test that all 8 mandatory declarations are uniquely represented without duplicates."""
    headers = auth_headers("inspector")

    # 1. Create and analyze scan for Dry Fruits
    create_resp = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Spencer's Retail, Delhi",
            "product_data": {
                "name": "Premium California Almonds 250g",
                "brand": "NutriBite",
                "category": "Dry Fruits & Nuts",
            },
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    scan_id = create_resp.json()["data"]["id"]

    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 2. Get scan detail
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    decls = detail_resp.json()["data"]["declarations"]

    field_types = [d["field_type"] for d in decls]
    # Check that each field_type is unique
    assert len(field_types) == len(set(field_types)), f"Duplicate fields detected: {field_types}"
    assert "net_quantity" in field_types
    assert field_types.count("net_quantity") == 1, "Net quantity must appear exactly once!"

    # 3. Generate Report and check context declarations
    rep_resp = await client.post(f"/api/v1/scans/{scan_id}/report", headers=headers)
    assert rep_resp.status_code == 201
    report = rep_resp.json()["data"]
    summary = report["summary_data"]
    rep_fields = [d["field_type"] for d in summary["declarations"]]
    assert len(rep_fields) == len(set(rep_fields)), f"Duplicate report fields detected: {rep_fields}"
    assert rep_fields.count("net_quantity") == 1


def test_common_name_handling_and_candidate_detection():
    """Test common name candidate recognition and uncertain verification handling."""
    loader = RuleConfigLoader.get_instance()
    rule = loader.get_rule_by_id("RULE_6_1_A_COMMON_NAME")
    validator = CommonNameValidator()

    # 1. Clear common name declaration with high confidence
    res_pass = validator.validate(rule, "California Almonds (Dry Fruits)", confidence_score=0.95)
    assert res_pass.is_compliant is True
    assert res_pass.severity == "none"
    assert "Statutory generic or common name" in res_pass.notes

    # 2. Candidate extracted from product category when OCR is uncertain
    res_candidate = validator.validate(
        rule,
        text="",
        metadata={"product_name": "NutriBite Whole Cashew", "product_category": "Dry Fruits"},
        confidence_score=0.92,
    )
    assert res_candidate.is_compliant is True
    assert "Dry Fruits" in res_candidate.extracted_value

    # 3. Completely uncertain / unverified generic name
    res_uncertain = validator.validate(rule, text="", metadata={}, confidence_score=0.0)
    assert res_uncertain.is_compliant is False
    assert res_uncertain.needs_review is True
    assert res_uncertain.severity == "needs_review"
    assert "could not be confidently verified" in res_uncertain.notes
    # Must NOT be a confirmed violation
    assert res_uncertain.severity != "critical"


def test_confidence_thresholds_and_categories():
    """Test confidence categorization: HIGH (>=0.90), MEDIUM (0.70-0.89), LOW (<0.70 -> NEEDS_REVIEW)."""
    loader = RuleConfigLoader.get_instance()
    rule = loader.get_rule_by_id("RULE_6_1_F_MRP")
    validator = MRPValidator()

    # High confidence (0.95) -> COMPLIANT
    res_high = validator.validate(rule, "MRP ₹ 100.00 (inclusive of all taxes)", confidence_score=0.95)
    assert res_high.is_compliant is True
    assert res_high.confidence_level == "HIGH"
    assert res_high.needs_review is False

    # Medium confidence (0.75) -> COMPLIANT
    res_med = validator.validate(rule, "MRP ₹ 100.00 (inclusive of all taxes)", confidence_score=0.75)
    assert res_med.is_compliant is True
    assert res_med.confidence_level == "MEDIUM"
    assert res_med.needs_review is False

    # Low confidence (0.55) -> NEEDS_REVIEW, do not treat as confirmed violation
    res_low = validator.validate(rule, "MRP ₹ 100.00 (inclusive of all taxes)", confidence_score=0.55)
    assert res_low.is_compliant is False
    assert res_low.needs_review is True
    assert res_low.severity == "needs_review"
    assert res_low.confidence_level == "LOW"
    assert "low OCR confidence" in res_low.notes


def test_font_size_uncalibrated_disclaimer():
    """Test that uncalibrated images display visual estimation disclaimers."""
    loader = RuleConfigLoader.get_instance()
    rule = loader.get_rule_by_id("RULE_6_1_D_NET_QUANTITY")
    validator = NetQuantityValidator()

    # Uncalibrated fallback
    res = validator.validate(
        rule,
        text="Net Qty: 500 g",
        metadata={"calibration_method": "estimated_default_dpi_fallback"},
        font_size_mm=2.5,
        confidence_score=0.95,
    )
    assert res.is_compliant is True
    assert "Estimated visual size: approximately 2.5 mm — subject to manual verification" in res.notes


def test_overall_compliance_determination():
    """Test that uncertain findings result in NEEDS_REVIEW, not NON_COMPLIANT."""
    engine = RuleEngine()

    # Case 1: All compliant with high confidence
    compliant_evals = [
        {"is_compliant": True, "confidence_score": 0.95, "severity": "none", "needs_review": False},
        {"is_compliant": True, "confidence_score": 0.92, "severity": "none", "needs_review": False},
    ]
    assert engine.calculate_overall_status(compliant_evals) == "compliant"

    # Case 2: Only uncertain findings (no confirmed violations) -> NEEDS_REVIEW
    uncertain_evals = [
        {"is_compliant": True, "confidence_score": 0.95, "severity": "none", "needs_review": False},
        {"is_compliant": False, "confidence_score": 0.50, "severity": "needs_review", "needs_review": True},
    ]
    assert engine.calculate_overall_status(uncertain_evals) == "needs_review"

    # Case 3: Confirmed violation with high confidence -> NON_COMPLIANT
    violation_evals = [
        {"is_compliant": True, "confidence_score": 0.95, "severity": "none", "needs_review": False},
        {"is_compliant": False, "confidence_score": 0.95, "severity": "critical", "needs_review": False, "is_present": True},
    ]
    assert engine.calculate_overall_status(violation_evals) == "non_compliant"


@pytest.mark.asyncio
async def test_human_in_the_loop_wording_in_reports(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test that generated PDF and DOCX reports contain human-in-the-loop statutory wording."""
    headers = auth_headers("inspector")

    # 1. Create scan
    create_resp = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Metro Cash & Carry, Bengaluru",
            "product_data": {
                "name": "Organic Turmeric Powder 100g",
                "brand": "SpiceRoot",
                "category": "Spices",
            },
        },
        headers=headers,
    )
    scan_id = create_resp.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 2. Generate Report
    rep_resp = await client.post(f"/api/v1/scans/{scan_id}/report", headers=headers)
    assert rep_resp.status_code == 201
    rep_data = rep_resp.json()["data"]
    summary = rep_data["summary_data"]

    # Check statutory assessment wording
    stat_assess = summary["statutory_assessment"]
    assert "Notice for compounding or prosecution may be initiated" not in stat_assess
    assert "Department of Legal Metrology" in summary.get("statutory_assessment", "") or "Legal Metrology" in str(summary)

    # 3. Test PDF download
    pdf_resp = await client.get(f"/api/v1/reports/{rep_data['id']}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert len(pdf_resp.content) > 200

    # 4. Test DOCX download
    docx_resp = await client.get(f"/api/v1/reports/{rep_data['id']}/docx", headers=headers)
    assert docx_resp.status_code == 200
    assert len(docx_resp.content) > 200


@pytest.mark.asyncio
async def test_dynamic_commodity_handling_dry_fruits_biscuits_rice(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Verify dynamic commodity analysis for dry fruits, biscuits, and rice."""
    headers = auth_headers("inspector")

    commodities = [
        {"name": "Whole Cashew Nuts 200g", "brand": "RoyalDryFruit", "category": "Dry Fruits"},
        {"name": "Butter Marie Biscuits 300g", "brand": "CrispyBakes", "category": "Biscuits"},
        {"name": "Traditional Basmati Rice 5kg", "brand": "GrainHeritage", "category": "Grains & Rice"},
    ]

    for item in commodities:
        create_resp = await client.post(
            "/api/v1/scans",
            json={"location_name": "Retail Store", "product_data": item},
            headers=headers,
        )
        assert create_resp.status_code == 201
        scan_id = create_resp.json()["data"]["id"]
        await run_scan_analysis_pipeline_async(scan_id, db=db_session)

        detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()["data"]
        decls = detail["declarations"]
        assert len(decls) >= 8

        # Verify no hardcoded foreign brands
        decl_texts = " ".join([d.get("extracted_text") or "" for d in decls])
        assert "AASHIRVAAD" not in decl_texts.upper()
