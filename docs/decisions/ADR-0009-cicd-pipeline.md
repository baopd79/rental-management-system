# ADR-0009: CI/CD Pipeline

> **Status**: Accepted
> **Date**: 2026-04-25
> **Deciders**: Bảo, Claude (as Senior Architect)
> **Related**: ADR-0008 (Frontend stack), Deliverable #7 (Alembic migration)

---

## Context

Phase 3 chốt backend + frontend stack + database schema + API spec.
Phase 4 sẽ implement và cần deploy ra production cho Bảo self-use và
showcase portfolio. ADR này chốt pipeline từ code push → running in
production.

**Constraints**:

1. **Solo dev budget**: $6-12/month infrastructure tối đa.
2. **Portfolio signal**: Pipeline phải thể hiện senior practices (lint,
   test, migration safety, rollback).
3. **Self-use production**: Bảo sẽ dogfood RMS quản lý 3 nhà trọ thực.
   Bug production = downtime business.
4. **Learning goal**: Pipeline phải expose Bảo với DevOps basics (Docker,
   secrets, migration, monitoring) — không magic đen.
5. **Reproducible**: Rebuild từ git commit phải tạo environment
   identical.
6. **Not over-engineered**: Không Kubernetes, không service mesh, không
   multi-region. YAGNI.

---

## Decision

Adopt **GitHub Actions + Docker Compose on VPS** pipeline với 2
environments (staging + production), branch-gated deploys, và Alembic
pre-start migration pattern.

Chi tiết phân thành 8 sub-decisions.

---

## Detailed Decisions

### D1. Deployment Target

**Choice**: **VPS** (Virtual Private Server) với Docker Compose.

**Provider recommendation** (chọn 1 khi Phase 4 deploy):
- **Hetzner Cloud CX22** (2 vCPU, 4GB RAM, 40GB SSD, €4.51/tháng) — best value
- **Vultr Regular** ($6/month, 1 vCPU, 1GB RAM, 25GB SSD) — có Singapore POP (low latency VN)
- **DigitalOcean Basic Droplet** ($6/month, 1 vCPU, 1GB RAM, 25GB SSD) — docs
  mature, VN community mạnh

**Recommend Hetzner** nếu budget cho phép 4GB RAM (Postgres + FastAPI +
Frontend + Nginx + headroom). Vultr/DO 1GB cramped, sẽ hit OOM khi có
5+ concurrent requests.

**Alternatives considered**:
- **Fly.io Free**: 256MB VM; Postgres free cũ deprecated → cost $5+/month
- **Railway**: $5 starter nhưng usage-based → unpredictable
- **Render Free**: cold start 30s → UX tệ
- **AWS/GCP Free Tier**: 12 tháng rồi charge cliff; học cost cao
- **Tailscale self-hosted home server**: free nhưng uptime phụ thuộc home ISP

**Rationale**:
- VPS = full control, học SRE basics (systemd, iptables, nginx, backup).
- Docker Compose = reproducible, dev/prod parity, migrate server dễ.
- Chi phí predictable, không surprise bill.
- Skill này transferable (90% startup/SME dùng VPS + Docker).

**Consequences**:
- Phải tự handle: OS updates, SSH hardening, firewall, backup, monitoring.
- Không có managed Postgres — phải tự run Postgres container (backup critical).
- Scaling vertical only (upgrade VPS); horizontal scaling defer v2.x.

---

### D2. Environments

**Choice**: **2 environments — staging + production**.

**Topology**:

```
┌─────────────────┐    ┌─────────────────┐
│    STAGING      │    │   PRODUCTION    │
│   VPS (small)   │    │   VPS (main)    │
│                 │    │                 │
│  api.staging.   │    │  api.rms-app.   │
│    rms-app.vn   │    │    vn           │
│                 │    │                 │
│  rms-app.vn/    │    │  rms-app.vn     │
│    staging      │    │                 │
└─────────────────┘    └─────────────────┘
      ▲                        ▲
      │ auto deploy            │ manual approve
      │ (main push)            │ (tag push)
      │                        │
┌─────────────────────────────────────────┐
│           GitHub main branch            │
└─────────────────────────────────────────┘
```

**2 VPS instances** hoặc **1 VPS với 2 docker-compose projects** (subdomain
routing):

- **MVP mode** (cheap): 1 VPS, staging + prod share server, khác subdomain
  + khác Docker network. Risk: staging crash có thể ảnh hưởng prod.
- **Production mode**: 2 VPS riêng biệt, hoàn toàn isolated. Cost 2x.

