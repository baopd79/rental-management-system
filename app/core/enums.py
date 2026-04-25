"""
Python Enum classes used as SQLModel field types.

These map 1-1 với PostgreSQL ENUM types defined ở Alembic migration.
Khi thêm enum mới:
1. Add class ở đây
2. Thêm CREATE TYPE trong Alembic migration
3. Ở model: dùng `sa.Enum(EnumName, name="enum_name_in_db")` trong Field()
"""

from enum import StrEnum


class UserRole(StrEnum):
    """ADR-0005 — MVP: 2 roles. v1.x thêm manager, v2.x investor."""

    LANDLORD = "landlord"
    TENANT = "tenant"


class DepositStatus(StrEnum):
    """Phase 2 Nhóm 4 — 4 trạng thái deposit."""

    HELD = "held"
    RETURNED = "returned"
    FORFEITED = "forfeited"
    DEDUCTED = "deducted"


class BillingType(StrEnum):
    """Phase 2 Nhóm 5 — 3 cách tính dịch vụ."""

    PER_METER = "per_meter"
    PER_PERSON = "per_person"
    FIXED = "fixed"


class ServiceScope(StrEnum):
    """Phase 2 Nhóm 5 — service áp dụng cho toàn bộ hay chọn lọc."""

    ALL_ROOMS = "all_rooms"
    SELECTED_ROOMS = "selected_rooms"


class MeterScope(StrEnum):
    """Phase 2 Nhóm 6 — công tơ chung hay riêng từng phòng."""

    SHARED = "shared"
    PER_ROOM = "per_room"


class LineType(StrEnum):
    """Phase 2 Nhóm 7 — 3 loại line trong Invoice."""

    RENT = "rent"
    SERVICE = "service"
    ADJUSTMENT = "adjustment"


class PaymentMethod(StrEnum):
    """Phase 2 Nhóm 8 — 4 phương thức thanh toán."""

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    EWALLET = "ewallet"
    OTHER = "other"


class VoidedReason(StrEnum):
    """Phase 2 US-084 AC2 — lý do void Invoice (enum, không free text)."""

    WRONG_METER_READING = "wrong_meter_reading"
    WRONG_RENT = "wrong_rent"
    WRONG_SERVICE_CONFIG = "wrong_service_config"
    TENANT_DISPUTE = "tenant_dispute"
    DUPLICATE = "duplicate"
    OTHER = "other"
