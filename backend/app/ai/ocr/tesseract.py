import io
from PIL import Image
from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock
from app.core.exceptions import AIPipelineException


class TesseractOCRProvider(OCRProvider):
    """Local Tesseract OCR Provider fallback."""

    async def extract_text(self, image_bytes: bytes, **kwargs) -> OCRResult:
        try:
            import pytesseract
            
            image = Image.open(io.BytesIO(image_bytes))
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            blocks = []
            full_text_list = []
            total_conf = 0.0
            valid_words = 0

            n_boxes = len(data["text"])
            for i in range(n_boxes):
                word = data["text"][i].strip()
                conf = float(data["conf"][i])
                if word and conf > 0:
                    full_text_list.append(word)
                    total_conf += conf
                    valid_words += 1
                    
                    x = float(data["left"][i])
                    y = float(data["top"][i])
                    w = float(data["width"][i])
                    h = float(data["height"][i])
                    
                    blocks.append(
                        TextBlock(
                            text=word,
                            bounding_box={"x": x, "y": y, "w": w, "h": h},
                            confidence=conf / 100.0,
                            font_size_px=h,
                        )
                    )

            full_text = " ".join(full_text_list)
            avg_conf = (total_conf / (valid_words * 100.0)) if valid_words > 0 else 0.0

            return OCRResult(
                full_text=full_text,
                blocks=blocks,
                confidence=avg_conf,
                language="en",
            )
        except ImportError:
            raise AIPipelineException("pytesseract package is not installed. Use OCR_PROVIDER=mock.")
        except Exception as e:
            raise AIPipelineException(f"Tesseract OCR failed: {str(e)}")
