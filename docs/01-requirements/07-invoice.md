# User Stories — Nhóm 7: Invoice (Hoá đơn)

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-18
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **Invoice (Hoá đơn)** — entity tổng hợp tất cả khoản
thu hàng tháng cho mỗi Lease. Đây là **nhóm phức tạp nhất** trong MVP vì
tổng hợp data từ Lease (rent), Service (fixed/per_person), và Meter Reading
(per_meter).

**Map với Vision:**

- MVP feature #6: Tự động tính hoá đơn tháng (tiền phòng + dịch vụ)
- MVP feature #7: Xem hoá đơn (Landlord + Tenant view)

**Key decisions (đã chốt):**

| #   | Decision                                                       | Lý do                                        |
| --- | -------------------------------------------------------------- | -------------------------------------------- |
| 1   | Invoice status lifecycle: `draft` → `unpaid` → `partial` → `paid` + `void` | Cover đủ các trạng thái thực tế        |
| 2   | No `draft` trong DB: dùng preview in-memory + commit           | Đơn giản hoá state                           |
| 3   | Preview-before-commit pattern (batch per Property)             | Landlord review trước khi tạo hàng loạt     |
| 4   | Individual mode: xuất 1 Invoice riêng (edge case)              | Linh hoạt cho terminate giữa tháng           |
| 5   | Invoice Immutability TUYỆT ĐỐI sau khi tạo                     | Audit, legal document                        |
| 6   | Void Invoice thay vì delete, void tạo Invoice mới replacement  | Audit trail + recreate workflow              |
| 7   | Adjustment = manual line trong Invoice tháng sau               | Tenant thấy 1 Invoice duy nhất với breakdown |
| 8   | Line items flatten với description gộp chỉ số                  | Đơn giản UI, dễ hiển thị                     |
| 9   | Billing period per line item (không chỉ per Invoice)           | Điện tháng 4 + rent tháng 5 cùng Invoice     |
| 10  | Per_person snapshot tại thời điểm tạo Invoice                  | Match workflow Landlord xuất đầu tháng       |
| 11  | In-app delivery only (MVP), Landlord nhắc Zalo thủ công        | Match Vision invoice flow                    |

## Personas liên quan

- **Landlord** (Persona A): tạo, xem, void Invoice
- **Tenant** (Persona B): xem Invoice của mình (read-only)

## Dependencies

- **Depends on**: Nhóm 4 (Lease — rent, pro-rata), Nhóm 5 (Service), Nhóm 6
  (Meter Reading — consumption)
- **Blocks**: Nhóm 8 (Payment — payment gắn với Invoice)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Core Concepts

### Invoice Status Lifecycle

```
       (preview in-memory, không lưu DB)
               │
               │ Landlord confirm
               ↓
         ┌──────────┐
         │  unpaid  │ ← Invoice vừa tạo, Tenant thấy trên app
         └────┬─────┘
              │
      ┌───────┼───────────────────┐
      │       │                   │
      ↓       ↓                   ↓
┌──────────┐ ┌──────┐        ┌─────────┐
│ partial  │ │ paid │        │  void   │
└────┬─────┘ └──────┘        └─────────┘
     │        (cuối)           (Landlord huỷ)
     │
     ↓ (Payment thêm)
   paid
```

**Rules:**
- `unpaid` → `partial`: có Payment < tổng Invoice
- `partial` → `paid`: Payment tích luỹ = tổng Invoice
- `unpaid`/`partial` → `paid`: 1 Payment đủ
- Bất kỳ → `void`: Landlord huỷ (chỉ được khi chưa có Payment)
- `paid` → không đổi được (immutable sau paid)

### Billing Period Pattern

**Quan trọng:** Invoice có `billing_month` chung, nhưng **mỗi line item có
`period_month` riêng**.

**Ví dụ Invoice tháng 5/2026:**
- `invoice.billing_month = 2026-05`
- Line "Tiền phòng": `period_month = 2026-05`
- Line "Điện": `period_month = 2026-04` (consumption tháng 4)
- Line "Nước": `period_month = 2026-04`
- Line "Rác": `period_month = 2026-05`
- Line "Internet": `period_month = 2026-05`

