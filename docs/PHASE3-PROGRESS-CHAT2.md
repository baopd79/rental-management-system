# Phase 3 Progress — Chat 2 Checkpoint

> **Purpose**: Context seed cho chat 3 (Stage 3 — autogenerate migration).
>
> **Usage**: Mở chat mới → paste file này + PHASE2-SUMMARY.md +
> erd.mmd + erd-reference.md + prompt cuối file → Claude có full context.
>
> **Started**: 2026-04-18
> **Last updated**: 2026-04-21 (end of Chat 2 — Dev Env + Alembic setup)
> **Authors**: Bảo (domain expert) + Claude (Senior Architect + Mentor)
> **Previous checkpoint**: `PHASE3-PROGRESS.md` (end of Chat 1)

---

## 1. Phase 3 Deliverables Checklist

| #   | Deliverable                               | Status                    | Files                                                  |
| --- | ----------------------------------------- | ------------------------- | ------------------------------------------------------ |
| 1   | ADRs (6 cái)                              | ✅ Done                   | `docs/decisions/ADR-0001.md` → `ADR-0006.md`           |
| 2   | Architecture Diagram                      | ✅ Done                   | `docs/02-architecture/architecture-diagram.svg`        |
| 3   | ERD                                       | ✅ Done (post-review)     | `docs/03-database/erd.mmd` + `erd-reference.md`        |
| 4   | SQLModel models (17 tables)               | ✅ Done                   | `app/models/*.py` (14 files, 17 classes)               |
| 5   | **Dev env (Docker Compose + uv)**         | ✅ **Done (Chat 2)**      | `docker-compose.yml`, `.env.example`, `pyproject.toml` |
| 6   | **Alembic config**                        | ✅ **Done (Chat 2)**      | `alembic/env.py`, `alembic.ini`                        |
| 7   | Alembic migration `001_initial_schema.py` | ⏳ **Next chat (Chat 3)** | —                                                      |
| 8   | API Spec (OpenAPI 3.0)                    | ⏳ Chat sau nữa           | —                                                      |
| 9   | Frontend decision + wireframes            | ⏳ Chat sau nữa           | —                                                      |
| 10  | CI/CD pipeline plan                       | ⏳ Cuối phase             | —                                                      |

---

## 2. Tech Stack — FINAL (chốt Chat 2)

| Component       | Choice                       | Rationale                                                               |
| --------------- | ---------------------------- | ----------------------------------------------------------------------- |
| Package manager | **uv**                       | Fast, modern, reproducible via `uv.lock`                                |
| Python          | 3.12.13                      | Stable, pinned via `.python-version`                                    |
| DB mode         | **Sync**                     | Đổi từ async sau khi đánh giá cognitive load. Phase 6-7 có thể migrate. |
| DB driver       | `psycopg[binary]` v3         | Modern replacement cho psycopg2                                         |
| ORM             | SQLModel (sync)              | Đã viết 17 models ở Chat 1                                              |
| Migration       | Alembic (sync template)      | Standard                                                                |
| Postgres        | 16 via Docker, port **5433** | 5432 bị Brew Postgres chiếm                                             |

**Dependencies installed:**

Core (10):

- fastapi, uvicorn[standard]
- sqlmodel, alembic, psycopg[binary]
- pydantic-settings, pydantic[email], python-dotenv
- python-jose[cryptography], passlib[bcrypt]

Dev (4): pytest, pytest-cov, ruff, mypy

---

## 3. Project Structure hiện tại

```
rental-management-system/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── enums.py              # 8 Python Enum classes
│   ├── db/
│   │   ├── __init__.py
│   │   └── base.py               # Mixins + NAMING_CONVENTION
│   └── models/
│       ├── __init__.py           # Central export, 17 classes
│       ├── user.py               # Nhóm 1
│       ├── token.py              # Nhóm 1 (3 classes)
│       ├── property.py           # Nhóm 2
│       ├── room.py               # Nhóm 2
│       ├── tenant.py             # Nhóm 3
│       ├── occupant.py           # Nhóm 3
│       ├── lease.py              # Nhóm 4
│       ├── service.py            # Nhóm 5
│       ├── service_room.py       # Nhóm 5
│       ├── meter_reading.py      # Nhóm 6
│       ├── invoice.py            # Nhóm 7 (Invoice + LineItem)
│       ├── payment.py            # Nhóm 8
│       ├── audit_log.py          # Nhóm 9
│       └── notification.py       # Nhóm 9
├── alembic/
│   ├── versions/                 # Empty, chờ migration đầu
│   ├── env.py                    # Configured
│   ├── README
│   └── script.py.mako
├── docs/                         # Từ Phase 2
├── .env                          # gitignored
├── .env.example                  # Commit
├── .gitignore
├── .python-version               # "3.12"
├── alembic.ini
├── docker-compose.yml            # Postgres 16, port 5433
├── pyproject.toml
├── uv.lock                       # Commit
└── README.md
```

**Bugs đã fix trong Chat 2:**

- `TimestampMixin` + `CreatedAtOnlyMixin` share Column instance → đổi sang `sa_type` + `sa_column_kwargs` pattern
- Thiếu `__init__.py` ở 4 folders (`app/`, `app/core/`, `app/db/`, `app/models/`)
- Thiếu `pydantic[email]` dependency

