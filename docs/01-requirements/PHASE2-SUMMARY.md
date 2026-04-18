# Phase 2 Summary — Context Seed cho Phase 3

> **Purpose**: Cô đọng mọi decisions và patterns của Phase 2 (Requirements)
> để paste vào chat Phase 3 mà không cần đọc lại 8 file requirements.
>
> **Usage**: Mở chat mới → paste file này + prompt "Tôi đang chuyển từ
> Phase 2 sang Phase 3. Đây là summary decisions" → Claude sẽ có full context.
>
> **Authors**: Bảo (domain expert) + Claude (senior engineer)
> **Completed**: 2026-04-18
> **File length target**: ~5-7 pages (cô đọng, không duplicate file gốc)

---

## 1. Project Context

**Product**: RMS (Rental Management System) — Alternative to TingTong,
positioning "Do less, but better".

**Primary user**: Landlord kiêm quản lý (Persona A, scale 5-100 phòng).
Bảo là product owner + primary user (self-dogfooding).

**Value prop**: "Từ đọc số điện đến người thuê nhận hoá đơn — trong vài click"

**MVP scope (11 features)**:

1. Quản lý nhà (Property CRUD)
2. Quản lý phòng (Room CRUD + status)
3. Quản lý Tenant (CRUD + Occupant)
4. Cấu hình Service
5. Ghi Meter Reading
6. Tự động tính Invoice
7. Xem Invoice (Landlord + Tenant)
8. Đánh dấu Payment
9. Quản lý Lease
10. Authentication
11. RBAC (Landlord + Tenant)

**Roadmap**: MVP → v1.x (Manager role, notification) → v2.x (Investor,
Technician, property types)

---

## 2. Core Entity Model

```
User (role: landlord | tenant)
  │
  ├── Property (1 Landlord owns N Properties)
  │     │
  │     ├── Room (1 Property has N Rooms)
  │     │    │
  │     │    └── Lease (1 Room has 0-1 active Lease, N historical)
  │     │         │
  │     │         ├── Tenant (1 Lease → 1 Tenant representative)
  │     │         │    │
  │     │         │    └── Occupant (1 Tenant → N Occupants, không có account)
  │     │         │
  │     │         └── Invoice (1 Lease → N Invoices monthly)
  │     │              │
  │     │              ├── InvoiceLineItem (1 Invoice → N line items)
  │     │              │
  │     │              └── Payment (1 Invoice → N Payments)
  │     │
  │     └── Service (1 Property → N Services)
  │          │
  │          └── MeterReading (1 Service per_meter → N readings)
```

**Glossary mapping**:

- Property = Nhà trọ
- Room = Phòng
- Lease = Hợp đồng
- Tenant = Người thuê (có account)
- Occupant = Người ở cùng (không account)
- Service = Dịch vụ
- Meter Reading = Chỉ số
- Invoice = Hoá đơn
- Payment = Thanh toán

---

## 3. Key Patterns (xuyên suốt)

### Pattern 1: Invoice Immutability (TUYỆT ĐỐI)

Invoice sau khi tạo **không đổi** (trừ status + Payments). Service/Reading
đổi giá/số → Invoice cũ giữ nguyên. Muốn sửa → **void + recreate**.

Áp dụng: Nhóm 5, 6, 7, 8.

### Pattern 2: Computed Status (không lưu DB)

Status của các entity chính đều **computed at query time**:

- `Room.status`: derive từ Lease.status 1-1
- `Lease.status`: derive từ start_date/end_date/terminated_at
- `Tenant.status`: derive từ Lease active count
- `Invoice.status`: derive từ Payments

**Trừ `Lease.terminated` lưu DB qua `terminated_at`** (là event, không phải
computation).

Lý do: tránh bug "status lệch data".

### Pattern 3: Date fields as policy tools

Landlord dùng `start_date`, `end_date`, `terminated_date` làm **công cụ
chính sách**, không phải feature riêng.

Ví dụ: Tenant vào 5/3, muốn tính full tháng 3 → Landlord set
`start_date = 1/3`. App không biết "ưu đãi", chỉ pro-rata theo date.

### Pattern 4: Task-oriented UI

UX theo workflow thực tế, không theo data structure.

Ví dụ: Landlord đọc công tơ cả nhà 1 vòng → form batch per Property, không
per Room.

### Pattern 5: Daily Status Maintenance Cron

1 cron duy nhất 00:05 daily để check Lease/Tenant status transitions và
trigger notifications. Computed status → không UPDATE DB, chỉ trigger
events.

