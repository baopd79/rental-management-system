"""
User model — Nhóm 1: Auth.

Decisions applied:
- ADR-0005: role enum 2 giá trị (landlord, tenant) cho MVP
- ADR-0006: consent_at timestamp cho GDPR/Nghị định 13/2023
- Post-review fix: thêm full_name + phone (Landlord profile, nullable)
- Pattern ADR-0001: is_active (feature toggle), không dùng is_archived
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.core.enums import UserRole
from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, create_pg_enum

# ============================================================
# Base schema — fields shared across all variants
# ============================================================


class UserBase(SQLModel):
    """Shared fields for User (domain info, no auth secrets)."""

    email: EmailStr = Field(
        max_length=255,
        unique=True,
        index=True,
        description="Dùng để login, unique global",
    )
    role: UserRole = Field(
        sa_type=create_pg_enum(UserRole),
        sa_column_kwargs={"nullable": False},
        description="ADR-0005: landlord hoặc tenant",
    )
    full_name: str | None = Field(
        default=None,
        max_length=200,
        description="Landlord profile, nullable cho Tenant (info ở Tenant entity)",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Landlord profile, không unique (không dùng làm identifier)",
    )


# ============================================================
# Table model — actual DB table
# ============================================================


class User(UserBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`users` table — auth + profile info."""

    __tablename__ = "users"

    password_hash: str = Field(
        max_length=255,
        description="bcrypt/argon2 hash, không bao giờ expose ra API",
    )
    is_active: bool = Field(
        default=True,
        description="ADR-0001 feature toggle. False khi Tenant archive → account invalidate",
    )
    consent_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="ADR-0006: timestamp Tenant accept ToS/privacy",
    )
    last_login_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="UX + audit — cập nhật khi login thành công",
    )


# ============================================================
# API schemas — input/output variants
# ============================================================


class UserCreate(UserBase):
    """Input schema khi tạo User (internal — qua signup hoặc invite accept).

    Note: password là raw, hash ở service layer trước khi persist.
    """

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Raw password, hash bcrypt/argon2 trước khi lưu",
    )


class UserRead(UserBase):
    """Output schema — an toàn để expose ra API.

    KHÔNG expose: password_hash, is_active (Rule 4 ADR-0001),
    consent_at (internal), last_login_at (chỉ admin view).
    """

    id: UUID
    created_at: datetime


class UserUpdate(SQLModel):
    """Input schema cho PATCH — tất cả fields optional.

    Lưu ý:
    - email không cho sửa qua đây (cần flow riêng với verify)
    - role không cho sửa (security-sensitive, admin only)
    - password đổi qua flow riêng (US-007 change password)
    """

    full_name: str | None = None
    phone: str | None = None
