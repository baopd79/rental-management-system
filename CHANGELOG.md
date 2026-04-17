# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### In Progress — Phase 2: Requirements

- Nhóm 4 (Lease): chưa bắt đầu
- Nhóm 5 (Service): chưa bắt đầu
- Nhóm 6 (Meter Reading): chưa bắt đầu
- Nhóm 7 (Invoice): chưa bắt đầu
- Nhóm 8 (Payment): chưa bắt đầu

## [0.2.0] – 2026-04-17 — Phase 2: Requirements (Nhóm 1-3) DRAFT

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

### Decisions

- Tenant và User tách 2 entity (Tenant = domain, User = auth)
- Room status là computed field (không lưu DB) — Single Source of Truth
- Lease status chuyển bằng cron job daily (active → expired)
- Unique phone/email theo scope (landlord_id, phone) WHERE is_archived=false
- Billing per_person dùng snapshot cuối tháng (MVP), pro-rata (v1.x)

### Total

- 26 user stories / ~55 dự kiến cho toàn MVP
- 3/8 nhóm hoàn thành draft

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
