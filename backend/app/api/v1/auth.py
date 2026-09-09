from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.rbac import get_current_active_user
from app.core.security import create_access_token, create_refresh_token, decode_token, verify_password
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.user import LoginRequest, RefreshTokenRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate via email + password or phone + OTP."""
    user = None
    if payload.email:
        result = await db.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
        
        if not user or not user.password_hash or not verify_password(payload.password or "", user.password_hash):
            raise UnauthorizedException("Invalid email or password")
            
    elif payload.phone:
        result = await db.execute(select(User).where(User.phone == payload.phone))
        user = result.scalar_one_or_none()
        
        # Simulated OTP validation (default demo OTP: '123456')
        if not user or (payload.otp != "123456" and not verify_password(payload.password or "", user.password_hash or "")):
            raise UnauthorizedException("Invalid phone number or OTP")
    else:
        raise ValidationException("Must provide either email and password or phone and OTP")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive. Please contact administrator.")
    if user.role.lower() not in ["admin", "inspector"]:
        raise UnauthorizedException("Account role is obsolete or unauthorized. Access denied.")

    access_token = create_access_token(subject=user.id, role=user.role)
    refresh_token = create_refresh_token(subject=user.id)

    return APIResponse(
        success=True,
        message="Login successful",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=60 * 24 * 60,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_tokens(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Refreshes access token given a valid refresh token."""
    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    user_id = token_data.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    if user.role.lower() not in ["admin", "inspector"]:
        raise UnauthorizedException("Account role is obsolete or unauthorized. Access denied.")

    new_access_token = create_access_token(subject=user.id, role=user.role)
    new_refresh_token = create_refresh_token(subject=user.id)

    return APIResponse(
        success=True,
        message="Tokens refreshed successfully",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=60 * 24 * 60,
            user=UserResponse.model_validate(user),
        ),
    )


@router.post("/logout", response_model=APIResponse[dict])
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logs out user session."""
    return APIResponse(success=True, message="Logged out successfully", data={})


@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Returns current user's profile and RBAC role."""
    return APIResponse(
        success=True,
        data=UserResponse.model_validate(current_user),
    )
