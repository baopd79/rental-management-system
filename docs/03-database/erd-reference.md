# ERD Reference — RMS Phase 3

> **Status**: Approved (post-review 2026-04-18)
> **Scope**: 17 bảng MVP + constraints, indexes, relationships
> **History**: v1 chốt 9 nhóm → v2 fix 10 missing fields + 1 type change
> + 2 decision conflicts từ cross-check với US Phase 2

Tài liệu này là **companion** của `erd.mmd`. Khi cần thông tin chi tiết
không hiển thị được trong diagram, xem ở đây.

---

## 1. Tổng quan 17 bảng

| Nhóm | Bảng | Mục đích |
|------|------|----------|
| 1. Auth | `users` | Tài khoản đăng nhập (Landlord + Tenant) |
| 1. Auth | `invite_tokens` | Token mời Tenant (TTL 7d) |
| 1. Auth | `password_reset_tokens` | Token reset password (TTL 1h) |
| 1. Auth | `refresh_tokens` | JWT refresh tokens với rotation |
| 2. Property | `properties` | Nhà trọ |
| 2. Property | `rooms` | Phòng |
| 3. Tenant | `tenants` | Người thuê (domain, per rental cycle) |
| 3. Tenant | `occupants` | Người ở cùng (không có account) |
| 4. Lease | `leases` | Hợp đồng thuê |
| 5. Service | `services` | Dịch vụ (điện, nước, rác, internet...) |
| 5. Service | `service_rooms` | Junction cho scope=selected_rooms |
| 6. Meter | `meter_readings` | Chỉ số công tơ |
| 7. Invoice | `invoices` | Hoá đơn |
| 7. Invoice | `invoice_line_items` | Dòng chi tiết hoá đơn |
| 8. Payment | `payments` | Thanh toán |
| 9. Cross | `audit_logs` | Audit trail (ADR-0003) |
| 9. Cross | `notifications` | Thông báo in-app (ADR-0004) |

---

## 2. Lifecycle field patterns

### ADR-0001 patterns (system lifecycle)

| Pattern | Bảng | Field |
|---------|------|-------|
| Soft delete | `rooms`, `tenants` | `is_archived` + `archived_at` |
| Feature toggle | `services`, `users` | `is_active` |
| Event timestamp | `leases`, `invoices`, `refresh_tokens` | `terminated_at` / `voided_at` / `revoked_at` |
| Single-use token | `invite_tokens`, `password_reset_tokens` | `used_at` |

### Domain date fields (distinct from ADR-0001)

Đây là date fields mang semantics nghiệp vụ, **user-entered**, khác với
system timestamps của ADR-0001:

| Field | Bảng | Semantics |
|-------|------|-----------|
| `move_out_date` | `tenants` | Ngày Tenant **thực tế** dọn đi (nhập tay). Khác `archived_at` (timestamp system archive record). Có thể: `move_out_date = 15/5`, `archived_at = 20/5` nếu Landlord archive 5 ngày sau. |
| `moved_in_date` | `occupants` | Ngày bắt đầu ở cùng (NOT NULL) |
| `moved_out_date` | `occupants` | Ngày dọn đi. NULL = còn ở. Dùng như soft delete nhưng là date nghiệp vụ, không timestamp. |

**Query "active occupants"**: `WHERE moved_out_date IS NULL`.

---

## 3. Partial unique indexes

Postgres partial unique index = unique chỉ trong subset rows match WHERE.

```sql
-- Room display_name unique trong property, nhưng archived không tính
CREATE UNIQUE INDEX idx_unique_room_name_per_property
  ON rooms (property_id, display_name)
  WHERE is_archived = FALSE;

-- Tenant phone unique per Landlord, chỉ active
CREATE UNIQUE INDEX idx_unique_tenant_phone_per_landlord
  ON tenants (landlord_id, phone)
  WHERE is_archived = FALSE;

-- Tenant email unique per Landlord, chỉ active, chỉ nếu có email
CREATE UNIQUE INDEX idx_unique_tenant_email_per_landlord
  ON tenants (landlord_id, email)
  WHERE is_archived = FALSE AND email IS NOT NULL;

-- Strict single-active lease per room
CREATE UNIQUE INDEX idx_one_active_lease_per_room
  ON leases (room_id)
  WHERE terminated_at IS NULL;

-- Không duplicate Invoice cùng lease+month (trừ voided)
CREATE UNIQUE INDEX idx_unique_invoice_per_lease_month
  ON invoices (lease_id, billing_month)
  WHERE voided_at IS NULL;

-- Invoice number unique per Landlord (trừ voided)
CREATE UNIQUE INDEX idx_unique_invoice_number_per_landlord
  ON invoices (landlord_id, invoice_number)
  WHERE voided_at IS NULL;
```

---

## 4. CHECK constraints