---

## 4. Quyết định quan trọng Chat 2

### 4.1. Naming convention cho DB constraints

Set trong `app/db/base.py`:

```python
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = NAMING_CONVENTION
```

**Lý do**: tên constraint predictable → migration drop/rename không cần query DB → reproducible giữa env.

### 4.2. Port Postgres = 5433 (không phải 5432)

Brew Postgres đã chiếm 5432 trên máy Bảo. Giải pháp: 2 Postgres song song, Docker port 5433.
`.env` và `docker-compose.yml` dùng biến `POSTGRES_PORT` nên dễ đổi nếu cần.

### 4.3. Alembic env.py đọc DB URL từ `.env`

Dùng `python-dotenv` (không `pydantic-settings` — đơn giản hơn cho migration tool).
`compare_type=True` enabled cho cả offline + online mode để detect type change khi autogenerate.

### 4.4. Mixin pattern — Field(sa_type=...) thay vì Field(sa_column=Column(...))

Bug phát hiện khi import nhiều model cùng lúc: `sa_column=Column(...)` tạo 1 Column instance ở class-level, share giữa các subclass → SQLAlchemy raise error.

Fix: dùng `sa_type` + `sa_column_kwargs` để SQLModel tự build Column mới mỗi subclass.

---

## 5. Stage 3 Plan — Autogenerate Migration (NEXT CHAT)

### Sub-stages:

- **S3.1** — Autogenerate baseline: `alembic revision --autogenerate -m "initial schema"`
- **S3.2** — Review + fix enum types (Postgres native enum autogenerate buggy)
- **S3.3** — Add 6 partial unique indexes manual
- **S3.4** — Add ~15 CHECK constraints manual
- **S3.5** — Add ~10 hot-path indexes
- **S3.6** — Test `upgrade head` + `downgrade base` reproducible

### Known debts sẽ nổ ở Stage 3:

1. **PostgreSQL enum types** — autogenerate duplicate enum creation trong downgrade
2. **Partial unique indexes** — SQLModel autogenerate KHÔNG detect (6 cái trong erd-reference section 3)
3. **CHECK constraints** với điều kiện phức tạp — không autogen (~15 cái trong erd-reference section 4)
4. **service_rooms composite PK** — có thể cần tweak sau autogen
5. **`updated_at` auto-update** — chưa implement trigger/listener (defer Phase 4)

### References cần đọc trước:

- `docs/03-database/erd.mmd` — full schema
- `docs/03-database/erd-reference.md`:
  - Section 3: 6 partial unique indexes (SQL statements có sẵn)
  - Section 4: 15+ CHECK constraints (SQL statements có sẵn)
  - Section 5: 10 hot-path indexes (SQL statements có sẵn)
  - Section 7: FK ON DELETE behaviors
  - Section 9: 8 enum types

---

## 6. Dev Learning Progress (Bảo)

**Chat 1 đã học:**

- Python type hints + `| None`
- Pydantic + SQLModel pattern 4-schema
- Mixin pattern

**Chat 2 đã học:**

- uv workflow (init, add, sync, run)
- Docker Compose concepts (service, volume, port mapping, healthcheck)
- 12-Factor App: `.env` vs `.env.example`
- Shell gotchas: zsh escaping `[extras]` với quote
- Verify-after-each-step discipline (Claude strict về pattern này)
- Naming convention cho DB constraints
- Alembic env.py structure (offline vs online mode)

**Mistakes & lessons:**

- Chạy `uv init` không pin Python 3.12 → Python 3.13 lẻn vào → phải reset
- Paste output "đã ok" thay vì output thật → bị Claude nhắc nhở nhiều lần
- Diễn giải quá chặt lời Claude (tách imports làm 2 khối vì nghĩ "phải đặt convention trước các import")
- Skip ruff check trước khi commit

---

## 7. Working Style Notes (Bảo's preferences)

- Request responses **ngắn gọn, signal-dense**. Khi dài, Bảo sẽ flag.
- Thích pattern: **concept → tự viết → Claude review → discuss edge case**
- Không muốn Claude copy-paste answer — muốn học pattern.
- Verify discipline: luôn paste output thật, không "trust me ok rồi".

---

## 8. Next Chat Opening Prompt (template)

```
Chào! Tôi tiếp tục Phase 3 Chat 3 của dự án RMS.

Đính kèm:
- PHASE2-SUMMARY.md (requirements summary)
- PHASE3-PROGRESS-CHAT2.md (progress đến end of Chat 2)
- erd.mmd + erd-reference.md (schema + constraints SQL)

Tôi muốn tiếp tục với Stage 3 — Autogenerate Migration.
Bắt đầu từ S3.1.

Working style như Chat 1+2:
- Senior Architect + Mentor
- Nói rõ các kiến thức mới theo what-why-how, câu hỏi logic, các phương án ( có recommend phương án tốt nhất)
- Concept trước → tôi tự làm → bạn phản biện, review
- trả lợi Ngắn gọn, đúng trọng tâm, không dài dòng xu nịnh, signal-dense
```

---

**End of Chat 2. Ready for Chat 3 — Stage 3.**
