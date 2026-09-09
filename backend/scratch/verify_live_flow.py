import io
import time
import httpx
from PIL import Image, ImageDraw

BASE_URL = "http://127.0.0.1:8080/api/v1"

def main():
    print("=== PACKCHECK LIVE END-TO-END VERIFICATION ===")

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Login as Inspector
        login_resp = client.post(
            "/auth/login",
            json={"email": "inspector.sharma@packcheck.gov.in", "password": "inspector123"}
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("1. Inspector Login: SUCCESS")

        # 2. Create New Scan for Dry Fruits package
        create_resp = client.post(
            "/scans",
            json={
                "location_name": "Spencer's Retail, Saket, New Delhi",
                "product_data": {
                    "name": "California Whole Almonds 250g",
                    "brand": "NutriBite",
                    "category": "Dry Fruits & Nuts",
                }
            },
            headers=headers
        )
        assert create_resp.status_code == 201, f"Create scan failed: {create_resp.text}"
        scan_id = create_resp.json()["data"]["id"]
        print(f"2. Create Scan for Dry Fruits: SUCCESS (Scan ID: {scan_id})")

        # 3. Upload Packaging Image
        img = Image.new("RGB", (900, 1100), color=(245, 240, 225))
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 50, 850, 1050], outline=(180, 120, 60), width=4)
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        upload_resp = client.post(
            f"/scans/{scan_id}/images",
            files={"files": ("nutribite_almonds_label.jpg", buf.getvalue(), "image/jpeg")},
            headers=headers
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        print("3. Upload Packaging Label Image: SUCCESS")

        # 4. Trigger AI Compliance Analysis
        analyze_resp = client.post(f"/scans/{scan_id}/analyze", headers=headers)
        assert analyze_resp.status_code == 200, f"Analyze failed: {analyze_resp.text}"
        print("4. Trigger AI Compliance Analysis: SUCCESS")

        # Poll until background processing completes
        for _ in range(10):
            time.sleep(0.5)
            detail_resp = client.get(f"/scans/{scan_id}", headers=headers)
            scan_detail = detail_resp.json()["data"]
            if scan_detail["declarations"] and len(scan_detail["declarations"]) > 0:
                break

        # 5. Retrieve Scan Analysis Findings
        detail_resp = client.get(f"/scans/{scan_id}", headers=headers)
        assert detail_resp.status_code == 200
        scan_detail = detail_resp.json()["data"]
        decls = scan_detail["declarations"]
        print(f"5. Retrieved {len(decls)} Declarations:")

        field_types = [d["field_type"] for d in decls]
        assert len(field_types) == len(set(field_types)), f"Duplicate fields found: {field_types}"
        assert field_types.count("net_quantity") == 1, "Net quantity duplicated!"

        for d in decls:
            conf = d["confidence_score"]
            conf_lvl = "HIGH" if conf >= 0.90 else ("MEDIUM" if conf >= 0.70 else "LOW")
            safe_text = (d["extracted_text"] or "").replace("\u20b9", "Rs.")
            print(f"   * [{d['field_type'].upper()}]: \"{safe_text}\" | Conf: {conf:.2f} ({conf_lvl}) | Status: {'COMPLIANT' if d['is_compliant'] else 'NON-COMPLIANT'}")

        # 6. Generate Statutory Report
        rep_resp = client.post(f"/scans/{scan_id}/report", headers=headers)
        assert rep_resp.status_code == 201
        report = rep_resp.json()["data"]
        report_id = report["id"]
        summary = report["summary_data"]
        print(f"6. Generate Report: SUCCESS (Report ID: {report_id})")
        print(f"   * Overall Result: {summary.get('overall_label')}")
        print(f"   * Statutory Assessment: {summary.get('statutory_assessment')}")

        # 7. Download PDF
        pdf_resp = client.get(f"/reports/{report_id}/pdf", headers=headers)
        assert pdf_resp.status_code == 200
        assert len(pdf_resp.content) > 100
        print(f"7. Stream PDF Report: SUCCESS ({len(pdf_resp.content)} bytes)")

        # 8. Download DOCX
        docx_resp = client.get(f"/reports/{report_id}/docx", headers=headers)
        assert docx_resp.status_code == 200
        assert len(docx_resp.content) > 100
        print(f"8. Stream DOCX Report: SUCCESS ({len(docx_resp.content)} bytes)")

        # 9. Verify RBAC Permissions
        # Reviewer Login
        rev_login = client.post("/auth/login", json={"email": "reviewer.patel@packcheck.gov.in", "password": "reviewer123"})
        assert rev_login.status_code == 200
        rev_token = rev_login.json()["data"]["access_token"]
        rev_headers = {"Authorization": f"Bearer {rev_token}"}

        # Reviewer cannot create scan
        rev_create = client.post("/scans", json={"location_name": "Test"}, headers=rev_headers)
        assert rev_create.status_code == 403, f"Expected 403 for Reviewer create, got {rev_create.status_code}"

        # Reviewer CAN override declaration
        first_decl_id = decls[0]["id"]
        rev_override = client.patch(
            f"/scans/{scan_id}/declarations/{first_decl_id}",
            json={"is_compliant": True, "reviewer_notes": "Verified by Senior Legal Metrology Officer Patel."},
            headers=rev_headers
        )
        assert rev_override.status_code == 200, f"Expected 200 for Reviewer override, got {rev_override.status_code}"
        print("9. Reviewer RBAC Verification: SUCCESS (Forbidden to create scan, Allowed to override)")

        # Viewer Login
        view_login = client.post("/auth/login", json={"email": "viewer@packcheck.gov.in", "password": "viewer123"})
        assert view_login.status_code == 200
        view_token = view_login.json()["data"]["access_token"]
        view_headers = {"Authorization": f"Bearer {view_token}"}

        # Viewer cannot create scan
        view_create = client.post("/scans", json={"location_name": "Test"}, headers=view_headers)
        assert view_create.status_code == 403

        # Viewer cannot override
        view_override = client.patch(
            f"/scans/{scan_id}/declarations/{first_decl_id}",
            json={"is_compliant": False, "reviewer_notes": "Attempted viewer override"},
            headers=view_headers
        )
        assert view_override.status_code == 403
        print("10. Viewer RBAC Verification: SUCCESS (Read-only strictly enforced)")

        # Admin Login
        admin_login = client.post("/auth/login", json={"email": "admin@packcheck.gov.in", "password": "admin123"})
        assert admin_login.status_code == 200
        print("11. Admin Login & Access: SUCCESS")

        print("\nALL LIVE END-TO-END VERIFICATIONS PASSED 100%!")

if __name__ == "__main__":
    main()
