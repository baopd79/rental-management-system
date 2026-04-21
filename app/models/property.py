"""
Property model — Nhóm 2: Property + Room.

Decisions applied:
- billing_day ở Property level (Edge case 1 post-review: hybrid Option B)
  Property có billing_day làm template, Lease snapshot khi ký
- Hard delete: Property chỉ xóa được khi hết Room (enforce ở service layer)
- address: free text string, không validate (Edge case 3 post-review)
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class PropertyBase(SQLModel):
    """Shared fields cho Property."""

    name: str = Field(
        max_length=200,
        description='Ví dụ "Nhà trọ Cầu Giát 1"',
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        description="Free text, không structured (MVP)",
    )
    billing_day: int = Field(
        ge=1,
        le=28,
        description="Ngày billing default cho Property, [1, 28]. "
        "Lease snapshot khi ký (Lease có billing_day riêng).",
    )


class Property(PropertyBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`properties` table."""

    __tablename__ = "properties"

    # CHECK constraint cho billing_day — enforce ở DB level, không chỉ Pydantic
    __table_args__ = (
        CheckConstraint(
            "billing_day BETWEEN 1 AND 28",
            name="billing_day_range",
        ),
    )

    landlord_id: UUID = Field(
        foreign_key="users.id",
        description="Landlord sở hữu property này (1 Landlord → N Properties)",
    )


# ============================================================
# API schemas
# ============================================================


class PropertyCreate(PropertyBase):
    """Input khi Landlord tạo Property — landlord_id inject từ JWT."""

    pass


class PropertyRead(PropertyBase):
    """Output — không expose landlord_id (redundant với ownership context)."""

    id: UUID
    created_at: datetime
    updated_at: datetime


class PropertyUpdate(SQLModel):
    """PATCH input — tất cả optional."""

    name: str | None = None
    address: str | None = None
    billing_day: int | None = Field(default=None, ge=1, le=28)
