import pytest
from app.rules.config_loader import RuleConfigLoader
from app.rules.engine import RuleEngine
from app.rules.validators.consumer_care import ConsumerCareValidator
from app.rules.validators.date_format import DateFormatValidator
from app.rules.validators.font_size import FontSizeValidator
from app.rules.validators.mrp import MRPValidator
from app.rules.validators.net_quantity import NetQuantityValidator
from app.rules.validators.presence import PresenceValidator


@pytest.fixture
def loader():
    return RuleConfigLoader.get_instance()


def test_mrp_validator_compliant(loader):
    rule = loader.get_rule_by_id("RULE_6_1_F_MRP")
    validator = MRPValidator()
    
    # Valid MRP with rupee symbol and tax inclusion
    res = validator.validate(rule, "MRP ₹ 150.00 (inclusive of all taxes)")
    assert res.is_compliant is True
    assert res.is_present is True
    assert res.severity == "none"


def test_mrp_validator_missing_tax_phrase(loader):
    rule = loader.get_rule_by_id("RULE_6_1_F_MRP")
    validator = MRPValidator()
    
    # Missing '(inclusive of all taxes)'
    res = validator.validate(rule, "MRP ₹ 150.00")
    assert res.is_compliant is False
    assert res.is_present is True
    assert res.severity == "critical"
    assert "missing mandatory 'inclusive of all taxes'" in res.notes


def test_mrp_validator_missing_currency_symbol(loader):
    rule = loader.get_rule_by_id("RULE_6_1_F_MRP")
    validator = MRPValidator()
    
    # Missing Rupee / Rs symbol
    res = validator.validate(rule, "MRP 150.00 (incl. of all taxes)")
    assert res.is_compliant is False
    assert res.severity == "major"


def test_net_quantity_standard_units(loader):
    rule = loader.get_rule_by_id("RULE_6_1_D_NET_QUANTITY")
    validator = NetQuantityValidator()

    # Valid metric units
    res1 = validator.validate(rule, "Net Weight: 500 g")
    assert res1.is_compliant is True

    res2 = validator.validate(rule, "Net Qty: 1 kg")
    assert res2.is_compliant is True

    res3 = validator.validate(rule, "Net Vol: 750 ml")
    assert res3.is_compliant is True


def test_net_quantity_non_standard_units(loader):
    rule = loader.get_rule_by_id("RULE_6_1_D_NET_QUANTITY")
    validator = NetQuantityValidator()

    # Non-standard 'gms' is prohibited under Rule 8
    res = validator.validate(rule, "Net Weight: 500 gms")
    assert res.is_compliant is False
    assert res.severity == "major"
    assert "Non-standard unit symbol 'gms' used" in res.notes


def test_font_size_slabs_evaluation(loader):
    rule = loader.get_rule_by_id("RULE_SECOND_SCHEDULE_FONT_SIZE")
    validator = FontSizeValidator()

    # Net quantity 5 kg (>5000g slab requires min 8.0mm)
    res_pass = validator.validate(rule, "Net Wt: 5 kg", metadata={"quantity_value": 5, "quantity_unit": "kg"}, font_size_mm=8.5)
    assert res_pass.is_compliant is True

    res_fail = validator.validate(rule, "Net Wt: 5 kg", metadata={"quantity_value": 5, "quantity_unit": "kg"}, font_size_mm=4.0)
    assert res_fail.is_compliant is False
    assert "below statutory minimum" in res_fail.notes


def test_date_format_validator(loader):
    rule = loader.get_rule_by_id("RULE_6_1_E_MFG_DATE")
    validator = DateFormatValidator()

    assert validator.validate(rule, "Mfg Date: 08/2026").is_compliant is True
    assert validator.validate(rule, "Packed: August 2026").is_compliant is True
    assert validator.validate(rule, "Mfg Date: 2026").is_compliant is False


def test_consumer_care_validator(loader):
    rule = loader.get_rule_by_id("RULE_6_1_H_CONSUMER_CARE")
    validator = ConsumerCareValidator()

    valid_text = "Customer Care Executive, P.O. Box 123. Toll Free: 1800-111-222, Email: care@brand.com"
    assert validator.validate(rule, valid_text).is_compliant is True

    missing_contact = "For complaints write to Manager, Mumbai HQ"
    assert validator.validate(rule, missing_contact).is_compliant is False


def test_full_rule_engine_evaluation():
    engine = RuleEngine()
    extracted_fields = {
        "mrp": {
            "text": "MRP ₹ 245.00 (inclusive of all taxes)",
            "bounding_box": {"x": 50, "y": 200, "w": 300, "h": 40},
            "confidence": 0.95,
            "font_size_mm": 4.5,
        },
        "net_quantity": {
            "text": "Net Qty: 1 kg",
            "bounding_box": {"x": 50, "y": 150, "w": 200, "h": 40},
            "confidence": 0.96,
            "font_size_mm": 6.5,
        },
        "common_name": {
            "text": "Whole Wheat Flour",
            "bounding_box": {"x": 50, "y": 80, "w": 250, "h": 50},
            "confidence": 0.98,
            "font_size_mm": 6.0,
        },
        "mfg_date": {
            "text": "Mfg: 08/2026",
            "bounding_box": {"x": 50, "y": 300, "w": 180, "h": 30},
            "confidence": 0.95,
            "font_size_mm": 3.5,
        },
        "manufacturer_details": {
            "text": "Manufactured by ABC Mills Ltd, Plot 12, Industrial Area, Noida - 201301",
            "bounding_box": {"x": 50, "y": 350, "w": 400, "h": 60},
            "confidence": 0.94,
            "font_size_mm": 3.0,
        },
        "consumer_care": {
            "text": "Care: 1800-100-200, care@abcmills.com",
            "bounding_box": {"x": 50, "y": 420, "w": 350, "h": 40},
            "confidence": 0.92,
            "font_size_mm": 3.0,
        },
    }

    results = engine.evaluate_scan(extracted_fields)
    assert len(results) > 0
    overall = engine.calculate_overall_status(results)
    assert overall in ("compliant", "partially_compliant", "non_compliant")
