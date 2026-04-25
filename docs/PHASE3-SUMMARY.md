# Phase 3 Complete — Context Seed cho Phase 4

> **Purpose**: Cô đọng tất cả decisions của Phase 3 (Architecture +
> Database + API + Frontend + CI/CD) để paste vào chat Phase 4.
>
> **Usage**: Mở chat Phase 4 → paste file này + PHASE2-SUMMARY.md →
> Claude có full context start implementation.
>
> **Authors**: Bảo + Claude (as Senior Architect + Mentor)
> **Completed**: 2026-04-25
> **Total Phase 3 duration**: ~1 tuần (5 chats)

---

## 1. Phase 3 Deliverables — All Complete ✅

| # | Deliverable | Output |
|---|---|---|
| 1 | 7 ADRs (0001-0007) | `docs/decisions/ADR-0001-*.md` |
| 2 | Architecture Diagram | `docs/02-architecture/architecture-diagram.svg` |
| 3 | ERD | `docs/03-database/erd.mmd` + `erd-reference.md` |
| 4 | SQLModel models (17 tables) | `app/models/*.py` |
| 5 | Dev env (Docker + uv) | `docker-compose.yml`, `.env.example`, `pyproject.toml` |
| 6 | Alembic config | `alembic/env.py`, `alembic.ini` |
| 7 | Migration 001_initial_schema | `alembic/versions/<hash>_initial_schema.py` |
| 8 | API Spec (OpenAPI) | `docs/04-api/openapi.yaml` + `endpoints.md` + `api-design-decisions.md` |
| 9 | Frontend Stack + Wireframes | `docs/decisions/ADR-0008-*.md` + `docs/02-architecture/wireframes/` + `PHASE3-FRONTEND-NOTES.md` |
| 10 | CI/CD Pipeline | `docs/decisions/ADR-0009-*.md` + `.github/workflows/*.yml` + `docs/07-deployment/*.md` |

---

## 2. Full Tech Stack (final)

### Backend

| Layer | Tech | Decided in |
|---|---|---|
| Language | Python 3.12 | Phase 2 |
| Package manager | uv | Phase 3 Chat 2 |
| Framework | FastAPI | Phase 2 |
| ORM | SQLModel (sync) | Phase 3 Chat 2 |
| DB driver | psycopg[binary] v3 | Phase 3 Chat 2 |
| Migration | Alembic (sync template) | Phase 3 Chat 3 |
| Database | PostgreSQL 16 | Phase 2 |
| Auth libs | python-jose + passlib[bcrypt] | ADR-0007 |
| Scheduler | APScheduler | ADR-0002 |
| Email | Resend + EmailService abstraction | Phase 2 |
| Rate limit | slowapi (in-memory) | Phase 2 |
| Logging | structlog | ADR-0009 |
| Testing | pytest + pytest-cov | Phase 3 |
| Lint/type | ruff + mypy | Phase 3 |

### Frontend (Phase 4 will implement)

| Layer | Tech | Decided in |
|---|---|---|
| Package manager | pnpm 10 | ADR-0008 |
| Language | TypeScript 5.7 strict | ADR-0008 |
| Build tool | Vite 6 | ADR-0008 |
| Framework | React 19 | ADR-0008 |
| Routing | React Router 7 (library mode) | ADR-0008 |
| Server state | TanStack Query 5 | ADR-0008 |
| Client state | Zustand 5 | ADR-0008 |
| Styling | Tailwind CSS 4 | ADR-0008 |
| UI components | shadcn/ui + Radix | ADR-0008 |
| Forms | React Hook Form + Zod | ADR-0008 |
| HTTP client | ky | ADR-0008 |
| API codegen | openapi-typescript + openapi-fetch | ADR-0008 |
| Testing | Vitest + RTL + MSW | ADR-0008 |
| Lint/format | ESLint 9 flat + Prettier 3 | ADR-0008 |

### Infrastructure

