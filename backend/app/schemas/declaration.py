from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class FieldTypeEnum(str, Enum):
    MRP = "mrp"
    NET_QUANTITY = "net_quantity"
    MFG_DATE = "mfg_date"
    EXPIRY_DATE = "expiry_date"
    MANUFACTURER_DETAILS = "manufacturer_details"
    CONSUMER_CARE = "consumer_care"
    COUNTRY_OF_ORIGIN = "country_of_origin"
    UNIT_SALE_PRICE = "unit_sale_price"
    COMMON_NAME = "common_name"
    BEST_BEFORE = "best_before"
    OTHER = "other"


class SeverityEnum(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"
    NEEDS_REVIEW = "needs_review"


class BoundingBox(BaseModel):
    x: float = Field(0.0, description="X coordinate (pixels or normalized 0-1)")
    y: float = Field(0.0, description="Y coordinate (pixels or normalized 0-1)")
    w: float = Field(0.0, description="Width (pixels or normalized 0-1)")
    h: float = Field(0.0, description="Height (pixels or normalized 0-1)")


class DeclarationBase(BaseModel):
    field_type: FieldTypeEnum
    extracted_text: Optional[str] = None
    raw_extracted_value: Optional[str] = None
    normalized_numeric_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    has_conflict: bool = False
    conflict_details: Optional[str] = None
    bounding_box: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = Field(0.0, ge=0.0, le=1.0)
    font_size_mm: Optional[float] = None
    is_present: bool = False
    is_compliant: bool = False
    rule_reference: str = "LMPC Rules 2011"
    severity: SeverityEnum = SeverityEnum.NONE
    reviewer_override: bool = False
    reviewer_notes: Optional[str] = None
    original_ai_status: Optional[str] = None
    original_ai_confidence: Optional[float] = 0.0
    # Workflow Automation & Threshold Fields
    violation_detection_rate: Optional[float] = None
    auto_confirm_threshold: Optional[float] = None
    workflow_decision: Optional[str] = None  # AUTO_CONFIRMED, MANUAL_REVIEW_REQUIRED, FINALIZED
    decision_method: Optional[str] = None  # SYSTEM_THRESHOLD, MANUAL, AUTOMATIC
    decision_reason: Optional[str] = None
    verification_status: Optional[str] = None  # AUTO_CONFIRMED, MANUAL_REVIEW_REQUIRED, INSPECTOR_CONFIRMED, INSPECTOR_REJECTED, INSPECTOR_OVERRIDDEN, FINALIZED
    verification_source: Optional[str] = None  # SYSTEM_THRESHOLD, INSPECTOR, MANUAL

    human_decision: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class DeclarationResponse(DeclarationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    created_at: datetime
    updated_at: datetime


class DeclarationOverrideRequest(BaseModel):
    is_compliant: Optional[bool] = None
    is_present: Optional[bool] = None
    extracted_text: Optional[str] = None
    font_size_mm: Optional[float] = None
    severity: Optional[SeverityEnum] = None
    reviewer_notes: str = Field(..., min_length=2, description="Mandatory notes explaining reason for override")


class DeclarationReviewRequest(BaseModel):
    action: str = Field(..., description="'confirm', 'reject', or 'override'")
    is_compliant: Optional[bool] = None
    severity: Optional[SeverityEnum] = None
    reviewer_notes: str = Field(..., min_length=2, description="Mandatory notes explaining the inspection decision")