**Recommend MVP mode** ban đầu (Phase 4 launch). Tách ra khi Phase 5 có
users thật.

**Alternatives considered**:
- **3 envs** (dev/staging/prod): Dev env cho solo dev = local Docker.
  Không cần VPS dev.
- **1 env** (prod only): Không test migration, risk data loss production.
- **4+ envs** (qa, uat, preprod, prod): enterprise scale, không phù hợp.

**Rationale**:
- Staging = safety net cho migration test + UAT self-testing new features.
- Production = real data, real uptime.
- 2 envs = minimum viable safety.

**Consequences**:
- Staging data = synthetic (reset được). Production data = real (backup
  critical).
- Cần duplicate secrets (2 sets).
- Migration test ở staging trước khi prod.

---

### D3. Branch Strategy

**Choice**: **main-first với tag-based production release**.

**Rules**:

| Trigger | Action |
|---|---|
| Push to `feature/*`, `fix/*` branch | CI only (lint, test, build) |
| Open PR → `main` | CI + require review (self-approve cho solo) |
| Merge to `main` | CI + **auto-deploy to staging** |
| Push tag `v*.*.*` | CI + **manual-approve deploy to production** |
| Hotfix critical | Branch `hotfix/*` → PR → main → tag `v*.*.*-hotfix.N` |

**Semver convention**:
- `v1.0.0` = MVP launch
- `v1.1.0` = minor feature (v1.x features như Manager role)
- `v1.0.1` = bugfix only
- `v2.0.0` = breaking change (schema migration không backward compat)

**Alternatives considered**:
- **GitFlow** (develop/release/hotfix/feature): overkill cho solo
- **Trunk-based** (commit → prod): risky không có staging gate
- **Release branches** (`release/v1.x`): duplicate work với tags

**Rationale**:
- Tag = explicit version marker cho production release.
- Branch `main` luôn deployable staging — mọi merge đều pass CI.
- Manual gate prod = ít risk deploy lúc ngủ.

**Consequences**:
- Phải discipline tag semver đúng.
- Rollback = redeploy previous tag (dễ dàng).
- Changelog tied với tags → automate qua `release-please` nếu muốn.

---

### D4. CI Checks (GitHub Actions)

**Choice**: Matrix of checks trên mọi PR + main push.

#### Backend CI (`.github/workflows/backend-ci.yml`)

Trigger: PR hoặc push → `main` với changes trong `backend/**` hoặc
`alembic/**`.

Jobs:

1. **Lint**: `ruff check backend/`
2. **Format check**: `ruff format --check backend/`
3. **Type check**: `mypy backend/`
4. **Unit + integration tests**: `pytest` với Postgres service container
5. **Migration check**: `alembic upgrade head` + `alembic downgrade base`
   + `alembic upgrade head` (test reproducibility)
6. **Docker build**: `docker build -t rms-backend:ci .` (verify Dockerfile
   valid)

#### Frontend CI (`.github/workflows/frontend-ci.yml`) — Phase 4 later

Trigger: PR hoặc push → `main` với changes trong `frontend/**`.

Jobs:

1. **Lint**: `pnpm lint`
2. **Type check**: `pnpm tsc --noEmit`
3. **Tests**: `pnpm test --run`
4. **Build**: `pnpm build`

#### Cross-cutting: OpenAPI drift check

Trigger: PR có changes trong cả backend routes AND `docs/04-api/openapi.yaml`.

Job:
1. Backend container startup với `/openapi.json` endpoint
2. Download `/openapi.json` → diff với `docs/04-api/openapi.yaml`
3. Tool: `openapi-diff` CLI
4. Fail if breaking change: removed endpoint, changed required field type,
   removed response code
5. Warn (non-fail) for additive: new endpoint, new optional field

Initial implementation defer Phase 4 (cần FastAPI code chạy được).

**Alternatives considered**:
- **Pre-commit hooks only**: không enforce ở remote, có thể skip
- **Single monolith workflow**: khó debug, slow feedback per PR
- **External tools (SonarQube, CodeClimate)**: free tier limited, setup phức tạp

**Rationale**:
- Split per domain = parallel runs, faster feedback.
- Migration check là critical cho RMS (schema drift = data loss risk).
- OpenAPI drift check = design-first → code-first reconciliation (ADR-0008).

**Consequences**:
- CI time: ~3-5 phút per PR (acceptable).
- GitHub Actions free tier: 2000 minutes/month. Solo dev với 10 PR/tuần +
  40 runs/PR = ~1600 min/month → OK.

---

### D5. CD Automation Level

**Choice**: **Staging fully automated, Production manual-approve gate**.

