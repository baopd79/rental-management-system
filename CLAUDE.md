# CLAUDE.md

Guidance cho Claude Code khi làm việc với repository này.

## Project Overview

RMS (Rental Management System) — Vietnamese rental property management
SaaS cho landlord 5-100 phòng. Solo developer (Bảo). Mục tiêu: portfolio

- dogfood quản lý 3 nhà trọ thật của Bảo.

**Status**: Phase 3 complete (architecture + design + 17 SQLModel models +
OpenAPI spec). Phase 4 implementation in progress.

**Stack**: FastAPI + SQLModel + PostgreSQL 16 (sync, MVP). Frontend Phase 4
sẽ là React 19 + TypeScript + Vite + shadcn/ui.

## Working Style (IMPORTANT — read first)

Bảo đang học backend để intern. Pattern hợp tác:

1. **Explain first, code second**: Trước khi tạo file/edit, explain
   pattern + rationale. Đợi Bảo OK mới code.
2. **Bảo writes logic-heavy files**: Service layer, business rules.
   Claude Code làm boilerplate (config, fixtures, Dockerfile, migrations).
3. **Code review pattern**: Bảo viết code → Claude Code review → discuss
   edge cases.
4. **Vietnamese trong docstrings + comments + chat responses**. English
   cho identifiers (variables, functions, classes).
5. **Concise**: Signal-dense responses. Khi nhiều hướng giải, nêu
   trade-off + recommend.
6. **Khi mơ hồ, làm rõ trước khi code** — đừng đoán.

## Current Sprint

**Phase 4 Sprint 1 — Backend Foundation + Auth Module**

Goal: Login API live trên staging end-of-sprint. Demo curl được:

- `POST /api/v1/auth/login` → access + refresh tokens
- `POST /api/v1/auth/refresh` → rotation work
- `POST /api/v1/auth/logout` → token revoked
- `GET /health` → 200 với version + DB status
- CI/CD pipeline run end-to-end

**Stages**:

- 1.1: FastAPI scaffold + /health + pytest fixture + first staging deploy
- 1.2: Auth core (US-001/002/003): register, login, JWT middleware
- 1.3: Token flows (US-007/008): logout, refresh rotation
- 1.4: Tenant invite (US-004/005): generate + accept
- 1.5: Password reset (US-006): request + confirm

Update file `docs/05-implementation/sprint-01.md` cuối mỗi stage.

## Critical Rules (must follow)

### From ADRs

- **ADR-0001 Lifecycle naming**: KHÔNG mix patterns trên 1 entity
  - Soft delete: `is_archived` + `archived_at` (rooms, tenants)
  - Toggle: `is_active` (services, users)
  - Event: `<event>_at` (leases.terminated_at, invoices.voided_at, refresh_tokens.revoked_at)
  - Single-use: `used_at` (invite_tokens, password_reset_tokens)

- **ADR-0005 RBAC**: KHÔNG đọc `role` từ JWT claims để authorization.
  Luôn qua `get_user_roles(user_id)` query DB. JWT `role` chỉ cho UX hint
  (render UI), không phải permission source of truth.

- **ADR-0007 JWT**: Refresh token rotation với reuse detection. Mỗi
  refresh sinh token mới + revoke cũ. Reuse detected → revoke entire
  family_id.

- **ADR-0009 Migration**: Mỗi migration phải backward-compatible. Schema
  add OK, drop/rename NOT OK trong cùng version với code changes.

### From PHASE3 implementation

- **Invoice immutability**: Void + recreate, NEVER edit. Edit endpoint
  không tồn tại trong API spec là intentional.
- **17 SQLModel models trong `app/models/` là FINAL** — đã viết Phase 3,
  đừng re-generate. Import dùng directly.
- **Computed status fields**: room/lease/tenant/invoice status derived
  at query time, NOT stored. Chỉ store `<event>_at` là event marker.
- **Per_person snapshot**: `meter_readings.person_count` snapshot tại
  thời điểm tạo invoice, không cuối tháng.

