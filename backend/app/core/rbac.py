from enum import Enum
from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False
)


class UserRole(str, Enum):
    INSPECTOR = "inspector"
    ADMIN = "admin"


VALID_ACTIVE_ROLES = {UserRole.INSPECTOR.value, UserRole.ADMIN.value}


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    if not token:
        raise UnauthorizedException("Authentication token required")
    
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid token type")
        
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Malformed token payload")

    # Reject tokens issued for obsolete/removed roles
    token_role = str(payload.get("role") or "").lower().strip()
    if token_role and token_role not in VALID_ACTIVE_ROLES:
        raise ForbiddenException("Account role is obsolete or unauthorized. Only Inspector and Admin accounts are authorized.")
        
    # Lazy import to avoid circular dependencies
    from app.models.user import User
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise UnauthorizedException("User not found or deactivated")
    if not user.is_active:
        raise ForbiddenException("User account is inactive")
    if user.role.lower() not in VALID_ACTIVE_ROLES:
        raise ForbiddenException("Account role is obsolete or unauthorized. Only Inspector and Admin accounts are authorized.")
        
    return user


async def get_current_active_user(
    current_user = Depends(get_current_user),
):
    if not current_user.is_active:
        raise ForbiddenException("User account is inactive")
    if current_user.role.lower() not in VALID_ACTIVE_ROLES:
        raise ForbiddenException("Account role is obsolete or unauthorized")
    return current_user


def require_roles(allowed_roles: List[UserRole]):
    async def role_checker(current_user = Depends(get_current_active_user)):
        user_role = str(current_user.role).lower()
        allowed_roles_str = [r.value.lower() for r in allowed_roles]
        if user_role not in allowed_roles_str and user_role != UserRole.ADMIN.value:
            raise ForbiddenException(
                f"Access denied: operation requires one of the following roles: {allowed_roles_str}"
            )
        return current_user
    return role_checker


# Dedicated RBAC dependencies
require_admin = require_roles([UserRole.ADMIN])
require_inspector = require_roles([UserRole.INSPECTOR, UserRole.ADMIN])
require_can_scan = require_roles([UserRole.INSPECTOR, UserRole.ADMIN])
require_can_review = require_roles([UserRole.INSPECTOR, UserRole.ADMIN])
require_inspector_or_above = require_can_scan
require_reviewer_or_above = require_can_review
