import io
import pytest
from httpx import AsyncClient
from PIL import Image

from app.api.v1.automation_config import (
    get_current_auto_confirm_threshold,
    set_current_auto_confirm_threshold,
)


from tests.conftest import create_clear_test_image_bytes

def create_test_image_bytes() -> bytes:
    return create_clear_test_image_bytes()


@pytest.mark.asyncio
async def test_workflow_all_auto_confirmed_and_direct_finalization(client: AsyncClient, test_users, auth_headers):
    """
    TEST 1: All 8 declarations >= threshold (auto-confirmed).
    - Inspection is ready for finalization.
    - Finalizing without payload.final_decision derives 'compliant' automatically.
    - No officer dropdown selection required.
    """
    set_current_auto_confirm_threshold(50.0)
    admin_headers = auth_headers("admin")

    # 1. Create a scan
    create_res = await client.post(
        "/api/v1/scans",
        headers=admin_headers,
        json={
            "source": "physical_store",
            "location_name": "Delhi Retail Mart",
            "batch_number": "BATCH-AUTO-ALL-001",
            "product_data": {
                "name": "Organic Almond Milk 1L",
                "brand": "NutriPure",
                "category": "Food & Beverages",
            },
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    # 2. Add an image
    img_bytes = create_test_image_bytes()
    img_res = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=admin_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    assert img_res.status_code == 200

    # 3. Analyze scan
    an_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=admin_headers)
    assert an_res.status_code == 200

    # 4. Check scan details: all declarations auto-confirmed, ready for finalization
    det_res = await client.get(f"/api/v1/scans/{scan_id}", headers=admin_headers)
    assert det_res.status_code == 200
    data = det_res.json()["data"]
    assert data["unresolved_count"] == 0
    assert data["ready_for_finalization"] is True
    assert data["derived_status"] == "compliant"

    # 5. Finalize scan directly without passing final_decision
    fin_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        headers=admin_headers,
        json={},
    )
    assert fin_res.status_code == 200
    fin_data = fin_res.json()["data"]
    assert fin_data["status"] == "finalized"
    assert fin_data["derived_status"] == "compliant"
    assert fin_data["metadata_json"]["final_decision"] == "compliant"
    assert fin_data["metadata_json"]["decision_source"] == "derived_from_declarations"


@pytest.mark.asyncio
async def test_workflow_mixed_unresolved_blocks_finalization(client: AsyncClient, test_users, auth_headers):
    """
    TEST 2: Mixed declarations with manual review required.
    - Finalization is blocked while unresolved manual-review items exist (422 Unprocessable Entity).
    - Resolving remaining manual-review declarations enables finalization.
    """
    try:
        # Set threshold high to force manual review
        set_current_auto_confirm_threshold(99.0)
        inspector_headers = auth_headers("inspector")

        # 1. Create scan
        create_res = await client.post(
            "/api/v1/scans",
            headers=inspector_headers,
            json={
                "source": "physical_store",
                "location_name": "Supermarket Hub",
                "batch_number": "BATCH-MIXED-002",
                "product_data": {
                    "name": "Fruit Juice 500ml",
                    "brand": "TropicFresh",
                    "category": "Food & Beverages",
                },
            },
        )
        assert create_res.status_code == 201
        scan_id = create_res.json()["data"]["id"]

        # 2. Add image & analyze
        img_bytes = create_test_image_bytes()
        await client.post(
            f"/api/v1/scans/{scan_id}/images",
            headers=inspector_headers,
            files={"files": ("front.jpg", img_bytes, "image/jpeg")},
            data={"image_type": "front"},
        )
        await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)

        det_res = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
        data = det_res.json()["data"]
        decls = data["declarations"]
        assert len(decls) > 0
        assert data["unresolved_count"] > 0
        assert data["ready_for_finalization"] is False

        # 3. Attempting to finalize while unresolved should fail (422 ValidationException)
        block_res = await client.post(
            f"/api/v1/scans/{scan_id}/finalize",
            headers=inspector_headers,
            json={},
        )
        assert block_res.status_code == 422
        err_body = str(block_res.json()).lower()
        assert "unresolved" in err_body or "manual" in err_body

        # 4. Resolve all unresolved declarations (confirm them)
        for decl in decls:
            if decl.get("workflow_decision") == "MANUAL_REVIEW_REQUIRED" or not decl.get("human_decision"):
                rev_res = await client.post(
                    f"/api/v1/scans/{scan_id}/declarations/{decl['id']}/review",
                    headers=inspector_headers,
                    json={"action": "confirm", "reviewer_notes": "Verified by inspector."},
                )
                assert rev_res.status_code == 200

        # 5. Check scan is now ready for finalization
        det_after = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
        assert det_after.json()["data"]["unresolved_count"] == 0
        assert det_after.json()["data"]["ready_for_finalization"] is True

        # 6. Finalize now succeeds
        fin_res = await client.post(
            f"/api/v1/scans/{scan_id}/finalize",
            headers=inspector_headers,
            json={},
        )
        assert fin_res.status_code == 200
        assert fin_res.json()["data"]["status"] == "finalized"
    finally:
        # Reset threshold back to 80.0
        set_current_auto_confirm_threshold(80.0)


