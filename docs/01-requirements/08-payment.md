# User Stories — Nhóm 8: Payment (Thanh toán)

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-18
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **Payment (Thanh toán)** — việc Landlord ghi nhận
khoản tiền đã nhận từ Tenant cho 1 Invoice. Đây là nhóm **đơn giản nhất**
trong MVP vì chủ yếu CRUD + auto-update Invoice.status.

**Map với Vision:**

- MVP feature #8: Đánh dấu trạng thái thanh toán (đã trả / chưa trả / trả một phần)

**Key decisions (đã chốt):**

| #   | Decision                                                     | Lý do                                    |
| --- | ------------------------------------------------------------ | ---------------------------------------- |
| 1   | Payment là **record-only** (Landlord ghi nhận hậu kiểm)       | MVP không có payment gateway             |
| 2   | Không có `type` enum — mỗi Payment chỉ là 1 amount            | Trạng thái đã có ở Invoice.status        |
| 3   | Invoice.status tự compute: `unpaid`/`partial`/`paid`          | Single source of truth từ Payments       |
| 4   | Validate strict: không overpay, không future date             | Prevent data integrity issues            |
| 5   | Hard delete Payment khi nhầm lẫn (trigger recompute status)   | Đơn giản cho MVP                         |
| 6   | Không tạo Payment cho deposit (Nhóm 4 đã decided)             | Deposit là trạng thái Lease              |
| 7   | Tenant thấy full Payment history (transparency)               | Match Vision "minh bạch"                 |
| 8   | Unlimited số Payment per Invoice                              | Thực tế hiếm, không cần limit            |

## Personas liên quan

- **Landlord** (Persona A): ghi nhận Payment
- **Tenant** (Persona B): xem Payment history (read-only)

## Dependencies

- **Depends on**: Nhóm 7 (Invoice — Payment gắn với Invoice)
- **Blocks**: không (nhóm cuối)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Core Concepts

### Payment Workflow

```
Tenant chuyển khoản / đưa tiền mặt (ngoài app)
  ↓
Landlord nhận tiền, verify
  ↓
Landlord vào app → Invoice → "Ghi nhận thanh toán"
  ↓
Nhập: amount, paid_date, method, note
  ↓
Hệ thống tự compute lại Invoice.status
```

**Không có** trong MVP:
- Tenant click "Pay" trong app
- Payment gateway
- Auto-reconciliation với bank
- Notification "đã nhận tiền"

### Invoice.status Computation

```python
def compute_invoice_status(invoice):
    if invoice.status == 'void':
        return 'void'  # void là terminal state
    
    total_paid = sum(p.amount for p in invoice.payments)
    
    if total_paid == 0:
        return 'unpaid'
    elif total_paid < invoice.total_amount:
        return 'partial'
    else:  # total_paid >= invoice.total_amount
        return 'paid'
```

**Recompute trigger:**
- Thêm Payment → check lại
- Sửa Payment (đổi amount) → check lại
- Xoá Payment → check lại

### Validation Rules

- `amount > 0` (không có Payment 0đ)
- `sum(existing payments) + new_amount <= invoice.total_amount` (không overpay)
- `paid_date <= today` (không tương lai)
- Invoice.status phải ∈ {`unpaid`, `partial`} (không cho thêm vào `paid` hoặc `void`)

---

## Stories

### US-090: Landlord ghi nhận Payment cho Invoice

**As a** Landlord vừa nhận tiền từ Tenant (chuyển khoản hoặc tiền mặt)
**I want to** ghi nhận khoản thanh toán vào app
**So that** Invoice.status auto-update và tôi theo dõi được công nợ

**Priority**: Must
**Estimate**: M
**Depends on**: US-080 (Invoice)

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Invoice, có nút "Ghi nhận thanh toán" (chỉ
      hiện khi Invoice.status ∈ {`unpaid`, `partial`})
- [ ] AC2: Form ghi nhận có các trường:
  - `amount` (bắt buộc, > 0, ≤ remaining_amount)
  - `paid_date` (bắt buộc, default = today, không cho tương lai)
  - `method` (bắt buộc, dropdown):
    - `cash`: Tiền mặt
    - `bank_transfer`: Chuyển khoản
    - `ewallet`: Ví điện tử (Momo, ZaloPay, ...)
    - `other`: Khác
  - `reference_number` (tuỳ chọn, max 50 ký tự) — mã giao dịch bank transfer
  - `note` (tuỳ chọn, free text max 200 ký tự)
- [ ] AC3: Validation chi tiết:
  - `amount > 0`
  - `amount <= remaining_amount` (chặn overpay)
  - Nếu overpay → hiện lỗi: "Số tiền [X] vượt quá số còn nợ [Y]đ"
  - `paid_date <= today`
