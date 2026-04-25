# ADR-0002: Cron Job Architecture

> **Status**: Accepted
> **Date**: 2026-04-18
> **Deciders**: Bảo (domain expert) + Claude (Senior Architect)

---

## Context

RMS cần xử lý các tác vụ định kỳ không gắn với HTTP request:
- Check Lease sắp hết hạn → notify Landlord
- Dọn dẹp expired tokens
- Anonymize PII Tenant cũ (ADR-0006)
- Nhắc Landlord xuất Invoice nếu chưa làm vào đầu tháng

Cần quyết định: dùng gì để schedule, chạy ở đâu, handle failure
như thế nào.

### Options

**Option A — APScheduler** (in-process, chạy trong FastAPI app)
**Option B — Celery Beat** (task queue riêng, worker riêng)
**Option C — System cron** (crontab gọi script Python độc lập)

---

## Decision

Chọn **Option A — APScheduler in-process** cho MVP.

**Lý do loại Option B**: Celery cần Redis/RabbitMQ làm broker —
thêm 1 infrastructure component. Overkill cho scale 50–100 phòng
với ~5 tasks/ngày. YAGNI.

**Lý do loại Option C**: System cron khó container hóa, khó test,
không có retry built-in, log phân tán.

**APScheduler** chạy trong process FastAPI, không cần infra thêm,
đủ cho MVP. Khi scale lên (v2.x, nhiều property, nhiều worker), có
thể migrate sang Celery Beat mà không thay đổi business logic — vì
task logic đã tách ra service layer.

---

## Task inventory

### Task 1 — `check_lease_status` (00:05 daily)

```python
async def check_lease_status():
    """
    Scan Lease sắp expire hoặc đã expire.
    KHÔNG update DB (status là computed).
    CHỈ trigger notification events.
    """
    today = date.today()
    warning_threshold = today + timedelta(days=30)

    # Lease sắp hết hạn (expiring_soon)
    leases = await lease_repo.get_expiring(before=warning_threshold)
    for lease in leases:
        await notification_service.emit("lease.expiring_soon", lease)

    # Lease đã hết hạn nhưng chưa terminate (expired)
    expired = await lease_repo.get_expired(as_of=today)
    for lease in expired:
        await notification_service.emit("lease.expired", lease)
```

### Task 2 — `send_invoice_reminder` (05 ngày hàng tháng, 08:00)

```python
async def send_invoice_reminder():
    """
    Nhắc Landlord xuất Invoice nếu tháng này chưa có Invoice
    cho Lease active.
    """
    current_month = date.today().replace(day=1)
    landlords = await invoice_repo.get_landlords_without_invoice(
        month=current_month
    )
    for landlord in landlords:
        await notification_service.emit("invoice.reminder", landlord)
```

### Task 3 — `cleanup_expired_tokens` (02:00 daily)

```python
async def cleanup_expired_tokens():
    await token_repo.delete_expired_invite_tokens()
    await token_repo.delete_expired_reset_tokens()
    await token_repo.delete_expired_refresh_tokens()
```

### Task 4 — `anonymize_old_tenants` (03:00 daily)

```python
async def anonymize_old_tenants():
    """Xem ADR-0006 — anonymize PII sau 5 năm."""
    cutoff = datetime.now(UTC) - timedelta(days=5 * 365)
    await tenant_repo.anonymize_archived_before(cutoff)
```

---

## Implementation

### Setup APScheduler với FastAPI lifespan

```python
# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def init_scheduler(app):
    @app.on_event("startup")
    async def start_scheduler():
        scheduler.add_job(
            check_lease_status,
            CronTrigger(hour=0, minute=5),
            id="check_lease_status",
            replace_existing=True,
        )
        scheduler.add_job(
            send_invoice_reminder,
            CronTrigger(day=5, hour=8, minute=0),
            id="invoice_reminder",
            replace_existing=True,
        )
        scheduler.add_job(
            cleanup_expired_tokens,
            CronTrigger(hour=2, minute=0),
            id="cleanup_tokens",
            replace_existing=True,
        )
        scheduler.add_job(
            anonymize_old_tenants,
            CronTrigger(hour=3, minute=0),
            id="anonymize_tenants",
            replace_existing=True,
        )
        scheduler.start()

    @app.on_event("shutdown")
    async def stop_scheduler():
        scheduler.shutdown()
```

### Idempotency requirement

Mỗi task **phải idempotent** — chạy nhiều lần cùng input → kết quả
như nhau, không duplicate side effect.

```python
# Đúng — idempotent
async def anonymize_old_tenants():
    await tenant_repo.anonymize_archived_before(cutoff)
    # SQL: WHERE anonymized_at IS NULL → safe khi chạy lại

# Sai — không idempotent
async def anonymize_old_tenants():
    tenants = await tenant_repo.get_archived_before(cutoff)
    for t in tenants:
        await tenant_repo.anonymize(t)  # Nếu crash giữa chừng → partial state
```

### Logging mỗi task run

```python
import logging
logger = logging.getLogger("scheduler")

async def check_lease_status():
    logger.info("check_lease_status: started")
    try:
        # ... logic ...
        logger.info("check_lease_status: done, processed %d leases", count)
    except Exception as e:
        logger.error("check_lease_status: failed — %s", str(e))
        raise  # Re-raise để APScheduler ghi vào job history
```

### Error handling

APScheduler tự động log exception nhưng **không retry** theo mặc định.
Với scale MVP, acceptable — task sẽ chạy lại vào ngày hôm sau. Nếu
cần retry (v1.x), migrate sang Celery Beat.

---

## Timezone

Tất cả cron schedule dùng **UTC+7 (Asia/Ho_Chi_Minh)**:

```python
scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
```

Lý do: Landlord VN, tất cả time display theo giờ VN. Dùng UTC+7
tường minh thay vì UTC để tránh nhầm lẫn khi đọc schedule.

---

## Môi trường

**Development**: Scheduler chạy bình thường nhưng có thể disable
bằng env var:

```python
if settings.ENABLE_SCHEDULER:
    init_scheduler(app)
```

**Test**: Scheduler tắt hoàn toàn. Task functions được test trực tiếp
(gọi function, không qua scheduler).

**Production**: Scheduler bật. Nếu deploy nhiều instance (future) →
cần distributed lock để tránh chạy cùng lúc. MVP: 1 instance, không
cần lock.

---

## Consequences

### Positive
- Không cần infra thêm — APScheduler chạy trong process FastAPI
- Task logic ở service layer → testable độc lập với scheduler
- Đủ cho MVP scale

### Negative / Trade-offs
- In-process → nếu app crash thì scheduler cũng dừng
- Không có built-in retry
- Không scale ngang — nếu chạy nhiều instance sẽ execute duplicate

### Neutral
- Migration path rõ ràng sang Celery Beat khi cần (v2.x): giữ
  nguyên task functions, chỉ thay scheduler wrapper

---

## References

- ADR-0006: Data Retention (anonymize_old_tenants task)
- ADR-0004: Notification Framework (emit events từ cron tasks)
- APScheduler docs: https://apscheduler.readthedocs.io
- Phase 2 Summary — Pattern 5: Daily Status Maintenance Cron
