from dataclasses import dataclass, field
import os
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class RuleDefinition:
    id: str
    field_type: str
    name: str
    description: str
    rule_reference: str
    validation_type: str
    severity: str
    enabled: bool = True
    min_confidence_threshold: float = 0.4
    allowed_units: Optional[Dict[str, List[str]]] = None
    disallowed_symbols: Optional[List[str]] = None
    currency_symbols: Optional[List[str]] = None
    mandatory_phrases: Optional[List[str]] = None
    requires_import_check: bool = False


@dataclass
class NetQuantitySlab:
    min_val: float
    max_val: float
    unit_category: str
    min_height_normal_mm: float
    min_height_blown_moulded_mm: float
    description: str


@dataclass
class PDPAreaSlab:
    min_area_sq_cm: float
    max_area_sq_cm: float
    min_height_normal_mm: float
    min_height_blown_moulded_mm: float
    description: str


class RuleConfigLoader:
    _instance: Optional["RuleConfigLoader"] = None
    
    def __init__(self, rules_dir: Optional[str] = None):
        if rules_dir is None:
            rules_dir = os.path.dirname(__file__)
        self.rules_dir = rules_dir
        self.rules: List[RuleDefinition] = []
        self.net_quantity_slabs: List[NetQuantitySlab] = []
        self.pdp_area_slabs: List[PDPAreaSlab] = []
        self.load_configs()

    @classmethod
    def get_instance(cls) -> "RuleConfigLoader":
        if cls._instance is None:
            cls._instance = RuleConfigLoader()
        return cls._instance

    def load_configs(self):
        rules_path = os.path.join(self.rules_dir, "lmpc_rules.yaml")
        font_path = os.path.join(self.rules_dir, "font_size_tables.yaml")

        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.rules = [
                    RuleDefinition(**r) for r in data.get("rules", [])
                ]

        if os.path.exists(font_path):
            with open(font_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.net_quantity_slabs = [
                    NetQuantitySlab(**s) for s in data.get("net_quantity_slabs", [])
                ]
                self.pdp_area_slabs = [
                    PDPAreaSlab(**s) for s in data.get("pdp_area_slabs", [])
                ]

    def get_rule_by_id(self, rule_id: str) -> Optional[RuleDefinition]:
        for r in self.rules:
            if r.id == rule_id:
                return r
        return None

    def get_rules_for_field(self, field_type: str) -> List[RuleDefinition]:
        return [r for r in self.rules if r.field_type == field_type and r.enabled]
