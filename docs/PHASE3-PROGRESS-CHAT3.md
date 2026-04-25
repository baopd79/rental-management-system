# Phase 3 Progress — Chat 3 Checkpoint

> **Purpose**: Context seed cho chat 4 (API Spec / Frontend decision).
>
> **Usage**: Mở chat mới → paste file này + PHASE2-SUMMARY.md +
> erd.mmd + erd-reference.md + prompt cuối file → Claude có full context.
>
> **Started**: 2026-04-21
> **Last updated**: 2026-04-22 (end of Chat 3 — Stage 3 Migration)
> **Authors**: Bảo (domain expert) + Claude (Senior Architect + Mentor)
> **Previous checkpoint**: `PHASE3-PROGRESS-CHAT2.md` (end of Chat 2)

---

## 1. Phase 3 Deliverables Checklist

| #   | Deliverable                             | Status                    | Files                                           |
| --- | --------------------------------------- | ------------------------- | ----------------------------------------------- |
| 1   | ADRs (6 cái)                            | ✅ Done                   | `docs/decisions/ADR-0001.md` → `ADR-0006.md`    |
| 2   | Architecture Diagram                    | ✅ Done                   | `docs/02-architecture/architecture-diagram.svg` |
| 3   | ERD                                     | ✅ Done                   | `docs/03-database/erd.mmd` + `erd-reference.md` |
| 4   | SQLModel models (17 tables)             | ✅ Done                   | `app/models/*.py`                               |
| 5   | Dev env (Docker Compose + uv)           | ✅ Done                   | `docker-compose.yml`, `pyproject.toml`          |
| 6   | Alembic config                          | ✅ Done                   | `alembic/env.py`, `alembic.ini`                 |
| 7   | **Alembic migrations (initial schema)** | ✅ **Done (Chat 3)**      | 3 migration files                               |
| 8   | API Spec (OpenAPI 3.0)                  | ⏳ **Next chat (Chat 4)** | —                                               |
| 9   | Frontend decision + wireframes          | ⏳ Chat sau               | —                                               |
| 10  | CI/CD pipeline plan                     | ⏳ Cuối phase             | —                                               |

---

## 2. Migrations State — FINAL (chốt Chat 3)

```
base → 140877bc29e5 (initial_schema)
       → 25bfdb8601ff (add_partial_unique_indexes)
         → a4d3745501b5 (add_hot_path_indexes)  [head]
```

### 2.1. Schema stats

| Category               | Count                               |
| ---------------------- | ----------------------------------- |
| Tables                 | 17                                  |
| PostgreSQL enum types  | 8                                   |
| CHECK constraints      | 17                                  |
| Partial unique indexes | 6                                   |
| Hot-path indexes       | 11                                  |
| Foreign keys           | 31 regular + 1 circular `use_alter` |

### 2.2. Migration file breakdown

| File                                         | Content                                                                                                                                                         |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `140877bc29e5_initial_schema.py`             | 17 tables + 8 enums (lowercase values, `<name>_enum`) + 17 CHECK + 31 FK + circular FK (via `op.create_foreign_key` at end of upgrade) + DROP TYPE in downgrade |
| `25bfdb8601ff_add_partial_unique_indexes.py` | 6 partial unique indexes                                                                                                                                        |
| `a4d3745501b5_add_hot_path_indexes.py`       | 11 hot-path indexes (tách `idx_line_items_meter_reading_start`/`_end` thành 2, không composite theo ERD)                                                        |

---

## 3. Quyết định quan trọng Chat 3

### 3.1. Enum helper `create_pg_enum()`

Trong `app/db/base.py`:

```python
def create_pg_enum(enum_cls: Type[Enum]) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        values_callable=lambda e: [m.value for m in e],
        name=f"{_camel_to_snake(enum_cls.__name__)}_enum",
    )
```

**Why**:

- `values_callable`: force lowercase `.value` thay cho UPPERCASE `.name` mặc định
- Name convention: `user_role_enum`, `billing_type_enum`... match ERD section 9

**Usage** trong models:

```python
# Không server_default
role: UserRole = Field(sa_type=create_pg_enum(UserRole), ...)

# Có server_default (cần sa_column thay sa_type)
scope: ServiceScope = Field(
    sa_column=Column(
        create_pg_enum(ServiceScope),
        nullable=False,
        server_default=ServiceScope.ALL_ROOMS.value,
    ),
    default=ServiceScope.ALL_ROOMS,
)
```

### 3.2. CHECK constraint naming — **KHÔNG prepend `ck_<table>_`**

Naming convention set Chat 2 **tự prepend** `ck_<table>_`. Nếu viết
`CheckConstraint(name="ck_leases_end_after_start")` sẽ thành
`ck_leases_ck_leases_end_after_start` (double prefix).

**Rule đúng**:

```python
# ❌ Wrong
CheckConstraint("end_date >= start_date", name="ck_leases_end_after_start")

# ✅ Right
CheckConstraint("end_date >= start_date", name="end_after_start")
```

