from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.declaration import DeclarationResponse
from app.schemas.product import ProductCreate, ProductResponse
from app.schemas.user import UserResponse


class ScanSourceEnum(str, Enum):
    PHYSICAL_STORE = "physical_store"
    ECOMMERCE = "ecommerce"


class ScanStatusEnum(str, Enum):
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REVIEWED = "reviewed"
    FINALIZED = "finalized"
    CLOSED = "closed"
    FAILED = "failed"



class ImageTypeEnum(str, Enum):
    FRONT = "front"
    BACK = "back"
    TOP = "top"
    BOTTOM = "bottom"
    SIDE = "side"
    OTHER = "other"


class ScanImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    image_url: str
    storage_key: str
    image_type: str
    width_px: Optional[int] = None
    height_px: Optional[int] = None
    uploaded_at: datetime

    # Image Quality & Blur Validation Gate
    image_quality: Optional[str] = "CLEAR"
    sharpness_score: Optional[float] = None
    quality_threshold: Optional[float] = None
    quality_validated_at: Optional[datetime] = None
    analysis_allowed: Optional[bool] = True
    quality_details_json: Optional[Dict[str, Any]] = None


class ImageQualityCheckResponse(BaseModel):
    image_quality: str = Field(..., description="'CLEAR', 'BLURRY', 'LOW_QUALITY', or 'FAILED'")
    sharpness_score: float = Field(..., description="Calculated 2D Laplacian variance metric")
    threshold: float = Field(..., description="Configured blur threshold limit")
    can_analyze: bool = Field(..., description="Whether this image passes quality validation and may proceed to OCR/AI analysis")
    width: Optional[int] = None
    height: Optional[int] = None
    reason: Optional[str] = None
    message: str = Field(..., description="Human-readable assessment and instructions")
    validation_timestamp: Optional[str] = None


class ScanCreateRequest(BaseModel):
    product_id: Optional[str] = None
    batch_number: Optional[str] = None
    lot_number: Optional[str] = None
    source: ScanSourceEnum = ScanSourceEnum.PHYSICAL_STORE
    source_url: Optional[str] = None
    location_name: Optional[str] = None
    gps_coordinates: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    product_data: Optional[ProductCreate] = None


class ScanDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: Optional[str] = None
    inspector_id: str
    source: ScanSourceEnum
    source_url: Optional[str] = None
    status: ScanStatusEnum
    location_name: Optional[str] = None
    gps_coordinates: Optional[str] = None
    batch_number: Optional[str] = None
    batch_number_extracted: Optional[str] = None
    batch_number_confidence: Optional[float] = 0.0
    batch_number_source: Optional[str] = "manual"
    batch_status: Optional[str] = "normal"
    batch_discrepancy: bool = False
    related_batch_scans_count: int = 0
    batch_attention_required: bool = False
    derived_status: Optional[str] = None
    auto_confirmed_count: int = 0
    inspector_resolved_count: int = 0
    unresolved_count: int = 0
    ready_for_finalization: bool = False
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    
    # Nested relations
    inspector: Optional[UserResponse] = None
    product: Optional[ProductResponse] = None
    images: List[ScanImageResponse] = Field(default_factory=list)
    declarations: List[DeclarationResponse] = Field(default_factory=list)


class ScanListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_category: Optional[str] = None
    batch_number: Optional[str] = None
    batch_status: Optional[str] = "normal"
    inspector_id: str
    inspector_name: Optional[str] = None
    source: ScanSourceEnum
    status: ScanStatusEnum
    location_name: Optional[str] = None
    region: Optional[str] = None
    total_declarations: int = 0
    non_compliant_count: int = 0
    overall_verdict: Optional[str] = None
    created_at: datetime


class AnalyzeScanResponse(BaseModel):
    job_id: str
    scan_id: str
    status: str
    message: str


class CloseScanRequest(BaseModel):
    notes: Optional[str] = None
    final_status: Optional[ScanStatusEnum] = ScanStatusEnum.CLOSED


class ScanFinalizeRequest(BaseModel):
    final_decision: Optional[str] = Field(None, description="Optional override ('compliant', 'non_compliant', 'needs_review'); if omitted, derived from declaration findings")
    remarks: Optional[str] = Field(None, description="Optional officer inspection remarks")


class BatchVerifyRequest(BaseModel):
    batch_number: str = Field(..., min_length=1, description="Verified or corrected batch/lot number")
    notes: Optional[str] = None


class BatchStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="'normal', 'attention_required', 'under_investigation', or 'resolved'")
    notes: Optional[str] = None


class BatchInspectionItem(BaseModel):
    id: str
    created_at: datetime
    status: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    product_category: Optional[str] = None
    inspector_id: str
    inspector_name: Optional[str] = None
    location_name: Optional[str] = None
    region: Optional[str] = None
    compliance_status: str
    findings_count: int = 0
    non_compliant_count: int = 0
    human_decision: Optional[str] = None
    image_url: Optional[str] = None


class BatchFindingSummary(BaseModel):
    field_type: str
    rule_reference: str
    count: int
    severity: str


class BatchDetailResponse(BaseModel):
    batch_number: str
    status: str  # normal, attention_required, under_investigation, resolved
    total_inspections: int = 0
    compliant_inspections: int = 0
    non_compliant_inspections: int = 0
    manual_review_inspections: int = 0
    first_inspection_date: Optional[datetime] = None
    latest_inspection_date: Optional[datetime] = None
    products: List[Dict[str, Any]] = Field(default_factory=list)
    findings_summary: List[BatchFindingSummary] = Field(default_factory=list)
    inspections: List[BatchInspectionItem] = Field(default_factory=list)


class BatchSummaryResponse(BaseModel):
    batch_number: str
    status: str
    product_name: Optional[str] = None
    product_brand: Optional[str] = None
    total_inspections: int = 0
    non_compliant_count: int = 0
    attention_required: bool = False
    latest_inspection_date: Optional[datetime] = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    metadata_json: Dict[str, Any] = Field(default_factory=dict)

