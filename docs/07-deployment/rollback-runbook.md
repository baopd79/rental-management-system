# Rollback Runbook — RMS Production

> **Purpose**: Step-by-step procedure khi production deploy fail hoặc bug
> lọt vào production.
>
> **When to use**: 
> - Health check fail sau deploy
> - Users report error 500 sustained
> - Data anomaly detected (wrong data được write)
> - Security vulnerability mới phát hiện
>
> **Target recovery time**: < 10 phút cho code-only rollback, < 30 phút
> nếu có schema migration involved.
>
> **Last updated**: 2026-04-25

---

## Quick Reference (TL;DR)

### Scenario A: Code-only rollback (most common)

```bash
# Local machine
git checkout v1.0.0                         # Previous stable tag
git push origin v1.0.0 --force-with-lease   # Not usually needed, just re-tag
# OR use workflow_dispatch:
gh workflow run backend-deploy-production.yml -f version=v1.0.0
```

Approve deployment in GitHub Actions → wait 2-3 min → verify `/health`.

### Scenario B: Rollback with schema migration (rare)

1. Stop new version traffic (scale backend to 0)
2. `alembic downgrade -1` on VPS
3. Deploy previous image
4. Resume traffic
5. Restore from backup if data corrupted

---

## Decision Tree

```
Deploy failed / bug detected
         │
         ▼
   Is schema changed in this release?
         │
    ┌────┴────┐
    │         │
   No        Yes
    │         │
    │         ▼
    │    Schema backward compat?
    │    (only ADD column/table, no DROP/RENAME)
    │         │
    │    ┌────┴────┐
    │    │         │
    │   Yes        No
    │    │         │
    │    │         ▼
    │    │    Data changed in new version?
    │    │         │
    │    │    ┌────┴────┐
    │    │    │         │
    │    │   No        Yes
    │    │    │         │
    ▼    ▼    ▼         ▼
  Path A  Path B     Path C
  (Code   (Code     (Restore
   only)   only)     backup)
```

---

## Path A: Code-Only Rollback

**When**: Schema không đổi, chỉ rollback code image.
**ETA**: 5-10 phút.
**Data loss**: None.

### Steps

1. **Identify previous stable version**
   ```bash
   # List recent tags
   git tag --sort=-creatordate | head -10
   ```

2. **Verify previous image exists in registry**
   ```bash
   # Replace v1.0.0 với tag thực
   docker pull ghcr.io/<repo>/backend:v1.0.0
   # Or check via GitHub UI: Packages tab
   ```

3. **Trigger redeploy**
   
   **Option 3a**: workflow_dispatch (recommend)
   ```bash
   gh workflow run backend-deploy-production.yml -f version=v1.0.0
   ```
   
   **Option 3b**: Manual tag push (nếu không có gh CLI)
   ```bash
   git tag -f v1.0.0-redeploy-$(date +%s) v1.0.0
   git push origin v1.0.0-redeploy-<timestamp>
   ```

4. **Approve deployment in GitHub**
   - Go to Actions tab
   - Click "Review deployments" → Approve

5. **Wait + verify**
   ```bash
   # Watch logs
   ssh rms@<VPS_IP> "cd /opt/rms/production && docker compose logs backend -f"
   
   # When "Starting API..." appears:
   curl https://rms-app.vn/health
   # Expect 200 with previous version in response
   ```

6. **Smoke test critical flows** (3-5 phút)
   - Login với test account
   - Xem dashboard
   - Tạo/xem 1 invoice existing

7. **Post-mortem**
   - File an issue: "Post-mortem: deploy v1.0.1 rolled back"
   - Root cause analysis
   - Fix → test staging → new tag

---

## Path B: Backward-Compatible Schema Rollback

**When**: Release v1.0.1 added columns/tables. Rolling back to v1.0.0 vẫn work vì old code không đụng columns/tables mới.
**ETA**: 5-10 phút.
**Data loss**: New columns vẫn tồn tại trong DB, không dùng. Clean sau.

### Steps

Same as Path A. Schema không cần downgrade vì backward compat.

### Cleanup later (when stable)

If you want to remove the unused columns/tables from failed release:

1. Wait ≥ 1 week for system stable
2. Write new migration that drops them
3. Deploy through normal pipeline

---

## Path C: Schema + Data Corruption Rollback

**When**: Migration v1.0.1 dropped column, OR data được write sai format do bug, OR logic bug corrupted state.
**ETA**: 20-60 phút.
**Data loss**: Bất kỳ writes từ lúc deploy đến lúc restore đều MẤT.

### Decision: DB restore or surgical fix?

**DB restore** (full recovery):
- Pro: clean state, no lingering corruption
- Con: lose all writes since backup

**Surgical fix** (SQL patches):
- Pro: keep good writes
- Con: complex, error-prone, need deep schema knowledge

**Default**: DB restore trừ khi writes quá nhiều/quan trọng.

### Restore DB from backup

1. **Pause traffic** (optional, recommend)
   ```bash
   ssh rms@<VPS_IP>
   cd /opt/rms/production
   docker compose stop backend
   # Now nginx sẽ 502, users không ghi data mới
   ```

2. **Backup current (corrupted) state for forensics**
   ```bash
   TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
   docker compose exec -T postgres pg_dump -U rms_user rms_prod | \
     gzip > /opt/rms/backups/corrupted-${TIMESTAMP}.sql.gz
   ```

