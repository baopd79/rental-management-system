# Phase 3 Progress — Context Seed cho Chat Mới

> **Purpose**: Cô đọng Phase 3 progress đến hiện tại để paste vào chat mới
> mà không cần đọc lại toàn bộ chat Phase 3 gốc.
>
> **Usage**: Mở chat mới → paste file này + PHASE2-SUMMARY.md + prompt
> "Tôi đang tiếp tục Phase 3 từ đây. Đây là progress summary" → Claude sẽ
> có full context.
>
> **Started**: 2026-04-18
> **Last updated**: 2026-04-20 (chat Phase 3 part 1 kết thúc)
> **Authors**: Bảo (domain expert) + Claude (Senior Architect + Mentor)

---

## 1. Phase 3 Deliverables Checklist

| # | Deliverable | Status | Files |
|---|-------------|--------|-------|
| 1 | ADRs (6 cái) | ✅ Done | `docs/decisions/ADR-0001.md` → `ADR-0006.md` |
| 2 | Architecture Diagram | ✅ Done | `docs/02-architecture/architecture-diagram.svg` |
| 3 | ERD | ✅ Done (post-review) | `docs/03-database/erd.mmd` + `erd.dbml` + `erd-reference.md` |
| 4 | SQLModel models (17 tables) | ✅ Done | `app/models/*.py` (13 files) |
| 5 | Alembic migration | ⏳ Next chat | — |
| 6 | Dev env (Docker Compose) | ⏳ Next chat | — |
| 7 | API Spec (OpenAPI 3.0) | ⏳ Chat sau nữa | — |
| 8 | Frontend decision + wireframes | ⏳ Chat sau nữa | — |
| 9 | CI/CD pipeline plan | ⏳ Cuối phase | — |

---

## 2. ADRs — Decisions Summary

| ADR | Title | Key decision |
|-----|-------|--------------|
| 0001 | Lifecycle field naming | 3 patterns: `is_archived`+`archived_at` (soft delete), `is_active` (toggle), `<event>_at` (event timestamp). Rule 4: API không expose lifecycle fields |
| 0002 | Cron architecture | APScheduler in-process, 4 daily tasks, idempotent, UTC+7 timezone |
| 0003 | Audit log | Application-level table, JSONB partial snapshots, same transaction với main op, scope critical entities |
| 0004 | Notification framework | Event-driven handler pattern. MVP in-app only, v1.x add email/Zalo |
| 0005 | RBAC strategy | Permission-based, in-code permissions, 2-layer check (permission middleware + ownership service layer), 404 không 403 cho ownership |
| 0006 | Data retention | PII Tenant 5 năm anonymize, Invoice/Payment/Audit 10 năm, consent tracking |

---

## 3. Architecture Overview

```
Web Client ──HTTPS──> FastAPI (Docker container)
                         │
                         ├── Auth middleware (JWT + RBAC, ADR-0005)
                         ├── Service layer (business logic + ownership)
                         ├── APScheduler (ADR-0002, in-process cron)
                         ├── Notification service (ADR-0004, in-app MVP)
                         └── Repository (SQLModel queries)
                                 │
                                 ↓ SQL
                         PostgreSQL 16 (Docker container)
                         ├── users, tokens (Nhóm 1)
                         ├── properties, rooms (Nhóm 2)
                         ├── tenants, occupants (Nhóm 3)
                         ├── leases (Nhóm 4)
                         ├── services, service_rooms (Nhóm 5)
                         ├── meter_readings (Nhóm 6)
                         ├── invoices, invoice_line_items (Nhóm 7)
                         ├── payments (Nhóm 8)
                         └── audit_logs, notifications (Nhóm 9)
```

**Zalo**: manual (Landlord copy link), v1.x mới integration qua Zalo OA.

---

## 4. ERD — 17 Tables

**Key patterns trong ERD:**