Lý do: điện nước "billing in arrears" (tháng trước), rent + fixed "billing
in advance" (tháng này).

### Invoice Immutability Pattern

**Một khi Invoice tạo (status ≠ preview), các field sau TUYỆT ĐỐI immutable:**

- Line items (content, price, quantity)
- `total_amount`
- `billing_month`
- `tenant_id`, `lease_id`, `room_id`

**Chỉ được thay đổi:**
- `status` (unpaid → partial → paid, hoặc void)
- Payment records (add Payment → tự tính lại status)
- Adjustment line (add vào Invoice **tháng sau**, không vào Invoice cũ)

**Hệ quả thực tế:**
- Service đổi giá → Invoice cũ giữ giá cũ
- Reading sửa → Invoice cũ KHÔNG update
- Sai Invoice → **Void + Recreate**, không edit

### Invoice Generation Logic (tổng quan)

Khi Landlord yêu cầu xuất Invoice tháng N cho Property:

```python
def generate_invoice_for_lease(lease, billing_month):
    line_items = []
    
    # 1. Rent (pro-rata theo Nhóm 4)
    rent_amount = calculate_prorata_rent(lease, billing_month)
    line_items.append({
        'line_type': 'rent',
        'description': f'Tiền phòng tháng {billing_month}',
        'period_month': billing_month,
        'quantity': 1,
        'unit': 'tháng',
        'unit_price': lease.rent_amount,
        'amount': rent_amount,
    })
    
    # 2. Services for Room
    for service in active_services_for_room(lease.room):
        if service.billing_type == 'fixed':
            line_items.append(build_fixed_line(service, billing_month))
        elif service.billing_type == 'per_person':
            n_persons = count_active_persons(lease.room, now())  # snapshot NOW
            line_items.append(build_per_person_line(service, n_persons, billing_month))
        elif service.billing_type == 'per_meter':
            # Consumption of billing_month - 1 (Option B Nhóm 6)
            prev_month = billing_month - 1
            consumption = calculate_consumption(service, lease.room, prev_month)
            if consumption is not None:
                line_items.append(build_per_meter_line(service, consumption, prev_month))
    
    return Invoice(
        lease_id=lease.id,
        room_id=lease.room_id,
        tenant_id=lease.tenant_id,
        billing_month=billing_month,
        line_items=line_items,
        total_amount=sum(li.amount for li in line_items),
        status='unpaid',
    )
```

---

## Stories

### US-080: Landlord xem preview và xuất Invoice (batch per Property)

**As a** Landlord đầu tháng, đã nhập reading xong
**I want to** xuất Invoice cho tất cả Lease active trong 1 Property cùng lúc
**So that** nhanh gọn, không làm từng phòng 1

**Priority**: Must
**Estimate**: L
**Depends on**: US-050 (Lease), US-060 (Service), US-071 (Meter Reading)

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Property, có nút "Xuất Invoice tháng
      [current_month]"
- [ ] AC2: Click → hệ thống **tính toán trong memory** (chưa lưu DB):
  - Duyệt tất cả Lease có status ∈ {`active`, `expiring_soon`, `expired`}
    thuộc Property (draft/terminated bỏ qua)
  - Với mỗi Lease: generate Invoice theo logic ở "Invoice Generation Logic"
  - Flag các Lease có issue:
    - Thiếu reading cho Service per_meter của tháng trước → cảnh báo
      "Chưa có chỉ số tháng [prev_month] cho phòng [X]"
    - Lease đã có Invoice tháng billing_month → cảnh báo "Đã có Invoice
      tháng [X] cho phòng [Y]" (prevent duplicate)
- [ ] AC3: Preview screen hiện:
  - Bảng tổng hợp: Room | Tenant | Status Lease | Tổng Invoice | Issues
  - Nếu có issue → row highlight vàng
  - Footer: tổng số Invoice sẽ tạo, tổng tiền
  - Click row → expand xem chi tiết line items
- [ ] AC4: **Landlord có thể exclude từng Lease** khỏi batch (checkbox):
  - VD: Lease thiếu reading → Landlord chọn bỏ qua, tạo sau
