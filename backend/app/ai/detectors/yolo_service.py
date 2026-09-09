from typing import List, Optional
import httpx
from app.ai.detectors.base import DetectedRegion, RegionDetector
from app.ai.ocr.base import OCRResult
from app.core.config import settings
from app.core.exceptions import AIPipelineException


class YOLOServiceRegionDetector(RegionDetector):
    """Inference client for external YOLOv8/Detectron2 Region Detection Microservice."""

    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or settings.YOLO_SERVICE_URL

    async def detect_regions(self, image_bytes: bytes, ocr_result: Optional[OCRResult] = None) -> List[DetectedRegion]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
                response = await client.post(self.endpoint_url, files=files)
                
                if response.status_code != 200:
                    # Fallback to heuristic detector if YOLO service is unreachable
                    from app.ai.detectors.heuristic import HeuristicRegionDetector
                    return await HeuristicRegionDetector().detect_regions(image_bytes, ocr_result)

                data = response.json()
                regions = []
                for item in data.get("predictions", []):
                    regions.append(
                        DetectedRegion(
                            field_type=item["class_name"],
                            bounding_box=item["bbox"],
                            confidence=item.get("confidence", 0.9),
                            text=item.get("text"),
                            font_size_px=item.get("font_size_px"),
                        )
                    )
                return regions
        except Exception:
            # Fallback gracefully to heuristic detector
            from app.ai.detectors.heuristic import HeuristicRegionDetector
            return await HeuristicRegionDetector().detect_regions(image_bytes, ocr_result)