### 3.3. Circular FK — `use_alter=True` phải tách ra `op.create_foreign_key`

`tenants.promoted_from_occupant_id → occupants.id` + `occupants.tenant_id → tenants.id`
tạo cycle. Fix:

**Model `tenant.py`**:

```python
promoted_from_occupant_id: UUID | None = Field(
    default=None,
    sa_column=Column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "occupants.id",
            use_alter=True,
            name="fk_tenants_promoted_from_occupant_id_occupants",
            ondelete="SET NULL",
        ),
        nullable=True,
    ),
)
```

**Migration**: Xóa `sa.ForeignKeyConstraint(use_alter=True)` khỏi `create_table("tenants", ...)`,
thêm `op.create_foreign_key(...)` ở cuối `upgrade()`:

```python
def upgrade() -> None:
    # ... all create_table ...

    # Circular FK — tách ra sau khi cả tenants và occupants đã tồn tại
    op.create_foreign_key(
        "fk_tenants_promoted_from_occupant_id_occupants",
        "tenants", "occupants",
        ["promoted_from_occupant_id"], ["id"],
        ondelete="SET NULL",
    )
```

**Downgrade**: Dùng `op.execute("ALTER TABLE ... DROP CONSTRAINT IF EXISTS ...")`
(không `op.drop_constraint` vì cần idempotent cho legacy state).

**Lý do**: `use_alter=True` nằm trong `sa.ForeignKeyConstraint` inline
không được Postgres áp dụng — migration render nhưng FK không xuất hiện trong DB.

### 3.4. DROP enum trong downgrade — bắt buộc

Alembic autogen **không** drop enum types. Phải thêm tay vào cuối `downgrade()`:

```python
for enum_name in (
    'user_role_enum', 'billing_type_enum', 'service_scope_enum',
    'meter_scope_enum', 'deposit_status_enum', 'voided_reason_enum',
    'line_type_enum', 'payment_method_enum',
):
    op.execute(f"DROP TYPE {enum_name}")
```

Không drop → downgrade rồi upgrade lần 2 fail với "type already exists".

### 3.5. Partial unique indexes + hot-path indexes — chỉ define ở migration

SQLModel autogen không detect được `postgresql_where` và DESC ordering.
→ Define trong migration file, không trong model `__table_args__`.

**Pattern**:

```python
op.create_index(
    'idx_name',
    'table',
    ['col1', sa.text('col2 DESC')],         # DESC via sa.text
    unique=True,
    postgresql_where=sa.text('col3 IS NULL'),  # partial
)
```

### 3.6. ERD overrides cho hot-path indexes

Chat 3 **cải thiện ERD** 2 điểm:

1. **Tách composite `(meter_reading_start_id, meter_reading_end_id)`** thành 2 partial indexes riêng —
   cover được cả query theo `end_id` (composite chỉ cover prefix `start_id`)
2. **Thêm DESC cho `idx_payments_invoice.paid_at`** — không có trong ERD nhưng là
   pattern phổ biến ("payment mới nhất trước")

### 3.7. Skip 2 constraints trong ERD

- `invoices.billing_month <= CURRENT_DATE` — **GIỮ**: sau khi verify, Postgres accept `CURRENT_DATE` trong CHECK
- `payments.paid_at <= CURRENT_DATE` — **GIỮ**: cùng lý do

(Trong draft ban đầu có định skip do nghi ngờ `CURRENT_DATE` immutable — đã revert sau verify)

### 3.8. Skip 2 hot-path indexes

- `idx_rooms_active` và `idx_tenants_active` — skip vì `idx_unique_room_name_per_property`
  và `idx_unique_tenant_phone_per_landlord` đã cover cùng prefix + cùng WHERE clause.

---

## 4. `alembic check` — Known false positives

Chạy `alembic check` sẽ warn **17 indexes "removed"**. Đây là false positive:

- Indexes define ở migration (không ở model `__table_args__`)
- Alembic compare metadata Python vs DB — metadata không có → nghĩ "user muốn drop"

**Options đã cân nhắc**:

- A. Accept + document (**chosen**)
- B. Duplicate khai báo `Index(...)` trong model — DRY violation
- C. Filter `include_object` trong `env.py` — ẩn cả bug thật

**Workflow verify drift manual**:

```bash
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "
SELECT COUNT(*) FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_%';
"
# Expected: 17
```

---

## 5. Project Structure (end of Chat 3)

