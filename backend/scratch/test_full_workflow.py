import sys
import os
sys.path.insert(0, os.path.abspath("."))
import asyncio
import io
from PIL import Image
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

async def run_full_test():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
        # 1. Login as Inspector
        login_res = await client.post("/api/v1/auth/login", json={
            "email": "inspector.sharma@packcheck.gov.in",
            "password": "inspector123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[PASS] Login successful")

        # 2. POST /api/v1/scans (New Scan)
        create_payload = {
            "source": "physical_store",
            "location_name": "Reliance Retail Mart, Sector 29, Gurugram",
            "gps_coordinates": "28.4595, 77.0266",
            "batch_number": "BAT-2026-TEST",
            "product_data": {
                "name": "Lay's India's Magic Masala Chips 50g",
                "brand": "Lay's",
                "category": "Packaged Snacks & Chips"
            }
        }
        create_res = await client.post("/api/v1/scans", json=create_payload, headers=headers)
        print("Create scan status:", create_res.status_code)
        if create_res.status_code != 201:
            print("Create scan error:", create_res.text)
        assert create_res.status_code == 201
        scan_id = create_res.json()["data"]["id"]
        print(f"[PASS] Scan created: {scan_id}")

        # 3. POST /api/v1/scans/{id}/images (Image Upload)
        img = Image.new("RGB", (800, 1000), color=(255, 235, 150))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        files = {"files": ("lays_chips_packet.jpg", buf.getvalue(), "image/jpeg")}
        upload_res = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
        print("Upload status:", upload_res.status_code)
        assert upload_res.status_code == 200
        print("[PASS] Image uploaded")

        # 4. POST /api/v1/scans/{id}/analyze (Trigger analysis)
        analyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
        print("Analyze status:", analyze_res.status_code)
        assert analyze_res.status_code == 200
        print("[PASS] Analysis queued")

        # 5. GET /api/v1/scans/{id} (Check result)
        detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
        print("Detail status:", detail_res.status_code)
        assert detail_res.status_code == 200
        data = detail_res.json()["data"]
        print(f"[PASS] Scan detail retrieved. Status: {data['status']}, Declarations: {len(data['declarations'])}")

        # Check declarations
        for d in data["declarations"]:
            print(f"  Decl: {d['field_type']} - Compliant: {d['is_compliant']} - Rate: {d['violation_detection_rate']} - Workflow: {d['workflow_decision']}")

if __name__ == "__main__":
    asyncio.run(run_full_test())
