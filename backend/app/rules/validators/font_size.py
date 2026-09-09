from typing import Any, Dict, Optional
from app.rules.config_loader import RuleConfigLoader, RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class FontSizeValidator(BaseRuleValidator):
    """
    Validates Numeral / Font Size against Second Schedule of LMPC Rules, 2011.
    Includes explicit calibration disclaimers for uncalibrated images.
    """

    def __init__(self):
        self.config_loader = RuleConfigLoader.get_instance()

    def get_min_font_height_for_quantity(self, qty_val: float, unit: str, is_blown_moulded: bool = False) -> float:
        # Convert kg/L to equivalent g/ml
        normalized_qty = qty_val
        if unit in ("kg", "l"):
            normalized_qty = qty_val * 1000.0
        elif unit in ("mg",):
            normalized_qty = qty_val / 1000.0

        for slab in self.config_loader.net_quantity_slabs:
            if slab.min_val <= normalized_qty <= slab.max_val:
                return slab.min_height_blown_moulded_mm if is_blown_moulded else slab.min_height_normal_mm

        return 2.0  # Default safe fallback

    def get_min_font_height_for_pdp(self, pdp_area_sq_cm: float, is_blown_moulded: bool = False) -> float:
        for slab in self.config_loader.pdp_area_slabs:
            if slab.min_area_sq_cm <= pdp_area_sq_cm <= slab.max_area_sq_cm:
                return slab.min_height_blown_moulded_mm if is_blown_moulded else slab.min_height_normal_mm
        return 2.0

    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        ref = rule.rule_reference or "Second Schedule of Legal Metrology (Packaged Commodities) Rules, 2011"

        if font_size_mm is None:
            return ValidationResult(
                is_compliant=True,
                is_present=True,
                rule_reference=ref,
                severity="none",
                notes="Font size: Cannot be reliably measured from this image — Manual Review Required.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text="Physical scale calibration unavailable.",
            )

        meta = metadata or {}
        calib_method = meta.get("calibration_method", "estimated_default_dpi_fallback")
        is_calibrated = calib_method in ("reference_marker_calibration", "physical_dimension_ratio")

        qty_val = meta.get("quantity_value")
        unit_val = meta.get("quantity_unit", "g")
        pdp_area = meta.get("pdp_area_sq_cm")
        is_blown = meta.get("is_blown_moulded", False)

        min_required = 2.0
        threshold_reason = "statutory standard"

        if qty_val is not None:
            min_required = self.get_min_font_height_for_quantity(float(qty_val), str(unit_val), is_blown)
            threshold_reason = f"declared net quantity ({qty_val} {unit_val})"
        elif pdp_area is not None:
            min_required = self.get_min_font_height_for_pdp(float(pdp_area), is_blown)
            threshold_reason = f"Principal Display Panel area ({pdp_area} cm²)"

        if font_size_mm < min_required:
            diff = round(min_required - font_size_mm, 2)
            if not is_calibrated:
                return ValidationResult(
                    is_compliant=False,
                    is_present=True,
                    rule_reference=ref,
                    severity="needs_review",
                    notes=f"Estimated visual size: approximately {font_size_mm:.1f} mm is below statutory minimum ({min_required:.1f} mm for {threshold_reason}). Deficit: {diff:.1f} mm — subject to manual verification by physical scale.",
                    suggested_correction=f"Verify numeral height on physical package to ensure >= {min_required:.1f} mm.",
                    extracted_value={"measured_mm": font_size_mm, "min_required_mm": min_required},
                    confidence_score=confidence_score,
                    needs_review=True,
                    evidence_text=f"Estimated visual height: ~{font_size_mm:.1f} mm",
                )
            
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes=f"Calibrated font height ({font_size_mm:.1f} mm) is below statutory minimum ({min_required:.1f} mm) for {threshold_reason}. Deficit: {diff:.1f} mm.",
                suggested_correction=f"Increase numeral and letter height to at least {min_required:.1f} mm.",
                extracted_value={"measured_mm": font_size_mm, "min_required_mm": min_required},
                confidence_score=confidence_score if confidence_score > 0 else 0.92,
                needs_review=False,
                evidence_text=f"Calibrated font height: {font_size_mm:.1f} mm",
            )

        notes = f"Compliant font height ({font_size_mm:.1f} mm >= required {min_required:.1f} mm)."
        if not is_calibrated:
            notes = f"Estimated visual size: approximately {font_size_mm:.1f} mm (meets required {min_required:.1f} mm) — subject to manual verification."

        return ValidationResult(
            is_compliant=True,
            is_present=True,
            rule_reference=ref,
            severity="none",
            notes=notes,
            extracted_value={"measured_mm": font_size_mm, "min_required_mm": min_required},
            confidence_score=confidence_score if confidence_score > 0 else 0.95,
            needs_review=not is_calibrated,
            evidence_text=f"Font height measurement: {font_size_mm:.1f} mm",
        )
