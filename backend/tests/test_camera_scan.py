import pytest
from httpx import AsyncClient
import io

@pytest.mark.asyncio
async def test_scan_new_page_contains_camera_and_upload_options(client: AsyncClient):
    res = await client.get("/scan/new")
    assert res.status_code == 200
    html = res.text

    # Verify both simultaneous visible choice cards
    assert "Scan / Capture Package" in html
    assert "Upload Image" in html
    assert "cameraCaptureBtn" in html
    assert "dropZone" in html
    assert "fileInput" in html

    # Verify Camera Modal Overlay Elements
    assert "cameraModal" in html
    assert "modalCameraVideo" in html
    assert "modalCapturedPhotoImg" in html
    assert "modalCameraErrorBox" in html
    assert "modalCaptureBtn" in html
    assert "modalUsePhotoBtn" in html
    assert "modalRetakeBtn" in html
    assert "modalFlipBtn" in html
    assert "modalCancelBtn" in html

    # Verify JavaScript Modal Lifecycle & Camera Operations
    assert "openCameraModal" in html
    assert "closeCameraModal" in html
    assert "startCameraStream" in html
    assert "stopActiveMediaStream" in html
    assert "captureModalPhoto" in html
    assert "retakeModalPhoto" in html
    assert "confirmModalPhoto" in html
    assert "navigator.mediaDevices.getUserMedia" in html
    assert "selectedFile = capturedFile" in html or "selectedFile =" in html

@pytest.mark.asyncio
async def test_camera_captured_photo_upload_and_analyze_pipeline(client: AsyncClient, test_users, auth_headers):
    headers = auth_headers("inspector")

    # 1. Create Scan
    scan_payload = {
        "source": "physical_store",
        "location_name": "Field Inspection - Reliance Retail Sector 29",
        "gps_coordinates": "28.4595, 77.0266",
        "product_data": {
            "name": "Haldiram's Bhujia Sev 200g",
            "brand": "Haldiram's",
            "category": "Packaged Food"
        }
    }
    create_res = await client.post("/api/v1/scans", json=scan_payload, headers=headers)
    assert create_res.status_code == 201
    scan_id = create_res.json()["data"]["id"]

    from tests.conftest import create_clear_test_image_bytes
    fake_camera_jpeg = create_clear_test_image_bytes()
    files = {
        "files": ("label_camera_1725450000.jpg", io.BytesIO(fake_camera_jpeg), "image/jpeg")
    }
    upload_res = await client.post(
        f"/api/v1/scans/{scan_id}/images",
        files=files,
        data={"image_type": "front"},
        headers=headers
    )
    assert upload_res.status_code == 200
    assert upload_res.json()["success"] is True
    uploaded_images = upload_res.json()["data"]
    assert len(uploaded_images) >= 1
    assert uploaded_images[0]["image_url"].endswith(".jpg")
    assert f"/api/v1/storage/scans/{scan_id}/" in uploaded_images[0]["image_url"]

    # 3. Trigger Analysis
    analyze_res = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_res.status_code == 200
    assert analyze_res.json()["success"] is True

    # 4. Fetch Scan Details
    detail_res = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_res.status_code == 200
    scan_data = detail_res.json()["data"]
    assert scan_data["id"] == scan_id
    assert len(scan_data["images"]) >= 1
    assert scan_data["product"]["name"] == "Haldiram's Bhujia Sev 200g"

@pytest.mark.asyncio
async def test_reviewer_and_viewer_cannot_create_or_upload_scans(client: AsyncClient, test_users, auth_headers):
    # Reviewer blocked
    rev_headers = auth_headers("reviewer")
    rev_res = await client.post("/api/v1/scans", json={"source": "physical_store"}, headers=rev_headers)
    assert rev_res.status_code == 403

    # Viewer blocked
    view_headers = auth_headers("viewer")
    view_res = await client.post("/api/v1/scans", json={"source": "physical_store"}, headers=view_headers)
    assert view_res.status_code == 403
