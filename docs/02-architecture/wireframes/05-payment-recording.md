# Wireframe 05 — Payment Recording Form

> **Purpose**: Validate simplest-but-critical form pattern. Payment
> record-only (no gateway), landlord hậu kiểm sau khi tenant chuyển khoản.
> **Covers**: US-091 (Nhóm 8 — Payment)
> **Endpoints**: `POST /api/v1/invoices/{iid}/payments`

---

## Context / User Flow

**Trigger** (3 entry points):
1. Dashboard quick action "Ghi thu" → chọn invoice → form
2. Invoice detail screen → button "Ghi thanh toán" → modal form
3. Invoice list → swipe action hoặc row action "Ghi thu"

**Flow**:
1. Form mở với context của 1 invoice (invoice info read-only top)
2. Landlord nhập amount, method, paid_at, note
3. Live validation (overpay, future date)
4. Submit → backend validate + save + recompute invoice status
5. Success toast + invoice status badge update realtime

---

## Layout (Modal trên desktop, full-screen trên mobile)

### Recommended: Modal dialog

```
+-------------------------------------------------------------+
|                                                             |
|   Ghi nhận thanh toán                              [ × ]   |
|   -------------------------------------------------------   |
|                                                             |
|   Hoá đơn: INV-2026-04-0012                                |
|   Phòng: P101 — Nguyễn Văn A                               |
|   Tháng: 4/2026                                            |
|                                                             |
|   +-----------------------------------------------------+  |
|   |  Tổng hoá đơn:       3.250.000 VND                  |  |
|   |  Đã thanh toán:      2.000.000 VND                  |  |
|   |  Còn lại:            1.250.000 VND  ← default input |  |
|   +-----------------------------------------------------+  |
|                                                             |
|   Số tiền *                                                 |
|   [ 1.250.000                             ] VND            |
|   [Thanh toán đủ]                                          |
|                                                             |
|   Hình thức thanh toán *                                    |
|   ( ) Tiền mặt                                             |
|   (●) Chuyển khoản                                         |
|   ( ) Ví điện tử                                           |
|   ( ) Khác                                                 |
|                                                             |
|   Ngày thanh toán *                                         |
|   [ 25/04/2026  📅 ]                                       |
|                                                             |
|   Ghi chú                                                   |
|   [                                                     ]  |
|   [                                                     ]  |
|   Placeholder: "Ví dụ: Vietcombank TXN 2026..."            |
|                                                             |
|   -------------------------------------------------------   |
|                                                             |
|                       [ Huỷ ]   [ Ghi nhận ]               |
|                                                             |
+-------------------------------------------------------------+
```

### Mobile layout (<768px): Full-screen

Same fields, stacked vertically, header có close button thay vì modal
overlay. Bottom fixed action bar.

---

## Zones breakdown

### Zone 1: Header

- Title: "Ghi nhận thanh toán"
- Close button (× icon) top-right
- Context breadcrumb: Invoice number + Room + Tenant + Month (read-only)

### Zone 2: Invoice summary card

3 lines, read-only:
- **Tổng hoá đơn**: `invoice.total_amount`
- **Đã thanh toán**: sum of existing payments
- **Còn lại**: `total - paid` (= default amount value)

### Zone 3: Form fields

#### Field 1: Số tiền (amount)

- Label: "Số tiền *"
- Input type: number với thousand separator display (1.250.000)
- Unit suffix: "VND"
- Default value: invoice remaining amount
- Quick action: `[Thanh toán đủ]` button → set to remaining
- Validation:
  - Required, > 0
  - `<= remaining` → show error "Vượt quá số còn lại"
  - = 0 → show error "Phải nhập số tiền"

#### Field 2: Hình thức (method)

- Label: "Hình thức thanh toán *"
- Radio group (not dropdown — fewer clicks):
  - Tiền mặt (`cash`)
  - Chuyển khoản (`bank_transfer`) — default
  - Ví điện tử (`ewallet`)
  - Khác (`other`)

#### Field 3: Ngày thanh toán (paid_at)

- Label: "Ngày thanh toán *"
- Date picker
- Default: today
- Validation: `<=  today` (no future date)

#### Field 4: Ghi chú (note)

- Label: "Ghi chú" (optional, no asterisk)
- Textarea 2-3 lines
- Placeholder: "Ví dụ: Vietcombank TXN 2026..."
- Max 500 chars

### Zone 4: Actions

- **Huỷ** (secondary) — close modal, discard
- **Ghi nhận** (primary) — submit

---

## Interactions

### Default value logic

- **Amount**: remaining = `total - sum(existing payments)`. If first
  payment → default = full total.
- **Method**: `bank_transfer` (most common per Vietnamese landlord
  workflow)
- **Date**: today
- **Note**: empty

### "Thanh toán đủ" quick button

Sets amount = remaining. Shortcut cho case full payment (common).

### Live validation

- On blur amount: check overpay
- On change date: check future date
- On submit: full server validation (includes amount format, method enum)

