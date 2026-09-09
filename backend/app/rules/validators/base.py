from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from app.rules.config_loader import RuleDefinition


@dataclass
class ValidationResult:
    is_compliant: bool
    is_present: bool
    rule_reference: str
    severity: str  # "none", "minor", "major", "critical", "needs_review"
    notes: Optional[str] = None
    extracted_value: Optional[Any] = None
    raw_extracted_value: Optional[str] = None
    normalized_numeric_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    has_conflict: bool = False
    conflict_details: Optional[str] = None
    suggested_correction: Optional[str] = None
    confidence_score: float = 0.0
    needs_review: bool = False
    evidence_text: Optional[str] = None

    @property
    def confidence_level(self) -> str:
        """Returns HIGH (>=0.90), MEDIUM (0.70-0.89), or LOW (<0.70)."""
        if self.confidence_score >= 0.90:
            return "HIGH"
        elif self.confidence_score >= 0.70:
            return "MEDIUM"
        return "LOW"


class BaseRuleValidator(ABC):
    @abstractmethod
    def validate(
        self,
        rule: RuleDefinition,
        text: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
        font_size_mm: Optional[float] = None,
        confidence_score: float = 0.0,
    ) -> ValidationResult:
        """Runs the validation logic on the extracted field text/metadata."""
        pass
