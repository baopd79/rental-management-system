"""
MeterReading model — Nhóm 6: Meter Reading (Chỉ số công tơ).

Decisions applied:
- Point-in-time schema: 1 record = 1 reading (không lưu cả kỳ old/new)
- room_id nullable: NULL = shared meter (1 công tơ cho nhóm), NOT NULL = per-room
- Append-only semantic: conceptually chỉ INSERT (UPDATE có điều kiện ở service layer)
- Reading mutability rules (enforce ở service, không DB):
  * Chưa ref Invoice → sửa thoải mái
  * Ref Invoice unpaid, no Payment → warn
  * Ref Invoice paid/partial → block
- Reading đã dùng cho Invoice → tracking qua invoice_line_items.meter_reading_*_id
- `service_id` phải là Service billing_type=per_meter (enforce ở service layer)
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin


class MeterReadingBase(SQLModel):
    """Shared fields cho reading."""

    reading_value: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Số trên công tơ tại reading_date. CHECK >= 0.",
    )
    reading_date: date = Field(
        description="Ngày đọc chỉ số",
    )
    note: str | None = Field(
        default=None,
        description="VD: 'Công tơ bị hỏng', 'Ước tính do không đọc được'",
    )


class MeterReading(MeterReadingBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`meter_readings` table."""

    __tablename__ = "meter_readings"

    __table_args__ = (
        CheckConstraint(
            "reading_value >= 0",
            name="value_non_negative",
        ),
    )

    service_id: UUID = Field(
        foreign_key="services.id",
        description="Service gắn reading (phải là billing_type=per_meter). "
        "Enforce ở service layer (DB không check enum tham chiếu).",
    )
    room_id: UUID | None = Field(
        default=None,
        foreign_key="rooms.id",
        description="NULL = shared meter (cả property). "
        "NOT NULL = per-room reading.",
    )
    created_by_user_id: UUID = Field(
        foreign_key="users.id",
        description="Landlord nhập reading. NOT NULL (audit lite).",
    )


class MeterReadingCreate(MeterReadingBase):
    """Input khi Landlord nhập reading.

    service_id từ context (batch form cho Property),
    room_id từ từng reading item trong batch.
    """

    service_id: UUID
    room_id: UUID | None = None


class MeterReadingRead(MeterReadingBase):
    """Output."""

    id: UUID
    service_id: UUID
    room_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class MeterReadingUpdate(SQLModel):
    """PATCH — chỉ cho sửa reading_value, reading_date, note.

    service_id, room_id IMMUTABLE sau khi tạo (nếu sai → delete + tạo mới).
    Service layer validate mutability dựa trên Invoice reference (Phase 2):
    - No Invoice ref → allow
    - Unpaid Invoice no Payment → warn
    - Paid/partial Invoice → block
    """

    reading_value: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        ge=0,
    )
    reading_date: date | None = None
    note: str | None = None
