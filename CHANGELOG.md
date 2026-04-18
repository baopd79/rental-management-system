# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### In Progress — Phase 2: Requirements

- Nhóm 6 (Meter Reading): chưa bắt đầu
- Nhóm 7 (Invoice): chưa bắt đầu
- Nhóm 8 (Payment): chưa bắt đầu

## [0.4.1] – 2026-04-18 — Phase 2 Gate Review (Mid-phase)

### Added

- **Phase 2 Review** (`docs/01-requirements/PHASE2-REVIEW.md`)
  - Full cross-reference review of Nhóm 1-5
  - Identified 2 Critical issues (C1, C2), 5 Should-fix (S1-S5),
    3 Observations (N1-N3), 4 Strengths
- **Phase 2 Review Patches** (`docs/01-requirements/PHASE2-REVIEW-PATCHES.md`)
  - Detailed before/after patches for Claude Code execution

### Fixed (from review)

- **C1**: Unified Room.status derivation — now maps 1-1 from Lease.status
  instead of computing from end_date independently
  - `02-property-room.md` US-017 AC2, AC5
- **C2**: Handled Tenant reactivation in invite flow — reuse forgot password
  flow instead of creating duplicate User account
  - `01-auth-rbac.md` US-004 AC8, US-005 AC6
- **S2**: Consolidated cron jobs into single "Daily Status Maintenance Cron"
  - `04-lease.md` US-057 AC1, architecture section
  - `03-tenant.md` US-036b added
- **S3**: Documented multi-role user as Open Question
  - `01-auth-rbac.md` Open Questions #6, #7
- **S4**: Clarified US-002 covers both Landlord and Tenant login
  - `01-auth-rbac.md` US-002 Notes

### Updated

- `glossary.md`: Added Occupant, billing_type, Service scope,
  full status enums for Room/Lease/Tenant/Invoice/Deposit

## [0.3.0] – 2026-04-17 — Phase 2: Requirements (Nhóm 1-4) DRAFT

### Added

- **Nhóm 1: Auth & RBAC** (`docs/01-requirements/01-auth-rbac.md`)
  - 8 user stories (US-001 → US-009, bỏ US-006)
  - Landlord self-signup với email + password
  - Tenant invite-based flow (không self-signup)
  - Invite token: single-use, TTL 7 ngày, stateful (DB)
  - Forgot password qua email
  - JWT access + refresh token
  - RBAC 2 role (Landlord, Tenant), mở rộng được

- **Nhóm 2: Property & Room** (`docs/01-requirements/02-property-room.md`)
  - 9 user stories (US-010 → US-018)
  - Property: hard delete khi hết Room
  - Room: soft delete (archive), computed status
  - Room status 4 trạng thái: vacant / occupied / expiring_soon / lease_expired
  - Room.display_name free text + floor optional
  - Tenant view-only thông tin phòng mình thuê

- **Nhóm 3: Tenant & Occupant** (`docs/01-requirements/03-tenant.md`)
  - 9 user stories (US-030 → US-038)
  - Tenant = người ký hợp đồng (có account), Occupant = người ở cùng (không account)
  - Soft delete Tenant khi dọn đi, hard delete Occupant cho case nhập nhầm
  - Occupant có moved_in_date / moved_out_date (hỗ trợ billing pro-rata v1.x)
  - Auto-suggest khi nhập phone trùng Tenant archived
  - US-036 Promote Occupant → Tenant (đổi người đại diện)
  - Data Retention Policy draft (theo Nghị định 13/2023/NĐ-CP)

- **Nhóm 4: Lease** (`docs/01-requirements/04-lease.md`)
  - 10 user stories (US-050 → US-059)
  - Strict single-active: 1 Room chỉ có 1 Lease active
  - 5 status: draft / active / expiring_soon / expired / terminated
  - Status computed (trừ terminated lưu terminated_at)
  - Pro-rata universal: rent = rent_amount × days_occupied / days_in_month
  - Deposit 4 status: held / returned / forfeited / deducted
  - Renewal = tạo Lease mới với renewed_from_lease_id link
  - Rollover deposit: dùng returned + amount=0 + note (không thêm status mới)
  - Grace period expired: vẫn tính Invoice theo rent cũ

