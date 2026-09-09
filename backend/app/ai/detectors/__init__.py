from app.ai.detectors.base import DetectedRegion, RegionDetector
from app.ai.detectors.heuristic import HeuristicRegionDetector
from app.ai.detectors.yolo_service import YOLOServiceRegionDetector
from app.core.config import settings

_detector_instance: RegionDetector = None


def get_region_detector() -> RegionDetector:
    global _detector_instance
    if _detector_instance is None:
        detector_name = settings.REGION_DETECTOR_PROVIDER.lower()
        if detector_name == "yolo_service":
            _detector_instance = YOLOServiceRegionDetector()
        else:
            _detector_instance = HeuristicRegionDetector()
    return _detector_instance


__all__ = [
    "DetectedRegion",
    "RegionDetector",
    "HeuristicRegionDetector",
    "YOLOServiceRegionDetector",
    "get_region_detector",
]
