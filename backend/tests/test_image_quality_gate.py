from datetime import datetime
import io
import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy import select

from app.ai.quality import ImageQualityValidator
from app.models.audit import AuditLog
from app.models.declaration import Declaration
from app.models.scan import Scan, ScanImage
from app.workers.tasks import run_scan_analysis_pipeline_async


def create_test_sharp_image(width=600, height=800) -> bytes:
    """Creates a high-contrast sharp test image with rich text/edge patterns that produces high Laplacian variance."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw sharp high-frequency edge patterns and simulated text
    for y in range(20, height - 20, 20):
        draw.line([(20, y), (width - 20, y)], fill=(0, 0, 0), width=3)
    for x in range(30, width - 30, 40):
        draw.rectangle([x, 50, x + 25, height - 50], fill=(20, 50, 150), outline=(0, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def create_test_blurry_image(width=600, height=800, blur_radius=8.0) -> bytes:
    """Creates an authentically blurred image with low Laplacian variance."""
    sharp_bytes = create_test_sharp_image(width, height)
    img = Image.open(io.BytesIO(sharp_bytes))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG", quality=75)
    return buf.getvalue()


# ---------------------------------------------------------
# Unit Tests for ImageQualityValidator
# ---------------------------------------------------------

def test_quality_validator_clear_image():
    sharp_bytes = create_test_sharp_image()
    res = ImageQualityValidator.validate_image_bytes(sharp_bytes, threshold=100.0)
    assert res["image_quality"] == "CLEAR"
    assert res["can_analyze"] is True
    assert res["sharpness_score"] >= 100.0
    assert res["width"] == 600
    assert res["height"] == 800
    assert "clear" in res["message"].lower()


def test_quality_validator_blurry_image():
    blurry_bytes = create_test_blurry_image(blur_radius=12.0)
    res = ImageQualityValidator.validate_image_bytes(blurry_bytes, threshold=100.0)
    assert res["image_quality"] == "BLURRY"
    assert res["can_analyze"] is False
    assert res["sharpness_score"] < 100.0
    assert "too blurry" in res["message"].lower()


def test_quality_validator_empty_image():
    res = ImageQualityValidator.validate_image_bytes(b"", threshold=100.0)
    assert res["image_quality"] == "FAILED"
    assert res["can_analyze"] is False
    assert res["sharpness_score"] == 0.0


def test_quality_validator_corrupt_image():
    res = ImageQualityValidator.validate_image_bytes(b"not-a-valid-image-stream-content", threshold=100.0)
    assert res["image_quality"] == "FAILED"
    assert res["can_analyze"] is False


def test_quality_validator_small_dimensions():
    tiny = Image.new("RGB", (50, 50), color=(255, 0, 0))
    buf = io.BytesIO()
    tiny.save(buf, format="JPEG")
    res = ImageQualityValidator.validate_image_bytes(buf.getvalue(), threshold=100.0)
    assert res["image_quality"] == "LOW_QUALITY"
    assert res["can_analyze"] is False
    assert "below the minimum required" in res["message"]


# ---------------------------------------------------------
# Integration Tests: Standalone Quality Check API Endpoints
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_api_quality_check_endpoints(client: AsyncClient, test_users, auth_headers):
    headers = auth_headers("inspector")
    sharp_bytes = create_test_sharp_image()
    blurry_bytes = create_test_blurry_image()

    # 1. Clear image via /scans/quality-check
    resp1 = await client.post(
        "/api/v1/scans/quality-check",
        files={"file": ("label_clear.jpg", sharp_bytes, "image/jpeg")},
        headers=headers,
    )
    assert resp1.status_code == 200
    data1 = resp1.json()["data"]
    assert data1["image_quality"] == "CLEAR"
    assert data1["can_analyze"] is True
    assert data1["sharpness_score"] >= 100.0

    # 2. Blurry image via /images/quality-check alias
    resp2 = await client.post(
        "/api/v1/images/quality-check",
        files={"file": ("label_blur.jpg", blurry_bytes, "image/jpeg")},
        headers=headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]
    assert data2["image_quality"] == "BLURRY"
    assert data2["can_analyze"] is False
    assert data2["sharpness_score"] < 100.0


# ---------------------------------------------------------
# End-to-End Workflow & Defense-in-Depth Tests
# ---------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_image_full_analysis_workflow(client: AsyncClient, test_users, auth_headers, db_session):
    """Test 1: Clear image passes quality check and proceeds through full OCR/AI analysis."""
    headers = auth_headers("inspector")

    # 1. Create Scan
    create_payload = {
        "source": "physical_store",
        "location_name": "Spencer's Retail, Bangalore",
        "batch_number": "BATCH-CLR-2026",
        "product_data": {
            "name": "Tata Tea Premium 250g",
            "brand": "Tata Tea",
            "category": "Beverages",
            "manufacturer_name": "Tata Consumer Products Ltd",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # 2. Upload Clear Image
    sharp_bytes = create_test_sharp_image()
    files = {"files": ("tea_label_clear.jpg", sharp_bytes, "image/jpeg")}
    upload_resp = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
    assert upload_resp.status_code == 200
    uploaded = upload_resp.json()["data"][0]
    assert uploaded["image_quality"] == "CLEAR"
    assert uploaded["analysis_allowed"] is True
    assert uploaded["sharpness_score"] >= 100.0

    # 3. Trigger AI Analysis
    analyze_resp = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_resp.status_code == 200
    assert analyze_resp.json()["data"]["status"] == "queued"

    # Execute pipeline
    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 4. Detail response has declarations
    detail_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["data"]
    assert detail["status"] == "needs_review"
    assert len(detail["declarations"]) > 0


@pytest.mark.asyncio
async def test_blurry_image_blocks_analysis_and_rejects_bypass(client: AsyncClient, test_users, auth_headers, db_session):
    """Test 2 & 5: Blurry image is blocked, direct API bypass is rejected with HTTP 400, no OCR/declarations created."""
    headers = auth_headers("inspector")

    # 1. Create Scan
    create_payload = {
        "source": "physical_store",
        "location_name": "Big Bazaar, Delhi",
        "batch_number": "BATCH-BLUR-99",
        "product_data": {
            "name": "Parle-G Gold Biscuits 100g",
            "brand": "Parle",
            "category": "Biscuits & Bakery",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # 2. Upload Blurry Image
    blurry_bytes = create_test_blurry_image(blur_radius=15.0)
    files = {"files": ("blurry_label.jpg", blurry_bytes, "image/jpeg")}
    upload_resp = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
    assert upload_resp.status_code == 200
    uploaded = upload_resp.json()["data"][0]
    assert uploaded["image_quality"] == "BLURRY"
    assert uploaded["analysis_allowed"] is False
    assert uploaded["sharpness_score"] < 100.0

    # 3. Direct API Bypass Attempt: Call /analyze on the blurry scan
    analyze_resp = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_resp.status_code in [400, 422]  # ValidationException defense-in-depth!
    error_msg = str(analyze_resp.json())
    assert "too blurry" in error_msg.lower() or "blocked" in error_msg.lower()

    # 4. Verify no declarations were generated from the blocked image
    decls_res = await db_session.execute(select(Declaration).where(Declaration.scan_id == scan_id))
    decls = decls_res.scalars().all()
    assert len(decls) == 0

    # 5. Check Audit Log records AI_ANALYSIS_BLOCKED
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_id == scan_id,
            AuditLog.action == "AI_ANALYSIS_BLOCKED",
        )
    )
    audit_entry = audit_res.scalar_one_or_none()
    assert audit_entry is not None
    assert audit_entry.metadata_json.get("reason") == "IMAGE_TOO_BLURRY"


@pytest.mark.asyncio
async def test_batch_persistence_across_blur_and_reupload(client: AsyncClient, test_users, auth_headers, db_session):
    """Test 7: Batch number is preserved when an image is blurry and subsequent clear upload completes analysis."""
    headers = auth_headers("inspector")
    target_batch = "DF240826A"

    # 1. Create Scan with Batch Number
    create_payload = {
        "source": "physical_store",
        "location_name": "HyperCITY, Mumbai",
        "batch_number": target_batch,
        "product_data": {
            "name": "Britannia Good Day Butter Cookies 200g",
            "brand": "Britannia",
            "category": "Cookies",
        },
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    scan_id = resp.json()["data"]["id"]

    # 2. Upload Blurry Image -> Blocked
    blurry_bytes = create_test_blurry_image(blur_radius=10.0)
    files = {"files": ("bad_photo.jpg", blurry_bytes, "image/jpeg")}
    up_resp1 = await client.post(f"/api/v1/scans/{scan_id}/images", files=files, headers=headers)
    assert up_resp1.status_code == 200
    assert up_resp1.json()["data"][0]["image_quality"] == "BLURRY"

    # Confirm scan still holds the batch number
    check_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert check_resp.json()["data"]["batch_number"] == target_batch

    # 3. User Re-uploads clear image for same scan (or replaces image)
    # Remove bad image & upload clear image
    sharp_bytes = create_test_sharp_image()
    # Delete old bad image from DB
    old_imgs = await db_session.execute(select(ScanImage).where(ScanImage.scan_id == scan_id))
    for oi in old_imgs.scalars().all():
        await db_session.delete(oi)
    await db_session.commit()

    files2 = {"files": ("good_photo.jpg", sharp_bytes, "image/jpeg")}
    up_resp2 = await client.post(f"/api/v1/scans/{scan_id}/images", files=files2, headers=headers)
    assert up_resp2.status_code == 200
    assert up_resp2.json()["data"][0]["image_quality"] == "CLEAR"

    # 4. Now analysis succeeds
    analyze_resp = await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)
    assert analyze_resp.status_code == 200

    await run_scan_analysis_pipeline_async(scan_id, db=db_session)

    # 5. Verify batch number remains intact after analysis
    final_resp = await client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    final_data = final_resp.json()["data"]
    assert final_data["batch_number"] == target_batch
    assert len(final_data["declarations"]) > 0


@pytest.mark.asyncio
async def test_report_generation_blocked_on_unverified_blurry_scan(client: AsyncClient, test_users, auth_headers):
    """Test 8: Statutory report cannot be generated from an unanalyzed scan blocked by image quality."""
    headers = auth_headers("inspector")

    # 1. Create Scan
    create_payload = {
        "source": "physical_store",
        "location_name": "Test Store",
        "product_data": {"name": "Test Product", "brand": "Brand", "category": "Category"},
    }
    resp = await client.post("/api/v1/scans", json=create_payload, headers=headers)
    scan_id = resp.json()["data"]["id"]

    # 2. Upload Blurry Image
    blurry_bytes = create_test_blurry_image(blur_radius=12.0)
    await client.post(f"/api/v1/scans/{scan_id}/images", files={"files": ("blurry.jpg", blurry_bytes, "image/jpeg")}, headers=headers)

    # 3. Attempt to trigger analysis -> fails
    await client.post(f"/api/v1/scans/{scan_id}/analyze", headers=headers)

    # 4. Attempt to generate report -> fails / rejected
    rep_resp = await client.post(f"/api/v1/scans/{scan_id}/report", json={"notes": "Attempting report on blurry image"}, headers=headers)
    assert rep_resp.status_code in [400, 422, 500]