@pytest.mark.asyncio
async def test_workflow_manual_override_derives_non_compliant(client: AsyncClient, test_users, auth_headers):
    """
    TEST 3: Manual override on a declaration changes derived overall status to NON_COMPLIANT.
    - No overall dropdown selection needed.
    """
    set_current_auto_confirm_threshold(50.0)
    inspector_headers = auth_headers("inspector")

    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "location_name": "Central Retail",
            "batch_number": "BATCH-OVERRIDE-003",
            "product_data": {
                "name": "Shampoo 200ml",
                "brand": "SilkCare",
                "category": "Personal Care",
            },
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=inspector_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)

    det_res = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
    decls = det_res.json()["data"]["declarations"]
    target_decl = decls[0]

    # Inspector overrides declaration to is_compliant=False (violation)
    rev_res = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{target_decl['id']}/review",
        headers=inspector_headers,
        json={
            "action": "override",
            "is_compliant": False,
            "severity": "major",
            "reviewer_notes": "Font size is below statutory minimum mm.",
        },
    )
    assert rev_res.status_code == 200

    # Check that derived status is now non_compliant
    det_after = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
    assert det_after.json()["data"]["derived_status"] == "non_compliant"

    # Finalize without passing final_decision dropdown
    fin_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        headers=inspector_headers,
        json={},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["data"]["metadata_json"]["final_decision"] == "non_compliant"
    assert fin_res.json()["data"]["metadata_json"]["decision_source"] == "derived_from_declarations"


@pytest.mark.asyncio
async def test_workflow_finalization_with_empty_or_optional_remarks(client: AsyncClient, test_users, auth_headers):
    """
    TEST 4: Finalize without mandatory final remarks.
    - Successfully finalizes even if remarks is None or empty.
    """
    set_current_auto_confirm_threshold(50.0)
    inspector_headers = auth_headers("inspector")

    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "batch_number": "BATCH-NOREMARKS-004",
            "product_data": {"name": "Biscuits 100g", "brand": "CrispyBite", "category": "Food"},
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=inspector_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)

    # Finalize with remarks=None
    fin_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        headers=inspector_headers,
        json={"remarks": None},
    )
    assert fin_res.status_code == 200
    assert fin_res.json()["data"]["status"] == "finalized"


@pytest.mark.asyncio
async def test_report_generation_with_derived_decision_and_breakdown(client: AsyncClient, test_users, auth_headers):
    """
    TEST 5: Finalize and generate PDF/DOCX report.
    - Report summary contains derived overall_status and resolution breakdown.
    - PDF/DOCX endpoints return 200 with application/pdf and docx content types.
    """
    set_current_auto_confirm_threshold(50.0)
    inspector_headers = auth_headers("inspector")

    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "batch_number": "BATCH-REPORT-005",
            "product_data": {"name": "Tea Leaves 250g", "brand": "ChaiTime", "category": "Beverages"},
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=inspector_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)
    fin_res = await client.post(f"/api/v1/scans/{scan_id}/finalize", headers=inspector_headers, json={})
    assert fin_res.status_code == 200

    # Generate report
    rep_res = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        headers=inspector_headers,
        json={"notes": "Standard statutory report"},
    )
    assert rep_res.status_code == 201
    rep_data = rep_res.json()["data"]
    rep_id = rep_data["id"]

    # Verify summary data has derived decision basis
    summary = rep_data["summary_data"]
    assert summary["overall_status"] == "compliant"
    assert "decision_basis" in summary
    assert "auto_confirmed_count" in summary
    assert "inspector_resolved_count" in summary

    # Verify PDF download
    pdf_res = await client.get(f"/api/v1/reports/{rep_id}/pdf", headers=inspector_headers)
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers.get("content-type", "")

    # Verify DOCX download
    docx_res = await client.get(f"/api/v1/reports/{rep_id}/docx", headers=inspector_headers)
    assert docx_res.status_code == 200


