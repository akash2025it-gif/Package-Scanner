import re
from typing import Any, Dict, Optional, Tuple
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult
from app.rules.validators.font_size import FontSizeValidator


class NetQuantityValidator(BaseRuleValidator):
    """
    Validates Net Quantity in standard units under Rule 6(1)(d) read with Rule 8 and Second Schedule.
    Integrates font size / numeral height verification with calibration disclaimers.
    """

    QTY_PATTERN = re.compile(
        r"(?:(?:net\s+(?:wt\.?|weight|qty\.?|quantity|content|volume))\s*[:\-]?\s*)?([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)",
        re.IGNORECASE,
    )

    STANDARD_MASS_UNITS = {"g", "kg", "mg"}
    STANDARD_VOLUME_UNITS = {"ml", "l", "kl", "l.", "ml."}
    STANDARD_COUNT_UNITS = {"n", "u", "unit", "units", "count", "pieces", "pcs", "pkt", "pkts", "sachets"}
    NON_STANDARD_UNITS = {"gms", "gms.", "kgs", "kgs.", "gm", "g.", "ltr", "ltrs", "lts", "ml."}

    def __init__(self):
        self.font_size_validator = FontSizeValidator()

    def parse_quantity_unit(self, text: str) -> Optional[Tuple[float, str]]:
        match = self.QTY_PATTERN.search(text)
        if match:
            try:
                qty_val = float(match.group(1))
                unit_val = match.group(2).strip().lower()
                return qty_val, unit_val
            except ValueError:
                pass
        return None

    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        cleaned_text = (text or "").strip()
        ref = rule.rule_reference or "Rule 6(1)(d) read with Rule 8 of LMPC Rules, 2011"

        if not cleaned_text or len(cleaned_text) < 1:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity="critical",
                notes="Net quantity declaration is missing on the package.",
                suggested_correction="Declare Net Quantity per Rule 6(1)(d) (e.g., 'Net Qty: 500 g').",
                confidence_score=confidence_score,
                needs_review=False,
                evidence_text="[Field absent on packaging label]",
            )

        # Low confidence handling
        if 0.0 < confidence_score < 0.70:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="needs_review",
                notes=f"Net quantity '{cleaned_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction="Verify Net Quantity on packaging label.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected OCR text: '{cleaned_text}'",
            )

        parsed = self.parse_quantity_unit(cleaned_text)
        if not parsed:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="critical",
                notes=f"Net quantity '{cleaned_text}' could not be parsed into a numeric value and standard unit.",
                suggested_correction="Specify numeric quantity followed by standard unit (e.g. 250 g, 1 kg, 500 ml, 10 N).",
                confidence_score=confidence_score,
                needs_review=False,
                evidence_text=f"Extracted text: '{cleaned_text}'",
            )

        qty_num, unit = parsed
        qty_str = f"{int(qty_num) if qty_num.is_integer() else qty_num} {unit}"

        # Standard physical unit normalization (Rule 8)
        norm_value = qty_num
        norm_unit = unit
        if unit == "kg":
            norm_value = qty_num * 1000.0
            norm_unit = "g"
        elif unit in ("l", "ltr", "l."):
            norm_value = qty_num * 1000.0
            norm_unit = "ml"
        elif unit in ("mg",):
            norm_value = qty_num / 1000.0
            norm_unit = "g"

        # Conflict Detection: Compare against any pre-existing or claimed product quantity
        meta = metadata or {}
        has_conflict = False
        conflict_msg = None
        claimed_qty = meta.get("claimed_net_quantity") or meta.get("expected_net_quantity")
        if claimed_qty:
            claimed_parsed = self.parse_quantity_unit(str(claimed_qty))
            if claimed_parsed:
                c_num, c_unit = claimed_parsed
                c_norm = c_num * 1000.0 if c_unit == "kg" else (c_num * 1000.0 if c_unit in ("l", "ltr") else c_num)
                if abs(c_norm - norm_value) > 1e-3:
                    has_conflict = True
                    conflict_msg = f"Extraction Conflict: Package evidence shows '{qty_str}' but declared reference is '{claimed_qty}'. Inspector verification required."

        # Check for non-standard symbols like "gms", "kgs", "gm"
        if unit in self.NON_STANDARD_UNITS or unit in (rule.disallowed_symbols or []):
            standard_replacement = "g" if "gm" in unit else ("kg" if "kg" in unit else "ml")
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes=f"Non-standard unit symbol '{unit}' used. Rule 8 strictly mandates standard unit symbols ('{standard_replacement}').",
                suggested_correction=f"Replace non-standard '{unit}' with statutory standard '{standard_replacement}'.",
                extracted_value=qty_str,
                raw_extracted_value=cleaned_text,
                normalized_numeric_value=norm_value,
                normalized_unit=norm_unit,
                has_conflict=has_conflict,
                conflict_details=conflict_msg,
                confidence_score=confidence_score if confidence_score > 0 else 0.95,
                needs_review=has_conflict,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        # Verify unit is in allowed standard units
        all_standard = self.STANDARD_MASS_UNITS | self.STANDARD_VOLUME_UNITS | self.STANDARD_COUNT_UNITS
        if unit not in all_standard:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes=f"Unrecognized or non-metric unit '{unit}' found in net quantity declaration.",
                suggested_correction="Use standard metric units (g, kg, ml, l) or count (N/units).",
                extracted_value=qty_str,
                raw_extracted_value=cleaned_text,
                normalized_numeric_value=norm_value,
                normalized_unit=norm_unit,
                has_conflict=has_conflict,
                conflict_details=conflict_msg,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=has_conflict,
                evidence_text=f"Extracted: '{cleaned_text}'",
            )

        # Evaluate font size if measurement / estimate exists
        calib_method = meta.get("calibration_method", "estimated_default_dpi_fallback")
        is_calibrated = calib_method in ("reference_marker_calibration", "physical_dimension_ratio")
        
        notes = f"Valid net quantity declaration: {qty_str}."
        if has_conflict:
            notes += f" {conflict_msg}"

        if font_size_mm is not None:
            if is_calibrated:
                # Check slab
                min_req = self.font_size_validator.get_min_font_height_for_quantity(qty_num, unit)
                if font_size_mm < min_req:
                    return ValidationResult(
                        is_compliant=False,
                        is_present=True,
                        rule_reference="Rule 6(1)(d) read with Second Schedule of LMPC Rules, 2011",
                        severity="major",
                        notes=f"Net quantity {qty_str} has numeral height ({font_size_mm:.1f} mm) below statutory minimum ({min_req:.1f} mm) per Second Schedule.",
                        suggested_correction=f"Increase numeral height to at least {min_req:.1f} mm.",
                        extracted_value=f"{qty_str} (Calibrated Font: {font_size_mm} mm)",
                        raw_extracted_value=cleaned_text,
                        normalized_numeric_value=norm_value,
                        normalized_unit=norm_unit,
                        has_conflict=has_conflict,
                        conflict_details=conflict_msg,
                        confidence_score=confidence_score if confidence_score > 0 else 0.95,
                        needs_review=has_conflict,
                        evidence_text=f"Label text: '{cleaned_text}', Font: {font_size_mm} mm",
                    )
                notes += f" Calibrated numeral height: {font_size_mm:.1f} mm (statutory min: {min_req:.1f} mm)."
            else:
                notes += f" Estimated visual size: approximately {font_size_mm:.1f} mm — subject to manual verification by physical scale."

        return ValidationResult(
            is_compliant=not has_conflict,
            is_present=True,
            rule_reference=ref,
            severity="needs_review" if has_conflict else "none",
            notes=notes,
            extracted_value=qty_str,
            raw_extracted_value=cleaned_text,
            normalized_numeric_value=norm_value,
            normalized_unit=norm_unit,
            has_conflict=has_conflict,
            conflict_details=conflict_msg,
            confidence_score=confidence_score if confidence_score > 0 else 0.96,
            needs_review=has_conflict,
            evidence_text=f"Label text: '{cleaned_text}'",
        )
