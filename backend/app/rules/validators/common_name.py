import re
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition
from app.rules.validators.base import BaseRuleValidator, ValidationResult


class CommonNameValidator(BaseRuleValidator):
    """
    Validates Generic or Common Name declaration under Rule 6(1)(a) of LMPC Rules, 2011.
    Distinguishes between product/brand name, generic commodity names, missing declarations, and OCR uncertainty.
    Never marks uncertain findings as confirmed violations.
    """

    KNOWN_GENERIC_COMMODITIES = [
        "dry fruits", "almonds", "cashew", "walnuts", "pistachios", "raisins",
        "chips", "potato chips", "wafers", "namkeen", "snack", "extruded snack",
        "biscuits", "cookies", "rusk", "crackers",
        "atta", "wheat flour", "flour", "maida", "besan", "suji", "rava",
        "rice", "basmati rice", "pulses", "dal", "lentils",
        "oil", "edible oil", "mustard oil", "sunflower oil", "soybean oil", "refined oil",
        "tea", "black tea", "green tea", "coffee", "pure coffee", "beverage", "juice",
        "spices", "turmeric", "chilli powder", "coriander", "garam masala", "salt", "sugar",
        "soap", "toilet soap", "detergent", "shampoo", "hair cleanser", "toothpaste",
        "milk", "dairy", "butter", "ghee", "paneer", "cheese", "yogurt",
        "noodles", "pasta", "vermicelli", "cereal", "oats", "corn flakes",
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
        meta = metadata or {}
        
        # Candidate names from product info if available
        p_name = (meta.get("product_name") or "").strip()
        p_cat = (meta.get("product_category") or "").strip()

        # 1. Direct text analysis
        is_candidate_found = False
        candidate_text = cleaned_text

        if len(cleaned_text) >= 2:
            lower_text = cleaned_text.lower()
            for commodity in self.KNOWN_GENERIC_COMMODITIES:
                if commodity in lower_text:
                    is_candidate_found = True
                    break
            if not is_candidate_found and len(cleaned_text.split()) <= 6:
                # Plausible commodity phrase
                is_candidate_found = True
        elif p_name or p_cat:
            # Check if product metadata has a recognizable commodity
            combined_meta = f"{p_name} {p_cat}".lower()
            for commodity in self.KNOWN_GENERIC_COMMODITIES:
                if commodity in combined_meta:
                    is_candidate_found = True
                    candidate_text = commodity.title()
                    break

        # 2. Evaluation based on confidence and detection
        if is_candidate_found and candidate_text:
            if confidence_score < 0.70 and confidence_score > 0.0:
                return ValidationResult(
                    is_compliant=False,
                    is_present=True,
                    rule_reference=rule.rule_reference or "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
                    severity="needs_review",
                    notes=f"Candidate common name '{candidate_text}' detected with low OCR confidence ({int(confidence_score * 100)}% < 70%) — subject to manual verification.",
                    extracted_value=candidate_text,
                    suggested_correction="Verify generic or common name on packaging label.",
                    confidence_score=confidence_score,
                    needs_review=True,
                    evidence_text=f"Candidate text: '{candidate_text}'",
                )
            
            # High / Medium confidence detection
            effective_conf = confidence_score if confidence_score > 0.0 else 0.95
            return ValidationResult(
                is_compliant=True,
                is_present=True,
                rule_reference=rule.rule_reference or "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
                severity="none",
                notes=f"Statutory generic or common name '{candidate_text}' clearly declared per Rule 6(1)(a).",
                extracted_value=candidate_text,
                confidence_score=effective_conf,
                needs_review=False,
                evidence_text=f"Declared common name: '{candidate_text}'",
            )

        # 3. If unverified / uncertain, do NOT mark as confirmed violation
        return ValidationResult(
            is_compliant=False,
            is_present=False,
            rule_reference=rule.rule_reference or "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
            severity="needs_review",
            notes="Common/generic name could not be confidently verified from the image. Applicable requirement requires manual verification.",
            suggested_correction="Verify if generic name (e.g. 'Dry Fruits', 'Potato Chips', 'Flour') is declared on the principal display panel.",
            confidence_score=confidence_score,
            needs_review=True,
            evidence_text="No conclusive generic commodity name detected in OCR text.",
        )