@pytest.mark.asyncio
async def test_historical_record_compatibility(client: AsyncClient, test_users, auth_headers):
    """
    TEST 6: Historical record containing older metadata fields still loads correctly.
    """
    inspector_headers = auth_headers("inspector")

    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "batch_number": "BATCH-HIST-006",
            "product_data": {"name": "Legacy Product", "brand": "OldBrand", "category": "General"},
            "metadata_json": {
                "final_decision": "compliant",
                "finalized_by": "Senior Officer Roy",
                "finalized_at": "2025-01-15T10:30:00Z",
                "final_remarks": "Legacy inspection record remarks.",
                "ai_preliminary_verdict": "compliant",
            },
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    det_res = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
    assert det_res.status_code == 200
    meta = det_res.json()["data"]["metadata_json"]
    assert meta["final_decision"] == "compliant"
    assert meta["finalized_by"] == "Senior Officer Roy"
    assert meta["final_remarks"] == "Legacy inspection record remarks."


@pytest.mark.asyncio
async def test_batch_intelligence_with_derived_final_status(client: AsyncClient, test_users, auth_headers):
    """
    TEST 7: Batch intelligence uses derived final status to escalate attention.
    """
    set_current_auto_confirm_threshold(50.0)
    inspector_headers = auth_headers("inspector")

    batch_num = "BATCH-INTELLIGENCE-007"
    # Create Scan
    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "batch_number": batch_num,
            "product_data": {"name": "Batch Test Item", "brand": "BrandX", "category": "Packaged"},
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=inspector_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)

    det_res = await client.get(f"/api/v1/scans/{scan_id}", headers=inspector_headers)
    target_decl = det_res.json()["data"]["declarations"][0]

    # Override declaration to non_compliant
    await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{target_decl['id']}/review",
        headers=inspector_headers,
        json={"action": "override", "is_compliant": False, "severity": "major", "reviewer_notes": "Statutory violation"},
    )

    # Finalize (derived status is non_compliant)
    fin_res = await client.post(f"/api/v1/scans/{scan_id}/finalize", headers=inspector_headers, json={})
    assert fin_res.status_code == 200

    # Query batch details
    b_res = await client.get(f"/api/v1/batches/{batch_num}", headers=inspector_headers)
    assert b_res.status_code == 200
    b_data = b_res.json()["data"]
    assert b_data["non_compliant_inspections"] >= 1
    assert b_data["status"] in ["attention_required", "under_investigation"]


@pytest.mark.asyncio
async def test_analytics_metrics_with_derived_final_status(client: AsyncClient, test_users, auth_headers):
    """
    TEST 8: Analytics metrics properly reflect finalized determinations.
    """
    set_current_auto_confirm_threshold(50.0)
    inspector_headers = auth_headers("inspector")

    analytics_before = await client.get("/api/v1/analytics/summary", headers=inspector_headers)
    assert analytics_before.status_code == 200
    initial_finalized = analytics_before.json()["data"]["finalized_count"]

    # Create and finalize a scan with complete product info
    create_res = await client.post(
        "/api/v1/scans",
        headers=inspector_headers,
        json={
            "source": "physical_store",
            "batch_number": "BATCH-ANALYTICS-008",
            "product_data": {"name": "Roasted Cashews 200g", "brand": "BrandY", "category": "Food & Beverages"},
        },
    )
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        headers=inspector_headers,
        files={"files": ("front.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=inspector_headers)
    
    fin_res = await client.post(f"/api/v1/scans/{scan_id}/finalize", headers=inspector_headers, json={})
    assert fin_res.status_code == 200

    analytics_after = await client.get("/api/v1/analytics/summary", headers=inspector_headers)
    assert analytics_after.status_code == 200
    assert analytics_after.json()["data"]["finalized_count"] == initial_finalized + 1
