# Phase 4 — Stage 1.2: Auth Core — SUMMARY

**Status**: ✅ Complete
**Branch**: `feature/auth-core-stage-1.2`
**Date completed**: 2026-04-28
**Tag (after merge)**: `v0.2.0-auth-core`

---

## 1. Goal

Implement core authentication flow for the RMS MVP:

- **US-001**: `POST /api/v1/auth/register` — Landlord self-registration
- **US-002**: `POST /api/v1/auth/login` — email + password authentication
- **US-003**: `get_current_user` dependency — JWT-based authorization

Stage 1.2 issues **access tokens only**. Refresh token rotation, logout, and the
HttpOnly refresh cookie are deferred to Stage 1.3.

---

## 2. Sub-task breakdown

| #     | Task                                | File(s)                                                                                                |
| ----- | ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| 2.1   | Pre-flight decisions                | (this document)                                                                                        |
| 2.2   | Password hashing + JWT helpers      | `app/core/security.py`                                                                                 |
| 2.3   | Domain exceptions + global handler  | `app/core/exceptions.py`, `app/main.py`                                                                |
| 2.4   | UserRepo                            | `app/repositories/user_repo.py`                                                                        |
| 2.4-p | Migration: UNIQUE on `users.email`  | `alembic/versions/<hash>_add_unique_constraint_on_users_email.py`, `app/models/user.py`                |
| 2.5   | Auth schemas                        | `app/schemas/auth.py`                                                                                  |
| 2.6   | AuthService (register + login)      | `app/services/auth_service.py`                                                                         |
| 2.7   | FastAPI auth dependencies           | `app/api/deps.py`                                                                                      |
| 2.8   | Auth endpoints + `/me`              | `app/api/v1/endpoints/auth.py`, `app/api/v1/router.py`                                                 |
| 2.9   | Integration tests + SAVEPOINT fix   | `tests/conftest.py`, `tests/integration/test_auth_*.py`, `tests/integration/test_db_isolation.py`      |
| 2.10  | Manual smoke + this SUMMARY         | `docs/04-implementation/PHASE4-STAGE1_2-SUMMARY.md`                                                    |

---

## 3. Endpoints delivered

| Method | Path                       | Auth          | Status code | Body in / out                                |
| ------ | -------------------------- | ------------- | ----------- | -------------------------------------------- |
| POST   | `/api/v1/auth/register`    | None          | 201         | `RegisterRequest` → `AuthSuccessResponse`    |
| POST   | `/api/v1/auth/login`       | None          | 200         | `LoginRequest` → `AuthSuccessResponse`       |
| GET    | `/api/v1/auth/me`          | Bearer JWT    | 200         | — → `UserRead`                               |

`AuthSuccessResponse` shape (matches OpenAPI spec):

```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": { "id": "...", "email": "...", "role": "landlord", ... }
}
```

Error response shape (handled by global `RMSException` handler):

```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "request_id": "<uuid>"
  }
}
```

---

## 4. Key architectural decisions (locked in this stage)

### 4.1 Password hashing

- **bcrypt cost factor 12** (passlib default — `~250ms/hash` on dev VPS).
- **Pinned `bcrypt<4.1`** because passlib 1.7.4 (latest) raises `ValueError: password
  cannot be longer than 72 bytes` against bcrypt 4.1+. Passlib upstream is stale.
- `passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")` —
  module-level singleton.
- `verify_password` wraps `try/except (UnknownHashError, ValueError) → False`
  to handle malformed hashes gracefully.

### 4.2 JWT access token

- **Algorithm**: HS256, secret from `settings.jwt_secret_key` (no default — fail-fast).
- **TTL**: 60 minutes (`jwt_access_token_expire_minutes`).
- **Claims**: `sub` (user_id as string), `role` (string from `UserRole.value`),
  `iat`, `exp` (both Unix int), `jti` (uuid4 str) for future revocation.
- **`exp` arithmetic**: `iat + ttl_minutes * 60` — pure int, never mix with `timedelta`.
- **`sub` is always a string** (JWT spec requires it) — even though it stores a UUID.
- Library: **`python-jose`** + `types-python-jose` for mypy stubs.

### 4.3 Domain exceptions + global handler

- **Base**: `RMSException` with `code: ClassVar[str]`, `status_code: ClassVar[int]`,
  `default_message: ClassVar[str]`. Override message in `__init__`.
- **Hierarchy**:
  - `AuthError` (categorical base, never raised)
    - `InvalidCredentialsError` — 401, `INVALID_CREDENTIALS`
    - `InvalidTokenError` — 401, `INVALID_TOKEN`
    - `TokenExpiredError` — 401, `TOKEN_EXPIRED`
  - `EmailAlreadyExistsError` — 409, `EMAIL_ALREADY_EXISTS`
  - `NotFoundError` — 404, `NOT_FOUND`
  - `PermissionDeniedError` — 403, `PERMISSION_DENIED`