### Decisions

- Landlord dùng start_date/terminated_date làm công cụ chính sách
  (không có field billing_mode riêng)
- Lease active gần immutable: chỉ sửa note + end_date
- Deposit là trạng thái của Lease, không phải giao dịch (không tạo Payment)
- Terminate và settle deposit tách 2 step riêng (cho flow thực tế linh hoạt)
- Auto-archive Tenant khi settle deposit xong (cầu nối Lease ↔ Tenant lifecycle)

## [0.4.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 5) DRAFT

### Added

- **Nhóm 5: Service** (`docs/01-requirements/05-service.md`)
  - 7 user stories (US-060 → US-066)
  - 3 billing types: per_meter / per_person / fixed
  - Service scope: all_rooms (default) / selected_rooms (cho công tơ chung)
  - Shared per_meter chia theo số người các phòng trong scope
  - Toggle is_active thay cho hard/soft delete
  - Unit auto theo billing_type (chỉ per_meter mới nhập)

### Decisions

- Service là template, không phải entity sống
- Invoice Immutability Pattern: Invoice snapshot giá tại thời điểm tạo,
  Service đổi sau không ảnh hưởng Invoice cũ
- Service config ở Property-level (không có Room-level)
- Không per-Lease override ở MVP
- Không đổi giá giữa kỳ (áp dụng từ tháng sau)
- Phòng trống trong shared meter không chịu phí

## [0.5.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 6) DRAFT

### Added

- **Nhóm 6: Meter Reading** (`docs/01-requirements/06-meter-reading.md`)
  - 6 user stories (US-070 → US-075)
  - Point-in-time schema: 1 record = 1 reading
  - Batch nhập reading per Property (Pattern Y.2)
  - Reading mutable khi Invoice reference chưa có Payment
  - Reminder ngày 5 hàng tháng nếu chưa xuất Invoice
  - room_id nullable (null = shared meter, có value = per-room)

### Decisions

- Reading là domain event, append-only bản chất
- Manual Invoice trigger (không cron auto-generate)
- Task-oriented UI: batch form theo workflow, không per-entity
- Validate `reading_value >= previous_value`, warn không block
- Auto-fill previous reading từ reading trước
- Shared meter applied_rooms fix ở Service, không chọn lại khi nhập

## [0.6.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 7) DRAFT

### Added

- **Nhóm 7: Invoice** (`docs/01-requirements/07-invoice.md`)
  - 9 user stories (US-080 → US-088)
  - Status lifecycle: unpaid → partial → paid + void
  - Preview + commit pattern (batch per Property)
  - Individual mode cho edge cases
  - Invoice Immutability tuyệt đối sau khi tạo
  - Void thay cho delete, void tạo Invoice mới replacement
  - Adjustment line manual trong Invoice tháng sau

### Decisions

- Billing month chung cho Invoice, period_month riêng per line item
- Service đổi giá không affect Invoice đã tạo (mọi status)
- Sửa reading không auto-update Invoice (Landlord tự void + recreate)
- Per_person snapshot tại thời điểm tạo Invoice
- Terminate Lease auto-prompt Invoice cuối pro-rata
- Line items flatten với description gộp chỉ số

### Format note

- Applied Option C Hybrid: Must stories chi tiết, Should stories gọn

## [0.7.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 8) DRAFT + COMPLETE

### Added

- **Nhóm 8: Payment** (`docs/01-requirements/08-payment.md`)
  - 5 user stories (US-090 → US-094)
  - Payment là record-only (Landlord ghi nhận hậu kiểm)
  - Invoice.status auto-compute từ Payments
  - Unlimited số Payment per Invoice
  - Hard delete với trigger recompute

### Decisions

- Không có type enum cho Payment (trạng thái đã ở Invoice.status)
- Validation strict: không overpay, không future date
- Tenant thấy full Payment history (transparency)

### Phase 2 COMPLETE 🎉

- **Total: 63 user stories** (US-001 → US-094)
- **8/8 nhóm** hoàn thành draft
- **Estimate tổng**: ~15 sprint