**Staging deploy** (`.github/workflows/backend-deploy-staging.yml`):

Trigger: `push: branches: [main]` sau khi CI pass.

Flow:
1. Build Docker image với tag `rms-backend:staging-<commit_sha>`
2. Push image lên GitHub Container Registry (`ghcr.io`)
3. SSH vào staging VPS
4. Pull new image
5. Run `docker compose pull && docker compose up -d`
6. Health check: curl `/health` — expect 200 trong 30s
7. Slack/Discord webhook notify (optional)

**Production deploy** (`.github/workflows/backend-deploy-production.yml`):

Trigger: `push: tags: ['v*.*.*']`.

Flow:
1. Build Docker image với tag `rms-backend:<version>` + `rms-backend:latest`
2. Push lên ghcr.io
3. **GATE: GitHub Environment "production" require manual approval**
   — Bảo click "Approve" trong GitHub UI mới continue
4. Take DB backup (pg_dump → S3 hoặc local tarball)
5. SSH vào prod VPS
6. Pull + compose up -d
7. Health check với extended timeout (60s cho migrate)
8. Smoke test: curl core endpoints (`/health`, `/api/v1/auth/login`)
9. Notify result

**Alternatives considered**:
- **Fully auto prod**: 1 bug merge main → prod crash users. Bảo self-user
  vẫn đau.
- **SSH manual deploy** (no automation): không reproducible, miss audit
  trail, rủi ro typo.
- **Blue-green / canary**: over-engineered cho <10 users, cần load balancer
  + 2x resources.

**Rationale**:
- Manual approval = 10 giây click nhưng tránh 10 tiếng recovery từ bug.
- Staging auto = fast feedback, integration testing môi trường thật.
- GitHub Environments feature free → không cần tool thứ 3.

**Consequences**:
- Prod deploy không 100% hands-off — cần Bảo online khi release.
- Off-hours deploy = plan ahead, không ad-hoc.
- Audit trail: GitHub Actions logs → ai approve, khi nào, commit gì.

---

### D6. Secrets Management

**Choice**: **GitHub Actions Secrets** (per environment) + runtime `.env` file trên VPS.

**Secrets categories**:

| Category | Storage | Example |
|---|---|---|
| CI/CD credentials | GitHub Secrets (repo-level) | `SSH_PRIVATE_KEY`, `GHCR_TOKEN` |
| Env-specific | GitHub Environments | `STAGING_DB_URL`, `PRODUCTION_DB_URL` |
| Runtime (VPS) | `/opt/rms/.env` (mode 600) | `DATABASE_URL`, `JWT_SECRET_KEY` |
| DB backup encryption | separate KMS key | `BACKUP_ENCRYPTION_KEY` |

**GitHub Secrets structure**:

```
Repository secrets (all envs):
  GHCR_TOKEN
  SLACK_WEBHOOK_URL  (optional)

Environment "staging":
  SSH_HOST
  SSH_USER
  SSH_PRIVATE_KEY
  DATABASE_URL
  JWT_SECRET_KEY
  RESEND_API_KEY  (email service, ADR-0004)

Environment "production":
  (same keys, different values)
```

**Rotation policy**:

- `JWT_SECRET_KEY`: không rotate để tránh invalidate existing sessions.
  Nếu compromised → rotate + users re-login. Document cho Phase 5.
- `DATABASE_URL`: rotate khi team change, restart containers để pick up.
- `SSH_PRIVATE_KEY`: rotate 6 tháng 1 lần hoặc khi laptop thay đổi.
- `GHCR_TOKEN`: fine-grained PAT, expire 90 ngày.

**Alternatives considered**:
- **HashiCorp Vault**: enterprise-grade, overkill.
- **AWS Secrets Manager**: cost $0.40/secret/month, vendor lock.
- **Docker secrets**: chỉ work với swarm mode.
- **.env committed + ignored**: unsafe, accident prone.

**Rationale**:
- GitHub Secrets native integration, free, sufficient cho solo/small team.
- Environment-scoped secrets = staging không accidentally deploy prod creds.
- `.env` file runtime = standard 12-factor app pattern.

**Consequences**:
- Phải manual sync khi thêm secret (GitHub UI).
- Không có secret audit log chi tiết (chỉ có "was rotated at X").
- Migration path sang Vault/cloud KMS nếu scale: straightforward.

---

### D7. Migration Strategy

**Choice**: **Alembic migrate BEFORE app startup** (blocking).

**Docker Compose pattern**:

