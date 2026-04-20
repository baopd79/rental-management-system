"""
Notification model — Nhóm 9: Cross-cutting (ADR-0004).

Decisions applied:
- MVP: in-app channel only (DB-backed). Email/Zalo OA defer v1.x.
- Retention 90 ngày (cleanup job weekly)
- Event-driven: emit từ Service layer / Cron (ADR-0002)
- Deep link via entity_type + entity_id (optional, nullable)

Không có Create schema — chỉ service layer emit qua NotificationService helper.
Read schema cho client GET /notifications (unread list, badge count).
Update chỉ cho mark-as-read (endpoint riêng).
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.base import CreatedAtOnlyMixin, UUIDPrimaryKeyMixin


class Notification(UUIDPrimaryKeyMixin, CreatedAtOnlyMixin, SQLModel, table=True):
    """`notifications` table.

    Query pattern phổ biến nhất: unread của user (badge + list).
    Cần index (recipient_id, is_read, created_at DESC) — define ở migration.
    """

    __tablename__ = "notifications"

    recipient_id: UUID = Field(
        foreign_key="users.id",
        description="User nhận notification. ON DELETE CASCADE "
                    "(xóa user → xóa notifications).",
    )
    event_key: str = Field(
        max_length=50,
        description="'lease.expiring_soon', 'invoice.created', 'invoice.overdue', ...",
    )
    title: str = Field(
        max_length=200,
        description="Tiêu đề hiển thị (format sẵn từ template)",
    )
    body: str = Field(
        description="Nội dung chi tiết (format sẵn từ template với context)",
    )

    # Deep link target (optional)
    entity_type: str | None = Field(
        default=None,
        max_length=50,
        description="Loại entity để link sang trang chi tiết ('invoice', 'lease', ...)",
    )
    entity_id: UUID | None = Field(
        default=None,
        description="ID entity để link. NULL nếu notification không có deep link",
    )

    # Read state
    is_read: bool = Field(
        default=False,
        description="False = unread (hiện trên badge). True = đã đọc.",
    )
    read_at: datetime | None = Field(
        default=None,
        description="Timestamp khi user mark-as-read. NULL iff is_read=False.",
    )


class NotificationRead(SQLModel):
    """Output cho client."""

    id: UUID
    event_key: str
    title: str
    body: str
    entity_type: str | None
    entity_id: UUID | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationMarkRead(SQLModel):
    """Input cho endpoint POST /notifications/{id}/read.

    Empty body — chỉ cần trigger. Server set is_read=True, read_at=now.
    Nhưng vẫn define schema để FastAPI generate OpenAPI doc rõ ràng.
    """
    pass


# Không có NotificationCreate — chỉ service layer emit qua NotificationService.
