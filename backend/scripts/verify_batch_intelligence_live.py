import asyncio
import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import User
from app.workers.tasks import run_scan_analysis_pipeline_async


async def verify_batch_intelligence_workflow():
    print("=" * 60)
    print("PACKSURE AI - BATCH INTELLIGENCE E2E VERIFICATION")
    print("=" * 60)

    # Initialize DB schema and run non-destructive column migrations
    from app.core.database import init_db
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with AsyncSessionLocal() as db:
            # Seed test inspector and reviewer
            inspector = await db.get(User, "live-insp-001")
            if not inspector:
                inspector = User(
                    id="live-insp-001",
                    name="Inspector R. K. Verma",
                    email="rkv.inspector@packcheck.gov.in",
                    password_hash=hash_password("insp123"),
                    role="inspector",
                    region="Delhi NCR",
                    is_active=True,
                )
                db.add(inspector)

            reviewer = await db.get(User, "live-rev-001")
            if not reviewer:
                reviewer = User(
                    id="live-rev-001",
                    name="Legal Metrology Officer S. Nair",
                    email="nair.reviewer@packcheck.gov.in",
                    password_hash=hash_password("rev123"),
                    role="reviewer",
                    region="Maharashtra",
                    is_active=True,
                )
                db.add(reviewer)

            await db.commit()

        insp_token = create_access_token(subject="live-insp-001", role="inspector")
        rev_token = create_access_token(subject="live-rev-001", role="reviewer")
        insp_headers = {"Authorization": f"Bearer {insp_token}"}
        rev_headers = {"Authorization": f"Bearer {rev_token}"}

        test_batch = "DF240826A"

        # 1. Create Scan 1 with Batch Number
        print(f"\n[1] Creating Inspection Scan 1 with Batch: {test_batch}")
        resp1 = await client.post(
            "/api/v1/scans",
            json={
                "source": "physical_store",
                "location_name": "Spencer's Retail, Gurugram",
                "batch_number": test_batch,
                "product_data": {
                    "name": "Tata Tea Gold 500g",
                    "brand": "Tata Tea",
                    "category": "Beverages",
                    "manufacturer_name": "Tata Consumer Products Ltd",
                },
            },
            headers=insp_headers,
        )
        assert resp1.status_code == 201, f"Failed: {resp1.text}"
        scan1 = resp1.json()["data"]
        scan1_id = scan1["id"]
        assert scan1["batch_number"] == test_batch
        print(f"    * Scan 1 initialized: ID={scan1_id}, Batch={scan1['batch_number']}, Source={scan1['batch_number_source']}")

        # 2. Run AI Analysis
        print("\n[2] Executing AI Analysis Pipeline for Scan 1")
        async with AsyncSessionLocal() as db:
            await run_scan_analysis_pipeline_async(scan1_id, db=db)

        detail1 = (await client.get(f"/api/v1/scans/{scan1_id}", headers=insp_headers)).json()["data"]
        assert detail1["batch_discrepancy"] is False
        print(f"    * AI Analysis complete: Status={detail1['status']}, Extracted Batch={detail1['batch_number_extracted']}, Discrepancy={detail1['batch_discrepancy']}")

        # 3. Create Scan 2 with Discrepant Batch
        print("\n[3] Creating Inspection Scan 2 with Discrepant Batch")
        resp2 = await client.post(
            "/api/v1/scans",
            json={
                "source": "physical_store",
                "location_name": "Reliance Fresh, Noida",
                "batch_number": "MANUAL-TYPO-99",
                "metadata_json": {"ocr_mock_batch": test_batch},
                "product_data": {
                    "name": "Tata Tea Gold 500g",
                    "brand": "Tata Tea",
                    "category": "Beverages",
                },
            },
            headers=insp_headers,
        )
        assert resp2.status_code == 201
        scan2_id = resp2.json()["data"]["id"]

        async with AsyncSessionLocal() as db:
            await run_scan_analysis_pipeline_async(scan2_id, db=db)

        detail2 = (await client.get(f"/api/v1/scans/{scan2_id}", headers=insp_headers)).json()["data"]
        assert detail2["batch_discrepancy"] is True
        print(f"    * Discrepancy detected: Manual='{detail2['batch_number']}' vs OCR='{detail2['batch_number_extracted']}'")

        # 4. Human Verification / Discrepancy Resolution
        print("\n[4] Resolving Discrepancy via Inspector Verification Endpoint")
        verify_resp = await client.patch(
            f"/api/v1/scans/{scan2_id}/batch",
            json={"batch_number": test_batch, "notes": "Verified against physical pouch laser etching."},
            headers=insp_headers,
        )
        assert verify_resp.status_code == 200
        resolved_detail = verify_resp.json()["data"]
        assert resolved_detail["batch_number"] == test_batch
        assert resolved_detail["batch_number_source"] == "verified"
        assert resolved_detail["batch_discrepancy"] is False
        print(f"    * Discrepancy resolved: Verified Batch='{resolved_detail['batch_number']}', Source='{resolved_detail['batch_number_source']}', Discrepancy={resolved_detail['batch_discrepancy']}")

        # 5. Batch Investigation Query
        print(f"\n[5] Querying Batch Intelligence Endpoint for '{test_batch}'")
        batch_resp = await client.get(f"/api/v1/batches/{test_batch}", headers=insp_headers)
        assert batch_resp.status_code == 200
        batch_data = batch_resp.json()["data"]
        print(f"    * Batch Overview: Batch={batch_data['batch_number']}, Total Scans={batch_data['total_inspections']}, Status={batch_data['status']}")
        assert batch_data["total_inspections"] == 2

        # 6. Flag Violation & Propagate Batch Attention
        print("\n[6] Finalizing Scan 1 as Non-Compliant and Propagating Batch Attention")
        finalize_resp = await client.post(
            f"/api/v1/scans/{scan1_id}/finalize",
            json={"final_decision": "non_compliant", "remarks": "Non-compliant font size and missing consumer care details."},
            headers=insp_headers,
        )
        assert finalize_resp.status_code == 200

        batch_after = (await client.get(f"/api/v1/batches/{test_batch}", headers=insp_headers)).json()["data"]
        assert batch_after["status"] == "attention_required"
        print(f"    * Batch Status Updated: {batch_after['status']} (Non-compliant count: {batch_after['non_compliant_inspections']})")

        # 7. Generate Statutory Report with Batch Metadata & Disclaimer
        print("\n[7] Generating Statutory Compliance Inspection Report")
        report_resp = await client.post(
            f"/api/v1/scans/{scan1_id}/report",
            json={"notes": "Statutory inspection concluded with non-compliance notice."},
            headers=insp_headers,
        )
        assert report_resp.status_code == 201
        report_id = report_resp.json()["data"]["id"]
        meta_resp = await client.get(f"/api/v1/reports/{report_id}", headers=insp_headers)
        rep_meta = meta_resp.json()["data"]
        assert rep_meta["summary_data"]["batch_number"] == test_batch
        print(f"    * Report generated: ID={report_id}, Batch in Report={rep_meta['summary_data']['batch_number']}")

        # 8. Check Analytics Dashboard
        print("\n[8] Querying Enforcement Intelligence Analytics Overview")
        analytics_resp = await client.get("/api/v1/analytics/summary", headers=insp_headers)
        assert analytics_resp.status_code == 200
        kpi = analytics_resp.json()["data"]
        print(f"    * Batches Inspected: {kpi['batches_inspected']}")
        print(f"    * Batches Attention Required: {kpi['batches_attention_required']}")
        print(f"    * Batch Alerts Count: {len(kpi['batch_investigation_alerts'])}")
        assert kpi["batches_attention_required"] >= 1

        print("\n" + "=" * 60)
        print("ALL BATCH INTELLIGENCE VERIFICATIONS PASSED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(verify_batch_intelligence_workflow())
