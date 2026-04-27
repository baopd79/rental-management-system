# Phase 4 — Stage 1.1 Complete

> **Purpose**: Context seed cho chat Stage 1.2 (Auth core).
>
> **Started**: 2026-04-25
> **Completed**: 2026-04-26
> **Authors**: Bảo + Claude (Senior Architect + Mentor)

---

## 1. Stage 1.1 Goal — Achieved

**Mục tiêu**: từ "có docs + models" → "FastAPI app chạy local + CI/CD pipeline green"

**Demo achieved**:
- ✅ `docker compose up -d postgres` + `uv run uvicorn` → app live
- ✅ `curl http://localhost:8000/health` → 200 OK với `{status, version, environment, database}`
- ✅ `curl /health` (DB down) → 503 graceful
- ✅ Logs structured (structlog), request_id tự inject + correlation
- ✅ Production Docker image build (79MB content)
- ✅ Backend CI workflow all green (4 jobs)

**Defer**:
- ⏸️ VPS provisioning + staging deploy (B4-B7) → defer cuối Sprint 1.5
- ⏸️ Migration-check job ở CI → defer khi verify migration up/down/up local OK

---

## 2. Files Created — Inventory

### Application code

```
app/
├── __init__.py
├── main.py                          # FastAPI app + lifespan + middleware
├── api/
│   ├── __init__.py
│   ├── deps.py                      # Common dependencies (re-export get_db)
│   ├── health.py                    # /health endpoint (root path, not /api/v1)
│   └── v1/
│       ├── __init__.py
│       ├── router.py                # Aggregate v1 routers (empty for Stage 1.1)
│       └── endpoints/
│           └── __init__.py          # Empty, Stage 1.2 sẽ thêm auth.py
├── core/
│   ├── __init__.py
│   ├── config.py                    # Settings (pydantic-settings + log_level validator)
│   ├── enums.py                     # ✅ DONE Phase 3 — migrated to StrEnum
│   ├── logging.py                   # structlog + request_id contextvar
│   ├── security.py                  # ✅ Empty — Stage 1.2 sẽ thêm JWT, bcrypt
│   └── exceptions.py                # ✅ Empty — Stage 1.2 sẽ thêm domain exceptions
├── db/
│   ├── __init__.py
│   ├── base.py                      # ✅ DONE Phase 3
│   └── session.py                   # Engine + get_db dependency
├── middleware/
│   ├── __init__.py
│   └── request_id.py                # RequestIDMiddleware (X-Request-ID header)
├── models/                          # ✅ DONE Phase 3 (17 tables)
├── schemas/                         # Empty — Stage 1.2 sẽ thêm LoginRequest, etc.
├── services/                        # Empty — Stage 1.2 sẽ thêm AuthService
└── repositories/                    # Empty — Stage 1.2 sẽ thêm UserRepo
```

### Tests

```
tests/
├── __init__.py
├── conftest.py                      # Fixtures: test_engine (session), db_session (function), client
├── unit/
│   └── __init__.py                  # Empty
└── integration/
    ├── __init__.py
    └── test_health.py               # 3 tests cho /health
```

### Infrastructure

```
.github/workflows/
└── backend-ci.yml                   # 4 jobs: lint, typecheck, test, docker-build

Dockerfile                           # Multi-stage (builder + runtime), non-root user
.dockerignore                        # Exclude .git, tests, .venv, .env*
```

### Config files

```
pyproject.toml                       # uv deps + ruff config + mypy config + pytest config
.env.example                         # Template (commit)
.env.test.example                    # Test env template (commit) — Bảo có thể đã không tạo
.env                                 # Local secrets (gitignored)
.env.test                            # Test secrets (gitignored)
.gitignore                           # Updated với .env*, __pycache__, .venv, etc.
```

---

## 3. Tech Decisions Confirmed (Stage 1.1)

