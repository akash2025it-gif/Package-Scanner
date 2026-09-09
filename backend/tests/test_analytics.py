import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_analytics_summary_empty(client: AsyncClient, test_users, auth_headers):
    """Verify summary metrics when database has users but no scans."""
    headers = auth_headers("inspector")
    resp = await client.get("/api/v1/analytics/summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_inspections"] == 0
    assert data["compliant_count"] == 0
    assert data["non_compliant_count"] == 0
    assert data["needs_review_count"] == 0
    assert data["compliance_rate"] is None
    assert data["violation_rate"] is None
    assert len(data["dynamic_insights"]) > 0


@pytest.mark.asyncio
async def test_enforcement_kpis_and_finalized_compliance_calculation(client: AsyncClient, test_users, auth_headers):
    """
    Create scans, analyze, finalize them, and verify that compliance_rate and violation_rate
    are computed strictly over finalized determinations, excluding unfinalized scans.
    """
    insp_headers = auth_headers("inspector")

    # Scan 1: Compliant & Finalized
    s1 = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Delhi Retail Store",
        "product_data": {"name": "Wheat Flour 5kg", "brand": "BrandA", "category": "Food Grains"}
    }, headers=insp_headers)
    s1_id = s1.json()["data"]["id"]
    await client.post(f"/api/v1/scans/{s1_id}/analyze", headers=insp_headers)
    await client.post(f"/api/v1/scans/{s1_id}/finalize", json={
        "final_decision": "compliant",
        "remarks": "Verified compliant by inspecting officer."
    }, headers=insp_headers)

    # Scan 2: Non-Compliant & Finalized
    s2 = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Delhi Retail Store",
        "product_data": {"name": "Shampoo 200ml", "brand": "BrandB", "category": "Cosmetics"}
    }, headers=insp_headers)
    s2_id = s2.json()["data"]["id"]
    await client.post(f"/api/v1/scans/{s2_id}/analyze", headers=insp_headers)
    await client.post(f"/api/v1/scans/{s2_id}/finalize", json={
        "final_decision": "non_compliant",
        "remarks": "Missing statutory mandatory MRP inclusive tax phrase."
    }, headers=insp_headers)

    # Scan 3: Unfinalized (Needs Review)
    s3 = await client.post("/api/v1/scans", json={
        "source": "ecommerce",
        "location_name": "Online Surveillance",
        "product_data": {"name": "Olive Oil 1L", "brand": "BrandC", "category": "Edible Oils"}
    }, headers=insp_headers)
    s3_id = s3.json()["data"]["id"]
    await client.post(f"/api/v1/scans/{s3_id}/analyze", headers=insp_headers)

    # Check Summary
    resp = await client.get("/api/v1/analytics/summary", headers=insp_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["total_inspections"] == 3
    assert data["compliant_count"] == 1
    assert data["non_compliant_count"] == 1
    assert data["needs_review_count"] == 1
    assert data["finalized_count"] == 2
    assert data["compliance_rate"] == 50.0
    assert data["violation_rate"] == 50.0
    assert data["compliance_distribution"]["compliant"] == 1
    assert data["compliance_distribution"]["non_compliant"] == 1
    assert data["compliance_distribution"]["needs_review"] == 1
    assert len(data["dynamic_insights"]) > 0


@pytest.mark.asyncio
async def test_analytics_filtering_by_days_and_category(client: AsyncClient, test_users, auth_headers):
    """Verify date filtering and category slice queries."""
    headers = auth_headers("inspector")

    # Seed 1 inspection in category Beverages
    s = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Store Alpha",
        "product_data": {"name": "Green Tea 250g", "brand": "TeaBrand", "category": "Beverages"}
    }, headers=headers)
    s_id = s.json()["data"]["id"]
    await client.post(f"/api/v1/scans/{s_id}/analyze", headers=headers)

    # Trends endpoint
    resp = await client.get("/api/v1/analytics/inspection-trends?days=7", headers=headers)
    assert resp.status_code == 200
    trends = resp.json()["data"]
    assert len(trends) == 7
    total_in_trend = sum(t["total_scans"] for t in trends)
    assert total_in_trend >= 1

    # Filter summary by category
    resp_cat = await client.get("/api/v1/analytics/summary?category=Beverages", headers=headers)
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()["data"]
    assert cat_data["total_inspections"] == 1

    # Filter summary by non-existent category
    resp_none = await client.get("/api/v1/analytics/summary?category=NonExistentCat", headers=headers)
    assert resp_none.status_code == 200
    none_data = resp_none.json()["data"]
    assert none_data["total_inspections"] == 0


