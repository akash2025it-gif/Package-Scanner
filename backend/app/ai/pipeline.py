import uuid
from typing import Any, Dict, List, Optional
from app.ai.barcode_detector import BarcodeQRDetector
from app.ai.calibration import FontSizeCalibrator
from app.ai.detectors import get_region_detector
from app.ai.ocr import get_ocr_provider
from app.ai.preprocessor import ImagePreprocessor
from app.rules.engine import RuleEngine


class AIPipeline:
    """End-to-end AI Analysis Pipeline for Legal Metrology compliance checks."""

    def __init__(self, ocr_provider: Optional[Any] = None):
        self.preprocessor = ImagePreprocessor()
        self.barcode_detector = BarcodeQRDetector()
        self.ocr_provider = ocr_provider or get_ocr_provider()
        self.region_detector = get_region_detector()
        self.rule_engine = RuleEngine()

    async def analyze_image_bytes(
        self,
        image_bytes: bytes,
        scan_metadata: Optional[Dict[str, Any]] = None,
        physical_pack_height_mm: Optional[float] = None,
        product_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the full packaging analysis pipeline:
        1. QR Code and 1D Barcode Detection
        2. Preprocess image (resizing, deskewing, contrast CLAHE, edge denoising)
        3. Extract OCR words & blocks with coordinates and confidence
        4. Detect declaration regions & bounding boxes
        5. Calibrate font size in mm against physical packaging scale if available
        6. Run deterministic LMPC 2011 rule engine
        7. Cross-check QR/barcode evidence against package text
        """
        meta = scan_metadata or {}

        # 1. Detect QR code and product barcode
        barcode_result = self.barcode_detector.detect_and_decode(image_bytes)

        # 2. Preprocess image
        prep_res = self.preprocessor.preprocess(image_bytes)
        if len(prep_res) == 4:
            processed_bytes, width_px, height_px, prep_meta = prep_res
        else:
            processed_bytes, width_px, height_px = prep_res[:3]
            prep_meta = {}

        # 3. Extract OCR text & bounding boxes
        ocr_result = await self.ocr_provider.extract_text(
            processed_bytes,
            product_info=product_info,
            image_width=width_px,
            image_height=height_px,
        )

        # 4. Detect declaration regions from OCR layout
        detected_regions = await self.region_detector.detect_regions(processed_bytes, ocr_result)

        # 5. Map detected regions to extracted fields & calibrate font size
        extracted_fields: Dict[str, Dict[str, Any]] = {}
        for region in detected_regions:
            box_h = region.bounding_box.get("h", 30.0)

            # Calibrate font size
            calib_res = FontSizeCalibrator.estimate_font_size(
                box_height_px=box_h,
                image_height_px=height_px,
                physical_pack_height_mm=physical_pack_height_mm,
            )

            extracted_fields[region.field_type] = {
                "text": region.text,
                "bounding_box": region.bounding_box,
                "confidence": region.confidence,
                "font_size_mm": calib_res.estimated_height_mm,
                "font_size_confidence": calib_res.confidence,
                "calibration_method": calib_res.method,
            }

        # Cross-reference QR/barcode evidence
        if barcode_result.get("items"):
            for item in barcode_result["items"]:
                # If a barcode number was found and not yet in fields, attach as supplementary evidence
                if item["type"] == "BARCODE" and "barcode" not in extracted_fields:
                    extracted_fields["barcode"] = {
                        "text": item["raw_content"],
                        "bounding_box": item["bounding_box"],
                        "confidence": item["confidence"],
                        "format": item["format"],
                        "source": "opencv_barcode_detector",
                    }
                elif item["type"] == "QR_CODE" and "qr_code" not in extracted_fields:
                    extracted_fields["qr_code"] = {
                        "text": item["raw_content"],
                        "bounding_box": item["bounding_box"],
                        "confidence": item["confidence"],
                        "is_url": item["is_url"],
                        "url_safety": item.get("url_safety", {}),
                        "source": "opencv_qr_detector",
                    }

        # 6. Execute LMPC Rule Engine
        combined_meta = dict(meta)
        combined_meta["barcode_info"] = barcode_result
        combined_meta["ocr_full_text"] = ocr_result.full_text
        combined_meta["full_text"] = ocr_result.full_text
        combined_meta["label_text"] = ocr_result.full_text

        declarations = self.rule_engine.evaluate_scan(
            extracted_fields=extracted_fields,
            scan_metadata=combined_meta,
        )

        overall_status = self.rule_engine.calculate_overall_status(declarations)

        return {
            "image_dimensions": {"width": width_px, "height": height_px},
            "preprocessing": prep_meta,
            "barcode_info": barcode_result,
            "ocr_full_text": ocr_result.full_text,
            "overall_status": overall_status,
            "declarations": declarations,
        }