### Pattern 6: Soft delete (archive) vs Toggle (is_active)

- **Soft delete**: Room, Tenant — dùng `is_archived` + `archived_at`
- **Toggle**: Service — dùng `is_active` (không phải delete, chỉ bật/tắt)

### Pattern 7: Pro-rata universal

1 công thức duy nhất cho rent: `rent_amount × days_occupied / days_in_month`.
Không có mode "full month" vs "pro-rata". Landlord dùng `start_date` /
`terminated_date` để control.

---

## 4. Decisions by Entity

### User & Auth (Nhóm 1, 8 stories)

- Landlord self-signup (email + password)
- Tenant invite-only (không self-signup, Landlord gửi link Zalo)
- Invite token: opaque, single-use, TTL 7 ngày, stateful DB
- Forgot password: pattern giống invite, TTL 1h
- JWT access (60min) + refresh token (7d)
- **RBAC 2 role** thiết kế mở, mở rộng Manager/Investor sau
- **Reactivation flow**: Tenant archived có user_id cũ → dùng reset password
  (không tạo User mới)
- **Multi-role**: Open question cho Phase 3 (MVP: 1 user 1 role)

### Property (Nhóm 2, 9 stories chung với Room)

- 1 Property → 1 Landlord (NOT NULL)
- Hard delete Property chỉ khi hết Room
- v2.x mở: Investor ownership

### Room

- `display_name` free text (unique trong Property)
- Soft delete (archive) — chặn khi còn Lease active hoặc Invoice unpaid
- **Room.status** 4 trạng thái computed từ Lease.status:
  - `vacant`: không Lease hoặc Lease draft/terminated
  - `occupied`: Lease active
  - `expiring_soon`: Lease expiring_soon
  - `lease_expired`: Lease expired (Tenant còn ở, hợp đồng hết)

### Tenant & Occupant (Nhóm 3, 9 stories)

- **Tách Tenant (domain) và User (auth)**: Tenant có `user_id` nullable
- Tenant unique phone/email trong scope Landlord + active
- **Occupant không có account** (khác biệt chính với Tenant)
- `Tenant.status` 3: `pending` / `active` / `moved_out` (computed)
- Soft delete Tenant khi dọn đi, invalidate User account
- Hard delete Occupant cho case nhập nhầm
- **Per_person snapshot**: tại thời điểm tạo Invoice (không phải cuối tháng)
- **US-036 Promote Occupant**: đổi người đại diện (wizard 3-step)

### Lease (Nhóm 4, 10 stories)

- **Strict single-active**: 1 Room max 1 Lease non-terminal
- 5 status: `draft` → `active` → `expiring_soon` → `expired` + `terminated`
- Renewal = tạo Lease mới (không extend end_date)
- **Deposit 4 status**: `held`/`returned`/`forfeited`/`deducted` — lưu ở
  Lease, KHÔNG tạo Payment
- **Pro-rata universal** theo start_date/end_date/terminated_date
- **Snapshot rent_amount và deposit_amount** vào Lease khi ký (không dùng
  live Room.default_rent)
- Lease active gần immutable: chỉ sửa `note` + `end_date`
- Auto-archive Tenant khi settle deposit xong (US-056)
- `billing_day` range [1, 28]
- **Rollover deposit** (renewal không thu cọc mới): dùng `returned` +
  amount=0 + note (không thêm status mới)
- **Grace period expired**: vẫn tính Invoice theo rent cũ

### Service (Nhóm 5, 7 stories)

- **3 billing types**: `per_meter` / `per_person` / `fixed`
- **Scope**: `all_rooms` (default) / `selected_rooms` (chỉ cho per_meter)
- **Shared meter chia theo số người** các phòng trong scope. Phòng trống
  không chịu phí.
- `applied_rooms` fix ở Service level, không select khi nhập reading
- **Toggle `is_active`** thay cho delete
- **Unit auto theo billing_type**: chỉ `per_meter` mới nhập (kWh/m³/khác)
- Không đổi giá giữa kỳ
- Không per-Lease override (dùng rent_amount work-around)

### Meter Reading (Nhóm 6, 6 stories)

- **Point-in-time schema**: 1 record = 1 reading (không lưu cả kỳ)
- **room_id nullable**: NULL = shared meter, value = per-room
- Reading là **domain event**, append-only conceptually
- Chỉ Landlord nhập, **batch per Property** (1 form cho cả nhà)
- **No deadline** — Invoice manual trigger, không cron auto
- **Reminder ngày 5** nếu chưa xuất Invoice
- Validate `reading_value >= previous_value` (warn, không block)
- Initial reading khi tạo Service per_meter (có thể skip, warn lần sau)
- **Reading → tháng billing (Option B)**: reading ngày 1/5 → consumption
  của tháng 4