- **Single handler** registered for `RMSException` — FastAPI's `isinstance`
  matching catches all subclasses.
- **`request_id`** read from `app.core.logging.request_id_var` ContextVar
  (set by `RequestIDMiddleware`), included in every error response body for
  log/response correlation.
- **Endpoints never `try/except`** domain exceptions — handler does it.

### 4.4 Email normalization (defense in depth)

Email is lowercased and stripped at TWO boundaries:

1. **Schema**: `BeforeValidator` in `RegisterRequest` and `LoginRequest`
   (`NormalizedEmail = Annotated[EmailStr, BeforeValidator(_normalize_email)]`).
2. **Repository**: `UserRepo._normalize_email` in `get_by_email` and `create`.

DB-level UNIQUE constraint on `email` (added in migration 2.4-p) prevents
TOCTOU races regardless.

### 4.5 Repository pattern

- **One repo per entity**: `app/repositories/user_repo.py`.
- **Repo signature uses keyword-only args** (`*` before all params in `create`)
  to prevent positional errors (e.g., swapping `email` and `password_hash`).
- **Repo commits transaction** at MVP. Caller does NOT commit.
- **Repo never catches `IntegrityError`** — service layer catches and maps to
  domain exceptions (e.g., `EmailAlreadyExistsError`).
- **Service catches + rolls back**: `try/except IntegrityError → db.rollback();
  raise EmailAlreadyExistsError() from e`. Rollback is mandatory because
  Postgres aborts the transaction on integrity violation.

### 4.6 Service injection (FastAPI Depends)

- **Service `__init__` takes `db: Session`** and instantiates repo internally:
  `self.user_repo = UserRepo(db)`. Not pure DI but adequate for MVP.
- Type aliases in `app/api/deps.py` for endpoint signatures:
  ```python
  DbDep         = Annotated[Session,      Depends(get_db)]
  AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
  CurrentUserDep = Annotated[User,        Depends(get_current_user)]
  ```

### 4.7 Authorization via `get_current_user`

- **`HTTPBearer(auto_error=False)`** — missing header returns `credentials=None`,
  we raise `InvalidTokenError` ourselves so the global handler produces a
  consistent JSON response (auto_error=True would short-circuit with FastAPI's
  default `HTTPException`).
- **`ExpiredSignatureError` caught BEFORE `JWTError`** — the former is a subclass
  of the latter; reverse order would never match expired.
- **Failure modes mapped explicitly**:
  - Missing credentials → `InvalidTokenError("Missing authentication token")`
  - Expired token → `TokenExpiredError`
  - Bad signature / malformed → `InvalidTokenError`
  - Token has no `sub` → `InvalidTokenError("Token missing 'sub' claim")`
  - `sub` not a UUID → `InvalidTokenError("Invalid user_id in token")`
  - User not in DB → `InvalidTokenError("User not found")`
  - User exists but `is_active=False` → `InvalidTokenError("User account inactive")`
- **Forward-compat (ADR-0007)**: backend MUST NOT read `role` directly from JWT
  for authorization decisions. Currently `get_current_user` only loads the user
  by `sub`; subsequent role checks (deferred to Stage 1.4) will route through
  `get_user_roles(user_id)`.

### 4.8 Anti-enumeration

All login failures return 401 with `code=INVALID_CREDENTIALS`, regardless of:

- email not found
- wrong password
- user `is_active=False`

Rationale: differentiated responses leak account existence/state. UX cost is
negligible compared to security benefit. (Timing attack mitigation deferred:
we currently skip bcrypt when user is None, so a fast 401 indicates "no user".
Acceptable for MVP; revisit if rate-limiting alone proves insufficient.)

### 4.9 RegisterRequest does NOT accept `role`

`RegisterRequest` only creates Landlords — role is hard-coded in
`AuthService.register_landlord`. Tenants come through the invite flow
(Stage 1.4, separate `InviteAcceptRequest`). Never let a client-supplied
field decide privilege.

### 4.10 Validation rules (`app/schemas/auth.py`)

| Field        | Rule                                                                   |
| ------------ | ---------------------------------------------------------------------- |
| `email`      | `EmailStr` + `BeforeValidator(strip + lower)`                          |
| `password`   | `min_length=8`, `max_length=72` (bcrypt limit), must contain `[a-z][A-Z][0-9]` |
| `full_name`  | `StringConstraints(strip_whitespace=True, min_length=1, max_length=255)` |
| `phone`      | regex `^[0-9+\-\s]{8,20}$`, optional                                   |
| `token_type` | hard-coded `"Bearer"` (capital, matches OpenAPI `enum: [Bearer]`)      |