```yaml
services:
  backend:
    image: ghcr.io/rms/backend:v1.0.0
    command: >
      sh -c "
        echo 'Running migrations...' &&
        alembic upgrade head &&
        echo 'Migrations OK, starting API...' &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000
      "
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
```

**Why blocking startup**:
- Container healthy = DB schema match code. Nếu migrate fail → container
  restart loop → alert visible ngay.
- Không có "app chạy nhưng DB sai schema" window (race condition bug).

**Rollback strategy**:

1. **Detect issue**: health check fail, error rate spike, Bảo thấy bug
2. **Immediate**: `git revert` commit → tag new version → deploy
3. **If schema backward compat** (add column, add table): rollback code OK, 
   schema mới vẫn work với code cũ
4. **If schema NOT backward compat** (drop column, rename): 
   - `alembic downgrade -1` **trên VPS manually** via SSH
   - Redeploy previous version
   - Write postmortem

**Backward-compat migration discipline**:

Enforce qua review rule Phase 4:
- Adding: always OK
- Renaming: NOT allowed (use add + migrate data + drop pattern over 2 releases)
- Dropping: NOT allowed trong cùng version với code changes (drop chỉ sau
  code stable ≥ 1 release)

**Alternatives considered**:
- **Migrate via init container**: 2 containers, complex orchestration
- **Migrate via sidecar**: same complexity
- **Migrate manually qua SSH**: không reproducible, human error
- **Non-blocking migrate**: risk schema drift runtime

**Rationale**:
- Simple blocking pattern = 99% case đủ cho MVP.
- Backward-compat discipline = cost upfront, benefit long-term (zero
  downtime deploys possible).
- Rollback path rõ ràng = giảm stress khi deploy fail.

**Consequences**:
- Deploy downtime ~30-60s per release (migration run time).
- Long migrations (add index trên table lớn) = longer downtime. Phase 5
  learn pattern `CREATE INDEX CONCURRENTLY` ngoài Alembic.
- First deploy luôn là initial migration (fastest).

---

### D8. Monitoring & Observability

**Choice**: **MVP minimal + structured logging**, defer APM/metrics
tooling to Phase 5.

**MVP scope**:

1. **Application logs**: structured JSON qua `structlog` hoặc Python
   `logging` + JSON formatter
2. **Access logs**: uvicorn + nginx access logs
3. **Container logs**: `docker compose logs` manually
4. **Health endpoint**: `GET /health` trả về `{"status":"ok","db":"ok","version":"v1.0.0"}`
5. **DB backup**: cron job `pg_dump` daily → encrypted → upload S3
   (Cloudflare R2 free tier 10GB đủ)
6. **Uptime monitoring**: UptimeRobot free (50 monitors, 5-min interval) ping `/health`
7. **Email alert khi down**: UptimeRobot → Bảo's email

**Deferred to Phase 5**:
- APM (Sentry, Datadog, New Relic) — cost + setup complexity
- Metrics (Prometheus + Grafana) — need adoption curve
- Distributed tracing — single-service MVP không cần
- Log aggregation (Loki, ELK) — file-based logs đủ cho vài user

**Alternatives considered**:
- **Full APM Day 1**: over-engineered, $0-50/month cost, setup eats dev time
- **No monitoring**: too risky for self-use production

**Rationale**:
- Structured logs = grep-able, prep cho Phase 5 aggregation.
- `/health` endpoint = lifeline, biết app alive.
- Daily backup = catastrophic recovery.
- UptimeRobot free = first line defense, Bảo biết khi down.

**Consequences**:
- Debug production bug = SSH + grep logs. Acceptable for MVP.
- No performance metrics → can't proactively tune. Phase 5 add.
- Alert fatigue risk: chỉ alert critical (down >5min, disk >90%).

---

## Final Pipeline Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Developer laptop                                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  git commit → push feature branch                         │   │
│  └────────────────────────────┬─────────────────────────────┘   │
└───────────────────────────────┼──────────────────────────────────┘
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│  GitHub                                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CI Workflow (backend-ci.yml)                             │   │
│  │  - Lint (ruff)                                            │   │
│  │  - Type check (mypy)                                      │   │
│  │  - Unit + integration tests (pytest + Postgres service)   │   │
│  │  - Migration up/down/up check                             │   │
│  │  - Docker build                                           │   │
│  └────────────────────────────┬─────────────────────────────┘   │
│                                ▼ (merge to main)                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CD Workflow (backend-deploy-staging.yml)                 │   │
│  │  - Build + push image to ghcr.io                          │   │
│  │  - SSH to staging VPS                                     │   │
│  │  - docker compose pull + up -d                            │   │
│  │  - Health check                                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│                                ▼ (git tag v*.*.*)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CD Workflow (backend-deploy-production.yml)              │   │
│  │  - Build + tag image                                      │   │
│  │  - MANUAL APPROVAL GATE (GitHub Environment)              │   │
│  │  - DB backup → S3                                         │   │
│  │  - SSH to prod VPS                                        │   │
│  │  - docker compose pull + up -d                            │   │
│  │  - Extended health check + smoke tests                    │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure as Code (defer Phase 5)

