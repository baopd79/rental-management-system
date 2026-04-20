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

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field, SQLModel


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

    Semantics:
    - `created_at`: set 1 lần khi INSERT, không đổi
    - `updated_at`: auto-update mỗi khi UPDATE (Phase 4 implement trigger/listener)

    Cả 2 đều NOT NULL với server default NOW() → không phụ thuộc app timezone.
    """

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )

    updated_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )


class CreatedAtOnlyMixin(SQLModel):
    """Mixin chỉ có created_at (cho append-only tables).

    Áp dụng: audit_logs, notifications, tokens, invoices, payments —
    những entity mà UPDATE không có ý nghĩa hoặc không được phép.
    """

    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(
            DateTime(timezone=True),
            nullable=False,
            server_default=text("NOW()"),
        ),
    )