- [ ] AC4: Quick-fill shortcuts cho `amount`:
  - Nút "Trả đủ" → amount = remaining_amount
  - Nút "Trả 50%" → amount = remaining_amount / 2
  - (optional UX, giúp thao tác nhanh)
- [ ] AC5: Submit → tạo Payment record trong transaction:
  - INSERT Payment
  - Trigger recompute Invoice.status (unpaid → partial, hoặc partial → paid)
- [ ] AC6: Sau submit → toast message:
  - Nếu Invoice → `paid`: "Đã thanh toán đủ. Invoice #[X] hoàn tất."
  - Nếu Invoice → `partial`: "Đã ghi nhận [Y]đ. Còn nợ [Z]đ."
- [ ] AC7: Redirect về trang chi tiết Invoice với Payment mới xuất hiện
      trong section "Lịch sử Payment"
- [ ] AC8: Chỉ Landlord sở hữu Invoice thực hiện được

**Notes:**

- AC2 `method` enum: chọn 4 values đủ cover thực tế VN. "Ví điện tử" gộp
  vì từng provider cụ thể (Momo, ZaloPay) thì dùng `reference_number` ghi.
- AC3 chặn overpay: edge case Tenant làm tròn trả thừa (VD: 3.1M cho
  Invoice 3M). Landlord ghi 3M đúng + note "Tenant trả thừa 100k, giữ cho
  tháng sau". 100k đó không vào Payment, chỉ ghi nhớ.
- AC5 transaction: đảm bảo atomic. Nếu INSERT Payment OK nhưng recompute
  fail → rollback.

---

### US-091: Landlord xem lịch sử Payment của Invoice

**As a** Landlord
**I want to** xem tất cả Payment đã ghi cho 1 Invoice
**So that** tôi audit, tra cứu khi có tranh chấp

**Priority**: Must
**Estimate**: S
**Depends on**: US-090

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Invoice (US-083), section "Lịch sử Payment"
      hiển thị bảng:
  - `paid_date`
  - `amount`
  - `method` (Vietnamese label)
  - `reference_number` (nếu có)
  - `note` (nếu có, truncate nếu dài)
  - `created_at` + ai ghi nhận (tuỳ chọn hiển thị)
  - Actions: Sửa / Xoá (Should — xem US-092)
- [ ] AC2: Summary ở cuối:
  - Tổng đã thu: [X]đ
  - Còn nợ: [Y]đ
  - Tỷ lệ: [Z]% (thanh bar progress)
- [ ] AC3: Empty state: "Chưa có thanh toán nào cho Invoice này."
- [ ] AC4: Sort: `paid_date DESC` (mới nhất trên đầu)
- [ ] AC5: Chỉ Landlord sở hữu xem được

---

### US-092: Landlord sửa/xoá Payment

**As a** Landlord ghi nhầm Payment (sai số tiền, sai ngày)
**I want to** sửa hoặc xoá Payment
**So that** dữ liệu đúng, Invoice.status chính xác

**Priority**: Should
**Estimate**: S
**Depends on**: US-090

**Acceptance Criteria:**

- [ ] AC1: Mỗi Payment row có nút "Sửa" và "Xoá"
- [ ] AC2: **Sửa**:
  - Form pre-fill data hiện tại
  - Cho sửa: `amount`, `paid_date`, `method`, `reference_number`, `note`
  - Validate như US-090 AC3 (check overpay tính cả Payments khác)
  - Submit → UPDATE + recompute Invoice.status
- [ ] AC3: **Xoá**:
  - Confirm dialog: "Xoá Payment [Y]đ ngày [X]? Invoice status sẽ được
    tính lại."
  - Submit → hard DELETE + recompute Invoice.status
- [ ] AC4: **Chặn** sửa/xoá nếu Invoice.status = `void`
- [ ] AC5: Nếu xoá/sửa Payment làm Invoice từ `paid` → `partial`/`unpaid`:
  - Silent recompute, không block
- [ ] AC6: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- Không có undo window: xoá là vĩnh viễn. Landlord cẩn thận khi xoá.

---

### US-093: Tenant xem Payment history của mình

**As a** Tenant
**I want to** xem các khoản Payment đã được ghi nhận cho Invoice của mình
**So that** tôi verify Landlord ghi đúng số tiền tôi đã chuyển

**Priority**: Must
**Estimate**: S
**Depends on**: US-090, US-087 (Tenant xem Invoice)

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Invoice của Tenant (US-087), section "Lịch
      sử thanh toán":
  - Bảng tương tự US-091 AC1
  - Tenant **thấy**: `paid_date`, `amount`, `method`, `reference_number`
  - Tenant **không thấy**: ai ghi (internal), `note` nội bộ
- [ ] AC2: Summary: tổng đã thanh toán, còn nợ
- [ ] AC3: Tenant **không có quyền** sửa/xoá Payment (chỉ Landlord làm)
- [ ] AC4: Empty state: "Chưa có thanh toán nào được ghi nhận."

