from typing import Any, Dict, List, Optional
from app.rules.config_loader import RuleConfigLoader, RuleDefinition
from app.rules.validators import VALIDATOR_REGISTRY, ValidationResult


class RuleEngine:
    def __init__(self):
        self.config_loader = RuleConfigLoader.get_instance()

    def evaluate_field(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        validator = VALIDATOR_REGISTRY.get(rule.validation_type)
        if not validator:
            validator = VALIDATOR_REGISTRY["presence"]
        return validator.validate(
            rule=rule,
            text=text,
            metadata=metadata,
            font_size_mm=font_size_mm,
            confidence_score=confidence_score,
        )

    def evaluate_scan(
        self,
        extracted_fields: Dict[str, Dict[str, Any]],
        scan_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs LMPC 2011 rule evaluation against extracted scan fields.
        Deduplicates declarations so each normalized declaration key appears exactly once.
        """
        results: List[Dict[str, Any]] = []
        meta = dict(scan_metadata or {})
        seen_field_types = set()

        # Extract net quantity info if available to pass to font size and other validators
        qty_info = {}
        if "net_quantity" in extracted_fields:
            net_q_text = extracted_fields["net_quantity"].get("text", "")
            from app.rules.validators.net_quantity import NetQuantityValidator
            parsed = NetQuantityValidator().parse_quantity_unit(net_q_text)
            if parsed:
                qty_info["quantity_value"] = parsed[0]
                qty_info["quantity_unit"] = parsed[1]

        # Iterate over all enabled rules
        for rule in self.config_loader.rules:
            if not rule.enabled:
                continue

            # Ensure strict deduplication by normalized field_type
            if rule.field_type in seen_field_types:
                continue
            seen_field_types.add(rule.field_type)

            field_data = extracted_fields.get(rule.field_type)
            
            if field_data:
                text = field_data.get("text")
                bbox = field_data.get("bounding_box", {})
                conf = float(field_data.get("confidence", 0.0))
                font_mm = field_data.get("font_size_mm")
                calib_method = field_data.get("calibration_method", "estimated_default_dpi_fallback")

                merged_meta = {**meta, **qty_info, "calibration_method": calib_method}
                v_result = self.evaluate_field(
                    rule=rule,
                    text=text,
                    metadata=merged_meta,
                    font_size_mm=font_mm,
                    confidence_score=conf,
                )

                # Determine confidence category
                if conf >= 0.90:
                    conf_level = "HIGH"
                elif conf >= 0.70:
                    conf_level = "MEDIUM"
                else:
                    conf_level = "LOW"

                # Determine display text
                display_val = v_result.extracted_value if (rule.field_type == "net_quantity" and v_result.extracted_value) else text

                results.append({
                    "field_type": rule.field_type,
                    "rule_id": rule.id,
                    "name": rule.name,
                    "extracted_text": display_val,
                    "raw_extracted_value": v_result.raw_extracted_value or text,
                    "normalized_numeric_value": v_result.normalized_numeric_value,
                    "normalized_unit": v_result.normalized_unit,
                    "has_conflict": v_result.has_conflict,
                    "conflict_details": v_result.conflict_details,
                    "bounding_box": bbox,
                    "confidence_score": round(conf, 2),
                    "confidence_level": conf_level,
                    "font_size_mm": font_mm,
                    "is_present": v_result.is_present,
                    "is_compliant": v_result.is_compliant,
                    "rule_reference": v_result.rule_reference or rule.rule_reference,
                    "severity": "needs_review" if v_result.has_conflict else v_result.severity,
                    "reviewer_notes": v_result.notes,
                    "suggested_correction": v_result.suggested_correction,
                    "needs_review": v_result.needs_review or v_result.has_conflict or (conf < 0.70 and conf > 0.0),
                    "evidence_text": v_result.evidence_text or (f"Label text: '{text}'" if text else "[Missing]"),
                })
            else:
                # Field was completely missed / not detected on package
                # For common_name: if not detected, mark as needs_review per requirements
                is_common_name = rule.field_type == "common_name"
                results.append({
                    "field_type": rule.field_type,
                    "rule_id": rule.id,
                    "name": rule.name,
                    "extracted_text": None,
                    "bounding_box": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0},
                    "confidence_score": 0.0,
                    "confidence_level": "LOW",
                    "font_size_mm": None,
                    "is_present": False,
                    "is_compliant": False,
                    "rule_reference": rule.rule_reference or "Applicable requirement requires manual verification.",
                    "severity": "needs_review" if is_common_name else rule.severity,
                    "reviewer_notes": (
                        "Common/generic name could not be confidently verified from the image. Subject to manual verification."
                        if is_common_name
                        else f"Mandatory declaration '{rule.name}' not detected on the scanned package."
                    ),
                    "suggested_correction": f"Ensure '{rule.name}' is declared prominently on the package label.",
                    "needs_review": is_common_name,
                    "evidence_text": "[Field absent on packaging label]",
                })

        return results

    @staticmethod
    def calculate_overall_status(evaluations: List[Dict[str, Any]]) -> str:
        """
        Determines overall compliance status:
        - 'compliant': All applicable declarations detected with sufficient confidence and no confirmed violation exists.
        - 'non_compliant': At least one confirmed requirement violation exists with sufficient confidence.
        - 'needs_review': Uncertain findings, low OCR confidence, uncalibrated estimates, or unverified common name exist, and no confirmed violations exist.
        """
        if not evaluations:
            return "needs_review"

        confirmed_violations = 0
        uncertain_findings = 0

        for e in evaluations:
            is_comp = e.get("is_compliant", False)
            sev = e.get("severity", "none")
            conf = e.get("confidence_score", 0.0)
            needs_rev = e.get("needs_review", False)

            if not is_comp:
                if sev == "needs_review" or needs_rev or (conf > 0.0 and conf < 0.70):
                    uncertain_findings += 1
                elif sev in ("critical", "major") and (conf >= 0.70 or not e.get("is_present")):
                    confirmed_violations += 1
                else:
                    uncertain_findings += 1
            else:
                if needs_rev or (conf > 0.0 and conf < 0.70):
                    uncertain_findings += 1

        if confirmed_violations > 0:
            return "non_compliant"
        elif uncertain_findings > 0:
            return "needs_review"
        return "compliant"
