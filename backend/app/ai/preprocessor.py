import io
import math
from typing import Tuple, Dict, Any, Optional
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


class ImagePreprocessor:
    """
    Advanced OpenCV & Pillow Packaging Image Preprocessor.
    Applies:
    1. EXIF orientation correction.
    2. Adaptive resizing preserving aspect ratio and text clarity.
    3. Deskewing & rotation correction via minimum-area bounding box of text contours.
    4. Contrast Limited Adaptive Histogram Equalization (CLAHE).
    5. Bilateral noise filtering preserving sharp font edges.
    6. Extraction of clean RGB and thresholded text masks.
    """

    @staticmethod
    def deskew_image(cv_img: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detects text skew angle and rotates image to align text horizontally.
        Returns: (deskewed_image, angle_degrees)
        """
        try:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
            # Downsample thumbnail for fast and robust angle estimation
            small = cv2.resize(gray, (0, 0), fx=0.25, fy=0.25)
            thresh = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

            coords = np.column_stack(np.where(thresh > 0))
            if coords.shape[0] < 30:
                return cv_img, 0.0

            # Subsample points for instant O(1) convex hull
            if coords.shape[0] > 500:
                coords = coords[:: coords.shape[0] // 500]

            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            # Ignore tiny negligible tilt
            if abs(angle) < 0.6 or abs(angle) > 45.0:
                return cv_img, 0.0

            (h, w) = cv_img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(
                cv_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            return rotated, round(float(angle), 2)
        except Exception:
            return cv_img, 0.0

    @classmethod
    def preprocess(cls, image_bytes: bytes) -> Tuple[bytes, int, int, Dict[str, Any]]:
        """
        Takes raw packaging image bytes and produces optimized, deskewed, contrast-enhanced image.
        Returns: (processed_bytes, width, height, metadata)
        """
        if not image_bytes:
            return image_bytes, 0, 0, {"error": "Empty bytes"}

        try:
            # 1. Load via Pillow for EXIF orientation handling
            pil_img = Image.open(io.BytesIO(image_bytes))
            pil_img = ImageOps.exif_transpose(pil_img)
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            orig_w, orig_h = pil_img.size

            # 2. Convert to OpenCV BGR
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            # 3. Dynamic resizing if image is excessively large or small
            max_dimension = 2400
            min_dimension = 800
            scale = 1.0
            if max(orig_w, orig_h) > max_dimension:
                scale = max_dimension / float(max(orig_w, orig_h))
                new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                cv_img = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            elif min(orig_w, orig_h) < min_dimension:
                scale = min_dimension / float(min(orig_w, orig_h))
                new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                cv_img = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

            # 4. Deskewing
            deskewed_img, skew_angle = cls.deskew_image(cv_img)

            # 5. Contrast Enhancement & Edge-preserving denoising
            # Convert to LAB for luminance channel processing
            lab = cv2.cvtColor(deskewed_img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)

            # Apply CLAHE to L-channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)

            merged_lab = cv2.merge((cl, a_channel, b_channel))
            enhanced_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

            # Light bilateral filter to reduce camera sensor noise while keeping text boundaries sharp
            denoised = cv2.bilateralFilter(enhanced_bgr, d=5, sigmaColor=35, sigmaSpace=35)

            # Convert back to RGB for Pillow output
            final_rgb = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB)
            final_pil = Image.fromarray(final_rgb)

            # Output buffer
            out_buf = io.BytesIO()
            final_pil.save(out_buf, format="JPEG", quality=94, optimize=True)
            res_bytes = out_buf.getvalue()

            fw, fh = final_pil.size
            return res_bytes, fw, fh, {
                "original_dimensions": {"width": orig_w, "height": orig_h},
                "processed_dimensions": {"width": fw, "height": fh},
                "skew_angle_deg": skew_angle,
                "scale_factor": round(scale, 3)
            }
        except Exception as e:
            # Safe fallback if advanced processing encounters unknown format
            return image_bytes, 1000, 1000, {"error": str(e), "fallback": True}