**MVP**: Manual VPS setup qua runbook (`docs/07-deployment/vps-setup.md`).

**Phase 5 consider**: Terraform / Ansible để codify infrastructure.

**Rationale**: 
- Solo dev + 1 VPS + rebuild rare = manual viable.
- Learning curve Terraform/Ansible = weeks.
- Phase 4 focus = code features, không infra.

---

## Consequences

### Positive

- **Reproducible**: commit hash + tag → deterministic image build.
- **Safety net**: staging catches 80% bugs before prod.
- **Audit trail**: GitHub Actions logs = ai deploy gì, khi nào.
- **Fast iteration**: merge → staging live trong 3-5 phút.
- **Portfolio signal**: CI/CD skill demonstrable.
- **Rollback path**: tag-based deploy = easy revert.
- **Cost**: ~$5-12/month infrastructure, free tier GitHub Actions.

### Negative

- **Setup cost**: 1-2 ngày initial setup (VPS provision, SSH, Docker,
  nginx, domain DNS, GitHub secrets).
- **Solo maintenance**: VPS updates, cert renewals, backup verification →
  Bảo phải tự. Monthly 1-2 hour chore.
- **No auto-scaling**: nếu đột biến traffic → VPS overload. MVP ok.
- **Manual prod approval**: không 100% hands-off. Intentional trade-off.
- **No preview environments per PR**: không có "review app" per PR. Can
  add sau nếu Phase 5 có contributors.

### Neutral

- **GitHub Actions lock-in**: migrate sang GitLab CI/Jenkins cost. Low
  risk — GitHub stable 15+ năm.
- **Docker Compose scale limit**: works up to ~100 concurrent users.
  Phase 5+ reconsider nếu grow.

---

## Implementation Checklist (Phase 4 kickoff tasks)

### Infrastructure setup (1-2 ngày)

- [ ] Provision VPS (Hetzner/Vultr)
- [ ] SSH key setup, disable password auth
- [ ] UFW firewall: allow 22, 80, 443 only
- [ ] Install Docker + Docker Compose
- [ ] Domain DNS: A record cho `rms-app.vn` và `staging.rms-app.vn`
- [ ] nginx reverse proxy + Let's Encrypt SSL (certbot)
- [ ] Create deployment user (không root)
- [ ] `/opt/rms/.env` với mode 600
- [ ] Cloudflare R2 bucket cho backups

### GitHub setup

- [ ] Create GitHub Container Registry
- [ ] Generate fine-grained PAT với `write:packages` scope
- [ ] Create Environments: `staging`, `production`
- [ ] Add required reviewers cho `production` env (Bảo self)
- [ ] Repository secrets + Environment secrets (per D6)

### Pipeline files

- [ ] `.github/workflows/backend-ci.yml`
- [ ] `.github/workflows/backend-deploy-staging.yml`
- [ ] `.github/workflows/backend-deploy-production.yml`
- [ ] `docs/07-deployment/deployment-guide.md`
- [ ] `docs/07-deployment/secrets-management.md`
- [ ] `docs/07-deployment/rollback-runbook.md`

### Application changes

- [ ] Create `/health` endpoint in FastAPI
- [ ] Configure structlog
- [ ] Docker Compose `depends_on` với `condition: service_healthy`
- [ ] Production Dockerfile (multi-stage, non-root user)

### Verification

- [ ] Deploy first version to staging, verify `/health` OK
- [ ] Tag `v0.1.0-beta`, deploy to production, verify
- [ ] Rollback test: tag `v0.1.1-beta`, deploy, then redeploy `v0.1.0-beta`
- [ ] Backup test: run pg_dump manually, restore to staging
- [ ] Alert test: stop container, verify UptimeRobot alerts

---

## References

- GitHub Actions docs: https://docs.github.com/en/actions
- GitHub Environments: https://docs.github.com/en/actions/deployment/targeting-different-environments
- Docker Compose prod patterns: https://docs.docker.com/compose/production/
- ADR-0008 (Frontend Stack) — CI parallel runs
- Deliverable #7 (Alembic migration) — migration patterns

---

**ADR-0009 End.**
