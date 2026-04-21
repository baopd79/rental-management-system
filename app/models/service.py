"""
Service model — Nhóm 5: Service (Dịch vụ).

Decisions applied:
- 3 billing types: per_meter, per_person, fixed
- Scope: all_rooms (default) / selected_rooms → junction table service_rooms
- meter_scope: shared/per_room, chỉ NOT NULL khi billing_type=per_meter
- unit: chỉ NOT NULL khi billing_type=per_meter (kWh, m³, khác)
- ADR-0001 feature toggle: is_active (bật/tắt, không soft delete)
- Giá snapshot vào invoice_line_items khi tạo Invoice (immutability)

Complex CHECK constraint:
Enforce consistency giữa billing_type, unit, meter_scope:
- billing_type = per_meter → unit NOT NULL, meter_scope NOT NULL
- billing_type != per_meter → unit NULL, meter_scope NULL
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, Column
from sqlmodel import Field, SQLModel

from app.core.enums import BillingType, MeterScope, ServiceScope
from app.db.base import TimestampMixin, UUIDPrimaryKeyMixin, create_pg_enum


class ServiceBase(SQLModel):
    """Shared domain fields cho Service."""

    name: str = Field(
        max_length=100,
        description='Ví dụ: "Điện", "Nước", "Internet", "Rác"',
    )
    billing_type: BillingType = Field(
        sa_type=create_pg_enum(BillingType),
        description="per_meter/per_person/fixed",
    )
    price: Decimal = Field(
        max_digits=12,
        decimal_places=2,
        ge=0,
        description="Đơn giá (VND per unit/person/fixed)",
    )
    unit: str | None = Field(
        default=None,
        max_length=20,
        description="Đơn vị đo: 'kWh', 'm³', 'khác'. NOT NULL iff billing_type=per_meter",
    )
    scope: ServiceScope = Field(
        sa_column=Column(
            create_pg_enum(ServiceScope),
            nullable=False,
            server_default=ServiceScope.ALL_ROOMS.value,
        ),
        default=ServiceScope.ALL_ROOMS,
        description="all_rooms (default) / selected_rooms (dùng junction table)",
    )
    meter_scope: MeterScope | None = Field(
        sa_type=create_pg_enum(MeterScope),
        default=None,
        description="shared (1 công tơ cho nhóm) / per_room (mỗi phòng 1 công tơ). "
        "NOT NULL iff billing_type=per_meter",
    )


class Service(ServiceBase, UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """`services` table.

    CHECK constraint phức tạp enforce consistency giữa 3 fields liên quan.
    Alembic autogenerate KHÔNG detect được CHECK này — phải verify ở migration.
    """

    __tablename__ = "services"

    __table_args__ = (
        CheckConstraint(
            "price >= 0",
            name="ck_services_price_non_negative",
        ),
        # Enforce: per_meter → có unit + meter_scope; ngược lại → cả 2 NULL
        CheckConstraint(
            """
            (billing_type = 'per_meter' AND unit IS NOT NULL AND meter_scope IS NOT NULL)
            OR
            (billing_type != 'per_meter' AND unit IS NULL AND meter_scope IS NULL)
            """,
            name="ck_services_per_meter_fields_consistency",
        ),
    )

    property_id: UUID = Field(
        foreign_key="properties.id",
        description="Service thuộc 1 Property (scope Landlord)",
    )

    # Feature toggle (ADR-0001) — không soft delete
    is_active: bool = Field(
        default=True,
        description="Landlord có thể tắt tạm thời. Default TRUE khi tạo. "
        "Invoice chỉ tính services is_active=True.",
    )


class ServiceCreate(ServiceBase):
    """Input khi Landlord tạo Service.

    property_id lấy từ URL path (/properties/{id}/services),
    không ở request body.

    Landlord phải đảm bảo consistency billing_type ↔ unit ↔ meter_scope
    ở UI (Phase 4 validate ở service layer).
    """

    pass


class ServiceRead(ServiceBase):
    """Output cho Landlord (Tenant không thấy Service detail)."""

    id: UUID
    property_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ServiceUpdate(SQLModel):
    """PATCH — cho sửa name, price, is_active.

    KHÔNG cho sửa billing_type, unit, meter_scope (Phase 2 Nhóm 5:
    "Không đổi giá giữa kỳ" - thực ra là không đổi core attributes;
    price đổi được nhưng chỉ apply cho Invoice tạo sau).
    """

    name: str | None = None
    price: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        ge=0,
    )
    is_active: bool | None = None
