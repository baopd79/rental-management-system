# Endpoint Mapping — RMS MVP

> **Status**: APPROVED (Phase 3 Chat 4, S4.2)
> **Scope**: 100% endpoints MVP, map sang Phase 2 user stories
> **Conventions**: xem `api-design-decisions.md`
> **Next step**: S4.4 — viết `openapi.yaml` dựa trên file này
>
> **Legend**:
> - 🏠 Landlord only
> - 👤 Tenant only
> - 🔓 Public (no auth)
> - 🔑 Auth required (role checked at handler)
> - ✅ Must story
> - ⚠️ Should story
> - 💡 Could story

---

## Summary

| Resource group | Endpoints | Stories covered |
|---|---|---|
| Auth | 8 | US-001→008 |
| Users | 3 | US-004 |
| Properties | 5 | US-010→013 |
| Rooms | 6 | US-015→018 |
| Tenants | 8 | US-023→032 |
| Occupants | 5 | US-033→036 |
| Leases | 8 | US-037→056 |
| Services | 7 | US-057→061 |
| Meter Readings | 5 | US-064→072 |
| Invoices | 9 | US-076→082 |
| Payments | 4 | US-090→094 |
| Notifications | 3 | ADR-0004 in-app badge |
| **Total** | **71** | **63 stories Phase 2** |

---

## 1. Auth — `/api/v1/auth/*`

Tất cả public (không cần JWT). Xem `api-design-decisions.md` section B3-B5.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 1 | POST | `/api/v1/auth/register` | 🔓 | US-001 ✅ | Landlord self-signup. Body: `{email, password, full_name, phone?}` |
| 2 | POST | `/api/v1/auth/login` | 🔓 | US-002 ✅ | Body: `{email, password}`. Response: access token + refresh cookie |
| 3 | POST | `/api/v1/auth/refresh` | 🔓 | US-003 ✅ | Cookie hoặc body `{refresh_token}`. Response: new access + new refresh cookie |
| 4 | POST | `/api/v1/auth/logout` | 🔑 | US-003 ✅ | Revoke current refresh token. Response: 204 |
| 5 | POST | `/api/v1/auth/invite/verify` | 🔓 | US-007 ✅ | Preview token + email trước khi set password |
| 6 | POST | `/api/v1/auth/invite/accept` | 🔓 | US-007 ✅ | Activate Tenant + set password + auto-login |
| 7 | POST | `/api/v1/auth/password-reset/request` | 🔓 | US-008 ✅ | Enumeration-safe. Body: `{email}` |
| 8 | POST | `/api/v1/auth/password-reset/confirm` | 🔓 | US-008 ✅ | Body: `{token, new_password}`. NO auto-login |

**Gap note**: US-002 không spec logout-all (single device logout đủ MVP). US-005/006 (RBAC check) là middleware concern, không endpoint riêng.

---

## 2. Users — `/api/v1/users`

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 9 | GET | `/api/v1/users/me` | 🔑 | US-004 ✅ | Own profile. Response: `{id, email, role, full_name, phone, is_active, created_at}` |
| 10 | PATCH | `/api/v1/users/me` | 🔑 | US-004 ✅ | Cập nhật profile. Body: `{full_name?, phone?, email?}`. Không đổi role/password ở đây |
| 11 | POST | `/api/v1/users/me/change-password` | 🔑 | US-004 ⚠️ | Body: `{current_password, new_password}`. Khác password-reset (cần current password) |

**Gap note**: Admin list users không có MVP (defer v2.x `/admin/*`).

---

## 3. Properties — `/api/v1/properties`

