# Secrets Management — RMS

> **Purpose**: Quy tắc quản lý secrets (credentials, tokens, keys) xuyên
> suốt các môi trường dev/CI/staging/production.
>
> **Audience**: Bảo + future contributors.
> **Last updated**: 2026-04-25

---

## Principles

1. **Never commit secrets to Git** — dùng `.gitignore`, pre-commit hook.
2. **Separate by environment** — staging key ≠ production key.
3. **Least privilege** — secret chỉ expose cho service cần.
4. **Rotate on leak** — suspect compromised → rotate ngay.
5. **Audit trail** — GitHub Secrets log "last updated by X at Y".

---

## Secret Inventory

### Development (local)

Location: `backend/.env` (gitignored).

```
DATABASE_URL=postgresql+psycopg://dev:dev@localhost:5433/rms_dev
JWT_SECRET_KEY=dev-secret-not-for-production
RESEND_API_KEY=<optional, or mock>
ENVIRONMENT=development
```

**Template**: `backend/.env.example` (committed, no real values).

### CI (GitHub Actions)

Location: GitHub repository secrets + environment secrets.

**Repository Secrets** (all workflows):

| Name | Source | Rotation |
|---|---|---|
| `GHCR_PULL_TOKEN` | Fine-grained PAT, scope `read:packages` | 90 days |
| `SLACK_WEBHOOK_URL` | Slack/Discord admin | On team change |

**Environment: staging**:

| Name | Source | Rotation |
|---|---|---|
| `SSH_HOST` | Hetzner IP | On VPS change |
| `SSH_USER` | VPS setup (usually `rms`) | Rarely |
| `SSH_PRIVATE_KEY` | `cat ~/.ssh/id_ed25519_staging` | 6 months |

**Environment: production**:

Same as staging but **different SSH key + IP**. **Never reuse staging key for prod**.

### Runtime (on VPS)

Location: `/opt/rms/<env>/.env` (mode 600).

```
BACKEND_IMAGE_TAG=production-latest

POSTGRES_DB=rms_prod
POSTGRES_USER=rms_user
POSTGRES_PASSWORD=<STRONG_32_CHAR>
DATABASE_URL=postgresql+psycopg://rms_user:${POSTGRES_PASSWORD}@postgres:5432/rms_prod

JWT_SECRET_KEY=<STRONG_64_CHAR_HEX>
JWT_ACCESS_TOKEN_TTL_MINUTES=60
JWT_REFRESH_TOKEN_TTL_DAYS=7

RESEND_API_KEY=<FROM_RESEND_DASHBOARD>
EMAIL_FROM_ADDRESS=noreply@rms-app.vn

ENVIRONMENT=production
```

### Backup encryption (R2)

Location: `/opt/rms/r2-credentials.env` (mode 600).

```
AWS_ACCESS_KEY_ID=<r2_token_id>
AWS_SECRET_ACCESS_KEY=<r2_token_secret>
R2_BUCKET=rms-backups
R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
```

---

## Generation Commands

### Strong password (Postgres user)

```bash
openssl rand -base64 32
# Example output: Kj9xP2mN5qR7vT3wY8zA1bC6dE4fG0hI
```

### JWT secret

```bash
openssl rand -hex 64
# 128 hex chars = 64 bytes of entropy
```

### SSH keypair

```bash
ssh-keygen -t ed25519 -C "rms-deploy-prod" -f ~/.ssh/id_ed25519_rms_prod
# No passphrase (automated deploys)
# Copy public key to VPS authorized_keys
# Copy private key content to GitHub Secret SSH_PRIVATE_KEY
```

---

## Rotation Procedures

### Rotate JWT secret

**Impact**: All users logged out (refresh tokens invalidated).

**When to rotate**:
- Suspect leak
- Key worked ≥ 1 year (preventive)

**Steps**:
1. Generate new secret: `openssl rand -hex 64`
2. Update `/opt/rms/production/.env` on VPS
3. Revoke all refresh tokens:
   ```sql
   UPDATE refresh_tokens 
   SET revoked_at = NOW(), revoked_reason = 'jwt_rotation';
   ```
4. Restart backend:
   ```bash
   docker compose restart backend
   ```
5. Communicate to users: "Vui lòng đăng nhập lại."

### Rotate Postgres password

**Impact**: Brief downtime (10-30s) while backend reconnects.

