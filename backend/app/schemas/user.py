from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRoleEnum(str, Enum):
    INSPECTOR = "inspector"
    ADMIN = "admin"


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    role: str = "inspector"
    department: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    role: UserRoleEnum = UserRoleEnum.INSPECTOR
    department: Optional[str] = Field(None, max_length=255)
    region: Optional[str] = Field(None, max_length=100)
    is_active: bool = True
    password: Optional[str] = Field(None, min_length=6)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    department: Optional[str] = None
    region: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=6)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    otp: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    refresh_token: str