- [ ] AC5: Nút "Xác nhận và xuất":
  - Chỉ enable khi ≥ 1 Lease được tick
  - Disable với tooltip nếu tất cả bị exclude
- [ ] AC6: Click "Xác nhận" → confirm dialog:
  - "Tạo [N] Invoice với tổng tiền [X]đ? Sau khi tạo, Invoice sẽ hiện
    cho Tenant và không sửa được nữa."
- [ ] AC7: Submit → tạo Invoice records atomic trong 1 transaction:
  - Tất cả Invoice lưu với status = `unpaid`
  - Line items snapshot đầy đủ (service_name, unit_price, unit, period_month)
  - Rollback nếu có lỗi giữa chừng
- [ ] AC8: Sau submit → redirect về trang chi tiết Property với message:
  - "Đã xuất [N] Invoice tháng [X]. Tổng: [Y]đ"
  - Widget hiện Invoice mới tạo với nút copy link cho Zalo
- [ ] AC9: Validation rule chặn submit:
  - Không cho tạo Invoice cho tháng trong tương lai (VD: tháng 7 khi today
    là tháng 5). Cho tháng hiện tại và quá khứ OK.
  - Không cho tạo duplicate cho cùng (lease_id, billing_month) — đã có
    Invoice non-void thì chặn (cần void cũ trước)
- [ ] AC10: Chỉ Landlord sở hữu Property thực hiện được

**Notes:**

- AC2 "in memory": không lưu DB ở step preview. Nếu Landlord đóng trình
  duyệt → reset, không có "draft lưu DB". Match decision Q7 (no draft state).
- AC4 exclude flexibility quan trọng: thực tế có Lease có issue riêng
  (VD: đang tranh chấp, đợi), Landlord có thể tạo Invoice cho các Lease
  khác trước, xử lý riêng sau.
- AC9 chặn duplicate: Landlord muốn redo → phải void Invoice cũ (US-084)
  trước khi tạo lại.

---

### US-081: Landlord xuất Invoice cho 1 Lease (individual mode)

**As a** Landlord cần tạo Invoice riêng cho 1 Lease (edge case)
**I want to** tạo Invoice không qua batch flow
**So that** xử lý các trường hợp đặc biệt: Lease terminate giữa tháng,
bổ sung Invoice bị miss, etc.

**Priority**: Must
**Estimate**: M
**Depends on**: US-080

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Lease hoặc Room, có nút "Xuất Invoice"
- [ ] AC2: Click → form chọn:
  - `billing_month` (default = tháng hiện tại, cho phép chọn tháng quá khứ)
- [ ] AC3: Submit → preview như US-080 AC3 nhưng chỉ 1 Invoice
- [ ] AC4: Landlord review → click "Xác nhận" → tạo Invoice
- [ ] AC5: Validation giống US-080 AC9 (không duplicate, không tương lai)
- [ ] AC6: Sau submit → redirect về trang chi tiết Lease với Invoice mới

**Notes:**

- Individual mode là UX shortcut cho edge case. Logic tạo Invoice giống
  hệt US-080, chỉ khác entry point.
- Terminate Lease auto-trigger Invoice cuối cùng — xem US-086.

---

### US-082: Landlord xem danh sách Invoice

**As a** Landlord
**I want to** xem tất cả Invoice đã tạo với filter linh hoạt
**So that** tôi tra cứu, theo dõi tình hình thu tiền

**Priority**: Must
**Estimate**: S
**Depends on**: US-080

**Acceptance Criteria:**

- [ ] AC1: Trang danh sách Invoice (có thể ở cấp Property hoặc global)
      hiển thị:
  - Invoice ID (hoặc số Invoice)
  - Room.display_name + Property.name
  - Tenant.full_name
  - `billing_month`
  - `total_amount`
  - `paid_amount` (computed từ Payments)
  - `remaining_amount` = total - paid
  - Status badge với màu:
    - `unpaid`: đỏ
    - `partial`: cam
    - `paid`: xanh lá
    - `void`: xám đậm
- [ ] AC2: Default sort: `billing_month DESC`, sau đó `created_at DESC`
- [ ] AC3: Filter:
  - Property (nếu global)
  - Room
  - Tenant
  - Status (multi-select)
  - Billing month (range)
  - "Chỉ hiện Invoice chưa trả đủ" (quick filter)
