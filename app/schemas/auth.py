from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field, field_validator
from sqlmodel import SQLModel

from app.core.enums import UserRole


class RegisterRequest(SQLModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, pattern=r"^[0-9+\-\s]{8,20}$")

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(SQLModel):
    email: EmailStr
    password: str


class UserResponse(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(SQLModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int


class AuthSuccessResponse(TokenResponse):
    user: UserResponse
