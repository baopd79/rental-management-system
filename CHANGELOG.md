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

## [0.0.1] – 2026-04-16

- Project kickoff
- Initial docs skeleton (Phase 0 – Bootstrap)
- README with documentation map
- ADR template
