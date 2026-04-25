# ADR-0007: Auth & Token Strategy

> **Status**: Accepted
> **Date**: 2026-04-18
> **Deciders**: Bảo, Claude (as Senior Architect)
> **Supersedes**: Phase 2 Nhóm 1 placeholder ("token rotation TBD Phase 3")

---

## Context

Phase 2 (Nhóm 1 — Auth) xác định JWT access token (60min) + refresh token
(7 ngày). Phase 3 cần chốt chi tiết:

- Rotation strategy (Batch 2 Decision #1 đã quyết: rotation + reuse detection)
- Storage server-side và client-side
- Invite token và password-reset token — share cơ chế với refresh token
  hay tách riêng?
- JWT signing algorithm + secret management
- Logout behavior

Constraints:

1. **App có data tài chính** (Invoice, Payment) → security không thể cắt
   góc.
2. **MVP monolith** + tương lai SPA + native mobile (v1.x).
3. **Solo dev** → infra phải đơn giản, tránh thêm dependency (không Redis MVP).
4. **Forward-compat với ADR-0005** (RBAC) — code không được đọc `role`
   trực tiếp từ JWT claims để authorization, chỉ dùng cho UX hint.

---

## Options Considered

### Option 1: Stateless JWT cho access, stateful refresh (recommend)

- Access token: JWT tự contain (`sub`, `role`, `iat`, `exp`, `jti`),
  server không lưu.
- Refresh token: opaque random string, hashed lưu DB, có thể revoke.

**Pros**:
- Access token verify nhanh (không query DB mỗi request)
- Refresh token có thể kill được (logout, theft detection)
- Scale horizontal dễ (không sticky session)
- Industry standard pattern

**Cons**:
- Access token bị lộ → tối đa 60min mới chết (chấp nhận với TTL ngắn)

### Option 2: Stateful cả hai

Cả access và refresh đều lưu DB, mỗi request query token table.

**Pros**: Revoke ngay lập tức.

**Cons**: Query DB mỗi request → overhead cao. Vô hiệu hoá lợi thế JWT.

### Option 3: Session-based, bỏ JWT

Dùng session cookie + Redis store.

**Pros**: Đơn giản, revoke dễ.

**Cons**:
- Không phù hợp SPA + mobile tương lai (mobile không cookie nice)
- Yêu cầu Redis ngay MVP (thêm dependency)
- Solo dev không muốn maintain Redis MVP

---

## Decision

**Adopt Option 1**: stateless JWT access token + stateful opaque refresh
token với rotation chain và reuse detection.

---

## Token Specs

### Token catalogue

| Token | Type | TTL | Storage server | Storage client |
|---|---|---|---|---|
| Access | JWT (HS256) | 60 min | Không lưu | In-memory (SPA) |
| Refresh | Opaque random (SHA-256 hash trong DB) | 7 ngày | `refresh_tokens` table | HttpOnly cookie (web) / native secure storage (mobile v1.x) |
| Invite | Opaque random (SHA-256 hash trong DB) | 7 ngày | `invite_tokens` table | URL param (1 lần qua email) |
| Password reset | Opaque random (SHA-256 hash trong DB) | 1 giờ | `password_reset_tokens` table | URL param (1 lần qua email) |

### JWT access token claims

```json
{
  "sub": "<user_id_uuid>",
  "role": "landlord",
  "iat": 1714000000,
  "exp": 1714003600,
  "jti": "<token_unique_id>"
}
```

**Claims rationale**:
- `sub`: user_id (standard JWT claim)
- `role`: single role per user trong MVP. Forward-compat note dưới đây.
- `iat`: issued_at (debugging, audit)
- `exp`: expiration (60 min)
- `jti`: unique token ID (debugging, future revocation list nếu cần)

**Không include**: email, name, phone, hay PII khác. Cần → query từ
`user_id`. Lý do: token có thể leak qua logs, browser history, error
reports → minimize PII surface area.

### CRITICAL Rule (forward-compat với ADR-0005)

**Code backend KHÔNG được đọc `role` trực tiếp từ JWT claims để
authorization**.

```python
# ❌ WRONG
def has_permission(jwt_payload):
    return jwt_payload["role"] == "landlord"

# ✅ CORRECT
def has_permission(user_id):
    roles = get_user_roles(user_id)  # Query DB or cache
    return "landlord" in roles
```

**Lý do**: 
- v1.x sẽ thêm Manager role → 1 user có thể có multi-role.
- JWT `role` claim chỉ cho UX hint (render UI cho đúng menu) — không phải
  source of truth permission.
- Source of truth = `user_roles` table (Phase 4 implement).

---

## Refresh Token Rotation

### Mechanism

```
Login → tạo refresh token R1 (family_id=F1, replaced_by=null)
         ↓
Client gọi /auth/refresh với R1
         ↓
Server validates R1, tạo R2 (family_id=F1, replaced_by=null)
         Set R1.revoked_at = NOW(), R1.replaced_by_token_id = R2.id
         Return new access + R2
         ↓
Client gọi /auth/refresh với R2 → R3 ...
```

### Reuse Detection (theft scenario)

```
Attacker steals R1 (chưa được rotate)
Attacker dùng R1 → server cấp R2 cho attacker
Legitimate user vẫn có R1 ở browser
Legitimate user gọi /auth/refresh với R1 (now revoked)
Server detects: R1 đã có replaced_by_token_id (= R2) NHƯNG vẫn được dùng
                → REUSE DETECTED
                → Revoke TOÀN BỘ family F1 (R1, R2, R3, ...)
                → Both attacker and user forced to re-login
```

### Family ID

- Mỗi login tạo `family_id` mới (UUID).
- Tất cả refresh tokens sinh từ chain rotation cùng login → cùng family_id.
- Detection mechanism: revoke whole family khi reuse detected.
- Logout = revoke chỉ token hiện tại (không revoke family — cho phép user
  logout 1 device, vẫn login device khác).

---

## Schema (final, implemented Phase 3 Deliverable #4)

### `refresh_tokens` table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    family_id UUID NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    revoked_reason VARCHAR(50) NULL,  -- 'logout', 'rotation', 'reuse_detected'
    rotated_to_id UUID NULL REFERENCES refresh_tokens(id),
    user_agent VARCHAR(255) NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_family_id ON refresh_tokens(family_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
```

### `invite_tokens` table

```sql
CREATE TABLE invite_tokens (
    id UUID PRIMARY KEY,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    invited_email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE NULL,
    created_by_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_invite_tokens_token_hash ON invite_tokens(token_hash);
CREATE INDEX idx_invite_tokens_tenant_id ON invite_tokens(tenant_id);
```

### `password_reset_tokens` table

```sql
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY,
    token_hash VARCHAR(128) NOT NULL UNIQUE,
    user_id UUID NOT NULL REFERENCES users(id),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_password_reset_tokens_token_hash ON password_reset_tokens(token_hash);
```

### Why 3 tables, not 1 generic `tokens` table

3 tables tách riêng thay vì 1 bảng `tokens` generic với `purpose` enum.

**Reasoning**:
- **Ngữ nghĩa khác**: refresh = session, invite = onboarding, reset = recovery
- **Query pattern khác**: refresh query nhiều (mỗi refresh request);
  invite/reset query rare (1 lần per flow)
- **Retention policy khác**: refresh = 7 days TTL; invite = 7 days; reset = 1 hour
- **Schema khác**: refresh có `family_id` + `rotated_to_id`; invite có
  `tenant_id` + `invited_email`; reset có chỉ `user_id`
- Không premature-generalize. YAGNI.

---

## Algorithms & Crypto

### JWT signing

- **Algorithm**: **HS256** (HMAC SHA-256)
- **Secret**: 256-bit random từ env var `JWT_SECRET_KEY`
- **Generation**: `openssl rand -hex 64` (64 bytes hex = 256 bit entropy)

**Why HS256 không RS256**:
- MVP monolith: 1 backend service ký + verify
- Không có microservices cần verify với public key
- HS256 đơn giản hơn (không quản lý keypair)
- Chuyển RS256 future nếu split services (low effort)

### Opaque token generation

- Library: Python `secrets.token_urlsafe(32)` 
- 32 bytes = 256 bit entropy, URL-safe base64 encoded
- Resulting string: ~43 chars, e.g. `xK_9pQ2vR8...`

### Hash storage

- **Algorithm**: SHA-256 (single round)
- **Why không bcrypt**:
  - Token = random 256-bit entropy → not bruteforce-able
  - bcrypt slow (~100ms) → unnecessary cost cho mỗi auth check
  - bcrypt designed cho weak passwords; tokens already strong

### Password hashing (separate from tokens)

- **Algorithm**: **bcrypt** (cost factor 12) qua `passlib`
- Stored ở `users.password_hash`
- Khác token hashing — passwords cần slow hash chống bruteforce

---

## Endpoint Behaviors

### `POST /api/v1/auth/login`

```
Input: { email, password }
Validate: bcrypt verify password, account active
Generate: 
  - access_token (JWT, 60min)
  - refresh_token_plain = secrets.token_urlsafe(32)
  - refresh_token_hash = sha256(refresh_token_plain)
  - family_id = uuid4()
Insert refresh_tokens (token_hash=hash, family_id=family_id, ...)
Response 200:
  Set-Cookie: refresh_token=<plain>; HttpOnly; Secure; SameSite=Strict; 
              Path=/api/v1/auth/refresh; Max-Age=604800
  Body: { access_token, token_type: "Bearer", expires_in: 3600, user: {...} }
```

### `POST /api/v1/auth/refresh`

```
Input: refresh_token from cookie OR body
Hash incoming token, query refresh_tokens by token_hash
Validate:
  - Token exists
  - revoked_at IS NULL
  - expires_at > NOW()
  - rotated_to_id IS NULL  ← critical: detect reuse
If rotated_to_id IS NOT NULL → REUSE DETECTED:
  - Set revoked_at = NOW(), revoked_reason = 'reuse_detected' on entire family_id
  - Return 401 REFRESH_TOKEN_REUSED
If valid:
  - Generate new refresh_token_plain + hash
  - Insert new refresh_tokens row (same family_id)
  - Update OLD: revoked_at = NOW(), revoked_reason = 'rotation', 
                rotated_to_id = NEW.id
  - Generate new access_token (JWT)
  - Return 200 with new tokens (same cookie pattern)
```

### `POST /api/v1/auth/logout`

```
Input: refresh_token from cookie
Hash, query, set revoked_at = NOW(), revoked_reason = 'logout'
Clear cookie (Max-Age=0)
Return 204
Note: Access token still valid up to 60min (stateless trade-off)
      "Logout all devices" = revoke entire family. v1.x feature.
```

### `POST /api/v1/auth/invite/verify` and `/accept`

Same opaque pattern, single-use (set `used_at` after accept).

### `POST /api/v1/auth/password-reset/request` and `/confirm`

Same opaque pattern, single-use, 1-hour TTL.
**Enumeration-safe**: `/request` always returns 200 regardless of email
existence (don't leak account presence).

---

## Logout Behavior Trade-offs

### Access token after logout (60min window)

**Decision**: Accept the trade-off — access token vẫn valid sau logout
trong tối đa 60 phút.

**Why acceptable**:
- TTL ngắn (60 min) → window nhỏ
- Real attack scenario rare: attacker phải có token + know user logged out
  + act quickly
- Mitigation alternatives đắt: revocation list (Redis) hoặc stateful access
  → vô hiệu hoá lợi thế stateless

**When unacceptable** (override Phase 5+):
- High-risk action (delete account, change password, large payment) → 
  re-authenticate (require password again) thay vì rely on token alone
- Implement token revocation list nếu compliance requirement

### "Logout all devices"

**MVP**: Không implement. User chỉ logout device hiện tại.

**v1.x**: Add via revoke entire `family_id` của tất cả tokens user.
UI: "Đăng xuất khỏi tất cả thiết bị" trong Settings.

---

## Consequences

### Positive

- **Theft mitigation**: Refresh token cướp → attacker có tối đa 1 lần dùng
  trước khi reuse detection triggers.
- **Stateless access**: Backend horizontal scaling không cần sticky session
  hay shared state.
- **Reusable token pattern**: Invite/password-reset dùng cùng opaque +
  hash + TTL pattern → code share.
- **No Redis dependency MVP**: Đơn giản infrastructure.
- **Industry standard**: Pattern OAuth 2.0 RFC 8725 recommendations.

### Negative

- **Access token compromise window**: 60 min sống sau leak. Acceptable.
- **Rotation client complexity**: SPA phải handle refresh token mới mỗi
  call. Wrap trong axios/ky interceptor (ADR-0008 frontend stack).
- **DB writes**: Mỗi refresh = 1 INSERT + 1 UPDATE. Volume thấp (~mỗi
  60 min/user). Không lo.
- **Reuse detection false positive**: Network glitch → client retries
  với same token → false reuse. Mitigation: client-side dedup, retry
  with backoff.

### Neutral

- **JWT_SECRET rotation**: Chưa plan auto-rotation. Manual rotation
  procedure documented ở `secrets-management.md`. Consequence của
  rotate: tất cả existing access tokens invalid → users get 401, force
  refresh, but refresh tokens still valid → seamless (refresh creates
  new access token với new secret). Acceptable.
- **Multi-role forward-compat**: Single role MVP, abstracted via
  `get_user_roles()`. v1.x extension low-cost.

---

## Implementation Notes (for Phase 4)

### Service layer pattern

```python
# app/services/auth_service.py

class AuthService:
    def login(self, email: str, password: str) -> TokenPair:
        user = self.user_repo.get_by_email(email)
        if not user or not bcrypt.verify(password, user.password_hash):
            raise InvalidCredentialsError()
        return self._issue_token_pair(user, family_id=uuid4())
    
    def refresh(self, refresh_token_plain: str) -> TokenPair:
        token_hash = sha256(refresh_token_plain.encode()).hexdigest()
        rt = self.refresh_repo.get_by_hash(token_hash)
        
        if rt is None:
            raise InvalidTokenError()
        if rt.revoked_at:
            raise InvalidTokenError()
        if rt.expires_at < datetime.utcnow():
            raise TokenExpiredError()
        if rt.rotated_to_id:
            # REUSE DETECTED — revoke entire family
            self.refresh_repo.revoke_family(
                family_id=rt.family_id, 
                reason="reuse_detected"
            )
            raise TokenReusedError()
        
        # Rotate: issue new, revoke old
        new_pair = self._issue_token_pair(
            user_id=rt.user_id, 
            family_id=rt.family_id
        )
        self.refresh_repo.mark_rotated(
            token_id=rt.id, 
            new_token_id=new_pair.refresh_token_id
        )
        return new_pair
```

### FastAPI dependency injection

```python
# app/api/deps.py

async def get_current_user(
    authorization: str = Header(...),
    user_repo: UserRepo = Depends(),
) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    
    token = authorization[7:]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Invalid token")
    
    user_id = payload["sub"]
    user = user_repo.get(user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "User not active")
    
    return user

async def require_roles(*allowed_roles: str):
    """Permission check — uses get_user_roles, not JWT claim."""
    async def checker(user: User = Depends(get_current_user)):
        roles = get_user_roles(user.id)  # ← from DB, not JWT
        if not any(r in roles for r in allowed_roles):
            raise HTTPException(403, "Insufficient permissions")
        return user
    return checker
```

### Cookie config (CSRF-safe)

```python
response.set_cookie(
    key="refresh_token",
    value=refresh_token_plain,
    max_age=7 * 24 * 3600,
    httponly=True,
    secure=True,                    # HTTPS only
    samesite="strict",              # CSRF protection
    path="/api/v1/auth/refresh",    # Scope hẹp
)
```

### Daily cleanup (APScheduler — ADR-0002)

```python
@scheduler.scheduled_job("cron", hour=0, minute=10)
async def cleanup_expired_tokens():
    """Daily cron 00:10 UTC: hard-delete expired tokens."""
    cutoff = datetime.utcnow() - timedelta(days=30)
    
    # Refresh tokens: delete expired AND revoked > 30 days
    await refresh_repo.delete_where(
        or_(
            RefreshToken.expires_at < datetime.utcnow(),
            and_(
                RefreshToken.revoked_at < cutoff,
                RefreshToken.revoked_at.is_not(None),
            )
        )
    )
    
    # Invite + reset tokens: delete expired
    await invite_repo.delete_where(InviteToken.expires_at < datetime.utcnow())
    await reset_repo.delete_where(PasswordResetToken.expires_at < datetime.utcnow())
```

---

## Test Cases (cho Phase 4)

### Critical paths to test

1. **Happy path login**: email + correct password → tokens issued
2. **Wrong password**: 401, no tokens
3. **Refresh happy**: valid refresh → new pair, old revoked
4. **Refresh expired**: 401 with `REFRESH_TOKEN_EXPIRED`
5. **Refresh reuse**: use already-rotated token → entire family revoked +
   401 `REFRESH_TOKEN_REUSED`
6. **Concurrent refresh**: 2 requests with same token simultaneously →
   only 1 succeeds, other gets reuse detection (or 1 success + 1 retry)
7. **Logout**: token revoked, subsequent refresh = 401
8. **Access token expiry**: 60 min later → 401, must refresh
9. **Multiple devices**: user login từ 2 devices → 2 families, logout 1
   không kill device 2
10. **Invite flow**: verify → accept (auto-login) → token usable
11. **Password reset**: request (always 200) → confirm (sets new password,
    revokes ALL refresh tokens for that user)

---

## References

- Phase 2 Nhóm 1 (Auth) — 8 user stories US-001 đến US-008
- Batch 2 Decision #1 (rotation + reuse detection) — confirmed 2026-04-15
- ADR-0005 (RBAC strategy) — never read role from JWT for authorization
- ADR-0006 (Data retention) — `consent_pii` flag in invite accept flow
- OAuth 2.0 Security Best Current Practice: https://datatracker.ietf.org/doc/html/rfc8725
- OWASP JWT Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html
- API spec endpoints: `POST /api/v1/auth/{login,refresh,logout,invite/verify,invite/accept,password-reset/request,password-reset/confirm}`
- Models: `app/models/token.py` (3 token tables)

---

**ADR-0007 End.**
