# Wireframe 04 — Invoice Preview → Commit Flow

> **Purpose**: Validate 2-step preview-commit pattern. Critical vì
> invoice immutable sau commit → preview là safety net cuối.
> **Covers**: US-076, US-077, US-078, US-081 (Nhóm 7 — Invoice)
> **Endpoints**: `POST /properties/{pid}/invoices/preview` (stateless),
> `POST /properties/{pid}/invoices` (commit batch)

---

## Context / User Flow

1. Landlord đến từ dashboard action "Xuất hoá đơn" hoặc chain từ
   Meter Reading (wireframe 03)
2. Chọn property + month → click "Xem trước" → backend generate
   invoices in-memory (NOT saved)
3. Xem danh sách N invoices với line items chi tiết
4. Per-invoice có option "Bỏ qua" (exclude) + preview total
5. Warnings block: thiếu meter reading, duplicate invoice, etc.
6. Click "Xác nhận xuất" → commit batch → invoices saved + locked
7. Redirect to Invoice list với filter tháng đã commit

---

## Layout (desktop 1280px) — Screen 4A: Preview

```
+---------------------------------------------------------------------+
| [Logo] RMS                               [Search] [Bell] [Avatar]   |
+--------+------------------------------------------------------------+
|        |                                                            |
| Nav    | < Quay lại | Xuất hoá đơn — Xem trước                     |
|        | -----------------------------------------------------------|
|  ...   |                                                            |
|        | Nhà: Nhà Hoàng Cầu     Tháng: 4/2026                      |
|        | -----------------------------------------------------------|
|        |                                                            |
|        | Tổng quan                                                  |
|        | +------------------------------------------------------+  |
|        | |  📊 8 hợp đồng active                                 |  |
|        | |  📄 Sẽ tạo 7 hoá đơn (1 hợp đồng đã có hoá đơn tháng 4)|  |
|        | |  💰 Tổng: 23.450.000 VND                              |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | Cảnh báo                                                   |
|        | +------------------------------------------------------+  |
|        | | ⚠️ 2 phòng thiếu chỉ số công tơ tháng 4              |  |
|        | |   - P103, P107 → hoá đơn sẽ không có tiền điện      |  |
|        | |   [Nhập công tơ ngay]                                |  |
|        | |                                                      |  |
|        | | 🔴 1 hoá đơn duplicate — đã có hoá đơn tháng 4       |  |
|        | |    P108 — sẽ bỏ qua                                  |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | Chi tiết hoá đơn (7)                                       |
|        |                                                            |
|        | +------------------------------------------------------+  |
|        | | ☑ P101 — Nguyễn Văn A                    3.250.000đ |  |
|        | |                                                      |  |
|        | | Tiền phòng (4/2026)                      2.500.000  |  |
|        | | Điện (kWh): 130 × 3,500 = 455.000        455.000    |  |
|        | | Nước (m³): chia phần = 3 × 12,000        36.000     |  |
|        | | Rác (cố định)                            50.000     |  |
|        | | Internet (cố định)                       150.000    |  |
|        | | Điều chỉnh tháng trước (+)               59.000     |  |
|        | | -----                                                |  |
|        | | Tổng                                     3.250.000  |  |
|        | |                                                      |  |
|        | |                              [Chi tiết] [Bỏ qua]    |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | +------------------------------------------------------+  |
|        | | ☑ P102 — Trần Thị B                      2.980.000đ |  |
|        | |   [Compact view — click để mở rộng]                 |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | +------------------------------------------------------+  |
|        | | ☐ P108 — Lê Văn C   (DUPLICATE - sẽ bỏ qua)          |  |
|        | |   Đã có hoá đơn INV-2026-04-0005 tạo ngày 28/4      |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | ...  (rows tiếp)                                           |
|        |                                                            |
|        |                                                            |
|        |                [ Huỷ ]   [ Xác nhận xuất 7 hoá đơn ]      |
+--------+------------------------------------------------------------+
```

---

## Zones breakdown (Screen 4A)

