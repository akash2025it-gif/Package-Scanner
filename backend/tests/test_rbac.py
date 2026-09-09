import pytest
from httpx import AsyncClient
from tests.conftest import create_clear_test_image_bytes


@pytest.mark.asyncio
async def test_users_api_rbac_strict_admin_only(client: AsyncClient, test_users, auth_headers):
    """Verify that only Admin can access /users APIs and non-admins get 403."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    # Admin: allowed
    res = await client.get("/api/v1/users", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Inspector: forbidden
    res = await client.get("/api/v1/users", headers=insp_headers)
    assert res.status_code == 403

    # Obsolete Reviewer: forbidden
    res = await client.get("/api/v1/users", headers=rev_headers)
    assert res.status_code == 403

    # Obsolete Viewer: forbidden
    res = await client.get("/api/v1/users", headers=view_headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_scan_creation_rbac(client: AsyncClient, test_users, auth_headers):
    """Verify that Inspector and Admin can create scans; obsolete Reviewer and Viewer get 403."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    payload = {
        "source": "physical_store",
        "location_name": "Test Supermarket",
        "product_data": {
            "name": "Test Snack 100g",
            "brand": "TestBrand",
            "category": "Snacks"
        }
    }

    # Admin: allowed
    res_admin = await client.post("/api/v1/scans", json=payload, headers=admin_headers)
    assert res_admin.status_code == 201
    assert res_admin.json()["success"] is True

    # Inspector: allowed
    res_insp = await client.post("/api/v1/scans", json=payload, headers=insp_headers)
    assert res_insp.status_code == 201
    assert res_insp.json()["success"] is True

    # Obsolete Reviewer: forbidden
    res_rev = await client.post("/api/v1/scans", json=payload, headers=rev_headers)
    assert res_rev.status_code == 403

    # Obsolete Viewer: forbidden
    res_view = await client.post("/api/v1/scans", json=payload, headers=view_headers)
    assert res_view.status_code == 403


@pytest.mark.asyncio
async def test_scan_upload_and_analyze_rbac(client: AsyncClient, test_users, auth_headers):
    """Verify that Inspector and Admin can upload images and trigger analysis; obsolete roles get 403."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    # Create a base scan as Inspector
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Store",
        "product_data": {"name": "Test Biscuit", "brand": "BrandX", "category": "Food"}
    }, headers=insp_headers)
    scan_id = scan_res.json()["data"]["id"]

    from tests.conftest import create_clear_test_image_bytes
    fake_img = create_clear_test_image_bytes()

    # Obsolete Reviewer upload: 403
    res_rev_up = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=[("files", ("test.jpg", fake_img, "image/jpeg"))],
        headers=rev_headers
    )
    assert res_rev_up.status_code == 403

    # Obsolete Viewer upload: 403
    res_view_up = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=[("files", ("test.jpg", fake_img, "image/jpeg"))],
        headers=view_headers
    )
    assert res_view_up.status_code == 403

    # Inspector upload: 200
    res_insp_up = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=[("files", ("test.jpg", fake_img, "image/jpeg"))],
        headers=insp_headers
    )
    assert res_insp_up.status_code == 200

    # Obsolete Reviewer trigger analyze: 403
    res_rev_an = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=rev_headers)
    assert res_rev_an.status_code == 403

    # Obsolete Viewer trigger analyze: 403
    res_view_an = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=view_headers)
    assert res_view_an.status_code == 403

    # Inspector trigger analyze: 200
    res_insp_an = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=insp_headers)
    assert res_insp_an.status_code == 200


@pytest.mark.asyncio
async def test_review_override_and_close_rbac(client: AsyncClient, test_users, auth_headers):
    """Verify Inspector and Admin can perform human verification (override/conclude), while removed roles get 403."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    # Create and analyze scan
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Market",
        "product_data": {"name": "Test Noodle", "brand": "BrandY", "category": "Food"}
    }, headers=insp_headers)
    scan_id = scan_res.json()["data"]["id"]
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=[("files", ("test.jpg", create_clear_test_image_bytes(), "image/jpeg"))],
        headers=insp_headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=insp_headers)

    # Get scan to get declaration ID
    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=insp_headers)
    assert detail_res.status_code == 200
    decls = detail_res.json()["data"]["declarations"]
    decl_id = decls[0]["id"]

    # Obsolete Viewer override: 403
    res_view_ov = await client.patch(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}",
        json={"is_compliant": True, "reviewer_notes": "Viewer attempt"},
        headers=view_headers
    )
    assert res_view_ov.status_code == 403

    # Obsolete Reviewer override: 403
    res_rev_ov = await client.patch(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}",
        json={"is_compliant": True, "reviewer_notes": "Obsolete reviewer attempt"},
        headers=rev_headers
    )
    assert res_rev_ov.status_code == 403

    # Inspector override: 200
    res_insp_ov = await client.patch(
        f"/api/v1/scans/{scan_id}/declarations/{decl_id}",
        json={"is_compliant": True, "reviewer_notes": "Verified and overridden by Inspector Sharma."},
        headers=insp_headers
    )
    assert res_insp_ov.status_code == 200
    assert res_insp_ov.json()["data"]["reviewer_override"] is True

    # Obsolete Viewer close: 403
    res_view_close = await client.post(
        f"/api/v1/scans/{scan_id}/close",
        json={"notes": "Viewer close attempt"},
        headers=view_headers
    )
    assert res_view_close.status_code == 403

    # Inspector close: 200
    res_insp_close = await client.post(
        f"/api/v1/scans/{scan_id}/close",
        json={"notes": "Concluded by Inspector Sharma."},
        headers=insp_headers
    )
    assert res_insp_close.status_code == 200
    assert res_insp_close.json()["data"]["status"] == "closed"


