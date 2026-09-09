import re
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class DateFormatValidator(BaseRuleValidator):
    # Matches MM/YYYY, MM/YY, Month YYYY, MM-YYYY, DD/MM/YYYY, etc.
    MONTH_NAMES = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    
    DATE_PATTERNS = [
        # MM/YYYY or MM-YYYY or MM.YYYY
        re.compile(r"\b(0[1-9]|1[0-2])[\/\-\.](20[2-3][0-9]|19[0-9]{2})\b"),
        # MM/YY
        re.compile(r"\b(0[1-9]|1[0-2])[\/\-\.]([2-3][0-9])\b"),
        # Month Year e.g. "August 2026", "Aug 2026"
        re.compile(rf"\b({MONTH_NAMES})\s*[\,\.\-]?\s*(20[2-3][0-9])\b", re.IGNORECASE),
        # Full date DD/MM/YYYY
        re.compile(r"\b(0[1-9]|[12][0-9]|3[01])[\/\-\.](0[1-9]|1[0-2])[\/\-\.](20[2-3][0-9])\b"),
    ]

    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        cleaned_text = (text or "").strip()
        ref = rule.rule_reference or "Rule 6(1)(e) of Legal Metrology (Packaged Commodities) Rules, 2011"

        if not cleaned_text or len(cleaned_text) < 2:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity="major",
                notes="Month and year of manufacture/packing/import is missing on the package.",
                suggested_correction="Declare month and year of mfg/packing (e.g. 'Mfg Date: 08/2026' or 'Packed: Aug 2026').",
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
                notes=f"Manufacturing date '{cleaned_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction="Verify manufacturing / packaging date on label.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected OCR text: '{cleaned_text}'",
            )

        matched_date = None
        for pattern in self.DATE_PATTERNS:
            m = pattern.search(cleaned_text)
            if m:
                matched_date = m.group(0)
                break

        if not matched_date:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes=f"Date text '{cleaned_text}' does not follow statutory Month/Year format per Rule 6(1)(e).",
                suggested_correction="Format date clearly as MM/YYYY or Month YYYY (e.g., '08/2026' or 'August 2026').",
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
            notes=f"Valid month/year of manufacture or packing detected ({matched_date}) per Rule 6(1)(e).",
            extracted_value=matched_date,
            confidence_score=confidence_score if confidence_score > 0 else 0.96,
            needs_review=False,
            evidence_text=f"Label text: '{cleaned_text}'",
        )