| Decision | Choice | Rationale |
|---|---|---|
| Config layer | pydantic-settings + `@lru_cache` | 12-Factor, type-safe |
| `extra="ignore"` cho Settings | Yes | Cùng `.env` cho Docker Compose + app |
| DB session pattern | `with Session(engine) as s: yield s` | Auto-close, simple |
| `/health` path | Root, không `/api/v1/health` | Ops endpoint, version-independent |
| Health DB ping | `session.scalar(text("SELECT 1"))` | Modern API, không deprecated như `execute` |
| Logging dev mode | `ConsoleRenderer(colors=True)` | Human-readable |
| Logging prod mode | `JSONRenderer` | Aggregator-friendly |
| Request correlation | `contextvars` + middleware | Thread-safe, async-safe |
| Middleware order | RequestID add SAU CORS (chạy outermost) | Mọi log có request_id |
| Test isolation | Transaction rollback per test | Fast (~10ms/test) |
| Docker stages | builder + runtime, cùng path `/app` | Tránh shebang issue |
| Docker user | Non-root (uid 1000) | Security best practice |
| CI trigger | Push lên main, feature/**, fix/**, PR to main | Comprehensive |

---

## 4. Lessons Learned (Stage 1.1)

### Technical lessons

1. **Mypy strict + SQLModel**: Cần module-level `disable_error_code = ["call-overload"]` cho `app.models.*` — false positive vì SQLModel `Field()` overloads
2. **`session.exec` vs `session.execute` vs `session.scalar`**:
   - `.exec(select(...))` — typed ORM query
   - `.execute(text(...))` — raw SQL (deprecated trong context Session)
   - `.scalar(text(...))` — raw SQL trả về 1 value, modern API
3. **Multi-stage Docker venv**: builder + runtime phải **cùng path** (`/app`) vì venv shebang hard-coded path. Khác path → "no such file or directory" khi exec scripts
4. **`StrEnum` (Python 3.11+)**: Thay thế pattern `class Foo(str, Enum)`. Backwards-compat trừ `str(member)` (giờ trả value thay vì class qualifier)
5. **FastAPI middleware order = LIFO stack**: `add_middleware` SAU = chạy TRƯỚC. RequestID thêm sau CORS để chạy outermost ở request side
6. **Pydantic-settings `extra="forbid"` default**: Phải `extra="ignore"` nếu `.env` chứa keys cho consumer khác (Docker Compose `POSTGRES_*`)
7. **Type alias từ library**: `structlog.types.{EventDict, Processor, WrappedLogger}`, `starlette.middleware.base.RequestResponseEndpoint` — dùng chuẩn lib thay tự type
8. **CI env vs Local env**: `DATABASE_URL` là single source of truth. Conftest fallback `.env.test` chỉ khi env chưa có (CI sẽ inject)

### Process lessons

1. **Branch strategy bị bypass**: Bảo push thẳng `main` thay vì `feature/sprint1-foundation`. Phase 4 nhiều stages — discipline tạo branch trước khi commit feature work
2. **Verify discipline**: Mỗi tool (ruff/mypy/pytest) all green local TRƯỚC khi push. Tiết kiệm CI minutes + tránh debug-CI-trong-khi-debug-code
3. **Đừng paste secrets**: Password DB bị paste 2 lần vào chat. Habit: mask trước khi paste, hoặc dùng `sed 's/PASSWORD=.*/***/'`
4. **Granular commits không bắt buộc**: Bảo gộp A1-A3 thành 1 commit. Acceptable trade-off, không cần rewrite history
5. **YAGNI applied**: `app.api.v1.router.py` empty từ A5 (chuẩn bị Stage 1.2). Trống nhưng wired vào main.py — Stage 1.2 chỉ thêm 1 dòng `include_router`

---

## 5. CI Workflow Status

**File**: `.github/workflows/backend-ci.yml`

**Triggers**:
- Push: `main`, `feature/**`, `fix/**`
- PR to `main`

**4 jobs running**:

| Job | Tools | Notes |
|---|---|---|
| `lint` | ruff check + ruff format --check | All checks passed |
| `typecheck` | mypy strict | 38 source files, 0 errors |
| `test` | pytest + Postgres 16 service | 3 tests `/health` pass |
| `docker-build` | docker buildx (no push) | Cache via `type=gha` |

**Job dependencies**: `docker-build` needs `[lint, typecheck, test]`

**CI env (workflow file)**:
```yaml
DATABASE_URL: postgresql+psycopg://rms:testpassword@localhost:5432/rms_test
JWT_SECRET_KEY: ci_test_secret_only
APP_ENV: development
LOG_LEVEL: WARNING
```

---

## 6. Sprint 1 Plan (Updated)

| Stage | Scope | Status |
|---|---|---|
| 1.1 | Repo + FastAPI structure + /health + CI | ✅ **DONE** |
| 1.2 | Auth core: US-001 (register), US-002 (login), US-003 (JWT middleware) | ⏳ **NEXT** |
| 1.3 | Token flows: US-007 (logout), US-008 (refresh rotation) | Pending |
| 1.4 | Tenant invite: US-004 (generate), US-005 (accept) | Pending |
| 1.5 | Password reset: US-006 (request + confirm) | Pending |
| Final | VPS provision + staging deploy + tag v0.1.0-alpha | Defer cuối Sprint 1 |