```sql
-- properties
CHECK (billing_day BETWEEN 1 AND 28)

-- rooms
CHECK (max_occupants IS NULL OR max_occupants > 0)

-- leases
CHECK (end_date >= start_date)
CHECK (rent_amount >= 0)
CHECK (deposit_amount >= 0)
CHECK (billing_day BETWEEN 1 AND 28)

-- services
CHECK (price >= 0)
CHECK (
  (billing_type = 'per_meter' AND unit IS NOT NULL AND meter_scope IS NOT NULL) OR
  (billing_type != 'per_meter' AND unit IS NULL AND meter_scope IS NULL)
)

-- meter_readings
CHECK (reading_value >= 0)

-- invoices

CHECK (billing_month <= DATE_TRUNC('month', CURRENT_DATE))
CHECK (total_amount >= 0)
-- Void consistency
CHECK (
  (voided_at IS NULL AND voided_reason IS NULL AND voided_by_user_id IS NULL) OR
  (voided_at IS NOT NULL AND voided_reason IS NOT NULL AND voided_by_user_id IS NOT NULL)
)
-- void_note required when reason=other — enforce ở application layer

-- invoice_line_items
CHECK (billing_period_end >= billing_period_start)
CHECK (
  (line_type = 'adjustment') OR (amount >= 0)
)
CHECK (
  (line_type = 'service' AND service_id IS NOT NULL) OR
  (line_type IN ('rent', 'adjustment') AND service_id IS NULL)
)

-- occupants
CHECK (moved_out_date IS NULL OR moved_out_date >= moved_in_date)

-- payments
CHECK (amount > 0)
CHECK (paid_at <= CURRENT_DATE)
-- SKIP (non-immutable, enforce ở service layer):
-- CHECK (billing_month <= DATE_TRUNC('month', CURRENT_DATE))
-- CHECK (paid_at <= CURRENT_DATE)
-- Ở Phase 4 cần validate 2 rule này ở Pydantic/service layer.
```

---

## 5. Hot-path indexes

```sql
-- Meter readings
CREATE INDEX idx_readings_service_room_date
  ON meter_readings (service_id, room_id, reading_date DESC);

CREATE INDEX idx_readings_service_shared_date
  ON meter_readings (service_id, reading_date DESC)
  WHERE room_id IS NULL;

-- Invoice line items
CREATE INDEX idx_line_items_invoice
  ON invoice_line_items (invoice_id, sort_order);

CREATE INDEX idx_line_items_meter_readings
  ON invoice_line_items (meter_reading_start_id, meter_reading_end_id)
  WHERE meter_reading_start_id IS NOT NULL;

-- Payments
CREATE INDEX idx_payments_invoice
  ON payments (invoice_id, paid_at);

-- Audit logs
CREATE INDEX idx_audit_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX idx_audit_actor  ON audit_logs (actor_id);
CREATE INDEX idx_audit_time   ON audit_logs (created_at DESC);

-- Notifications
CREATE INDEX idx_notif_recipient
  ON notifications (recipient_id, is_read, created_at DESC);

-- Token lookups
CREATE INDEX idx_invite_tokens_hash ON invite_tokens (token_hash);
CREATE INDEX idx_password_reset_tokens_hash ON password_reset_tokens (token_hash);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens (token_hash);

-- Soft delete partial indexes
CREATE INDEX idx_rooms_active
  ON rooms (property_id) WHERE is_archived = FALSE;

CREATE INDEX idx_tenants_active
  ON tenants (landlord_id) WHERE is_archived = FALSE;

-- Active occupants (query phổ biến cho billing per_person)
CREATE INDEX idx_occupants_active
  ON occupants (tenant_id) WHERE moved_out_date IS NULL;
```

---

## 6. Denormalization decisions

| Field | Bảng đích | Lý do |
|-------|-----------|-------|
| `landlord_id` | `invoices` | Unique invoice_number per Landlord, ownership check không JOIN chain 3 bảng |
| `landlord_id` | `audit_logs` | Query "audit của tôi" không cần JOIN |

Các bảng khác **không denormalize** (`payments.tenant_id`,
`invoices.room_id`, etc.) vì chain JOIN ≤ 2 bảng là đủ cho MVP scale.

---

## 7. Foreign Key ON DELETE behaviors

