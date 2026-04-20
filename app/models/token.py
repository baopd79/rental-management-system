"""
Token models — Nhóm 1: Auth.

3 loại token tách bảng riêng (không gộp 1 bảng với `type` enum):
- InviteToken: Landlord mời Tenant (TTL 7d, ref Tenant + email chưa có User)
- PasswordResetToken: User reset password (TTL 1h)
- RefreshToken: JWT refresh với rotation chain (TTL 7d)

Lý do tách bảng:
- Field đặc thù khác nhau (invite có invited_email, refresh có rotated_to_id)
- Cleanup job per table (TTL khác nhau)
- Query frequency khác (refresh hot, invite/reset cold)

Common pattern (không làm base class vì 3 bảng có constraints và FK khác nhau):
- token_hash: SHA-256 hash của opaque token (không lưu raw)
- expires_at: NOT NULL, TTL khác nhau
- created_at only (CreatedAtOnlyMixin — token không UPDATE)
"""

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.db.base import CreatedAtOnlyMixin, UUIDPrimaryKeyMixin


# ============================================================
# InviteToken — US-004 Landlord mời Tenant
# ============================================================

class InviteTokenBase(SQLModel):
    """Shared fields cho invite token."""

    invited_email: EmailStr = Field(
        max_length=255,
        description="Email sẽ dùng làm login sau khi accept (có thể khác tenant.email)",
    )


class InviteToken(
    InviteTokenBase, UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True
):
    """`invite_tokens` table — TTL 7 ngày, single-use."""

    __tablename__ = "invite_tokens"

    token_hash: str = Field(
        max_length=128,
        unique=True,
        index=True,
        description="SHA-256 của opaque token (lưu hash, không lưu raw)",
    )
    tenant_id: UUID = Field(
        foreign_key="tenants.id",
        description="Tenant được invite",
    )
    created_by_user_id: UUID = Field(
        foreign_key="users.id",
        description="Landlord tạo invite",
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="TTL 7 ngày từ created_at",
    )
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="NULL = chưa dùng. NOT NULL = đã accept (single-use)",
    )


# ============================================================
# PasswordResetToken — reset password flow
# ============================================================

class PasswordResetToken(UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True):
    """`password_reset_tokens` table — TTL 1 giờ, single-use."""

    __tablename__ = "password_reset_tokens"

    token_hash: str = Field(
        max_length=128,
        unique=True,
        index=True,
    )
    user_id: UUID = Field(
        foreign_key="users.id",
        description="User yêu cầu reset password",
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="TTL 1 giờ từ created_at",
    )
    used_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )


# ============================================================
# RefreshToken — JWT refresh với rotation chain
# ============================================================

class RefreshToken(UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True):
    """`refresh_tokens` table — rotation chain for theft detection.

    Rotation logic (implement ở Phase 4):
    - Client dùng refresh → cấp access mới + refresh mới → revoke refresh cũ
    - Nếu refresh cũ (đã rotated_to_id) được dùng lại → dấu hiệu theft →
      revoke toàn bộ chain
    """

    __tablename__ = "refresh_tokens"

    token_hash: str = Field(
        max_length=128,
        unique=True,
        index=True,
    )
    user_id: UUID = Field(
        foreign_key="users.id",
        description="User sở hữu token",
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        description="TTL 7 ngày từ created_at",
    )
    revoked_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="NULL = active. NOT NULL = đã revoke (logout/rotation/theft)",
    )
    rotated_to_id: UUID | None = Field(
        default=None,
        foreign_key="refresh_tokens.id",
        description="Self-FK: token này được rotate thành token nào. "
                    "NULL = chưa rotate hoặc token mới nhất.",
    )


# ============================================================
# API schemas (minimal — tokens ít khi expose ra client)
# ============================================================

class InviteTokenCreate(SQLModel):
    """Input khi Landlord gửi invite — service layer tự sinh token_hash + expires_at."""

    tenant_id: UUID
    invited_email: EmailStr