- [ ] AC4: Summary footer:
  - Tổng tiền Invoice
  - Tổng đã thu
  - Tổng còn nợ
- [ ] AC5: Click row → trang chi tiết Invoice (US-083)
- [ ] AC6: Chỉ Landlord sở hữu xem được Invoice của mình

---

### US-083: Landlord xem chi tiết Invoice

**As a** Landlord
**I want to** xem toàn bộ chi tiết 1 Invoice
**So that** tôi trả lời được thắc mắc của Tenant, audit được

**Priority**: Must
**Estimate**: M
**Depends on**: US-080

**Acceptance Criteria:**

- [ ] AC1: Trang chi tiết Invoice hiển thị:
  - **Header**: Invoice ID, billing_month, status badge, ngày tạo
  - **Info**: Property, Room, Tenant, Lease link
  - **Line items** (bảng flatten):
    | Description | Period | Qty | Unit | Unit Price | Amount |
    - Mỗi line 1 row
    - Cho `per_meter`: description gồm cả chỉ số cũ/mới, VD:
      "Điện tháng 4 (1000 → 1150, 150 kWh)"
    - Adjustment line (nếu có) được highlight màu xanh dương + icon "±"
  - **Total**: tổng tiền
  - **Payments** (nếu có):
    - List các Payment đã ghi nhận (ngày, số tiền, method)
    - Paid: [X]đ / [Y]đ
    - Remaining: [Z]đ
  - **Actions** (tuỳ status):
    - `unpaid`/`partial`: "Ghi nhận thanh toán" (link Nhóm 8), "Void", 
      "Thêm adjustment", "Copy link Zalo"
    - `paid`: "Xem lịch sử Payment"
    - `void`: hiển thị lý do void, ai void, khi nào
- [ ] AC2: **Copy link Zalo**: nút copy link dạng 
      `{base_url}/invoices/{id}/public?token=xxx` → Tenant click xem 
      (nếu đã login → dashboard, chưa → login page)
- [ ] AC3: **Xem lịch sử**: tab "History" hiển thị:
  - Ngày tạo + ai tạo
  - Các Payment thêm vào
  - Nếu void: ngày void + lý do
- [ ] AC4: Print view: có nút "In" mở view cho in/export PDF (v1.x)
- [ ] AC5: Chỉ Landlord sở hữu xem được

**Notes:**

- AC1 description gộp chỉ số: match decision Q4 Option B. Không có column
  riêng cho chỉ số cũ/mới, nhưng description đủ thông tin.
- AC2 link Zalo: match Vision "Landlord tạo → Tenant xem trên app →
  Landlord nhắc qua Zalo".
- Print/PDF defer v1.x vì chưa có PDF generation lib chọn.

---

### US-084: Landlord void Invoice

**As a** Landlord lỡ tạo Invoice sai (sai số điện, sai rent, etc.)
**I want to** void Invoice đó thay vì edit
**So that** dữ liệu immutable, audit trail rõ, có thể tạo Invoice mới replacement

**Priority**: Must
**Estimate**: M
**Depends on**: US-080

**Acceptance Criteria:**

- [ ] AC1: Nút "Void Invoice" hiện trên trang chi tiết Invoice khi:
  - Invoice status ∈ {`unpaid`, `partial`}
  - **VÀ** không có Payment nào (nếu có Payment → phải xoá Payment trước,
    xem Nhóm 8)
- [ ] AC2: Click → form void:
  - `void_reason` (bắt buộc, enum):
    - `wrong_meter_reading`: Sai chỉ số công tơ
    - `wrong_rent`: Sai tiền phòng
    - `wrong_service_config`: Sai cấu hình dịch vụ
    - `tenant_dispute`: Tranh chấp với Tenant
    - `duplicate`: Tạo trùng
    - `other`: Khác
  - `void_note` (bắt buộc nếu chọn `other`, min 20 ký tự)
- [ ] AC3: Confirm dialog:
  - "Void Invoice #[X]? Invoice sẽ không tính vào công nợ nữa. Hành động
    không thể hoàn tác. Bạn có thể tạo Invoice mới cho tháng này sau khi void."