Landlord only. Tenant không thấy properties.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 12 | GET | `/api/v1/properties` | 🏠 | US-010 ✅ | List own properties. Filter: `name__contains`. Sort: `name`. Pagination standard |
| 13 | POST | `/api/v1/properties` | 🏠 | US-011 ✅ | Create property. Body: `{name, address, billing_day?}` |
| 14 | GET | `/api/v1/properties/{id}` | 🏠 | US-010 ✅ | Detail + stats (room count, active lease count, monthly revenue) |
| 15 | PATCH | `/api/v1/properties/{id}` | 🏠 | US-012 ✅ | Partial update. Body: `{name?, address?, billing_day?}` |
| 16 | DELETE | `/api/v1/properties/{id}` | 🏠 | US-013 ✅ | Hard delete. Guard: không delete khi còn Room → 409 `PROPERTY_HAS_ROOMS` |

**Filterable fields**: `name__contains`.
**Sortable fields**: `name`, `created_at`.

---

## 4. Rooms — `/api/v1/rooms`

Landlord manage. Tenant view room của mình (qua lease active).

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 17 | GET | `/api/v1/properties/{pid}/rooms` | 🏠 | US-015 ✅ | List rooms của property. Filter: `is_archived`, `status__in`. Sort: `display_name` |
| 18 | POST | `/api/v1/properties/{pid}/rooms` | 🏠 | US-016 ✅ | Create room. Body: `{display_name, floor?, max_occupants?, default_rent, note?}` |
| 19 | GET | `/api/v1/rooms/{id}` | 🔑 | US-015 ✅ | Detail. Computed: `status` (vacant/occupied/expiring_soon/lease_expired). Landlord = any, Tenant = chỉ room đang thuê |
| 20 | PATCH | `/api/v1/rooms/{id}` | 🏠 | US-017 ✅ | Partial update. Body: `{display_name?, floor?, max_occupants?, default_rent?, note?}` |
| 21 | POST | `/api/v1/rooms/{id}/archive` | 🏠 | US-018 ✅ | Soft delete. Guard: active lease → 409 `ROOM_HAS_ACTIVE_LEASE`, unpaid invoice → 409 `ROOM_HAS_UNPAID_INVOICES` |
| 22 | GET | `/api/v1/rooms` | 🏠 | US-015 ✅ | Alias flat: `?property_id=X`. Cross-property filter: `?status=vacant` (Landlord dashboard) |

**Filterable fields**: `property_id`, `is_archived`, `status__in`, `display_name__contains`.
**Sortable fields**: `display_name`, `default_rent`, `created_at`.

**Computed field `status`**:
```
vacant         = no active/expiring/expired lease
occupied       = lease.status = active
expiring_soon  = lease.status = expiring_soon (≤30 days to end_date)
lease_expired  = lease.status = expired (end_date passed, not terminated)
```

---

## 5. Tenants — `/api/v1/tenants`

Landlord manage. Tenant view own profile (qua `/users/me`).

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 23 | GET | `/api/v1/tenants` | 🏠 | US-023 ✅ | List tenants của landlord. Filter: `is_archived`, `name__contains`, `phone__startswith`. Sort: `name` |
| 24 | POST | `/api/v1/tenants` | 🏠 | US-024 ✅ | Create tenant record + generate invite. Body: `{name, phone, email?, id_card_number?, note?}`. Response: `{tenant, invite_link}` |
| 25 | GET | `/api/v1/tenants/{id}` | 🏠 | US-023 ✅ | Detail. Computed: `status` (pending/active/moved_out) |
| 26 | PATCH | `/api/v1/tenants/{id}` | 🏠 | US-025 ✅ | Partial update. Body: `{name?, phone?, email?, id_card_number?, note?}` |
| 27 | POST | `/api/v1/tenants/{id}/archive` | 🏠 | US-032 ✅ | Soft delete. Guards: active lease → 409, unpaid invoices → 409. Side effect: invalidate User account |
| 28 | POST | `/api/v1/tenants/{id}/reactivate` | 🏠 | US-030 ✅ | Unarchive. Guard: anonymized → 409 `TENANT_ANONYMIZED`. Side effect: không send invite lại tự động |
| 29 | POST | `/api/v1/tenants/{id}/resend-invite` | 🏠 | — | Inferred from invite flow (re-gen token if invite chưa dùng/hết hạn). Guard: tenant đã có account → 409 |
| 30 | GET | `/api/v1/tenants/{id}/invoices` | 🏠 | — | Cross-lease invoices của 1 tenant. Alias for `/invoices?tenant_id={id}` |

