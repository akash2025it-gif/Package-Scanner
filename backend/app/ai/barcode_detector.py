import re
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None


class BarcodeQRDetector:
    """
    Real QR Code and 1D Barcode Detection Engine using OpenCV.
    Detects QR codes and retail product barcodes (EAN-13, UPC-A, Code 128, etc.).
    Extracts decoded content, bounding box locations, formats, and validates URL safety.
    """

    def __init__(self):
        if cv2 is not None:
            self.qr_detector = cv2.QRCodeDetector()
            try:
                self.barcode_detector = cv2.barcode.BarcodeDetector()
            except Exception:
                self.barcode_detector = None
        else:
            self.qr_detector = None
            self.barcode_detector = None

    @staticmethod
    def _is_url(text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        stripped = text.strip()
        return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", stripped, re.IGNORECASE))

    @classmethod
    def validate_url_safety(cls, url_str: str) -> Dict[str, Any]:
        """
        Validates URL structure and safety before exposing navigation.
        Blocks suspicious schemes, IP-based URLs, and local loopbacks.
        """
        if not cls._is_url(url_str):
            return {
                "is_url": False,
                "is_safe": False,
                "reason": "Not a standard HTTP/HTTPS web address."
            }

        try:
            parsed = urllib.parse.urlparse(url_str.strip())
            scheme = (parsed.scheme or "").lower()
            hostname = (parsed.hostname or "").lower()

            if scheme not in ("http", "https"):
                return {
                    "is_url": True,
                    "is_safe": False,
                    "reason": f"Disallowed scheme: '{scheme}'. Only HTTPS/HTTP permitted."
                }

            # Guard against local/private addresses
            if hostname in ("localhost", "127.0.0.1", "0.0.0.0") or hostname.startswith("192.168.") or hostname.startswith("10."):
                return {
                    "is_url": True,
                    "is_safe": False,
                    "reason": "Points to a private or internal network address."
                }

            # Check for suspicious numeric-only domains or credential patterns
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", hostname):
                return {
                    "is_url": True,
                    "is_safe": False,
                    "reason": "Direct IP addresses are blocked for safety."
                }

            if "@" in (parsed.netloc or ""):
                return {
                    "is_url": True,
                    "is_safe": False,
                    "reason": "URL contains embedded user authentication credentials."
                }

            return {
                "is_url": True,
                "is_safe": True,
                "scheme": scheme,
                "domain": hostname,
                "url": url_str.strip(),
                "reason": "Standard public HTTPS/HTTP domain."
            }
        except Exception as e:
            return {
                "is_url": True,
                "is_safe": False,
                "reason": f"URL parsing error: {str(e)}"
            }

    @staticmethod
    def _points_to_bbox(points: Any, img_w: int, img_h: int) -> Dict[str, float]:
        """Converts OpenCV corner points to normalized or pixel bounding box."""
        if points is None or len(points) == 0:
            return {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}

        pts = points.reshape(-1, 2)
        x_min = float(np.min(pts[:, 0]))
        y_min = float(np.min(pts[:, 1]))
        x_max = float(np.max(pts[:, 0]))
        y_max = float(np.max(pts[:, 1]))

        w = max(0.0, x_max - x_min)
        h = max(0.0, y_max - y_min)

        return {
            "x": round(max(0.0, x_min), 1),
            "y": round(max(0.0, y_min), 1),
            "w": round(w, 1),
            "h": round(h, 1),
            "width": round(w, 1),
            "height": round(h, 1)
        }

    def detect_and_decode(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Processes packaging image bytes and performs full QR and Barcode inspection.
        Returns detailed evidence structure.
        """
        if not image_bytes:
            return {
                "qr_detected": False,
                "barcode_detected": False,
                "items": [],
                "summary": "No image bytes provided.",
                "legal_disclaimer": "A QR code or barcode is supplementary evidence and does not constitute proof of legal compliance."
            }

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return {
                    "qr_detected": False,
                    "barcode_detected": False,
                    "items": [],
                    "summary": "Failed to decode image data into valid image array.",
                    "legal_disclaimer": "A QR code or barcode is supplementary evidence and does not constitute proof of legal compliance."
                }
        except Exception as e:
            return {
                "qr_detected": False,
                "barcode_detected": False,
                "items": [],
                "summary": f"Image decoding exception: {str(e)}",
                "legal_disclaimer": "A QR code or barcode is supplementary evidence and does not constitute proof of legal compliance."
            }

        img_h, img_w = img.shape[:2]
        detected_items: List[Dict[str, Any]] = []

        # Optimize resolution for fast QR/barcode detection if image is large
        detect_img = img
        scale = 1.0
        if max(img_h, img_w) > 1200:
            scale = 1200.0 / float(max(img_h, img_w))
            new_w, new_h = int(img_w * scale), int(img_h * scale)
            detect_img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        # 1. Detect QR Codes
        try:
            # Check multi-QR first
            retval, decoded_info, points, straight_qrcode = self.qr_detector.detectAndDecodeMulti(detect_img)
            if retval and decoded_info:
                for idx, text in enumerate(decoded_info):
                    if text and text.strip():
                        pts = points[idx] if points is not None and len(points) > idx else None
                        if pts is not None and scale != 1.0:
                            pts = pts / scale
                        bbox = self._points_to_bbox(pts, img_w, img_h)
                        url_check = self.validate_url_safety(text)
                        detected_items.append({
                            "type": "QR_CODE",
                            "format": "QR_CODE",
                            "raw_content": text.strip(),
                            "is_url": url_check["is_url"],
                            "url_safety": url_check,
                            "bounding_box": bbox,
                            "confidence": 1.0
                        })
            else:
                # Single QR fallback
                text, points, straight_qrcode = self.qr_detector.detectAndDecode(detect_img)
                if text and text.strip():
                    if points is not None and scale != 1.0:
                        points = points / scale
                    bbox = self._points_to_bbox(points, img_w, img_h)
                    url_check = self.validate_url_safety(text)
                    detected_items.append({
                        "type": "QR_CODE",
                        "format": "QR_CODE",
                        "raw_content": text.strip(),
                        "is_url": url_check["is_url"],
                        "url_safety": url_check,
                        "bounding_box": bbox,
                        "confidence": 1.0
                    })
        except Exception:
            pass

        # 2. Detect 1D Barcodes
        if self.barcode_detector is not None:
            try:
                decoded_info, barcode_type, points = self.barcode_detector.detectAndDecode(detect_img)
                if decoded_info:
                    infos = [decoded_info] if isinstance(decoded_info, str) else list(decoded_info)
                    types = [barcode_type] if isinstance(barcode_type, (str, int)) else list(barcode_type or [])
                    
                    for idx, b_text in enumerate(infos):
                        if b_text and str(b_text).strip():
                            b_type = str(types[idx]) if idx < len(types) else "EAN/UPC"
                            pts = points[idx] if points is not None and len(points) > idx else None
                            if pts is not None and scale != 1.0:
                                pts = pts / scale
                            bbox = self._points_to_bbox(pts, img_w, img_h)
                            detected_items.append({
                                "type": "BARCODE",
                                "format": b_type,
                                "raw_content": str(b_text).strip(),
                                "is_url": False,
                                "url_safety": {"is_url": False, "is_safe": False, "reason": "Standard product barcode"},
                                "bounding_box": bbox,
                                "confidence": 0.95
                            })
            except Exception:
                pass

        qr_count = sum(1 for item in detected_items if item["type"] == "QR_CODE")
        barcode_count = sum(1 for item in detected_items if item["type"] == "BARCODE")

        summary_parts = []
        if qr_count > 0:
            summary_parts.append(f"{qr_count} QR code(s) detected")
        if barcode_count > 0:
            summary_parts.append(f"{barcode_count} product barcode(s) detected")
        if not detected_items:
            summary_parts.append("No QR code or barcode detected on package image")

        return {
            "qr_detected": qr_count > 0,
            "barcode_detected": barcode_count > 0,
            "total_detected": len(detected_items),
            "items": detected_items,
            "summary": "; ".join(summary_parts) + ".",
            "legal_disclaimer": "IMPORTANT: A QR code or barcode is supplementary evidence and does not constitute statutory proof of compliance under Legal Metrology (Packaged Commodities) Rules, 2011."
        }