- [ ] AC4: Submit → set:
  - `status = 'void'`
  - `voided_at = now()`
  - `void_reason`, `void_note`
  - `voided_by = current_user.id`
- [ ] AC5: Sau void:
  - Invoice vẫn hiển thị trong danh sách với badge "Đã huỷ"
  - Không tính vào dashboard "Công nợ"
  - Tenant thấy trạng thái "Đã huỷ" trên app
  - **Reading được unlock**: Nếu Invoice ref MeterReading nào → reading
    đó không còn ràng buộc, Landlord có thể sửa nếu muốn
- [ ] AC6: Sau void → có nút "Xuất Invoice mới cho tháng này" (shortcut
      sang US-081 với billing_month pre-fill)
- [ ] AC7: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC1 không cho void khi có Payment: Payment ghi nhận tiền đã thu, không
  thể tự nhiên mất. Landlord phải xoá Payment trước (ghi nhận hoàn tiền),
  rồi mới void được.
- AC5 unlock reading: match Invoice Immutability — Invoice void thì coi
  như không tồn tại (với reading), reading lại editable.
- Void là **hard lock**: không có "unvoid". Nếu void nhầm → tạo Invoice
  mới, không phục hồi cái cũ.

---

### US-085: Landlord thêm adjustment line vào Invoice

**As a** Landlord cần điều chỉnh Invoice tháng sau vì sai tháng trước
**I want to** thêm 1 line adjustment vào Invoice hiện tại
**So that** Tenant trả/nhận lại đúng số, Invoice cũ không phải edit

**Priority**: Should
**Estimate**: M
**Depends on**: US-083

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Invoice (status = `unpaid`), có nút "Thêm
      điều chỉnh"
- [ ] AC2: Form:
  - `description` (bắt buộc, text) — VD: "Điều chỉnh điện tháng 4 (thiếu 10 kWh)"
  - `amount` (bắt buộc, có thể âm) — dương = thu thêm, âm = trả lại
  - `adjustment_reason` (tuỳ chọn, text)
- [ ] AC3: Submit → thêm line item với `line_type = 'adjustment'`, gắn vào
      Invoice, recalculate `total_amount`
- [ ] AC4: Adjustment line hiển thị nổi bật (icon "±", màu xanh dương) trong
      chi tiết Invoice
- [ ] AC5: Chỉ cho thêm khi Invoice `unpaid` (chưa có Payment)

**Notes:**

- Adjustment chỉ cho Invoice unpaid để đơn giản. Case Invoice `paid` cần
  adjustment → tạo Invoice riêng hoặc adjustment ở tháng sau.

---

### US-086: Invoice cuối cùng khi terminate Lease

**As a** Landlord terminate Lease giữa tháng
**I want to** hệ thống gợi ý tạo Invoice cuối cùng pro-rata
**So that** tôi không quên, data complete trước khi settle deposit

**Priority**: Must
**Estimate**: M
**Depends on**: US-055 (terminate Lease), US-080

**Acceptance Criteria:**

- [ ] AC1: Khi Landlord terminate Lease (US-055 AC6): sau khi set
      `terminated_at`, hệ thống check:
  - Invoice cho tháng `terminated_date` đã tồn tại chưa?
  - Nếu CHƯA → hiện dialog: "Tạo Invoice cuối cùng cho tháng [X] pro-rata 
    đến ngày [terminated_date]?"
  - Nếu ĐÃ (VD: Landlord đã xuất Invoice tháng đó trước khi terminate) → 
    warn: "Invoice tháng [X] đã tồn tại. Bạn có thể void và tạo lại cho 
    đúng với ngày terminate, hoặc thêm adjustment."
- [ ] AC2: Nếu Landlord click "Tạo Invoice":
  - Pre-fill billing_month = tháng của `terminated_date`
  - Rent pro-rata tính đến `terminated_date` (công thức Nhóm 4 Pro-rata Rule)
  - Service per_meter: dùng reading cuối (nếu chưa có → prompt Landlord 
    nhập reading trước)
  - Service per_person: snapshot NOW
  - Service fixed: pro-rata? → **Option: tính full tháng** (vì Tenant đã 
    đóng cho tháng đó rồi khi vào), hoặc pro-rata giống rent