- **Reading mutability**:
  - Chưa ref Invoice: sửa thoải mái
  - Ref Invoice unpaid + no Payment: warn "Invoice không auto-update"
  - Ref Invoice paid/partial: block
- Landlord sửa reading → KHÔNG tự động touch Invoice (Option 3)

### Invoice (Nhóm 7, 9 stories — phức tạp nhất)

- Status: `unpaid` → `partial` → `paid` + `void`
- **No draft in DB**: preview in-memory + commit
- **Preview-before-commit (batch per Property)**: sinh N Invoice cùng lúc
  với option exclude từng Lease
- Individual mode cho edge cases
- **Invoice Immutability tuyệt đối**: void + recreate thay cho edit
- **Billing period per line item**: Invoice tháng 5 có line rent tháng 5 +
  line điện tháng 4 (cùng Invoice)
- **Line items flatten**: description gộp chỉ số cũ/mới (không columns riêng)
- `line_type` enum: `rent` / `service` / `adjustment`
- **Adjustment manual**: Landlord tự thêm line vào Invoice tháng sau
- **US-086**: Terminate Lease auto-prompt Invoice cuối pro-rata
- Pro-rata áp dụng cho cả Service fixed/per_person khi terminate giữa tháng
- **Delivery MVP**: in-app + Landlord nhắc Zalo thủ công
- Validation: không tạo Invoice tương lai, không duplicate (lease+month)

### Payment (Nhóm 8, 5 stories — đơn giản nhất)

- **Record-only**: Landlord ghi nhận hậu kiểm, không có payment gateway
- Không có `type` enum (trạng thái đã ở Invoice.status)
- `method` enum: cash/bank_transfer/ewallet/other
- Validate strict: `amount > 0`, không overpay, không future date
- Hard delete allowed → trigger recompute Invoice.status
- Unlimited Payment per Invoice
- **Không Payment cho deposit** (deposit là Lease state)
- Tenant thấy full Payment history (transparency)

---

## 5. Cross-Cutting Concerns (cần Phase 3 ADRs)

### ADR-0001: Naming convention for lifecycle fields

- `is_archived` + `archived_at`: soft delete pattern (Room, Tenant)
- `is_active`: feature toggle (Service)
- `terminated_at`: event timestamp (Lease)
- Document clearly để dev mới không nhầm.

### ADR-0002: Cron job architecture

Single cron 00:05 daily:

- Task 1: Lease status check + notifications
- Task 2: Tenant status check + notifications
- Task 3: (future) Invoice reminders, anomaly detection
- Idempotent, logged

### ADR-0003: Audit log architecture

Mentioned trong US-004, US-052, US-063. Chưa design:

- Scope: mọi write hay chỉ critical?
- Storage: same DB or separate?
- Retention?

### ADR-0004: Notification framework

Defer đến v1.x nhưng cần design pattern:

- Channels: in_app_badge (MVP) → email → push → zalo_oa
- Triggers: lease_expiring, invoice_created, invoice_overdue, etc.
- Queue/worker architecture

### ADR-0005: RBAC strategy

Hiện tại role-based đơn giản. Cân nhắc:

- Permission-based khi có Manager role
- Policy-based cho Investor

### ADR-0006: Data Retention (Nghị định 13/2023/NĐ-CP)

Draft policy ở Nhóm 3:

- Tenant active: giữ full PII
- Tenant archived: 5 năm, sau đó anonymize
- Invoice/Payment: 10 năm (luật kế toán VN)
- User consent checkbox trong flow accept invite

**Cần review pháp lý trước khi production**.

---

## 6. Tech Stack Decisions (pending Phase 3)

**Đã chốt (từ Vision):**

- Backend: FastAPI + SQLModel + PostgreSQL + Alembic
- Infra: Docker + Docker Compose
- Auth: JWT + RBAC

**Pending (Phase 3):**

- Frontend stack (TBD từ Vision)
- Refresh token rotation strategy
- Email service (SMTP vs SaaS)
- Rate limiting (in-memory vs Redis)
- Deployment target (VPS, cloud, free-tier...)

---

## 7. Stats & Metrics

- **8 groups completed**: Auth, Property/Room, Tenant, Lease, Service,
  Meter Reading, Invoice, Payment
