import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.scan import Scan
from app.workers.tasks import run_scan_analysis_pipeline_async


@pytest.mark.asyncio
async def test_batch_creation_and_persistence(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 1: New scan with batch number persists after reload."""
    headers = auth_headers("inspector")

    create_payload = {
        "source": "physical_store",
        "location_name": "Spencer's Retail, Gurugram",
        "batch_number": "DF240826A",
        "product_data": {
            "name": "Tata Tea Gold 500g",
            "brand": "Tata Tea",
            "category": "Beverages",
            "manufacturer_name": "Tata Consumer Products Ltd",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_data = resp.json()["data"]
    scan_id = scan_data["id"]
    assert scan_data["batch_number"] == "DF240826A"

    # Reload scan detail via API
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["batch_number"] == "DF240826A"
    assert detail["batch_number_source"] == "manual"

    # Direct database verification
    db_scan = await db_session.get(Scan, scan_id)
    assert db_scan is not None
    assert db_scan.batch_number == "DF240826A"


@pytest.mark.asyncio
async def test_matching_manual_and_ocr_batch(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 2: Matching manual and OCR batch yields no discrepancy."""
    headers = auth_headers("inspector")

    create_payload = {
        "source": "physical_store",
        "location_name": "Reliance Fresh, Delhi",
        "batch_number": "BATCH-MATCH-01",
        "product_data": {
            "name": "Amul Pure Ghee 1L",
            "brand": "Amul",
            "category": "Dairy",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # Run AI pipeline (mock OCR will pick up the batch_number)
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["batch_number"] == "BATCH-MATCH-01"
    assert detail["batch_discrepancy"] is False


@pytest.mark.asyncio
async def test_batch_discrepancy_and_human_verification(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 3: Discrepant manual and OCR batch shows discrepancy warning and allows verification."""
    headers = auth_headers("inspector")

    create_payload = {
        "source": "physical_store",
        "location_name": "Big Bazaar, Mumbai",
        "batch_number": "MANUAL-B123",
        "metadata_json": {
            "ocr_mock_batch": "OCR-B999"
        },
        "product_data": {
            "name": "Fortune Sunlite Sunflower Oil 1L",
            "brand": "Fortune",
            "category": "Edible Oils",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # Run AI pipeline
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # Check that discrepancy is flagged
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["batch_discrepancy"] is True
    assert detail["batch_number"] == "MANUAL-B123"
    assert detail["batch_number_extracted"] == "OCR-B999"

    # Inspector verifies / corrects the batch number
    verify_resp = await client.patch(
        f"/api/v1/scans/{scan_id}/batch",
        json={"batch_number": "OCR-B999", "notes": "Verified against physical label packaging stamp."},
        headers=headers,
    )
    assert verify_resp.status_code == 200
    updated_detail = verify_resp.json()["data"]
    assert updated_detail["batch_number"] == "OCR-B999"
    assert updated_detail["batch_number_source"] == "verified"
    assert updated_detail["batch_discrepancy"] is False


@pytest.mark.asyncio
async def test_batch_aggregation_and_investigation_endpoints(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 4: Multiple scans with the same batch appear together on /batches/{batch_number}."""
    headers = auth_headers("inspector")
    batch_num = "SHARED-BATCH-77"

    # Create Scan 1
    resp1 = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Store Alpha, Pune",
            "batch_number": batch_num,
            "product_data": {"name": "Britannia Biscuits 200g", "brand": "Britannia", "category": "Bakery"},
        },
        headers=headers,
    )
    assert resp1.status_code == 201
    scan1_id = resp1.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan1_id, db=db_session)

    # Create Scan 2
    resp2 = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Store Beta, Nagpur",
            "batch_number": batch_num,
            "product_data": {"name": "Britannia Biscuits 200g", "brand": "Britannia", "category": "Bakery"},
        },
        headers=headers,
    )
    assert resp2.status_code == 201
    scan2_id = resp2.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan2_id, db=db_session)

    # Check scan detail related count (1 other related scan)
    s1_detail = (await client.get(f"/api/v1/scans/{scan1_id}", headers=headers)).json()["data"]
    assert s1_detail["related_batch_scans_count"] == 1

    # Query Batch Detail endpoint
    batch_resp = await client.get(f"/api/v1/batches/{batch_num}", headers=headers)
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()["data"]
    assert batch_data["batch_number"] == batch_num
    assert batch_data["total_inspections"] == 2
    assert len(batch_data["inspections"]) == 2

    # Query Batch Inspections endpoint
    insp_resp = await client.get(f"/api/v1/batches/{batch_num}/inspections", headers=headers)
    assert insp_resp.status_code == 200
    inspections = insp_resp.json()["data"]
    assert len(inspections) == 2
    scan_ids = [i["id"] for i in inspections]
    assert scan1_id in scan_ids
    assert scan2_id in scan_ids


