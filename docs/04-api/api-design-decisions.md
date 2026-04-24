# API Design Decisions — RMS

> **Status**: APPROVED (end of Phase 3 Chat 4, S4.1)
> **Scope**: Cross-cutting API design conventions cho 11 resources MVP
> **Audience**: Backend developers (Phase 4 implementation), future maintainers
> **Companion docs**:
> - `openapi.yaml` — full OpenAPI 3.0 spec (S4.4)
> - `endpoints.md` — resource → endpoint mapping table (S4.2)
> - `../02-architecture/*` — architecture decisions (ADR-0001 → ADR-0007)
>
> **Relationship to ADRs**: Document này chứa ~24 decisions. Cuối Phase 3,
> các decisions có **reversal cost cao + cross-module impact** sẽ được
> promote thành ADR-0008+. Các decisions convention-level giữ lại ở đây.

---

## Table of Contents

- [1. Foundation (Group A)](#1-foundation-group-a)
- [2. Authentication & Authorization (Group B)](#2-authentication--authorization-group-b)
- [3. Resource Modeling (Group C)](#3-resource-modeling-group-c)
- [4. Querying (Group D)](#4-querying-group-d)
- [5. Error Handling (Group E)](#5-error-handling-group-e)
- [6. Special Operations (Group F)](#6-special-operations-group-f)
- [7. Convention Reference](#7-convention-reference)
- [8. Error Code Registry](#8-error-code-registry)
- [9. Future Considerations](#9-future-considerations)

---

## 1. Foundation (Group A)

### A1 — API Versioning

**Decision**: URL path versioning — `/api/v1/*` từ đầu.

**Rationale**:
- Visible trong log, URL share được, debug dễ
- FastAPI idiomatic (`APIRouter(prefix="/api/v1")`)
- Industry majority (Stripe, GitHub, Twitter)
- Mobile app v1 còn chạy khi ship v2 → giữ `/api/v1/*` sống song song

**Trade-off chấp nhận**: Không "REST purist" (URL không stable vĩnh viễn), nhưng visibility value cao hơn với portfolio/solo-dev context.

**Header versioning** (`Accept: application/vnd.rms.v1+json`) chỉ phù hợp khi URL là public contract stable cho nhiều client lớn — RMS MVP không thuộc case đó.

### A2 — Base URL Structure

**Decision**: Flat under `/api/v1/*` cho business + auth; ops concerns riêng.

```
/api/v1/auth/*      ← Auth flows (public endpoints)
/api/v1/users/*     ← User profile
/api/v1/{resource}/* ← 11 business resources
/health             ← Ops, no version (stable contract)
/docs               ← Swagger UI
/redoc              ← Redoc UI
/openapi.json       ← OpenAPI spec raw
```

**Future zones** (không làm MVP):
- `/admin/*` — khi có Staff role (v2.x)
- `/webhooks/*` — khi tích hợp Zalo OA / payment gateway (v1.x+)
- `/public/*` — khi share invoice qua signed link (v1.x+)
- `/ws/*` — khi có real-time (v2.x)
- `/metrics` — khi deploy Prometheus

**Principle**: "Add zones when driven by concrete use case, not speculation." Mỗi zone = 1 middleware config + 1 auth strategy + cognitive cost. Thêm sau cost thấp.

### A3 — Content Negotiation

**Decision**: JSON-only cho MVP.

- **Request**: `Content-Type: application/json` required. Khác → 415 Unsupported Media Type.
- **Response**: `Content-Type: application/json; charset=utf-8`. UTF-8 bắt buộc (tiếng Việt có dấu).
- **Error response**: cùng `application/json` shape (không `application/problem+json`).

**Non-JSON cases future** (convention ghi sẵn để v1.x không phải suy nghĩ lại):

| Use case | Format | Pattern |
|---|---|---|
| Upload ảnh phòng, CCCD | `multipart/form-data` | `POST /{resource}/{id}/attachments` |
| Download invoice PDF | `application/pdf` | `GET /invoices/{id}/pdf` |
| Export CSV/Excel | `text/csv`, `application/vnd.ms-excel` | `GET /api/v1/exports/{resource}.{ext}` |

Mọi export dùng endpoint riêng dưới `/api/v1/exports/*` — không merge qua query param `?format=csv`.

### A4 — Request Tracing

**Decision**: `X-Request-Id` header, client-provided with server fallback.

**Behavior**:
1. Middleware intercept mọi incoming request
2. Check `X-Request-Id` header:
   - Valid (regex `^[A-Za-z0-9_-]{1,64}$`) → dùng giá trị client
   - Invalid/missing → server generate UUID v4
3. Set vào context (ContextVar) → mọi logger dùng được
4. Set response header `X-Request-Id` (luôn trả về)

**Log format** (Phase 4 implement):
```
2026-04-22 15:30:12 [req_id=550e8400-...] INFO GET /api/v1/invoices/123
2026-04-22 15:30:12 [req_id=550e8400-...] ERROR Invoice not found: 123
```

**MVP scope**: log meta only (method, path, status, duration, request_id). Không log request/response body (PII/password risk).

---

## 2. Authentication & Authorization (Group B)

### B1 — Token Delivery

**Decision**: Authorization Bearer header only.

```http
Authorization: Bearer <jwt_access_token>
```

**Client storage strategy** (advisory, không constraint trong OpenAPI spec):
- Access token → **in-memory** phía frontend (React state, không persist)
- Refresh browser → phải login lại hoặc rely on refresh cookie
- Không dùng `localStorage`/`sessionStorage` cho access token (XSS risk)

**OpenAPI security scheme**:
```yaml
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []   # Global default

# Public endpoints override:
paths:
  /api/v1/auth/login:
    post:
      security: []
```

**XSS mitigation**: CSP strict, React default escaping, in-memory storage, 60-min access token TTL, refresh token rotation (ADR-0007).

### B2 — Refresh Token Flow

**Decision**: Rotation với hybrid delivery.

**Refresh token storage**:
- Web: **HttpOnly cookie**, `Path=/api/v1/auth/refresh` (scope hẹp)
- Mobile: **secure native storage** (Keychain iOS / EncryptedSharedPreferences Android)

**Cookie attributes**:
```
Set-Cookie: refresh_token=<opaque>;
  HttpOnly;
  Secure;
  SameSite=Strict;
  Path=/api/v1/auth/refresh;
  Max-Age=604800            ; 7 days
```

**Endpoint**: `POST /api/v1/auth/refresh`

**Accept refresh token from** (priority order):
1. Cookie `refresh_token` (web path)
2. Body `{"refresh_token": "..."}` (mobile path)

**Response** (rotation — cả 2 token mới):
```json
Response 200:
Set-Cookie: refresh_token=<new_opaque>; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=604800

{
  "access_token": "new.jwt.token",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Rotation detection** (ADR-0007): cùng refresh token dùng 2 lần → revoke toàn token family.

**Client refresh trigger**: Reactive (retry on 401) — interceptor-based. Không constraint ở spec, là client concern.

### B3 — Invite Accept Flow (Tenant Activation)

**Decision**: 2 endpoints — verify trước, accept sau. Accept auto-login.

#### `POST /api/v1/auth/invite/verify`

Check invite token validity (preview trước khi user nhập password).

```json
Request:
{"token": "opaque_token_string"}

Response 200 (valid):
{
  "valid": true,
  "email": "tenant@example.com",
  "name": "Nguyen Van A",
  "landlord_name": "Mr Thanh"
}

Response 400 (invalid):
{"error": {"code": "INVITE_TOKEN_EXPIRED", ...}}
```

Token ở **body** (POST) — không vào URL để tránh leak qua logs/history.

#### `POST /api/v1/auth/invite/accept`

Activate account + set password + auto-login.

```json
Request:
{
  "token": "opaque_token_string",
  "password": "SecurePass123!",
  "consent_pii": true
}

Response 200:
Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/refresh; Max-Age=604800

{
  "access_token": "jwt.token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "tenant@example.com",
    "role": "tenant"
  }
}
```

**Required fields**: `token`, `password`, `consent_pii` (must be `true` — ADR-0006 explicit consent).

**Error codes**: `INVALID_INVITE_TOKEN`, `INVITE_TOKEN_USED`, `INVITE_TOKEN_EXPIRED`, `WEAK_PASSWORD`, `CONSENT_REQUIRED`.

### B4 — Password Reset Flow

**Decision**: 2-step (request/confirm), enumeration-safe, NO auto-login.

#### `POST /api/v1/auth/password-reset/request`

```json
Request:
{"email": "user@example.com"}

Response 200 (always, enumeration-safe):
{"message": "If this email is registered, a password reset link has been sent."}
```

**Enumeration protection**: Email tồn tại hay không → cùng 200 response. Không leak thông tin account existence.

#### `POST /api/v1/auth/password-reset/confirm`

```json
Request:
{
  "token": "opaque_reset_token",
  "new_password": "NewSecurePass123!"
}

Response 200 (NO auto-login):
{"message": "Password updated. Please login with new password."}
```

**Side effects (server-side, Phase 4)**:
- Revoke all refresh tokens của user (invalidate all sessions)
- Access tokens đang active tự expire sau tối đa 60 phút (acceptable window)

**Rate limiting flag (Phase 4)**:
- 3 requests / hour / IP
- 1 request / 5 minutes / email
- Implement qua `slowapi` (in-memory)

**Error codes**: `INVALID_RESET_TOKEN`, `RESET_TOKEN_USED`, `RESET_TOKEN_EXPIRED`, `WEAK_PASSWORD`.

### B5 — Logout

**Decision**: Current device only MVP, idempotent.

#### `POST /api/v1/auth/logout`

```http
Authorization: Bearer <access_token>
Cookie: refresh_token=...     (web)
# OR
Content-Type: application/json
{"refresh_token": "..."}      (mobile)

Response 204 No Content
Set-Cookie: refresh_token=; Max-Age=0   (clear cookie)
```

**Semantics**:
- Revoke refresh token hiện tại
- Access token không revoke được (stateless JWT) — tự expire
- **Idempotent**: gọi nhiều lần đều 204, kể cả khi refresh token đã invalid

**Future v1.x**: `POST /api/v1/auth/logout-all` — revoke mọi refresh token của user (use case: báo mất điện thoại).

### B6 — Authorization Error Mapping

**Decision**: 401 / 403 / 404 rõ ranh giới semantic.

| Scenario | Status | Code |
|---|---|---|
| No `Authorization` header | 401 | `AUTHENTICATION_REQUIRED` |
| Malformed token (không phải Bearer) | 401 | `TOKEN_INVALID` |
| Token signature invalid | 401 | `TOKEN_INVALID` |
| Token expired | 401 | `TOKEN_EXPIRED` |
| User đã archive (`is_active=false`) | 401 | `USER_INACTIVE` |
| Auth OK, role không có permission | 403 | `PERMISSION_DENIED` |
| Auth OK, có permission, nhưng không own resource | **404** | `NOT_FOUND` |

**401 responses**: kèm header `WWW-Authenticate: Bearer` (RFC 6750 compliance).

**Ownership = 404 rule (quan trọng)**:
- Landlord A gọi `GET /api/v1/properties/{uuid_của_B}` → trả 404, không 403
- **Lý do**: principle of least information. 403 tiết lộ "UUID này là property thật, của user khác". 404 không phân biệt "không tồn tại" vs "thuộc user khác".
- **Áp dụng tất cả operations**: GET/PATCH/POST action/DELETE khi resource không own.

**Trade-off**: Debug khó hơn cho dev (confuse "không tồn tại" vs "không có quyền"). Acceptable vì MVP solo dev biết schema.

---

## 3. Resource Modeling (Group C)

### C1 — Naming Convention

**Decision**: Plural nouns, kebab-case.

| Rule | Example |
|---|---|
| Collections plural | `/properties`, `/invoices` |
| Multi-word kebab-case | `/meter-readings` |
| Item access | `/{collection}/{id}` |
| Singleton "own" | `/users/me` |

**11 top-level resources MVP**:

```
/api/v1/users
/api/v1/properties
/api/v1/rooms
/api/v1/tenants
/api/v1/occupants
/api/v1/leases
/api/v1/services
/api/v1/meter-readings
/api/v1/invoices
/api/v1/payments
/api/v1/notifications
```

**Not exposed MVP**:
- `audit_logs` — defer v1.x (chưa có UI; Landlord dùng psql)
- `invite_tokens`, `password_reset_tokens`, `refresh_tokens` — internal only
- `service_rooms` — junction table, expose qua `applied_room_ids` trong Service (C3)

### C2 — Resource Nesting Rules

**Decision**: Hybrid nesting, max 1 level.

| Rule | Pattern | Example |
|---|---|---|
| R1 — Item access | Flat | `GET /rooms/{id}` |
| R2 — List children của parent | Nested 1 level | `GET /properties/{pid}/rooms` |
| R3 — Create với parent context | Nested | `POST /rooms/{rid}/leases` |
| R4 — Max depth | 1 level | ❌ `/properties/{pid}/rooms/{rid}/leases` |
| R5 — Cross-parent filter | Flat + query | `GET /invoices?tenant_id=X&status=unpaid` |
| R6 — Update/Delete | Flat | `PATCH /rooms/{id}` |

**Alias pattern accepted**: `GET /properties/{pid}/rooms` và `GET /rooms?property_id={pid}` làm cùng việc, share backend logic. Nested đọc intent rõ (tour guide), flat dễ compose multi-filter.

**Anti-pattern đã loại**:
```
❌ /properties/{pid}/rooms/{rid}/leases/{lid}/invoices/{iid}/payments/{pmid}
```

Client có payment ID là đủ → `/payments/{id}`.

### C3 — Sub-Resource Ownership Edge Cases

**Occupants** (ownership = Tenant):
- Primary: `GET /tenants/{tid}/occupants`
- Alias: `GET /occupants?tenant_id=X`
- Không expose `/rooms/{rid}/occupants` (derived context, dùng query compose)

**Services ↔ Rooms junction** (embedded, không expose junction table):
```json
GET /services/{id}
{
  "id": "...",
  "scope": "selected_rooms",
  "applied_room_ids": ["room-uuid-1", "room-uuid-2"]
}

PATCH /services/{id}
{
  "scope": "selected_rooms",
  "applied_room_ids": ["room-uuid-1", "room-uuid-3"]   ← Replace whole array
}
```

PATCH replace semantic: server tính diff internal → INSERT/DELETE `service_rooms` rows.

**Invoice line items** (embedded trong detail, summary trong list):
```json
GET /invoices                       ← List: {data: [{..., total_amount, line_item_count}], pagination}
GET /invoices/{id}                  ← Detail: {..., line_items: [...]}
```

Line items không mutate lẻ (Invoice Immutability — ADR Phase 2).

**Meter readings** (dual pattern):
- Batch create: `POST /properties/{pid}/meter-readings` (Phase 2 primary UX)
- Per-reading CRUD: `GET/PATCH/DELETE /meter-readings/{id}` (sửa sai riêng)
- List: `GET /meter-readings?property_id=X&reading_date__gte=...`

### C4 — Action Endpoints (Non-CRUD)

**Convention**: `POST /{resource}/{id}/{verb}`.

**Rules**:
1. Method: **POST** always (non-idempotent natural, có body input)
2. Path suffix: verb imperative English (`void`, `terminate`, `promote`, `activate`)
3. Body: action input only (không include resource state)
4. Response: full resource after action (client không cần re-fetch)
5. Error codes: 409 invalid state, 422 validation, 403 permission, 404 ownership

**Action inventory MVP**:

| # | Endpoint | Semantic |
|---|---|---|
| 1 | `POST /invoices/{id}/void` | Hủy invoice (immutability pattern) |
| 2 | `POST /properties/{pid}/invoices/preview` | Preview batch trước commit |
| 3 | `POST /properties/{pid}/invoices` | Commit batch (regular create) |
| 4 | `POST /leases/{id}/terminate` | Chấm dứt lease + side effects |
| 5 | `POST /leases/{id}/settle-deposit` | Tất toán cọc (separate step) |
| 6 | `POST /leases/{id}/renew` | Tạo lease mới link chain |
| 7 | `POST /occupants/{id}/promote` | Lên Tenant đại diện (atomic) |
| 8 | `POST /tenants/{id}/archive` | Soft delete với guards |
| 9 | `POST /tenants/{id}/reactivate` | Unarchive (US-030 flow A) |
| 10 | `POST /services/{id}/activate` | Toggle `is_active=true` |
| 11 | `POST /services/{id}/deactivate` | Toggle `is_active=false` |

**Idempotency (future Phase 4)**: Actions quan trọng (`void`, `terminate`, `promote`) nên support header `Idempotency-Key` (UUID client-generated, server cache response 24h). Không implement MVP.

---

## 4. Querying (Group D)

### D1 — Pagination

**Decision**: Offset-based với envelope shape.

**Request**:
```
GET /invoices?limit=20&offset=0
```

**Response envelope**:
```json
{
  "data": [...],
  "pagination": {
    "limit": 20,
    "offset": 0,
    "total": 127
  }
}
```

**Defaults + validation**:
- `limit` default: 20
- `limit` range: [1, 100] — out of range → 422
- `offset` default: 0
- `offset` min: 0 — negative → 422
- `total`: always included

**Apply cho mọi list endpoint**: invoices, rooms, tenants, leases, payments, meter-readings, properties, occupants, services, notifications, users.

**Future v2.x**: Migrate sang cursor-based khi scale > 10K rows/collection. Response shape đã prepared — thêm `next_cursor` field, backward compatible.

### D2 — Filter Syntax

**Decision**: `field__operator=value` (Django `__` convention).

**Operators MVP**:

| Operator | Suffix | Example | SQL |
|---|---|---|---|
| equals | (none) | `status=unpaid` | `status = 'unpaid'` |
| in list | `__in` | `status__in=unpaid,partial` | `status IN (...)` |
| greater than or equal | `__gte` | `billing_month__gte=2026-01-01` | `>= ` |
| less than or equal | `__lte` | `billing_month__lte=2026-12-31` | `<= ` |
| greater than | `__gt` | `amount__gt=1000000` | `> ` |
| less than | `__lt` | `amount__lt=5000000` | `< ` |
| contains (ILIKE) | `__contains` | `name__contains=Nguyen` | `ILIKE '%...%'` |
| starts with (ILIKE) | `__startswith` | `phone__startswith=090` | `ILIKE '...%'` |
| is null | `__isnull` | `archived_at__isnull=true` | `IS NULL` |

**Rules**:
- **IN separator**: comma (`status__in=a,b,c`). Không multi-param.
- **Logical**: AND between params. OR không support MVP.
- **Whitelist strict**: mỗi endpoint declare filter fields được support; undeclared → 400 `UNKNOWN_FILTER_FIELD`.
- **Boolean**: `true` / `false` (case-insensitive).
- **Date/datetime**: ISO 8601 (`YYYY-MM-DD`, `YYYY-MM-DDTHH:MM:SSZ`).

### D3 — Sort Syntax

**Decision**: `sort=-field` minus prefix convention.

```
GET /invoices?sort=-created_at                      ← DESC
GET /invoices?sort=billing_month,-total_amount      ← Multi-sort (tuần tự priority)
```

**Rules**:
- **Default sort per endpoint**: declared trong OpenAPI spec. Missing `sort` → apply default.
- **Whitelist**: mỗi endpoint declare sortable fields (chỉ field có index). Undeclared → 400 `UNKNOWN_SORT_FIELD`.
- **Max fields per request**: 3 (prevent abuse).

**Default sort registry**:

| Endpoint | Default |
|---|---|
| `/invoices` | `-created_at` |
| `/tenants` | `name` |
| `/rooms` | `display_name` |
| `/leases` | `-start_date` |
| `/payments` | `-paid_at` |
| `/meter-readings` | `-reading_date` |
| `/notifications` | `-created_at` |
| `/properties` | `name` |
| `/occupants` | `moved_in_date` |
| `/services` | `name` |

### D4 — Search

**Decision**: No dedicated search endpoint MVP — use filter `__contains` / `__startswith`.

Phase 2 scale (100 phòng/Landlord) → Postgres `ILIKE` đủ nhanh. Migration path: v1.x/v2.x thêm `/api/v1/search/*` với full-text khi scale lớn — không đụng filter pattern.

**Phase 4 optimization flag**: nếu `ILIKE '%X%'` chậm, thêm `pg_trgm` GIN index:
```sql
CREATE INDEX idx_tenants_name_trgm ON tenants USING gin (name gin_trgm_ops);
```

---

## 5. Error Handling (Group E)

### E1 — Error Response Schema

**Decision**: Custom structured error (không RFC 7807).

**Shape** (all errors):
```json
{
  "error": {
    "code": "ERROR_CODE_ENUM",
    "message": "Human-readable English message",
    "request_id": "req_abc123",
    "details": { ... }                 // Optional
  }
}
```

**Content-Type**: `application/json` (không `application/problem+json`).

**Field semantics**:

| Field | Type | Required | Semantics |
|---|---|---|---|
| `error.code` | string (UPPER_SNAKE_CASE) | ✅ | Stable API contract. Client switch case trên field này. |
| `error.message` | string | ✅ | English, concise, may contain dynamic info. **Không stable wording** — client không parse. i18n ở frontend dựa trên `code`. |
| `error.request_id` | string | ✅ | Match response header `X-Request-Id`. Dùng debug. |
| `error.details` | object \| array | ⚠️ optional | Shape varies theo error type. Validation = array, business = object. |

### E2 — HTTP Status Code Mapping

| Status | Semantic | RMS Use Cases |
|---|---|---|
| 400 Bad Request | Malformed request (parse fail) | Invalid JSON body, wrong `Content-Type` |
| 401 Unauthorized | Auth missing/invalid | No token, expired, invalid signature, user inactive |
| 403 Forbidden | Auth OK, role denied | Tenant cố PATCH property, Landlord cố access admin |
| 404 Not Found | Resource không tồn tại OR ownership denied | GET/PATCH/action trên resource không own (ownership = 404 rule) |
| 409 Conflict | Valid request, invalid state | Void invoice đã void, archive tenant có unpaid invoices, duplicate invoice lease+month |
| 422 Unprocessable Entity | Validation fail (format, business rule input) | Email format sai, billing_day > 28, weak password |
| 429 Too Many Requests | Rate limit exceeded | (Phase 4 flag — password reset throttle) |
| 500 Internal Server Error | Unexpected bug | Exception không handle (log + generic message) |

**Edge cases chốt**:

- **Ownership denied**: 404, không 403 (information leakage protection)
- **Invalid state action** (void-already-voided): 409, không 422
- **Missing required field**: 422 (body parse được, chỉ validation fail)
- **Malformed JSON**: 400 (không parse được)

### E3 — Validation Error Shape (Pydantic Normalize)

**Decision**: Custom FastAPI exception handler convert Pydantic errors → E1 shape.

**Pydantic default** (phải override):
```json
{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}
```

**Normalized shape** (E1 compliant):
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "req_abc",
    "details": [
      {
        "field": "email",
        "error": "Invalid email format",
        "code": "value_error.email"
      },
      {
        "field": "billing_day",
        "error": "Ensure this value is less than or equal to 28",
        "code": "value_error.number.not_le"
      }
    ]
  }
}
```

**`details[].field` format**:
- Root body field: `email`
- Nested: dotted path — `lease.start_date`, `line_items.0.amount`
- Query: prefix — `query.limit`
- Path: prefix — `path.id`
- Header: prefix — `header.authorization`

**Business validation** (service layer, không Pydantic):

```json
{
  "error": {
    "code": "ROOM_HAS_ACTIVE_LEASE",
    "message": "Cannot archive room with active lease",
    "request_id": "req_abc",
    "details": {
      "room_id": "abc",
      "active_lease_id": "xyz"
    }
  }
}
```

`details` = object (không array) cho business errors.

---

## 6. Special Operations (Group F)

### F1 — Preview-Commit Pattern (Invoice Batch)

**Decision**: Two-step stateless endpoints.

**Preview** (compute, no persist):
```http
POST /api/v1/properties/{pid}/invoices/preview
{
  "billing_month": "2026-05",
  "exclude_lease_ids": []
}

Response 200:
{
  "data": [
    {
      "lease_id": "abc",
      "room_display_name": "P101",
      "tenant_name": "Nguyen Van A",
      "total_amount": 2500000,
      "line_items": [
        {"type": "rent", "description": "...", "amount": 2000000},
        {"type": "service", "description": "Điện 120kWh", "amount": 400000}
      ],
      "warnings": ["Meter reading for 'Điện' missing"]
    }
  ],
  "summary": {
    "total_invoices": 8,
    "total_amount": 18500000,
    "excluded_count": 2,
    "warning_count": 1
  }
}
```

**Commit** (persist):
```http
POST /api/v1/properties/{pid}/invoices
{
  "billing_month": "2026-05",
  "exclude_lease_ids": ["lease-to-skip-uuid"]
}

Response 201:
{
  "data": [...created invoices...],
  "summary": {"created_count": 7, "skipped_count": 1}
}
```

**Stateless rationale**: Client gửi lại `exclude_lease_ids` ở cả preview + commit. Không session state phía server (simple, scalable).

**Trade-off**: Data có thể đổi giữa preview và commit (reading mới được thêm, lease terminated). Acceptable — server return actual result, client reconcile nếu cần.

**Individual mode** (single lease):
```http
POST /api/v1/leases/{lid}/invoices/preview
POST /api/v1/leases/{lid}/invoices
```

Cho edge cases: fix 1 invoice riêng, generate invoice cuối khi terminate lease.

### F2 — Void & Recreate Pattern

**Decision**: Two separate endpoints, client orchestrate, non-atomic.

**Step 1 — Void**:
```http
POST /api/v1/invoices/{id}/void
{
  "reason": "wrong_meter_reading",
  "note": "Meter reading was entered incorrectly"
}

Response 200: {full voided invoice}
```

**Step 2 — Recreate** (usually preview + commit):
```http
POST /api/v1/properties/{pid}/invoices/preview
POST /api/v1/leases/{lid}/invoices
```

**Rationale cho client orchestration**:
- **Composability**: void có thể đi lẻ (không phải lúc nào cũng recreate)
- **Explicit audit trail**: 2 events riêng (void + create)
- **Error recovery**: nếu recreate fail, void vẫn còn — client decide
- **Simplicity**: không có compound action endpoint

**Atomicity trade-off**: Void OK → recreate fail → state "invoice voided, chưa recreate". Acceptable — Landlord thấy status, retry recreate.

**Frontend UX guidance**:
1. User click "Sửa hoá đơn" → UI dialog "Không thể sửa. Hủy + tạo lại?"
2. User confirm + nhập reason
3. Client call `POST /invoices/{id}/void`
4. Client redirect preview page với `lease_id` + `billing_month`
5. User điều chỉnh (fix reading upstream nếu cần) + commit
6. Invoice mới được tạo

### F3 — Batch Operations (Meter Readings)

**Decision**: All-or-nothing transaction, single endpoint.

```http
POST /api/v1/properties/{pid}/meter-readings
{
  "reading_date": "2026-05-01",
  "readings": [
    {"service_id": "dien-uuid", "room_id": "p101-uuid", "value": 1234, "note": ""},
    {"service_id": "dien-uuid", "room_id": "p102-uuid", "value": 5678, "note": ""},
    {"service_id": "nuoc-uuid", "room_id": null, "value": 999, "note": "Shared meter"}
  ]
}

Response 201:
{
  "data": [...created readings...],
  "summary": {
    "created_count": 3,
    "warning_count": 1,
    "warnings": [
      {"index": 0, "type": "value_lower_than_previous", "message": "Reading 1234 < previous 1250"}
    ]
  }
}
```

**Semantic**:
- **All-or-nothing**: 1 reading fail → rollback batch, return 422. Không partial success.
- **Errors** (reject batch): invalid `service_id`, invalid `room_id`, `value < 0`
- **Warnings** (accept batch): `value < previous_value`, gap > 45 days since last reading
- **Batch size limit**: max 100 readings (covers Phase 2 max property size)

**Individual CRUD** (C3 dual pattern):
```http
GET    /api/v1/meter-readings/{id}
PATCH  /api/v1/meter-readings/{id}
DELETE /api/v1/meter-readings/{id}
```

Cho sửa reading riêng lẻ (US-071/072).

### F4 — Wizard Multi-step (Promote Occupant)

**Decision**: Single atomic endpoint. Wizard = client UI concern.

```http
POST /api/v1/occupants/{id}/promote
{
  "effective_date": "2026-05-15",
  "tenant_info": {
    "name": "Nguyen Van A",
    "phone": "0901234567",
    "email": "a@example.com",
    "id_card_number": "..."
  }
}

Response 200:
{
  "new_tenant": {
    "id": "new-tenant-uuid",
    "name": "Nguyen Van A",
    "promoted_from_occupant_id": "old-occupant-uuid",
    ...
  },
  "updated_occupant": {
    "id": "old-occupant-uuid",
    "moved_out_date": "2026-05-15"
  },
  "updated_lease": {
    "id": "...",
    "tenant_id": "new-tenant-uuid",
    "previous_tenant_id": "previous-representative-uuid"
  }
}
```

**Why single-step**:
- **Atomicity**: 3 changes (occupant.moved_out_date, new tenant, lease.tenant_id) phải trong 1 transaction
- **Wizard = UI concern**: 3 screens client side, 1 endpoint server side
- **Simple**: 1 validation, 1 audit log entry
- **Error handling**: fail → nothing changed, no cleanup

**Validation rules (Phase 4)**:
- Occupant phải active (`moved_out_date IS NULL`)
- Occupant thuộc lease active
- `effective_date >= occupant.moved_in_date`
- `effective_date <= lease.end_date`
- `phone` unique per landlord (active tenants only)

**Error codes**:
- 409 `OCCUPANT_ALREADY_MOVED_OUT`
- 409 `DUPLICATE_TENANT_PHONE`
- 422 `INVALID_EFFECTIVE_DATE`

---

## 7. Convention Reference

### URL Patterns

| Pattern | Rule | Example |
|---|---|---|
| Collection | Plural kebab-case | `/api/v1/meter-readings` |
| Item | `{collection}/{id}` | `/api/v1/rooms/{id}` |
| Singleton own | `/users/me` | `GET /api/v1/users/me` |
| List children | Nested 1 level | `GET /api/v1/properties/{pid}/rooms` |
| Create with parent | Nested | `POST /api/v1/rooms/{rid}/leases` |
| Cross-parent filter | Flat + query | `GET /api/v1/invoices?tenant_id=X` |
| Action | `POST {item}/{verb}` | `POST /api/v1/invoices/{id}/void` |

### HTTP Methods

| Method | Usage |
|---|---|
| GET | Retrieve (list or item) |
| POST | Create OR action |
| PATCH | Partial update (preferred over PUT) |
| DELETE | Hard delete (rare — most "deletes" are `archive` action) |

**Không dùng PUT** cho MVP — PATCH đủ cho update pattern. PUT nếu cần idempotent replace whole resource.

### Query Parameter Conventions

| Purpose | Syntax | Example |
|---|---|---|
| Pagination | `limit`, `offset` | `?limit=20&offset=40` |
| Filter equals | `field=value` | `?status=unpaid` |
| Filter operator | `field__operator=value` | `?billing_month__gte=2026-01-01` |
| Filter IN | `field__in=v1,v2` | `?status__in=unpaid,partial` |
| Sort | `sort=[-]field[,...]` | `?sort=-created_at,name` |

### Headers

**Request**:

| Header | Required | Notes |
|---|---|---|
| `Content-Type` | ✅ POST/PATCH | Must be `application/json` |
| `Authorization` | ✅ Protected endpoints | `Bearer <jwt>` |
| `X-Request-Id` | ⚠️ Optional | Client-provided trace ID (server fallback generate) |
| `Accept-Language` | ⚠️ Optional | Future i18n (không MVP) |

**Response**:

| Header | When | Notes |
|---|---|---|
| `Content-Type` | Always | `application/json; charset=utf-8` |
| `X-Request-Id` | Always | Echo/generated |
| `WWW-Authenticate` | 401 responses | `Bearer` |
| `Set-Cookie: refresh_token=...` | Login/refresh/logout | HttpOnly, Secure, SameSite=Strict, Path scope |

### Response Envelopes

**List**:
```json
{
  "data": [...],
  "pagination": {"limit": 20, "offset": 0, "total": 127}
}
```

**Item** (single resource):
```json
{
  ...resource fields...
}
```

No envelope cho item response — resource trực tiếp.

**Error**:
```json
{"error": {"code": "...", "message": "...", "request_id": "...", "details": ...}}
```

**Action success** (returns resource):
```json
{...full resource after action...}
```

**Batch action**:
```json
{
  "data": [...],
  "summary": {...}
}
```

---

## 8. Error Code Registry

Stable API contract. Codes UPPER_SNAKE_CASE. Namespace: `<resource>_<condition>` optional.

### Generic

| Code | Status | Notes |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Umbrella cho Pydantic schema fail |
| `NOT_FOUND` | 404 | Resource không tồn tại OR ownership denied |
| `PERMISSION_DENIED` | 403 | Role không cho phép |
| `MALFORMED_REQUEST` | 400 | Body parse fail |
| `INVALID_CONTENT_TYPE` | 400 | Wrong Content-Type header |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Request non-JSON |
| `RATE_LIMIT_EXCEEDED` | 429 | (Phase 4) |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected bug |
| `UNKNOWN_FILTER_FIELD` | 400 | Filter field không trong whitelist |
| `UNKNOWN_SORT_FIELD` | 400 | Sort field không trong whitelist |

### Auth-related

| Code | Status | Notes |
|---|---|---|
| `AUTHENTICATION_REQUIRED` | 401 | Missing Authorization header |
| `TOKEN_INVALID` | 401 | Malformed, wrong signature |
| `TOKEN_EXPIRED` | 401 | JWT `exp` past |
| `USER_INACTIVE` | 401 | User archived |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `INVALID_REFRESH_TOKEN` | 401 | Refresh token unknown/invalid |
| `REFRESH_TOKEN_EXPIRED` | 401 | Refresh token TTL past |
| `REFRESH_TOKEN_REUSED` | 401 | Rotation detection — revoke family |

### Invite / Password Reset

| Code | Status | Notes |
|---|---|---|
| `INVALID_INVITE_TOKEN` | 400 | Unknown token |
| `INVITE_TOKEN_USED` | 400 | `used_at IS NOT NULL` |
| `INVITE_TOKEN_EXPIRED` | 400 | TTL 7d past |
| `INVALID_RESET_TOKEN` | 400 | Unknown token |
| `RESET_TOKEN_USED` | 400 | `used_at IS NOT NULL` |
| `RESET_TOKEN_EXPIRED` | 400 | TTL 1h past |
| `WEAK_PASSWORD` | 422 | Không match policy |
| `CONSENT_REQUIRED` | 422 | `consent_pii` không true |

### Business — Invoice

| Code | Status | Notes |
|---|---|---|
| `INVOICE_ALREADY_VOIDED` | 409 | Void invoice đã void |
| `INVOICE_IMMUTABLE` | 409 | Cố PATCH invoice (không phải status/payment-related) |
| `DUPLICATE_INVOICE` | 409 | Trùng `(lease_id, billing_month)` non-voided |
| `INVALID_BILLING_MONTH` | 422 | Future month hoặc invalid format |
| `MISSING_METER_READING` | 409 | Generate invoice nhưng thiếu reading per_meter service |

### Business — Lease

| Code | Status | Notes |
|---|---|---|
| `LEASE_ALREADY_TERMINATED` | 409 | Terminate lease đã terminated |
| `ROOM_HAS_ACTIVE_LEASE` | 409 | Create lease khi room có active lease |
| `INVALID_LEASE_DATES` | 422 | `end_date < start_date` |
| `DEPOSIT_ALREADY_SETTLED` | 409 | Settle deposit đã settle |

### Business — Tenant / Occupant

| Code | Status | Notes |
|---|---|---|
| `DUPLICATE_TENANT_PHONE` | 409 | Phone trùng trong active tenants của landlord |
| `DUPLICATE_TENANT_EMAIL` | 409 | Email trùng (nếu có) |
| `TENANT_HAS_ACTIVE_LEASE` | 409 | Archive tenant đang có active lease |
| `TENANT_HAS_UNPAID_INVOICES` | 409 | Archive tenant còn unpaid invoice |
| `TENANT_ALREADY_ARCHIVED` | 409 | Archive tenant đã archived |
| `TENANT_ANONYMIZED` | 409 | Reactivate tenant đã anonymized (data gone) |
| `OCCUPANT_ALREADY_MOVED_OUT` | 409 | Promote occupant đã moved_out |
| `INVALID_EFFECTIVE_DATE` | 422 | Promote date không hợp lệ |

### Business — Room / Property / Service

| Code | Status | Notes |
|---|---|---|
| `ROOM_HAS_UNPAID_INVOICES` | 409 | Archive room còn unpaid |
| `DUPLICATE_ROOM_NAME` | 409 | Room display_name trùng trong property |
| `PROPERTY_HAS_ROOMS` | 409 | Hard delete property còn room |
| `INVALID_SERVICE_CONFIG` | 422 | billing_type=per_meter nhưng thiếu unit/scope |
| `SERVICE_ALREADY_ACTIVE` | 409 | Activate service đã active |
| `SERVICE_ALREADY_INACTIVE` | 409 | Deactivate service đã inactive |

### Business — Payment

| Code | Status | Notes |
|---|---|---|
| `INVOICE_NOT_PAYABLE` | 409 | Payment vào invoice voided |
| `PAYMENT_OVERPAY` | 422 | Total payments > invoice total |
| `INVALID_PAYMENT_DATE` | 422 | Future date |

---

## 9. Future Considerations

### Deferred cho v1.x / v2.x (không implement MVP)

#### Pagination
- **Cursor-based** khi scale > 10K rows per collection. Response shape đã chuẩn bị — thêm `next_cursor` field, backward compatible.

#### Search
- **Dedicated endpoints** `/api/v1/search/{resource}?q=...` khi cần full-text ranking / cross-resource search.
- **Postgres pg_trgm GIN index** optimization khi `ILIKE` chậm.

#### Idempotency
- **Header `Idempotency-Key`** cho actions quan trọng (void, terminate, promote). Server cache response 24h theo key.

#### File handling
- **Upload**: `multipart/form-data`, endpoint per resource — `POST /{resource}/{id}/attachments`
- **Download**: endpoint raw binary — `GET /invoices/{id}/pdf`, `GET /rooms/{id}/photos/{photo_id}`

#### Exports
- Dedicated zone `/api/v1/exports/*`:
  - `GET /api/v1/exports/tenants.csv`
  - `GET /api/v1/exports/invoices.xlsx?billing_month__gte=...`
  - `GET /api/v1/exports/revenue.xlsx?year=2026`

#### WebSocket
- `/ws/*` zone khi có real-time requirements (notifications push, technician live tracking v2.x).

#### Admin / Staff
- `/api/v1/admin/*` zone khi có Staff role.

#### Webhooks
- `/webhooks/*` zone cho incoming webhooks (Zalo OA, payment gateway).

#### Rate limiting
- `slowapi` in-memory middleware, Phase 4 implement:
  - Password reset request: 3/hour/IP, 1/5min/email
  - Login: 5/min/IP
  - Invite verify/accept: 5/min/IP
- Error: 429 `RATE_LIMIT_EXCEEDED`

#### Versioning v2
- Add `/api/v2/*` router parallel với `/api/v1/*`
- Deprecation policy: v1 support tối thiểu 6 tháng sau v2 GA
- Response header `Deprecation: true` + `Sunset: <date>` cho deprecated endpoints

#### i18n
- Response messages English only MVP
- Future: `Accept-Language` header → localized `error.message` (frontend vẫn fallback `error.code` mapping)

#### OpenAPI enhancements
- Examples block cho mỗi endpoint (Phase 4)
- `x-code-samples` extension cho code examples (Python, JavaScript, curl)
- API changelog trong `/docs/04-api/CHANGELOG.md`

---

## Appendix A — References

- `PHASE2-SUMMARY.md` — Product requirements
- `docs/03-database/erd.mmd` + `erd-reference.md` — Schema
- `docs/decisions/ADR-0005-*.md` — RBAC strategy
- `docs/decisions/ADR-0007-*.md` — JWT + refresh token design
- RFC 6750 — Bearer Token Usage
- RFC 7807 — Problem Details (considered, not adopted)
- Stripe API docs — reference for cursor pagination, action endpoints
- GitHub REST API docs — reference for action endpoints, nesting

---

## Appendix B — Promote to ADR candidates

Cuối Phase 3, review các decisions và promote thành ADR-0008+:

| Candidate | Reason to promote |
|---|---|
| B1+B2 combined (Token delivery) | High reversal cost — đụng toàn bộ auth flow, frontend storage, mobile client. Worth ADR. |
| D1 (Offset pagination) | Cross-cutting tất cả list endpoints. Migration path có giá trị document. |
| E1 (Error schema) | Impact mọi endpoint response shape. Changing = breaking API. |
| F1 (Preview-commit pattern) | Business-critical pattern, unique cho invoice flow. |

Convention-level decisions (naming, query syntax, nesting rules, action URL format) giữ ở file này.

---

**End of API Design Decisions. Ready for S4.2 — Resource → Endpoint Mapping.**