**Filterable fields**: `is_archived`, `name__contains`, `phone__startswith`, `email__contains`.
**Sortable fields**: `name`, `created_at`.

**Tenant status computed**:
```
pending    = user_id IS NOT NULL và chưa có active lease
active     = có ít nhất 1 active lease (qua lease → room → property của landlord)
moved_out  = is_archived = TRUE
```

**Reactivation flow note** (US-030):
- Landlord tạo Tenant mới, nhập phone trùng tenant archived → UI show dialog [A] reactivate / [B] create new
- [A] → `POST /tenants/{archived_id}/reactivate`
- [B] → `POST /tenants` thường (tạo record mới)

---

## 6. Occupants — `/api/v1/occupants`

Landlord only. Occupant không có account.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 31 | GET | `/api/v1/tenants/{tid}/occupants` | 🏠 | US-033 ✅ | List occupants của tenant. Filter: `moved_out_date__isnull`. Default: active only |
| 32 | POST | `/api/v1/tenants/{tid}/occupants` | 🏠 | US-033 ✅ | Add occupant. Body: `{name, moved_in_date, id_card_number?, note?}` |
| 33 | PATCH | `/api/v1/occupants/{id}` | 🏠 | US-033 ✅ | Update. Body: `{name?, moved_in_date?, moved_out_date?, id_card_number?, note?}` |
| 34 | DELETE | `/api/v1/occupants/{id}` | 🏠 | US-034 ✅ | Hard delete. Only if: chưa được reference (`promoted_from_occupant_id IS NULL`). Guard: else 409 |
| 35 | POST | `/api/v1/occupants/{id}/promote` | 🏠 | US-036 ✅ | Promote to Tenant representative. Atomic: update occupant + create tenant + update lease. Body: `{effective_date, tenant_info: {name, phone, email?, id_card_number?}}` |

**Filterable fields**: `moved_out_date__isnull` (active/history).

**Promote response** (multi-resource):
```json
{
  "new_tenant": {...},
  "updated_occupant": {"moved_out_date": "..."},
  "updated_lease": {"tenant_id": "new_tenant_id"}
}
```

---

## 7. Leases — `/api/v1/leases`

Landlord manage. Tenant view own lease.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 36 | GET | `/api/v1/rooms/{rid}/leases` | 🏠 | US-037 ✅ | Lease history của room. Sort: `-start_date`. Filter: `terminated_at__isnull` |
| 37 | POST | `/api/v1/rooms/{rid}/leases` | 🏠 | US-038 ✅ | Create lease (draft). Body: `{tenant_id, start_date, end_date, rent_amount, deposit_amount, billing_day, note?}`. Guard: active lease exists → 409 `ROOM_HAS_ACTIVE_LEASE` |
| 38 | GET | `/api/v1/leases/{id}` | 🔑 | US-037 ✅ | Detail. Computed: `status`. Landlord = any own, Tenant = only own |
| 39 | PATCH | `/api/v1/leases/{id}` | 🏠 | US-039 ⚠️ | Limited update. Body: `{end_date?, note?}`. Guard: active lease chỉ cho phép 2 fields đó |
| 40 | POST | `/api/v1/leases/{id}/terminate` | 🏠 | US-055 ✅ | Body: `{terminated_date, reason?}`. Side effects: set `terminated_at`, prompt invoice cuối (response kèm `pending_final_invoice: true/false`) |
| 41 | POST | `/api/v1/leases/{id}/settle-deposit` | 🏠 | US-056 ✅ | Body: `{deposit_status, amount_returned?, deduction_note?}`. `deposit_status` ∈ `{returned, forfeited, deducted}`. Side effect: auto-archive tenant nếu không còn active lease |
| 42 | POST | `/api/v1/leases/{id}/renew` | 🏠 | US-050 ⚠️ | Tạo Lease mới link chain. Body: `{start_date, end_date, rent_amount, deposit_amount?, billing_day?, note?}`. Response: `{new_lease, previous_lease_id}` |
| 43 | GET | `/api/v1/leases` | 🔑 | US-037 ✅ | Flat alias. Landlord: all own. Tenant: own lease. Filter: `room_id`, `tenant_id`, `status__in`, `terminated_at__isnull` |

