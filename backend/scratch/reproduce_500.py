import sys
import os
sys.path.insert(0, os.path.abspath("."))
import asyncio
import sqlite3
import traceback
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

def inspect_sqlite():
    conn = sqlite3.connect("packcheck.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables in packcheck.db:")
    for t in tables:
        t_name = t[0]
        cursor.execute(f"PRAGMA table_info({t_name});")
        cols = cursor.fetchall()
        print(f"Table {t_name}: {[c[1] for c in cols]}")
    conn.close()

async def test_reproduce():
    try:
        print("--- Running init_db ---")
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://localhost:8000") as client:
            # Login as inspector
            login_resp = await client.post("/api/v1/auth/login", json={
                "email": "inspector.sharma@packcheck.gov.in",
                "password": "inspector123"
            })
            print("Login response:", login_resp.status_code, login_resp.text)
            token = login_resp.json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

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

            print("--- Sending POST /api/v1/scans ---")
            scan_res = await client.post("/api/v1/scans", json=create_payload, headers=headers)
            print("Scan creation status:", scan_res.status_code)
            print("Scan creation response:", scan_res.text)

    except Exception as e:
        print("EXCEPTION in test_reproduce:")
        traceback.print_exc()

if __name__ == "__main__":
    print("=== Inspecting SQLite DB ===")
    inspect_sqlite()
    print("\n=== Reproducing Request ===")
    asyncio.run(test_reproduce())
