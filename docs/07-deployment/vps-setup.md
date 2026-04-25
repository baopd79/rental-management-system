# VPS Setup Guide — RMS Production / Staging

> **Purpose**: Reproducible runbook để setup VPS từ fresh Ubuntu 24.04 →
> ready to receive GitHub Actions deploys.
>
> **Time estimate**: 1-2 giờ lần đầu, ~30 phút khi đã quen.
> **Audience**: Bảo (solo dev) + future contributors.
> **Last updated**: 2026-04-25

---

## Prerequisites

- [ ] VPS provider account (Hetzner / Vultr / DigitalOcean)
- [ ] SSH keypair local machine (`~/.ssh/id_ed25519`)
- [ ] Domain name với DNS access (ví dụ `rms-app.vn`)
- [ ] GitHub repository với CI/CD workflows đã commit

---

## Step 1: Provision VPS

### Hetzner (recommend)

1. Log in https://console.hetzner.cloud
2. Create Project "RMS"
3. Create Server:
   - **Location**: Singapore (closest to VN)
   - **Image**: Ubuntu 24.04
   - **Type**: CX22 (2 vCPU, 4GB RAM, 40GB SSD) — ~€4.5/month
   - **SSH Key**: Paste your public key (`cat ~/.ssh/id_ed25519.pub`)
   - **Name**: `rms-production` hoặc `rms-staging`
4. Wait 30s for provisioning
5. Note IP address (IPv4)

### DNS configuration

Point domain → VPS IP:

```
A     rms-app.vn                →  <VPS_IP>
A     www.rms-app.vn            →  <VPS_IP>
A     staging.rms-app.vn        →  <VPS_IP_staging>
A     api.rms-app.vn            →  <VPS_IP>  (optional, for API-only subdomain)
```

Wait DNS propagation (~5-30 min). Verify:
```bash
dig rms-app.vn +short
# Should show VPS IP
```

---

## Step 2: Initial SSH + Hardening

### Connect first time

```bash
ssh root@<VPS_IP>
# Should work với key-based auth (no password prompt)
```

### Update system

```bash
apt update && apt upgrade -y
apt install -y ufw fail2ban unattended-upgrades curl git
```

### Enable auto-security updates

```bash
dpkg-reconfigure -plow unattended-upgrades
# Select "Yes"
```

### Configure UFW firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (Let's Encrypt + redirect)
ufw allow 443/tcp   # HTTPS
ufw enable          # Confirm "y"
ufw status          # Verify
```

### Harden SSH

Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin prohibit-password  # Key-only, no password
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
```

Restart SSH:
```bash
systemctl restart ssh
```

### Configure fail2ban

```bash
systemctl enable fail2ban
systemctl start fail2ban
```

Default config bans brute-force SSH OK cho MVP.

---

## Step 3: Create deployment user

```bash
adduser rms --disabled-password --gecos ""
usermod -aG sudo rms  # Optional: sudo access
usermod -aG docker rms  # Will add after Docker install

# Copy SSH key
mkdir -p /home/rms/.ssh
cp /root/.ssh/authorized_keys /home/rms/.ssh/
chown -R rms:rms /home/rms/.ssh
chmod 700 /home/rms/.ssh
chmod 600 /home/rms/.ssh/authorized_keys
```

**Test**: logout, SSH as `rms@<VPS_IP>`, should work.

---

## Step 4: Install Docker

Official install script:

```bash
# As root
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin

# Verify
docker --version
docker compose version

# Add rms user to docker group (if not done earlier)
usermod -aG docker rms

# Test as rms user
su - rms
docker ps   # Should work without sudo
exit
```

### Enable Docker on boot

```bash
systemctl enable docker
```

---

## Step 5: Install Nginx (reverse proxy)

```bash
apt install -y nginx certbot python3-certbot-nginx
```

### Verify nginx running

```bash
systemctl status nginx
curl http://localhost  # Should show nginx welcome
```

---

## Step 6: Setup Let's Encrypt SSL

```bash
# For production
certbot --nginx -d rms-app.vn -d www.rms-app.vn --agree-tos --no-eff-email -m your-email@example.com

# For staging
certbot --nginx -d staging.rms-app.vn --agree-tos --no-eff-email -m your-email@example.com
```

Certbot sẽ:
1. Verify domain ownership qua HTTP challenge
2. Issue cert
3. Auto-configure nginx cho HTTPS redirect
4. Setup cron renewal (check twice daily)

