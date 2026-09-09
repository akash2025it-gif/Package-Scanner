from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.audit import AuditService
from app.core.database import get_db
from app.core.exceptions import ConflictException, NotFoundException
from app.core.rbac import require_admin
from app.core.security import hash_password
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users (Admin Only)"])


@router.get("", response_model=APIResponse[PaginatedResponse[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    role: Optional[str] = None,
    region: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """List all system users with filtering and pagination (Admin only)."""
    query = select(User)
    
    if role:
        query = query.where(User.role == role)
    if region:
        query = query.where(User.region == region)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                User.name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.department.ilike(search_pattern),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_count = (await db.execute(count_query)).scalar_one()

    # Apply pagination and sorting
    query = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()

    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

    return APIResponse(
        success=True,
        data=PaginatedResponse(
            items=[UserResponse.model_validate(u) for u in users],
            pagination=PaginationMeta(
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        ),
    )


@router.post("", response_model=APIResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Create a new user/officer account."""
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise ConflictException("User with this email already exists")

    hashed_pw = hash_password(payload.password) if payload.password else None

    user = User(
        id=str(uuid.uuid4()),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        password_hash=hashed_pw,
        role=payload.role.value,
        department=payload.department,
        region=payload.region,
        is_active=payload.is_active,
    )
    db.add(user)
    
    await AuditService.log_action(
        db=db,
        action="USER_CREATED",
        entity_type="user",
        entity_id=user.id,
        user_id=admin_user.id,
        metadata={"email": user.email, "role": user.role},
    )

    await db.commit()
    await db.refresh(user)

    return APIResponse(
        success=True,
        message="User created successfully",
        data=UserResponse.model_validate(user),
    )


@router.get("/{id}", response_model=APIResponse[UserResponse])
async def get_user_by_id(
    id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException(f"User {id} not found")
    return APIResponse(success=True, data=UserResponse.model_validate(user))


@router.patch("/{id}", response_model=APIResponse[UserResponse])
async def update_user(
    id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException(f"User {id} not found")

    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.role is not None:
        user.role = payload.role.value
    if payload.department is not None:
        user.department = payload.department
    if payload.region is not None:
        user.region = payload.region
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password:
        user.password_hash = hash_password(payload.password)

    await AuditService.log_action(
        db=db,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        user_id=admin_user.id,
        metadata={"updated_fields": payload.model_dump(exclude_unset=True, exclude={"password"})},
    )

    await db.commit()
    await db.refresh(user)

    return APIResponse(
        success=True,
        message="User updated successfully",
        data=UserResponse.model_validate(user),
    )


@router.delete("/{id}", response_model=APIResponse[dict])
async def delete_user(
    id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    result = await db.execute(select(User).where(User.id == id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundException(f"User {id} not found")

    user.is_active = False
    await AuditService.log_action(
        db=db,
        action="USER_DEACTIVATED",
        entity_type="user",
        entity_id=user.id,
        user_id=admin_user.id,
    )
    await db.commit()

    return APIResponse(success=True, message=f"User {id} deactivated successfully", data={})
