from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class FontSizeEstimationResult:
    estimated_height_mm: float
    confidence: str  # "high", "medium", "low"
    pixel_height: float
    pixels_per_mm: float
    method: str

    @property
    def is_calibrated(self) -> bool:
        return self.method in ("reference_marker_calibration", "physical_dimension_ratio")

    @property
    def display_text(self) -> str:
        if self.is_calibrated:
            return f"{self.estimated_height_mm:.2f} mm"
        return f"Estimated visual size: approximately {self.estimated_height_mm:.1f} mm — subject to manual verification"


class FontSizeCalibrator:
    """Estimates font/numeral physical height in millimeters from pixel bounding boxes."""

    # 1 inch = 25.4 mm. Standard print resolution is ~300 DPI, typical phone photo of 15cm pack is ~10-15 px/mm.
    DEFAULT_PIXELS_PER_MM = 11.81  # ~300 DPI (300 / 25.4)

    @classmethod
    def estimate_font_size(
        cls,
        box_height_px: float,
        image_height_px: int,
        physical_pack_height_mm: Optional[float] = None,
        reference_marker_px_per_mm: Optional[float] = None,
        line_count: int = 1,
    ) -> FontSizeEstimationResult:
        """
        Estimates letter/numeral height in mm.
        Uses reference marker or physical package height if supplied, else estimates with low confidence.
        """
        single_line_px = box_height_px / max(1, line_count)
        
        # Approximate cap height as 70% of line box height
        cap_height_px = single_line_px * 0.70

        if reference_marker_px_per_mm and reference_marker_px_per_mm > 0:
            px_per_mm = reference_marker_px_per_mm
            height_mm = round(cap_height_px / px_per_mm, 2)
            return FontSizeEstimationResult(
                estimated_height_mm=height_mm,
                confidence="high",
                pixel_height=cap_height_px,
                pixels_per_mm=px_per_mm,
                method="reference_marker_calibration",
            )

        if physical_pack_height_mm and physical_pack_height_mm > 0 and image_height_px > 0:
            px_per_mm = image_height_px / physical_pack_height_mm
            height_mm = round(cap_height_px / px_per_mm, 2)
            return FontSizeEstimationResult(
                estimated_height_mm=height_mm,
                confidence="medium",
                pixel_height=cap_height_px,
                pixels_per_mm=px_per_mm,
                method="physical_dimension_ratio",
            )

        # Fallback estimation without calibration reference
        px_per_mm = cls.DEFAULT_PIXELS_PER_MM
        height_mm = round(cap_height_px / px_per_mm, 2)
        return FontSizeEstimationResult(
            estimated_height_mm=height_mm,
            confidence="low",
            pixel_height=cap_height_px,
            pixels_per_mm=px_per_mm,
            method="estimated_default_dpi_fallback",
        )
