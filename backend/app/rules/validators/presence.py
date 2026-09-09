from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class PresenceValidator(BaseRuleValidator):
    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        cleaned_text = (text or "").strip()
        is_present = len(cleaned_text) >= 2
        ref = rule.rule_reference or "Legal Metrology (Packaged Commodities) Rules, 2011"

        if not is_present:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity=rule.severity or "critical",
                notes=f"Mandatory declaration '{rule.name}' is missing on the product package label.",
                suggested_correction=f"Add mandatory declaration for {rule.name} per {ref}.",
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
                notes=f"Declaration '{rule.name}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction=f"Verify {rule.name} on packaging label.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected OCR text: '{cleaned_text}'",
            )

        # For manufacturer address, check if it's too short (e.g. just 1-2 words)
        if rule.field_type in ("manufacturer_details", "manufacturer") and len(cleaned_text.split()) < 3:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes="Manufacturer declaration is present but appears incomplete (missing complete postal address/location per Rule 6(1)(b)).",
                suggested_correction="Declare complete name and postal address of manufacturer/packer/importer.",
                extracted_value=cleaned_text,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=False,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        return ValidationResult(
            is_compliant=True,
            is_present=True,
            rule_reference=ref,
            severity="none",
            notes=f"Valid statutory declaration for '{rule.name}' detected.",
            extracted_value=cleaned_text,
            confidence_score=confidence_score if confidence_score > 0 else 0.95,
            needs_review=False,
            evidence_text=f"Label text: '{cleaned_text}'",
        )