Login schema does NOT enforce password complexity — users with legacy weak
passwords must still be able to log in.

### 4.11 Pydantic `model_validate(orm_user)` over `User(**user.__dict__)`

`UserRead` has `model_config = ConfigDict(from_attributes=True)`. Service builds
response via `UserRead.model_validate(user)` to read attributes safely
(SQLModel's `__dict__` includes `_sa_instance_state` and would break).

### 4.12 `response_model` AND return-type annotation on every endpoint

```python
@router.post("/register", response_model=AuthSuccessResponse, status_code=201, ...)
def register(req: RegisterRequest, svc: AuthServiceDep) -> AuthSuccessResponse:
    return svc.register_landlord(req)
```

- `response_model` → runtime validation, OpenAPI docs, **filters fields not in
  schema** (extra defense against `password_hash` leak).
- Return type → static checking (mypy/Pylance).

---

## 5. Database changes this stage

- **Migration 2.4-p** (manual, NOT autogen):
  - `op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)`
- **Model change**: `app/models/user.py` `UserBase.email` got `unique=True, index=True`.

**Migration policy reaffirmed**: write migrations manually with
`alembic revision -m "..."` (no `--autogenerate`). Phase 3 migrations have
hand-written partial indexes and circular-FK ordering that autogen will drop
incorrectly. Documented in project Instructions.

---

## 6. Test infrastructure changes

### 6.1 SAVEPOINT pattern for `db_session` fixture

The Stage 1.1 fixture rolled back the outer transaction at teardown — but if
test code called `session.commit()` (which `UserRepo.create` does), the outer
transaction was already gone, so rollback was a no-op and data leaked between
tests.

**Fix** (`tests/conftest.py`):

```python
@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    nested = connection.begin_nested()  # SAVEPOINT

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session
    session.close()
    transaction.rollback()
    connection.close()
```

`tests/integration/test_db_isolation.py` verifies the pattern (test-A creates a
user, test-B asserts it's gone).

### 6.2 New shared fixtures (`tests/conftest.py`)

```python
landlord_user   # Creates a Landlord with password "ValidPass1"
landlord_token  # JWT for landlord_user
auth_header     # {"Authorization": f"Bearer {landlord_token}"}
```

### 6.3 Test files added

- `tests/integration/test_db_isolation.py` — 2 tests
- `tests/integration/test_auth_register.py` — 7 tests (`TestRegister` class)
- `tests/integration/test_auth_login.py` — 5 tests (`TestLogin` class)
- `tests/integration/test_auth_get_current_user.py` — 4 tests (`TestGetCurrentUser` class)

**Total Stage 1.2 tests: 18 (16 auth + 2 isolation). All passing.**

---

## 7. Tech debt logged (review at end of Sprint 1)

1. **Test schema uses `SQLModel.metadata.create_all`** instead of running Alembic
   migrations. Test schema may diverge from prod (no partial indexes, no
   expression indexes, no triggers). Defer until first divergence catches a bug.
2. **Models lack `__table_args__` `Index()` definitions** for the 16 indexes
   created by Phase 3 migrations. Autogen will keep proposing to drop them.
   Project Instructions document the workaround (manual migrations only).
   Permanent fix deferred — out of scope for Stage 1.2.
3. **`passlib` `crypt` deprecation warning** (Python 3.13 will remove `crypt`).
   passlib 1.7.4 last released 2020 and is effectively abandoned. Migrate to
   direct `bcrypt` lib or argon2-cffi when this becomes a hard error.
4. **Per-login `last_login_at` UPDATE** writes to `users` on every login.
   Acceptable at MVP scale; revisit if write load grows (debounce, cached
   write-behind, or column move to a separate table).
5. **No timing-attack mitigation** in login (we skip `verify_password` when user
   is None). Combined with rate limiting (slowapi, Stage 1.5+), the risk is
   low. If formal hardening required: always run a dummy bcrypt verify when
   user is None.
6. **`pytest_collection_modifyitems` doesn't randomize order** — test isolation
   fix relies on the fact that step1 runs before step2 in a stable order.
   Adding `pytest-randomly` would be a stronger guarantee.

---

## 8. Deferred to Stage 1.3 — Refresh Token Rotation

### Endpoints to add

| Method | Path                       | Auth                | Purpose                              |
| ------ | -------------------------- | ------------------- | ------------------------------------ |
| POST   | `/api/v1/auth/refresh`     | Refresh token       | Rotate tokens (new access + refresh) |
| POST   | `/api/v1/auth/logout`      | Refresh token       | Revoke current refresh token         |
| POST   | `/api/v1/auth/logout-all`  | Bearer + refresh    | Revoke entire family (TBD)           |

### New components

- **`app/repositories/token_repo.py`** — `RefreshTokenRepo` for the
  `refresh_tokens` table (already in DB from Phase 3).
- **`app/services/refresh_token_service.py`** — issue / rotate / revoke /
  reuse-detection logic.
- **`AuthService.register_landlord` and `AuthService.login`** must be updated
  to ALSO issue a refresh token and write it to the DB.
- **`AuthSuccessResponse`** stays the same (access only in body); refresh token
  goes into `Set-Cookie`. Mobile clients can additionally receive refresh in
  body — TBD.

### Behavior to implement (per ADR-0007)

- **Stateless access JWT** (already done) + **stateful opaque refresh token**.
- Refresh token: 32+ bytes random, **SHA-256 hashed at rest** (DB stores hash, not raw).
- **Family rotation**: each refresh issues a new token in the same family
  (`token_family_id`). Old token marked `used_at=NOW()`.
- **Reuse detection**: if a refresh token is presented after `used_at` is set,
  revoke the entire family (`revoked_at=NOW()` on all rows with that family_id).
- **TTL**: 7 days (`jwt_refresh_token_expire_days`, already in `Settings`).

### Open questions for Stage 1.3 (resolve in pre-flight)

1. **Cookie attributes** for production vs dev:
   - `Secure` on prod (HTTPS), off on local dev?
   - `SameSite`: `Strict` per OpenAPI spec — verify CSRF/UX trade-off.
   - `Path=/api/v1/auth/refresh` or `/`?
2. **Mobile client refresh delivery** — body, header, or both? OpenAPI spec
   mentions both cookie (web) and body (mobile) for `/refresh`.
3. **Logout semantic** — current token only, or entire family?
   ADR-0007 should be re-read; if ambiguous, propose default + flag.
4. **Concurrent refresh** — if two tabs both use the same refresh token within
   ms of each other, one will trigger reuse-detection. Acceptable, or add
   short grace window?
5. **Revoke-on-password-change** — when implementing `/users/me` password
   change (Stage 1.4+), should it revoke all refresh tokens for the user?

### Things that must stay backward compatible

- `AuthSuccessResponse` schema — Stage 1.2 already returns it; Stage 1.3 must
  not break the body shape. Add refresh via cookie, not by mutating the body.
- `/auth/me` endpoint — no change needed.
- All Stage 1.2 tests must continue passing without modification.

---

## 9. References

- **ADR-0001**: Lifecycle field naming (soft delete vs feature toggle vs event timestamp)
- **ADR-0005**: RBAC strategy (forward-compat: `get_user_roles(user_id)`)
- **ADR-0006**: Data retention (consent_at, archive vs delete)
- **ADR-0007**: JWT access + refresh rotation — **primary reference for Stage 1.3**
- **`docs/api/endpoints.md`** — endpoint catalog
- **`docs/api/openapi.yaml`** — OpenAPI source of truth (used to lock schemas in 2.5)
- Project Instructions — manual migration policy

---

## 10. Commit history (Stage 1.2)

```
39727d2  feat(auth): add /me endpoint and integration tests
1247e2c  feat(auth): add register and login endpoints
e8d8f6a  feat(auth): add FastAPI dependencies for auth
3aac9b6  feat(auth): add AuthService for register and login
06a4557  feat(auth): add request/response schemas
d2fa643  feat(auth): add UserRepo with email normalization
70f5fe1  fix(db): add unique constraint on users.email
80dfbff  feat(auth): add domain exceptions and global handler
8149858  feat(auth): add password hashing and JWT helpers
```

(SAVEPOINT-pattern fix was folded into commit `39727d2` along with the test
infrastructure additions.)

---

## 11. How to use this document for Stage 1.3

When opening a new chat for Stage 1.3:

1. Attach this file to project knowledge.
2. Tell Claude: "Continue Phase 4 from Stage 1.3 (refresh token rotation).
   See `PHASE4-STAGE1_2-SUMMARY.md` for what's done."
3. Claude should:
   - Not re-implement anything in section 3 (Endpoints delivered) or section 4
     (Decisions locked).
   - Re-read ADR-0007 in full before proposing Stage 1.3 sub-tasks.
   - Resolve the open questions in section 8 in pre-flight (sub-task 3.1),
     same workflow as Stage 1.2's pre-flight.
   - Continue manual-migration policy.
   - Continue verify-discipline workflow (paste real outputs, not "trust me").
