"""
Base classes và mixins cho SQLModel.

Design patterns:
- `UUIDPrimaryKeyMixin`: UUID PK với server-side gen (gen_random_uuid)
- `TimestampMixin`: created_at + updated_at auto-manage
- Base models thuần (không có id, timestamps) dùng cho Create/Read schemas

Lưu ý về `updated_at`:
Auto-update qua SQLAlchemy event listener ở Phase 4 (chưa implement ở đây).
Alternative: PostgreSQL trigger — defer decision to Phase 4.
"""
import re
import sqlalchemy as sa
from enum import Enum
from typing import Type
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, text
from sqlmodel import Field, SQLModel


# ============================================================
# Naming convention for database constraints
# ============================================================
# Ensures predictable, reproducible constraint names across
# environments. Must be set BEFORE any table class is defined.
#
# Patterns:
#   ix = index
#   uq = unique constraint
#   ck = check constraint
#   fk = foreign key
#   pk = primary key
# ============================================================

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

SQLModel.metadata.naming_convention = NAMING_CONVENTION

def _camel_to_snake(name: str) -> str:
    """UserRole -> user_role, BillingType -> billing_type."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def create_pg_enum(enum_cls: Type[Enum]) -> sa.Enum:
    """Factory tạo sa.Enum cho Postgres với:
    - values_callable: dùng .value lowercase thay vì .name UPPERCASE
    - name: <snake_case>_enum, match convention ERD section 9

    Ví dụ: create_pg_enum(UserRole) -> sa.Enum(..., name='user_role_enum')
    """
    return sa.Enum(
        enum_cls,
        values_callable=lambda e: [m.value for m in e],
        name=f"{_camel_to_snake(enum_cls.__name__)}_enum",
    )

def _utc_now() -> datetime:
    """Current UTC time with tz-aware datetime."""
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin(SQLModel):
    """Mixin cho table có UUID primary key.

    Dùng PostgreSQL `gen_random_uuid()` ở server-side — consistent giữa
    app và migration, tránh Python UUID mismatch nếu có INSERT từ SQL raw.
    """

    id: UUID | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )


class TimestampMixin(SQLModel):
    """Mixin cho created_at + updated_at.
    ...
    """

    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("NOW()"),
        },
    )

    updated_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("NOW()"),
        },
    )


class CreatedAtOnlyMixin(SQLModel):
    """Mixin chỉ có created_at (cho append-only tables).

    Áp dụng: audit_logs, notifications, tokens, invoices, payments —
    những entity mà UPDATE không có ý nghĩa hoặc không được phép.
    """

    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={
            "nullable": False,
            "server_default": text("NOW()"),
        },
    )
