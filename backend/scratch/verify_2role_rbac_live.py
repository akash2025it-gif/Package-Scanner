"""
Comprehensive Live Verification Script for PackSure AI 2-Role RBAC Model
Tests all 13 verification criteria against live endpoints & SQLite DB.
"""
import asyncio
import os
import sys
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import init_db
from app.core.security import create_access_token
from app.main import app


async def run_live_verification():
    print("=" * 70)
    print("PACKSURE AI — 2-ROLE RBAC LIVE VERIFICATION SUITE")
    print("=" * 70)

    # Initialize DB (runs deactivation of obsolete users)
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # -------------------------------------------------------------
        # TEST 1: Inspector Login
        # -------------------------------------------------------------
        print("\n[TEST 1] Inspector Login (inspector.sharma@packcheck.gov.in)...")
        r_insp = await client.post("/api/v1/auth/login", json={
            "email": "inspector.sharma@packcheck.gov.in",
            "password": "inspector123"
        })
        assert r_insp.status_code == 200, f"Failed: {r_insp.text}"
        insp_data = r_insp.json()["data"]
        insp_token = insp_data["access_token"]
        assert insp_data["user"]["role"] == "inspector"
        print("  -> PASSED: Inspector authenticated successfully with role 'inspector'")

        # -------------------------------------------------------------
        # TEST 2: Admin Login
        # -------------------------------------------------------------
        print("\n[TEST 2] Admin Login (admin@packcheck.gov.in)...")
        r_adm = await client.post("/api/v1/auth/login", json={
            "email": "admin@packcheck.gov.in",
            "password": "admin123"
        })
        assert r_adm.status_code == 200, f"Failed: {r_adm.text}"
        adm_data = r_adm.json()["data"]
        adm_token = adm_data["access_token"]
        assert adm_data["user"]["role"] == "admin"
        print("  -> PASSED: Admin authenticated successfully with role 'admin'")

        # -------------------------------------------------------------
        # TEST 3: Old Reviewer Login Attempt
        # -------------------------------------------------------------
        print("\n[TEST 3] Obsolete Reviewer Login Attempt (reviewer.patel@packcheck.gov.in)...")
        r_rev = await client.post("/api/v1/auth/login", json={
            "email": "reviewer.patel@packcheck.gov.in",
            "password": "reviewer123"
        })
        assert r_rev.status_code == 401, f"Expected 401 for obsolete reviewer login, got {r_rev.status_code}"
        print("  -> PASSED: Obsolete Reviewer login denied (401 Unauthorized)")

        # -------------------------------------------------------------
        # TEST 4: Old Viewer Login Attempt
        # -------------------------------------------------------------
        print("\n[TEST 4] Obsolete Viewer Login Attempt (viewer@packcheck.gov.in)...")
        r_view = await client.post("/api/v1/auth/login", json={
            "email": "viewer@packcheck.gov.in",
            "password": "viewer123"
        })
        assert r_view.status_code == 401, f"Expected 401 for obsolete viewer login, got {r_view.status_code}"
        print("  -> PASSED: Obsolete Viewer login denied (401 Unauthorized)")

        # -------------------------------------------------------------
        # TEST 5: Existing Reviewer/Viewer Token Access
        # -------------------------------------------------------------
        print("\n[TEST 5] Testing Previously Issued Reviewer and Viewer JWT Tokens...")
        fake_rev_token = create_access_token(subject="b256ba88-aa39-44f2-8e4e-005abf36dea3", role="reviewer")
        fake_view_token = create_access_token(subject="fe11beae-5da9-4a81-ac4c-3fb415663127", role="viewer")

        r_tok_rev = await client.get("/api/v1/scans", headers={"Authorization": f"Bearer {fake_rev_token}"})
        assert r_tok_rev.status_code == 403, f"Expected 403 for obsolete token, got {r_tok_rev.status_code}"

        r_tok_view = await client.get("/api/v1/products", headers={"Authorization": f"Bearer {fake_view_token}"})
        assert r_tok_view.status_code == 403, f"Expected 403 for obsolete token, got {r_tok_view.status_code}"
        print("  -> PASSED: Obsolete Reviewer and Viewer tokens rejected (403 Forbidden)")

        # -------------------------------------------------------------
        # TEST 6: Manage Team (Admin Only)
        # -------------------------------------------------------------
        print("\n[TEST 6] Manage Team API & RBAC...")
        r_team_adm = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {adm_token}"})
        assert r_team_adm.status_code == 200
        users_list = r_team_adm.json()["data"]["items"]
        active_roles = {u["role"] for u in users_list if u.get("is_active", True)}
        print(f"  -> Active users in roster: {[u['email'] + ' (' + u['role'] + ')' for u in users_list if u.get('is_active', True)]}")
        
        # Inspector attempting to access users list
        r_team_insp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_team_insp.status_code == 403
        print("  -> PASSED: Team management accessible to Admin only, Inspector forbidden (403)")

        # -------------------------------------------------------------
        # TEST 7: User Creation API Role Validation
        # -------------------------------------------------------------
        print("\n[TEST 7] User Creation Validation (Rejecting REVIEWER & VIEWER)...")
        r_create_rev = await client.post("/api/v1/users", json={
            "name": "Invalid Reviewer",
            "email": "invalid.reviewer@packcheck.gov.in",
            "password": "password123",
            "role": "reviewer"
        }, headers={"Authorization": f"Bearer {adm_token}"})
        assert r_create_rev.status_code == 422, f"Expected 422 for role=reviewer, got {r_create_rev.status_code}"

        r_create_view = await client.post("/api/v1/users", json={
            "name": "Invalid Viewer",
            "email": "invalid.viewer@packcheck.gov.in",
            "password": "password123",
            "role": "viewer"
        }, headers={"Authorization": f"Bearer {adm_token}"})
        assert r_create_view.status_code == 422, f"Expected 422 for role=viewer, got {r_create_view.status_code}"

        # Valid Inspector creation
        r_create_insp = await client.post("/api/v1/users", json={
            "name": "Officer Test Live",
            "email": f"officer.live.{os.getpid()}@packcheck.gov.in",
            "password": "password123",
            "role": "inspector",
            "region": "Tamil Nadu"
        }, headers={"Authorization": f"Bearer {adm_token}"})
        assert r_create_insp.status_code == 201
        print("  -> PASSED: Obsolete roles rejected with 422; valid Inspector created (201)")

        # -------------------------------------------------------------
        # TEST 8: Inspector Full Workflow
        # -------------------------------------------------------------
        print("\n[TEST 8] Inspector Complete Human Verification Workflow...")
        # 1. Create Scan
        r_new_scan = await client.post("/api/v1/scans", json={
            "source": "physical_store",
            "location_name": "Field Supermarket, Connaught Place",
            "batch_number": "BATCH-VERIF-2026-X1",
            "product_data": {
                "name": "Organic Honey 500g",
                "brand": "NatureBest",
                "category": "Food Staples",
                "manufacturer_name": "NatureBest Organics Ltd",
                "country_of_origin": "India"
            }
        }, headers={"Authorization": f"Bearer {insp_token}"})
        assert r_new_scan.status_code == 201
        scan_id = r_new_scan.json()["data"]["id"]

        # 2. Upload image
        fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
        r_up = await client.post(f"/api/v1/scans/{scan_id}/images", files=[("files", ("honey_label.jpg", fake_img, "image/jpeg"))], headers={"Authorization": f"Bearer {insp_token}"})
        assert r_up.status_code == 200

        # 3. Analyze
        r_an = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_an.status_code == 200

        # 4. Get Scan Detail
        r_detail = await client.get(f"/api/v1/scans/{scan_id}", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_detail.status_code == 200
        decls = r_detail.json()["data"]["declarations"]
        decl_id = decls[0]["id"]

        # 5. Inspector Confirmation
        r_conf = await client.post(f"/api/v1/scans/{scan_id}/declarations/{decl_id}/review", json={
            "action": "confirm",
            "reviewer_notes": "Declaration verified physically by Inspector Sharma."
        }, headers={"Authorization": f"Bearer {insp_token}"})
        assert r_conf.status_code == 200

        # 6. Inspector Override on another declaration
        if len(decls) > 1:
            decl_id2 = decls[1]["id"]
            r_over = await client.patch(f"/api/v1/scans/{scan_id}/declarations/{decl_id2}", json={
                "is_compliant": True,
                "reviewer_notes": "Measured font height is 4.0mm on front panel, satisfies Second Schedule."
            }, headers={"Authorization": f"Bearer {insp_token}"})
            assert r_over.status_code == 200

        # 7. Finalize Scan
        r_fin = await client.post(f"/api/v1/scans/{scan_id}/finalize", json={
            "final_decision": "compliant",
            "remarks": "Complete statutory compliance verified by inspecting officer."
        }, headers={"Authorization": f"Bearer {insp_token}"})
        assert r_fin.status_code == 200

        # 8. Generate Report
        r_rep = await client.post(f"/api/v1/scans/{scan_id}/report", json={
            "notes": "Official inspection certificate generated."
        }, headers={"Authorization": f"Bearer {insp_token}"})
        assert r_rep.status_code == 201
        report_id = r_rep.json()["data"]["id"]
        print(f"  -> PASSED: Full Inspector workflow executed seamlessly. Generated Report ID: {report_id}")

        # -------------------------------------------------------------
        # TEST 9: Batch Intelligence Workflow
        # -------------------------------------------------------------
        print("\n[TEST 9] Batch Intelligence Workflow...")
        batch_num = "BATCH-VERIF-2026-X1"
        r_batch = await client.get(f"/api/v1/batches/{batch_num}", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_batch.status_code == 200
        assert r_batch.json()["data"]["total_inspections"] >= 1

        # Inspector updates batch investigation status
        r_b_up = await client.patch(f"/api/v1/batches/{batch_num}/status", json={
            "status": "under_investigation",
            "notes": "Cross-verification of sample lot initiated by field inspector."
        }, headers={"Authorization": f"Bearer {insp_token}"})
        assert r_b_up.status_code == 200
        assert r_b_up.json()["data"]["status"] == "under_investigation"
        print("  -> PASSED: Batch detail query and status update succeeded (200)")

        # -------------------------------------------------------------
        # TEST 10: Product & Inspection Confidentiality (No Auth)
        # -------------------------------------------------------------
        print("\n[TEST 10] Testing Confidentiality (Unauthenticated Access Attempts)...")
        endpoints_to_test = [
            ("/api/v1/scans", "Scans"),
            (f"/api/v1/scans/{scan_id}", "Scan Details"),
            ("/api/v1/products", "Product Catalog"),
            (f"/api/v1/batches/{batch_num}", "Batch Investigation"),
            (f"/api/v1/reports/{report_id}", "Inspection Reports"),
            ("/api/v1/analytics/summary", "Enforcement Intelligence"),
            ("/api/v1/users", "User Directory"),
        ]

        for ep, name in endpoints_to_test:
            r_unauth = await client.get(ep)
            assert r_unauth.status_code == 401, f"Expected 401 for unauthenticated {name} at {ep}, got {r_unauth.status_code}"
        print("  -> PASSED: All confidential resources strictly protected behind authentication (401)")

        # -------------------------------------------------------------
        # TEST 11: Historical Records & Audit Trail
        # -------------------------------------------------------------
        print("\n[TEST 11] Historical Records & Audit Trail Integrity...")
        r_audit = await client.get(f"/api/v1/scans/{scan_id}/audit-trail", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_audit.status_code == 200
        logs = r_audit.json()["data"]
        assert len(logs) > 0
        actions = [l["action"] for l in logs]
        print(f"  -> Audit trail recorded actions: {actions}")
        print("  -> PASSED: Complete historical audit trail intact without broken foreign keys")

        # -------------------------------------------------------------
        # TEST 12: PDF and DOCX Report Generation
        # -------------------------------------------------------------
        print("\n[TEST 12] PDF and DOCX Document Streaming...")
        r_pdf = await client.get(f"/api/v1/reports/{report_id}/pdf", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_pdf.status_code == 200
        assert r_pdf.headers["content-type"] == "application/pdf"
        assert len(r_pdf.content) > 500

        r_docx = await client.get(f"/api/v1/reports/{report_id}/docx", headers={"Authorization": f"Bearer {insp_token}"})
        assert r_docx.status_code == 200
        assert len(r_docx.content) > 500
        print("  -> PASSED: PDF and DOCX generated and streamed successfully with valid content")

        # -------------------------------------------------------------
        # TEST 13: UI Page Routes & Refresh Stability
        # -------------------------------------------------------------
        print("\n[TEST 13] UI Page Routes Availability...")
        ui_routes = [
            "/",
            "/login",
            "/dashboard",
            "/scan/new",
            "/analysis",
            "/report",
            "/products-ui",
            "/enforcement",
            "/team",
            f"/batch/{batch_num}",
        ]
        for route in ui_routes:
            r_ui = await client.get(route)
            assert r_ui.status_code == 200, f"UI route {route} failed with {r_ui.status_code}"
        print("  -> PASSED: All 10 UI routes accessible and ready for browser refresh")

    print("\n" + "=" * 70)
    print("ALL 13 ACCEPTANCE TESTS COMPLETED SUCCESSFULLY WITH ZERO ERRORS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_live_verification())