1. **6 partial unique indexes** — unique chỉ trong subset rows (ví dụ `tenants.phone` unique per landlord WHERE NOT archived)
2. **Snapshot pattern** — `leases.rent_amount`, `leases.billing_day`, `invoice_line_items.*` đều snapshot khi tạo, immutable sau đó
3. **Computed status** không lưu DB — Room, Lease, Tenant, Invoice status compute từ related fields
4. **Denormalization có chọn lọc** — chỉ `invoices.landlord_id` và `audit_logs.landlord_id`
5. **JSONB** cho audit_logs `before`/`after`

**Post-review fixes áp dụng** (cross-check với US gốc Phase 2):
- Thêm 10 missing fields vào 5 bảng
- Đổi `invoices.voided_reason` từ `text` sang enum 6 giá trị
- Override 2 Phase 2 decisions:
  - US-036 Promote Occupant: keep record với `promoted_from_occupant_id` trace (không hard delete)
  - US-030 Reactivation: support cả flow A (unarchive) và B (create new)

---

## 5. SQLModel Models Structure

**Project layout:**
```
app/
├── core/
│   └── enums.py              # 8 Python Enum classes
├── db/
│   └── base.py               # UUIDPrimaryKeyMixin, TimestampMixin, CreatedAtOnlyMixin
└── models/
    ├── user.py               # Nhóm 1
    ├── token.py              # Nhóm 1 (3 token tables)
    ├── property.py           # Nhóm 2
    ├── room.py               # Nhóm 2
    ├── tenant.py             # Nhóm 3
    ├── occupant.py           # Nhóm 3
    ├── lease.py              # Nhóm 4
    ├── service.py            # Nhóm 5
    ├── service_room.py       # Nhóm 5 (junction)
    ├── meter_reading.py      # Nhóm 6
    ├── invoice.py            # Nhóm 7 (Invoice + LineItem)
    ├── payment.py            # Nhóm 8
    ├── audit_log.py          # Nhóm 9
    └── notification.py       # Nhóm 9
```

**Pattern chuẩn áp dụng xuyên suốt:**

Mỗi entity có 4-5 schema variants:
```
XxxBase       — Shared fields (không table=True)
Xxx           — Table class (table=True, + FK + lifecycle + mixins)
XxxCreate     — Input POST (kế thừa Base)
XxxRead       — Output GET (kế thừa Base, + id, timestamps, domain dates)
XxxUpdate     — Input PATCH (kế thừa SQLModel thuần, tất cả optional)
```

**Ngoại lệ cho Action schemas:**
- `LeaseTerminate`, `LeaseSettleDeposit` (Nhóm 4) — cho action riêng
- `InvoiceVoid`, `InvoiceAdjustmentAdd` (Nhóm 7) — cho action riêng

**Không có Update schema cho:**
- Token models (append-only)
- Invoice + InvoiceLineItem (immutability tuyệt đối)
- Payment (hard delete + recreate thay vì edit)
- AuditLog, Notification (append-only)

**Rule 4 ADR-0001 enforced**: tất cả `XxxRead` KHÔNG expose `is_archived`, `archived_at`, `is_active`, `revoked_at`.

---

## 6. Dev Learning Progress (Bảo)

**Đã học:**
- Python type hints + `| None` pattern
- Pydantic: BaseModel, Field() constraints, EmailStr
- ORM concept: Session, Engine, FK, Migration, N+1 problem
- SQLModel = SQLAlchemy + Pydantic, `table=True` keyword
- Pattern 4-schema (Base/Table/Create/Read/Update)
- Mixin pattern (UUIDPrimaryKeyMixin, TimestampMixin)

**Đã tự viết 2 models:**
- `tenant.py` — lần 1 sai 7 điểm, lần 2 sai 2 điểm, lần 3 clean
- `occupant.py` — lần 1 sai 11 điểm, lần 2 sai 2 điểm