| FK | ON DELETE | Lý do |
|----|-----------|-------|
| `invite_tokens.tenant_id` | CASCADE | Token không có ý nghĩa khi Tenant bị xóa |
| `password_reset_tokens.user_id` | CASCADE | Tokens follow user lifecycle |
| `refresh_tokens.user_id` | CASCADE | Same |
| `refresh_tokens.rotated_to_id` | SET NULL | Self-ref, không break chain |
| `properties.landlord_id` | RESTRICT | Không cho delete User khi còn Property |
| `rooms.property_id` | RESTRICT | Hard delete Property chỉ khi hết Room |
| `tenants.user_id` | SET NULL | Anonymize User không break Tenant record |
| `tenants.landlord_id` | RESTRICT | Không cho delete Landlord khi còn Tenant |
| `tenants.promoted_from_occupant_id` | SET NULL | Occupant có thể bị hard delete (case nhập nhầm), giữ Tenant record |
| `occupants.tenant_id` | CASCADE | Occupants thuộc về Tenant |
| `leases.room_id` | RESTRICT | Room không thể hard delete khi còn Lease |
| `leases.tenant_id` | RESTRICT | Tenant không hard delete |
| `services.property_id` | CASCADE | Services thuộc Property |
| `service_rooms.service_id` | CASCADE | Junction follow Service |
| `service_rooms.room_id` | CASCADE | Junction follow Room |
| `meter_readings.service_id` | RESTRICT | Không xóa Service nếu còn readings |
| `meter_readings.room_id` | RESTRICT | Không hard delete Room nếu còn readings |
| `meter_readings.created_by_user_id` | RESTRICT | Audit |
| `invoices.lease_id` | RESTRICT | Lease không hard delete nếu còn Invoice |
| `invoices.landlord_id` | RESTRICT | — |
| `invoices.created_by_user_id` | RESTRICT | Audit |
| `invoices.voided_by_user_id` | RESTRICT | Audit |
| `invoice_line_items.invoice_id` | CASCADE | Lines thuộc Invoice |
| `invoice_line_items.service_id` | RESTRICT | — |
| `invoice_line_items.meter_reading_*_id` | RESTRICT | Giữ integrity với reading |
| `payments.invoice_id` | RESTRICT | Payment giữ audit dù Invoice void |
| `payments.recorded_by_user_id` | RESTRICT | — |
| `audit_logs.actor_id` | RESTRICT | Không xóa audit khi xóa User |
| `audit_logs.landlord_id` | RESTRICT | — |
| `notifications.recipient_id` | CASCADE | Notifications follow recipient |

---

## 8. JSONB fields

Chỉ 2 fields dùng JSONB:

- `audit_logs.before` — partial snapshot trước event
- `audit_logs.after` — partial snapshot sau event

Không index JSONB trong MVP (xem ADR-0003).

---

## 9. Enum types

Dùng PostgreSQL enum type thay cho VARCHAR + CHECK:

```sql
CREATE TYPE user_role_enum          AS ENUM ('landlord', 'tenant');
CREATE TYPE deposit_status_enum     AS ENUM ('held', 'returned', 'forfeited', 'deducted');
CREATE TYPE billing_type_enum       AS ENUM ('per_meter', 'per_person', 'fixed');
CREATE TYPE service_scope_enum      AS ENUM ('all_rooms', 'selected_rooms');
CREATE TYPE meter_scope_enum        AS ENUM ('shared', 'per_room');
CREATE TYPE line_type_enum          AS ENUM ('rent', 'service', 'adjustment');
CREATE TYPE payment_method_enum     AS ENUM ('cash', 'bank_transfer', 'ewallet', 'other');
CREATE TYPE voided_reason_enum      AS ENUM (
  'wrong_meter_reading',
  'wrong_rent',
  'wrong_service_config',
  'tenant_dispute',
  'duplicate',
  'other'
);
```

---

## 10. Phase 2 overrides (post-review 2026-04-18)

Quyết định Phase 3 override Phase 2 text ở 2 chỗ:

### Override 1 — US-036 Promote Occupant

**Phase 2 text (US-036 AC2 Step 2)**: "Xoá Occupant record cũ (vì đã
'lên chức' Tenant)"

**Phase 3 decision**: **Không hard delete Occupant**. Thay vào đó:
- Set `occupants.moved_out_date = effective_date` của promote
- `tenants.promoted_from_occupant_id = old_occupant.id` (new Tenant)
- Giữ Occupant row cho audit trail

**Lý do**:
- Hard delete làm `promoted_from_occupant_id` FK bị SET NULL → mất trace
- Keep record cho ADR-0003 audit

**Action cần làm ở Phase 4**: Update code implement US-036 theo quyết
định mới, không theo Phase 2 text literal.

### Override 2 — US-030 Reactivation flow

**Phase 2 text (US-030 AC7-AC8)**: Landlord nhập phone trùng Tenant
archived → dialog [A] reactivate / [B] new / [C] cancel.

**Phase 3 initial decision** (sai): "Tenant per rental cycle — luôn
create new".

**Phase 3 revised decision** (đúng): Support cả 2 flows như US yêu cầu.

- **Flow A (reactivate)**: Unarchive Tenant cũ:
  ```sql
  UPDATE tenants SET
    is_archived = FALSE,
    archived_at = NULL,
    move_out_date = NULL
  WHERE id = ?
  ```
  Giữ `user_id` cũ, `anonymized_at` cũ (nếu đã anonymize thì không
  reactivate được — data gone).

- **Flow B (create new)**: Tạo Tenant record mới với `user_id = NULL`.

**Schema không đổi** — đã support sẵn qua partial unique index trên
active Tenants.

---

## 11. Open items cho Phase 4

1. Invoice number generation — cần PostgreSQL `SEQUENCE` per Landlord
   per month, hoặc application-level lock
2. Cron job anonymize tenants (ADR-0006) — APScheduler task
3. Refresh token rotation detection — service layer logic
4. Audit log helper middleware/decorator
5. Notification delivery cho Tenant chưa có account — skip gracefully
6. `updated_at` auto-update — SQLModel event listener hoặc PG trigger
   (chưa decide)
7. Dialog reactivation flow UI (US-030 AC7) — frontend logic
