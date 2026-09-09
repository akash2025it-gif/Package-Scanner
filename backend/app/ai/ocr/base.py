from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextBlock:
    text: str
    bounding_box: Dict[str, float]  # {"x": float, "y": float, "w": float, "h": float}
    confidence: float
    font_size_px: Optional[float] = None


@dataclass
class OCRResult:
    full_text: str
    blocks: List[TextBlock] = field(default_factory=list)
    confidence: float = 0.0
    language: str = "en"
    raw_response: Optional[Dict[str, Any]] = None


class OCRProvider(ABC):
    @abstractmethod
    async def extract_text(
        self,
        image_bytes: bytes,
        product_info: Optional[Dict[str, Any]] = None,
        image_width: int = 1000,
        image_height: int = 1000,
        **kwargs,
    ) -> OCRResult:
        """Extracts text, words, and bounding boxes from image bytes."""
        pass

