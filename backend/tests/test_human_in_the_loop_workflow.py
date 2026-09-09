import io
import pytest
from httpx import AsyncClient
from PIL import Image


from tests.conftest import create_clear_test_image_bytes

def create_test_image_bytes() -> bytes:
    return create_clear_test_image_bytes()


@pytest.mark.asyncio
async def test_human_in_the_loop_review_and_override(client: AsyncClient, test_users, auth_headers):
    headers = auth_headers("inspector")

    # 1. Create scan for a packaged commodity
    scan_res = await client.post("/api/v1/scans", json={
        "product_data": {
            "name": "Organic Green Cardamom - Spices",
            "brand": "Nature Fresh",
            "category": "Spices & Condiments",
            "manufacturer_name": "Nature Fresh Agro Ltd",
            "manufacturer_address": "Cochin, Kerala",
            "country_of_origin": "India",
            "barcode": "8901234567890"
        },
        "source": "physical_store",
        "location_name": "Metro Cash & Carry, Bangalore"
    }, headers=headers)
    assert scan_res.status_code == 201
    scan_id = scan_res.json()["data"]["id"]

    # 2. Upload image and analyze
    img_bytes = create_test_image_bytes()
    up_res = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("cardamom_label.jpg", img_bytes, "image/jpeg")},
        data={"image_type": "front"},
        headers=headers
    )
    assert up_res.status_code == 200

    analyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200

    # 3. Fetch scan details and verify declarations
    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    assert len(decls) > 0
    target_decl = decls[0]
    decl_id = target_decl["id"]

    # 4. Review finding: Confirm action
    confirm_res = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={
            "action": "confirm",
            "reviewer_notes": "Declaration confirmed by inspecting officer based on visible text."
        },
        headers=headers
    )
    assert confirm_res.status_code == 200
    c_data = confirm_res.json()["data"]
    assert c_data["human_decision"] == "confirmed"
    assert c_data["reviewer_notes"] == "Declaration confirmed by inspecting officer based on visible text."
    assert c_data["reviewed_by"] is not None

    # 5. Review finding: Override action with custom status
    override_res = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={
            "action": "override",
            "is_compliant": True,
            "severity": "none",
            "reviewer_notes": "Verified manually on package back panel; declaration complies with Rule 6."
        },
        headers=headers
    )
    assert override_res.status_code == 200
    o_data = override_res.json()["data"]
    assert o_data["human_decision"] == "overridden"
    assert o_data["reviewer_override"] is True
    assert o_data["is_compliant"] is True
    assert o_data["reviewer_notes"] == "Verified manually on package back panel; declaration complies with Rule 6."

    # 6. Finalize Inspection
    finalize_res = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={
            "final_decision": "compliant",
            "remarks": "Package fully inspected and verified by Legal Metrology officer Vikram Sharma."
        },
        headers=headers
    )
    assert finalize_res.status_code == 200
    f_data = finalize_res.json()["data"]
    assert f_data["status"] == "finalized"
    meta = f_data["metadata_json"]
    assert meta["final_decision"] == "compliant"
    assert meta["finalized_by"] is not None
    assert "Vikram Sharma" in meta["final_remarks"]

    # 7. Check Audit Trail
    audit_res = await client.get(f"/api/v1/scans/{scan_id}/audit-trail", headers=headers)
    assert audit_res.status_code == 200
    audit_logs = audit_res.json()["data"]
    assert len(audit_logs) >= 3  # SCAN_CREATED, AI_ANALYSIS, CONFIRMED/OVERRIDDEN, FINALIZED
    actions = [a["action"] for a in audit_logs]
    assert "SCAN_FINALIZED" in actions
    assert any("DECLARATION" in a for a in actions)

    # 8. Generate Report and check human-in-the-loop contents
    rep_res = await client.post(f"/api/v1/scans/{scan_id}/report", headers=headers)
    assert rep_res.status_code == 201
    rep_id = rep_res.json()["data"]["id"]
    summary = rep_res.json()["data"]["summary_data"]
    assert summary["final_human_decision"] == "compliant"
    assert "Vikram Sharma" in summary["final_remarks"]
    assert "audit_trail" in summary
    assert len(summary["audit_trail"]) > 0


@pytest.mark.asyncio
async def test_rbac_review_finalize_and_removed_roles_rejection(client: AsyncClient, test_users, auth_headers):
    insp_headers = auth_headers("inspector")
    admin_headers = auth_headers("admin")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    # Create a scan as Inspector first
    scan_res = await client.post("/api/v1/scans", json={
        "product_data": {
            "name": "Roasted Salted Almonds",
            "brand": "Nutty Delight",
            "category": "Dry Fruits",
            "country_of_origin": "India"
        }
    }, headers=insp_headers)
    scan_id = scan_res.json()["data"]["id"]

    img_bytes = create_test_image_bytes()
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files={"files": ("label.jpg", img_bytes, "image/jpeg")},
        headers=insp_headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=insp_headers)
    
    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=insp_headers)
    decls = detail_res.json()["data"]["declarations"]
    decl_id = decls[0]["id"]

    # 1. Inspector: Can review & finalize
    insp_review = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={"action": "confirm", "reviewer_notes": "Reviewed and verified by Inspector Sharma."},
        headers=insp_headers
    )
    assert insp_review.status_code == 200

    insp_final = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={"final_decision": "compliant", "remarks": "Finalized by Inspector Sharma."},
        headers=insp_headers
    )
    assert insp_final.status_code == 200

    # 2. Obsolete Reviewer: Denied access (403)
    rev_create = await client.post("/api/v1/scans", json={"source": "physical_store"}, headers=rev_headers)
    assert rev_create.status_code == 403

    rev_review = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={"action": "confirm", "reviewer_notes": "Attempt by obsolete reviewer"},
        headers=rev_headers
    )
    assert rev_review.status_code == 403

    # 3. Obsolete Viewer: Denied access (403)
    v_view_scan = await client.get(f"/api/v1/scans/{scan_id}", headers=view_headers)
    assert v_view_scan.status_code == 403

    v_review = await client.post(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review",
        json={"action": "confirm", "reviewer_notes": "Attempt by viewer"},
        headers=view_headers
    )
    assert v_review.status_code == 403

    v_finalize = await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={"final_decision": "compliant", "remarks": "Attempt by viewer"},
        headers=view_headers
    )
    assert v_finalize.status_code == 403
