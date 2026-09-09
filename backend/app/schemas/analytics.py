from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CategoryViolationStat(BaseModel):
    category: str
    total_scans: int
    violations_count: int
    compliance_rate: float


class RuleViolationStat(BaseModel):
    rule_reference: str
    field_type: str
    count: int
    severity: str


class TrendDataPoint(BaseModel):
    date: str
    total_scans: int
    compliant_scans: int
    non_compliant_scans: int
    needs_review_scans: int = 0


class ViolationFindingItem(BaseModel):
    finding_name: str
    field_type: str
    rule_reference: str
    affected_inspections: int
    total_violations: int = 0
    percentage_of_non_compliant: float = 0.0
    severity: str = "major"


class ProductRiskItem(BaseModel):
    category: str
    total_inspections: int
    non_compliant_count: int
    compliant_count: int
    needs_review_count: int
    compliance_rate: Optional[float] = None
    violation_rate: Optional[float] = None
    risk_level: str = "LOW"  # HIGH, MEDIUM, LOW, INSUFFICIENT_DATA


class AttentionInspectionItem(BaseModel):
    id: str
    product_name: str
    product_brand: Optional[str] = None
    product_category: Optional[str] = None
    inspector_name: Optional[str] = None
    location_name: Optional[str] = None
    status: str
    final_decision: Optional[str] = None
    created_at: str
    findings_count: int = 0
    violations_count: int = 0
    needs_review_count: int = 0
    min_confidence: Optional[float] = None
    attention_reason: str = "Requires Officer Review"


class OfficerActivityItem(BaseModel):
    officer_id: str
    officer_name: str
    department: Optional[str] = None
    region: Optional[str] = None
    total_inspections: int
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int
    finalized_count: int


class RegionHeatmapItem(BaseModel):
    region: str
    state_code: Optional[str] = None
    total_inspections: int
    compliant_count: int
    non_compliant_count: int
    needs_review_count: int = 0
    violation_rate: float
    top_violated_rule: Optional[str] = None


class OfficerPerformanceItem(BaseModel):
    officer_id: str
    officer_name: str
    region: Optional[str] = None
    total_scans: int
    reviewed_count: int
    pending_review_count: int
    average_review_time_hours: float
    violations_detected: int


class BatchAlertItem(BaseModel):
    batch_number: str
    product_name: str
    product_brand: Optional[str] = None
    reason: str = "Verified defect found in associated inspection"
    related_inspections: int = 0
    non_compliant_inspections: int = 0
    status: str = "attention_required"
    latest_inspection_date: Optional[str] = None


class AnalyticsSummaryResponse(BaseModel):
    # Backward compatibility fields
    total_scans: int
    total_products: int
    total_violations: int
    overall_compliance_percentage: float
    scans_needing_review: int
    scans_closed: int
    violations_by_category: List[CategoryViolationStat] = Field(default_factory=list)
    violations_by_rule: List[RuleViolationStat] = Field(default_factory=list)
    trend_over_time: List[TrendDataPoint] = Field(default_factory=list)

    # Enforcement Intelligence Dashboard Fields
    total_inspections: int = 0
    compliant_count: int = 0
    non_compliant_count: int = 0
    needs_review_count: int = 0
    finalized_count: int = 0
    compliance_rate: Optional[float] = None
    violation_rate: Optional[float] = None
    compliance_distribution: Dict[str, int] = Field(default_factory=dict)
    dynamic_insights: List[str] = Field(default_factory=list)
    available_categories: List[str] = Field(default_factory=list)
    available_regions: List[str] = Field(default_factory=list)
    most_common_findings: List[ViolationFindingItem] = Field(default_factory=list)
    product_risk_overview: List[ProductRiskItem] = Field(default_factory=list)
    attention_inspections: List[AttentionInspectionItem] = Field(default_factory=list)
    officer_activity: List[OfficerActivityItem] = Field(default_factory=list)
    regional_overview: List[RegionHeatmapItem] = Field(default_factory=list)

    # Batch Intelligence Fields
    batches_inspected: int = 0
    batches_attention_required: int = 0
    batches_under_investigation: int = 0
    frequently_flagged_batches: List[BatchAlertItem] = Field(default_factory=list)
    batch_investigation_alerts: List[BatchAlertItem] = Field(default_factory=list)

    # Compliance Automation Finding Fields
    automatically_confirmed_findings_count: int = 0
    manual_review_findings_count: int = 0
    automatic_confirmation_rate: Optional[float] = None