| Layer | Tech | Decided in |
|---|---|---|
| Deployment target | VPS (Hetzner/Vultr) | ADR-0009 |
| Container | Docker Compose | ADR-0009 |
| Reverse proxy | Nginx + Let's Encrypt | ADR-0009 |
| CI/CD | GitHub Actions | ADR-0009 |
| Container registry | GitHub Container Registry (ghcr.io) | ADR-0009 |
| Environments | staging + production (2 envs) | ADR-0009 |
| Secrets | GitHub Secrets + VPS .env | ADR-0009 |
| Backup | pg_dump daily → Cloudflare R2 (10GB free) | ADR-0009 |
| Monitoring | UptimeRobot free + structured logs | ADR-0009 |

---

## 3. All 9 ADRs at a Glance

| # | ADR | Key Rule |
|---|---|---|
| 0001 | Lifecycle field naming | Soft delete: `is_archived`+`archived_at`. Toggle: `is_active`. Event: `<event>_at`. Not mix pattern per entity. |
| 0002 | Cron architecture | APScheduler in-process, 1 daily cron @ 00:05 UTC |
| 0003 | Audit log | Application-level, JSONB before/after snapshot |
| 0004 | Notification framework | Event-driven, channels: in_app → email → push → zalo_oa |
| 0005 | RBAC | Permission-based, in-code permission sets, 2-layer checks. **Never read role directly from JWT** — use `get_user_roles(user_id)` |
| 0006 | Data retention | PII anonymize 5 years, financial 10 years (Nghị định 13/2023) |
| 0007 | JWT auth | Stateless access (HS256, 60min, claims `sub/role/iat/exp/jti`) + stateful opaque refresh (SHA-256 hashed, token family rotation + reuse detection). Invite/reset tokens same opaque pattern. |
| 0008 | Frontend stack | React 19 + TS + Vite + shadcn/ui + TanStack Query. 15 decisions consolidated. |
| 0009 | CI/CD pipeline | GitHub Actions + VPS + Docker Compose. 2 envs (staging auto, prod manual-approve). Alembic migrate BEFORE app start. Backward-compat schema discipline. |

---

## 4. Schema & API at a Glance

### Database: 17 tables

Groups:
- **Auth** (4): `users`, `invite_tokens`, `password_reset_tokens`, `refresh_tokens`
- **Property** (2): `properties`, `rooms`
- **Tenant** (2): `tenants`, `occupants`
- **Lease** (1): `leases`
- **Service** (2): `services`, `service_rooms`
- **Meter** (1): `meter_readings`
- **Invoice** (2): `invoices`, `invoice_line_items`
- **Payment** (1): `payments`
- **Cross-cutting** (2): `audit_logs`, `notifications`

### API: 71 endpoints (OpenAPI 3.0)

- Auth (8) — login, refresh, logout, invite, reset, verify, change-password, consent
- Users (3) — me, update, delete-account
- Properties (5) — CRUD + list
- Rooms (6) — CRUD + archive/unarchive
- Tenants (8) — CRUD + archive/reactivate/promote-occupant
- Occupants (5) — CRUD + move-out
- Leases (8) — CRUD + terminate + settle-deposit
- Services (7) — CRUD + activate/deactivate
- Meter Readings (5) — batch + CRUD
- Invoices (9) — preview/commit (batch + single) + CRUD + void
- Payments (4) — CRUD (alias under Invoices: 1 GET)
- Notifications (3) — list + mark-read + mark-all-read

**Total**: 71 operations, 102 schemas, 55 error codes.

---

## 5. Key Patterns (xuyên suốt, inherited from Phase 2)

1. **Invoice immutability**: void + recreate, never edit.
2. **Computed status**: Room/Lease/Tenant/Invoice status derived at query time, not stored (except `terminated_at` is stored event).
3. **Date fields as policy tools**: Landlord dùng start_date/end_date/terminated_date để control billing.
4. **Task-oriented UI**: UX theo workflow thật (batch per property), không theo data structure.
5. **Daily cron maintenance**: 1 cron 00:05 daily cho status transitions + notifications.
6. **Soft delete vs toggle**: archive (Room, Tenant) = `is_archived`+`archived_at`; toggle (Service) = `is_active`.
7. **Pro-rata universal**: 1 formula `rent × days_occupied / days_in_month`.
8. **Preview-commit**: Invoice generation stateless preview + commit.
9. **Reading → month**: reading ngày 1/5 = consumption tháng 4 (Option B).
10. **Per_person snapshot**: tại thời điểm tạo Invoice, không cuối tháng.

