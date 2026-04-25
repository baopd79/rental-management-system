# ADR-0001: Lifecycle Field Naming Convention

> **Status**: Accepted
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

Phase 2 xác định nhiều pattern lifecycle khác nhau cho entities, dùng
tên field khác nhau. Nếu không chuẩn hoá, dev (cả Bảo và contributor
tương lai) sẽ nhầm lẫn: "entity này soft-delete hay toggle? Có restore
được không?"

Các pattern đã xuất hiện trong Phase 2:

- `rooms`, `tenants`: soft delete với `is_archived` + `archived_at`
- `services`, `users`: feature toggle với `is_active`
- `leases`: event timestamp với `terminated_at`
- `invoices`: event timestamp với `voided_at`
- `refresh_tokens`: event timestamp với `revoked_at`

---

## Options Considered

### Option 1: Một field `status` enum cho tất cả

**Pros**: Uniform, dễ query.
**Cons**: Ép nhiều concept khác nhau vào 1 field → mất ngữ nghĩa. Status
"archived" vs "inactive" vs "terminated" conceptually khác nhau, gộp
chung sẽ mất thông tin về intent.

### Option 2: Chuẩn hoá theo semantic (đã dùng Phase 2)

Tách 3 pattern theo ngữ nghĩa:

- Soft delete (có thể restore, UI ẩn khỏi list default): `is_archived` + `archived_at`
- Feature toggle (bật/tắt, không phải delete): `is_active`
- Event timestamp (trạng thái = có/không có event): `<event>_at`

**Pros**: Ngữ nghĩa rõ, dev đọc field name hiểu ngay intent.
**Cons**: Phải nhớ 3 pattern (nhưng có document này).

### Option 3: Dùng ORM soft-delete library (SQLAlchemy plugin)

**Pros**: Tự động filter archived khỏi queries.
**Cons**: Magic behavior, khó debug. Không cover được Service toggle và
Lease termination (không phải soft-delete). Vendor lock-in vào plugin.

---

## Decision

**Chọn Option 2**. Ba pattern rõ ràng, áp dụng theo semantic:

| Pattern | Fields | Khi nào dùng | Entities |
|---------|--------|--------------|----------|
| Soft Delete | `is_archived: bool`, `archived_at: timestamptz` | Entity "biến mất khỏi UI" nhưng giữ data cho FK integrity + audit | `rooms`, `tenants` |
| Feature Toggle | `is_active: bool` | Entity vẫn tồn tại và visible, chỉ đang "tắt chức năng" | `services`, `users` |
| Event Timestamp | `<event>_at: timestamptz` | Trạng thái là event, có thể reverse qua event khác | `leases.terminated_at`, `invoices.voided_at`, `refresh_tokens.revoked_at` |

---

## Rules cho dev

### Rule 1 — Query default

- **Soft Delete**: query default thêm `WHERE is_archived = FALSE`.
  Muốn include archived → explicit `include_archived=True` param.
- **Feature Toggle**: query mặc định KHÔNG filter — entity vẫn hiển
  thị dưới dạng "đã tắt". UI tự handle ẩn/hiện.
- **Event Timestamp**: không có boolean `is_terminated`. Check
  `terminated_at IS NOT NULL`. Lý do: timestamp vừa là state vừa là
  data (khi nào xảy ra).

### Rule 2 — Không trộn pattern

Không dùng đồng thời `is_archived` + `is_active` trên cùng entity.
Chọn 1 pattern theo semantic.

### Rule 3 — Không dùng `deleted_at`

Tên gây nhầm lẫn giữa soft delete và hard delete. Dùng `archived_at`
thay thế.

### Rule 4 — API không expose internal lifecycle fields

- `archived_at`, `is_archived`, `is_active`, `revoked_at` → KHÔNG trả
  về trong response body của API public
- Client chỉ nhận computed `status` field (ví dụ `lease.status`,
  `room.status`)
- Exception: Admin/debug endpoint (ngoài MVP scope)

### Rule 5 — Invariant phải được enforce ở application layer

```python
# Đúng — set cả hai field cùng lúc
entity.is_archived = True
entity.archived_at = datetime.now(UTC)

# Sai — chỉ set 1 field, tạo inconsistency
entity.is_archived = True  # archived_at còn NULL
```

### Rule 6 — Migration convention

Khi thêm soft delete vào entity mới:

```sql
ALTER TABLE <table>
  ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN archived_at TIMESTAMPTZ DEFAULT NULL;

-- Partial index: chỉ index active records
CREATE INDEX idx_<table>_active
  ON <table> (<parent_fk_id>)
  WHERE is_archived = FALSE;
```

**Lý do partial index**: Table như `tenants` sẽ có hàng nghìn row
archived sau vài năm. Partial index chỉ cover `is_archived = FALSE` →
list query active nhanh hơn đáng kể, size index nhỏ hơn.

---

## Consequences

### Positive
- Field name tự diễn đạt intent, giảm cognitive load
- Dễ grep: tìm mọi soft-delete entity → search `is_archived`
- Tránh bug "status lệch data"
- Query pattern nhất quán, dễ review

### Negative / Trade-offs
- Phải nhớ 3 pattern — chấp nhận được với document này
- Soft Delete cần nhớ thêm filter `WHERE is_archived = FALSE` — dễ bỏ
  sót nếu không có base query class
- Event Timestamp không có boolean đi kèm → developer phải quen với
  `IS NULL` / `IS NOT NULL` check

### Neutral
- Naming là convention, không enforce bằng DB. Phụ thuộc code review và
  test coverage.

---

## Mitigation

**Tránh bỏ sót `WHERE is_archived = FALSE`**:
- Repository layer dùng base class với filtered default query
- Integration test kiểm tra archived entity không xuất hiện trong list API

---

## References

- Phase 2 Summary §3 Pattern 6 (Soft delete vs Toggle)
- Phase 2 Nhóm 2 (Room), Nhóm 3 (Tenant), Nhóm 4 (Lease), Nhóm 5 (Service)
- PostgreSQL partial indexes: https://www.postgresql.org/docs/current/indexes-partial.html
