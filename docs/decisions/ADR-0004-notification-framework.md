# ADR-0004: Notification Framework

> **Status**: Accepted (MVP scope) — channels mở rộng ở v1.x
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

RMS cần notify Landlord và Tenant về các sự kiện quan trọng:
- Lease sắp hết hạn
- Invoice vừa được tạo
- Invoice quá hạn thanh toán
- Invoice reminder (đầu tháng chưa xuất)

Phase 2 xác định: MVP delivery là **in-app badge**, Landlord nhắc
Tenant thủ công qua Zalo. Email, push notification, Zalo OA là v1.x.

Cần design notification framework ngay từ MVP để v1.x thêm channel
mới không phải sửa business logic.

---

## Decision

Dùng **Event-driven notification** với interface đơn giản. MVP chỉ
implement **in-app (DB-backed)**, nhưng architecture cho phép thêm
channel mà không sửa emitter.

---

## Event catalog

| Event key | Trigger | Recipient |
|-----------|---------|-----------|
| `lease.expiring_soon` | Lease còn ≤ 30 ngày | Landlord |
| `lease.expired` | Lease qua end_date, chưa terminate | Landlord |
| `invoice.created` | Invoice mới được tạo | Tenant + Landlord |
| `invoice.overdue` | Invoice unpaid > 7 ngày sau billing_day | Landlord |
| `invoice.reminder` | Ngày 5 mà chưa xuất Invoice tháng này | Landlord |

---

## Schema — in-app notifications

```sql
CREATE TABLE notifications (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_id UUID         NOT NULL REFERENCES users(id),
    event_key    VARCHAR(50)  NOT NULL,
    title        VARCHAR(200) NOT NULL,
    body         TEXT         NOT NULL,
    entity_type  VARCHAR(50)  DEFAULT NULL,  -- 'lease', 'invoice', ...
    entity_id    UUID         DEFAULT NULL,  -- deep link target
    is_read      BOOLEAN      NOT NULL DEFAULT FALSE,
    read_at      TIMESTAMPTZ  DEFAULT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notif_recipient ON notifications(recipient_id, is_read, created_at DESC);
```

---

## Implementation

### NotificationService interface

```python
# app/services/notification_service.py

class NotificationService:
    """
    Emitter duy nhất cho toàn bộ hệ thống.
    Business logic chỉ gọi emit() — không biết channel nào được dùng.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.handlers: list[NotificationHandler] = [
            InAppHandler(db),
            # v1.x: EmailHandler(smtp_client),
            # v1.x: ZaloOAHandler(zalo_client),
        ]

    async def emit(self, event_key: str, context: dict) -> None:
        event = self._build_event(event_key, context)
        for handler in self.handlers:
            if handler.can_handle(event):
                await handler.send(event)

    def _build_event(self, event_key: str, context: dict) -> NotificationEvent:
        templates = EVENT_TEMPLATES[event_key]
        return NotificationEvent(
            event_key   = event_key,
            recipients  = templates["recipients"](context),
            title       = templates["title"].format(**context),
            body        = templates["body"].format(**context),
            entity_type = context.get("entity_type"),
            entity_id   = context.get("entity_id"),
        )
```

### Event templates

```python
# app/core/notification_templates.py

EVENT_TEMPLATES = {
    "lease.expiring_soon": {
        "recipients": lambda ctx: [ctx["landlord_id"]],
        "title": "Hợp đồng sắp hết hạn",
        "body":  "Phòng {room_name} — hợp đồng hết hạn ngày {end_date}.",
    },
    "lease.expired": {
        "recipients": lambda ctx: [ctx["landlord_id"]],
        "title": "Hợp đồng đã hết hạn",
        "body":  "Phòng {room_name} — hợp đồng hết hạn từ {end_date}. Cần xử lý.",
    },
    "invoice.created": {
        "recipients": lambda ctx: [ctx["landlord_id"], ctx["tenant_user_id"]],
        "title": "Hoá đơn tháng {month} đã tạo",
        "body":  "Phòng {room_name} — {total_amount:,.0f}đ. Hạn thanh toán: {due_date}.",
    },
    "invoice.overdue": {
        "recipients": lambda ctx: [ctx["landlord_id"]],
        "title": "Hoá đơn quá hạn",
        "body":  "Phòng {room_name} — hoá đơn tháng {month} chưa thanh toán.",
    },
    "invoice.reminder": {
        "recipients": lambda ctx: [ctx["landlord_id"]],
        "title": "Nhắc xuất hoá đơn tháng {month}",
        "body":  "Nhà {property_name} chưa có hoá đơn tháng {month}.",
    },
}
```

### InAppHandler

```python
class InAppHandler:
    def can_handle(self, event: NotificationEvent) -> bool:
        return True  # In-app luôn active

    async def send(self, event: NotificationEvent) -> None:
        for recipient_id in event.recipients:
            if recipient_id is None:
                continue  # Tenant chưa có account → skip
            notif = Notification(
                recipient_id = recipient_id,
                event_key    = event.event_key,
                title        = event.title,
                body         = event.body,
                entity_type  = event.entity_type,
                entity_id    = event.entity_id,
            )
            self.db.add(notif)
```

---

## API endpoints

```
GET  /notifications              → list unread (pagination)
GET  /notifications/count        → unread count (cho badge)
POST /notifications/{id}/read    → đánh dấu đã đọc
POST /notifications/read-all     → đánh dấu tất cả đã đọc
```

---

## Retention

Notification giữ **90 ngày** rồi xóa. Không phải dữ liệu kế toán,
không cần giữ lâu. Cleanup job chạy weekly (thêm vào ADR-0002).

---

## v1.x extension plan

Khi thêm Email channel:
1. Implement `EmailHandler(smtp_client)`
2. Thêm vào `self.handlers` list trong `NotificationService.__init__`
3. Không sửa business logic, không sửa emitter calls

Business logic chỉ biết `notification_service.emit(event_key, context)`.
Channel là implementation detail của NotificationService.

---

## Consequences

### Positive
- Business logic không biết channel → thêm Email/Zalo OA không
  cần sửa service layer
- Template tập trung → dễ maintain content
- In-app backed bởi DB → reliable, có thể query history

### Negative / Trade-offs
- Template dùng `.format()` → lỗi typo key là runtime error, không
  phải compile-time. Cần test coverage cho từng template.
- Notification gửi trong main request/cron → nếu handler chậm
  sẽ ảnh hưởng response time. MVP acceptable; v1.x có thể move
  sang async queue.

### Neutral
- MVP: Tenant không có account vẫn tạo Invoice → `tenant_user_id`
  có thể NULL → InAppHandler skip, Landlord nhắc thủ công Zalo.
  Đây là expected behavior.

---

## References

- Phase 2 Summary — ADR-0004 (notification channels)
- Phase 2 Summary — Invoice delivery (in-app + Zalo thủ công)
- ADR-0002: Cron Job Architecture (emit từ scheduled tasks)