---

## 6. Phase 4 Implementation Plan (proposed)

### Sprint 1 — Backend foundation (1 tuần)

- [ ] FastAPI app structure setup
- [ ] `/health` endpoint
- [ ] Structured logging
- [ ] CORS + rate limiting middleware
- [ ] Auth module: login, refresh, logout, invite, password reset (Nhóm 1, 8 stories)
- [ ] Deploy to staging (verify pipeline end-to-end)

### Sprint 2 — Property + Room + Service (1 tuần)

- [ ] Property CRUD (Nhóm 2)
- [ ] Room CRUD + archive (Nhóm 2)
- [ ] Service CRUD + toggle (Nhóm 5)
- [ ] Tests: unit + integration

### Sprint 3 — Tenant + Occupant + Lease (1.5 tuần)

- [ ] Tenant CRUD + archive/reactivate (Nhóm 3)
- [ ] Occupant CRUD + move-out (Nhóm 3)
- [ ] Lease CRUD + terminate + settle-deposit (Nhóm 4)
- [ ] Promote Occupant (US-036, apply Phase 3 override decision)

### Sprint 4 — Meter + Invoice + Payment (2 tuần)

- [ ] Meter Reading batch + CRUD (Nhóm 6)
- [ ] Invoice preview-commit + CRUD + void (Nhóm 7) — complex
- [ ] Payment CRUD (Nhóm 8)
- [ ] Cross-cutting: audit logs, notifications

### Sprint 5 — Frontend foundation (1 tuần, parallel starting Sprint 2)

- [ ] Vite + React + TS scaffold
- [ ] shadcn/ui init + theme tokens
- [ ] OpenAPI codegen setup
- [ ] Router + AppShell layout
- [ ] Auth pages (login, forgot, reset)

### Sprint 6-8 — Frontend features (3-4 tuần)

- [ ] Dashboard (per PHASE3-FRONTEND-NOTES hi-fi reference)
- [ ] Property + Room management
- [ ] Tenant management
- [ ] Lease management
- [ ] Service management
- [ ] Meter reading batch form
- [ ] Invoice preview-commit flow
- [ ] Payment recording

### Sprint 9 — Polish + production launch (1 tuần)

- [ ] E2E smoke tests
- [ ] Production VPS provision (follow vps-setup.md)
- [ ] Tag v1.0.0 → production deploy
- [ ] Bảo self-onboard: migrate 3 real properties in
- [ ] Monitoring setup

**Estimated Phase 4 duration**: 9-10 tuần (với parallel FE/BE).

---

## 7. Open Questions cho Phase 4

### From Phase 2 still open

1. ~~Refresh token rotation~~ — DECIDED (ADR-0007)
2. ~~Frontend stack~~ — DECIDED (ADR-0008)
3. ~~Email service~~ — Resend (Phase 2 confirmed)
4. Rate limiting: slowapi in-memory OK MVP, Redis khi scale
5. Deployment target — DECIDED (ADR-0009, VPS)
6. ~~Multi-role per user~~ — Defer v1.x (abstracted via `get_user_roles`)
7. Bulk import Tenant từ Excel — defer v1.x
8. Late fee / discount — defer v1.x, manual adjustment line item OK
9. Invoice number format — **CHỐT PHASE 4**: `INV-YYYY-MM-NNNN` per landlord per month (PostgreSQL SEQUENCE hoặc application lock)

### New from Phase 3