## Commands

### Environment Setup

```bash
uv sync --frozen          # Install dependencies from lockfile
docker compose up -d      # Start PostgreSQL 16 dev database
cp .env.example .env      # Then fill in credentials
```

### Database Migrations

```bash
uv run alembic upgrade head                            # Apply all
uv run alembic downgrade base                          # Revert all
uv run alembic revision --autogenerate -m ""  # Generate new
```

### Lint / Format / Type Check

```bash
uv run ruff check backend/           # Lint
uv run ruff format backend/          # Auto-format
uv run ruff format --check backend/  # Format check (CI mode)
uv run mypy backend/                 # Static type checking
```

### Testing

```bash
uv run pytest --cov=backend --cov-report=xml --cov-fail-under=70 -v
```

CI enforces 70% coverage minimum. Migration tests run up/down/up to verify
reproducibility (per ADR-0009 backend-ci.yml).

## Architecture

### Layer Structure (Phase 4)

FastAPI Router → Request Handler → Service Layer → Repository → SQLModel → PostgreSQL

**Conventions**:

- Service layer: business logic + transaction boundary
- Repository: SQLModel queries, no business logic
- Router: thin, delegate to service. Validation via Pydantic schemas.
- No async ORM MVP — SQLModel sync. Defer async to Phase 5 nếu cần.

### Authentication (ADR-0007)

- Access token: JWT HS256, 60-min TTL, claims `sub/role/iat/exp/jti`
- Refresh token: opaque random, SHA-256 hash trong DB, family rotation
- 4 token tables: `refresh_tokens`, `invite_tokens`, `password_reset_tokens`
  (`users.password_hash` qua bcrypt, separate)
- Web: refresh trong HttpOnly cookie, Path `/api/v1/auth/refresh`
- Mobile (v1.x): refresh trong native secure storage

### Database (`app/db/base.py`, `app/models/`)

3 mixins compose:

- `UUIDPrimaryKeyMixin` — UUID PK với `gen_random_uuid()` server-side
- `TimestampMixin` — `created_at` + `updated_at` qua `NOW()` server-side
- `CreatedAtOnlyMixin` — append-only (audit_logs, notifications, invoices, payments)

PostgreSQL enums dùng factory `create_pg_enum()` từ `app/core/enums.py`.
Đừng dùng SQLAlchemy `Enum` trực tiếp — extend file đó.

### Indexes

- Partial unique indexes cho "unique when active" (e.g., room
  `display_name` unique per property khi `is_archived = FALSE`)
- All FK columns có covering indexes hot-path. Add explicit trong
  migrations — Alembic không auto-generate.

### API (71 endpoints)

Full spec: `docs/04-api/openapi.yaml`. Khi implement endpoint mới:

- Match request/response schema chính xác (FE codegen depends)
- Match error codes enum (55 codes documented)
- Pagination/filter/sort patterns: xem `api-design-decisions.md`

### Audit & Notifications

- **Audit log** (ADR-0003): application-level, JSONB before/after snapshot
  trong `audit_logs` table. KHÔNG dùng DB triggers.
- **Notifications** (ADR-0004): event-driven, in-app first MVP. Email/
  push/Zalo deferred.

### Cron

APScheduler in-process (ADR-0002). 1 daily job @ 00:05 UTC. KHÔNG tạo
worker process riêng cho MVP.

## Test Strategy (Sprint 1 establish patterns)

- **Fixture pattern**: pytest fixtures cho `db_session` (transaction
  rollback per test), `client` (FastAPI TestClient), `auth_headers`
  (logged-in user)
- **Postgres test container**: GitHub Actions service container (xem
  `.github/workflows/backend-ci.yml`). Local: dùng cùng `docker-compose.yml`
  database, schema rolled back per test.
- **Coverage target**: 70% min CI fail-under. Service layer aim 90%,
  routers 60% OK (thin layer).
