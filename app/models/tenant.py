# stdlib
from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr

# third-party
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

# local
from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class TenantBase(SQLModel):
    """Shared fields for Tenant (domain info, no auth secrets)."""

    full_name: str = Field(
        max_length=200,
        description="Full name của tenant, NOT NULL",
    )
    phone: str = Field(
        max_length=20,
        description="Phone number của tenant, NOT NULL",
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Email của tenant, nullable (không bắt buộc, có thể dùng phone để contact)",
    )
    id_card_number: str | None = Field(
        default=None,
        max_length=20,
        description="Số CCCD/CMND của tenant, nullable (không bắt buộc)",
    )
    birth_date: date | None = Field(
        default=None,
        description="Ngày sinh của tenant, nullable",
    )
    hometown: str | None = Field(
        default=None,
        max_length=200,
        description="Quê quán của tenant, nullable",
    )
    note: str | None = Field(
        default=None,
        description="Landlord internal note về tenant, nullable",
    )


class Tenant(TenantBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`tenants` table — thông tin tenant + lifecycle fields."""

    __tablename__ = "tenants"
    move_out_date: date | None = Field(
        default=None,
        description="Ngày thực tế tenant dọn đi, nullable (để track lịch sử occupancy)",
    )
    is_archived: bool = Field(
        default=False,
        description="ADR-0001: soft delete pattern. True khi tenant dọn đi",
    )
    archived_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp khi tenant bị archive, nullable",
    )
    anonymized_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="ADR-0006: Timestamp khi tenant bị anonymize, nullable",
    )
    user_id: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        description="Link đến User account nếu tenant đã accept invite, nullable",
    )
    landlord_id: UUID = Field(
        foreign_key="users.id",
        description="Landlord sở hữu tenant này (1 Landlord → N Tenants)",
    )
    promoted_from_occupant_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey(
                "occupants.id",
                use_alter=True,
                name="fk_tenants_promoted_from_occupant_id_occupants",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        description="...",
    )


class TenantCreate(TenantBase):
    """Schema để tạo tenant mới — dùng trong API endpoint."""

    pass  # kế thừa tất cả fields từ TenantBase, không có thêm gì


class TenantRead(TenantBase):
    """Schema để đọc tenant — dùng trong API response."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    move_out_date: date | None


class TenantUpdate(SQLModel):
    """Schema để cập nhật tenant — tất cả fields optional cho PATCH."""

    full_name: str | None = Field(
        default=None,
        max_length=200,
        description="Full name của tenant, optional",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        description="Phone number của tenant, optional",
    )
    email: EmailStr | None = Field(
        default=None,
        max_length=255,
        description="Email của tenant, optional",
    )
    id_card_number: str | None = Field(
        default=None,
        max_length=20,
        description="Số CCCD/CMND của tenant, optional",
    )
    birth_date: date | None = Field(
        default=None,
        description="Ngày sinh của tenant, optional",
    )
    hometown: str | None = Field(
        default=None,
        max_length=200,
        description="Quê quán của tenant, optional",
    )
    note: str | None = Field(
        default=None,
        description="Landlord internal note về tenant, optional",
    )
