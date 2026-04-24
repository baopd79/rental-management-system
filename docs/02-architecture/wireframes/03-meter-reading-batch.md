# Wireframe 03 — Batch Meter Reading Form

> **Purpose**: Validate batch-per-property UX. Critical workflow vì
> landlord đọc công tơ cả nhà trong 1 vòng đi — UI phải match real-world.
> **Covers**: US-064, US-065, US-067, US-070 (Nhóm 6 — Meter Reading)
> **Endpoints**: `POST /api/v1/properties/{pid}/meter-readings/batch`,
> `GET /api/v1/properties/{pid}/meter-readings/previous?service_id=X`

---

## Context / User Flow

1. Landlord chọn "Nhập công tơ" từ dashboard quick action
2. Chọn Property → chọn month
3. Thấy form: per-meter service × rooms in scope (filter phòng có active
   lease)
4. Nhập reading value từng cell, thấy previous value làm reference
5. Submit batch → backend validate, tạo MeterReading records
6. Redirect về dashboard hoặc Invoice preview (chain to wireframe 04)

---

## Layout (desktop 1280px)

```
+---------------------------------------------------------------------+
| [Logo] RMS                               [Search] [Bell] [Avatar]   |
+--------+------------------------------------------------------------+
|        |                                                            |
| Nav    | < Quay lại | Nhập chỉ số công tơ                          |
|        | ----------------------------------------------------------|
|  ...   |                                                            |
|        | Bước 1: Chọn nhà và tháng                                  |
|        | +------------------------------------------------------+  |
|        | | Nhà trọ:  [ Nhà Hoàng Cầu (8 phòng)    v ]          |  |
|        | | Tháng:    [ Tháng 4/2026              v ]            |  |
|        | |           Chỉ số ngày:  [01/05/2026]                 |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | Bước 2: Nhập chỉ số                                        |
|        | +------------------------------------------------------+  |
|        | | Điện (kWh) — điện riêng theo phòng                   |  |
|        | |                                                      |  |
|        | | Phòng | Kỳ trước  | Kỳ này       | Tiêu thụ | Warn  |  |
|        | |-------|-----------|--------------|----------|-------|  |
|        | | P101  | 1250      | [1380      ] | 130      |       |  |
|        | | P102  | 2110      | [2245      ] | 135      |       |  |
|        | | P103  | 890       | [          ] |          |       |  |
|        | | P104  | 3420      | [3420      ] | 0        | ⚠️    |  |
|        | | P105  | 1820      | [1790      ] | -30      | 🔴    |  |
|        | | ...                                                  |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | +------------------------------------------------------+  |
|        | | Nước (m³) — đồng hồ chung chia theo người            |  |
|        | |                                                      |  |
|        | | Kỳ trước:  450                                       |  |
|        | | Kỳ này:    [485          ]                           |  |
|        | | Tiêu thụ:  35 m³ → chia cho 23 người ở               |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        | Bước 3: Xem lại và lưu                                     |
|        | +------------------------------------------------------+  |
|        | | ✅ 7 phòng đã nhập đủ                                 |  |
|        | | ⚠️ 1 phòng có tiêu thụ bằng 0 (P104)                  |  |
|        | | 🔴 1 phòng có tiêu thụ âm (P105) — cần kiểm tra      |  |
|        | | ⏭️ 1 phòng chưa nhập (P103) — sẽ bỏ qua              |  |
|        | +------------------------------------------------------+  |
|        |                                                            |
|        |                    [ Lưu nháp ]  [ Lưu và tiếp tục ]      |
+--------+------------------------------------------------------------+
```

---

## Zones breakdown

### Zone 1: Header

- Back button (text "< Quay lại" hoặc arrow icon) → về dashboard
- Page title: "Nhập chỉ số công tơ"
- (Optional) Progress indicator: Bước 1 → 2 → 3

### Zone 2: Step 1 — Property + Month selection

Form card với 3 fields:
- **Property select**: dropdown, shows property name + room count
- **Month select**: dropdown, default = current month -1 (ví dụ hôm nay
  1/5 → default "Tháng 4/2026"). Lý do: reading 1/5 là consumption
  của tháng 4 (Option B in Phase 2).
- **Reading date** (read-only): auto today's date

### Zone 3: Step 2 — Per-service reading input

Mỗi per_meter service là một card riêng.

#### Card per_room service (e.g., điện)

- **Header**: Service name + unit + scope note ("điện riêng theo phòng")
- **Table**:
  - Column: Phòng (room display_name)
  - Column: Kỳ trước (read-only, từ last reading)
  - Column: Kỳ này (input number, focus trap qua phòng tiếp theo on Enter)
  - Column: Tiêu thụ (computed: kỳ này - kỳ trước)
  - Column: Warning (icon nếu có anomaly)
- **Row states**:
  - Empty (chưa nhập) — input placeholder, tiêu thụ empty
  - Normal — green check implicit
  - Zero consumption — ⚠️ yellow
  - Negative — 🔴 red với message "Tiêu thụ âm — kiểm tra lại"
  - Same as previous — ⚠️ yellow với message "Không thay đổi"

#### Card shared meter service (e.g., nước chung)

Đơn giản hơn:
- **Kỳ trước**: một số duy nhất (read-only)
- **Kỳ này**: 1 input
- **Tiêu thụ**: computed
- **Chia cho**: tự động hiển thị "N người ở tại X phòng" (context, read-only)

