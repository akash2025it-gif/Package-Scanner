import re
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class UnitSalePriceValidator(BaseRuleValidator):
    """
    Validates Unit Sale Price (USP) declaration under Rule 6(1)(g) of LMPC Rules, 2011.
    Mandates unit sale price rounded off to nearest two decimal places per g/kg/ml/l/unit.
    """

    USP_PATTERN = re.compile(
        r"(?:(?:unit\s+sale\s+price|u\.?s\.?p\.?|unit\s+price)\s*[:\-]?\s*)?(?:(₹|rs\.?|inr)\s*)?([0-9]+(?:\.[0-9]{1,2})?)\s*(?:\/|\s+per\s+)\s*([a-zA-Z]+)",
        re.IGNORECASE,
    )

    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        cleaned_text = (text or "").strip()
        ref = rule.rule_reference or "Rule 6(1)(g) of Legal Metrology (Packaged Commodities) Rules, 2011"

        if not cleaned_text or len(cleaned_text) < 2:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity=rule.severity or "major",
                notes="Unit Sale Price (USP) declaration is missing on the package.",
                suggested_correction="Declare Unit Sale Price as 'Unit Sale Price: ₹ XX.XX / g' (or kg/ml/l/unit).",
                confidence_score=confidence_score,
                needs_review=False,
                evidence_text="[Field absent on packaging label]",
            )

        # Check confidence
        if 0.0 < confidence_score < 0.70:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="needs_review",
                notes=f"Unit Sale Price '{cleaned_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction="Verify Unit Sale Price on packaging label.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected text: '{cleaned_text}'",
            )

        match = self.USP_PATTERN.search(cleaned_text)
        if match:
            price_val = match.group(2)
            unit_val = match.group(3)
            formatted = f"₹ {price_val} / {unit_val}"
            return ValidationResult(
                is_compliant=True,
                is_present=True,
                rule_reference=ref,
                severity="none",
                notes=f"Compliant Unit Sale Price declared per Rule 6(1)(g) ({formatted}).",
                extracted_value=formatted,
                confidence_score=confidence_score if confidence_score > 0 else 0.94,
                needs_review=False,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        # Text is present but doesn't clearly match ₹/unit
        if any(sym in cleaned_text.lower() for sym in ("₹", "rs", "inr", "/")):
            return ValidationResult(
                is_compliant=True,
                is_present=True,
                rule_reference=ref,
                severity="none",
                notes=f"Unit Sale Price declaration detected: '{cleaned_text}'.",
                extracted_value=cleaned_text,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=False,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        return ValidationResult(
            is_compliant=False,
            is_present=True,
            rule_reference=ref,
            severity="major",
            notes=f"Unit Sale Price text '{cleaned_text}' does not specify valid price per unit measure.",
            suggested_correction="Format Unit Sale Price clearly with currency and unit (e.g. ₹ 0.50 / g).",
            extracted_value=cleaned_text,
            confidence_score=confidence_score,
            needs_review=False,
            evidence_text=f"Extracted: '{cleaned_text}'",
        )
