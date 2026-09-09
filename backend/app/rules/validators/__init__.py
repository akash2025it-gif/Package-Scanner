from app.rules.validators.base import BaseRuleValidator, ValidationResult
from app.rules.validators.presence import PresenceValidator
from app.rules.validators.mrp import MRPValidator
from app.rules.validators.net_quantity import NetQuantityValidator
from app.rules.validators.font_size import FontSizeValidator
from app.rules.validators.date_format import DateFormatValidator
from app.rules.validators.consumer_care import ConsumerCareValidator
from app.rules.validators.common_name import CommonNameValidator
from app.rules.validators.unit_sale_price import UnitSalePriceValidator

VALIDATOR_REGISTRY = {
    "presence": PresenceValidator(),
    "common_name": CommonNameValidator(),
    "mrp": MRPValidator(),
    "net_quantity": NetQuantityValidator(),
    "font_size": FontSizeValidator(),
    "date_format": DateFormatValidator(),
    "consumer_care": ConsumerCareValidator(),
    "unit_sale_price": UnitSalePriceValidator(),
}

__all__ = [
    "BaseRuleValidator",
    "ValidationResult",
    "PresenceValidator",
    "CommonNameValidator",
    "MRPValidator",
    "NetQuantityValidator",
    "FontSizeValidator",
    "DateFormatValidator",
    "ConsumerCareValidator",
    "UnitSalePriceValidator",
    "VALIDATOR_REGISTRY",
]