### Zone 4: Step 3 — Summary + validation

Pre-submit checklist:
- ✅ Count phòng đã nhập đủ
- ⚠️ Count phòng có warning (zero/same)
- 🔴 Count phòng có error (negative)
- ⏭️ Count phòng chưa nhập → sẽ skip

### Zone 5: Actions (sticky bottom)

- **Lưu nháp** (secondary) — save partial, can resume
- **Lưu và tiếp tục** (primary) — submit batch, redirect to Invoice preview

---

## Interactions

### Input behaviors

- **Auto-focus**: cursor focus first empty "Kỳ này" input on mount
- **Tab order**: input → input theo thứ tự phòng (top to bottom)
- **Enter key**: move focus to next input (same behavior as Tab)
- **Number validation**: chỉ accept integer ≥ 0, no decimals (reading
  công tơ thực tế chỉ integer)
- **Live computation**: tiêu thụ + warning icon update on blur

### Warnings (non-blocking)

| Scenario | Icon | Message (tooltip) |
|---|---|---|
| Consumption = 0 | ⚠️ | "Tiêu thụ bằng 0 — đồng hồ có hỏng không?" |
| Consumption < 0 | 🔴 | "Tiêu thụ âm — nhập lại hoặc xác nhận đồng hồ reset" |
| Consumption > 2× average | ⚠️ | "Tiêu thụ cao bất thường — kiểm tra" |
| Same value as previous | ⚠️ | "Giá trị không đổi — phòng có người ở không?" |

Warnings không block submit (Phase 2 decision US-067: warn, không block).

### Submit

- Click "Lưu và tiếp tục":
  1. Client validate: nothing (warnings OK to submit)
  2. `POST /api/v1/properties/{pid}/meter-readings/batch` với payload
     chứa tất cả readings đã nhập (skip phòng empty)
  3. Success: toast "Đã lưu X chỉ số công tơ" → redirect to
     `/properties/{pid}/invoices/preview?month=YYYY-MM`
  4. Error: inline error per field (validation), hoặc toast (network)

---

## States

| State | What shows |
|---|---|
| Initial | Step 1 only, Step 2+3 grayed out |
| Property selected | Step 2 loads (prev readings fetched) |
| All typing | Live summary update in Step 3 |
| Submitting | Primary button spinner, disable inputs |
| Success | Redirect (no success screen) |
| Partial error | Inline red borders per field, error summary top of Step 3 |

---

## Claude Design Prompt (copy-paste below)

```
Create a low-fidelity wireframe for a "batch meter reading" form
in RMS (Rental Management System). This is the most complex data
entry screen.

Use case: Landlord reads electric/water meters for all rooms in one
property at once (monthly workflow). Screen must support fast
data entry for 10-50 rooms.

Layout (desktop 1280x1000):

Top: Same sidebar nav as dashboard. Main content has:

1. Header: back link "< Quay lại" + page title "Nhập chỉ số công tơ"

2. Step 1 card — "Bước 1: Chọn nhà và tháng":
   - Property dropdown "Nhà Hoàng Cầu (8 phòng)"
   - Month dropdown "Tháng 4/2026"
   - Read-only date "Chỉ số ngày: 01/05/2026"

3. Step 2 card — "Bước 2: Nhập chỉ số":
   a. Service card "Điện (kWh) — điện riêng theo phòng":
      Table with columns: "Phòng", "Kỳ trước", "Kỳ này" (input),
      "Tiêu thụ" (computed), "Warn" (icon column).
      Show 5-6 rows:
      - P101, 1250, [1380], 130, (no warn)
      - P102, 2110, [2245], 135, (no warn)
      - P103, 890, [empty input], "—", (no warn)
      - P104, 3420, [3420], 0, ⚠️ warning icon
      - P105, 1820, [1790], -30, 🔴 error icon

   b. Service card "Nước (m³) — đồng hồ chung chia theo người":
      Simpler layout: "Kỳ trước: 450", "Kỳ này: [485]" input,
      "Tiêu thụ: 35 m³ → chia cho 23 người ở"

4. Step 3 card — "Bước 3: Xem lại và lưu":
   Summary list with status icons:
   - "✅ 7 phòng đã nhập đủ"
   - "⚠️ 1 phòng có tiêu thụ bằng 0 (P104)"
   - "🔴 1 phòng có tiêu thụ âm (P105)"
   - "⏭️ 1 phòng chưa nhập (P103)"

5. Sticky bottom action bar:
   - Secondary button "Lưu nháp"
   - Primary button "Lưu và tiếp tục"

Style: low-fidelity wireframe, grayscale, emphasis on table
structure readability. Information-dense. Tables should look
scannable (alternating row subtle background OK in grayscale).
Reference shadcn/ui Table component aesthetic.

Locale: Vietnamese as shown.
```

---

## Acceptance Criteria

- [ ] 3 steps visually separated (cards or dividers)
- [ ] Step 1 shows property + month selectors
- [ ] Step 2 shows ≥2 service cards (per-room table + shared simple)
- [ ] Table columns: Phòng, Kỳ trước, Kỳ này (input), Tiêu thụ, Warn
- [ ] Warning icons visible (at least 2 different states shown)
- [ ] Step 3 summary with status icons
- [ ] Sticky bottom with 2 buttons
- [ ] No decorative colors (warnings allowed to have subtle emphasis)

---

**Export**: Save as `03-meter-batch.png` in this folder.