- [ ] AC3: **Quyết định fixed/per_person khi terminate giữa tháng:**
  - Match với pro-rata Rent (pro-rata theo số ngày) để consistency
  - Confirm với Landlord qua preview trước khi submit
- [ ] AC4: Sau khi tạo Invoice cuối → CTA sang US-056 (xử lý cọc)
- [ ] AC5: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC2 flow "prompt nhập reading nếu chưa có": Landlord terminate ngày 15/5,
  chưa nhập reading tháng 5 → prompt nhập reading ngày terminate → tính
  consumption từ reading 1/5 đến 15/5.
- AC3 pro-rata cho fixed/per_person cần clarify ở Open Questions. MVP 
  propose: pro-rata tương tự rent.

---

### US-087: Tenant xem Invoice của mình

**As a** Tenant
**I want to** xem tất cả Invoice của phòng mình với chi tiết rõ ràng
**So that** tôi hiểu số tiền từ đâu ra, trả đúng

**Priority**: Must
**Estimate**: S
**Depends on**: US-080, US-005 (Tenant login)

**Acceptance Criteria:**

- [ ] AC1: Dashboard Tenant có section "Hoá đơn của tôi":
  - Invoice gần nhất (tháng hiện tại hoặc gần nhất) hiển thị prominent
  - Danh sách Invoice các tháng trước
- [ ] AC2: Click Invoice → trang chi tiết như US-083 nhưng **giới hạn**:
  - **Không thấy**: nút Void, Thêm adjustment, void_note, edit gì
  - **Thấy**: line items, total, payments, trạng thái
- [ ] AC3: Status display cho Tenant:
  - `unpaid`: "Chưa thanh toán" + số tiền cần trả
  - `partial`: "Đã trả một phần" + đã trả / tổng / còn lại
  - `paid`: "Đã thanh toán" + ngày trả cuối
  - `void`: "Đã huỷ" (không hiện lý do)
- [ ] AC4: Tenant **không thấy**: `void_reason`, `void_note`, lịch sử nội 
      bộ (ai tạo, sửa gì)
- [ ] AC5: Nếu Tenant archive (đã dọn đi) → không login được, không cần 
      handle ở đây

**Notes:**

- AC4 privacy: void note là ghi chú nội bộ của Landlord.
- AC2 "giới hạn": dùng cùng component UI nhưng conditional render theo role.

---

### US-088: Dashboard Landlord — Invoice cần xử lý

**As a** Landlord
**I want to** thấy widget Invoice cần xử lý trên dashboard
**So that** nắm nhanh tình hình, không để sót

**Priority**: Should
**Estimate**: S
**Depends on**: US-080

**Acceptance Criteria:**

- [ ] AC1: Widget "Hoá đơn cần chú ý" với sections:
  - "Chưa thanh toán quá 7 ngày": Invoice `unpaid`/`partial` có
    `created_at < today - 7 days`
  - "Tháng này chưa xuất": Property chưa có Invoice tháng hiện tại (merge
    với widget US-074)
- [ ] AC2: Mỗi item: Room, Tenant, Amount, Days overdue
- [ ] AC3: Click → trang chi tiết Invoice
- [ ] AC4: Empty state: "Chưa có Invoice nào cần xử lý 🎉"

---

## Open Questions (cần trả lời trước Phase 3)

1. **Service fixed/per_person pro-rata khi terminate giữa tháng (US-086)**: 
   pro-rata theo số ngày hay full tháng?
   - Đề xuất: pro-rata để consistency với rent.

2. **Invoice number format**: có cần sinh số Invoice dạng "INV-2026-05-001"
   không, hay dùng UUID?
   - Đề xuất: có, format dễ đọc. Auto-increment trong scope
     (landlord_id, billing_month).

3. **Late fee (phí trả chậm)**: có tính không?
   - Đề xuất: **Không** cho MVP. Thực tế Bảo có tính không? v1.x add.

4. **Discount (giảm giá, VD Tenant thân thiết)**: manual discount line?
   - Đề xuất: dùng adjustment line âm (US-085). Không cần feature riêng.

