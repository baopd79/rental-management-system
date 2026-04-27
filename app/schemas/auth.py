import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.core.enums import UserRole

# Password — bcrypt 72-byte limit + complexity validated below
Password = Annotated[str, Field(min_length=8, max_length=72)]

# Full name — strip whitespace, 1-255 chars
FullName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

# Phone — regex match OpenAPI spec
PHONE_REGEX = r"^[0-9+\-\s]{8,20}$"
Phone = Annotated[str, Field(pattern=PHONE_REGEX)]


def _normalize_email(v: str) -> str:
    return v.strip().lower() if isinstance(v, str) else v


NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]


class RegisterRequest(BaseModel):
    """Landlord self-registration. Tenant goes through invite flow."""

    email: NormalizedEmail
    password: Password
    full_name: FullName
    phone: Phone | None = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """Require lowercase + uppercase + digit."""
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain lowercase letter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain uppercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain digit")
        return v


class LoginRequest(BaseModel):
    """Email + password login."""

    email: NormalizedEmail
    password: str  # KHÔNG validate complexity ở login (user đã có pass weak từ trước → cứ nhận)


class UserRead(BaseModel):
    """Public user profile. NEVER includes password_hash."""

    id: UUID
    email: EmailStr
    role: UserRole
    full_name: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthSuccessResponse(BaseModel):
    """Returned by /register and /login. Matches OpenAPI TokenResponse + user."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds, copy từ JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    user: UserRead