**Filterable fields**: `room_id`, `tenant_id`, `status__in`, `terminated_at__isnull`, `end_date__lte`, `end_date__gte`.
**Sortable fields**: `start_date`, `end_date`, `created_at`.

**Lease status computed**:
```
draft          = start_date > TODAY (not yet started)
active         = start_date <= TODAY AND end_date > TODAY + 30d AND terminated_at IS NULL
expiring_soon  = start_date <= TODAY AND end_date BETWEEN TODAY AND TODAY+30d AND terminated_at IS NULL
expired        = end_date < TODAY AND terminated_at IS NULL
terminated     = terminated_at IS NOT NULL
```

**Terminate response**:
```json
{
  "lease": {...terminated lease},
  "pending_final_invoice": true,
  "suggested_billing_month": "2026-05"
}
```

---

## 8. Services — `/api/v1/services`

Landlord only.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 44 | GET | `/api/v1/properties/{pid}/services` | 🏠 | US-057 ✅ | List services của property. Filter: `is_active`, `billing_type` |
| 45 | POST | `/api/v1/properties/{pid}/services` | 🏠 | US-058 ✅ | Create service. Body: `{name, billing_type, price, unit?, scope, applied_room_ids?, note?}`. Guard: `per_meter` phải có `unit` + `scope` |
| 46 | GET | `/api/v1/services/{id}` | 🏠 | US-057 ✅ | Detail kèm `applied_room_ids` array |
| 47 | PATCH | `/api/v1/services/{id}` | 🏠 | US-059 ✅ | Partial update. Body: `{name?, applied_room_ids?, note?}`. **Immutable**: `billing_type`, `unit`, `price`, `scope`. Đổi giá → deactivate + tạo service mới |
| 48 | POST | `/api/v1/services/{id}/activate` | 🏠 | US-061 ✅ | Toggle `is_active=true`. Guard: đã active → 409 `SERVICE_ALREADY_ACTIVE` |
| 49 | POST | `/api/v1/services/{id}/deactivate` | 🏠 | US-061 ✅ | Toggle `is_active=false`. Guard: đã inactive → 409 `SERVICE_ALREADY_INACTIVE` |
| 50 | GET | `/api/v1/services` | 🏠 | US-057 ✅ | Flat alias: `?property_id=X`. Filter: `is_active`, `billing_type` |

**Filterable fields**: `property_id`, `is_active`, `billing_type`.
**Sortable fields**: `name`, `created_at`.

**Immutability note**: `billing_type` và `unit` không đổi được sau khi tạo (PATCH guard). Nếu cần đổi → deactivate + tạo service mới.

---

## 9. Meter Readings — `/api/v1/meter-readings`

Landlord only.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 51 | POST | `/api/v1/properties/{pid}/meter-readings` | 🏠 | US-064 ✅ | **Batch create** (primary UX). Body: `{reading_date, readings: [{service_id, room_id?, value, note?}]}`. All-or-nothing. Max 100/batch. Warnings trong response. |
| 52 | GET | `/api/v1/meter-readings` | 🏠 | US-065 ✅ | List. Filter: `property_id`, `service_id`, `room_id__isnull`, `reading_date__gte`, `reading_date__lte` |
| 53 | GET | `/api/v1/meter-readings/{id}` | 🏠 | US-065 ✅ | Detail. Kèm `previous_reading` (service + room same) và `referenced_invoice_id` nếu đã dùng |
| 54 | PATCH | `/api/v1/meter-readings/{id}` | 🏠 | US-071 ✅ | Sửa value/note. Guard: `referenced_invoice_id IS NOT NULL AND invoice.status IN (paid, partial)` → 409 `READING_REFERENCED_BY_PAID_INVOICE`. Nếu ref invoice unpaid → 200 + warning |
| 55 | DELETE | `/api/v1/meter-readings/{id}` | 🏠 | US-072 ⚠️ | Guard: referenced by invoice → 409. |

