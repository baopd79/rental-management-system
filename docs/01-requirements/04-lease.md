# User Stories — Nhóm 4: Lease (Hợp đồng)

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-17
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **Lease (Hợp đồng)** — entity trung tâm của toàn bộ
hệ thống. Lease kết nối Tenant ↔ Room, là nguồn sinh Invoice hàng tháng,
và quyết định Room.status (vacant/occupied/expiring_soon).

**Map với Vision:**

- MVP feature #9: Hợp đồng cơ bản (ngày bắt đầu, ngày kết thúc, tiền cọc,
  giá phòng)
- Gián tiếp: quyết định logic Invoice (feature #6) và Room status (feature #2)

**Key decisions (đã chốt):**

| #   | Decision                                                             | Lý do                                               |
| --- | -------------------------------------------------------------------- | --------------------------------------------------- |
| 1   | Strict single-active: 1 Room chỉ có 1 Lease active tại một thời điểm | Đơn giản Invoice logic, match 95% case thực tế      |
| 2   | Lease có status `draft` (khi today < start_date)                     | Cho phép tạo trước ngày bắt đầu                     |
| 3   | Renewal = tạo Lease mới (không extend)                               | Audit trail rõ ràng, hỗ trợ đổi giá                 |
| 4   | Deposit lưu ở Lease, không phải Invoice                              | Deposit là trạng thái, không phải giao dịch định kỳ |
| 5   | Rent snapshot vào Lease.rent_amount                                  | Giá thay đổi ở Room không ảnh hưởng Lease đã ký     |
| 6   | Deposit 4 status: held / returned / forfeited / deducted             | Đủ cover các case thực tế Bảo gặp                   |
| 7   | Pro-rata theo `start_date` và `end_date/terminated_date`             | Rule đơn giản, áp dụng cho mọi Lease                |
| 8   | Landlord dùng date fields làm công cụ chính sách                     | App giữ logic đơn giản, linh hoạt đẩy ra input      |

## Personas liên quan

- **Landlord** (Persona A): CRUD Lease, terminate, renewal, xử lý deposit
- **Tenant** (Persona B): xem Lease của mình (read-only)

## Dependencies

- **Depends on**: Nhóm 2 (Room), Nhóm 3 (Tenant)
- **Blocks**: Nhóm 5 (Service — một số Service có thể override ở Lease),
  Nhóm 6 (Meter Reading — reading gắn với Lease active),
  Nhóm 7 (Invoice — Invoice generate từ Lease),
  Nhóm 8 (Payment — gián tiếp qua Invoice)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Lease Lifecycle (Computed Status)

Giống Room.status, Lease.status là **computed field**, không lưu DB (trừ
`terminated_at`). Transition chạy bằng **cron daily** (chung với Nhóm 3).

```
                   ┌─────────┐
    create  ─────→ │  draft  │  (today < start_date)
                   └────┬────┘
                        │ cron: today >= start_date
                        ↓
                   ┌─────────┐
                   │ active  │  (start_date ≤ today ≤ end_date - 30d)
                   └────┬────┘
                        │ cron: today > end_date - 30d
                        ↓
                   ┌──────────────┐
                   │expiring_soon │  (end_date - 30d < today ≤ end_date)
                   └──────┬───────┘
                          │ cron: today > end_date
                          ↓
                   ┌──────────┐
                   │ expired  │  (today > end_date)
                   └──────────┘

                   Bất kỳ lúc nào (draft/active/expiring_soon):
                   ┌────────────┐
                   │ terminated │  (terminated_at IS NOT NULL)
                   └────────────┘
```

**Detailed rules:**

| Status          | Điều kiện (computed)                                                    |
| --------------- | ----------------------------------------------------------------------- |
| `draft`         | `today < start_date` AND `terminated_at IS NULL`                        |
| `active`        | `start_date ≤ today ≤ (end_date - 30 days)` AND `terminated_at IS NULL` |
| `expiring_soon` | `(end_date - 30 days) < today ≤ end_date` AND `terminated_at IS NULL`   |
| `expired`       | `today > end_date` AND `terminated_at IS NULL`                          |
| `terminated`    | `terminated_at IS NOT NULL` (bất kể start/end_date)                     |

---

## Pro-rata Billing Rule

Áp dụng cho **mọi Lease**, không có option khác.

**Công thức:**

```
Cho Invoice tháng N của Lease:
  month_start = ngày 1 của tháng N
  month_end   = ngày cuối của tháng N (28/29/30/31)
  days_in_month = month_end - month_start + 1

  period_start = MAX(month_start, lease.start_date)
  period_end   = MIN(month_end, lease.effective_end_date)

  days_occupied = period_end - period_start + 1

  rent_amount = lease.rent_amount × days_occupied / days_in_month
```

Trong đó `effective_end_date` = `terminated_at::date` nếu terminated,
ngược lại = `end_date`.

**Ví dụ** (rent_amount = 3.000.000đ, tháng 3 có 31 ngày):

| Case                                     | days_occupied | Rent tính             |
| ---------------------------------------- | ------------- | --------------------- |
| start_date = 1/3, active cả tháng        | 31            | 3.000.000đ            |
| start_date = 5/3                         | 27            | 2.612.903đ (làm tròn) |
| start_date = 20/3                        | 12            | 1.161.290đ            |
| terminated 10/3, start từ trước 1/3      | 10            | 967.742đ              |
| start 5/3 + terminated 20/3 (cùng tháng) | 16            | 1.548.387đ            |

**Landlord kiểm soát chính sách qua date fields:**

| Tình huống thực tế                    | Cách Landlord xử lý          |
| ------------------------------------- | ---------------------------- |
| Tenant vào 5/3, tính full tháng 3     | Set `start_date = 1/3`       |
| Tenant vào 5/3, tính đúng 27 ngày     | Set `start_date = 5/3`       |
| Tenant vào 28/3, ở ké 3 ngày miễn phí | Set `start_date = 1/4`       |
| Tenant ra 15/6, đã đóng đủ tháng 6    | Set `terminated_date = 30/6` |
| Tenant ra 15/6, chỉ tính đến ngày đi  | Set `terminated_date = 15/6` |

**App không biết các chính sách này** — chỉ pro-rata theo ngày Landlord nhập.

**Note về làm tròn:**

MVP làm tròn đến **đồng** (không có lẻ). Dùng `ROUND(x, 0)`. Điều này có
thể gây sai số nhỏ 1-2đ khi cộng dồn, chấp nhận được ở MVP. Nếu Tenant
phản ánh → ghi rõ công thức trong Invoice (Nhóm 7).

---

## Stories

### US-050: Landlord tạo Lease mới

**As a** Landlord cần ký hợp đồng cho Tenant vào Room
**I want to** tạo Lease với đầy đủ thông tin hợp đồng
**So that** hệ thống bắt đầu tính tiền và quản lý thời hạn

**Priority**: Must
**Estimate**: L
**Depends on**: US-014 (Room tồn tại), US-030 (Tenant tồn tại)

**Acceptance Criteria:**

- [ ] AC1: Form tạo Lease có các trường:
  - `room_id` (bắt buộc, chọn từ Room **vacant** hoặc Room có Lease
    `expired`/`terminated`)
  - `tenant_id` (bắt buộc, chọn từ Tenant chưa có Lease active)
  - `start_date` (bắt buộc, có thể là ngày trong tương lai)
  - `end_date` (bắt buộc, phải > `start_date`, thường = `start_date + 6 tháng`
    hoặc `+12 tháng`)
  - `rent_amount` (bắt buộc, default = `Room.default_rent`, cho phép sửa)
  - `deposit_amount` (bắt buộc, default = `rent_amount × 1`, cho phép sửa)
  - `billing_day` (bắt buộc, default = 1, range 1-28) — ngày xuất Invoice
    hàng tháng
  - `note` (tuỳ chọn, free text max 500 ký tự) — điều khoản đặc biệt,
    VD: "Báo trước 30 ngày khi chấm dứt"
- [ ] AC2: Validation:
  - `end_date > start_date` (tối thiểu 1 ngày)
  - `end_date - start_date >= 30 days` (không cho hợp đồng quá ngắn — cảnh báo)
  - `rent_amount > 0`, `deposit_amount >= 0`
  - `billing_day` trong [1, 28] — tránh edge case tháng 2
- [ ] AC3: **Chặn tạo** nếu Room đã có Lease active/expiring_soon/draft:
  - Hiện lỗi: "Phòng [X] đã có hợp đồng [status] từ [start] đến [end].
    Vui lòng chấm dứt hợp đồng cũ trước."
- [ ] AC4: **Chặn tạo** nếu Tenant đã có Lease active ở Room khác (cùng Landlord):
  - Hiện lỗi: "Tenant [tên] đang thuê phòng [Y]. Một tenant chỉ có 1 Lease active."
  - _Exception_: Nếu Lease hiện tại của Tenant là `expiring_soon` hoặc
    `terminated` **đã xử lý deposit** → cho phép (trường hợp chuyển phòng)
- [ ] AC5: Tạo thành công:
  - Lease có `status = 'draft'` nếu `today < start_date`, ngược lại `active`
  - Set `deposit_status = 'held'`
  - Room.status auto cập nhật:
    - Lease `draft` → Room vẫn `vacant`
    - Lease `active` → Room `occupied`
  - Tenant.status auto cập nhật → `active`
- [ ] AC6: Sau khi tạo → redirect sang trang chi tiết Lease, có CTA:
  - "Ghi nhận thanh toán tiền cọc" (link sang Payment, v1.x)
  - "Tạo Invoice đầu tiên" (link sang Invoice, Nhóm 7)
- [ ] AC7: Chỉ Landlord sở hữu Property mới tạo được Lease

**Notes:**

- AC1 `billing_day`: Landlord có thể chọn ngày xuất Invoice khác nhau cho
  từng Lease. VD: Lease A xuất ngày 1, Lease B xuất ngày 5 (ngày Tenant
  nhận lương). MVP default = 1, Landlord ít khi đổi.
- AC2 `billing_day ≤ 28`: tránh trường hợp tháng 2 không có ngày 29/30/31.
  Alternative: dùng "ngày cuối tháng" hoặc "ngày 1 tháng sau" cho edge case,
  phức tạp hơn. MVP stick với [1, 28].
- AC4 exception: Case thực tế **chuyển phòng trong cùng nhà**. Bảo có 1
  Tenant đang thuê phòng 101, hết hạn muốn chuyển sang phòng 201 (rộng hơn).
  Không cần terminate rồi re-invite, chỉ cần Lease cũ expired/terminated
  là OK.
- AC5: Room status là **computed** từ Lease status (xem Nhóm 2 US-016).
  Không phải update trực tiếp Room.status.
- `deposit_amount = 0` được phép: case Landlord miễn cọc cho Tenant quen.

---

### US-051: Landlord xem danh sách và chi tiết Lease

**As a** Landlord
**I want to** xem danh sách Lease và chi tiết từng hợp đồng
**So that** tôi nắm được tình hình tất cả hợp đồng đang quản lý

**Priority**: Must
**Estimate**: S
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: Trang danh sách hiển thị: Room.display_name, Tenant.full_name,
      start_date, end_date, rent_amount, status (với badge màu)
- [ ] AC2: Status badge màu:
  - `draft` → xám
  - `active` → xanh lá
  - `expiring_soon` → vàng (có icon chuông)
  - `expired` → đỏ
  - `terminated` → đen/xám đậm
- [ ] AC3: Filter:
  - Theo Property / Room
  - Theo status (multi-select)
  - Theo ngày: "Sắp hết hạn trong 30/60/90 ngày"
- [ ] AC4: Sort: default theo `end_date ASC` (sắp hết hiện trước), có thể
      đổi sang `created_at DESC`
- [ ] AC5: Trang chi tiết Lease hiển thị:
  - **Thông tin cơ bản**: Room (link), Tenant (link), start/end_date,
    status, rent, deposit, billing_day, note
  - **Deposit**: deposit_amount, deposit_status, deposit_returned_amount,
    deposit_settlement_note, deposit_settled_at
  - **Timeline**: ngày tạo, ngày active, ngày terminated (nếu có)
  - **Invoice list**: danh sách Invoice của Lease này (link sang Nhóm 7)
  - **Actions** (tuỳ status): Sửa, Chấm dứt, Gia hạn, Xử lý cọc
- [ ] AC6: Chỉ Landlord sở hữu mới xem được Lease của mình (RBAC)

---

### US-052: Landlord sửa Lease (trước khi active)

**As a** Landlord lỡ tạo Lease sai thông tin
**I want to** sửa Lease khi còn ở status `draft`
**So that** dữ liệu đúng trước khi có hiệu lực, tránh phải terminate rồi tạo lại

**Priority**: Must
**Estimate**: M
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: Nút "Sửa" chỉ hiện khi Lease.status = `draft` (chưa đến `start_date`)
- [ ] AC2: Cho phép sửa: `start_date`, `end_date`, `rent_amount`,
      `deposit_amount`, `billing_day`, `note`
- [ ] AC3: **Không cho sửa**: `room_id`, `tenant_id` (nếu nhầm → delete Lease
      và tạo mới — xem US-053)
- [ ] AC4: Validation như US-050 AC2, AC3, AC4
- [ ] AC5: **Với Lease active**: chỉ cho sửa `end_date` (gia hạn/rút ngắn) và
      `note`. Các field khác (rent, deposit) không sửa được vì đã có Invoice/
      Payment tham chiếu.
  - Nếu muốn đổi rent → tạo Lease mới (renewal — US-054)
- [ ] AC6: Với Lease `expiring_soon`/`expired`/`terminated`: không cho sửa
      (read-only)
- [ ] AC7: Audit log: ghi lại ai sửa, sửa gì, lúc nào (MVP log DB, v1.x có UI)

**Notes:**

- AC5 design quan trọng: **Lease active gần như immutable**. Chỉ cho sửa
  note + end_date. Lý do: Invoice tháng trước đã tính theo rent_amount cũ,
  sửa giữa chừng làm sai audit. Landlord muốn đổi → end hợp đồng + tạo mới.
- Alternative: cho sửa hết, nhưng track version. Quá phức tạp cho MVP.

---

### US-053: Landlord xoá Lease (chỉ khi draft, chưa có side effect)

**As a** Landlord tạo nhầm Lease (sai Tenant, sai Room)
**I want to** xoá Lease khi chưa có hệ quả
**So that** data sạch, không cần để lại Lease "rác"

**Priority**: Should
**Estimate**: S
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: Nút "Xoá" chỉ hiện khi:
  - Lease.status = `draft`
  - **Và** không có Invoice nào tham chiếu đến Lease
  - **Và** không có Payment nào ghi nhận deposit của Lease
- [ ] AC2: Click "Xoá" → confirm dialog: "Xoá Lease này? Hành động không thể hoàn tác."
- [ ] AC3: Xoá thành công:
  - Hard delete Lease record
  - Room.status update lại (về `vacant` nếu Room không còn Lease nào)
  - Tenant.status update lại (về `pending` nếu Tenant không còn Lease nào)
- [ ] AC4: Các Lease khác (active, expired, terminated) **không xoá được**,
      phải terminate hoặc giữ nguyên cho audit

**Notes:**

- Hard delete ở MVP vì Lease draft chưa có hệ quả (chưa tính Invoice, chưa
  thu deposit). Safe to delete.
- Lease active có thể bị terminate nhầm → dùng "undo terminate" (v1.x) thay
  vì xoá.

---

### US-054: Landlord gia hạn Lease (tạo Lease mới nối tiếp)

**As a** Landlord khi Lease hiện tại sắp/đã hết hạn và Tenant muốn ở tiếp
**I want to** tạo Lease mới nối tiếp Lease cũ
**So that** ghi nhận đúng việc tái ký, có thể đổi giá/điều khoản, giữ
lịch sử rõ ràng

**Priority**: Should
**Estimate**: M
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: Nút "Gia hạn" hiện khi Lease.status ∈ {`expiring_soon`, `expired`}
- [ ] AC2: Click → mở form tạo Lease mới **pre-fill** từ Lease cũ:
  - `room_id`, `tenant_id`: copy, không cho sửa
  - `start_date`: default = `old_lease.end_date + 1 day`, cho phép sửa
  - `end_date`: default = `start_date + (old_lease_duration)` (cùng độ dài)
  - `rent_amount`: default = copy từ Lease cũ (Landlord thường tăng giá)
  - `deposit_amount`: default = `old_lease.deposit_amount` (thường giữ nguyên,
    không thu thêm cọc)
  - `billing_day`: copy
  - `note`: để trống (điều khoản mới)
- [ ] AC3: Nếu chọn `deposit_amount` giống Lease cũ → hiện option:
  - "Chuyển cọc cũ sang Lease mới" (mặc định checked): giữ nguyên deposit,
    không tạo Payment mới. Lease cũ set `deposit_status = 'returned'`,
    `deposit_returned_amount = 0`, `deposit_settlement_note = 'Chuyển cọc
sang Lease #[new_lease_id]'`. Lease mới nhận deposit_amount bằng cọc cũ.
  - "Thu cọc mới": tạo Lease mới với deposit riêng, Lease cũ xử lý deposit
    bình thường (return/deduct qua US-056)
- [ ] AC4: Nếu `deposit_amount` khác → bắt buộc chọn 1 trong 2:
  - Trả lại cọc cũ + thu cọc mới
  - Bù chênh lệch (nếu deposit mới > cũ: Tenant đóng thêm; nếu < cũ:
    Landlord trả lại phần dư)
- [ ] AC5: Validation:
  - `start_date` của Lease mới phải > `end_date` của Lease cũ
    (hoặc = `terminated_date + 1` nếu cũ bị terminate)
  - Không được overlap với Lease cũ
- [ ] AC6: Tạo thành công:
  - Lease mới có link "renewed_from" → Lease cũ (để xem lịch sử)
  - Lease cũ: nếu chưa expire, tự động set `end_date = new_lease.start_date - 1`
    để chấm dứt đúng ngày
- [ ] AC7: Trên trang chi tiết Lease, hiển thị timeline: "Lease #123 →
      Lease #456 (gia hạn) → ..."

**Notes:**

- AC3 deposit rollover: **đã chốt**. Không thêm status mới, dùng `returned`
  với amount=0 + note rõ ràng. Ưu điểm: giữ schema đơn giản, dễ query
  "deposit đã xử lý chưa" (chỉ cần check `deposit_status != 'held'`).
- AC4: Bù chênh lệch là **case phức tạp**. MVP có thể force option 1
  (trả hết + thu mới) cho đơn giản. v1.x add option bù chênh lệch.
- Renewal là action **quan trọng nhưng không cấp thiết**: Tenant có thể
  ký hợp đồng mới bình thường (US-050) mà không dùng flow này. Flow này
  chủ yếu để **pre-fill data + link lịch sử**, tăng UX.

---

### US-055: Landlord chấm dứt Lease sớm (terminate)

**As a** Landlord khi Tenant dọn đi trước hạn hoặc vi phạm hợp đồng
**I want to** chấm dứt Lease với lý do và ngày cụ thể
**So that** hệ thống ngừng tính Invoice tháng sau, có căn cứ xử lý deposit

**Priority**: Must
**Estimate**: L
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: Nút "Chấm dứt" hiện khi Lease.status ∈ {`draft`, `active`, `expiring_soon`}
- [ ] AC2: Click → form terminate:
  - `terminated_date` (bắt buộc, default = today, range: `start_date` → `end_date`)
  - `termination_reason` (bắt buộc, enum):
    - `tenant_moved_out_on_time`: Tenant dọn đúng hạn, báo trước đủ
    - `tenant_moved_out_early`: Tenant dọn sớm, đã thoả thuận OK
    - `tenant_breach`: Tenant vi phạm (không trả tiền, phá phòng...)
    - `landlord_request`: Landlord yêu cầu (lý do đặc biệt)
    - `mutual_agreement`: Thoả thuận chung
  - `termination_note` (tuỳ chọn, free text)
- [ ] AC3: Pre-check và hiển thị thông tin:
  - Liệt kê Invoice `unpaid`/`partial` của Lease (nếu có)
  - Liệt kê Occupant đang active (nếu có) — sẽ xử lý thế nào?
  - Tổng nợ (nếu có): sum unpaid invoices
  - Gợi ý xử lý deposit (xem AC4)
- [ ] AC4: **Gợi ý deposit_status** dựa vào `termination_reason` + tổng nợ:
  - `tenant_breach` + có nợ → gợi ý `forfeited` hoặc `deducted`
  - `tenant_moved_out_on_time` + không nợ → gợi ý `returned`
  - `tenant_moved_out_early` + không nợ → gợi ý `returned`
  - Tất cả chỉ là **gợi ý**, Landlord tự chọn khi xử lý deposit (US-056)
- [ ] AC5: Confirm dialog:
      "Chấm dứt Lease [X] từ ngày [terminated_date]?
      Lý do: [reason]
      Hệ thống sẽ:
  - Set status = terminated
  - Tạo Invoice cuối cùng pro-rata đến ngày [terminated_date] (nếu chưa có Invoice tháng đó)
  - Đánh dấu Occupant active → moved_out_date = [terminated_date]
  - **Chưa xử lý deposit** — bạn sẽ xử lý ở bước sau"
- [ ] AC6: Terminate thành công:
  - Set `terminated_at = now()`, `terminated_date = input`, `termination_reason`,
    `termination_note`
  - Lease.status → `terminated`
  - Room.status → `vacant` (nếu không có Lease khác)
  - Occupant của Tenant (cùng Room) → set `moved_out_date = terminated_date`
  - Tenant.status: vẫn giữ (không archive) cho đến khi deposit xử lý xong
    (US-056)
  - Tự động tạo **Invoice tháng cuối** nếu chưa có (pro-rata theo `terminated_date`)
    — chi tiết ở Nhóm 7
- [ ] AC7: Redirect sang trang chi tiết Lease với CTA nổi bật: "Xử lý tiền cọc"

**Notes:**

- AC2 enum reason giúp phân loại case cho Nhóm 7 (Invoice settlement) và
  cho analytics sau này (bao nhiêu % terminate do breach?).
- AC4 chỉ là **gợi ý UX**, không phải ràng buộc. Landlord có thể phá rule
  (VD: breach nhưng vẫn trả cọc cho đẹp).
- AC6 Invoice tháng cuối auto-tạo: **design choice**. Alternative: Landlord
  tạo tay. Auto tạo tốt hơn vì Landlord ít quên. Nhưng edge case: nếu
  Invoice tháng đó đã tồn tại (Landlord tạo trước) → chỉ update, không tạo
  mới. Sẽ detail ở Nhóm 7.
- AC6 Tenant.status giữ nguyên: **design quan trọng**. Archive Tenant
  (US-033 Nhóm 3) chỉ khi deposit đã xử lý xong. Tránh case Tenant archive
  nhưng còn deposit treo.

---

### US-056: Landlord xử lý tiền cọc sau khi terminate/expire

**As a** Landlord sau khi Lease kết thúc (terminate hoặc expired)
**I want to** ghi nhận việc đã xử lý tiền cọc (trả lại / giữ lại / trừ)
**So that** có audit trail rõ ràng, biết đã thanh lý hợp đồng xong

**Priority**: Must
**Estimate**: M
**Depends on**: US-055

**Acceptance Criteria:**

- [ ] AC1: Nút "Xử lý cọc" hiện khi:
  - Lease.status ∈ {`terminated`, `expired`}
  - Và `deposit_status = 'held'` (chưa xử lý)
- [ ] AC2: Form xử lý cọc:
  - **Tóm tắt**: deposit_amount gốc, tổng Invoice unpaid còn lại (nếu có)
  - `deposit_status` (bắt buộc, radio):
    - `returned`: Trả lại cọc (có thể trừ hỏng hóc/dịch vụ tháng cuối)
    - `forfeited`: Mất cọc toàn bộ (Tenant vi phạm)
    - `deducted`: Lấy cọc bù nợ (tiền phòng/dịch vụ chưa trả)
  - `deposit_returned_amount` (bắt buộc nếu chọn `returned` hoặc `deducted`):
    - Với `returned`: số tiền thực trả lại (≤ deposit_amount)
    - Với `deducted`: số tiền còn dư sau khi bù nợ (≥ 0)
    - Với `forfeited`: auto = 0, disable input
  - `deposit_settlement_note` (bắt buộc, free text min 20 ký tự):
    - Ghi rõ đã trừ gì, ví dụ: "Trừ 500k tiền điện tháng 6, 200k sửa cửa,
      trả lại 2.3M cho Tenant ngày 15/6"
- [ ] AC3: Validation:
  - `deposit_returned_amount >= 0`
  - `deposit_returned_amount <= deposit_amount`
- [ ] AC4: **Cảnh báo** (không chặn) nếu còn Invoice unpaid và chọn `returned`:
  - "Tenant còn [X] đồng chưa trả. Bạn chắc chắn muốn trả lại cọc đầy đủ?"
- [ ] AC5: Submit thành công:
  - Set `deposit_status`, `deposit_returned_amount`,
    `deposit_settlement_note`, `deposit_settled_at = now()`
  - Tenant.is_archived = true, Tenant.archived_at = now(),
    Tenant.move_out_date = Lease.terminated_date ?? Lease.end_date
  - Invalidate Tenant's User account (không cho login nữa)
- [ ] AC6: Sau submit → trang chi tiết Lease hiển thị kết quả:
  - "Đã xử lý cọc ngày [X]: [status], trả lại [amount]. Tenant [tên] đã dọn đi."
- [ ] AC7: Có thể **sửa lại** trong 7 ngày nếu nhập sai
      (unarchive Tenant, reset deposit_status về `held`, v.v.) — v1.x
- [ ] AC8: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC2 `deposit_settlement_note` bắt buộc và min 20 ký tự: ép Landlord
  ghi lại chi tiết, tránh tranh chấp sau này. 20 ký tự là threshold hợp lý
  để ghi ít nhất 1 câu.
- AC5 auto-archive Tenant: đây là **cầu nối** giữa Lease và Tenant lifecycle.
  Logic từ US-033 Nhóm 3 (archive Tenant) giờ trigger tự động.
- AC7 undo window 7 ngày: quan trọng vì Landlord có thể xử lý sai cọc
  (nhập nhầm số). MVP có thể skip, v1.x add.
- **Không tạo Payment record cho việc trả cọc**: MVP giữ deposit là
  trạng thái của Lease, không phải giao dịch riêng. Alternative: tạo
  Payment type=deposit_return. Phức tạp, không cần MVP.

---

### US-057: Lease auto-transition status (cron daily)

**As a** hệ thống (cron job)
**I want to** chuyển Lease.status đúng lúc khi đến ngày
**So that** Landlord thấy status cập nhật mỗi ngày mà không cần thao tác

**Priority**: Must
**Estimate**: M
**Depends on**: US-050

**Acceptance Criteria:**

- [ ] AC1: **Daily Status Maintenance Cron** chạy **mỗi ngày lúc 00:05**.
      Đây là **cron job duy nhất** cho status maintenance của toàn hệ thống,
      xử lý cả Lease, Tenant, và các trigger khác. Xem chi tiết trong Ghi
      chú kiến trúc cuối file.
- [ ] AC2: Logic check Lease status (pseudo-code):
  ```
  FOR each Lease WHERE terminated_at IS NULL:
    IF today < start_date: computed_status = 'draft'
    ELSE IF today <= end_date - 30 days: computed_status = 'active'
    ELSE IF today <= end_date: computed_status = 'expiring_soon'
    ELSE: computed_status = 'expired'
  ```
- [ ] AC3: **Lease là computed status** — cron không UPDATE DB cho 4 status
      `draft/active/expiring_soon/expired`. Chỉ `terminated` lưu DB qua
      `terminated_at`.
- [ ] AC4: **Side effects khi status chuyển**:
  - `draft → active`: Room.status → `occupied` (computed tự động theo Nhóm 2)
  - `active → expiring_soon`: trigger notification cho Landlord
    (v1.x: email/push, MVP: chỉ hiện UI badge vàng + dashboard)
  - `expiring_soon → expired`: trigger notification cho Landlord
    ("Lease [X] đã hết hạn, cần quyết định gia hạn hay terminate")
    - Room.status → `lease_expired` (Nhóm 2 US-016)
- [ ] AC5: Cron log: số Lease check, số Lease đổi status, errors nếu có
- [ ] AC6: Cron idempotent: chạy 2 lần liên tiếp → kết quả như 1 lần

**Notes:**

- Thực ra vì status là computed, không cần UPDATE DB. Cron chỉ để **trigger
  notifications** khi status chuyển. MVP không có notification → cron gần
  như không làm gì cho Lease, nhưng vẫn giữ structure để v1.x plug notification.
- Alternative: tính status on-the-fly mỗi khi query. Đã chọn ở Nhóm 2 và 3.
- AC4 `expired` Lease + Room.status `lease_expired`: đây là status đặc biệt
  ở Nhóm 2 để Landlord thấy "Tenant còn ở nhưng hợp đồng hết hạn, cần xử lý".

---

### US-058: Landlord xem cảnh báo Lease sắp hết hạn

**As a** Landlord
**I want to** thấy danh sách Lease sắp/đã hết hạn ngay trên dashboard
**So that** tôi không quên gia hạn/xử lý, giảm rủi ro mất kiểm soát

**Priority**: Should
**Estimate**: S
**Depends on**: US-057

**Acceptance Criteria:**

- [ ] AC1: Trên dashboard Landlord, có widget "Hợp đồng cần chú ý":
  - Section 1: "Sắp hết hạn" — Lease có status `expiring_soon`
  - Section 2: "Đã hết hạn" — Lease có status `expired`
  - Section 3: "Cọc chưa xử lý" — Lease terminated/expired + `deposit_status = 'held'`
- [ ] AC2: Mỗi item hiển thị: Room.display_name, Tenant.full_name, end_date,
      số ngày còn/đã quá
- [ ] AC3: Click → chuyển sang trang chi tiết Lease
- [ ] AC4: Section rỗng → hiện empty state thân thiện
      ("Không có hợp đồng cần xử lý 🎉")
- [ ] AC5: Update real-time khi load dashboard (query DB mỗi lần)

**Notes:**

- Widget này **không phải notification** thực sự (không push/email). Chỉ là
  UI nhắc khi Landlord vào app. v1.x mới có notification thật.
- Có thể tách thành "Cần xử lý hôm nay" widget chung với các reminder khác
  (Invoice unpaid, Meter reading chưa nhập...) — design sau ở Phase 3/4.

---

### US-059: Tenant xem Lease của mình

**As a** Tenant đã login
**I want to** xem hợp đồng hiện tại và lịch sử hợp đồng của mình
**So that** tôi biết thời hạn, giá thuê, điều khoản, ngày hết hạn

**Priority**: Must
**Estimate**: S
**Depends on**: US-050, US-005 (Tenant login)

**Acceptance Criteria:**

- [ ] AC1: Trên trang chủ của Tenant, hiển thị Lease hiện tại:
  - Room (tên, địa chỉ Property)
  - start_date, end_date
  - Status (badge màu như US-051)
  - rent_amount, deposit_amount, billing_day
  - Số ngày còn lại đến `end_date` (nếu active/expiring_soon)
- [ ] AC2: Có section "Lịch sử hợp đồng" hiển thị các Lease cũ (expired/
      terminated) nếu có — chỉ xem, read-only
- [ ] AC3: Tenant **không thấy**: `termination_note`, `deposit_settlement_note`
      (là ghi chú nội bộ của Landlord)
- [ ] AC4: Tenant **thấy**: `note` của Lease (điều khoản thoả thuận, công khai)
- [ ] AC5: Nếu Lease `expiring_soon` → hiện CTA: "Liên hệ chủ nhà để gia hạn"
      với SĐT Landlord
- [ ] AC6: Tenant **không có quyền** sửa/chấm dứt Lease (chỉ Landlord làm)
- [ ] AC7: Nếu Tenant đã archive (dọn đi) + account bị invalidate → không
      login được, không cần handle case này ở đây

**Notes:**

- AC3 quan trọng cho privacy: Landlord ghi note nội bộ (VD: "Tenant khó
  chịu, không gia hạn") → Tenant không nên thấy.
- v1.x có thể thêm: Tenant download/export Lease thành PDF để lưu.

---

## Open Questions (cần trả lời trước Phase 3)

1. ~~**Deposit rollover khi renewal (US-054 AC3)**~~ **CHỐT**: Giữ 4 status
   hiện tại (`held/returned/forfeited/deducted`). Khi rollover → set
   `deposit_status = 'returned'`, `deposit_returned_amount = 0`, note ghi
   rõ "Chuyển cọc sang Lease #XXX". Không thêm status mới.

2. **Billing day edge cases**: hiện chặn ở [1, 28]. Case Landlord muốn
   billing ngày cuối tháng (28/29/30/31) → xử lý thế nào? Bỏ qua cho MVP?
   - Đề xuất: **MVP chặn [1, 28]**, note rõ trong tooltip. v1.x mở rộng nếu cần.

3. **Co-sign Lease** (2 Tenant cùng đứng tên): đã defer sang v2.x ở Nhóm 3.
   Cần bỏ hoàn toàn khỏi scope MVP → xác nhận.

4. **Auto Invoice cuối cùng khi terminate (US-055 AC6)**: tạo tự động hay
   Landlord tạo tay?
   - Đề xuất: **Auto tạo** nhưng đánh dấu là "draft invoice", Landlord phải
     review + confirm trước khi "finalize". Chi tiết ở Nhóm 7.

5. **Lease extension thay vì renewal**: Bảo đã chốt renewal (tạo mới). Có
   case nào đơn giản chỉ extend end_date không? VD: Landlord + Tenant đồng
   ý kéo dài thêm 1 tháng, giữ nguyên giá.
   - Đề xuất: **Vẫn tạo Lease mới** cho nhất quán. Nếu muốn extend mà không
     đổi gì → copy Lease rất nhanh (US-054 pre-fill).

6. ~~**Grace period cho expired Lease**~~ **CHỐT**: Tenant còn ở sau
   `end_date` nhưng chưa ký mới → **vẫn tính Invoice theo rent_amount cũ**.
   Lease ở status `expired` + Room status `lease_expired`. Landlord thấy
   cảnh báo, phải gia hạn (US-054) hoặc terminate (US-055). Grace period
   là **ở tạm**, không miễn phí.

## Ghi chú kiến trúc cho Phase 3

**Daily Status Maintenance Cron** (kiến trúc tổng):

```
┌────────────────────────────────────────────┐
│ Cron: 00:05 daily                          │
├────────────────────────────────────────────┤
│ Task 1: Check Lease status transitions     │
│   - Trigger notifications khi đổi status  │
│   - KHÔNG UPDATE DB (status computed)      │
│                                            │
│ Task 2: Check Tenant status transitions    │
│   - Trigger notifications                  │
│   - KHÔNG UPDATE DB (status computed)      │
│                                            │
│ Task 3: Room status                        │
│   - Không cần check (derive từ Lease)      │
│                                            │
│ Task 4: Future v1.x — invoice reminders,  │
│         notification delivery, etc.        │
├────────────────────────────────────────────┤
│ Output: Log file (count + errors)          │
│ Property: Idempotent (chạy 2 lần = 1 lần) │
└────────────────────────────────────────────┘
```

**Lưu ý**: MVP không có notification thật (email/push), nên cron task 1-3
gần như no-op về side effects. Nhưng giữ structure để v1.x plug notification
vào dễ dàng. Xem Phase 3 ADR "Cron job architecture" để chi tiết.

**Entity Relationships (preview):**

```
Room         1──* Lease  (1 Room có nhiều Lease qua thời gian, chỉ 1 active)
Tenant       1──* Lease  (1 Tenant có thể có nhiều Lease nối tiếp, VD: đổi phòng)
Lease        1──* Invoice (1 Lease sinh nhiều Invoice hàng tháng)
Lease        0──1 Lease  (renewed_from: Lease mới tham chiếu Lease cũ)
```

**Trường DB dự kiến:**

```
Lease:
  id, landlord_id (FK, denormalized — qua Room → Property → Landlord),
  room_id (FK), tenant_id (FK),
  start_date, end_date,
  rent_amount, deposit_amount, billing_day,
  note,
  -- Termination
  terminated_at (nullable), terminated_date (nullable),
  termination_reason (nullable, enum),
  termination_note (nullable, text),
  -- Deposit settlement
  deposit_status (enum: held/returned/forfeited/deducted, default 'held'),
  deposit_returned_amount (nullable, decimal),
  deposit_settlement_note (nullable, text),
  deposit_settled_at (nullable),
  -- Renewal link
  renewed_from_lease_id (nullable, FK self),
  created_at, updated_at

  CONSTRAINT: UNIQUE(room_id) WHERE status IN ('draft', 'active', 'expiring_soon')
    -- 1 Room không thể có 2 Lease non-terminal cùng lúc
    -- Note: status là computed, nên constraint này phải implement qua
    -- partial unique index trên các cột date, hoặc application-level check
```

**Computed fields (không lưu DB):**

- `Lease.status`: derive từ start_date, end_date, terminated_at, today
- `Lease.days_remaining`: end_date - today (nếu active/expiring_soon)
- `Lease.total_invoiced`: sum Invoice.total_amount của Lease
- `Lease.total_unpaid`: sum Invoice unpaid của Lease

**Pro-rata calculation:** implement ở Nhóm 7 (Invoice generation). Lease
chỉ cung cấp `start_date`, `end_date`, `terminated_date`, `rent_amount`.

Sẽ finalize ở Phase 3 (Architecture + Database Design).

---

## Summary

| Story  | Title                                      | Priority | Estimate |
| ------ | ------------------------------------------ | -------- | -------- |
| US-050 | Landlord tạo Lease mới                     | Must     | L        |
| US-051 | Landlord xem danh sách và chi tiết Lease   | Must     | S        |
| US-052 | Landlord sửa Lease (trước active)          | Must     | M        |
| US-053 | Landlord xoá Lease (chỉ draft)             | Should   | S        |
| US-054 | Landlord gia hạn Lease (renewal)           | Should   | M        |
| US-055 | Landlord chấm dứt Lease sớm (terminate)    | Must     | L        |
| US-056 | Landlord xử lý tiền cọc sau Lease kết thúc | Must     | M        |
| US-057 | Lease auto-transition status (cron)        | Must     | M        |
| US-058 | Landlord xem cảnh báo Lease sắp hết hạn    | Should   | S        |
| US-059 | Tenant xem Lease của mình                  | Must     | S        |

**Total**: 10 stories, trong đó 7 Must + 3 Should.
**Estimate**: 3L + 4M + 3S ≈ 2–3 sprint.
