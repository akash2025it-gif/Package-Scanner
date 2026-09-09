import io
import time
import httpx
from PIL import Image

def main():
    client = httpx.Client(base_url='http://127.0.0.1:8080/api/v1')

    # 1. Login
    login_res = client.post('/auth/login', json={'email': 'inspector.sharma@packcheck.gov.in', 'password': 'inspector123'})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()['data']['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Create Scan
    scan_res = client.post('/scans', json={
        'source': 'physical_store',
        'location_name': 'Reliance Smart, Gurgaon',
        'product_data': {
            'name': "Lay's India's Magic Masala Potato Chips 50g",
            'brand': "Lay's",
            'category': "Packaged Snacks & Chips"
        }
    }, headers=headers)
    assert scan_res.status_code == 201, f"Create scan failed: {scan_res.text}"
    scan_id = scan_res.json()['data']['id']
    print(f"[1] Created Scan ID: {scan_id}")

    # 3. Upload Image
    buf = io.BytesIO()
    img = Image.new('RGB', (800, 1000), color=(240, 200, 100))
    img.save(buf, format='JPEG')
    buf.seek(0)
    upload_res = client.post(
        f'/scans/{scan_id}/images',
        files={'files': ('lays_magic_masala.jpg', buf.getvalue(), 'image/jpeg')},
        headers=headers
    )
    assert upload_res.status_code == 200, f"Upload image failed: {upload_res.text}"
    uploaded_img = upload_res.json()['data'][0]
    print(f"[2] Uploaded Image URL: {uploaded_img['image_url']}, size: {uploaded_img['width_px']}x{uploaded_img['height_px']}")

    # 4. Trigger Analysis
    analyze_res = client.post(f'/scans/{scan_id}/analyze', headers=headers)
    assert analyze_res.status_code == 200, f"Trigger analysis failed: {analyze_res.text}"
    print("[3] Analysis Triggered")

    # Give background task a moment
    time.sleep(1)

    # 5. Fetch resulting scan
    get_res = client.get(f'/scans/{scan_id}', headers=headers)
    assert get_res.status_code == 200, f"Get scan failed: {get_res.text}"
    data = get_res.json()['data']

    print(f"[4] Scan Status: {data['status']}")
    print(f"    Product: {data['product']['name']} ({data['product']['brand']})")
    print(f"    Images: {len(data['images'])} attached -> {data['images'][0]['image_url']}")
    print(f"    Declarations Count: {len(data['declarations'])}")

    combined_text = ""
    for d in data['declarations']:
        txt = d['extracted_text'] or '[Absent]'
        combined_text += " " + txt
        safe_txt = txt.encode('ascii', 'replace').decode('ascii')
        print(f"     * {d['field_type']}: {safe_txt} | compliant: {d['is_compliant']} | font: {d['font_size_mm']}mm")

    # Verify no Aashirvaad / 5kg / ITC
    assert "AASHIRVAAD" not in combined_text.upper(), "Found Aashirvaad in declarations!"
    assert "5 kg" not in combined_text, "Found 5 kg in declarations!"
    assert "ITC Limited" not in combined_text, "Found ITC Limited in declarations!"

    # 6. Verify image retrieval from storage endpoint
    img_url = data['images'][0]['image_url']
    img_res = client.get(img_url.replace('/api/v1', ''))
    assert img_res.status_code == 200, f"Image fetch failed: {img_res.status_code}"
    assert img_res.headers.get("content-type") == "image/jpeg", f"Wrong content-type: {img_res.headers.get('content-type')}"
    assert len(img_res.content) == len(buf.getvalue()), "Image bytes length mismatch"
    print(f"[5] Verified Storage Layer: Retrieved {len(img_res.content)} bytes with content-type image/jpeg")

    # 7. Test Override workflow
    first_decl_id = data['declarations'][0]['id']
    override_res = client.patch(
        f"/scans/{scan_id}/declarations/{first_decl_id}",
        json={"is_compliant": True, "reviewer_notes": "Verified against physical pouch"},
        headers=headers
    )
    assert override_res.status_code == 200, "Override failed"
    assert override_res.json()['data']['reviewer_override'] is True
    print(f"[6] Verified Inspector Override: Declaration {first_decl_id} overridden successfully")

    # 8. Test Statutory Report Generation
    report_res = client.post(f"/scans/{scan_id}/report", json={"notes": "Inspection concluded"}, headers=headers)
    assert report_res.status_code == 201, f"Report generation failed: {report_res.status_code}"
    report_id = report_res.json()['data']['id']
    print(f"[7] Verified Statutory Report Generation: Report ID {report_id}")

    # 9. Test Close Scan
    close_res = client.post(f"/scans/{scan_id}/close", json={"notes": "All checks verified"}, headers=headers)
    assert close_res.status_code == 200, "Close scan failed"
    assert close_res.json()['data']['status'] == "closed"
    print(f"[8] Verified Conclude Inspection: Scan status marked as CLOSED")

    print("\n=======================================================")
    print("[SUCCESS] All 8 Verification Milestones Passed Successfully!")
    print("=======================================================")

if __name__ == '__main__':
    main()
