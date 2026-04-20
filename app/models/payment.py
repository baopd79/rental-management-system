"""
Payment model — Nhóm 8: Payment (Thanh toán) — đơn giản nhất.

Decisions applied:
- Record-only: Landlord ghi nhận hậu kiểm, không có payment gateway
- Không có type enum (Invoice.status đã cover)
- Method enum: cash, bank_transfer, ewallet, other
- Hard delete allowed → recompute Invoice.status
- Unlimited Payment per Invoice
- Validate: amount > 0, paid_at <= today (enforce DB CHECK)
- Không overpay (enforce service layer, DB không check được aggregate)
- Không Payment cho Invoice voided (service layer block)

Không có is_archived hoặc updated_at — Payment append-only:
- Create → record
- Delete → hard delete (recompute Invoice status)
- Update Payment? → Không. Sai → delete + tạo lại.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.core.enums import PaymentMethod
from app.db.base import CreatedAtOnlyMixin, UUIDPrimaryKeyMixin


class PaymentBase(SQLModel):
    """Shared fields cho Payment."""

    amount: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        gt=0,
        description="Số tiền thanh toán. CHECK > 0 (strict positive, không = 0).",
    )
    paid_at: date = Field(
        description="Ngày thực tế Tenant trả (Landlord ghi nhận hậu kiểm). "
                    "CHECK <= today (không future date).",
    )
    method: PaymentMethod = Field(
        description="cash / bank_transfer / ewallet / other",
    )
    reference: str | None = Field(
        default=None,
        max_length=100,
        description="Mã giao dịch bank transfer, số biên nhận...",
    )
    note: str | None = Field(
        default=None,
        description="Ghi chú thêm từ Landlord",
    )


class Payment(PaymentBase, UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, table=True):
    """`payments` table."""

    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_payments_amount_strict_positive",
        ),
        CheckConstraint(
            "paid_at <= CURRENT_DATE",
            name="ck_payments_paid_at_not_future",
        ),
    )

    invoice_id: UUID = Field(
        foreign_key="invoices.id",
        description="Invoice được trả. ON DELETE RESTRICT "
                    "(Payment không CASCADE khi Invoice void).",
    )
    recorded_by_user_id: UUID = Field(
        foreign_key="users.id",
        description="Landlord ghi nhận Payment (audit)",
    )


class PaymentCreate(PaymentBase):
    """Input khi Landlord ghi Payment.

    invoice_id từ URL path (/invoices/{id}/payments).
    recorded_by_user_id từ JWT.

    Service layer validate:
    - Invoice not voided
    - amount <= remaining (không overpay)
    """
    pass


class PaymentRead(PaymentBase):
    """Output.

    Tenant cũng thấy Payment (transparency). Không expose internal
    fields sensitive — Payment đã đơn giản.
    """

    id: UUID
    invoice_id: UUID
    recorded_by_user_id: UUID
    created_at: datetime


# Không có PaymentUpdate — Payment không edit.
# Hard delete qua endpoint DELETE /payments/{id}, service layer recompute Invoice status.