3. **List available backups**
   ```bash
   ls -lht /opt/rms/backups/daily-*.sql.gz | head -5
   # Or from R2 if using cloud backup
   aws s3 ls s3://rms-backups/backups/ --endpoint-url $R2_ENDPOINT | tail -10
   ```

4. **Choose backup before incident time**
   ```bash
   BACKUP_FILE=/opt/rms/backups/daily-20260425-030000.sql.gz
   ```

5. **Drop + recreate database**
   ```bash
   docker compose exec postgres psql -U rms_user -d postgres <<EOF
   DROP DATABASE IF EXISTS rms_prod;
   CREATE DATABASE rms_prod OWNER rms_user;
   EOF
   ```

6. **Restore backup**
   ```bash
   gunzip < ${BACKUP_FILE} | docker compose exec -T postgres psql -U rms_user rms_prod
   ```

7. **Downgrade Alembic to matching version**
   
   Check what version of schema matches backup:
   ```bash
   docker compose exec postgres psql -U rms_user -d rms_prod -c "SELECT * FROM alembic_version;"
   # Note the revision hash
   ```
   
   If needed to downgrade further:
   ```bash
   docker compose run --rm backend alembic downgrade <revision_hash>
   ```

8. **Deploy stable code version**
   
   Update `.env`:
   ```bash
   sed -i "s|^BACKEND_IMAGE_TAG=.*|BACKEND_IMAGE_TAG=v1.0.0|" /opt/rms/production/.env
   ```

9. **Restart backend**
   ```bash
   docker compose up -d backend
   ```

10. **Verify health + smoke test** (Path A steps 5-6)

11. **Notify users** (if applicable)
    - Post on status page
    - Email users explaining downtime + data state

12. **Full post-mortem** (required for data loss incidents)
    - Root cause
    - Timeline
    - Impact (how many users, how many records)
    - Prevention measures

---

## Scenario-Specific Playbooks

### Migration deadlock

**Symptom**: Deploy hangs at "Running migrations...", container health check timeout.

**Diagnosis**:
```bash
ssh rms@<VPS_IP>
cd /opt/rms/production
docker compose logs backend --tail 50
```

Look for: `could not obtain lock`, `statement timeout`, `deadlock detected`.

**Fix**:
```bash
# Kill the pending migration lock
docker compose exec postgres psql -U rms_user rms_prod <<EOF
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'active' AND query LIKE '%alembic%';
EOF

# Restart backend (will retry migration)
docker compose restart backend
```

If still fails → rollback Path A.

### Disk full during deploy

**Symptom**: `no space left on device` error.

**Fix**:
```bash
# Clean up old Docker images
docker image prune -a -f --filter "until=72h"

# Clean old backups if needed
find /opt/rms/backups -name 'daily-*.sql.gz' -mtime +14 -delete

# Check
df -h
```

### Wrong image deployed (human error)

**Symptom**: Accidentally deployed feature branch to production.

**Fix**: Path A — redeploy last stable tag.

### Corrupted database (filesystem issue)

**Symptom**: Postgres won't start, `FATAL: database files are incompatible`.

**Fix**:
1. Check Postgres container logs
2. If filesystem corruption → restore from backup (Path C)
3. Consider VPS SSD failure — provision new VPS if needed

---

## Post-Deploy Verification (every deploy)

Run mỗi sau deploy:

```bash
# Health
curl -f https://rms-app.vn/health | jq .

# Version match (should show new tag)
curl -s https://rms-app.vn/health | jq -r .version

# Response time
time curl -s -o /dev/null https://rms-app.vn/health

# Error rate (last 5 min via logs)
ssh rms@<VPS_IP> "docker compose -f /opt/rms/production/docker-compose.yml logs --since 5m backend | grep -c ERROR"
# Expect: 0 or very low
```

---

## Communication Template

### To users (if downtime > 5 min)

```
Subject: RMS - Bảo trì hệ thống (expected downtime: X phút)

Chào các bạn,

Hệ thống RMS đang bảo trì từ <HH:MM> đến <HH:MM> (giờ VN).
Trong thời gian này, dịch vụ có thể tạm thời không truy cập được.

Chúng tôi sẽ thông báo khi hệ thống hoạt động lại.

Cảm ơn sự kiên nhẫn của bạn!
```

### Post-mortem template (internal)

```markdown
# Incident Post-Mortem: <date>

## Summary
<1-2 sentences on what happened>

## Timeline (UTC)
- HH:MM — Deploy started (v1.0.1)
- HH:MM — Health check fail detected
- HH:MM — Decision to rollback
- HH:MM — Rollback executed
- HH:MM — Service restored

## Root Cause
<Technical detail>

## Impact
- Users affected: <N>
- Data loss: <Yes/No + scope>
- Downtime: <X minutes>

## Detection
<How did we notice?>

## Response Actions
<What we did>

## Prevention
- [ ] <Action item 1>
- [ ] <Action item 2>
```

---

## Related

- `docs/decisions/ADR-0009-cicd-pipeline.md` — CI/CD decisions
- `docs/07-deployment/vps-setup.md` — initial setup
- `.github/workflows/backend-deploy-production.yml` — pipeline source
