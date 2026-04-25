"""
Room model — Nhóm 2: Property + Room.

Decisions applied:
- ADR-0001 soft delete: is_archived + archived_at
- display_name unique per property WHERE NOT archived (partial index, manual ở migration)
- Post-review fix: thêm max_occupants (US-034 AC3)
- description: free text thay asset management (MVP)
- default_rent: nullable, chỉ là default khi tạo Lease (Lease snapshot giá)
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class RoomBase(SQLModel):
    """Shared fields cho Room."""

    display_name: str = Field(
        max_length=100,
        description='Tên phòng free text, ví dụ "P101", "Phòng A1". '
        "Unique per property WHERE NOT archived (partial index).",
    )
    default_rent: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="Giá mặc định khi tạo Lease. Lease snapshot giá, "
        "không dùng live value này để tính Invoice.",
    )
    description: str | None = Field(
        default=None,
        description="Mô tả tài sản trong phòng (thay asset management MVP). "
        "Free text, text type (không limit length).",
    )
    max_occupants: int | None = Field(
        default=None,
        description="Giới hạn số người (Tenant + Occupants). NULL = không giới hạn. US-034 AC3.",
    )


class Room(RoomBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`rooms` table.

    Note về unique constraint:
    `display_name` unique per property, nhưng chỉ cho active (is_archived=FALSE).
    Archived room giữ display_name cũ, không conflict với room mới cùng tên.
    → Partial unique index, không dùng UniqueConstraint bình thường.
    → Define ở Alembic migration (autogenerate không support partial index).
    """

    __tablename__ = "rooms"

    __table_args__ = (
        CheckConstraint(
            "max_occupants IS NULL OR max_occupants > 0",
            name="max_occupants_positive",
        ),
    )

    property_id: UUID = Field(
        foreign_key="properties.id",
        description="Property chứa room này",
    )

    # ADR-0001 soft delete pattern
    is_archived: bool = Field(
        default=False,
        description="ADR-0001 pattern: soft delete. "
        "Invariant: is_archived=TRUE iff archived_at IS NOT NULL.",
    )
    archived_at: datetime | None = Field(
        default=None,
        description="Timestamp khi archive. NULL iff is_archived=FALSE.",
    )


# ============================================================
# API schemas
# ============================================================


class RoomCreate(RoomBase):
    """Input — property_id trong URL path."""

    pass


class RoomRead(RoomBase):
    """Output — KHÔNG expose is_archived, archived_at (Rule 4 ADR-0001).

    Client thấy `status` computed (vacant/occupied/expiring_soon/lease_expired)
    thay vì raw is_archived — service layer compute tại query time.
    """

    id: UUID
    property_id: UUID
    created_at: datetime
    updated_at: datetime


class RoomUpdate(SQLModel):
    """PATCH input — chỉ cho sửa domain fields, không cho sửa lifecycle."""

    display_name: str | None = None
    default_rent: Decimal | None = None
    description: str | None = None
    max_occupants: int | None = None
