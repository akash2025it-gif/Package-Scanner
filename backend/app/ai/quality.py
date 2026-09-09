from datetime import datetime, timezone
import io
import math
from typing import Any, Dict, Optional
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from app.core.config import settings


class ImageQualityValidator:
    """
    Evaluates image quality, blur, and sharpness using Laplacian variance.
    Guarantees that blurry, low-resolution, or corrupted images are halted BEFORE
    reaching OCR or AI compliance pipelines.
    """

    DEFAULT_BLUR_THRESHOLD: float = settings.BLUR_THRESHOLD
    MIN_DIMENSION: int = settings.MIN_IMAGE_DIMENSION

    @classmethod
    def calculate_laplacian_variance(cls, image: Image.Image) -> float:
        """
        Calculates the sharpness score via the variance of the 2D discrete Laplacian operator.
        sharpness_score = Var(Laplacian(grayscale_image))

        Uses standard 5-point discrete Laplacian convolution kernel:
        [ 0,  1,  0 ]
        [ 1, -4,  1 ]
        [ 0,  1,  0 ]
        """
        # Convert to grayscale for single-channel intensity analysis
        gray = image.convert("L")
        arr = np.asarray(gray, dtype=np.float64)

        # Minimum matrix dimension guard
        if arr.shape[0] < 3 or arr.shape[1] < 3:
            return 0.0

        # Discrete 2D Laplacian operator across interior pixels
        lap = (
            arr[:-2, 1:-1]
            + arr[2:, 1:-1]
            + arr[1:-1, :-2]
            + arr[1:-1, 2:]
            - 4.0 * arr[1:-1, 1:-1]
        )

        var = float(lap.var())
        if math.isnan(var) or math.isinf(var):
            return 0.0
        return round(max(0.0, var), 2)

    @classmethod
    def validate_image_bytes(
        cls,
        image_bytes: bytes,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Validates raw image bytes for:
        1. Non-empty and readable image stream
        2. Minimum pixel dimensions
        3. Real Laplacian variance / sharpness calculation against configured threshold

        Returns structured quality assessment:
        - image_quality: "CLEAR" | "BLURRY" | "LOW_QUALITY" | "FAILED"
        - sharpness_score: float (actual computed variance)
        - threshold: float
        - can_analyze: bool
        - width: int
        - height: int
        - reason: str
        - message: str
        - validation_timestamp: str (ISO-8601 UTC)
        """
        thresh = threshold if threshold is not None else settings.BLUR_THRESHOLD
        now_iso = datetime.now(timezone.utc).isoformat()

        if not image_bytes or len(image_bytes) == 0:
            return {
                "image_quality": "FAILED",
                "sharpness_score": 0.0,
                "threshold": thresh,
                "can_analyze": False,
                "width": 0,
                "height": 0,
                "reason": "EMPTY_IMAGE",
                "message": "The uploaded image file is empty or missing. Please provide a valid packaging photo.",
                "validation_timestamp": now_iso,
            }

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # Auto-orient EXIF metadata if present
            image = ImageOps.exif_transpose(image)
            width, height = image.size

            # Check minimum dimensions
            if width < cls.MIN_DIMENSION or height < cls.MIN_DIMENSION:
                return {
                    "image_quality": "LOW_QUALITY",
                    "sharpness_score": 0.0,
                    "threshold": thresh,
                    "can_analyze": False,
                    "width": width,
                    "height": height,
                    "reason": "DIMENSIONS_TOO_SMALL",
                    "message": f"Image dimensions ({width}x{height} px) are below the minimum required resolution ({cls.MIN_DIMENSION}x{cls.MIN_DIMENSION} px) for reliable text extraction.",
                    "validation_timestamp": now_iso,
                }

            # Calculate actual mathematical Laplacian variance
            score = cls.calculate_laplacian_variance(image)
            is_clear = score >= thresh
            quality = "CLEAR" if is_clear else "BLURRY"

            if is_clear:
                message = "Image quality is clear and verified for OCR and compliance analysis."
                reason = "CLEAR"
            else:
                message = "The uploaded image is too blurry for reliable text extraction and compliance analysis. Please re-upload a clearer image or rescan the product."
                reason = "IMAGE_TOO_BLURRY"

            return {
                "image_quality": quality,
                "sharpness_score": score,
                "threshold": thresh,
                "can_analyze": is_clear,
                "width": width,
                "height": height,
                "reason": reason,
                "message": message,
                "validation_timestamp": now_iso,
            }

        except Exception as exc:
            return {
                "image_quality": "FAILED",
                "sharpness_score": 0.0,
                "threshold": thresh,
                "can_analyze": False,
                "width": 0,
                "height": 0,
                "reason": "CORRUPTED_OR_UNSUPPORTED",
                "message": f"Image quality could not be validated due to processing error: {str(exc)}. Please re-upload or rescan the product.",
                "validation_timestamp": now_iso,
            }

    @staticmethod
    def create_blurred_copy(image_bytes: bytes, radius: float = 6.0) -> bytes:
        """Utility for testing: generates an authentically blurred JPEG copy of an image."""
        img = Image.open(io.BytesIO(image_bytes))
        blurred = img.filter(ImageFilter.GaussianBlur(radius=radius))
        out = io.BytesIO()
        blurred.save(out, format="JPEG", quality=80)
        return out.getvalue()
