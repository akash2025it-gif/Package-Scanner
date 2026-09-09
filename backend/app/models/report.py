from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scan_id: Mapped[str] = mapped_column(String(36), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True)
    generated_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False, default="non_compliant")  # compliant, non_compliant, partially_compliant
    pdf_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    docx_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    scan = relationship("Scan", back_populates="reports")
    author = relationship("User", back_populates="reports")
