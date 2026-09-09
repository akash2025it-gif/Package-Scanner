from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional
from app.ai.ocr.base import OCRResult


@dataclass
class DetectedRegion:
    field_type: str
    bounding_box: Dict[str, float]  # {"x": float, "y": float, "w": float, "h": float}
    confidence: float
    text: Optional[str] = None
    font_size_px: Optional[float] = None


class RegionDetector(ABC):
    @abstractmethod
    async def detect_regions(self, image_bytes: bytes, ocr_result: Optional[OCRResult] = None) -> List[DetectedRegion]:
        """Localizes label declaration fields on the package image."""
        pass