**Learning pattern:**
- Bảo improve rõ rệt giữa 2 models
- Gotcha phát hiện: `default` vs `default_factory`, đồng bộ type giữa Base và Update, import ambiguity (DateTime)

**Còn lại trong Phase 3 cần học:**
- Relationship() trong SQLModel (chưa dùng — dự kiến Phase 4)
- Alembic migration workflow (chat tiếp theo)
- Async session với SQLModel

---

## 7. Open Questions / Debt

**Technical debts hiện có:**

1. **`updated_at` auto-update**: Chưa implement trigger/listener. Phase 4 quyết:
   SQLAlchemy event listener vs PostgreSQL trigger.

2. **Partial unique indexes**: SQLModel autogenerate KHÔNG detect được.
   Phải viết manual trong Alembic migration. Ví dụ:
   - `rooms.display_name` unique per property WHERE NOT archived
   - `tenants.phone` unique per landlord WHERE active
   - `invoices.invoice_number` unique per landlord WHERE NOT voided

3. **PostgreSQL enum types**: Autogenerate có bug với enum, thường phải edit
   manual migration.

4. **Complex CHECK constraints**: SQLAlchemy không autogenerate constraint
   dạng `CHECK (a OR b AND c)`. Phải manual edit.

5. **`service_rooms` junction PK**: Composite PK có thể cần tweak sau khi
   autogenerate.

**Product decisions defer Phase 4:**
- Refresh token rotation logic (schema ready với `rotated_to_id`)
- Anonymize cron task (ADR-0006 đã define pattern)
- Invoice number generation với sequence/lock
- Audit log helper pattern (AuditLogger class trong service layer)

---

## 8. Chat Organization

**Chat 1 (đã xong)** — "Phase 3: Foundation":
- 6 ADRs + Architecture + ERD + 17 SQLModel models
- Mentoring mode (Python/Pydantic/ORM/SQLModel patterns)

**Chat 2 (tiếp theo)** — "Phase 3: Schema Implementation":
- Alembic setup + `001_initial_schema.py` migration
- Manual fixes cho partial indexes + CHECK constraints + enums
- Dev environment (Docker Compose)
- Test migration upgrade/downgrade

**Chat 3 (sau)** — "Phase 3: API & Frontend":
- OpenAPI 3.0 spec cho tất cả endpoints
- Frontend stack decision
- Wireframes (paper/Figma)

**Chat 4 (cuối Phase 3)** — "Phase 3: DevOps":
- CI/CD pipeline plan
- PHASE3-SUMMARY.md (context seed cho Phase 4)

---

## 9. Reference Files (đính kèm chat mới)

Paste cùng với file này khi mở chat mới:

**Bắt buộc:**
- `PHASE2-SUMMARY.md` — context seed Phase 2
- `PHASE3-PROGRESS.md` — file này

**Optional (khi cần verify):**
- `docs/03-database/erd.mmd` — source ERD (full fields)
- `docs/03-database/erd-reference.md` — constraints + indexes
- `docs/decisions/ADR-*.md` — 6 ADRs (chỉ paste khi discussion liên quan)

**Không cần paste:**
- `app/models/*.py` — Claude có thể re-generate hoặc đọc khi cần

---

## 10. Next Chat Opening Prompt (template)

```
Chào! Tôi tiếp tục Phase 3 của dự án RMS.

Đính kèm:
- PHASE2-SUMMARY.md (requirements summary)
- PHASE3-PROGRESS.md (progress đến giờ)

Tôi muốn tiếp tục với [Alembic migration / API spec / ...].

Lưu ý working style:
- Đóng vai Senior Architect + Mentor (không chỉ viết code)
- Giải thích pattern trước, cho tôi review hoặc tự viết, rồi review code tôi
- Mỗi edge case discuss trước khi decide
- Tôi đang học backend, cần hiểu sâu hơn là code nhanh
```

---

**End of PHASE3-PROGRESS.md. Ready for chat 2.**