---

## 7. Open Questions / Decisions cho Stage 1.2

Bảo nên suy nghĩ trước khi vào Stage 1.2:

1. **Schema layer**: SQLModel `*Create/*Read/*Update` (Cách 2 đã chốt) hay tách Pydantic riêng cho LoginRequest/LoginResponse?
2. **Service injection**: `Depends(AuthService)` hay constructor injection? FastAPI pattern thường dùng `Depends`
3. **bcrypt cost factor**: 12 (default passlib) hay tune theo VPS RAM?
4. **Repository pattern**: 1 file/entity hay gộp? (`UserRepo`, `TokenRepo`, ...)
5. **Error handling**: Domain exception → HTTP code mapping ở exception_handlers global hay per-endpoint try/except?
6. **JWT_SECRET_KEY rotation**: Manual rotation ADR-0007 đã chốt — nhưng implement procedure ở Stage nào? (defer Stage 1.5?)
7. **Test strategy**: Service layer test với mocked repo, hay integration test với real DB cho service? Trade-off speed vs realism
8. **First migration after models**: Có migration nào cần thêm cho auth (ngoài 17 tables Phase 3)? (theory: không, đã đủ user/refresh_tokens/invite_tokens/password_reset_tokens)

---

## 8. Working Style (Continued from Phase 2-3)

- **Language**: Vietnamese throughout
- **Response style**: concise, signal-dense, what-why-how format
- **Decision pattern**: Claude recommend → Bảo review → chốt
- **Code pattern**: Claude explain concept → Bảo self-write → Claude review → discuss edge case
- **Verify discipline**: paste output thật, không "trust me ok rồi"
- **Commit discipline**: 1 PR per feature, conventional commits format
- **Pace**: Bảo flag khi quá nhanh hoặc dài

---

## 9. Files cần đính kèm chat Stage 1.2

**Bắt buộc (paste vào chat mới)**:
- `PHASE4-STAGE1.1-SUMMARY.md` — file này
- `PHASE3-SUMMARY.md` (đã có trong Project Knowledge)
- `endpoints.md` (đã có trong Project Knowledge) — auth endpoints spec
- `ADR-0007-jwt-refresh-rotation.md` (đã có trong Project Knowledge)
- `ADR-0005-rbac-strategy.md` (đã có trong Project Knowledge)

**Optional**:
- Code đã viết Stage 1.1 (Bảo có thể paste khi cần Claude review pattern cụ thể)

---

## 10. Next Chat Opening Prompt

```
Chào! Tôi tiếp tục Phase 4 của dự án RMS.

Đính kèm:
- PHASE4-STAGE1.1-SUMMARY.md (vừa hoàn thành Stage 1.1)
- PHASE3-SUMMARY.md (Phase 3 decisions)
- ADR-0007 (JWT + refresh rotation), ADR-0005 (RBAC)
- endpoints.md (API spec), api-design-decisions.md

## Stage 1.2 Goal — Auth Core

3 user stories:
- US-001: POST /api/v1/auth/register — Đăng ký landlord
- US-002: POST /api/v1/auth/login — Đăng nhập (JWT + refresh)
- US-003: JWT auth middleware — get_current_user dependency

Plus:
- bcrypt password hashing helper (app/core/security.py)
- JWT encode/decode helpers (app/core/security.py)
- AuthService (app/services/auth_service.py)
- UserRepo (app/repositories/user_repo.py)
- LoginRequest/LoginResponse schemas
- Exception → HTTP mapping (app/core/exceptions.py)

## Working Style (giữ nguyên)
- Senior Architect + Mentor
- What-why-how, câu hỏi logic, recommend phương án
- Concept trước → tôi tự viết → bạn review → discuss edge case
- Ngắn gọn, signal-dense, không xu nịnh
- Verify discipline: tôi paste output thật

## Bắt đầu

Đầu tiên bạn check 3 file Project Knowledge (ADR-0007, endpoints.md,
PHASE4-STAGE1.1-SUMMARY) rồi propose Stage 1.2 plan chia sub-tasks
(2.1, 2.2, ... tương tự A1-A6 ở Stage 1.1).

Sau khi tôi confirm plan, bắt đầu sub-task đầu tiên.
```

---

**End of PHASE4-STAGE1.1-SUMMARY.md. Ready for Stage 1.2.** 🚀
