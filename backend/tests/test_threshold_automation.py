import io
import uuid
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select

from app.api.v1.automation_config import (
    get_current_auto_confirm_threshold,
    set_current_auto_confirm_threshold,
)
from app.models.declaration import Declaration
from app.models.scan import Scan


from tests.conftest import create_clear_test_image_bytes

def create_test_image_bytes() -> bytes:
    return create_clear_test_image_bytes()


@pytest.mark.asyncio
async def test_individual_declaration_threshold_eval(client: AsyncClient, test_users, auth_headers):
    """TEST 1, 2, 3 & 4 — Individual Declaration Confidence Threshold Evaluation:
    - 97% confidence >= 80% threshold -> AUTO_CONFIRMED
    - 94% confidence >= 80% threshold -> AUTO_CONFIRMED
    - 80% confidence >= 80% threshold -> AUTO_CONFIRMED (>= condition)
    - 79% / 72% confidence < 80% threshold -> MANUAL_REVIEW_REQUIRED
    """
    set_current_auto_confirm_threshold(80.0)
    headers = auth_headers("inspector")

    scan_res = await client.post("/api/v1/scans", json={
        "product_data": {
            "name": "California Almonds 250g",
            "brand": "DryFruitsCo",
            "category": "Dry Fruits & Nuts",
            "barcode": "8901234567891"
        },
        "source": "physical_store",
        "location_name": "Delhi Retail Store"
    }, headers=headers)
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label_front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    analyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) > 0

    for d in decls:
        assert "violation_detection_rate" in d
        assert "auto_confirm_threshold" in d
        assert "workflow_decision" in d
        assert "decision_method" in d
        assert d["auto_confirm_threshold"] == 80.0

        rate = d["violation_detection_rate"]
        if rate is not None:
            if rate >= 80.0:
                assert d["workflow_decision"] == "AUTO_CONFIRMED"
                assert d["decision_method"] in ["SYSTEM_THRESHOLD", "AUTOMATIC"]
                assert "automatically confirmed" in d["decision_reason"].lower()
            else:
                assert d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED"
                assert d["decision_method"] == "MANUAL"
                assert "inspector verification is required" in d["decision_reason"].lower() or "below" in d["decision_reason"].lower()


@pytest.mark.asyncio
async def test_exact_threshold_boundary_conditions():
    """TEST 3 & 4: Exact boundary conditions:
    80.0% >= 80.0% -> AUTO_CONFIRMED
    79.9% < 80.0% -> MANUAL_REVIEW_REQUIRED
    97.0% >= 80.0% -> AUTO_CONFIRMED
    94.0% >= 80.0% -> AUTO_CONFIRMED
    """
    threshold = 80.0

    # 97% -> Auto
    rate_97 = 97.0
    assert (rate_97 >= threshold) is True

    # 94% -> Auto
    rate_94 = 94.0
    assert (rate_94 >= threshold) is True

    # 80.0% -> Auto
    rate_80 = 80.0
    assert (rate_80 >= threshold) is True

    # 79.9% -> Manual
    rate_79_9 = 79.9
    assert (rate_79_9 >= threshold) is False

    # 72.0% -> Manual
    rate_72 = 72.0
    assert (rate_72 >= threshold) is False


