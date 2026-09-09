from datetime import datetime, timezone
from typing import List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    inspector_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="physical_store")  # physical_store, ecommerce
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing", index=True)  # processing, needs_review, reviewed, closed
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gps_coordinates: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    batch_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    batch_number_extracted: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    batch_number_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    batch_number_source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="manual")  # manual, ocr, verified
    batch_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="normal")  # normal, attention_required, under_investigation, resolved
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    inspector = relationship("User", back_populates="scans")
    product = relationship("Product", back_populates="scans")
    images: Mapped[List["ScanImage"]] = relationship("ScanImage", back_populates="scan", cascade="all, delete-orphan")
    declarations: Mapped[List["Declaration"]] = relationship("Declaration", back_populates="scan", cascade="all, delete-orphan")
    reports: Mapped[List["ComplianceReport"]] = relationship("ComplianceReport", back_populates="scan", cascade="all, delete-orphan")


class ScanImage(Base):
    __tablename__ = "scan_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id: Mapped[str] = mapped_column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url: Mapped[str] = mapped_column(Text, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    image_type: Mapped[str] = mapped_column(String(50), nullable=False, default="front")  # front, back, top, bottom, side, other
    width_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height_px: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Image Quality & Blur Validation Gate
    image_quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="CLEAR")  # CLEAR, BLURRY, LOW_QUALITY, FAILED
    sharpness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    analysis_allowed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=True)
    quality_details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Relationships
    scan = relationship("Scan", back_populates="images")