**Filterable fields**: `property_id`, `service_id`, `room_id`, `room_id__isnull`, `reading_date__gte`, `reading_date__lte`.
**Sortable fields**: `reading_date`.

**Batch response**:
```json
{
  "data": [...created readings...],
  "summary": {
    "created_count": 3,
    "warning_count": 1,
    "warnings": [
      {
        "index": 0,
        "type": "value_lower_than_previous",
        "message": "Reading 1234 < previous 1250"
      }
    ]
  }
}
```

**Mutability rules** (Phase 2 US-071):
```
reading.referenced_invoice_ids = []         → sửa thoải mái
reading.referenced_invoice đang unpaid      → warn, không block (PATCH OK, response kèm warning)
reading.referenced_invoice đang paid/partial → block 409 READING_REFERENCED_BY_PAID_INVOICE
```

---

## 10. Invoices — `/api/v1/invoices`

Landlord manage, Tenant view own.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 56 | POST | `/api/v1/properties/{pid}/invoices/preview` | 🏠 | US-076 ✅ | **Preview batch** (no persist). Body: `{billing_month, exclude_lease_ids?}`. Response: preview array + summary + warnings |
| 57 | POST | `/api/v1/properties/{pid}/invoices` | 🏠 | US-077 ✅ | **Commit batch** (persist). Body: `{billing_month, exclude_lease_ids?, on_duplicate?}`. Response: created invoices + summary. Guard: duplicate (lease+month) skip hoặc 409 theo `on_duplicate` body field |
| 58 | POST | `/api/v1/leases/{lid}/invoices/preview` | 🏠 | US-076 ✅ | Preview single lease invoice |
| 59 | POST | `/api/v1/leases/{lid}/invoices` | 🏠 | US-077 ✅ | Commit single lease invoice. Guard: duplicate → 409 `DUPLICATE_INVOICE` |
| 60 | GET | `/api/v1/invoices` | 🔑 | US-078 ✅ | List. Landlord = all own. Tenant = own only. Filter: `status__in`, `lease_id`, `tenant_id`, `billing_month__gte`, `billing_month__lte`, `voided_at__isnull` |
| 61 | GET | `/api/v1/leases/{lid}/invoices` | 🔑 | US-078 ✅ | Alias nested: invoices của 1 lease |
| 62 | GET | `/api/v1/invoices/{id}` | 🔑 | US-079 ✅ | Detail kèm `line_items` array. Landlord + Tenant xem được. Tenant: chỉ own |
| 63 | POST | `/api/v1/invoices/{id}/void` | 🏠 | US-082 ✅ | Body: `{reason, note?}`. `reason` ∈ voided_reason_enum. Guard: đã void → 409. Response: voided invoice |

**Filterable fields**: `status__in`, `lease_id`, `tenant_id`, `property_id`, `billing_month__gte`, `billing_month__lte`, `voided_at__isnull`.
**Sortable fields**: `billing_month`, `total_amount`, `created_at`.

**Preview response shape**:
```json
{
  "data": [
    {
      "lease_id": "...",
      "room_display_name": "P101",
      "tenant_name": "Nguyen Van A",
      "billing_month": "2026-05",
      "total_amount": 2500000,
      "line_items": [
        {
          "line_type": "rent",
          "description": "Tiền phòng tháng 5/2026",
          "amount": 2000000,
          "billing_period_start": "2026-05-01",
          "billing_period_end": "2026-05-31"
        },
        {
          "line_type": "service",
          "service_name": "Điện",
          "description": "120 kWh (1110 → 1230)",
          "amount": 400000,
          "billing_period_start": "2026-04-01",
          "billing_period_end": "2026-04-30"
        }
      ],
      "warnings": []
    }
  ],
  "summary": {
    "total_invoices": 8,
    "total_amount": 18500000,
    "excluded_count": 2,
    "warning_count": 0
  }
}
```