- **Test naming**: `test_<scenario>_<expected>` e.g.
  `test_login_with_wrong_password_returns_401`

## Branching & Workflow (ADR-0009)

- `main` → push → auto-deploy to staging
- Tag `v*.*.*` (semver) → push → manual-approve deploy to production
- Feature branches: `feature/<scope>` (e.g., `feature/auth-login`)
- Fix branches: `fix/<scope>`
- Hotfix: `hotfix/<scope>` → PR to main → tag `v*.*.*-hotfix.N`

NO `develop` branch (solo dev, không cần extra integration layer).

## Key Reference Docs

| Path                                  | When to read                                      |
| ------------------------------------- | ------------------------------------------------- |
| `docs/PHASE3-SUMMARY.md`              | Start here when picking up project — full context |
| `docs/decisions/ADR-*.md`             | Before changing design pattern (9 ADRs)           |
| `docs/04-api/openapi.yaml`            | Source of truth khi implement endpoint            |
| `docs/04-api/endpoints.md`            | Quick endpoint lookup                             |
| `docs/04-api/api-design-decisions.md` | Conventions (pagination, errors, special flows)   |
| `docs/03-database/erd-reference.md`   | Schema reference                                  |
| `docs/01-requirements/`               | 63 user stories, 8 functional groups              |
| `docs/07-deployment/vps-setup.md`     | Sprint 1 deploy instructions                      |

## Infrastructure Notes

- **Package manager**: `uv` — always `uv run` to invoke Python tools.
  Do not use `pip` or bare `python`.
- **Secrets**: GitHub Secrets (CI) + VPS `.env` files. Never commit `.env`.
- **Pre-start migration**: `alembic upgrade head` runs trước khi FastAPI
  start. Migrations must be backward-compatible.
- **Frontend** (Phase 4 Sprint 5+): pnpm 10, TypeScript strict, API
  client auto-gen từ OpenAPI spec qua `openapi-typescript` + `openapi-fetch`.

## Common Pitfalls (avoid these)

1. **Don't re-write models** — 17 files trong `app/models/` đã FINAL.
2. **Don't read role from JWT** — always `get_user_roles(user_id)`.
3. **Don't edit invoices** — void + recreate.
4. **Don't add async ORM** — SQLModel sync OK MVP.
5. **Don't skip migration backward-compat check** — drop/rename = 2 releases.
6. **Don't mix lifecycle patterns** — 1 entity = 1 pattern.
7. **Don't use SQLAlchemy `Enum` directly** — use `create_pg_enum()` factory.
8. **Don't store computed status** — derive at query time.

Recommendation: Replace CLAUDE.md
Bảo paste version trên vào CLAUDE.md → commit:
bash# Trong project root
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with Phase 3 context + working style + critical rules"
Sau đó: Sẵn sàng start Stage 1.1
Khi CLAUDE.md update xong, prompt cho Stage 1.1 trong Claude Code:
Phase 4 Sprint 1 Stage 1.1 — FastAPI scaffold + /health endpoint

Pattern: Explain first, code second. Bảo writes logic-heavy, Claude
Code does boilerplate (xem CLAUDE.md Working Style).

Plan đề xuất:

1. Setup pyproject.toml với dependencies categorized
2. App folder structure (app/core/, app/api/v1/, app/services/,
   app/repos/, app/db/)
3. Config qua pydantic-settings + .env.example
4. /health endpoint (no DB yet, simple)
5. Structured logging (structlog)
6. Alembic config + verify initial migration apply local
7. docker-compose.yml dev (postgres 16 + backend)
8. pytest fixtures (db_session với transaction rollback, TestClient)
9. First commit + push → verify CI workflow run

Trước khi tạo file:

1. Recommend folder structure cụ thể với rationale
2. Liệt kê dependencies (categorized: runtime / dev / test)
3. Order tạo file (dependency order)
4. Files Bảo nên tự viết (logic) vs Claude Code viết (boilerplate)

Đừng tạo files yet. Tôi review plan trước.