### Submit behaviors

- Click "Ghi nhận":
  1. Client validate: amount > 0, amount <= remaining, paid_at <= today
  2. `POST /api/v1/invoices/{iid}/payments` với body
  3. Success:
     - Close modal
     - Toast "Đã ghi thanh toán 1.250.000 VND"
     - Update invoice row in list/detail: status badge refresh
     - If invoice now `paid` → visual cue (green check icon)
  4. Error 422 (overpay): inline error on amount field
  5. Error 422 (future date): inline error on date field
  6. Error 409 (invoice voided): full-form error "Hoá đơn đã hủy,
     không thể ghi thanh toán"

---

## States

| State | What shows |
|---|---|
| Initial | Defaults filled, Ghi nhận button enabled |
| Typing invalid | Inline error on field, Ghi nhận still enabled (server check) |
| Submitting | Button spinner + disable form |
| Success | Close + toast |
| Server error | Inline or banner error, form stays |

---

## Edge Cases

### Invoice fully paid (status = `paid`)

Form không nên mở được. Entry points phải hide "Ghi thanh toán" action.
Nếu somehow opened → form shows banner "Hoá đơn đã thanh toán đủ".
Submit disabled.

### Invoice voided (status = `void`)

Button hide ở entry points. Nếu force open → banner red "Hoá đơn đã hủy".
Submit disabled.

### Multiple partial payments

Each submit creates new payment record. Running sum displayed in Zone 2
updates in realtime after success.

### Refund / negative payment

**NOT SUPPORTED** (per Phase 2 decision). Mistake corrections = delete
payment (separate action).

---

## Alternative Layout: Inline on Invoice Detail

Thay vì modal, có thể embed form collapsed trong Invoice detail screen:

```
+---- Invoice Detail P101 ----+
| ... invoice content ...     |
|                             |
| Thanh toán (2 records)      |
| - 15/4 Cash 1.000.000       |
| - 20/4 Chuyển khoản 1.000.000|
|                             |
| [+ Ghi thanh toán mới] ←---+ click expand inline form
|                             |
+-----------------------------+
```

**Recommend modal** cho MVP vì:
- Focus UX: user task-oriented "ghi thanh toán" 1 lần
- Re-use: có thể open từ list (không cần navigate detail)
- Simpler state management (1 form instance)

---

## Claude Design Prompt (copy-paste below)

```
Create a low-fidelity wireframe for a "Record Payment" modal
dialog in RMS. This is a simple form but critical — landlord
records payments after tenant transfers money (no gateway, just
record-keeping).

Layout: modal centered on dimmed background, max-width 520px,
vertical scroll if needed.

Modal content:

1. Header row:
   - Title "Ghi nhận thanh toán" (left)
   - Close button "×" (right)
   - Divider below

2. Context block (read-only):
   - "Hoá đơn: INV-2026-04-0012"
   - "Phòng: P101 — Nguyễn Văn A"
   - "Tháng: 4/2026"

3. Summary card (bordered inner card):
   - "Tổng hoá đơn:       3.250.000 VND"
   - "Đã thanh toán:      2.000.000 VND"
   - "Còn lại:            1.250.000 VND ← default input"

4. Form fields stacked:

   a. Amount input:
      - Label "Số tiền *"
      - Number input showing "1.250.000" with "VND" suffix
      - Small link-button below: "[Thanh toán đủ]"

   b. Payment method radio group:
      - Label "Hình thức thanh toán *"
      - 4 radio options (show second one selected):
        ○ Tiền mặt
        ● Chuyển khoản
        ○ Ví điện tử
        ○ Khác

   c. Date input:
      - Label "Ngày thanh toán *"
      - Date picker with value "25/04/2026" + calendar icon

   d. Textarea:
      - Label "Ghi chú" (optional, no asterisk)
      - Empty textarea 2-3 lines high
      - Placeholder text "Ví dụ: Vietcombank TXN 2026..."

5. Divider

6. Action row bottom:
   - Right-aligned: secondary button "Huỷ" + primary button "Ghi nhận"

Style: low-fidelity wireframe, grayscale, standard modal dialog.
Clear label-above-input form pattern. Reference shadcn/ui Dialog
+ Form components.

Locale: Vietnamese as shown.
```

---

## Acceptance Criteria

- [ ] Modal dialog layout (overlay on dimmed background)
- [ ] Context block shows invoice identifier + tenant + month
- [ ] Summary card shows 3 amounts (total / paid / remaining)
- [ ] Amount input with "VND" suffix + "Thanh toán đủ" quick button
- [ ] Radio group for 4 payment methods (not dropdown)
- [ ] Date picker with calendar icon
- [ ] Textarea for notes with placeholder
- [ ] Bottom action row with Cancel + Submit
- [ ] All labels in Vietnamese
- [ ] Form hierarchy clear (labels above inputs)

---

**Export**: Save as `05-payment-record.png` in this folder.
