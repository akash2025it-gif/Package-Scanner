import re
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class ConsumerCareValidator(BaseRuleValidator):
    EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    PHONE_PATTERN = re.compile(r"(?:tel|phone|contact|toll\s*free|care|helpline|call)?\s*[:\-]?\s*(?:\+?91[\-\s]?)?[0-9]{3,5}[\-\s]?[0-9]{5,8}\b", re.IGNORECASE)

    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        cleaned_text = (text or "").strip()
        ref = rule.rule_reference or "Rule 6(1)(h) of Legal Metrology (Packaged Commodities) Rules, 2011"

        if not cleaned_text or len(cleaned_text) < 3:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity="major",
                notes="Consumer care contact details are missing on the package.",
                suggested_correction="Declare contact name/address, toll-free phone number, and email for consumer grievance redressal per Rule 6(1)(h).",
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
                notes=f"Consumer care details '{cleaned_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction="Verify consumer care contacts on physical packaging.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected OCR text: '{cleaned_text}'",
            )

        has_email = bool(self.EMAIL_PATTERN.search(cleaned_text))
        has_phone = bool(self.PHONE_PATTERN.search(cleaned_text))

        if not (has_email or has_phone):
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes="Consumer care details do not include a valid telephone number, toll-free helpline, or email address.",
                suggested_correction="Provide telephone number or email address for consumer complaints per Rule 6(1)(h).",
                extracted_value=cleaned_text,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=False,
                evidence_text=f"Extracted: '{cleaned_text}'",
            )

        return ValidationResult(
            is_compliant=True,
            is_present=True,
            rule_reference=ref,
            severity="none",
            notes="Valid statutory consumer care details detected with active helpline and/or email address.",
            extracted_value=cleaned_text,
            confidence_score=confidence_score if confidence_score > 0 else 0.94,
            needs_review=False,
            evidence_text=f"Label text: '{cleaned_text}'",
        )