5. **Currency**: chỉ VND MVP?
   - Đề xuất: Có. v2.x multi-currency nếu export quốc tế.

6. **Round to**: làm tròn đến đơn vị nào? (đồng, trăm, nghìn?)
   - Đã quyết ở Nhóm 4: làm tròn đồng (`ROUND(x, 0)`).

7. **Invoice có ảnh chụp/file đính kèm không?**
   - Đề xuất: **không** MVP. v1.x add (ảnh hỏng hóc để trừ cọc, evidence).

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships:**

```
Lease           1──* Invoice
Invoice         1──* InvoiceLineItem
InvoiceLineItem 0──1 MeterReading  (tham chiếu, chỉ cho per_meter line)
InvoiceLineItem 0──1 Service       (tham chiếu, không dùng cho logic)
Invoice         1──* Payment       (Nhóm 8)
Room            1──* Invoice       (denormalized FK)
Tenant          1──* Invoice       (denormalized FK)
```

**Trường DB dự kiến:**

```sql
Invoice:
  id (UUID hoặc formatted string như INV-2026-05-001),
  lease_id (FK), room_id (FK denorm), tenant_id (FK denorm),
  billing_month (date, dạng 2026-05-01 để index),
  status (enum: unpaid/partial/paid/void),
  total_amount (decimal),
  created_at, created_by (FK User),
  -- Void fields
  voided_at (nullable), voided_by (nullable),
  void_reason (enum, nullable), void_note (text, nullable)
  
  UNIQUE(lease_id, billing_month) WHERE status != 'void'
  -- Đảm bảo 1 Lease có max 1 Invoice non-void cho 1 tháng
  
  INDEX(tenant_id, billing_month DESC)  -- query Tenant
  INDEX(room_id, billing_month DESC)    -- query Room
  INDEX(status, created_at)             -- query overdue

InvoiceLineItem:
  id, invoice_id (FK),
  line_type (enum: rent/service/adjustment),
  description (text),
  period_month (date),
  quantity (decimal),
  unit (string),
  unit_price (decimal),
  amount (decimal),  -- redundant = quantity × unit_price, nhưng lưu để immutable
  -- Snapshots/references
  service_id (FK nullable, ref only),
  meter_reading_id (FK nullable, ref only),
  service_name_snapshot (string nullable),
  billing_type_snapshot (enum nullable),
  -- Metadata
  created_at
```

**Computed fields (query-time, không lưu):**

- `Invoice.paid_amount`: SUM(Payment.amount) WHERE invoice_id = ?
- `Invoice.remaining_amount`: total - paid
- `Invoice.is_overdue`: created_at < now - 7 days AND status != paid
- `Lease.total_unpaid`: SUM(Invoice.remaining_amount) for Lease

**Transaction boundaries:**

Tạo Invoice batch (US-080):
```sql
BEGIN;
  FOR each Lease in batch:
    INSERT INTO invoice (...);
    FOR each line_item:
      INSERT INTO invoice_line_item (...);
COMMIT;
```

Void Invoice (US-084):
```sql
BEGIN;
  UPDATE invoice SET status='void', voided_at=NOW(), ... WHERE id=?;
COMMIT;
```

Sẽ finalize ở Phase 3.

---

## Summary

| Story  | Title                                                | Priority | Est |
| ------ | ---------------------------------------------------- | -------- | --- |
| US-080 | Landlord xem preview và xuất Invoice (batch)         | Must     | L   |
| US-081 | Landlord xuất Invoice cho 1 Lease (individual mode)  | Must     | M   |
| US-082 | Landlord xem danh sách Invoice                       | Must     | S   |
| US-083 | Landlord xem chi tiết Invoice                        | Must     | M   |
| US-084 | Landlord void Invoice                                | Must     | M   |
| US-085 | Landlord thêm adjustment line                        | Should   | M   |
| US-086 | Invoice cuối cùng khi terminate Lease                | Must     | M   |
| US-087 | Tenant xem Invoice của mình                          | Must     | S   |
| US-088 | Dashboard Landlord — Invoice cần xử lý               | Should   | S   |

**Total**: 9 stories (7 Must + 2 Should).
**Estimate**: 1L + 5M + 3S ≈ 2–2.5 sprint.