**Steps**:
1. Generate new password: `openssl rand -base64 32`
2. Connect Postgres:
   ```bash
   docker compose exec postgres psql -U rms_user rms_prod
   ALTER USER rms_user PASSWORD '<NEW_PASSWORD>';
   \q
   ```
3. Update `/opt/rms/production/.env` `POSTGRES_PASSWORD` + `DATABASE_URL`
4. Restart backend: `docker compose restart backend`

### Rotate SSH deploy key

**Impact**: None if done correctly.

**Steps**:
1. Generate new keypair on dev machine
2. Add NEW public key to VPS `authorized_keys` (keep old key too)
3. Update GitHub Secret `SSH_PRIVATE_KEY` with NEW private key
4. Trigger test deploy → verify new key works
5. Remove OLD public key from VPS `authorized_keys`

### Rotate GHCR token

**When**: Every 90 days (auto-expire with fine-grained PAT).

**Steps**:
1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained
2. Create new token:
   - Scope: `read:packages` + `write:packages`
   - Expire: 90 days
3. Update GitHub Secret `GHCR_PULL_TOKEN`
4. Update VPS docker login:
   ```bash
   ssh rms@<VPS_IP>
   echo "<NEW_TOKEN>" | docker login ghcr.io -u <username> --password-stdin
   ```
5. Revoke old token in GitHub settings

### Rotate Resend API key (email)

**Impact**: Emails temporarily fail until updated.

**Steps**:
1. Resend dashboard → Create new key
2. Update `/opt/rms/production/.env`
3. Restart backend: `docker compose restart backend`
4. Test: trigger invite email
5. Revoke old key in Resend

---

## Incident: Suspected Leak

### Level 1: Non-critical (staging secret)

1. Rotate secret immediately
2. Audit: who had access? when was last commit? git log?
3. Add post-mortem note

### Level 2: Critical (production secret)

1. **STOP** — do not deploy further until investigated
2. Rotate immediately per procedures above
3. Audit logs:
   - Nginx access log: `/var/log/nginx/access.log`
   - Docker logs: `docker compose logs backend --since 7d`
   - DB queries (if JWT leak): `audit_logs` table
4. Check for unauthorized access:
   ```sql
   SELECT * FROM audit_logs 
   WHERE created_at > NOW() - INTERVAL '7 days' 
   ORDER BY created_at DESC;
   ```
5. Notify users if PII accessed
6. Full post-mortem

### Level 3: Confirmed breach

1. Take service offline (nginx returns 503)
2. All Level 2 steps
3. Law enforcement if PII breach (VN Nghị định 13/2023)
4. Rebuild VPS from scratch if OS-level compromise suspected

---

## Do's and Don'ts

### DO

- ✅ Commit `.env.example` with placeholder values
- ✅ Use `openssl rand` for crypto secrets (not `uuidgen`, not passwords)
- ✅ Set `.env` file mode to 600 (`chmod 600 .env`)
- ✅ Use environment-scoped secrets in GitHub Actions
- ✅ Keep staging and production keys completely separate
- ✅ Document rotation date in team wiki
- ✅ Use fine-grained PATs (expire, scoped) over classic PATs

### DON'T

- ❌ Commit `.env`, `*.key`, `*.pem` files
- ❌ Paste secrets in Slack/Discord/email
- ❌ Log secret values (even masked — grep can find)
- ❌ Reuse passwords across services
- ❌ Put secrets in URL query strings (visible in logs)
- ❌ Store secrets in Git history (use `git filter-repo` if committed accidentally)
- ❌ Share SSH private key with humans — only GitHub Secret

---

## .gitignore checklist

Verify `.gitignore` includes:

```
# Secrets
.env
.env.local
.env.*.local
*.key
*.pem
*.p12
*.pfx

# SSH
id_rsa*
id_ed25519*

# Cloud credentials
.aws/
.gcloud/
r2-credentials.env
```

---

## Pre-commit hook (recommend)

Install `detect-secrets`:

```bash
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

Install hook:
```bash
pre-commit install
```

Now mỗi commit sẽ scan for secret patterns (AWS keys, generic tokens, etc.).

---

## Related

- `docs/decisions/ADR-0009-cicd-pipeline.md` — CI/CD decisions
- `docs/07-deployment/vps-setup.md` — initial setup
- `docs/07-deployment/rollback-runbook.md` — incident recovery