- **63 user stories total**: 42 Must + 17 Should + 4 Could
- **Estimate total**: ~95 dev-days ≈ 19 weeks solo
- **Vision original estimate**: 10 weeks → **actual 1.9x**

**Timeline realism**:

- Bảo phải chọn: scope cut, extend timeline, hoặc cả hai
- Vì là portfolio project (không deadline cứng), extend timeline OK
- Recommend: demote một số Must → Should khi plan sprint

---

## 8. Key Decisions Ảnh Hưởng Nhiều Nhóm

### Decision: "Đẩy flexibility ra input, không vào business logic"

Thể hiện ở:

- Pro-rata theo date (Nhóm 4) — không có billing_mode field
- Service billing_type cho Landlord tự chọn (Nhóm 5)
- Batch UI cho workflow thật (Nhóm 6) — không config

### Decision: "Data immutable, UI flexible"

- Invoice immutable, UI render khác nhau (compact/detail)
- Reading append-only, UI có lịch sử
- Service changes không retroactive

### Decision: "Split actions theo time, không theo concept"

- US-055 (terminate Lease) và US-056 (settle deposit) tách 2 step
- Reading nhập và Invoice xuất tách 2 step (không auto)
- Void Invoice và tạo Invoice mới tách 2 step

### Decision: "YAGNI for deposit/refund flows"

- Deposit là Lease state, không Payment transaction
- Refund ngoài app (Landlord ghi note)
- Không có Payment âm
- v1.x/v2.x handle khi có use case thật

---

## 9. Open Questions còn lại (cho Phase 3)

**Technical:**

1. Refresh token rotation — áp dụng hay không?
2. Frontend stack — React / Vue / Svelte?
3. Email service — self-host hay SaaS?
4. Rate limiting — in-memory hay Redis?

**Product:** 5. Multi-role per user (Landlord + Tenant cùng account)? 6. Bulk import Tenant từ Excel? 7. Late fee / discount handling? 8. Invoice number format (UUID vs "INV-2026-05-001")? 9. Service fixed/per_person pro-rata khi terminate — confirmed Option A
(pro-rata)

**Legal:** 10. Data retention policy — review pháp lý trước production

---

## 10. Lessons Learned (Bảo's retrospective)

**Nếu làm lại Phase 2:**

1. **Viết gọn hơn từ đầu** — không cố gắng hoàn hảo MVP, chỉ "đủ chạy +
   đủ để v1.x/v2.x mở rộng"
2. **Gate Review 2 lần** (giữa phase + cuối phase) thay vì 1 lần
3. **Vẫn bắt đầu từ Auth** (dependency đúng)

**Patterns Bảo đã internalize:**

- YAGNI discipline
- Task-oriented UI design
- Invoice Immutability
- Computed vs Stored status
- Trust but verify (AI collaboration)

---

## 11. Ready for Phase 3

**Phase 3 deliverables:**

1. **Architecture Diagram** (system components + data flow)
2. **ERD** (refined từ "Ghi chú kiến trúc" của 8 nhóm)
3. **Database Schema** (migration-ready)
4. **API Spec** (OpenAPI 3.0)
5. **ADRs** (6 ADRs đã list ở section 5)
6. **Frontend decision** + UI wireframes
7. **Dev environment** setup (Docker Compose)
8. **CI/CD pipeline plan**

**Estimated Phase 3 duration**: 2-3 weeks (prep cho Phase 4 coding)

---

## Appendix: File References

Trong repo:

- `docs/00-overview/vision.md` — Vision APPROVED
- `docs/00-overview/glossary.md` — Terms (updated with all statuses)
- `docs/01-requirements/01-auth-rbac.md` — Nhóm 1
- `docs/01-requirements/02-property-room.md` — Nhóm 2
- `docs/01-requirements/03-tenant.md` — Nhóm 3
- `docs/01-requirements/04-lease.md` — Nhóm 4
- `docs/01-requirements/05-service.md` — Nhóm 5
- `docs/01-requirements/06-meter-reading.md` — Nhóm 6
- `docs/01-requirements/07-invoice.md` — Nhóm 7
- `docs/01-requirements/08-payment.md` — Nhóm 8
- `docs/01-requirements/PHASE2-REVIEW.md` — Gate Review
- `docs/01-requirements/PHASE2-REVIEW-PATCHES.md` — Applied patches
- `CHANGELOG.md` — Version history

---

**End of Phase 2. Ready to enter Phase 3. 🚀**