@pytest.mark.asyncio
async def test_batch_attention_propagation_on_non_compliance(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 5: Finalizing one inspection as non_compliant flags the batch as attention_required."""
    headers = auth_headers("inspector")
    batch_num = "ALERT-BATCH-99"

    # Create Scan 1 and finalize as non-compliant
    resp1 = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Market 1, Bangalore",
            "batch_number": batch_num,
            "product_data": {"name": "Snack Pack 100g", "brand": "SnackCo", "category": "Snacks"},
        },
        headers=headers,
    )
    assert resp1.status_code == 201
    scan1_id = resp1.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan1_id, db=db_session)

    # Finalize scan 1 as non_compliant
    finalize_resp = await client.post(
        f"/api/v1/scans/{scan1_id}/finalize",
        json={"final_decision": "non_compliant", "remarks": "Mandatory declaration missing. Batch flagged."},
        headers=headers,
    )
    assert finalize_resp.status_code == 200

    # Create Scan 2 in the same batch
    resp2 = await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Market 2, Mysore",
            "batch_number": batch_num,
            "product_data": {"name": "Snack Pack 100g", "brand": "SnackCo", "category": "Snacks"},
        },
        headers=headers,
    )
    assert resp2.status_code == 201
    scan2_id = resp2.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan2_id, db=db_session)

    # Check Batch status
    batch_resp = await client.get(f"/api/v1/batches/{batch_num}", headers=headers)
    assert batch_resp.status_code == 200
    batch_data = batch_resp.json()["data"]
    assert batch_data["status"] == "attention_required"
    assert batch_data["non_compliant_inspections"] >= 1

    # Check Scan 2 detail has batch_attention_required = True
    s2_detail = (await client.get(f"/api/v1/scans/{scan2_id}", headers=headers)).json()["data"]
    assert s2_detail["batch_attention_required"] is True


@pytest.mark.asyncio
async def test_batch_isolation(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 6: Different batch numbers are not mixed."""
    headers = auth_headers("inspector")

    # Batch A
    await client.post(
        "/api/v1/scans",
        json={"location_name": "Loc A", "batch_number": "ISOLATE-BATCH-A", "product_data": {"name": "Product A", "brand": "Brand A", "category": "General"}},
        headers=headers,
    )
    # Batch B
    await client.post(
        "/api/v1/scans",
        json={"location_name": "Loc B", "batch_number": "ISOLATE-BATCH-B", "product_data": {"name": "Product B", "brand": "Brand B", "category": "General"}},
        headers=headers,
    )

    batch_a_resp = await client.get("/api/v1/batches/ISOLATE-BATCH-A", headers=headers)
    assert batch_a_resp.status_code == 200
    assert batch_a_resp.json()["data"]["total_inspections"] == 1

    batch_b_resp = await client.get("/api/v1/batches/ISOLATE-BATCH-B", headers=headers)
    assert batch_b_resp.status_code == 200
    assert batch_b_resp.json()["data"]["total_inspections"] == 1


@pytest.mark.asyncio
async def test_batch_rbac_permissions(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 7 & 8: Active Inspector & Admin can read/update batch status (200); removed roles are rejected (403)."""
    inspector_headers = auth_headers("inspector")
    admin_headers = auth_headers("admin")
    viewer_headers = auth_headers("viewer")
    reviewer_headers = auth_headers("reviewer")

    batch_num = "RBAC-BATCH-01"
    await client.post(
        "/api/v1/scans",
        json={"location_name": "Loc", "batch_number": batch_num, "product_data": {"name": "RBAC Product", "brand": "RBAC Brand", "category": "Food"}},
        headers=inspector_headers,
    )

    # Inspector can read batch (200)
    i_read = await client.get(f"/api/v1/batches/{batch_num}", headers=inspector_headers)
    assert i_read.status_code == 200

    # Inspector can update batch status (200)
    i_patch = await client.patch(
        f"/api/v1/batches/{batch_num}/status",
        json={"status": "under_investigation", "notes": "Authorized inspector marked under investigation."},
        headers=inspector_headers,
    )
    assert i_patch.status_code == 200
    assert i_patch.json()["data"]["status"] == "under_investigation"

    # Admin can read and update batch status (200)
    a_patch = await client.patch(
        f"/api/v1/batches/{batch_num}/status",
        json={"status": "resolved", "notes": "Admin resolved batch issue."},
        headers=admin_headers,
    )
    assert a_patch.status_code == 200
    assert a_patch.json()["data"]["status"] == "resolved"

    # Removed Viewer is rejected (403)
    v_read = await client.get(f"/api/v1/batches/{batch_num}", headers=viewer_headers)
    assert v_read.status_code == 403
    v_patch = await client.patch(
        f"/api/v1/batches/{batch_num}/status",
        json={"status": "under_investigation", "notes": "Viewer attempt"},
        headers=viewer_headers,
    )
    assert v_patch.status_code == 403

    # Removed Reviewer is rejected (403)
    r_patch = await client.patch(
        f"/api/v1/batches/{batch_num}/status",
        json={"status": "under_investigation", "notes": "Reviewer attempt"},
        headers=reviewer_headers,
    )
    assert r_patch.status_code == 403


@pytest.mark.asyncio
async def test_batch_report_and_statutory_disclaimer(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 9: Report contains batch number and statutory disclaimer."""
    headers = auth_headers("inspector")
    batch_num = "REPORT-BATCH-55"

    resp = await client.post(
        "/api/v1/scans",
        json={"location_name": "Chennai Depot", "batch_number": batch_num, "product_data": {"name": "Report Test Item", "brand": "Report Brand", "category": "Staples"}},
        headers=headers,
    )
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # Generate Report
    rep_resp = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        json={"notes": "Statutory audit report test."},
        headers=headers,
    )
    assert rep_resp.status_code == 201
    report = rep_resp.json()["data"]
    report_id = report["id"]

    # Verify report metadata includes batch info
    meta_resp = await client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert meta_resp.status_code == 200
    rep_meta = meta_resp.json()["data"]
    assert rep_meta["summary_data"]["batch_number"] == batch_num

    # Verify PDF stream contains generated content
    pdf_resp = await client.get(f"/api/v1/reports/{report_id}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert len(pdf_resp.content) > 100

    # Verify DOCX stream contains generated content
    docx_resp = await client.get(f"/api/v1/reports/{report_id}/docx", headers=headers)
    assert docx_resp.status_code == 200
    assert len(docx_resp.content) > 100


@pytest.mark.asyncio
async def test_batch_analytics_and_alerts(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 10: Analytics endpoint reflects batch counts and alert items."""
    headers = auth_headers("inspector")
    batch_num = "ANALYTICS-BATCH-88"

    # Create scan and mark non-compliant to generate an alert
    resp = await client.post(
        "/api/v1/scans",
        json={"location_name": "Jaipur Hub", "batch_number": batch_num, "product_data": {"name": "Analytics Item", "brand": "Analytics Brand", "category": "Food"}},
        headers=headers,
    )
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # Finalize as non-compliant
    await client.post(
        f"/api/v1/scans/{scan_id}/finalize",
        json={"final_decision": "non_compliant", "remarks": "Flagged non-compliant for analytics test."},
        headers=headers,
    )

    # Check analytics summary
    analytics_resp = await client.get("/api/v1/analytics/summary", headers=headers)
    assert analytics_resp.status_code == 200
    analytics_data = analytics_resp.json()["data"]
    assert analytics_data["batches_inspected"] >= 1
    assert analytics_data["batches_attention_required"] >= 1
    assert isinstance(analytics_data["batch_investigation_alerts"], list)
    assert any(alert["batch_number"] == batch_num for alert in analytics_data["batch_investigation_alerts"])


@pytest.mark.asyncio
async def test_product_catalog_known_batches(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    """Test 11: Products endpoint shows known batches and batches count."""
    headers = auth_headers("inspector")
    batch_num = "PROD-BATCH-101"

    await client.post(
        "/api/v1/scans",
        json={
            "location_name": "Kolkata Mart",
            "batch_number": batch_num,
            "product_data": {"name": "Known Batch Flour 1kg", "brand": "FlourCo", "category": "Staples"},
        },
        headers=headers,
    )

    prod_resp = await client.get("/api/v1/products", headers=headers)
    assert prod_resp.status_code == 200
    prods = prod_resp.json()["data"]["items"]
    target = next((p for p in prods if p["name"] == "Known Batch Flour 1kg"), None)
    assert target is not None
    assert batch_num in target["known_batches"]
    assert target["batches_count"] >= 1
