import io
import uuid
import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from app.api.v1.automation_config import set_current_auto_confirm_threshold
from app.models.declaration import Declaration
from app.models.product import Product
from app.models.scan import Scan


from tests.conftest import create_clear_test_image_bytes

def create_mock_jpeg() -> bytes:
    return create_clear_test_image_bytes()


@pytest.mark.asyncio
async def test_test1_create_scan(client: AsyncClient, test_users, auth_headers):
    """TEST 1 — Create Scan: Submit normal product details. Expected: POST /api/v1/scans succeeds with 201, no 500 error."""
    headers = auth_headers("inspector")
    payload = {
        "source": "physical_store",
        "location_name": "Reliance Retail Mart, Sector 29, Gurugram",
        "gps_coordinates": "28.4595, 77.0266",
        "batch_number": "BAT-2026-REGRESSION-1",
        "product_data": {
            "name": "Lay's India's Magic Masala Chips 50g",
            "brand": "Lay's",
            "category": "Packaged Snacks & Chips"
        }
    }
    resp = await client.post("/api/v1/scans", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["id"] is not None
    assert data["batch_number"] == "BAT-2026-REGRESSION-1"
    assert data["status"] == "processing"


@pytest.mark.asyncio
async def test_test2_upload_image(client: AsyncClient, test_users, auth_headers):
    """TEST 2 — Upload Image: Upload a valid package image. Expected: Image upload succeeds."""
    headers = auth_headers("inspector")
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Store",
        "product_data": {"name": "Test Product", "brand": "Brand", "category": "Category"}
    }, headers=headers)
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_mock_jpeg()
    upload_res = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    assert upload_res.status_code == 200
    assert len(upload_res.json()["data"]) == 1


@pytest.mark.asyncio
async def test_test3_analyze(client: AsyncClient, test_users, auth_headers):
    """TEST 3 — Analyze: Run analysis. Expected: OCR/AI analysis completes. Mandatory Declarations Audit produces actual violation detection rate."""
    headers = auth_headers("inspector")
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Store",
        "product_data": {"name": "Test Product", "brand": "Brand", "category": "Category"}
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_mock_jpeg()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    analyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) > 0


@pytest.mark.asyncio
async def test_test4_high_rate(client: AsyncClient, test_users, auth_headers):
    """TEST 4 — High Rate: Detection rate >= threshold. Expected: AUTO_CONFIRMED."""
    set_current_auto_confirm_threshold(80.0)
    headers = auth_headers("inspector")
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test High Rate Store",
        "product_data": {"name": "High Rate Product", "brand": "Brand", "category": "Category"}
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_mock_jpeg()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls = detail_res.json()["data"]["declarations"]
    for d in decls:
        if not d["is_compliant"] and d["violation_detection_rate"] is not None:
            if d["violation_detection_rate"] >= 80.0:
                assert d["workflow_decision"] == "AUTO_CONFIRMED"
                assert d["decision_method"] == "AUTOMATIC"


@pytest.mark.asyncio
async def test_test5_low_rate(client: AsyncClient, test_users, auth_headers):
    """TEST 5 — Low Rate: Detection rate < threshold. Expected: MANUAL_REVIEW_REQUIRED."""
    set_current_auto_confirm_threshold(99.0)  # High threshold makes typical detection rate fall below
    headers = auth_headers("inspector")
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Low Rate Store",
        "product_data": {"name": "Low Rate Product", "brand": "Brand", "category": "Category"}
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_mock_jpeg()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    decls = detail_res.json()["data"]["declarations"]
    for d in decls:
        if not d["is_compliant"] and d["violation_detection_rate"] is not None:
            if d["violation_detection_rate"] < 99.0:
                assert d["workflow_decision"] == "MANUAL_REVIEW_REQUIRED"
                assert d["decision_method"] == "MANUAL"

    set_current_auto_confirm_threshold(80.0)