10. **Audit log exposure**: Expose via API hay internal-only? (From Wireframe 02 dashboard activity feed — need decision)
11. **Dashboard aggregation queries**: Performance khi 100+ rooms. Cache layer (Redis)? Materialized view?
12. **Search endpoint**: MVP có cần `GET /api/v1/search?q=X` không? Hay client-side filter đủ?
13. **Frontend environment detection**: `VITE_API_URL` per env build, hay single build + runtime config?
14. **CSRF protection**: SPA với cookie auth cần double-submit token? Or rely on SameSite cookies?
15. **Session management**: "Force logout all devices" UI cần có MVP không?

### Legal (defer pre-production)

16. Data retention policy review — lawyer consult before real users
17. Terms of Service + Privacy Policy drafting — when opening beta to friends

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Invoice preview-commit race condition (2 tabs commit same property) | High | Application-level lock per property+month |
| VPS single point of failure | High | Daily backup + documented restore procedure |
| Postgres disk full (logs, data grow) | Medium | Log rotation + monitoring disk usage alert |
| JWT secret leak | Critical | Rotation procedure documented (secrets-management.md) |
| Migration deadlock in production | High | Staging test mandatory, migration pre-review |
| Bảo burnout solo building 9-10 weeks | Medium | Sprint-based, realistic scope, weekly retrospective |
| Scope creep (v1.x features sneak into MVP) | Medium | Strict gate: no new feature without demoting another |

---

## 9. Success Criteria cho Phase 4

Phase 4 done khi:

- [ ] All 71 endpoints implemented + tested (≥70% coverage)
- [ ] All 11 MVP features functional end-to-end
- [ ] Frontend 5 critical flows polished (match wireframe specs)
- [ ] Deployed to production VPS
- [ ] Bảo successfully used RMS for 1 full billing cycle (real property data)
- [ ] CI/CD pipeline stable (no failed deploys last 10 runs)
- [ ] Documentation complete cho v1.0.0 launch

---

## 10. Working Style (continued from Phase 2-3)

- **Language**: Vietnamese throughout
- **Response style**: concise, signal-dense, what-why-how format
- **Decision pattern**: Claude recommend → Bảo review → chốt
- **Code pattern**: Claude explain concept → Bảo self-write → Claude review
- **Commit discipline**: 1 PR per feature, sprint-based Pull Request review
- **Chat boundary**: 1 chat per sprint hoặc 1 chat per feature group (Phase 4 scale)

---

## Appendix: File References

Phase 3 deliverables location:

```
docs/
├── decisions/
│   ├── ADR-0001-lifecycle-field-naming.md
│   ├── ADR-0002-cron-architecture.md
│   ├── ADR-0003-audit-log.md
│   ├── ADR-0004-notification-framework.md
│   ├── ADR-0005-rbac-strategy.md
│   ├── ADR-0006-data-retention.md
│   ├── ADR-0007-jwt-refresh-rotation.md
│   ├── ADR-0008-frontend-stack.md
│   └── ADR-0009-cicd-pipeline.md
├── 02-architecture/
│   ├── architecture-diagram.svg
│   ├── wireframes/
│   │   ├── README.md
│   │   ├── 01-login-dashboard-entry.md (+.png)
│   │   ├── 02-landlord-dashboard.md (+.png)
│   │   ├── 03-meter-reading-batch.md (+.png)
│   │   ├── 04-invoice-preview-commit.md (+.png)
│   │   └── 05-payment-recording.md (+.png)
│   └── PHASE3-FRONTEND-NOTES.md
├── 03-database/
│   ├── erd.mmd
│   └── erd-reference.md
├── 04-api/
│   ├── api-design-decisions.md
│   ├── endpoints.md
│   └── openapi.yaml
└── 07-deployment/
    ├── vps-setup.md
    ├── secrets-management.md
    └── rollback-runbook.md

.github/workflows/
├── backend-ci.yml
├── backend-deploy-staging.yml
└── backend-deploy-production.yml

app/
├── core/enums.py
├── db/base.py
└── models/ (17 model files)

alembic/
├── env.py
├── alembic.ini
└── versions/<hash>_initial_schema.py

Root:
├── docker-compose.yml
├── .env.example
├── pyproject.toml
└── uv.lock
```

---

**End of Phase 3. Ready for Phase 4 — Implementation. 🚀**