### Next steps

- PHASE2-SUMMARY.md (context seed cho Phase 3)
- Phase 3: Architecture + Database Design

## [0.1.0] – 2026-04-17 — Phase 1: Vision & Scope APPROVED

### Added

- Vision & Scope document (approved by Bảo)
  - Problem statement with real workflow pain points
  - Vision statement: "Từ đọc số điện đến người thuê nhận hoá đơn — trong vài click"
  - 5 personas (2 MVP, 3 post-MVP)
  - MVP scope: 11 features, 2 roles (Landlord + Tenant)
  - Versioned roadmap: MVP → v1.x → v2.x → NEVER
  - Success metrics, constraints, risks
- Glossary with entities, roles, and statuses (Vietnamese ↔ English)
- Invoice flow defined: Landlord tạo → Tenant xem trên app → nhắc qua Zalo

### Decisions

- MVP roles = 2 (Landlord + Tenant), thiết kế mở để mở rộng
- Persona D (cho thuê nguyên căn) → v2.x, implement qua property type
- Notification → v1.x, MVP dùng Zalo để nhắc
## [Unreleased]

### Added — Phase 3: Architecture & Database Design (2026-04-18)

**Architecture Decision Records:**

- `docs/decisions/ADR-0001-lifecycle-field-naming.md` (v2 post-review)
  3 pattern rõ ràng cho lifecycle fields: soft delete (`is_archived` +
  `archived_at`), feature toggle (`is_active`), domain event timestamp
  (`terminated_at`, `voided_at`, `revoked_at`). Options considered với
  lý do reject Option 1 và Option 3. 6 rules cho dev bao gồm no-mix
  pattern, no `deleted_at`, API không expose lifecycle fields, partial
  index migration convention.

- `docs/decisions/ADR-0002-cron-architecture.md`
  APScheduler in-process (không cần Redis/Celery ở MVP). 4 tasks:
  `check_lease_status` (00:05), `send_invoice_reminder` (ngày 5 08:00),
  `cleanup_expired_tokens` (02:00), `anonymize_old_tenants` (03:00).
  Timezone Asia/Ho_Chi_Minh. Idempotency requirement.

- `docs/decisions/ADR-0003-audit-log.md`
  Application-level audit table trong same DB. Scope: critical entities
  (lease, invoice, payment, room, tenant, service, user). Pattern:
  `before`/`after` JSONB partial snapshot. Ghi trong cùng transaction
  với main operation. Retention 10 năm.

- `docs/decisions/ADR-0004-notification-framework.md`
  Event-driven với handler pattern. MVP: InAppHandler (DB-backed).
  v1.x: thêm EmailHandler, ZaloOAHandler mà không sửa business logic.
  5 event keys. Retention 90 ngày.

- `docs/decisions/ADR-0005-rbac-strategy.md`
  Permission-based RBAC. Permission string dạng `resource:action`.
  Permissions lưu in-code (không lưu DB). Tách 2 tầng: permission check
  (middleware) + ownership check (service layer). MVP: 1 user = 1 role.
  404 thay vì 403 cho ownership violation.

- `docs/decisions/ADR-0006-data-retention.md`
  PII Tenant: giữ full khi active, anonymize sau 5 năm khi archived.
  Invoice/Payment/Audit log: giữ 10 năm (luật kế toán VN). Tokens:
  xóa sau TTL. Consent timestamp `users.consent_at`. Cần review pháp
  lý trước production.

**Architecture Diagram:**

- `docs/02-architecture/architecture-diagram.svg`
  Three-tier: Web Client → FastAPI backend → PostgreSQL, tất cả wrapped
  trong Docker Compose. FastAPI có 5 internal layer: Auth middleware,
  Service layer, APScheduler, Notification service, Repository.

**Entity Relationship Diagram:**