### Verify

```bash
curl -I https://rms-app.vn
# Should show 200 OK + nginx
```

---

## Step 7: Nginx RMS configuration

Edit `/etc/nginx/sites-available/rms-production`:

```nginx
server {
    listen 443 ssl http2;
    server_name rms-app.vn www.rms-app.vn;

    # SSL certs managed by certbot
    ssl_certificate /etc/letsencrypt/live/rms-app.vn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rms-app.vn/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend static (Phase 4)
    location / {
        root /opt/rms/production/frontend-dist;
        try_files $uri $uri/ /index.html;
    }

    # API reverse proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Health endpoint
    location = /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }

    # /docs (FastAPI Swagger UI) — hide in prod optional
    location /docs {
        # Uncomment to restrict by IP in prod:
        # allow <YOUR_OFFICE_IP>;
        # deny all;
        proxy_pass http://127.0.0.1:8000/docs;
    }
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name rms-app.vn www.rms-app.vn;
    return 301 https://$server_name$request_uri;
}
```

Enable + reload:
```bash
ln -s /etc/nginx/sites-available/rms-production /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t   # Test config
systemctl reload nginx
```

---

## Step 8: RMS application directory

```bash
# As rms user
su - rms
mkdir -p /opt/rms/production /opt/rms/staging /opt/rms/backups
chmod 750 /opt/rms

# Create .env files (template, will fill secrets)
cd /opt/rms/production
```

Create `/opt/rms/production/.env` (mode 600):

```bash
# Image tag (updated by CD workflow)
BACKEND_IMAGE_TAG=production-latest

# Database
POSTGRES_DB=rms_prod
POSTGRES_USER=rms_user
POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>
DATABASE_URL=postgresql+psycopg://rms_user:${POSTGRES_PASSWORD}@postgres:5432/rms_prod

# JWT
JWT_SECRET_KEY=<GENERATE_STRONG_SECRET>
JWT_ACCESS_TOKEN_TTL_MINUTES=60
JWT_REFRESH_TOKEN_TTL_DAYS=7

# Email (Resend)
RESEND_API_KEY=<FROM_RESEND_DASHBOARD>
EMAIL_FROM_ADDRESS=noreply@rms-app.vn

# Env marker
ENVIRONMENT=production
```

Generate secrets:
```bash
# Strong password for Postgres
openssl rand -base64 32

# JWT secret (64 bytes)
openssl rand -hex 64
```

Set permissions:
```bash
chmod 600 /opt/rms/production/.env
```

### Copy `docker-compose.yml`

From repo (`backend/docker-compose.production.yml`) to `/opt/rms/production/docker-compose.yml`.

Template:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    image: ghcr.io/${GITHUB_REPOSITORY}/backend:${BACKEND_IMAGE_TAG}
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"   # Bind localhost only, nginx proxies
    command: >
      sh -c "
        echo 'Running migrations...' &&
        alembic upgrade head &&
        echo 'Starting API...' &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
      "
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  pgdata:
```

---

## Step 9: Backup setup

### Daily DB dump cron

Create `/opt/rms/backup-daily.sh`:

```bash
#!/bin/bash
set -e

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
BACKUP_DIR=/opt/rms/backups
BACKUP_FILE="${BACKUP_DIR}/daily-${TIMESTAMP}.sql.gz"

cd /opt/rms/production
docker compose exec -T postgres pg_dump -U rms_user rms_prod | gzip > "${BACKUP_FILE}"

# Keep only last 14 days
find "${BACKUP_DIR}" -name 'daily-*.sql.gz' -mtime +14 -delete

# Upload to Cloudflare R2 (if configured)
if [ -f /opt/rms/r2-credentials.env ]; then
    source /opt/rms/r2-credentials.env
    aws s3 cp "${BACKUP_FILE}" "s3://${R2_BUCKET}/backups/" \
      --endpoint-url "${R2_ENDPOINT}" \
      --profile r2
fi

echo "Backup OK: ${BACKUP_FILE}"
```

Make executable + schedule:

```bash
chmod +x /opt/rms/backup-daily.sh

