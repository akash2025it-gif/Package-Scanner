from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Declaration(Base):
    __tablename__ = "declarations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id: Mapped[str] = mapped_column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # mrp, net_quantity, mfg_date, expiry_date, manufacturer_details, consumer_care, country_of_origin, unit_sale_price, common_name, best_before, other
    field_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_extracted_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_numeric_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    normalized_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conflict_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Bounding box JSON: {x: float, y: float, w: float, h: float} normalized or pixels
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    font_size_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    is_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rule_reference: Mapped[str] = mapped_column(String(255), nullable=False, default="LMPC Rules 2011")
    severity: Mapped[str] = mapped_column(String(50), nullable=False, default="none")  # none, minor, major, critical
    
    reviewer_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_ai_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    original_ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Violation Detection Rate & Workflow Automation Fields
    violation_detection_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auto_confirm_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    workflow_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # AUTO_CONFIRMED, MANUAL_REVIEW_REQUIRED, FINALIZED
    decision_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # SYSTEM_THRESHOLD, MANUAL, AUTOMATIC
    decision_reason: Mapped[Optional[Text]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # AUTO_CONFIRMED, MANUAL_REVIEW_REQUIRED, INSPECTOR_CONFIRMED, INSPECTOR_REJECTED, INSPECTOR_OVERRIDDEN, FINALIZED
    verification_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # SYSTEM_THRESHOLD, INSPECTOR, MANUAL

    human_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # confirmed, rejected, overridden
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    scan = relationship("Scan", back_populates="declarations")

