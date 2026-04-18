# ADR-0003: Audit Log Architecture

> **Status**: Accepted
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

Audit log được đề cập ở 3 user stories trong Phase 2:
- **US-004**: Landlord xem lịch sử thay đổi của Property/Room
- **US-052**: Landlord xem lịch sử thay đổi Lease
- **US-063**: Landlord xem lịch sử void/recreate Invoice

Cần quyết định: lưu gì, lưu ở đâu, ai đọc được, giữ bao lâu.

### 3 Options phổ biến

**Option 1 — Application-level audit table (same DB)**
Mỗi write operation → insert 1 row vào bảng `audit_logs`.

**Option 2 — Event sourcing (append-only event log)**
Mọi thay đổi đều là event. State = replay toàn bộ events.

**Option 3 — PostgreSQL trigger-based (pgaudit / custom trigger)**
DB trigger tự động ghi log mọi INSERT/UPDATE/DELETE.

---

## Decision

Chọn **Option 1 — Application-level audit table**, scope giới hạn ở
**critical entities**.

---

## Lý do loại Option 2 và Option 3

**Option 2 (Event sourcing)**: Quá phức tạp cho MVP. Event sourcing
phù hợp khi toàn bộ hệ thống được thiết kế từ đầu theo pattern đó.
Retrofit vào RMS hiện tại = rewrite. YAGNI.

**Option 3 (DB trigger)**: Trigger log mọi thứ kể cả những thứ không
cần thiết (e.g., cập nhật `updated_at`). Output là raw SQL diff, không
có business context ("ai làm gì tại sao"). Khó filter, khó đọc cho
Landlord non-technical.

---

## Schema

```sql
CREATE TABLE audit_logs (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Actor
    actor_id     UUID         NOT NULL REFERENCES users(id),
    actor_role   VARCHAR(20)  NOT NULL,
    -- Target
    entity_type  VARCHAR(50)  NOT NULL,   -- 'lease', 'invoice', 'room', ...
    entity_id    UUID         NOT NULL,
    -- Action
    action       VARCHAR(50)  NOT NULL,   -- 'created', 'updated', 'archived',
                                          -- 'terminated', 'voided', ...
    -- Payload
    before       JSONB        DEFAULT NULL,  -- snapshot trước khi thay đổi
    after        JSONB        DEFAULT NULL,  -- snapshot sau khi thay đổi
    note         TEXT         DEFAULT NULL,  -- context thêm nếu cần
    -- Meta
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_actor  ON audit_logs(actor_id);
CREATE INDEX idx_audit_time   ON audit_logs(created_at DESC);
```

---

## Scope: critical entities only

Không log mọi thứ — chỉ log những gì Landlord cần tra cứu:

| Entity | Actions được log |
|--------|-----------------|
| `lease` | created, updated, terminated, deposit_settled |
| `invoice` | created, voided |
| `payment` | created, deleted |
| `room` | archived, unarchived |
| `tenant` | archived, reactivated |
| `service` | created, updated, toggled |
| `user` | invited, password_reset, role_changed |

**Không log**: meter_reading (append-only, bản thân là audit trail),
property CRUD (ít thay đổi, không critical), occupant (low risk).

---

## Payload convention

`before` và `after` chứa **partial snapshot** — chỉ các field thay đổi,
không phải toàn bộ entity. Ngoại lệ: `created` action thì `before = null`,
`after` = full snapshot. `deleted`/`archived` thì `after = null`.

```python
# Ví dụ: Landlord terminate Lease
{
    "entity_type": "lease",
    "entity_id":   "uuid-...",
    "action":      "terminated",
    "before": {
        "terminated_at": null,
        "deposit_status": "held"
    },
    "after": {
        "terminated_at": "2026-05-15T10:30:00Z",
        "deposit_status": "held"
    },
    "note": "Tenant dọn đi sớm"
}

# Ví dụ: void Invoice
{
    "entity_type": "invoice",
    "entity_id":   "uuid-...",
    "action":      "voided",
    "before": { "voided_at": null, "status": "unpaid" },
    "after":  { "voided_at": "2026-05-15T11:00:00Z", "status": "void" },
    "note":   "Nhập sai chỉ số điện"
}
```