# Add to cron (as rms user)
crontab -e
# Add line:
0 3 * * * /opt/rms/backup-daily.sh >> /opt/rms/backups/cron.log 2>&1
```

### Cloudflare R2 setup (recommend, 10GB free)

1. Sign up https://dash.cloudflare.com/ → R2
2. Create bucket `rms-backups`
3. Create API token with Object Read & Write
4. Create `/opt/rms/r2-credentials.env`:
   ```
   AWS_ACCESS_KEY_ID=<token_id>
   AWS_SECRET_ACCESS_KEY=<token_secret>
   R2_BUCKET=rms-backups
   R2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com
   ```
5. `chmod 600 /opt/rms/r2-credentials.env`

---

## Step 10: UptimeRobot monitoring

1. Sign up https://uptimerobot.com (free tier)
2. Add Monitor:
   - **Type**: HTTP(s)
   - **URL**: `https://rms-app.vn/health`
   - **Interval**: 5 minutes
   - **Alert contacts**: Your email + Telegram bot (optional)
3. Add similar for staging: `https://staging.rms-app.vn/health`

---

## Step 11: GitHub Secrets setup

Repository: https://github.com/<you>/rms/settings/secrets/actions

### Repository Secrets

```
GHCR_PULL_TOKEN     = <fine-grained PAT with read:packages>
SLACK_WEBHOOK_URL   = <optional, for notifications>
```

### Environment Secrets

Navigate: Settings → Environments → Create "staging" and "production".

**Staging environment**:
```
SSH_HOST             = <staging VPS IP>
SSH_USER             = rms
SSH_PRIVATE_KEY      = <contents of ~/.ssh/id_ed25519 — PRIVATE, not .pub>
```

**Production environment**:
```
SSH_HOST             = <production VPS IP>
SSH_USER             = rms
SSH_PRIVATE_KEY      = <different key ideally>
```

### Production environment protection

Settings → Environments → production:
- **Required reviewers**: Bảo (self)
- **Wait timer**: 0 minutes (approve immediately)
- **Deployment branches**: Selected tags only, pattern `v*.*.*`

This enables the manual approval gate mentioned in ADR-0009.

---

## Step 12: First deploy smoke test

### Trigger staging deploy

```bash
# Local machine
git commit --allow-empty -m "ci: trigger initial staging deploy"
git push origin main
```

Watch GitHub Actions tab. Expected:
- `backend-ci.yml` runs → passes
- `backend-deploy-staging.yml` runs → passes
- Visit `https://staging.rms-app.vn/health` → 200 OK

### Trigger production deploy

```bash
git tag v0.1.0-beta
git push origin v0.1.0-beta
```

- GitHub Actions starts `backend-deploy-production.yml`
- **Job "deploy" paused, waiting approval**
- Go to Actions tab → click "Review deployments" → Approve
- Deploy proceeds
- Visit `https://rms-app.vn/health` → 200 OK

---

## Verification Checklist

- [ ] `https://rms-app.vn` loads (or 404 if frontend not deployed yet)
- [ ] `https://rms-app.vn/health` returns `{"status":"ok","db":"ok"}`
- [ ] SSL cert valid (green padlock)
- [ ] HTTP redirects to HTTPS
- [ ] SSH password auth disabled
- [ ] UFW enabled, only 22/80/443 open
- [ ] Docker containers `postgres` + `backend` both healthy
- [ ] `docker compose logs backend | grep "Migrations OK"`
- [ ] Daily backup cron scheduled (`crontab -l`)
- [ ] UptimeRobot monitor active
- [ ] GitHub environments `staging` + `production` configured với required reviewers

---

## Troubleshooting

### Container won't start

```bash
cd /opt/rms/production
docker compose logs backend --tail 100
```

Common causes:
- Migration fail → check `alembic upgrade head` output
- Env var missing → verify `.env` complete
- DB not ready → increase `depends_on` healthcheck retries

### Health check 502 from nginx

```bash
# Check if backend binding to localhost
curl http://127.0.0.1:8000/health   # From VPS shell
# If OK → nginx proxy config issue
nginx -t
tail -f /var/log/nginx/error.log
```

### SSL cert renewal fail

```bash
certbot renew --dry-run
```

Common cause: DNS changed or firewall blocks 80. Fix DNS / UFW.

### Disk full

```bash
docker system prune -a   # Careful: removes unused images
du -sh /opt/rms/backups   # Old backups?
journalctl --vacuum-time=7d   # systemd logs
```

---

## Related

- `docs/decisions/ADR-0009-cicd-pipeline.md` — CI/CD decisions
- `docs/07-deployment/secrets-management.md` — secret handling detail
- `docs/07-deployment/rollback-runbook.md` — rollback procedure