```
rental-management-system/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── enums.py              # 8 Python Enums (str, Enum), .value lowercase
│   ├── db/
│   │   ├── __init__.py
│   │   └── base.py               # NAMING_CONVENTION + mixins + create_pg_enum helper
│   └── models/
│       ├── __init__.py           # Central export, 17 classes
│       ├── user.py               # UserRole via create_pg_enum
│       ├── token.py              # 3 classes (invite, password_reset, refresh)
│       ├── property.py
│       ├── room.py
│       ├── tenant.py             # FK circular use_alter (split to op.create_foreign_key)
│       ├── occupant.py
│       ├── lease.py
│       ├── service.py            # 3 enums via create_pg_enum (billing_type, scope, meter_scope)
│       ├── service_room.py
│       ├── meter_reading.py
│       ├── invoice.py            # 2 classes (Invoice + InvoiceLineItem)
│       ├── payment.py
│       ├── audit_log.py
│       └── notification.py
├── alembic/
│   ├── versions/
│   │   ├── 140877bc29e5_initial_schema.py
│   │   ├── 25bfdb8601ff_add_partial_unique_indexes.py
│   │   └── a4d3745501b5_add_hot_path_indexes.py
│   ├── env.py
│   └── script.py.mako            # Patched with `import sqlmodel`
├── scripts/
│   ├── __init__.py
│   └── smoke_test.py             # End-to-end ORM ↔ DB verify
├── docs/                         # Từ Phase 2
├── .env                          # gitignored
├── .env.example
├── .gitignore
├── .python-version
├── alembic.ini
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## 6. Dev Learning Progress (Bảo)

**Chat 1-2 đã học**: xem `PHASE3-PROGRESS-CHAT2.md` section 6.

**Chat 3 đã học**:

- Alembic autogenerate workflow + limitations:
  - Không detect partial index, DESC, expression
  - Circular FK cycle handling với `use_alter=True`
  - Enum type không auto-drop trong downgrade
- PG enum type deep dive:
  - `values_callable` để lowercase
  - Naming convention `<name>_enum`
  - Trade-off với CHECK constraint
  - `ALTER TYPE ADD VALUE` (future knowledge khi thêm value mới)
- SQLModel 2 API khai báo field:
  - `sa_type=...` (gọn, cho case đơn giản)
  - `sa_column=Column(...)` (full control — khi cần `server_default`, FK phức tạp)
- Python `default` vs DB `server_default`:
  - `default=EnumMember` — engine convert qua type adapter
  - `server_default=EnumMember.value` — raw SQL literal, cần `.value`
- Naming convention cho constraints:
  - Pitfall: không prepend `ck_<table>_` ở tên
  - `op.f(...)` wrapper để mark "đã final"
- Partial index vs unique constraint:
  - NULL != NULL → partial `WHERE col IS NOT NULL` + unique cho nullable
  - Multi-column prefix matching rule
- Index cost model:
  - Disk 10-30%, write slowdown 5-15%
  - Tạo theo query pattern thực tế, không "phòng khi cần"

**Mistakes & lessons Chat 3**:

- Nhảy bước Step 6 trước khi chạy Step 5 → verify trên file cũ → confuse
- Paste text summary thay output thật → bị push back về verify discipline
- Tin autogen không verify kỹ → miss FK circular bị silent drop

---

## 7. Working Style Notes (unchanged)

- Responses **ngắn gọn, signal-dense**
- Concept → tự viết → Claude review → discuss edge case
- `CURRENT_DATE` case: Claude initial over-cautious, Bảo push back (hợp lý) → revise decision

---

## 8. Next Chat Opening Prompt (template)

```
Chào! Tôi tiếp tục Phase 3 Chat 4 của dự án RMS.

Đính kèm:
- PHASE2-SUMMARY.md (requirements summary)
- PHASE3-PROGRESS-CHAT3.md (progress đến end of Chat 3)
- erd.mmd + erd-reference.md (schema + constraints SQL)

Tôi muốn tiếp tục với API Spec (OpenAPI 3.0) — Deliverable #8.

Working style như Chat 1-3:
- Senior Architect + Mentor
- Nói rõ các kiến thức mới theo what-why-how, câu hỏi logic,
  các phương án (có recommend phương án tốt nhất)
- Concept trước → tôi tự làm → bạn phản biện, review
- Trả lời ngắn gọn, đúng trọng tâm, không dài dòng xu nịnh, signal-dense
```

---

## 9. Open Questions cho Chat 4 (API Spec)

Một số vấn đề sẽ gặp khi viết API spec, Bảo nên suy nghĩ trước:

1. **API versioning**: `/api/v1/...` hay header-based? (recommend path-based)
2. **Pagination style**: offset/limit vs cursor-based?
3. **Filter/sort syntax**: query params flat vs nested JSON?
4. **Error response schema**: RFC 7807 Problem Details hay custom?
5. **Authentication endpoints**: prefix `/auth/*` hay `/users/login`?
6. **Invoice preview endpoint**: GET with query hay POST with body?
   (Phase 2 US-076: preview-before-commit)
7. **Batch operations**: single endpoint `/rooms/bulk-create` hay loop client-side?
8. **Resource nesting depth**: `/properties/{id}/rooms/{id}/leases/{id}` —
   nested depth nào là quá sâu?

---

**End of Chat 3. Ready for Chat 4 — API Spec.**