@pytest.mark.asyncio
async def test_report_generation_rbac(client: AsyncClient, test_users, auth_headers):
    """Verify Inspector and Admin can generate and view reports; obsolete roles get 403."""
    admin_headers = auth_headers("admin")
    insp_headers = auth_headers("inspector")
    rev_headers = auth_headers("reviewer")
    view_headers = auth_headers("viewer")

    # Create and analyze scan
    scan_res = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Test Market",
        "product_data": {"name": "Report Test Product", "brand": "BrandZ", "category": "Food"}
    }, headers=insp_headers)
    scan_id = scan_res.json()["data"]["id"]
    await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=[("files", ("test.jpg", create_clear_test_image_bytes(), "image/jpeg"))],
        headers=insp_headers
    )
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=insp_headers)

    # Obsolete Viewer generate report: 403
    res_view_rep = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        json={"notes": "Viewer attempt"},
        headers=view_headers
    )
    assert res_view_rep.status_code == 403

    # Obsolete Reviewer generate report: 403
    res_rev_rep = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        json={"notes": "Reviewer report."},
        headers=rev_headers
    )
    assert res_rev_rep.status_code == 403

    # Inspector generate report: 201
    res_insp_rep = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        json={"notes": "Inspector statutory report."},
        headers=insp_headers
    )
    assert res_insp_rep.status_code == 201
    report_id = res_insp_rep.json()["data"]["id"]

    # Inspector read report: 200
    res_insp_get = await client.get(f"/api/v1/reports/{report_id}", headers=insp_headers)
    assert res_insp_get.status_code == 200

    # Inspector download PDF report: 200
    res_insp_pdf = await client.get(f"/api/v1/reports/{report_id}/pdf", headers=insp_headers)
    assert res_insp_pdf.status_code == 200
    assert res_insp_pdf.headers["content-type"] == "application/pdf"

    # Admin read report: 200
    res_admin_get = await client.get(f"/api/v1/reports/{report_id}", headers=admin_headers)
    assert res_admin_get.status_code == 200


@pytest.mark.asyncio
async def test_read_endpoints_accessible_only_to_active_roles(client: AsyncClient, test_users, auth_headers):
    """Verify that Dashboard, Scans, Products, and Analytics read endpoints are accessible only to active roles (Inspector & Admin)."""
    # Active roles: allowed (200)
    for role in ["admin", "inspector"]:
        headers = auth_headers(role)

        # Scans list
        res = await client.get("/api/v1/scans", headers=headers)
        assert res.status_code == 200, f"Role {role} failed /scans"

        # Products list
        res = await client.get("/api/v1/products", headers=headers)
        assert res.status_code == 200, f"Role {role} failed /products"

        # Analytics summary
        res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert res.status_code == 200, f"Role {role} failed /analytics/summary"

        # Analytics heatmap
        res = await client.get("/api/v1/analytics/region-heatmap", headers=headers)
        assert res.status_code == 200, f"Role {role} failed /analytics/region-heatmap"

        # Analytics officer performance
        res = await client.get("/api/v1/analytics/officer-performance", headers=headers)
        assert res.status_code == 200, f"Role {role} failed /analytics/officer-performance"

    # Removed/obsolete roles: rejected (403)
    for role in ["reviewer", "viewer"]:
        headers = auth_headers(role)
        res = await client.get("/api/v1/scans", headers=headers)
        assert res.status_code == 403, f"Removed role {role} should be forbidden on /scans"

        res = await client.get("/api/v1/products", headers=headers)
        assert res.status_code == 403, f"Removed role {role} should be forbidden on /products"

        res = await client.get("/api/v1/analytics/summary", headers=headers)
        assert res.status_code == 403, f"Removed role {role} should be forbidden on /analytics/summary"