### Zone 1: Header

- Back button
- Page title: "Xuất hoá đơn — Xem trước"
- Context line: Property name + Month (read-only, set from previous screen)

### Zone 2: Summary card

3 key metrics:
- **Active leases count** — total potentially billable
- **Invoices sẽ tạo** — after excluding duplicates
- **Total amount** — sum of preview invoices

### Zone 3: Warnings card (if any)

Collapsible warning list:

**Missing meter readings** (⚠️ yellow)
- List rooms thiếu chỉ số
- CTA button: `[Nhập công tơ ngay]` → wireframe 03 với context pre-filled

**Duplicate detection** (🔴 red)
- List leases đã có invoice tháng đó
- Note: sẽ auto-skip (không block submit)

**Negative consumption** (🔴 red)
- Link to meter reading review

**Settings conflicts** (⚠️)
- Service active mid-month, new rate, etc.

### Zone 4: Invoice preview list

Mỗi invoice là 1 card expandable:

**Collapsed state** (default):
- Checkbox (include/exclude)
- Room + tenant name
- Total amount right-aligned
- Click card → expand

**Expanded state**:
- Line items table (line_type · description · amount)
- Subtotal logic visible
- `[Chi tiết]` button → modal với full detail
- `[Bỏ qua]` button → toggle checkbox off

**Disabled state** (duplicate):
- Checkbox disabled, grayscaled
- Badge "DUPLICATE - sẽ bỏ qua"
- Link to existing invoice

### Zone 5: Bottom sticky actions

- **Huỷ** (secondary) — back to Invoice list (discard preview)
- **Xác nhận xuất N hoá đơn** (primary) — N là count non-excluded

N cập nhật realtime khi toggle checkbox.

---

## Layout Screen 4B: Confirmation Dialog

Sau khi click "Xác nhận xuất":

```
+---------------------------------------------------+
|                                                   |
|   Xác nhận xuất hoá đơn?                         |
|   -------------------------------------------     |
|                                                   |
|   Bạn sẽ tạo 7 hoá đơn cho tháng 4/2026.         |
|   Tổng: 23.450.000 VND                           |
|                                                   |
|   ⚠️ Sau khi xuất, hoá đơn không thể chỉnh sửa.  |
|      Muốn sửa phải void và tạo lại.              |
|                                                   |
|   [ Huỷ ]  [ Xác nhận và xuất ]                  |
|                                                   |
+---------------------------------------------------+
```

Modal buộc click explicit để tránh accidental commit.

---

## Layout Screen 4C: Success (toast + redirect)

Commit success:
- Toast: "Đã xuất 7 hoá đơn. Tổng 23.450.000 VND"
- Redirect to: `/invoices?billing_month=2026-04&property_id=<pid>`
- List page highlight new invoices (subtle pulse animation 2s)

---

## Interactions

### Checkbox per invoice

- Toggle off → update summary count + total
- "Bỏ qua" button = shortcut for toggle off

### Expand/collapse invoice card

- Click card body → expand
- Default state: all collapsed except first invoice (auto-expand top)

### Edit before commit?

**NO** — per Invoice Immutability rule (Phase 2). Preview = review, not edit.

Workaround: nếu thấy sai, click "Bỏ qua" for that invoice → commit rest
→ fix root cause (meter reading, service config) → preview + commit
remaining standalone.

### Duplicate handling

`on_duplicate` body field options (decided in API spec):
- **skip** (default): preview đã show, commit auto-skip duplicates
- **error**: toggle cho user choose → preview returns 409 upfront

MVP default = skip. UI không expose toggle (hide complexity).

### Warning: missing meter readings

Click "Nhập công tơ ngay" → navigate to wireframe 03 với:
- Property + month pre-filled
- Flag return destination = back to this preview

After save meter readings → auto re-run preview.

---

## States

