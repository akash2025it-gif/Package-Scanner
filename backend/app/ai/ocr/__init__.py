from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock
from app.ai.ocr.mock import MockOCRProvider
from app.ai.ocr.google_vision import GoogleVisionOCRProvider
from app.ai.ocr.tesseract import TesseractOCRProvider
from app.ai.ocr.win_ocr import WindowsMediaOCRProvider
from app.core.config import settings

_ocr_instance: OCRProvider = None


def get_ocr_provider() -> OCRProvider:
    global _ocr_instance
    import os
    provider_name = (os.environ.get("OCR_PROVIDER") or settings.OCR_PROVIDER or "").lower()
    if _ocr_instance is None or getattr(_ocr_instance, "_provider_name", None) != provider_name:
        if provider_name == "mock":
            _ocr_instance = MockOCRProvider()
        elif provider_name == "google_vision":
            _ocr_instance = GoogleVisionOCRProvider()
        elif provider_name == "tesseract":
            _ocr_instance = TesseractOCRProvider()
        elif provider_name in ("windows_media", "winocr", "native"):
            _ocr_instance = WindowsMediaOCRProvider()
        else:
            # Auto-detect native Windows OCR if available, otherwise fallback
            try:
                import winocr
                _ocr_instance = WindowsMediaOCRProvider()
            except ImportError:
                _ocr_instance = MockOCRProvider()
        _ocr_instance._provider_name = provider_name
    return _ocr_instance


__all__ = [
    "OCRProvider",
    "OCRResult",
    "TextBlock",
    "MockOCRProvider",
    "GoogleVisionOCRProvider",
    "TesseractOCRProvider",
    "WindowsMediaOCRProvider",
    "get_ocr_provider",
]
