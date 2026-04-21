"""
Invoice + InvoiceLineItem models — Nhóm 7: Invoice (phức tạp nhất).

Decisions applied:
- Invoice IMMUTABILITY TUYỆT ĐỐI: chỉ voided_at + Payment relationship đổi được
  → dùng CreatedAtOnlyMixin (không có updated_at)
- No draft in DB: Invoice record chỉ tạo sau commit
- Status (unpaid/partial/paid/void): COMPUTED from payments + voided_at, không lưu
- Void: event timestamp (voided_at), enum reason, required void_note if reason='other'
- Billing period per line item: mỗi line có billing_period_start/end riêng
- Line types: rent / service / adjustment
- adjustment cho phép amount âm (giảm tiền)
- meter_reading_start_id + meter_reading_end_id: snapshot IDs cho per_meter lines
- Denormalized landlord_id: đơn giản unique invoice_number per landlord + ownership query

Complex constraints (enforce ở DB + service layer):
- Unique invoice_number per landlord (partial unique WHERE voided_at IS NULL)
- Không duplicate Invoice cùng (lease_id, billing_month) non-void (partial unique)
- billing_month <= current month (không tạo Invoice tương lai)
- line amount >= 0 trừ line_type=adjustment
- service_id required iff line_type=service
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlmodel import Field, SQLModel

from app.core.enums import LineType, VoidedReason
from app.db.base import CreatedAtOnlyMixin, UUIDPrimaryKeyMixin, create_pg_enum


# ============================================================
# Invoice
# ============================================================


class InvoiceBase(SQLModel):
    """Shared domain fields cho Invoice."""

    billing_month: date = Field(
        description="Ngày 1 của tháng billing (VD: 2026-05-01). "
        "CHECK <= current month (không tạo Invoice tương lai).",
    )
    due_date: date = Field(
        description="Hạn thanh toán",
    )
    total_amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Tổng = SUM(line_items.amount). Snapshot tại thời điểm tạo.",
    )
    note: str | None = Field(
        default=None,
        description="Ghi chú thêm từ Landlord",
    )


class Invoice(InvoiceBase, UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True):
    """`invoices` table.

    IMMUTABLE fields (set khi tạo, không đổi):
    - lease_id, landlord_id, invoice_number, billing_month, total_amount, due_date

    MUTABLE fields:
    - voided_at + voided_reason + void_note + voided_by_user_id (khi void)
    - Payments (thêm Payment → Invoice.status recompute)

    Không có updated_at → dùng CreatedAtOnlyMixin.
    """

    __tablename__ = "invoices"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="total_non_negative",
        ),
        # Void consistency: tất cả void fields NULL hoặc tất cả NOT NULL
        CheckConstraint(
            """
            (voided_at IS NULL AND voided_reason IS NULL AND voided_by_user_id IS NULL)
            OR
            (voided_at IS NOT NULL AND voided_reason IS NOT NULL AND voided_by_user_id IS NOT NULL)
            """,
            name="void_fields_consistency",
        ),
        CheckConstraint(
            "billing_month <= DATE_TRUNC('month', CURRENT_DATE)",
            name="billing_month_not_future",
        ),
    )

    lease_id: UUID = Field(
        foreign_key="leases.id",
        description="Invoice gắn với 1 Lease",
    )
    landlord_id: UUID = Field(
        foreign_key="users.id",
        description="Denormalized từ lease → room → property → landlord. "
        "Simplify unique invoice_number + ownership query (ADR-0005).",
    )
    created_by_user_id: UUID = Field(
        foreign_key="users.id",
        description="User tạo Invoice (thường = landlord, có thể = manager ở v1.x)",
    )

    invoice_number: str = Field(
        max_length=30,
        description="Format 'INV-YYYY-MM-NNN', unique per landlord (partial index "
        "WHERE voided_at IS NULL → voided có thể reuse number)",
    )

    # Void fields (event timestamp pattern)
    voided_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
        description="Event timestamp. NULL = active, NOT NULL = voided",
    )
    voided_reason: VoidedReason | None = Field(
        sa_type=create_pg_enum(VoidedReason),
        default=None,
        description="Enum 6 giá trị (US-084 AC2). Required when voided_at NOT NULL.",
    )
    void_note: str | None = Field(
        default=None,
        description="Required when voided_reason='other' (enforce ở service layer)",
    )
    voided_by_user_id: UUID | None = Field(
        default=None,
        foreign_key="users.id",
        description="Ai void. Required when voided_at NOT NULL (audit).",
    )


class InvoiceCreate(InvoiceBase):
    """Input khi Landlord tạo Invoice.

    lease_id từ context (batch per property hoặc individual).
    invoice_number generate ở service layer (pattern INV-YYYY-MM-NNN).
    landlord_id derive từ lease → room → property.
    created_by_user_id từ JWT (current user).
    """

    lease_id: UUID


class InvoiceRead(InvoiceBase):
    """Output — expose domain + lifecycle fields.

    Computed `status` field (unpaid/partial/paid/void) thêm ở service layer.
    Client thấy status dễ hiểu thay vì phải compute từ payments + voided_at.
    """

    id: UUID
    lease_id: UUID
    invoice_number: str
    voided_at: datetime | None
    voided_reason: VoidedReason | None
    void_note: str | None
    created_at: datetime


class InvoiceVoid(SQLModel):
    """Input cho void endpoint (US-084).

    Tách khỏi Update vì void là action đặc biệt với required fields.
    """

    voided_reason: VoidedReason
    void_note: str | None = Field(
        default=None,
        description="Required if voided_reason='other' (validate service layer)",
    )


# ============================================================
# InvoiceLineItem
# ============================================================


class InvoiceLineItemBase(SQLModel):
    """Shared fields cho line item."""

    line_type: LineType = Field(
        sa_type=create_pg_enum(LineType),
        description="rent / service / adjustment",
    )
    description: str = Field(
        max_length=500,
        description='Human-readable. VD: "Điện T04/2026: 1234 → 1456 = 222 kWh × 3,500đ"',
    )
    unit: str | None = Field(
        default=None,
        max_length=20,
        description="kWh / m³ / người / tháng... (per-line unit)",
    )
    billing_period_start: date = Field(
        description="Start của period line này cover (có thể khác Invoice.billing_month)",
    )
    billing_period_end: date = Field(
        description="End period. CHECK >= start.",
    )
    quantity: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="Số lượng (kWh, m³, người, ngày). NULL cho line_type=adjustment.",
    )
    unit_price: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        description="Đơn giá snapshot. NULL cho line_type=adjustment.",
    )
    amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        description="Tổng line. Có thể âm CHỈ khi line_type=adjustment. "
        "Cho rent/service: amount = quantity × unit_price",
    )
    sort_order: int = Field(
        default=0,
        description="Thứ tự hiển thị trong Invoice",
    )


class InvoiceLineItem(
    InvoiceLineItemBase, UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True
):
    """`invoice_line_items` table.

    Line item IMMUTABLE cùng với Invoice (không có updated_at).
    """

    __tablename__ = "invoice_line_items"

    __table_args__ = (
        CheckConstraint(
            "billing_period_end >= billing_period_start",
            name="period_end_after_start",
        ),
        # amount âm chỉ cho adjustment
        CheckConstraint(
            "line_type = 'adjustment' OR amount >= 0",
            name="amount_non_negative_non_adjustment",
        ),
        # service_id required iff line_type='service'
        CheckConstraint(
            """
            (line_type = 'service' AND service_id IS NOT NULL)
            OR
            (line_type IN ('rent', 'adjustment') AND service_id IS NULL)
            """,
            name="service_id_consistency",
        ),
    )

    invoice_id: UUID = Field(
        foreign_key="invoices.id",
        description="Invoice cha",
    )

    # Reference fields (nullable tùy line_type)
    service_id: UUID | None = Field(
        default=None,
        foreign_key="services.id",
        description="Required iff line_type='service'",
    )
    meter_reading_start_id: UUID | None = Field(
        default=None,
        foreign_key="meter_readings.id",
        description="Reading đầu kỳ cho per_meter lines. NULL cho non-per_meter.",
    )
    meter_reading_end_id: UUID | None = Field(
        default=None,
        foreign_key="meter_readings.id",
        description="Reading cuối kỳ. NULL cho non-per_meter.",
    )


class InvoiceLineItemCreate(InvoiceLineItemBase):
    """Input khi tạo line (thường trong batch cùng Invoice).

    invoice_id inject bởi service layer (sau khi tạo Invoice parent).
    """

    service_id: UUID | None = None
    meter_reading_start_id: UUID | None = None
    meter_reading_end_id: UUID | None = None


class InvoiceLineItemRead(InvoiceLineItemBase):
    """Output."""

    id: UUID
    invoice_id: UUID
    service_id: UUID | None
    meter_reading_start_id: UUID | None
    meter_reading_end_id: UUID | None
    created_at: datetime


# Không có Update schema — line items immutable cùng Invoice.
# Sửa Invoice = void + recreate.


class InvoiceAdjustmentAdd(SQLModel):
    """Input cho endpoint "Thêm adjustment vào Invoice" (US-085).

    Chỉ cho Invoice status=unpaid. Validate ở service layer.
    """

    description: str = Field(max_length=500)
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    billing_period_start: date
    billing_period_end: date
