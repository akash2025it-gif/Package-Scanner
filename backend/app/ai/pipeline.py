import uuid
from typing import Any, Dict, List, Optional
from app.ai.calibration import FontSizeCalibrator
from app.ai.detectors import get_region_detector
from app.ai.ocr import get_ocr_provider
from app.ai.preprocessor import ImagePreprocessor
from app.rules.engine import RuleEngine


class AIPipeline:
    """End-to-end AI Analysis Pipeline for Legal Metrology compliance checks."""

    def __init__(self, ocr_provider: Optional[Any] = None):
        self.preprocessor = ImagePreprocessor()
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
        Executes the full pipeline:
        1. Preprocess image
        2. Extract OCR words & blocks
        3. Detect declaration regions & bounding boxes
        4. Calibrate and calculate font size in mm
        5. Run LMPC 2011 rule engine
        """
        meta = scan_metadata or {}

        # 1. Preprocess image
        processed_bytes, width_px, height_px = self.preprocessor.preprocess(image_bytes)

        # 2. Extract OCR
        ocr_result = await self.ocr_provider.extract_text(
            processed_bytes,
            product_info=product_info,
            image_width=width_px,
            image_height=height_px,
        )

        # 3. Detect regions
        detected_regions = await self.region_detector.detect_regions(processed_bytes, ocr_result)

        # 4. Map detected regions to extracted fields & calibrate font size
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

        # 5. Execute LMPC Rule Engine
        declarations = self.rule_engine.evaluate_scan(
            extracted_fields=extracted_fields,
            scan_metadata=meta,
        )

        overall_status = self.rule_engine.calculate_overall_status(declarations)

        return {
            "image_dimensions": {"width": width_px, "height": height_px},
            "ocr_full_text": ocr_result.full_text,
            "overall_status": overall_status,
            "declarations": declarations,
        }