---

## Implementation pattern

Audit log được ghi ở **service layer**, không phải repository hay
middleware — vì chỉ service layer có đủ business context.

```python
# app/core/audit.py

class AuditLogger:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        actor: User,
        entity_type: str,
        entity_id: UUID,
        action: str,
        before: dict | None = None,
        after:  dict | None = None,
        note:   str  | None = None,
    ) -> None:
        entry = AuditLog(
            actor_id    = actor.id,
            actor_role  = actor.role,
            entity_type = entity_type,
            entity_id   = entity_id,
            action      = action,
            before      = before,
            after       = after,
            note        = note,
        )
        self.db.add(entry)
        # Không commit ở đây — commit cùng với main transaction
```

**Quan trọng**: Audit log phải nằm trong **cùng transaction** với
main operation. Nếu main operation rollback → audit log cũng rollback.
Không dùng fire-and-forget async task cho audit.

```python
# app/services/lease_service.py

async def terminate_lease(
    lease_id: UUID,
    terminated_at: date,
    note: str,
    current_user: User,
    db: AsyncSession,
) -> Lease:
    lease = await lease_repo.get(lease_id, db)

    before = {"terminated_at": None, "deposit_status": lease.deposit_status}

    # Main operation
    lease.terminated_at = terminated_at
    await db.flush()  # Flush nhưng chưa commit

    after = {"terminated_at": terminated_at.isoformat(), "deposit_status": lease.deposit_status}

    # Audit log cùng transaction
    await audit_logger.log(
        actor       = current_user,
        entity_type = "lease",
        entity_id   = lease.id,
        action      = "terminated",
        before      = before,
        after       = after,
        note        = note,
    )

    await db.commit()  # Commit cả hai cùng lúc
    return lease
```

---

## Visibility

| Actor | Thấy gì |
|-------|---------|
| Landlord | Audit log của mọi entity thuộc Property mình |
| Tenant | Không thấy audit log (chỉ thấy Invoice + Payment history) |
| Manager *(v1.x)* | Audit log của Property được assign |

API endpoint: `GET /properties/{id}/audit-logs?entity_type=lease&entity_id=xxx`

---

## Retention

Audit log giữ **10 năm** — cùng policy với Invoice/Payment theo luật
kế toán VN (xem ADR-0006).

Không implement purge logic trong MVP. Khi cần → scheduled job xóa
rows `created_at < NOW() - INTERVAL '10 years'`.

---

## Consequences

### Positive
- Business context rõ ràng: "ai làm gì lúc nào, trước/sau ra sao"
- Cùng DB → không cần infrastructure thêm cho MVP
- Cùng transaction → không có audit log "phantom" (log thành công
  nhưng main operation fail)
- Scope giới hạn → table không phình to vô kiểm soát

### Negative / Trade-offs
- Developer phải nhớ gọi `audit_logger.log()` thủ công ở service layer
  — dễ bỏ sót
- `before`/`after` là JSONB → không có schema enforcement, dễ inconsistent
  giữa các service nếu không có convention rõ

### Neutral
- Cùng DB → audit log bị ảnh hưởng nếu DB down. Với scale MVP
  (50–100 phòng), acceptable trade-off.

---

## Mitigation

**Tránh bỏ sót audit call**: Viết integration test cho mỗi critical
action — assert rằng `audit_logs` có đúng 1 row sau khi gọi service.

**JSONB consistency**: Define TypedDict cho payload của từng action:
```python
class LeaseTerminatedPayload(TypedDict):
    terminated_at: str | None
    deposit_status: str
```

---

## References

- Phase 2 Summary — US-004, US-052, US-063
- ADR-0006: Data Retention (retention period)
- PostgreSQL JSONB: https://www.postgresql.org/docs/current/datatype-json.html