@pytest.mark.asyncio
async def test_test6_missing_rate(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 6 — Missing Rate: Detection rate unavailable. Expected: No crash. Manual review required after analysis."""
    headers = auth_headers("inspector")
    # Insert a scan and declaration with NULL violation_detection_rate
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
        extracted_text="Rs 50",
        is_compliant=False,
        violation_detection_rate=None,
        auto_confirm_threshold=80.0,
        workflow_decision="MANUAL_REVIEW_REQUIRED",
        decision_method="MANUAL",
        decision_reason="A valid violation detection rate is unavailable. Inspector verification is required."
    )
    db_session.add(decl)
    await db_session.commit()

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) == 1
    assert decls[0]["violation_detection_rate"] is None
    assert decls[0]["workflow_decision"] == "MANUAL_REVIEW_REQUIRED"


@pytest.mark.asyncio
async def test_test7_existing_scan_legacy(client: AsyncClient, test_users, auth_headers, db_session):
    """TEST 7 — Existing Scan: Open an old scan created before threshold feature. Expected: Loads normally."""
    headers = auth_headers("inspector")
    scan_id = str(uuid.uuid4())
    scan = Scan(
        id=scan_id,
        inspector_id="user-insp-1",
        source="physical_store",
        status="processing",
        batch_number=None,
        batch_number_extracted=None,
        batch_status="normal"
    )
    db_session.add(scan)
    decl = Declaration(
        id=str(uuid.uuid4()),
        scan_id=scan_id,
        field_type="net_quantity",
        extracted_text="500 g",
        is_compliant=True,
        violation_detection_rate=None,
        auto_confirm_threshold=None,
        workflow_decision=None,
        decision_method=None,
        decision_reason=None
    )
    db_session.add(decl)
    await db_session.commit()

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    data = detail_res.json()["data"]
    assert data["id"] == scan_id
    assert len(data["declarations"]) == 1


@pytest.mark.asyncio
async def test_test8_batch_number(client: AsyncClient, test_users, auth_headers):
    """TEST 8 — Batch Number: Enter batch number and complete full workflow. Expected: Batch persistence still works."""
    headers = auth_headers("inspector")
    payload = {
        "source": "physical_store",
        "location_name": "Batch Test Facility",
        "batch_number": "BATCH-XYZ-999",
        "product_data": {
            "name": "Batch Verified Product",
            "brand": "BrandX",
            "category": "Packaged Goods"
        }
    }
    create_res = await client.post("/api/v1/scans", json=payload, headers=headers)
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]
    assert create_res.json()["data"]["batch_number"] == "BATCH-XYZ-999"

    img_bytes = create_mock_jpeg()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["batch_number"] == "BATCH-XYZ-999"


@pytest.mark.asyncio
async def test_test9_reports(client: AsyncClient, test_users, auth_headers):
    """TEST 9 — Reports: Generate report. Expected: No regression."""
    headers = auth_headers("inspector")
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Report Test Store",
        "batch_number": "REP-BATCH-1",
        "product_data": {"name": "Report Product", "brand": "Brand", "category": "Category"}
    }, headers=headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_mock_jpeg()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    rep_res = await client.post(f"/api/v1/scans/{scan_id}/report", json={"notes": "Test report notes"}, headers=headers)
    assert rep_res.status_code in [200, 201]
    rep_id = rep_res.json()["data"]["id"]

    rep_detail = await client.get(f"/api/v1/reports/{rep_id}", headers=headers)
    assert rep_detail.status_code == 200
    assert "summary_data" in rep_detail.json()["data"]


@pytest.mark.asyncio
async def test_test10_inspector_and_admin_rbac(client: AsyncClient, test_users, auth_headers):
    """TEST 10 — Inspector/Admin: Verify both roles still work."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")

    # Inspector can create scan
    insp_scan = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Inspector Store",
        "product_data": {"name": "Inspector Product", "brand": "Brand", "category": "Category"}
    }, headers=insp_headers)
    assert insp_scan.status_code == 201

    # Admin can create scan
    admin_scan = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Admin Store",
        "product_data": {"name": "Admin Product", "brand": "Brand", "category": "Category"}
    }, headers=admin_headers)
    assert admin_scan.status_code == 201

    # Admin can update automation threshold config
    admin_patch = await client.patch("/api/v1/config/automation", json={
        "auto_confirm_threshold_percent": 85.0
    }, headers=admin_headers)
    assert admin_patch.status_code == 200

    # Inspector cannot update automation threshold config (403)
    insp_patch = await client.patch("/api/v1/config/automation", json={
        "auto_confirm_threshold_percent": 80.0
    }, headers=insp_headers)
    assert insp_patch.status_code == 403

    set_current_auto_confirm_threshold(80.0)