@pytest.mark.asyncio
async def test_product_risk_and_violations_ranking(client: AsyncClient, test_users, auth_headers):
    """Verify product category risk tiers and violation rankings."""
    headers = auth_headers("inspector")

    # Create and finalize a non-compliant scan
    s = await client.post("/api/v1/scans", json={
        "source": "physical_store",
        "location_name": "Mumbai Store",
        "product_data": {"name": "Packaged Snacks 50g", "brand": "SnackCo", "category": "Snacks"}
    }, headers=headers)
    s_id = s.json()["data"]["id"]
    await client.post(f"/api/v1/scans/{s_id}/analyze", headers=headers)
    await client.post(f"/api/v1/scans/{s_id}/finalize", json={
        "final_decision": "non_compliant",
        "remarks": "Missing manufacturer address."
    }, headers=headers)

    # Product risk endpoint
    p_resp = await client.get("/api/v1/analytics/product-risk", headers=headers)
    assert p_resp.status_code == 200
    risk_items = p_resp.json()["data"]
    assert len(risk_items) >= 1
    snack_cat = next((c for c in risk_items if c["category"] == "Snacks"), None)
    assert snack_cat is not None
    assert snack_cat["non_compliant_count"] >= 1
    assert snack_cat["risk_level"] in ["HIGH", "MEDIUM", "LOW"]

    # Violations ranking endpoint
    v_resp = await client.get("/api/v1/analytics/violations", headers=headers)
    assert v_resp.status_code == 200
    assert isinstance(v_resp.json()["data"], list)


@pytest.mark.asyncio
async def test_attention_inspections_queue(client: AsyncClient, test_users, auth_headers):
    """Verify attention queue returns unfinalized/non-compliant scans."""
    headers = auth_headers("inspector")

    # Inspector can read attention queue
    att_resp = await client.get("/api/v1/analytics/attention", headers=headers)
    assert att_resp.status_code == 200
    items = att_resp.json()["data"]
    assert isinstance(items, list)


@pytest.mark.asyncio
async def test_officer_activity_and_regional_overview(client: AsyncClient, test_users, auth_headers):
    """Verify officer activity and regional heatmap endpoints."""
    headers = auth_headers("admin")

    # Officer Activity
    off_resp = await client.get("/api/v1/analytics/officer-activity", headers=headers)
    assert off_resp.status_code == 200
    officers = off_resp.json()["data"]
    assert isinstance(officers, list)
    assert len(officers) > 0

    # Regional Heatmap
    reg_resp = await client.get("/api/v1/analytics/region-heatmap", headers=headers)
    assert reg_resp.status_code == 200
    regions = reg_resp.json()["data"]
    assert isinstance(regions, list)
    assert len(regions) > 0


@pytest.mark.asyncio
async def test_all_roles_can_access_analytics_endpoints(client: AsyncClient, test_users, auth_headers):
    """Ensure RBAC permissions: Active roles (Admin, Inspector) can access; obsolete roles are rejected."""
    endpoints = [
        "/api/v1/analytics/summary",
        "/api/v1/analytics/inspection-trends",
        "/api/v1/analytics/violations",
        "/api/v1/analytics/product-risk",
        "/api/v1/analytics/attention",
        "/api/v1/analytics/officer-activity",
        "/api/v1/analytics/region-heatmap",
        "/api/v1/analytics/officer-performance",
    ]

    # Active roles: allowed
    for role in ["admin", "inspector"]:
        headers = auth_headers(role)
        for ep in endpoints:
            r = await client.get(ep, headers=headers)
            assert r.status_code == 200, f"Active role {role} failed on {ep} with status {r.status_code}"

    # Obsolete roles: rejected (403)
    for role in ["reviewer", "viewer"]:
        headers = auth_headers(role)
        for ep in endpoints:
            r = await client.get(ep, headers=headers)
            assert r.status_code == 403, f"Removed role {role} should be rejected on {ep}"
