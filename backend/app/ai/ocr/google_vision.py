import os
from typing import Optional
from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock
from app.core.config import settings
from app.core.exceptions import AIPipelineException


class GoogleVisionOCRProvider(OCRProvider):
    """Google Cloud Vision API OCR Provider."""

    def __init__(self, credentials_path: Optional[str] = None):
        cred = credentials_path or settings.GOOGLE_APPLICATION_CREDENTIALS
        if cred and os.path.exists(cred):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred

    async def extract_text(self, image_bytes: bytes, **kwargs) -> OCRResult:
        try:
            from google.cloud import vision
            client = vision.ImageAnnotatorClient()
            
            image = vision.Image(content=image_bytes)
            response = client.text_detection(image=image)
            
            if response.error.message:
                raise AIPipelineException(f"Google Vision API error: {response.error.message}")

            texts = response.text_annotations
            if not texts:
                return OCRResult(full_text="", blocks=[], confidence=0.0)

            full_text = texts[0].description
            blocks = []

            for annotation in texts[1:]:
                vertices = annotation.bounding_poly.vertices
                xs = [v.x for v in vertices if v.x is not None]
                ys = [v.y for v in vertices if v.y is not None]
                
                if xs and ys:
                    x = min(xs)
                    y = min(ys)
                    w = max(xs) - x
                    h = max(ys) - y
                    blocks.append(
                        TextBlock(
                            text=annotation.description,
                            bounding_box={"x": float(x), "y": float(y), "w": float(w), "h": float(h)},
                            confidence=0.95,
                            font_size_px=float(h),
                        )
                    )

            return OCRResult(
                full_text=full_text,
                blocks=blocks,
                confidence=0.95,
                language="en",
            )
        except ImportError:
            raise AIPipelineException("google-cloud-vision package is not installed. Please install it or use OCR_PROVIDER=mock.")
        except Exception as e:
            raise AIPipelineException(f"Failed to perform Google Vision OCR: {str(e)}")
