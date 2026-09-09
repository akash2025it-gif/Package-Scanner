from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.core.rbac import get_current_active_user, require_can_review
from app.models import ComplianceReport, Scan, User
from app.schemas.common import APIResponse
from app.schemas.report import ComplianceReportCreateRequest, ComplianceReportResponse
from app.services.reports.generator import ReportCoordinator
from app.services.storage import get_storage_service

router = APIRouter(prefix="", tags=["Compliance Reports"])


@router.post("/scans/{id}/report", response_model=APIResponse[ComplianceReportResponse], status_code=status.HTTP_201_CREATED)
async def generate_scan_report(
    id: str,
    payload: ComplianceReportCreateRequest = ComplianceReportCreateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_can_review),
):
    """Generates official statutory PDF + editable DOCX compliance reports for a scan."""
    coordinator = ReportCoordinator()
    report = await coordinator.generate_scan_report(
        db=db,
        scan_id=id,
        user_id=current_user.id,
        notes=payload.notes,
    )

    return APIResponse(
        success=True,
        message="Compliance report generated successfully",
        data=ComplianceReportResponse.model_validate(report),
    )


@router.get("/reports/{id}", response_model=APIResponse[ComplianceReportResponse])
async def get_report_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Retrieves report metadata and document download links."""
    result = await db.execute(select(ComplianceReport).where(ComplianceReport.id == id))
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundException(f"Compliance report {id} not found")

    return APIResponse(
        success=True,
        data=ComplianceReportResponse.model_validate(report),
    )


@router.get("/reports/{id}/pdf")
async def download_pdf_report(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Streams the generated PDF report."""
    result = await db.execute(select(ComplianceReport).where(ComplianceReport.id == id))
    report = result.scalar_one_or_none()
    if not report or not report.summary_data:
        raise NotFoundException(f"Compliance report {id} not found")

    storage_service = get_storage_service()
    coordinator = ReportCoordinator()
    pdf_bytes = coordinator.pdf_generator.generate_pdf_bytes(report.summary_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="compliance_report_{report.scan_id}.pdf"'},
    )


@router.get("/reports/{id}/docx")
async def download_docx_report(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Streams the editable DOCX compliance report."""
    result = await db.execute(select(ComplianceReport).where(ComplianceReport.id == id))
    report = result.scalar_one_or_none()
    if not report or not report.summary_data:
        raise NotFoundException(f"Compliance report {id} not found")

    coordinator = ReportCoordinator()
    docx_bytes = coordinator.docx_generator.generate_docx_bytes(report.summary_data)

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="compliance_report_{report.scan_id}.docx"'},
    )
