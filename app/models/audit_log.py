"""
AuditLog model — Nhóm 9: Cross-cutting (ADR-0003).

Decisions applied:
- Application-level audit table (không DB trigger, không event sourcing)
- Scope: critical entities only (lease, invoice, payment, room, tenant, service, user)
- Partial JSONB snapshot (before/after) — chỉ fields đổi, không full entity
- Ghi trong cùng transaction với main operation (không fire-and-forget)
- Retention 10 năm (giống Invoice/Payment)
- Generic entity_type + entity_id (không FK — audit cover nhiều bảng)
- Denormalized landlord_id — query "audit của tôi" không cần JOIN

Không có Update schema — audit log immutable (append-only).
Không có Read schema chi tiết vì Landlord xem qua dedicated endpoint
với filter (entity_type, entity_id, date range) — không expose full CRUD.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.db.base import CreatedAtOnlyMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, SQLModel, table=True):
    """`audit_logs` table.

    Append-only. Không có Create/Update API — ghi bởi service layer
    qua AuditLogger helper (ADR-0003).

    Query patterns:
    - "Audit của entity X": WHERE entity_type='lease' AND entity_id=<uuid>
    - "Audit bởi user Y": WHERE actor_id=<uuid>
    - "Audit trong landlord Z": WHERE landlord_id=<uuid> (denorm)
    """

    __tablename__ = "audit_logs"

    # Actor
    actor_id: UUID = Field(
        foreign_key="users.id",
        description="User thực hiện action",
    )
    actor_role: str = Field(
        max_length=20,
        description="Snapshot role tại thời điểm event (role có thể đổi sau này)",
    )

    # Denormalized scope
    landlord_id: UUID = Field(
        foreign_key="users.id",
        description="Denormalized — scope Landlord của audit entry này. "
        "Cho query 'audit trong property tôi' không JOIN",
    )

    # Target (generic, no FK)
    entity_type: str = Field(
        max_length=50,
        description="'lease', 'invoice', 'payment', 'room', 'tenant', 'service', 'user'",
    )
    entity_id: UUID = Field(
        description="ID entity bị tác động. KHÔNG FK (generic, cover nhiều bảng)",
    )

    # Action
    action: str = Field(
        max_length=50,
        description="'created', 'updated', 'archived', 'terminated', 'voided', ...",
    )

    # Payload — partial JSONB snapshots
    before: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Snapshot fields thay đổi TRƯỚC action. NULL cho action='created'.",
    )
    after: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Snapshot fields thay đổi SAU action. NULL cho action='deleted/archived'.",
    )

    note: str | None = Field(
        default=None,
        description="Context từ Landlord (lý do void, terminate...)",
    )


class AuditLogRead(SQLModel):
    """Output cho endpoint GET /audit-logs (Landlord xem)."""

    id: UUID
    actor_id: UUID
    actor_role: str
    entity_type: str
    entity_id: UUID
    action: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    note: str | None
    created_at: datetime


# Không có AuditLogCreate — chỉ service layer tạo qua AuditLogger helper.
# Không có AuditLogUpdate — immutable.
