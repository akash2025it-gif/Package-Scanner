import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.workers.tasks import run_scan_analysis_pipeline_async


@pytest.mark.asyncio
async def test_report_generation_and_downloads(client: AsyncClient, test_users, auth_headers, db_session: AsyncSession):
    headers = auth_headers("inspector")

    # 1. Create and populate a scan
    create_resp = await client.post(
        "/api/v1/scans",
        json={"location_name": "Delhi Retail Mart", "product_data": {"name": "Demo Rice 10kg", "brand": "Demo", "category": "Grains"}},
        headers=headers,
    )
    scan_id = create_resp.json()["data"]["id"]
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 2. Generate Report
    rep_resp = await client.post(
        f"/api/v1/scans/{scan_id}/report",
        json={"notes": "Routine market audit."},
        headers=headers,
    )
    assert rep_resp.status_code == 201
    report = rep_resp.json()["data"]
    report_id = report["id"]

    # 3. Get Report metadata
    meta_resp = await client.get(f"/api/v1/reports/{report_id}", headers=headers)
    assert meta_resp.status_code == 200

    # 4. Stream PDF
    pdf_resp = await client.get(f"/api/v1/reports/{report_id}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert len(pdf_resp.content) > 100

    # 5. Stream DOCX
    docx_resp = await client.get(f"/api/v1/reports/{report_id}/docx", headers=headers)
    assert docx_resp.status_code == 200
    assert len(docx_resp.content) > 100
