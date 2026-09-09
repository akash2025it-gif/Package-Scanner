import re
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class MRPValidator(BaseRuleValidator):
    # Regex to capture currency and price: e.g. "MRP Rs. 150.00 (incl. of all taxes)", "₹99.00", "MRP: Rs 45"
    PRICE_PATTERN = re.compile(
        r"(?:(?:mrp|maximum\s+retail\s+price|m\.r\.p\.)\s*[:\-]?\s*)?(?:(₹|rs\.?|inr)\s*)?([0-9]+(?:[.,][0-9]{1,2})?)",
        re.IGNORECASE,
    )

    TAX_INCLUSIVE_PATTERNS = [
        re.compile(r"incl(?:usive)?\.?\s+of\s+all\s+taxes", re.IGNORECASE),
        re.compile(r"incl(?:usive)?\.?\s+all\s+taxes", re.IGNORECASE),
        re.compile(r"all\s+taxes\s+incl(?:uded|usive)?", re.IGNORECASE),
        re.compile(r"incl\.?\s+taxes", re.IGNORECASE),
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
        ref = rule.rule_reference or "Rule 6(1)(f) of Legal Metrology (Packaged Commodities) Rules, 2011"

        if not cleaned_text or len(cleaned_text) < 2:
            return ValidationResult(
                is_compliant=False,
                is_present=False,
                rule_reference=ref,
                severity="critical",
                notes="MRP declaration is completely missing on the package.",
                suggested_correction="Declare 'MRP ₹ XX.XX (inclusive of all taxes)'.",
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
                notes=f"MRP text '{cleaned_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                extracted_value=cleaned_text,
                suggested_correction="Verify MRP and tax statement on physical package label.",
                confidence_score=confidence_score,
                needs_review=True,
                evidence_text=f"Detected OCR text: '{cleaned_text}'",
            )

        # Check numeric price match
        price_match = self.PRICE_PATTERN.search(cleaned_text)
        has_tax_phrase = any(p.search(cleaned_text) for p in self.TAX_INCLUSIVE_PATTERNS)
        
        # Check currency symbol presence
        has_currency_symbol = any(sym.lower() in cleaned_text.lower() for sym in (rule.currency_symbols or ["₹", "rs", "inr"]))

        if not price_match or not price_match.group(2):
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="critical",
                notes="MRP text is present on label but does not contain a clear numeric price.",
                suggested_correction="Ensure numeric retail price is clearly specified (e.g. MRP ₹ 100.00).",
                confidence_score=confidence_score,
                needs_review=False,
                evidence_text=f"Extracted text: '{cleaned_text}'",
            )

        extracted_price = price_match.group(2)

        if not has_currency_symbol:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="major",
                notes="MRP does not contain statutory currency designation (₹ or Rs.).",
                suggested_correction="Prepend Rupee symbol '₹' to the MRP amount.",
                extracted_value=extracted_price,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=False,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        if not has_tax_phrase:
            return ValidationResult(
                is_compliant=False,
                is_present=True,
                rule_reference=ref,
                severity="critical",
                notes="MRP declaration violates Rule 6(1)(f): missing mandatory 'inclusive of all taxes' statement.",
                suggested_correction="Append '(inclusive of all taxes)' or '(incl. of all taxes)' to the MRP declaration.",
                extracted_value=extracted_price,
                confidence_score=confidence_score if confidence_score > 0 else 0.90,
                needs_review=False,
                evidence_text=f"Label text: '{cleaned_text}'",
            )

        return ValidationResult(
            is_compliant=True,
            is_present=True,
            rule_reference=ref,
            severity="none",
            notes="Valid MRP declaration with statutory currency symbol and tax-inclusive clause.",
            extracted_value=f"₹ {extracted_price} (inclusive of all taxes)",
            confidence_score=confidence_score if confidence_score > 0 else 0.96,
            needs_review=False,
            evidence_text=f"Label text: '{cleaned_text}'",
        )
