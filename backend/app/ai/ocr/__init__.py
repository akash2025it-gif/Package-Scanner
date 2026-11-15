from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock
from app.ai.ocr.real_ocr import RealHybridOCRProvider
from app.ai.ocr.google_vision import GoogleVisionOCRProvider
from app.ai.ocr.tesseract import TesseractOCRProvider
from app.ai.ocr.win_ocr import WindowsMediaOCRProvider
from app.ai.ocr.mock import MockOCRProvider
from app.core.config import settings

_ocr_instance: OCRProvider = None


def get_ocr_provider() -> OCRProvider:
    global _ocr_instance
    import os
    provider_name = (os.environ.get("OCR_PROVIDER") or settings.OCR_PROVIDER or "real").lower()
    if _ocr_instance is None or getattr(_ocr_instance, "_provider_name", None) != provider_name:
        if provider_name == "google_vision":
            _ocr_instance = GoogleVisionOCRProvider()
        elif provider_name == "tesseract":
            _ocr_instance = TesseractOCRProvider()
        elif provider_name in ("windows_media", "winocr", "native"):
            _ocr_instance = WindowsMediaOCRProvider()
        elif provider_name == "mock":
            _ocr_instance = MockOCRProvider()
        else:
            # Default production real OCR provider with automatic engine selection
            _ocr_instance = RealHybridOCRProvider()
        _ocr_instance._provider_name = provider_name
    return _ocr_instance


__all__ = [
    "OCRProvider",
    "OCRResult",
    "TextBlock",
    "RealHybridOCRProvider",
    "GoogleVisionOCRProvider",
    "TesseractOCRProvider",
    "WindowsMediaOCRProvider",
    "MockOCRProvider",
    "get_ocr_provider",
]