| State | What shows |
|---|---|
| Loading preview | Full-page spinner "Đang tính toán hoá đơn..." |
| Preview loaded | Full layout as spec |
| Partial warnings | Warnings card expanded, invoice list scrollable |
| All excluded | Submit button disabled, hint "Chọn ít nhất 1 hoá đơn" |
| Submitting | Primary button spinner + disabled |
| Commit success | Redirect to list |
| Commit error | Toast with error message, preview stays |

---

## Claude Design Prompt (copy-paste below)

```
Create a low-fidelity wireframe for "Invoice Preview Screen" in
RMS. This is step 1 of a 2-step preview-commit pattern for
generating monthly invoices.

Context: Landlord clicks "Xuất hoá đơn" for Nhà Hoàng Cầu in
April 2026. Backend returns 8 preview invoices in-memory (NOT
saved yet). Landlord reviews, excludes any problematic ones,
then commits the batch.

Layout (desktop 1280x1100):

Same top bar + sidebar as dashboard.

Main content:

1. Header: "< Quay lại" + "Xuất hoá đơn — Xem trước" +
   subtitle "Nhà: Nhà Hoàng Cầu  Tháng: 4/2026"

2. Summary card at top:
   - "📊 8 hợp đồng active"
   - "📄 Sẽ tạo 7 hoá đơn (1 hợp đồng đã có hoá đơn tháng 4)"
   - "💰 Tổng: 23.450.000 VND"

3. Warnings section:
   - Yellow card: "⚠️ 2 phòng thiếu chỉ số công tơ tháng 4 —
     P103, P107 → hoá đơn sẽ không có tiền điện" +
     [Nhập công tơ ngay] button
   - Red card: "🔴 1 hoá đơn duplicate — P108 sẽ bỏ qua"

4. Invoice list header: "Chi tiết hoá đơn (7)"

5. First invoice card (EXPANDED state):
   - Header row: checkbox ☑ + "P101 — Nguyễn Văn A" + right-aligned
     amount "3.250.000đ"
   - Line items table below:
     * "Tiền phòng (4/2026) ......... 2.500.000"
     * "Điện (kWh): 130 × 3,500 ..... 455.000"
     * "Nước (m³): chia phần 3 × 12k  36.000"
     * "Rác (cố định) ................ 50.000"
     * "Internet (cố định) ........... 150.000"
     * "Điều chỉnh tháng trước (+) ... 59.000"
     * Divider
     * "Tổng ......................... 3.250.000"
   - Action row: [Chi tiết] [Bỏ qua]

6. Second invoice card (COLLAPSED):
   - Single row: ☑ + "P102 — Trần Thị B" + "2.980.000đ" +
     hint "Click để mở rộng"

7. Third invoice card (DISABLED - duplicate):
   - Disabled checkbox ☐ + grayscale text
   - "P108 — Lê Văn C  (DUPLICATE - sẽ bỏ qua)"
   - Subtitle: "Đã có hoá đơn INV-2026-04-0005 tạo ngày 28/4"

8. Placeholder for 4 more invoice rows (compact)

9. Sticky bottom bar:
   - Left button "Huỷ" (secondary)
   - Right button "Xác nhận xuất 7 hoá đơn" (primary)

Style: low-fidelity wireframe, grayscale, emphasis on scannable
invoice list. Clear visual distinction between collapsed vs
expanded vs disabled states (use different border styles or
opacity). Reference shadcn/ui Card + Table components.

Locale: Vietnamese as shown.
```

---

## Acceptance Criteria

- [ ] Header with back link + title + context subtitle
- [ ] Summary card with 3 metrics
- [ ] Warnings section visible with 2 alert types
- [ ] Invoice list shows at least 3 states: expanded / collapsed / disabled
- [ ] Expanded state shows full line items with totals
- [ ] Disabled state clearly different (grayscale)
- [ ] Checkboxes visible per invoice
- [ ] Sticky bottom bar with 2 actions
- [ ] Submit button shows dynamic count "N hoá đơn"

---

**Export**:
- `04-invoice-preview.png` — main preview screen
- `04b-invoice-confirm-modal.png` — confirmation dialog (optional)
