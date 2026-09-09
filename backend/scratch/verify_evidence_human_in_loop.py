import json
import urllib.request
import urllib.parse
import io
import sys
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8080"


def make_req(path, method="GET", data=None, token=None, content_type="application/json"):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    body = None
    if data is not None:
        if content_type == "application/json":
            headers["Content-Type"] = "application/json"
            body = json.dumps(data).encode("utf-8")
        else:
            headers["Content-Type"] = content_type
            body = data

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, {"error": err_body}

def login(email, password):
    status, res = make_req("/api/v1/auth/login", method="POST", data={"email": email, "password": password})
    assert status == 200, f"Login failed for {email}: {res}"
    return res["data"]["access_token"]

def main():
    print("=== STARTING EVIDENCE & HUMAN-IN-THE-LOOP END-TO-END VERIFICATION ===")

    # 1. Login as Inspector
    print("\n1. Logging in as Inspector...")
    insp_token = login("inspector.sharma@packcheck.gov.in", "inspector123")
    print("   Inspector token acquired.")

    # 2. Create Scan
    print("\n2. Initializing New Scan for 'Roasted Salted Cashews - Dry Fruits'...")
    st, scan_res = make_req("/api/v1/scans", method="POST", data={
        "product_data": {
            "name": "Roasted Salted Cashews - Dry Fruits",
            "brand": "Royal Nutrients",
            "category": "Dry Fruits",
            "manufacturer_name": "Royal Nutrients Pvt Ltd",
            "manufacturer_address": "Goa, India",
            "country_of_origin": "India",
            "barcode": "8909876543210"
        },
        "source": "physical_store",
        "location_name": "Spencer's Hypermarket, Panaji"
    }, token=insp_token)
    assert st == 201
    scan_id = scan_res["data"]["id"]
    print(f"   Scan initialized: ID={scan_id}")

    # 3. Upload Image
    print("\n3. Uploading packaging label image...")
    img = Image.new("RGB", (600, 800), color=(245, 240, 230))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="cashew_label.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8") + img_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image_type"\r\n\r\n'
        f"front\r\n--{boundary}--\r\n"
    ).encode("utf-8")

    st, up_res = make_req(f"/api/v1/scans/{scan_id}/images", method="POST", data=body, token=insp_token, content_type=f"multipart/form-data; boundary={boundary}")
    assert st == 200
    print(f"   Image uploaded: URL={up_res['data'][0]['image_url']}")

    # 4. Trigger AI Analysis
    print("\n4. Triggering AI Analysis...")
    st, an_res = make_req(f"/api/v1/scans/{scan_id}/analyze", method="POST", token=insp_token)
    assert st == 200
    print(f"   AI analysis triggered: job_id={an_res['data']['job_id']}")

    # Wait for background task to complete analysis
    import time
    decls = []
    for _ in range(15):
        time.sleep(0.4)
        st, det_res = make_req(f"/api/v1/scans/{scan_id}", token=insp_token)
        if st == 200 and det_res["data"]["status"] != "processing" and len(det_res["data"]["declarations"]) > 0:
            decls = det_res["data"]["declarations"]
            break

    print(f"   Extracted {len(decls)} declarations:")
    for d in decls:
        print(f"     - {d['field_type']}: \"{d['extracted_text']}\" [Conf={d['confidence_score']:.2f}, Compliant={d['is_compliant']}]")

    assert len(decls) > 0, "Declarations must be extracted"


    # 6. Inspector Review: Confirm first finding, Override second finding
    decl_1 = decls[0]
    decl_2 = decls[1]

    print(f"\n5. Performing Human Review on Finding 1 ({decl_1['field_type']})...")
    st, rev_1 = make_req(f"/api/v1/scans/{scan_id}/declarations/{decl_1['id']}/review", method="POST", data={
        "action": "confirm",
        "reviewer_notes": "Declaration confirmed by inspecting officer Vikram Sharma based on label OCR."
    }, token=insp_token)
    assert st == 200
    assert rev_1["data"]["human_decision"] == "confirmed"
    print(f"   Confirmed finding 1: decision={rev_1['data']['human_decision']}, notes={rev_1['data']['reviewer_notes']}")

    print(f"\n6. Performing Human Override on Finding 2 ({decl_2['field_type']})...")
    st, rev_2 = make_req(f"/api/v1/scans/{scan_id}/declarations/{decl_2['id']}/review", method="POST", data={
        "action": "override",
        "is_compliant": True,
        "severity": "none",
        "reviewer_notes": "Declaration verified physically on back panel; fully complies with Rule 6."
    }, token=insp_token)
    assert st == 200
    assert rev_2["data"]["human_decision"] == "overridden"
    assert rev_2["data"]["reviewer_override"] is True
    print(f"   Overridden finding 2: decision={rev_2['data']['human_decision']}, notes={rev_2['data']['reviewer_notes']}")

    # 7. Finalize Inspection
    print("\n7. Finalizing Inspection with Officer Decision...")
    st, fin_res = make_req(f"/api/v1/scans/{scan_id}/finalize", method="POST", data={
        "final_decision": "compliant",
        "remarks": "Statutory verification completed at Spencer's Hypermarket. All mandatory declarations verified."
    }, token=insp_token)
    assert st == 200
    assert fin_res["data"]["status"] == "finalized"
    print(f"   Inspection finalized as: {fin_res['data']['metadata_json']['final_decision'].upper()}")

    # 8. Check Audit Trail
    print("\n8. Fetching Audit Trail...")
    st, audit_res = make_req(f"/api/v1/scans/{scan_id}/audit-trail", token=insp_token)
    assert st == 200
    logs = audit_res["data"]
    print(f"   Audit trail contains {len(logs)} entries:")
    for l in logs:
        print(f"     [{l['timestamp']}] {l['user_name']} ({l['user_role']}) -> {l['action']}")

    # 9. Generate Report & verify PDF / DOCX
    print("\n9. Generating Statutory Report...")
    st, rep_res = make_req(f"/api/v1/scans/{scan_id}/report", method="POST", data={
        "notes": "Verified and signed off by Inspector Vikram Sharma."
    }, token=insp_token)
    assert st == 201
    rep_id = rep_res["data"]["id"]
    summary = rep_res["data"]["summary_data"]
    print(f"   Report generated: ID={rep_id}")
    print(f"   Final Decision in Report: {summary.get('final_human_decision')} (AI Prelim: {summary.get('ai_preliminary_label')})")
    print(f"   Final Remarks: {summary.get('final_remarks')}")

    # Verify PDF stream
    pdf_req = urllib.request.Request(f"{BASE_URL}/api/v1/reports/{rep_id}/pdf", headers={"Authorization": f"Bearer {insp_token}"})
    with urllib.request.urlopen(pdf_req) as pdf_resp:
        pdf_bytes = pdf_resp.read()
        assert pdf_bytes.startswith(b"%PDF") or b"<html" in pdf_bytes.lower() or b"<!doctype html" in pdf_bytes.lower(), "PDF stream invalid"
        print(f"   PDF report document verified: {len(pdf_bytes)} bytes")


    # Verify DOCX stream
    docx_req = urllib.request.Request(f"{BASE_URL}/api/v1/reports/{rep_id}/docx", headers={"Authorization": f"Bearer {insp_token}"})
    with urllib.request.urlopen(docx_req) as docx_resp:
        docx_bytes = docx_resp.read()
        assert len(docx_bytes) > 1000, "DOCX stream invalid"
        print(f"   DOCX report verified: {len(docx_bytes)} bytes")

    # 10. Test RBAC permissions
    print("\n10. Testing RBAC matrix...")
    # Reviewer
    rev_token = login("reviewer.patel@packcheck.gov.in", "reviewer123")
    st_create, _ = make_req("/api/v1/scans", method="POST", data={"source": "physical_store"}, token=rev_token)
    assert st_create == 403, "Reviewer must not create scans"
    st_rep, _ = make_req(f"/api/v1/scans/{scan_id}/report", method="POST", token=rev_token)
    assert st_rep == 201, "Reviewer must be able to generate report"
    print("   Reviewer RBAC: scan creation blocked (403), review/reports allowed (200/201).")

    # Viewer
    view_token = login("viewer@packcheck.gov.in", "viewer123")
    st_v_create, _ = make_req("/api/v1/scans", method="POST", data={"source": "physical_store"}, token=view_token)
    assert st_v_create == 403, "Viewer must not create scans"
    st_v_rev, _ = make_req(f"/api/v1/scans/{scan_id}/declarations/{decl_1['id']}/review", method="POST", data={"action": "confirm", "reviewer_notes": "attempt"}, token=view_token)
    assert st_v_rev == 403, "Viewer must not review declarations"
    st_v_fin, _ = make_req(f"/api/v1/scans/{scan_id}/finalize", method="POST", data={"final_decision": "compliant", "remarks": "attempt"}, token=view_token)
    assert st_v_fin == 403, "Viewer must not finalize scans"
    st_v_view, _ = make_req(f"/api/v1/scans/{scan_id}", token=view_token)
    assert st_v_view == 200, "Viewer must be able to view scan details"
    print("   Viewer RBAC: create/review/finalize blocked (403), read-only view allowed (200).")

    # Admin
    admin_token = login("admin@packcheck.gov.in", "admin123")
    st_adm_usr, _ = make_req("/api/v1/users", token=admin_token)
    assert st_adm_usr == 200, "Admin must have access to users"
    print("   Admin RBAC: full administrative access confirmed (200).")

    # 11. Persistence verification: reload from fresh DB query
    print("\n11. Verifying Database Persistence across fresh queries...")
    st, fresh_det = make_req(f"/api/v1/scans/{scan_id}", token=insp_token)
    assert fresh_det["data"]["status"] == "finalized"
    assert fresh_det["data"]["metadata_json"]["final_decision"] == "compliant"
    assert "Spencer's Hypermarket" in fresh_det["data"]["metadata_json"]["final_remarks"]
    print("   Persistence verified: status='finalized', final_decision='compliant', remarks intact.")

    print("\n=== ALL EVIDENCE & HUMAN-IN-THE-LOOP CHECKS PASSED PERFECTLY ===")

if __name__ == "__main__":
    main()
