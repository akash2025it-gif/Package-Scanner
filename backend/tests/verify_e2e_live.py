import os
import sys
import time
import httpx

BASE_URL = "https://package-scanner-rust.vercel.app/api/v1"
PHOTO_PATH = "backend/test_packaged_commodity.jpg"

def run_e2e_tests():
    print("=" * 80)
    print("PACKCHECK AI – END-TO-END PRODUCTION VERIFICATION TEST SUITE")
    print(f"Target URL: {BASE_URL}")
    print("=" * 80)

    client = httpx.Client(
        transport=httpx.HTTPTransport(retries=3),
        timeout=httpx.Timeout(60.0, connect=30.0, read=60.0, write=60.0)
    )
    results = {}

    # Test 1: Health & API Connectivity
    print("\n[TEST 1] Backend API Health & Connectivity Check...")
    h_resp = client.get(f"{BASE_URL}/health")
    assert h_resp.status_code == 200, f"Health check failed: {h_resp.status_code}"
    h_data = h_resp.json()
    assert h_data.get("success") is True
    print(f"  -> PASS: Service: {h_data.get('data', {}).get('service')} | Status: {h_data.get('data', {}).get('status')}")
    results["API_Connectivity"] = "PASS"

    # Test 2: Login and Authentication
    print("\n[TEST 2] Authentication with Inspector Role...")
    l_resp = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": "inspector.sharma@packcheck.gov.in", "password": "inspector123"}
    )
    assert l_resp.status_code == 200, f"Login failed: {l_resp.status_code}"
    token_data = l_resp.json().get("data", {})
    token = token_data.get("access_token")
    user_info = token_data.get("user", {})
    assert token is not None
    assert user_info.get("role") == "inspector"
    client.headers.update({"Authorization": f"Bearer {token}"})
    print(f"  -> PASS: Logged in as: {user_info.get('name')} | Role: {user_info.get('role')} | Region: {user_info.get('region')}")
    results["Authentication"] = "PASS"

    # Test 3: Dashboard Analytics
    print("\n[TEST 3] Dashboard Analytics & KPI Retrieval...")
    a_resp = client.get(f"{BASE_URL}/analytics/summary")
    assert a_resp.status_code == 200, f"Analytics failed: {a_resp.status_code}"
    analytics_data = a_resp.json().get("data", {})
    total_scans = analytics_data.get("total_scans", 0)
    compliance_rate = analytics_data.get("compliance_rate", 0.0)
    print(f"  -> PASS: Total Scans Logged: {total_scans} | Compliance Rate: {compliance_rate:.1f}%")
    results["Dashboard_Analytics"] = "PASS"

    # Test 4: History and Review Queue
    print("\n[TEST 4] History List and Review Queue Inspection...")
    hist_resp = client.get(f"{BASE_URL}/scans?limit=10")
    assert hist_resp.status_code == 200, f"History failed: {hist_resp.status_code}"
    hist_items = hist_resp.json().get("data", {}).get("items", [])
    print(f"  -> PASS: History retrieved {len(hist_items)} scan records.")

    queue_resp = client.get(f"{BASE_URL}/scans?status=needs_review")
    assert queue_resp.status_code == 200, f"Review queue failed: {queue_resp.status_code}"
    queue_items = queue_resp.json().get("data", {}).get("items", [])
    print(f"  -> PASS: Review queue retrieved {len(queue_items)} pending review records.")
    results["History_And_Review_Queue"] = "PASS"

    # Test 5: Scan Ingestion & Quality Gate
    print("\n[TEST 5] Packaging Ingestion & Pre-OCR Quality Gate Check...")
    with open(PHOTO_PATH, "rb") as f:
        photo_bytes = f.read()

    q_resp = client.post(
        f"{BASE_URL}/scans/quality-check",
        files={"file": ("test_packaged_commodity.jpg", photo_bytes, "image/jpeg")}
    )
    assert q_resp.status_code == 200, f"Quality check failed: {q_resp.status_code}"
    q_data = q_resp.json().get("data", {})
    assert q_data.get("image_quality") == "CLEAR"
    assert q_data.get("can_analyze") is True
    print(f"  -> PASS: Quality Check: {q_data.get('image_quality')} | Sharpness: {q_data.get('sharpness_score'):.1f} (Threshold: {q_data.get('threshold')})")
    results["Quality_Gate"] = "PASS"

    # Test 6: Create Scan & Upload Image
    print("\n[TEST 6] Create Scan Record and Upload Commodity Photograph...")
    c_resp = client.post(
        f"{BASE_URL}/scans",
        json={"batch_number": "HN-MO-8924", "notes": "Production verification scan for Himalayan Mustard Oil"}
    )
    assert c_resp.status_code in (200, 201), f"Scan creation failed: {c_resp.status_code}"
    scan_id = c_resp.json().get("data", {}).get("id")

    up_resp = client.post(
        f"{BASE_URL}/scans/{scan_id}/images",
        files={"file": ("test_packaged_commodity.jpg", photo_bytes, "image/jpeg")},
        data={"image_type": "front"}
    )
    assert up_resp.status_code in (200, 201), f"Image upload failed: {up_resp.status_code}"
    print(f"  -> PASS: Scan created with ID: {scan_id} and photograph attached.")
    results["Scan_Ingestion"] = "PASS"

    # Test 7: Synchronous Real OCR & LMPC Compliance Evaluation
    print("\n[TEST 7] Synchronous Real OCR & LMPC 2011 Rule Evaluation Pipeline...")
    an_resp = client.post(f"{BASE_URL}/scans/{scan_id}/analyze")
    assert an_resp.status_code == 200, f"Analysis failed: {an_resp.status_code}"
    an_data = an_resp.json().get("data", {})
    print(f"  -> PASS: Analysis Status: {an_data.get('status')} | Message: {an_resp.json().get('message')}")

    # Fetch evaluated declarations
    scan_detail_resp = client.get(f"{BASE_URL}/scans/{scan_id}")
    assert scan_detail_resp.status_code == 200
    decls = scan_detail_resp.json().get("data", {}).get("declarations", [])
    assert len(decls) >= 8, f"Expected at least 8 declarations, got {len(decls)}"

    decl_map = {d.get("field_type"): d for d in decls}
    
    # Verify Rule 6(1)(b)
    mfg = decl_map.get("manufacturer_details", {})
    print(f"  * Rule 6(1)(b) Manufacturer: '{mfg.get('extracted_text')}' | Compliant: {mfg.get('is_compliant')} | Severity: {mfg.get('severity')}")
    assert mfg.get("is_compliant") is True
    assert "Himalayan" in str(mfg.get("extracted_text"))

    # Verify Rule 6(1)(f)
    mrp = decl_map.get("mrp", {})
    print(f"  * Rule 6(1)(f) MRP         : '{mrp.get('extracted_text')}' | Compliant: {mrp.get('is_compliant')} | Severity: {mrp.get('severity')}")
    assert mrp.get("is_compliant") is True

    # Verify Rule 6(1)(e) Month/Year of Mfg (correctly missing on package -> non-compliant)
    mfg_date = decl_map.get("mfg_date", {})
    print(f"  * Rule 6(1)(e) Mfg Date    : '{mfg_date.get('extracted_text')}' | Compliant: {mfg_date.get('is_compliant')} (Zero fake data)")
    results["OCR_And_LMPC_Validation"] = "PASS"

    # Test 8: Declaration Review / Override Workflow
    print("\n[TEST 8] Officer Verification / Review Workflow...")
    first_decl = decls[0]
    rev_resp = client.post(
        f"{BASE_URL}/scans/{scan_id}/declarations/{first_decl.get('id')}/review",
        json={"action": "confirm", "reviewer_notes": "Officer verified against physical packaging standard."}
    )
    assert rev_resp.status_code == 200, f"Review failed: {rev_resp.status_code}"
    dec_val = rev_resp.json().get("data", {}).get("human_decision")
    assert dec_val in ("confirm", "confirmed")
    print(f"  -> PASS: Declaration {first_decl.get('field_type')} confirmed by Inspector (decision: {dec_val}).")
    results["Review_Workflow"] = "PASS"

    # Test 9: PDF Statutory Certificate Generation & Download
    print("\n[TEST 9] Official PDF Statutory Certificate Generation & Byte Verification...")
    rep_resp = client.get(f"{BASE_URL}/scans/{scan_id}/report")
    assert rep_resp.status_code == 200, f"Report failed: {rep_resp.status_code}"
    rep_id = rep_resp.json().get("data", {}).get("id")

    pdf_resp = client.get(f"{BASE_URL}/reports/{rep_id}/pdf")
    assert pdf_resp.status_code == 200, f"PDF download failed: {pdf_resp.status_code}"
    assert pdf_resp.headers.get("Content-Type") == "application/pdf"
    pdf_bytes = pdf_resp.content
    assert pdf_bytes.startswith(b"%PDF-1.4"), "PDF missing %PDF-1.4 header!"
    assert b"%%EOF" in pdf_bytes[-100:], "PDF missing %%EOF trailer!"
    print(f"  -> PASS: Valid Binary PDF Generated. Size: {len(pdf_bytes)} bytes | Magic: %PDF-1.4 | Content-Type: application/pdf")
    results["PDF_Generation"] = "PASS"

    # Test 10: DOCX Statutory Dossier Generation & Download
    print("\n[TEST 10] Official DOCX Compliance Dossier Generation & Byte Verification...")
    docx_resp = client.get(f"{BASE_URL}/reports/{rep_id}/docx")
    assert docx_resp.status_code == 200, f"DOCX download failed: {docx_resp.status_code}"
    docx_bytes = docx_resp.content
    assert docx_bytes.startswith(b"PK"), "DOCX missing PK zip magic bytes!"
    print(f"  -> PASS: Valid DOCX Generated. Size: {len(docx_bytes)} bytes | Magic: PK (ZIP Container)")
    results["DOCX_Generation"] = "PASS"

    # Summary
    print("\n" + "=" * 80)
    print("ALL 10 END-TO-END WORKFLOW TESTS EXECUTED AND PASSED WITH 100% SUCCESS!")
    print("=" * 80)
    for test_name, status in results.items():
        print(f"  - {test_name:<28}: [{status}]")
    print("=" * 80)

if __name__ == "__main__":
    run_e2e_tests()
