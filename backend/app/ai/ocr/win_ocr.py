import asyncio
import io
from typing import Any, Dict, List, Optional
from PIL import Image
from app.ai.ocr.base import OCRProvider, OCRResult, TextBlock
from app.core.exceptions import AIPipelineException


class WindowsMediaOCRProvider(OCRProvider):
    """
    Native Windows Media OCR Provider.
    Extracts real text and word bounding boxes directly from package image bytes
    using Windows 10/11 built-in OcrEngine via winocr.
    Supports multi-scale scanning for high accuracy on both headline text and fine print.
    """

    def __init__(self, default_lang: str = "en"):
        self.default_lang = default_lang

    async def extract_text(
        self,
        image_bytes: bytes,
        product_info: Optional[Dict[str, Any]] = None,
        image_width: int = 1000,
        image_height: int = 1000,
        **kwargs,
    ) -> OCRResult:
        if not image_bytes:
            return OCRResult(full_text="", blocks=[], confidence=0.0)

        try:
            import winocr
        except ImportError:
            raise AIPipelineException("winocr package is not installed.")

        try:
            orig_img = Image.open(io.BytesIO(image_bytes))
            if orig_img.mode != "RGB":
                orig_img = orig_img.convert("RGB")
        except Exception as e:
            raise AIPipelineException(f"Failed to decode image bytes for OCR: {str(e)}")

        orig_w, orig_h = orig_img.size

        # Multi-scale recognition to capture both normal and fine print (e.g. Net Weight in corner)
        scales = [1.0]
        if orig_w > 1200 or orig_h > 1200:
            scales = [1.0, 1.25]

        all_lines = []
        seen_texts = set()

        for scale in scales:
            if scale == 1.0:
                scan_img = orig_img
            else:
                new_size = (int(orig_w * scale), int(orig_h * scale))
                scan_img = orig_img.resize(new_size, Image.Resampling.LANCZOS)

            try:
                ocr_output = await winocr.recognize_pil(scan_img, lang=self.default_lang)
            except Exception:
                continue

            for line in ocr_output.lines:
                if not line.words:
                    continue
                line_str = " ".join([w.text for w in line.words]).strip()
                if not line_str:
                    continue

                min_x = min(w.bounding_rect.x for w in line.words) / scale
                min_y = min(w.bounding_rect.y for w in line.words) / scale
                max_x = max(w.bounding_rect.x + w.bounding_rect.width for w in line.words) / scale
                max_y = max(w.bounding_rect.y + w.bounding_rect.height for w in line.words) / scale

                # Normalization check to deduplicate across scales
                line_key = (line_str.lower(), round(min_y / 30.0))
                if line_key in seen_texts:
                    continue
                seen_texts.add(line_key)

                all_lines.append({
                    "text": line_str,
                    "x": float(max(0.0, min_x)),
                    "y": float(max(0.0, min_y)),
                    "w": float(min(orig_w - min_x, max_x - min_x)),
                    "h": float(min(orig_h - min_y, max_y - min_y)),
                    "font_size": float(max_y - min_y),
                })

        # Sort lines top-to-bottom, left-to-right
        all_lines.sort(key=lambda l: (l["y"], l["x"]))

        blocks: List[TextBlock] = []
        full_text_parts: List[str] = []

        for item in all_lines:
            full_text_parts.append(item["text"])
            blocks.append(
                TextBlock(
                    text=item["text"],
                    bounding_box={
                        "x": round(item["x"], 1),
                        "y": round(item["y"], 1),
                        "w": round(item["w"], 1),
                        "h": round(item["h"], 1),
                    },
                    confidence=0.96,
                    font_size_px=round(item["font_size"], 1),
                )
            )

        full_text = "\n".join(full_text_parts)
        avg_conf = 0.95 if blocks else 0.0

        return OCRResult(
            full_text=full_text,
            blocks=blocks,
            confidence=avg_conf,
            language="en",
        )