**Invoice status** (computed từ payments):
```
unpaid   = total_paid = 0
partial  = 0 < total_paid < total_amount
paid     = total_paid >= total_amount
void     = voided_at IS NOT NULL
```

**Line item types**:
- `rent` — tiền phòng (pro-rata nếu partial month)
- `service` — điện/nước/internet... (mô tả kèm reading cũ/mới)
- `adjustment` — manual (Landlord add note)

**`on_duplicate` body field** cho batch commit:
- `skip` (default) — bỏ qua lease có invoice trùng tháng
- `error` — fail nếu có bất kỳ duplicate

---

## 11. Payments — `/api/v1/payments`

Landlord manage. Tenant view own (read-only).

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 64 | GET | `/api/v1/invoices/{iid}/payments` | 🔑 | US-090 ✅ | Payments của invoice. Landlord + Tenant view. Sort: `-paid_at` |
| 65 | POST | `/api/v1/invoices/{iid}/payments` | 🏠 | US-091 ✅ | Record payment. Body: `{amount, method, paid_at, note?}`. Guards: overpay → 422, future date → 422, invoice voided → 409 |
| 66 | GET | `/api/v1/payments` | 🔑 | US-090 ✅ | Flat alias. Filter: `invoice_id`, `method`, `paid_at__gte`, `paid_at__lte` |
| 67 | GET | `/api/v1/payments/{id}` | 🔑 | US-090 ✅ | Detail |
| 68 | DELETE | `/api/v1/payments/{id}` | 🏠 | US-094 ⚠️ | Hard delete (ghi nhầm). Side effect: recompute invoice.status. Response: 200 kèm `updated_invoice: {status}` |

**Filterable fields**: `invoice_id`, `method`, `paid_at__gte`, `paid_at__lte`.
**Sortable fields**: `paid_at`, `amount`.

**Payment method enum**: `cash`, `bank_transfer`, `ewallet`, `other`.

**Delete response** (kèm updated invoice):
```json
{
  "deleted_payment_id": "...",
  "updated_invoice": {
    "id": "...",
    "status": "unpaid",
    "total_paid": 0
  }
}
```

---

## 12. Notifications — `/api/v1/notifications`

In-app badge MVP. Cả Landlord + Tenant nhận.

| # | Method | Path | Auth | Stories | Notes |
|---|---|---|---|---|---|
| 69 | GET | `/api/v1/notifications` | 🔑 | ADR-0004 | List notifications của user. Filter: `is_read`, `type__in`. Sort: `-created_at`. Response kèm `unread_count` trong envelope |
| 70 | POST | `/api/v1/notifications/{id}/read` | 🔑 | ADR-0004 | Mark 1 as read. Response: 200 |
| 71 | POST | `/api/v1/notifications/read-all` | 🔑 | ADR-0004 | Mark all as read. Response: `{marked_count: N}` |

**Notification types** (trigger từ cron ADR-0002):

| Type | Trigger | Recipient |
|---|---|---|
| `lease_expiring_soon` | Lease `end_date` ≤ 30 ngày | Landlord |
| `lease_expired` | Lease `end_date` passed, không terminate | Landlord |
| `invoice_created` | Invoice được tạo | Tenant |
| `invoice_overdue` | Invoice unpaid sau billing_day + 15 ngày | Landlord + Tenant |
| `invoice_reminder` | Ngày 5 chưa xuất invoice cho property | Landlord |
| `payment_received` | Payment được record | (Landlord only — self record) |

**Envelope cho list notifications**:
```json
{
  "data": [...],
  "pagination": {...},
  "unread_count": 3
}
```

---

## 13. Cross-Cutting: Không có endpoint riêng

Các concerns sau là **server-side only**, không expose endpoint:

| Concern | Implementation | Phase |
|---|---|---|
| Computed room.status | Query-time derive từ lease | Phase 4 |
| Computed lease.status | Query-time derive từ dates | Phase 4 |
| Computed invoice.status | Query-time sum payments | Phase 4 |
| Computed tenant.status | Query-time derive từ lease | Phase 4 |
| Audit logging | Middleware/decorator tự động | Phase 4 (ADR-0003) |
| Cron daily 00:05 | APScheduler task | Phase 4 (ADR-0002) |
| Rate limiting | slowapi middleware | Phase 4 |
| PII anonymization | APScheduler task (5-year) | Phase 4 (ADR-0006) |

---

## 14. User Story Coverage Matrix

| US Group | Stories range | Endpoints | Notes |
|---|---|---|---|
| Nhóm 1 — Auth/RBAC | US-001→008 | #1→#11 | Full cover. RBAC = middleware, không endpoint. #29 resend-invite inferred |
| Nhóm 2 — Property/Room | US-010→022 | #12→#22 | Full cover |
| Nhóm 3 — Tenant/Occupant | US-023→036 | #23→#35 | Full cover. US-030 reactivation = #28. #30 `/tenants/{id}/invoices` inferred alias |
| Nhóm 4 — Lease | US-037→056 | #36→#43 | Full cover. US-055 terminate = #40, US-056 settle = #41 |
| Nhóm 5 — Service | US-057→063 | #44→#50 | Full cover |
| Nhóm 6 — Meter Reading | US-064→072 | #51→#55 | Full cover. US-071/072 = PATCH/DELETE per reading |
| Nhóm 7 — Invoice | US-073→089 | #56→#63 | Full cover. US-076 preview = #56+#58, US-082 void = #63.  |
| Nhóm 8 — Payment | US-090→095 | #64→#68 | Full cover |

**Gaps intentional** (không tạo endpoint):
- US-005/006 (RBAC check) = middleware concern
- US-086 (prompt invoice cuối khi terminate) = response field `pending_final_invoice` trong #40
- US-088/089 (invoice delivery) = in-app (#70-72) + Landlord manual Zalo (không có API)
- Cron triggers (US-043 lease status, US-049 expiring reminder) = APScheduler không expose endpoint

---

## 15. Special Endpoint Notes

### Endpoint quan trọng cần implement cẩn thận Phase 4

| # | Endpoint | Complexity | Risk |
|---|---|---|---|
| #51 | Batch meter-readings | High | All-or-nothing transaction, warning vs error logic |
| #56+57 | Invoice preview + commit batch | High | Stateless compute, pro-rata, shared meter logic |
| #35 | Promote occupant | High | Atomic multi-table, circular FK |
| #40 | Terminate lease | Medium | Side effects: prompt invoice, deposit |
| #63 | Void invoice | Medium | Invoice immutability enforcement |
| #69 | Delete payment | Medium | Recompute invoice status |
| #6 | Invite accept | Medium | Multi-step: activate + login + PII consent |

### Performance-sensitive endpoints

| Endpoint | Concern | Mitigation |
|---|---|---|
| `GET /invoices` | Join chain lease→room→property | Index `landlord_id` (denormalized) |
| `GET /notifications` | Unread count per request | Add to envelope, share query |
| `POST /properties/{pid}/invoices/preview` | N leases × M services compute | In-memory, không persist |
| `GET /meter-readings` | Lookup previous reading per service/room | Index `(service_id, room_id, reading_date DESC)` |

---

## 16. Endpoint Count Summary

| Category | Count |
|---|---|
| Auth (public) | 8 |
| Users | 3 |
| Properties | 5 |
| Rooms | 6 |
| Tenants | 8 |
| Occupants | 5 |
| Leases | 8 |
| Services | 7 |
| Meter Readings | 5 |
| Invoices | 9 |
| Payments | 4 |
| Notifications | 3 |
| **Total** | **71** |

---

**End of S4.2 Endpoint Mapping. Ready for S4.3 (special flows detail) or S4.4 (OpenAPI YAML).**