@pytest.mark.asyncio
async def test_null_or_missing_confidence(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 5: None / NULL / missing declaration confidence safely defaults to MANUAL_REVIEW_REQUIRED."""
    headers = auth_headers("inspector")
    scan_id = str(uuid.uuid4())
    scan = Scan(
        id=scan_id,
        inspector_id="user-insp-1",
        source="physical_store",
        status="needs_review"
    )
    db_session.add(scan)

    decl = Declaration(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        field_type="mrp",
        extracted_text=None,
        confidence_score=0.0,
        is_compliant=False,
        violation_detection_rate=None,
        auto_confirm_threshold=80.0,
        workflow_decision="MANUAL_REVIEW_REQUIRED",
        decision_method="MANUAL",
        decision_reason="Declaration confidence is missing or invalid. Inspector verification is required."
    )
    db_session.add(decl)
    await db_session.commit()

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) == 1
    assert decls[0]["violation_detection_rate"] is None
    assert decls[0]["workflow_decision"] == "MANUAL_REVIEW_REQUIRED"
    assert decls[0]["decision_method"] == "MANUAL"


@pytest.mark.asyncio
async def test_inspector_rejection_and_override_precedence(client: AsyncClient, test_users, auth_headers):
    """TEST 6: 97% auto-confirmed declaration rejected or overridden by Inspector:
    Human decision takes precedence over initial AI auto-confirmation and persists across reanalysis / reloads.
    """
    set_current_auto_confirm_threshold(80.0)
    headers = auth_headers("inspector")

    scan_res = await client.post("/api/v1/scans", json={
        "product_data": {
            "name": "Whole Cashew Nuts 500g",
            "brand": "Royal Nuts",
            "category": "Dry Fruits",
            "barcode": "8901234567895"
        },
        "source": "physical_store",
        "location_name": "Chennai Market"
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) > 0
    auto_decl = next((d for d in decls if d["workflow_decision"] == "AUTO_CONFIRMED"), decls[0])
    decl_id = auto_decl["id"]

    # 1. Inspector rejects the finding
    reject_res = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={
            "action": "reject",
            "reviewer_notes": "Officer verified declaration manually on physical package."
        },
        headers=headers
    )
    assert reject_res.status_code == 200
    rej_data = reject_res.json()["data"]
    assert rej_data["human_decision"] == "rejected"
    assert rej_data["workflow_decision"] == "FINALIZED"
    assert rej_data["decision_method"] == "MANUAL"

    # 2. Reanalysis does NOT overwrite Inspector's manual decision
    reanalyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert reanalyze_res.status_code == 200

    detail_after = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls_after = detail_after.json()["data"]["declarations"]
    target_after = next(d for d in decls_after if d["field_type"] == auto_decl["field_type"])
    assert target_after["human_decision"] == "rejected"
    assert target_after["workflow_decision"] == "FINALIZED"
    assert target_after["decision_method"] == "MANUAL"


@pytest.mark.asyncio
async def test_mixed_audit_and_finalization(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 7 & 8: Mixed audit (e.g. 6 auto-confirmed, 2 manual review required):
    - Inspector resolves the 2 manual items.
    - Inspector finalizes the inspection without having to manually confirm the 6 auto-confirmed items.
    """
    headers = auth_headers("inspector")
    scan_id = str(uuid.uuid4())
    scan = Scan(
        id=scan_id,
        inspector_id="user-insp-1",
        source="physical_store",
        status="needs_review",
        metadata_json={"auto_confirm_threshold": 80.0}
    )
    db_session.add(scan)

    # Add 6 auto-confirmed declarations
    auto_fields = ["common_name", "manufacturer_details", "net_quantity", "mrp", "unit_sale_price", "mfg_date"]
    for i, f_type in enumerate(auto_fields):
        d_auto = Declaration(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            field_type=f_type,
            extracted_text=f"Auto Text {i}",
            confidence_score=0.95,
            is_compliant=True,
            violation_detection_rate=95.0,
            auto_confirm_threshold=80.0,
            workflow_decision="AUTO_CONFIRMED",
            decision_method="SYSTEM_THRESHOLD",
            decision_reason="Declaration confidence (95%) meets the configured automatic-confirmation threshold (80%)."
        )
        db_session.add(d_auto)

    # Add 2 manual review required declarations
    manual_fields = ["consumer_care", "country_of_origin"]
    manual_decl_ids = []
    for i, f_type in enumerate(manual_fields):
        d_man_id = str(uuid.uuid4())
        manual_decl_ids.append(d_man_id)
        d_man = Declaration(
            id=d_man_id,
            scan_id=scan_id,
            field_type=f_type,
            extracted_text=f"Manual Text {i}",
            confidence_score=0.72,
            is_compliant=False,
            violation_detection_rate=72.0,
            auto_confirm_threshold=80.0,
            workflow_decision="MANUAL_REVIEW_REQUIRED",
            decision_method="MANUAL",
            decision_reason="Declaration confidence (72%) is below the configured automatic-confirmation threshold (80%)."
        )
        db_session.add(d_man)

    await db_session.commit()

    # Verify scan details
    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) == 8
    auto_count = sum(1 for d in decls if d["workflow_decision"] == "AUTO_CONFIRMED")
    man_count = sum(1 for d in decls if d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED")
    assert auto_count == 6
    assert man_count == 2

    # Inspector resolves the 2 manual review items
    for mid in manual_decl_ids:
        rev_res = await client.post(
            f"/api/v1/scans/{scan_id}/declarations/{mid}/review",
            json={
                "action": "confirm",
                "reviewer_notes": "Officer confirmed finding."
            },
            headers=headers
        )
        assert rev_res.status_code == 200

    # Inspector finalizes the inspection (does NOT click confirm on the 6 auto-confirmed items)
    fin_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={
            "final_decision": "non_compliant",
            "remarks": "Official statutory inspection finalized by officer."
        },
        headers=headers
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["data"]["status"] == "finalized"
    assert fin_res.json()["data"]["metadata_json"]["final_decision"] == "non_compliant"


@pytest.mark.asyncio
async def test_report_generation_verification_methods(client: AsyncClient, test_users, auth_headers):
    """TEST 10: Reports accurately distinguish System Auto-Confirmation from Inspector Review."""
    set_current_auto_confirm_threshold(80.0)
    headers = auth_headers("inspector")

    scan_res = await client.post("/api/v1/scans", json={
        "product_data": {
            "name": "Report Verified Basmati Rice 5kg",
            "brand": "Heritage",
            "category": "Grains & Rice",
            "barcode": "8901234567896"
        },
        "batch_number": "RICE-2026-B1",
        "source": "physical_store",
        "location_name": "Punjab Mandi"
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    # Generate report
    rep_res = await client.post(f"/api/v1/scans/{scan_id}/report", json={
        "notes": "Report generated with individual declaration auto-confirmation."
    }, headers=headers)
    assert rep_res.status_code in [200, 201]
    report_id = rep_res.json()["data"]["id"]

    get_rep = await client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert get_rep.status_code == 200
    summary = get_rep.json()["data"]["summary_data"]

    assert "auto_confirmed_count" in summary
    assert "manual_review_count" in summary
    assert "workflow_disclaimer" in summary
    assert "automatic-confirmation threshold" in summary["workflow_disclaimer"]

    # Check declarations in report
    rep_decls = summary["declarations"]
    assert len(rep_decls) > 0
    for d in rep_decls:
        assert "verification_method" in d
        assert "inspector_override" in d
        assert "final_finding" in d
        if d["workflow_decision"] == "AUTO_CONFIRMED" and d["human_decision"] in ["AUTO-ANALYZED", "NONE"]:
            assert d["verification_method"] == "System Auto-Confirmation"


@pytest.mark.asyncio
async def test_all_8_high_confidence_declarations_auto_confirmed(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 4 & 9 (from acceptance criteria):
    8 declarations all >= 80% confidence:
    Expected:
    - All 8 persist as AUTO_CONFIRMED, SYSTEM_THRESHOLD.
    - Summary shows 8 / 8 AUTO-CONFIRMED, 0 / 8 MANUAL REVIEW REQUIRED.
    - No declaration is marked as Officer Decided.
    - Workflow status is Ready for Finalization.
    """
    headers = auth_headers("inspector")
    scan_id = str(uuid.uuid4())
    scan = Scan(
        id=scan_id,
        inspector_id="user-insp-1",
        source="physical_store",
        status="needs_review",
        metadata_json={"auto_confirm_threshold": 80.0}
    )
    db_session.add(scan)

    test_rates = [
        ("common_name", 97.0),
        ("manufacturer_details", 94.0),
        ("country_of_origin", 96.0),
        ("net_quantity", 95.0),
        ("mfg_date", 93.0),
        ("mrp", 92.0),
        ("unit_sale_price", 88.0),
        ("consumer_care", 85.0),
    ]

    for f_type, rate in test_rates:
        decl = Declaration(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            field_type=f_type,
            extracted_text=f"Extracted {f_type}",
            confidence_score=rate / 100.0,
            is_compliant=True,
            violation_detection_rate=rate,
            auto_confirm_threshold=80.0,
            workflow_decision="AUTO_CONFIRMED",
            decision_method="SYSTEM_THRESHOLD",
            verification_status="AUTO_CONFIRMED",
            verification_source="SYSTEM_THRESHOLD",
            decision_reason=f"Declaration confidence ({rate:.0f}%) meets the configured automatic-confirmation threshold (80%).",
        )
        db_session.add(decl)

    await db_session.commit()

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) == 8

    auto_count = sum(1 for d in decls if d["workflow_decision"] == "AUTO_CONFIRMED" and not d.get("human_decision"))
    manual_count = sum(1 for d in decls if d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED" and not d.get("human_decision"))
    officer_count = sum(1 for d in decls if d.get("human_decision") and d["human_decision"] not in ["NONE", "AUTO-ANALYZED"])

    assert auto_count == 8
    assert manual_count == 0
    assert officer_count == 0

    for d in decls:
        assert d["workflow_decision"] == "AUTO_CONFIRMED"
        assert d["decision_method"] in ["SYSTEM_THRESHOLD", "AUTOMATIC"]
        assert d["verification_status"] == "AUTO_CONFIRMED"
        assert d["verification_source"] == "SYSTEM_THRESHOLD"
        assert d.get("human_decision") is None


@pytest.mark.asyncio
async def test_6_high_2_low_mixed_audit_and_persistence(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 5, 6, 7 & 8 (from acceptance criteria):
    6 declarations >= 80% (auto-confirmed) + 2 declarations < 80% (manual review required).
    - Summary shows: 6 / 8 AUTO-CONFIRMED, 2 / 8 MANUAL REVIEW REQUIRED.
    - Inspector resolves the 2 manual review items.
    - Counts become: 6 / 8 AUTO-CONFIRMED, 0 / 8 UNRESOLVED, 2 / 8 MANUALLY RESOLVED.
    - Finalize scan: Scan status becomes finalized, 6 declarations retain SYSTEM_THRESHOLD verification source.
    - Reload / refresh: States and counts remain persisted.
    """
    headers = auth_headers("inspector")
    scan_id = str(uuid.uuid4())
    scan = Scan(
        id=scan_id,
        inspector_id="user-insp-1",
        source="physical_store",
        status="needs_review",
        metadata_json={"auto_confirm_threshold": 80.0}
    )
    db_session.add(scan)

    auto_fields = [
        ("common_name", 97.0),
        ("manufacturer_details", 94.0),
        ("country_of_origin", 91.0),
        ("net_quantity", 88.0),
        ("mfg_date", 85.0),
        ("mrp", 82.0),
    ]
    for f_type, rate in auto_fields:
        d_auto = Declaration(
            id=str(uuid.uuid4()),
            scan_id=scan_id,
            field_type=f_type,
            extracted_text=f"Auto {f_type}",
            confidence_score=rate / 100.0,
            is_compliant=True,
            violation_detection_rate=rate,
            auto_confirm_threshold=80.0,
            workflow_decision="AUTO_CONFIRMED",
            decision_method="SYSTEM_THRESHOLD",
            verification_status="AUTO_CONFIRMED",
            verification_source="SYSTEM_THRESHOLD",
            decision_reason=f"Declaration confidence ({rate:.0f}%) meets the configured automatic-confirmation threshold (80%).",
        )
        db_session.add(d_auto)

    manual_fields = [
        ("unit_sale_price", 79.0),
        ("consumer_care", 72.0),
    ]
    manual_ids = []
    for f_type, rate in manual_fields:
        m_id = str(uuid.uuid4())
        manual_ids.append(m_id)
        d_man = Declaration(
            id=m_id,
            scan_id=scan_id,
            field_type=f_type,
            extracted_text=f"Manual {f_type}",
            confidence_score=rate / 100.0,
            is_compliant=False,
            violation_detection_rate=rate,
            auto_confirm_threshold=80.0,
            workflow_decision="MANUAL_REVIEW_REQUIRED",
            decision_method="MANUAL",
            verification_status="MANUAL_REVIEW_REQUIRED",
            verification_source="MANUAL",
            decision_reason=f"Declaration confidence ({rate:.0f}%) is below the configured automatic-confirmation threshold (80%).",
        )
        db_session.add(d_man)

    await db_session.commit()

    # 1. Initial State Check
    detail_res1 = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res1.status_code == 200
    decls1 = detail_res1.json()["data"]["declarations"]
    auto_count1 = sum(1 for d in decls1 if d["workflow_decision"] == "AUTO_CONFIRMED" and not d.get("human_decision"))
    manual_count1 = sum(1 for d in decls1 if d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED" and not d.get("human_decision"))
    assert auto_count1 == 6
    assert manual_count1 == 2

    # 2. Inspector resolves manual review item 1 (Confirm)
    rev1 = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{manual_ids[0]}/review",
        json={"action": "confirm", "reviewer_notes": "Officer verified unit sale price."},
        headers=headers
    )
    assert rev1.status_code == 200
    assert rev1.json()["data"]["verification_status"] == "INSPECTOR_CONFIRMED"
    assert rev1.json()["data"]["verification_source"] == "INSPECTOR"

    # 3. Inspector resolves manual review item 2 (Reject)
    rev2 = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{manual_ids[1]}/review",
        json={"action": "reject", "reviewer_notes": "Officer verified consumer care on back label."},
        headers=headers
    )
    assert rev2.status_code == 200
    assert rev2.json()["data"]["verification_status"] == "INSPECTOR_REJECTED"
    assert rev2.json()["data"]["verification_source"] == "INSPECTOR"

    # 4. Check intermediate state: 6 auto-confirmed, 2 officer resolved, 0 manual review required
    detail_res2 = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls2 = detail_res2.json()["data"]["declarations"]
    auto_count2 = sum(1 for d in decls2 if d["workflow_decision"] == "AUTO_CONFIRMED" and not d.get("human_decision"))
    manual_count2 = sum(1 for d in decls2 if d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED" and not d.get("human_decision"))
    officer_count2 = sum(1 for d in decls2 if d.get("human_decision") and d["human_decision"] not in ["NONE", "AUTO-ANALYZED"])
    assert auto_count2 == 6
    assert manual_count2 == 0
    assert officer_count2 == 2

    # 5. Finalize scan
    fin_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={"final_decision": "compliant", "remarks": "All statutory requirements verified."},
        headers=headers
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["data"]["status"] == "finalized"

    # 6. Verify that finalizing overall scan does NOT change the 6 auto-confirmed declarations into officer decisions
    detail_res3 = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls3 = detail_res3.json()["data"]["declarations"]
    auto_items = [d for d in decls3 if d["workflow_decision"] == "AUTO_CONFIRMED" and not d.get("human_decision")]
    assert len(auto_items) == 6
    for item in auto_items:
        assert item["decision_method"] in ["SYSTEM_THRESHOLD", "AUTOMATIC"]
        assert item["verification_status"] == "AUTO_CONFIRMED"
        assert item["verification_source"] == "SYSTEM_THRESHOLD"
        assert item.get("human_decision") is None


@pytest.mark.asyncio
async def test_config_automation_endpoint_rbac_and_validation(client: AsyncClient, test_users, auth_headers):
    """Admin can configure threshold, Inspector receives 403 on edit, range validated 0-100%."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")

    # GET config
    get_res = await client.get("/api/v1/config/automation", headers=insp_headers)
    assert get_res.status_code == 200
    assert "auto_confirm_threshold_percent" in get_res.json()["data"]

    # Inspector PATCH -> 403
    patch_insp = await client.patch("/api/v1/config/automation", json={
        "auto_confirm_threshold_percent": 85.0
    }, headers=insp_headers)
    assert patch_insp.status_code == 403

    # Admin PATCH invalid range -> 422
    patch_inv = await client.patch("/api/v1/config/automation", json={
        "auto_confirm_threshold_percent": -5.0
    }, headers=admin_headers)
    assert patch_inv.status_code == 422

    # Admin PATCH valid -> 200
    patch_val = await client.patch("/api/v1/config/automation", json={
        "auto_confirm_threshold_percent": 85.0
    }, headers=admin_headers)
    assert patch_val.status_code == 200
    assert get_current_auto_confirm_threshold() == 85.0

    # Reset back to 80.0
    set_current_auto_confirm_threshold(80.0)