**Notes:**

- AC1 `note` field ẩn với Tenant: Landlord có thể ghi note nội bộ
  ("Tenant trả thiếu 50k, nhắc lần sau"). Show với Tenant có thể gây
  khó chịu.

---

### US-094: Dashboard Landlord — Tổng thu tháng

**As a** Landlord
**I want to** xem tổng tiền đã thu trong tháng hiện tại
**So that** nắm nhanh tình hình tài chính, không phải cộng thủ công

**Priority**: Should
**Estimate**: S
**Depends on**: US-090

**Acceptance Criteria:**

- [ ] AC1: Dashboard Landlord có widget "Tổng thu tháng [current_month]":
  - Tổng đã thu (SUM Payment.amount where paid_date in current month)
  - Tổng phát sinh (SUM Invoice.total_amount where billing_month = current)
  - Tỷ lệ thu / phát sinh
- [ ] AC2: Breakdown theo Property (nếu Landlord có nhiều Property)
- [ ] AC3: So sánh với tháng trước (+/- %)
- [ ] AC4: Click → link sang báo cáo chi tiết (v1.x)

**Notes:**

- Widget chỉ hiển thị số. Không biểu đồ (v1.x).

---

## Open Questions (cần trả lời trước Phase 3)

1. **Auto-suggest `amount` = `remaining_amount`?**
   - Đã có "Trả đủ" button (US-090 AC4). Đủ.

2. **Notification khi Payment ghi nhận → Tenant biết?**
   - MVP: Không. Tenant login mới thấy.
   - v1.x: Push/email notification.

3. **Export Payment report (Excel/PDF)?**
   - v1.x.

4. **Payment cho nhiều Invoice cùng lúc?**
   - Case: Tenant trả 5M để cover 2 Invoice tháng 4 (2M) + tháng 5 (3M)
   - MVP: Landlord tạo 2 Payment riêng (2M cho tháng 4, 3M cho tháng 5)
   - v1.x: bulk Payment allocation

5. **Partial refund khi adjust Invoice?**
   - MVP: Landlord tạo adjustment line âm (US-085), Tenant Payment sẽ overpay
     tương ứng → Landlord ghi Payment âm? **Không support Payment âm ở MVP.**
   - Work-around: Landlord trả Tenant ngoài app, ghi note.

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships:**

```
Invoice     1──* Payment
User        1──* Payment  (created_by, audit)
```

**Trường DB dự kiến:**

```sql
Payment:
  id (UUID),
  invoice_id (FK NOT NULL),
  amount (decimal(12,0), > 0),
  paid_date (date, NOT NULL),
  method (enum: cash/bank_transfer/ewallet/other, NOT NULL),
  reference_number (varchar(50), nullable),
  note (text, nullable),
  created_at, created_by (FK User)

  INDEX(invoice_id, paid_date DESC)  -- query lịch sử theo Invoice
  INDEX(created_by, paid_date)       -- query theo Landlord + month
```

**Computed fields:**

- `Invoice.paid_amount`: SUM(Payment.amount) for invoice
- `Invoice.remaining_amount`: Invoice.total_amount - paid_amount
- `Invoice.status`: derived (xem Core Concepts)

**Triggers / Event hooks:**

Khi Payment thay đổi (INSERT/UPDATE/DELETE):
1. Recompute Invoice.status
2. Update dashboard widgets (in-memory cache invalidate)

MVP có thể implement bằng application-level logic (không cần DB trigger).

Sẽ finalize ở Phase 3.

---

## Summary

| Story  | Title                                     | Priority | Est |
| ------ | ----------------------------------------- | -------- | --- |
| US-090 | Landlord ghi nhận Payment                 | Must     | M   |
| US-091 | Landlord xem lịch sử Payment              | Must     | S   |
| US-092 | Landlord sửa/xoá Payment                  | Should   | S   |
| US-093 | Tenant xem Payment history                | Must     | S   |
| US-094 | Dashboard — Tổng thu tháng                | Should   | S   |

**Total**: 5 stories (3 Must + 2 Should).
**Estimate**: 1M + 4S ≈ 1 sprint.

---

## 🎉 Phase 2 Completion

Nhóm 8 là nhóm cuối cùng của Phase 2. Sau khi Bảo approve nhóm này:

**Tổng Phase 2:**
- 8 nhóm hoàn thành
- 63 user stories (US-001 → US-094)
- Tổng estimate: ~15 sprint (~3.5-4 tháng solo)

**Next steps:**
1. Bảo review Nhóm 8 → approve
2. Viết `PHASE2-SUMMARY.md` (context seed cho Phase 3)
3. Gate Review round 2 (nếu cần)
4. Chuyển sang **Phase 3: Architecture + Database Design**
