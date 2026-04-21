"""
Lease model — Nhóm 4: Lease (Hợp đồng thuê).

Decisions applied:
- Strict single-active: partial unique index (room_id WHERE terminated_at IS NULL)
  → define ở Alembic migration, không ở table class
- ADR-0001 event timestamp: terminated_at (không dùng is_terminated boolean)
- Deposit: 4 status enum, snapshot fields immutable sau khi tạo
- Pro-rata universal: qua start_date/end_date/terminated date (không có billing_mode)
- Snapshot: rent_amount, deposit_amount, billing_day đều snapshot khi ký
- Computed status (active/draft/expiring_soon/expired/terminated) — không lưu DB

Immutability pattern:
- LeaseCreate: input khi ký Lease mới (full fields)
- LeaseUpdate: CHỈ cho sửa `note` và `end_date` (Phase 2 Nhóm 4)
  Các field khác phải void+recreate
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlmodel import Field, SQLModel

from app.core.enums import DepositStatus
from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, create_pg_enum


class LeaseBase(SQLModel):
    """Shared domain fields cho Lease."""

    start_date: date = Field(
        description="Ngày bắt đầu thuê",
    )
    end_date: date = Field(
        description="Ngày kết thúc hợp đồng. CHECK end_date >= start_date",
    )
    rent_amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Tiền thuê/tháng. Snapshot, immutable sau khi Lease tạo.",
    )
    deposit_amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Tiền cọc. Có thể = 0 (rollover). Snapshot, immutable.",
    )
    billing_day: int = Field(
        ge=1,
        le=28,
        description="Ngày billing, snapshot từ property.billing_day khi ký Lease",
    )
    note: str | None = Field(
        default=None,
        description="Ghi chú hợp đồng, mutable (có thể update sau khi ký)",
    )


class Lease(LeaseBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`leases` table.

    Unique constraint đặc biệt (define ở migration, không ở đây):
    - Strict single-active: partial unique index room_id WHERE terminated_at IS NULL
      → 1 Room max 1 Lease non-terminated tại 1 thời điểm.

    Computed status (không lưu, compute at query):
    - draft: start_date > today
    - active: start_date <= today <= end_date - 30 days
    - expiring_soon: today > end_date - 30 days AND today <= end_date
    - expired: today > end_date (và chưa terminated)
    - terminated: terminated_at IS NOT NULL
    """

    __tablename__ = "leases"

    __table_args__ = (
        CheckConstraint(
            "end_date >= start_date",
            name="end_after_start",
        ),
        CheckConstraint(
            "rent_amount >= 0",
            name="rent_non_negative",
        ),
        CheckConstraint(
            "deposit_amount >= 0",
            name="deposit_non_negative",
        ),
        CheckConstraint(
            "billing_day BETWEEN 1 AND 28",
            name="billing_day_range",
        ),
    )

    room_id: UUID = Field(
        foreign_key="rooms.id",
        description="Room được thuê. NOT NULL.",
    )
    tenant_id: UUID = Field(
        foreign_key="tenants.id",
        description="Tenant đại diện (1 Lease → 1 Tenant).",
    )

    # Event timestamp (ADR-0001)
    terminated_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp khi Lease bị terminate. NULL = chưa terminate.",
    )
    terminated_reason: str | None = Field(
        default=None,
        description="Lý do terminate (free text)",
    )

    # Deposit tracking (state + metadata)
    deposit_status: DepositStatus = Field(
        sa_column=Column(
            create_pg_enum(DepositStatus),
            nullable=False,
            server_default=DepositStatus.HELD.value,
        ),
        default=DepositStatus.HELD,
        description="Trạng thái cọc: held/returned/forfeited/deducted",
    )
    deposit_settled_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Timestamp khi settle deposit (khác terminated_at)",
    )
    deposit_settlement_note: str | None = Field(
        default=None,
        description="Ghi chú settle cọc, ví dụ 'trừ 200k sửa tường'",
    )


class LeaseCreate(LeaseBase):
    """Input khi Landlord ký Lease mới.

    Bao gồm room_id + tenant_id (chọn Room và Tenant tại thời điểm tạo).
    Các field deposit/terminate set default ở service layer (deposit_status=held).
    """

    room_id: UUID
    tenant_id: UUID


class LeaseRead(LeaseBase):
    """Output — expose domain fields + lifecycle dates.

    Client cần biết:
    - terminated_at: để hiển thị "đã kết thúc ngày X"
    - deposit_status: để biết trạng thái cọc
    - deposit_settled_at, deposit_settlement_note: transparency cho Tenant

    Computed `status` field thêm ở service layer, không ở schema.
    """

    id: UUID
    room_id: UUID
    tenant_id: UUID
    terminated_at: datetime | None
    terminated_reason: str | None
    deposit_status: DepositStatus
    deposit_settled_at: datetime | None
    deposit_settlement_note: str | None
    created_at: datetime
    updated_at: datetime


class LeaseUpdate(SQLModel):
    """PATCH input — chỉ cho sửa `note` và `end_date` (Phase 2 Nhóm 4).

    Các field khác (rent_amount, deposit_amount, dates) IMMUTABLE sau khi ký.
    Muốn sửa → terminate Lease cũ + tạo Lease mới.
    """

    note: str | None = None
    end_date: date | None = None


class LeaseTerminate(SQLModel):
    """Input riêng cho endpoint terminate Lease (US-055).

    Không phải PATCH chung — terminate là action riêng, cần fields khác.
    """

    terminated_date: date = Field(
        description="Ngày hiệu lực terminate (có thể < today nếu back-date)",
    )
    terminated_reason: str | None = None


class LeaseSettleDeposit(SQLModel):
    """Input riêng cho endpoint settle deposit (US-056).

    Tách khỏi terminate vì 2 action khác timeline (terminate trước, settle sau).
    """

    deposit_status: DepositStatus = Field(
        description="Trạng thái cuối: returned/forfeited/deducted",
    )
    deposit_settlement_note: str | None = None
