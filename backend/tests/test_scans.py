import io
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from app.models.audit import AuditLog
from app.models.declaration import Declaration
from app.workers.tasks import run_scan_analysis_pipeline_async


@pytest.mark.asyncio
async def test_scan_lifecycle(client: AsyncClient, test_users, auth_headers, db_session):
    headers = auth_headers("inspector")

    # 1. Create Scan
    create_payload = {
        "source": "physical_store",
        "location_name": "Test Supermarket, Delhi",
        "product_data": {
            "name": "Test Tea 500g",
            "brand": "Test Tea",
            "category": "Beverages",
            "manufacturer_name": "Test Beverages Ltd",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_data = resp.json()["data"]
    scan_id = scan_data["id"]

    # 2. Upload Image
    from tests.conftest import create_clear_test_image_bytes
    img_bytes = create_clear_test_image_bytes()
    files = {"files": ("test_label.jpg", img_bytes, "image/jpeg")}
    upload_resp = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
    assert upload_resp.status_code == 200

    # 3. Trigger AI Analysis
    analyze_resp = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_resp.status_code == 200
    assert analyze_resp.json()["data"]["status"] == "queued"

    # Manually execute background processing pipeline in test with db_session
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 4. Get Scan Detail
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["status"] == "needs_review"
    assert len(detail["declarations"]) > 0

    first_decl = detail["declarations"][0]

    # 5. Inspector Override
    override_payload = {
        "is_compliant": False,
        "reviewer_notes": "Font height measured with digital vernier caliper was 1.2mm, below 3.0mm requirement.",
    }
    override_resp = await client.patch(
        f"/api/v1/scans/{scan_id}/declarations/{first_decl['id']}",
        json=override_payload,
        headers=headers,
    )
    assert override_resp.status_code == 200
    assert override_resp.json()["data"]["reviewer_override"] is True

    # Check Audit Log record was created
    audit_res = await db_session.execute(
        select(AuditLog).where(AuditLog.entity_id == first_decl["id"])
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.action == "DECLARATION_OVERRIDDEN"

    # 6. Close Scan
    close_resp = await client.post(
        f"/api/v1/scans/{scan_id}/close",
        json={"notes": "Inspection completed. Notice issued for font size violation."},
        headers=headers,
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["data"]["status"] == "closed"


@pytest.mark.asyncio
async def test_chips_packet_dynamic_scan_workflow(client: AsyncClient, test_users, auth_headers, db_session):
    headers = auth_headers("inspector")

    # 1. Create Scan with Chips product data
    create_payload = {
        "source": "physical_store",
        "location_name": "Spencer's Retail, Gurugram",
        "product_data": {
            "name": "Lay's Classic Salted Potato Chips 50g",
            "brand": "Lay's",
            "category": "Packaged Snacks & Chips",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # 2. Upload packaging image
    from tests.conftest import create_clear_test_image_bytes
    img_bytes = create_clear_test_image_bytes(width=800, height=1000)
    files = {"files": ("lays_chips_packet.jpg", img_bytes, "image/jpeg")}
    upload_resp = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
    assert upload_resp.status_code == 200
    uploaded_imgs = upload_resp.json()["data"]
    assert len(uploaded_imgs) == 1
    assert uploaded_imgs[0]["width_px"] == 800
    assert uploaded_imgs[0]["height_px"] == 1000

    # 3. Trigger AI Analysis
    analyze_resp = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_resp.status_code == 200

    # Execute background pipeline with db_session
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 4. Retrieve resulting scan
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]

    assert detail["status"] == "needs_review"
    assert detail["product"]["name"] == "Lay's Classic Salted Potato Chips 50g"
    assert detail["product"]["brand"] == "Lay's"
    assert len(detail["images"]) == 1
    assert detail["images"][0]["image_url"].startswith("/api/v1/storage/scans/")

    # 5. Verify declarations match Lay's chips, NOT Aashirvaad Atta / 5 kg / ITC
    decls = detail["declarations"]
    assert len(decls) > 0

    decl_texts = [d["extracted_text"] for d in decls if d["extracted_text"]]
    combined_decl_text = " ".join(decl_texts)

    # Must NOT contain hardcoded Aashirvaad / 5 kg / ITC data
    assert "AASHIRVAAD" not in combined_decl_text.upper()
    assert "5 kg" not in combined_decl_text
    assert "ITC Limited" not in combined_decl_text

    # Must contain chips and PepsiCo declarations
    assert any("chips" in (d.get("extracted_text") or "").lower() for d in decls)
    assert any("50 g" in (d.get("extracted_text") or "") for d in decls)
    assert any("pepsico" in (d.get("extracted_text") or "").lower() for d in decls)

    # Verify bounding boxes exist and have valid coordinates
    for d in decls:
        if d.get("bounding_box") and d.get("is_present"):
            bbox = d["bounding_box"]
            assert bbox["w"] > 0
            assert bbox["h"] > 0

