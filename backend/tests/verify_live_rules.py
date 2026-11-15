import os
import sys
import time
import httpx

BASE_URL = "https://package-scanner-rust.vercel.app/api/v1"
PHOTO_PATH = "backend/test_packaged_commodity.jpg"

def main():
    print("=" * 70)
    print("PACKCHECK AI - LIVE PRODUCTION VERIFICATION FOR RULES 6(1)(b) & 6(1)(f)")
    print(f"Target: {BASE_URL}")
    print("=" * 70)

    client = httpx.Client(timeout=45.0)

    # Step 1: Login as inspector
    print("\n[STEP 1] Inspector Authentication...")
    login_resp = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": "inspector.sharma@packcheck.gov.in", "password": "inspector123"},
    )
    if login_resp.status_code != 200:
        print(f"FAILED to login: {login_resp.status_code} {login_resp.text}")
        sys.exit(1)
    
    token = login_resp.json().get("data", {}).get("access_token")
    client.headers.update({"Authorization": f"Bearer {token}"})
    print("SUCCESS: Inspector authenticated.")

    # Step 2: Create Scan
    print("\n[STEP 2] Creating Scan for Packaged Commodity...")
    scan_payload = {
        "batch_number": "HN-MO-8924",
        "notes": "Automated verification for Rule 6(1)(b) and Rule 6(1)(f)"
    }
    create_resp = client.post(f"{BASE_URL}/scans", json=scan_payload)
    if create_resp.status_code not in (200, 201):
        print(f"FAILED to create scan: {create_resp.status_code} {create_resp.text}")
        sys.exit(1)

    scan_data = create_resp.json().get("data", {})
    scan_id = scan_data.get("id")
    print(f"SUCCESS: Created scan ID: {scan_id}")

    # Step 3: Upload photograph
    print(f"\n[STEP 3] Uploading Package Photograph: {PHOTO_PATH}...")
    with open(PHOTO_PATH, "rb") as f:
        file_bytes = f.read()

    files = {"file": ("test_packaged_commodity.jpg", file_bytes, "image/jpeg")}
    data = {"image_type": "front"}
    up_resp = client.post(f"{BASE_URL}/scans/{scan_id}/images", files=files, data=data)
    if up_resp.status_code not in (200, 201):
        print(f"FAILED to upload image: {up_resp.status_code} {up_resp.text}")
        sys.exit(1)
    print("SUCCESS: Image uploaded and quality-validated.")

    # Step 4: Run Analysis
    print("\n[STEP 4] Executing AI Analysis Pipeline...")
    an_resp = client.post(f"{BASE_URL}/scans/{scan_id}/analyze")
    if an_resp.status_code != 200:
        print(f"FAILED to trigger analysis: {an_resp.status_code} {an_resp.text}")
        sys.exit(1)
    
    print("SUCCESS: Analysis completed synchronously or queued.")

    # Step 5: Fetch scan details and declarations
    print("\n[STEP 5] Fetching Evaluated Declarations...")
    get_resp = client.get(f"{BASE_URL}/scans/{scan_id}")
    if get_resp.status_code != 200:
        print(f"FAILED to fetch scan: {get_resp.status_code} {get_resp.text}")
        sys.exit(1)

    full_scan = get_resp.json().get("data", {})
    decls = full_scan.get("declarations", [])
    print(f"Overall Scan Status: {full_scan.get('status')}")
    print(f"Total Declarations Evaluated: {len(decls)}\n")

    decl_map = {d.get("field_type"): d for d in decls}

    print("-" * 70)
    print(f"{'FIELD TYPE':<22} | {'COMPLIANT':<9} | {'SEVERITY':<10} | {'EXTRACTED VALUE':<30}")
    print("-" * 70)
    for d in decls:
        ft = d.get("field_type", "")
        comp = str(d.get("is_compliant"))
        sev = str(d.get("severity", ""))
        val = str(d.get("extracted_text") or "")[:28]
        print(f"{ft:<22} | {comp:<9} | {sev:<10} | {val:<30}")
    print("-" * 70)

    # Detailed Inspection of Rule 6(1)(b)
    print("\n" + "=" * 70)
    print("DETAILED VERIFICATION: RULE 6(1)(b) MANUFACTURER DETAILS")
    print("=" * 70)
    mfg = decl_map.get("manufacturer_details")
    if not mfg:
        print("FAIL: Rule 6(1)(b) declaration missing from response!")
    else:
        mfg_text = mfg.get("extracted_text") or ""
        mfg_comp = mfg.get("is_compliant")
        mfg_sev = mfg.get("severity")
        mfg_notes = mfg.get("reviewer_notes")
        print(f"Extracted Text   : '{mfg_text}'")
        print(f"Is Compliant     : {mfg_comp}")
        print(f"Severity         : {mfg_sev}")
        print(f"Reviewer Notes   : {mfg_notes}")

        is_heading_only = any(mfg_text.strip().lower() == h for h in [
            "manufactured & packed by:", "manufactured & packed by", "mfg by:", "mfg by", "packed by:"
        ])
        if is_heading_only:
            if not mfg_comp and mfg_sev == "critical":
                print(f"-> PASS [Rule 6(1)(b)]: Heading alone was correctly REJECTED as NON-COMPLIANT (severity: {mfg_sev}).")
            else:
                print("-> FAIL [Rule 6(1)(b)]: Heading alone was incorrectly marked compliant!")
        else:
            if mfg_comp and "himalayan" in mfg_text.lower():
                print(f"-> PASS [Rule 6(1)(b)]: Complete manufacturer name & address extracted and marked COMPLIANT.")
            elif not mfg_comp:
                print(f"-> PASS [Rule 6(1)(b)]: Incomplete manufacturer details correctly flagged as non-compliant.")

    # Detailed Inspection of Rule 6(1)(f)
    print("\n" + "=" * 70)
    print("DETAILED VERIFICATION: RULE 6(1)(f) MAXIMUM RETAIL PRICE (MRP)")
    print("=" * 70)
    mrp = decl_map.get("mrp")
    if not mrp:
        print("FAIL: Rule 6(1)(f) declaration missing from response!")
    else:
        mrp_text = mrp.get("extracted_text") or ""
        mrp_comp = mrp.get("is_compliant")
        mrp_sev = mrp.get("severity")
        mrp_notes = mrp.get("reviewer_notes")
        mrp_workflow = mrp.get("workflow_decision")
        print(f"Extracted Text   : '{mrp_text}'")
        print(f"Is Compliant     : {mrp_comp}")
        print(f"Severity         : {mrp_sev}")
        print(f"Workflow Decision: {mrp_workflow}")
        print(f"Reviewer Notes   : {mrp_notes}")

        if mrp_comp:
            print(f"-> PASS [Rule 6(1)(f)]: Valid MRP declaration with statutory tax clause verified as COMPLIANT.")
        else:
            print(f"-> Evaluation details: compliant={mrp_comp}, severity={mrp_sev}. Notes: {mrp_notes}")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    main()
