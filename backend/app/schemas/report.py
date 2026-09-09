from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class OverallStatusEnum(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NEEDS_REVIEW = "needs_review"


class ComplianceReportCreateRequest(BaseModel):
    notes: Optional[str] = None
    custom_summary: Optional[str] = None


class ComplianceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scan_id: str
    generated_by: str
    overall_status: OverallStatusEnum
    pdf_url: Optional[str] = None
    docx_url: Optional[str] = None
    summary_data: Optional[Dict[str, Any]] = None
    generated_at: datetime