- `docs/03-database/erd.mmd` (Mermaid source, v2 post-review)
- `docs/03-database/erd-reference.md` (companion doc)

  17 bảng: `users`, `invite_tokens`, `password_reset_tokens`,
  `refresh_tokens`, `properties`, `rooms`, `tenants`, `occupants`,
  `leases`, `services`, `service_rooms`, `meter_readings`, `invoices`,
  `invoice_line_items`, `payments`, `audit_logs`, `notifications`.

  Đặc trưng:
  - 6 partial unique indexes (unique scope WHERE active)
  - Snapshot pattern cho immutability: `leases.rent_amount`,
    `leases.billing_day`, `invoice_line_items.*`
  - Computed status (không lưu DB) cho Room, Lease, Tenant, Invoice
  - Denormalization chọn lọc: `landlord_id` trên `invoices` và
    `audit_logs`
  - JSONB cho audit log payload

### Changed — Post-review fixes (2026-04-18)

Cross-check ERD v1 với user stories gốc Phase 2 (file `03-tenant.md`
và `07-invoice.md`) tìm ra 9 vấn đề, đã fix:

**Missing fields added:**
- `users`: `full_name`, `phone` (Landlord profile, nullable)
- `tenants`: `hometown`, `note`, `move_out_date`
- `occupants`: `moved_in_date`, `moved_out_date`, `note`
- `rooms`: `max_occupants`
- `invoices`: `void_note`, `voided_by_user_id`, `created_by_user_id`
- `invoice_line_items`: `unit`

**Field type changed:**
- `invoices.voided_reason`: `text` → `enum` với 6 giá trị
  (`wrong_meter_reading`, `wrong_rent`, `wrong_service_config`,
  `tenant_dispute`, `duplicate`, `other`)

**Field renamed** (match Phase 2 US naming):
- `tenants.id_number` → `tenants.id_card_number`
- `tenants.date_of_birth` → `tenants.birth_date`
- `occupants.id_number` → `occupants.id_card_number`
- `occupants.date_of_birth` → `occupants.birth_date`

**Phase 2 overrides** (documented trong `erd-reference.md` §10):
- US-036 Promote Occupant: giữ Phase 3 decision (Cách 2 — keep với
  trace), update US-036 để mark thay vì delete
- US-030 Reactivation: relax Phase 3 decision, support cả flow A
  (unarchive Tenant cũ) và flow B (create new) như US yêu cầu

---

### Added — Phase 3: Architecture & Database Design (2026-04-18)

**Architecture Decision Records:**

- `docs/decisions/ADR-0001-lifecycle-field-naming.md` (v2 post-review)
  3 pattern rõ ràng cho lifecycle fields: soft delete (`is_archived` +
  `archived_at`), feature toggle (`is_active`), domain event timestamp
  (`terminated_at`, `voided_at`, `revoked_at`). Options considered với
  lý do reject Option 1 và Option 3. 6 rules cho dev bao gồm no-mix
  pattern, no `deleted_at`, API không expose lifecycle fields, partial
  index migration convention.

- `docs/decisions/ADR-0002-cron-architecture.md`
  APScheduler in-process (không cần Redis/Celery ở MVP). 4 tasks:
  `check_lease_status` (00:05), `send_invoice_reminder` (ngày 5 08:00),
  `cleanup_expired_tokens` (02:00), `anonymize_old_tenants` (03:00).
  Timezone Asia/Ho_Chi_Minh. Idempotency requirement.

- `docs/decisions/ADR-0003-audit-log.md`
  Application-level audit table trong same DB. Scope: critical entities
  (lease, invoice, payment, room, tenant, service, user). Pattern:
  `before`/`after` JSONB partial snapshot. Ghi trong cùng transaction
  với main operation. Retention 10 năm.

- `docs/decisions/ADR-0004-notification-framework.md`
  Event-driven với handler pattern. MVP: InAppHandler (DB-backed).
  v1.x: thêm EmailHandler, ZaloOAHandler mà không sửa business logic.
  5 event keys. Retention 90 ngày.

- `docs/decisions/ADR-0005-rbac-strategy.md`
  Permission-based RBAC. Permission string dạng `resource:action`.
  Permissions lưu in-code (không lưu DB). Tách 2 tầng: permission check
  (middleware) + ownership check (service layer). MVP: 1 user = 1 role.
  404 thay vì 403 cho ownership violation.

