from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import AuditService
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ValidationException
from app.core.rbac import get_current_active_user, require_admin
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/config/automation", tags=["Compliance Automation Configuration"])


class AutomationConfigResponse(BaseModel):
    auto_confirm_violation_threshold: float
    auto_confirm_threshold_percent: float
    description: str
    rule_definition: str
    statutory_disclaimer: str
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None


class AutomationConfigUpdateRequest(BaseModel):
    auto_confirm_violation_threshold: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Threshold percentage between 0 and 100 for automatic finding confirmation",
    )
    auto_confirm_threshold_percent: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Alias threshold percentage between 0 and 100",
    )
    notes: Optional[str] = None


# In-memory tracking of runtime updates to threshold
_runtime_config = {
    "threshold": settings.AUTO_CONFIRM_VIOLATION_THRESHOLD,
    "updated_at": None,
    "updated_by": "System Default",
}


def get_current_auto_confirm_threshold() -> float:
    """Returns the effective threshold for automatic confirmation."""
    return float(_runtime_config.get("threshold", settings.AUTO_CONFIRM_VIOLATION_THRESHOLD))


def set_current_auto_confirm_threshold(val: float, user_name: str = "Admin"):
    """Sets the runtime threshold."""
    _runtime_config["threshold"] = float(val)
    _runtime_config["updated_at"] = datetime.now(timezone.utc).isoformat()
    _runtime_config["updated_by"] = user_name


@router.get("", response_model=APIResponse[AutomationConfigResponse])
async def get_automation_config(
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves current compliance automation threshold and statutory rules.
    Accessible to authorized Inspectors and Admins.
    """
    threshold = get_current_auto_confirm_threshold()
    return APIResponse(
        success=True,
        message="Automation configuration retrieved successfully",
        data=AutomationConfigResponse(
            auto_confirm_violation_threshold=threshold,
            auto_confirm_threshold_percent=threshold,
            description="Findings with a violation detection rate greater than or equal to this threshold are automatically confirmed for inspection workflow.",
            rule_definition="Detection Rate >= Threshold -> AUTO-CONFIRMED; Detection Rate < Threshold -> MANUAL REVIEW REQUIRED",
            statutory_disclaimer="Workflow automation only. Final regulatory decisions remain under authorized human control.",
            updated_at=_runtime_config.get("updated_at"),
            updated_by=_runtime_config.get("updated_by"),
        ),
    )


@router.patch("", response_model=APIResponse[AutomationConfigResponse])
async def update_automation_config(
    payload: AutomationConfigUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Updates the automatic violation confirmation threshold.
    Strictly restricted to Admin role.
    """
    new_val = payload.auto_confirm_threshold_percent if payload.auto_confirm_threshold_percent is not None else payload.auto_confirm_violation_threshold
    if new_val is None:
        raise ValidationException("Threshold percentage must be specified.")
    if new_val < 0.0 or new_val > 100.0:
        raise ValidationException("Threshold must be a valid percentage between 0 and 100.")

    old_val = get_current_auto_confirm_threshold()
    set_current_auto_confirm_threshold(new_val, user_name=current_user.name)

    await AuditService.log_action(
        db=db,
        action="AUTOMATION_THRESHOLD_UPDATED",
        entity_type="system_config",
        entity_id="compliance_automation",
        user_id=current_user.id,
        metadata={
            "old_threshold": old_val,
            "new_threshold": new_val,
            "updated_by": current_user.name,
            "user_role": current_user.role,
            "notes": payload.notes or "Threshold updated via administration settings.",
        },
    )
    await db.commit()

    return APIResponse(
        success=True,
        message=f"Automatic confirmation threshold updated to {new_val:.1f}%",
        data=AutomationConfigResponse(
            auto_confirm_violation_threshold=new_val,
            auto_confirm_threshold_percent=new_val,
            description="Findings with a violation detection rate greater than or equal to this threshold are automatically confirmed for inspection workflow.",
            rule_definition="Detection Rate >= Threshold -> AUTO-CONFIRMED; Detection Rate < Threshold -> MANUAL REVIEW REQUIRED",
            statutory_disclaimer="Workflow automation only. Final regulatory decisions remain under authorized human control.",
            updated_at=_runtime_config.get("updated_at"),
            updated_by=current_user.name,
        ),
    )
