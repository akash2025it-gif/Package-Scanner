import os
import pytest
import numpy as np
import cv2
from PIL import Image

from app.ai.barcode_detector import BarcodeQRDetector
from app.ai.preprocessor import ImagePreprocessor
from app.ai.pipeline import AIPipeline
from app.rules.engine import RuleEngine
from app.rules.config_loader import RuleConfigLoader


def test_barcode_qr_detector_blank_image():
    detector = BarcodeQRDetector()
    # Create blank white image bytes
    img = np.ones((400, 400, 3), dtype=np.uint8) * 255
    _, buf = cv2.imencode(".jpg", img)
    res = detector.detect_and_decode(buf.tobytes())

    assert res["qr_detected"] is False
    assert res["barcode_detected"] is False
    assert res["total_detected"] == 0
    assert len(res["items"]) == 0
    assert "A QR code or barcode is supplementary evidence" in res["legal_disclaimer"]


def test_url_safety_validation():
    # Safe public URL
    safe_res = BarcodeQRDetector.validate_url_safety("https://www.example.gov.in/verify?id=123")
    assert safe_res["is_url"] is True
    assert safe_res["is_safe"] is True

    # Private loopback address blocked
    unsafe_loopback = BarcodeQRDetector.validate_url_safety("http://127.0.0.1:8000/admin")
    assert unsafe_loopback["is_url"] is True
    assert unsafe_loopback["is_safe"] is False
    assert "private or internal" in unsafe_loopback["reason"]

    # Direct raw IP blocked
    unsafe_ip = BarcodeQRDetector.validate_url_safety("http://192.168.1.1/device")
    assert unsafe_ip["is_url"] is True
    assert unsafe_ip["is_safe"] is False

    # Disallowed javascript scheme
    unsafe_js = BarcodeQRDetector.validate_url_safety("javascript:alert(1)")
    assert unsafe_js["is_url"] is False


def test_image_preprocessor_deskew_and_clahe():
    # Create simple test image with high-contrast text lines
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    cv2.putText(img, "LEGAL METROLOGY LMPC 2011", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "MRP RS. 150.00 INCL TAXES", (50, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    _, buf = cv2.imencode(".jpg", img)

    proc_bytes, w, h, meta = ImagePreprocessor.preprocess(buf.tobytes())
    assert len(proc_bytes) > 0
    assert w >= 500
    assert h >= 500
    assert "skew_angle_deg" in meta
    assert "scale_factor" in meta


@pytest.mark.asyncio
async def test_ai_pipeline_with_real_image():
    from app.ai.ocr.mock import MockOCRProvider
    from PIL import Image, ImageDraw
    import io

    # Generate genuine packaging label image in memory
    img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 580, 780], outline=(0, 0, 0), width=3)
    draw.text((40, 50), "BRAND: PACKCHECK QUALITY FLOUR", fill=(0, 0, 0))
    draw.text((40, 100), "MRP Rs. 240.00 (INCL. OF ALL TAXES)", fill=(0, 0, 0))
    draw.text((40, 150), "NET QUANTITY: 1 kg", fill=(0, 0, 0))
    draw.text((40, 200), "MFD: 10/2026", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    img_bytes = buf.getvalue()

    pipeline = AIPipeline(ocr_provider=MockOCRProvider())
    result = await pipeline.analyze_image_bytes(
        image_bytes=img_bytes,
        scan_metadata={"source": "test_suite"},
    )

    assert "image_dimensions" in result
    assert "barcode_info" in result
    assert "declarations" in result
    assert "overall_status" in result
    assert result["overall_status"] in ("compliant", "non_compliant", "needs_review")

    # Check barcode info structure
    b_info = result["barcode_info"]
    assert "qr_detected" in b_info
    assert "barcode_detected" in b_info
    assert "legal_disclaimer" in b_info


def test_rule_engine_deterministic_statuses():
    engine = RuleEngine()
    
    # 1. Compliant Net Quantity
    valid_net_q = {
        "net_quantity": {
            "text": "Net Qty: 500 g",
            "bounding_box": {"x": 50, "y": 100, "w": 120, "h": 25},
            "confidence": 0.95,
        }
    }
    evals = engine.evaluate_scan(valid_net_q)
    net_q_eval = next((e for e in evals if e["field_type"] == "net_quantity"), None)
    assert net_q_eval is not None
    assert net_q_eval["is_compliant"] is True
    assert net_q_eval["is_present"] is True

    # 2. Non-compliant MRP (missing taxes)
    invalid_mrp = {
        "mrp": {
            "text": "MRP Rs. 150.00",
            "bounding_box": {"x": 50, "y": 150, "w": 120, "h": 25},
            "confidence": 0.92,
        }
    }
    evals_mrp = engine.evaluate_scan(invalid_mrp)
    mrp_eval = next((e for e in evals_mrp if e["field_type"] == "mrp"), None)
    assert mrp_eval is not None
    assert mrp_eval["is_compliant"] is False
    assert mrp_eval["severity"] in ("critical", "major")