- `docs/decisions/ADR-0006-data-retention.md`
  PII Tenant: giữ full khi active, anonymize sau 5 năm khi archived.
  Invoice/Payment/Audit log: giữ 10 năm (luật kế toán VN). Tokens:
  xóa sau TTL. Consent timestamp `users.consent_at`. Cần review pháp
  lý trước production.

**Architecture Diagram:**

- `docs/02-architecture/architecture-diagram.svg`
  Three-tier: Web Client → FastAPI backend → PostgreSQL, tất cả wrapped
  trong Docker Compose. FastAPI có 5 internal layer: Auth middleware,
  Service layer, APScheduler, Notification service, Repository.

**Entity Relationship Diagram:**

- `docs/03-database/erd.mmd` (Mermaid source, v2 post-review)
- `docs/03-database/erd-reference.md` (companion doc)

  17 bảng: `users`, `invite_tokens`, `password_reset_tokens`,
  `refresh_tokens`, `properties`, `rooms`, `tenants`, `occupants`,
  `leases`, `services`, `service_rooms`, `meter_readings`, `invoices`,
  `invoice_line_items`, `payments`, `audit_logs`, `notifications`.

  Đặc trưng:
  - 6 partial unique indexes (unique scope WHERE active)
  - Snapshot pattern cho immutability: `leases.rent_amount`,
    `leases.billing_day`, `invoice_line_items.*`
  - Computed status (không lưu DB) cho Room, Lease, Tenant, Invoice
  - Denormalization chọn lọc: `landlord_id` trên `invoices` và
    `audit_logs`
  - JSONB cho audit log payload

### Changed — Post-review fixes (2026-04-18)

Cross-check ERD v1 với user stories gốc Phase 2 (file `03-tenant.md`
và `07-invoice.md`) tìm ra 9 vấn đề, đã fix:

**Missing fields added:**
- `users`: `full_name`, `phone` (Landlord profile, nullable)
- `tenants`: `hometown`, `note`, `move_out_date`
- `occupants`: `moved_in_date`, `moved_out_date`, `note`
- `rooms`: `max_occupants`
- `invoices`: `void_note`, `voided_by_user_id`, `created_by_user_id`
- `invoice_line_items`: `unit`

**Field type changed:**
- `invoices.voided_reason`: `text` → `enum` với 6 giá trị
  (`wrong_meter_reading`, `wrong_rent`, `wrong_service_config`,
  `tenant_dispute`, `duplicate`, `other`)

**Field renamed** (match Phase 2 US naming):
- `tenants.id_number` → `tenants.id_card_number`
- `tenants.date_of_birth` → `tenants.birth_date`
- `occupants.id_number` → `occupants.id_card_number`
- `occupants.date_of_birth` → `occupants.birth_date`

**Phase 2 overrides** (documented trong `erd-reference.md` §10):
- US-036 Promote Occupant: giữ Phase 3 decision (Cách 2 — keep với
  trace), update US-036 để mark thay vì delete
- US-030 Reactivation: relax Phase 3 decision, support cả flow A
  (unarchive Tenant cũ) và flow B (create new) như US yêu cầu

---

## [Unreleased — Phase 2: Requirements] (2026-04-18)

### Added
- 8 requirement groups hoàn chỉnh (63 user stories: 42 Must + 17 Should + 4 Could)
- `docs/01-requirements/01-auth-rbac.md`
- `docs/01-requirements/02-property-room.md`
- `docs/01-requirements/03-tenant.md`
- `docs/01-requirements/04-lease.md`
- `docs/01-requirements/05-service.md`
- `docs/01-requirements/06-meter-reading.md`
- `docs/01-requirements/07-invoice.md`
- `docs/01-requirements/08-payment.md`
- `docs/01-requirements/PHASE2-REVIEW.md` — Gate Review
- `docs/01-requirements/PHASE2-REVIEW-PATCHES.md` — Applied patches
- `docs/00-overview/glossary.md` — Glossary đầy đủ
- `PHASE2-SUMMARY.md` — Context seed cho Phase 3

---

## [0.0.1] – 2026-04-16

- Project kickoff
- Initial docs skeleton (Phase 0 – Bootstrap)
- README with documentation map
- ADR template
