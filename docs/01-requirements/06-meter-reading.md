# User Stories — Nhóm 6: Meter Reading (Chỉ số đồng hồ)

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-18
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **Meter Reading (Chỉ số đồng hồ)** — việc ghi nhận
số đọc từ công tơ điện/nước tại một thời điểm. Reading là input cơ sở
để tính tiền điện/nước trong Invoice hàng tháng (Nhóm 7).

**Map với Vision:**

- MVP feature #5: Ghi chỉ số điện/nước hàng tháng, lưu lịch sử, số mới tự
  động thành số cũ cho kỳ tiếp theo

**Key decisions (đã chốt):**

| #   | Decision                                                     | Lý do                                          |
| --- | ------------------------------------------------------------ | ---------------------------------------------- |
| 1   | Point-in-time schema: 1 record = 1 reading                   | Single source of truth, consumption computed   |
| 2   | Chỉ Landlord nhập reading ở MVP                              | Tránh chaos khi Tenant nhập không đồng đều     |
| 3   | Manual Invoice trigger sau khi có reading (Pattern Y.2)      | Invoice luôn sinh ra đầy đủ, không half-baked  |
| 4   | Batch nhập reading cho toàn Property (1 form duy nhất)       | Match workflow thực tế của Landlord            |
| 5   | Reminder ngày 5 hàng tháng nếu chưa xuất Invoice             | Tránh quên, giữ tính nhẹ nhàng                 |
| 6   | Validate `reading_value >= previous_value`                   | Case thực tế không có reset, giữ rule đơn giản |
| 7   | `room_id` nullable: NULL = shared meter, có value = per-room | Gắn với scope của Service                      |
| 8   | Shared meter `applied_rooms` fix ở Service, không chọn lại   | Config 1 lần khi tạo Service                   |
| 9   | Auto-fill previous reading trong form                        | UX tốt, tránh nhập sai số cũ                   |
| 10  | Reading mutable khi Invoice reference chưa có Payment        | Match case thực tế nhập sai + chưa thu tiền    |
| 11  | Reading gắn với Room, dùng tiếp khi Lease mới                | Công tơ thuộc phòng, không thuộc Tenant        |
| 12  | Skip anomaly warning ở MVP                                   | Tránh over-engineering, v1.x add               |

## Personas liên quan

- **Landlord** (Persona A): primary actor, nhập reading
- **Tenant** (Persona B): xem consumption của phòng mình (read-only)

## Dependencies

- **Depends on**: Nhóm 2 (Room), Nhóm 5 (Service per_meter)
- **Blocks**: Nhóm 7 (Invoice — Invoice dùng reading để tính tiền điện/nước)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Core Concepts

### Reading là domain event, không phải entity

Meter Reading **mô tả sự thật vật lý tại 1 thời điểm** (đồng hồ hiện số X
lúc Y). Sự thật quá khứ không đổi. Đây là **event**, append-only bản chất.

Hệ quả:

- 1 record = 1 reading (point-in-time)
- Consumption = reading(now) - reading(previous) — **computed**, không lưu
- "Sửa reading" chỉ được phép khi chưa có downstream consequence (Invoice
  chưa có Payment)

### Reading gắn với gì?

| Service scope    | Reading gắn với              | `room_id` |
| ---------------- | ---------------------------- | --------- |
| `all_rooms`      | Room cụ thể (1 công tơ/Room) | NOT NULL  |
| `selected_rooms` | Service (1 công tơ chung)    | NULL      |

### Lifecycle của 1 Reading

```
┌─────────────┐
│   Created   │ ← Landlord nhập
└──────┬──────┘
       │
       ↓
┌─────────────┐
│   Unused    │ ← Chưa có Invoice tham chiếu
└──────┬──────┘
       │ (Landlord xuất Invoice tháng đó)
       ↓
┌─────────────┐
│   Locked    │ ← Invoice đã tham chiếu, Tenant đã trả
└─────────────┘

       Có thể sửa:
       - Unused: sửa thoải mái
       - Invoice tham chiếu unpaid + chưa có Payment: sửa được, rebuild Invoice
       - Invoice paid hoặc có Payment: KHÔNG sửa, phải adjustment ở Invoice tháng sau (Nhóm 7)
```

---

## Stories

### US-070: Landlord nhập initial reading khi tạo Service per_meter

**As a** Landlord vừa tạo Service per_meter cho Property
**I want to** nhập số đầu tiên của mỗi công tơ
**So that** tháng đầu tiên tính được consumption chính xác

**Priority**: Must
**Estimate**: M
**Depends on**: US-060 (Service all_rooms per_meter), US-061 (Service
selected_rooms per_meter)

**Acceptance Criteria:**

- [ ] AC1: Sau khi Landlord tạo Service `per_meter` → redirect sang form
      "Nhập chỉ số khởi đầu"
- [ ] AC2: Nếu Service có `scope = 'all_rooms'`:
  - Form hiện bảng các Room không-archived trong Property
  - Mỗi Room có 1 ô nhập: `reading_value` (bắt buộc, >= 0)
  - 1 ô nhập `reading_date` chung cho cả batch (default = today)
- [ ] AC3: Nếu Service có `scope = 'selected_rooms'`:
  - Form chỉ có 1 ô nhập duy nhất (vì là công tơ chung)
  - Hiển thị: "Công tơ này dùng chung cho: Phòng [X, Y, Z]"
  - `reading_value` (bắt buộc, >= 0)
  - `reading_date` (default = today)
- [ ] AC4: Validation:
  - Tất cả `reading_value >= 0`
  - `reading_date` không được trong tương lai
- [ ] AC5: Submit → tạo MeterReading records với các value đã nhập
- [ ] AC6: **Cho phép skip**: Landlord có thể bỏ qua, không nhập initial
      reading. Khi đó Service vẫn được tạo, nhưng sẽ không có số cũ khi
      nhập reading lần sau (US-071 sẽ handle edge case này).
- [ ] AC7: Sau khi submit → redirect về trang danh sách Service với message
      "Đã lưu chỉ số khởi đầu cho [tên Service]"
- [ ] AC8: Chỉ Landlord sở hữu Property thực hiện được

**Notes:**

- AC6 cho phép skip vì thực tế Landlord có thể:
  - Chưa đến tháng mới, chưa đọc số
  - Tạo Service trước, tháng sau mới đi đọc
    → Ép nhập ngay sẽ làm friction. Cho skip, nhưng warn ở lần nhập đầu tiên.

- Logic khi nhập reading lần đầu mà không có initial reading (AC6 skip):
  - Treat số đầu tiên nhập như initial
  - Tháng sau mới có consumption thực

- AC3 shared meter UI: quan trọng phải hiển thị rõ "dùng chung cho phòng
  nào" để Landlord confirm đúng công tơ.

---

### US-071: Landlord nhập reading định kỳ (batch per Property)

**As a** Landlord đầu tháng đi đọc công tơ cả nhà
**I want to** nhập chỉ số tháng mới cho tất cả Service per_meter trong 1 form
**So that** tôi nhập 1 lượt thay vì 10 lần cho 10 phòng

**Priority**: Must
**Estimate**: L
**Depends on**: US-070

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Property, có nút "Nhập chỉ số tháng [current_month]"
- [ ] AC2: Click → form batch hiển thị:
  - Tiêu đề: "Nhập chỉ số tháng [X]/[Y]"
  - Field `reading_date` chung (default = today)
  - **Section 1: Dịch vụ theo chỉ số riêng phòng** (Service per_meter,
    scope=all_rooms, is_active=true):
    - Với mỗi Service → 1 sub-section
    - Sub-section hiện bảng: Room | Số cũ | Số mới | Consumption (auto-calc)
    - Mỗi Room 1 row
    - "Số cũ" auto-fill từ reading gần nhất, read-only
    - "Số mới" là input
    - "Consumption" auto-calc = số mới - số cũ (hiển thị khi nhập)
  - **Section 2: Dịch vụ theo chỉ số dùng chung** (Service per_meter,
    scope=selected_rooms, is_active=true):
    - Với mỗi Service → 1 row
    - Row hiện: Tên Service (dùng cho: [rooms]) | Số cũ | Số mới | Consumption
- [ ] AC3: Auto-fill logic:
  - Số cũ = `reading_value` của MeterReading gần nhất của cùng
    (service, room) hoặc (service, NULL) với shared meter
  - Nếu chưa có reading nào (Service vừa tạo, skip initial) → "Số cũ" = 0,
    hiển thị warning nhỏ: "Chưa có chỉ số trước"
- [ ] AC4: Real-time validation mỗi ô nhập:
  - `reading_value >= 0`
  - `reading_value >= previous_value` → nếu nhỏ hơn, hiện warning **inline**
    (không block submit): "Số mới [X] nhỏ hơn số cũ [Y]. Kiểm tra lại?"
  - Warning chỉ là nhắc, Landlord có thể bypass
- [ ] AC5: **Cho phép submit partial**: Landlord không bắt buộc nhập tất cả
      Room/Service. Row trống → không tạo reading cho row đó.
- [ ] AC6: Submit → tạo/update MeterReading records:
  - Nếu đã có reading cùng (service, room, reading_date) → update value
    (để Landlord có thể sửa ngay trong form, chưa kịp escape-fix qua US-073)
  - Nếu chưa → insert mới
- [ ] AC7: Transaction: tất cả reading trong batch lưu atomic (all or nothing)
- [ ] AC8: Sau submit → redirect về trang chi tiết Property với:
  - Message: "Đã lưu chỉ số cho [N] phòng / [M] dịch vụ"
  - CTA nổi bật: "Xuất Invoice tháng [X] cho Property này" (link sang Nhóm 7)
- [ ] AC9: Chỉ Landlord sở hữu Property thực hiện được

**Notes:**

- AC2 UI: với Property 20 phòng × 2 service per_meter = 40 rows + shared
  meters. Cần design responsive: desktop hiện table, mobile hiện accordion.
- AC4 warning không block: match Q3 decision (Bảo nói rule đơn giản,
  không cần case reset/thay đồng hồ).
- AC5 partial submit: thực tế Landlord có thể quên đọc 1 phòng, về nhập
  các phòng khác trước, lúc nào đọc được phòng còn lại thì vào nhập bổ sung.
- AC6 update behavior: quan trọng cho UX. Landlord nhập 150 rồi thấy sai,
  nhập lại 160 cùng ngày → update record cũ, không tạo 2 record. Nếu nhập
  ngày khác → tạo record mới.
- AC8 CTA sang Nhóm 7: giữ flow liền mạch "nhập số → xuất Invoice".

---

### US-072: Landlord xem lịch sử reading

**As a** Landlord
**I want to** xem tất cả reading đã nhập cho 1 Room/Service
**So that** tôi tra cứu được khi có tranh chấp hoặc muốn verify

**Priority**: Must
**Estimate**: S
**Depends on**: US-071

**Acceptance Criteria:**

- [ ] AC1: Có 2 entry points để xem lịch sử reading:
  - Trang chi tiết Service → tab "Lịch sử chỉ số"
  - Trang chi tiết Room → tab "Chỉ số đồng hồ"
- [ ] AC2: Hiển thị bảng với columns:
  - `reading_date`
  - `reading_value`
  - `previous_value` (computed từ reading trước)
  - `consumption` (computed)
  - `unit` (từ Service)
  - Invoice tham chiếu (nếu có — link sang Nhóm 7)
  - Actions: Sửa (nếu điều kiện đủ — US-073), Xem chi tiết
- [ ] AC3: Default sort: `reading_date DESC` (mới nhất trên đầu)
- [ ] AC4: Filter theo khoảng thời gian (từ ngày - đến ngày)
- [ ] AC5: Nếu trang Room: hiện reading của **tất cả Service per_meter**
      liên quan đến Room (cả all_rooms và selected_rooms chứa Room này)
- [ ] AC6: Nếu trang Service scope=selected_rooms: hiện reading của shared
      meter (không có room_id), rõ "Dùng chung cho phòng X, Y, Z"
- [ ] AC7: Empty state thân thiện: "Chưa có chỉ số nào. [Nhập chỉ số →]"
- [ ] AC8: Chỉ Landlord sở hữu xem được

**Notes:**

- AC2 "Invoice tham chiếu": giúp Landlord biết reading nào đã locked (không
  sửa được nữa).
- v1.x có thể thêm: biểu đồ consumption theo tháng, detect anomaly.

---

### US-073: Landlord sửa reading (với điều kiện)

**As a** Landlord phát hiện nhập nhầm reading
**I want to** sửa lại nếu hệ thống cho phép
**So that** dữ liệu chính xác, Invoice đúng

**Priority**: Should
**Estimate**: M
**Depends on**: US-071

**Acceptance Criteria:**

- [ ] AC1: Nút "Sửa" trên row reading trong trang lịch sử (US-072)
- [ ] AC2: **Điều kiện cho phép sửa** — check trước khi mở form:
  - **Case 1** (editable tự do): Reading **chưa được Invoice nào tham chiếu**
  - **Case 2** (editable có cảnh báo): Reading được Invoice tham chiếu,
    nhưng **Invoice đó có status = `unpaid` AND chưa có Payment nào**
  - **Case 3** (không cho sửa): Reading được Invoice tham chiếu có status
    `partial`/`paid` hoặc có Payment → nút "Sửa" disabled với tooltip:
    "Chỉ số này đã dùng cho Invoice đã thanh toán. Tạo điều chỉnh ở Invoice
    tháng sau."
- [ ] AC3: Form sửa cho phép edit: `reading_value`, `reading_date`
- [ ] AC4: Validation như US-071 AC4 (warn nếu < previous, không block)
- [ ] AC5: **Case 2 warning trước khi submit:**
      "Chỉ số này đang được dùng cho Invoice #[X] tháng [Y] (chưa thanh toán).
      Khi sửa chỉ số, Invoice #[X] sẽ KHÔNG tự cập nhật.
      Nếu bạn muốn Tenant thấy Invoice đúng với chỉ số mới:

Sửa chỉ số (bước hiện tại)
Vào Invoice #[X] → Void Invoice
Xuất Invoice mới cho tháng đó"

- Landlord chọn "Tôi hiểu, tiếp tục sửa" → submit
- [ ] AC6: Submit → update MeterReading record. KHÔNG tự động touch Invoice.
- [ ] AC7: Sau submit → toast message + redirect về trang lịch sử reading
- [ ] AC8: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC2 là **Invoice Immutability Pattern** (đã document ở Nhóm 5) áp dụng
  ngược: reading tạo ra Invoice, Invoice chưa có Payment thì upstream
  (reading) còn sửa được.
- AC5 option [B] hiếm dùng, nhưng giữ để edge case: Landlord muốn sửa
  reading cho thống kê nội bộ mà không muốn Invoice đổi (đã thoả thuận với
  Tenant giá cũ).
- AC6 rebuild Invoice: Nhóm 7 sẽ expose endpoint để nhận trigger này.
  Nhóm 6 chỉ cần call sang.

---

### US-074: Dashboard reminder — chưa xuất Invoice tháng này

**As a** Landlord bận rộn, hay quên workflow hàng tháng
**I want to** được nhắc khi chưa xuất Invoice dù đã qua đầu tháng
**So that** Tenant không bị thiếu hoá đơn, tôi không mất tiền thu

**Priority**: Should
**Estimate**: S
**Depends on**: US-071

**Acceptance Criteria:**

- [ ] AC1: Trên dashboard Landlord, có widget "Cần xử lý":
  - Condition hiển thị: `today >= ngày 5 của tháng` **AND** tồn tại Property
    chưa có Invoice cho tháng đó
  - Trước ngày 5 → widget không hiện (tránh làm phiền lúc chưa cần)
- [ ] AC2: Widget hiển thị list:
  - Property A: "Chưa xuất Invoice tháng [X] cho [N] phòng"
  - Property B: "Chưa nhập chỉ số tháng [X]" (nếu còn thiếu reading)
  - Property C: "Đã nhập đủ chỉ số, chưa xuất Invoice"
- [ ] AC3: Click → điều hướng sang trang Property tương ứng với CTA cụ thể:
  - Nếu thiếu reading → "Nhập chỉ số tháng [X]" (US-071)
  - Nếu đã có reading, thiếu Invoice → "Xuất Invoice tháng [X]" (Nhóm 7)
- [ ] AC4: Widget rỗng → không hiển thị (không phải empty state, mà ẩn hẳn)
- [ ] AC5: Reminder chỉ cho **tháng hiện tại + tháng trước nếu quá hạn**.
      Không spam reminder cho nhiều tháng cũ.
- [ ] AC6: Update real-time khi load dashboard

**Notes:**

- AC1 ngày 5: cố định ở MVP. Không configurable để tránh complexity.
  v1.x có thể cho Landlord set.
- AC5 giới hạn scope để reminder có ý nghĩa. Landlord bỏ 3 tháng không
  dùng app → vào lại chỉ thấy 1-2 tháng cảnh báo, không bị ngợp.
- Không có notification thật ở MVP (không push/email/Zalo). Widget chỉ
  hiện khi Landlord vào app. v1.x plug notification framework.

---

### US-075: Tenant xem consumption của phòng mình

**As a** Tenant đã login
**I want to** xem các chỉ số và consumption điện/nước của phòng mình
**So that** tôi hiểu Invoice được tính từ đâu, minh bạch

**Priority**: Should
**Estimate**: S
**Depends on**: US-071, US-005 (Tenant login)

**Acceptance Criteria:**

- [ ] AC1: Trên dashboard Tenant, có section "Chỉ số đồng hồ tháng này"
- [ ] AC2: Hiển thị bảng:
  - Service (Điện, Nước, ...)
  - Số cũ (reading tháng trước)
  - Số mới (reading tháng này)
  - Consumption
  - Unit
- [ ] AC3: Chỉ hiện reading của Service áp dụng cho Room của Tenant:
  - Service `scope=all_rooms` → reading với `room_id = tenant's room_id`
  - Service `scope=selected_rooms` chứa Room của Tenant → reading chung
    (hiển thị thêm note: "Chia với phòng [X, Y]")
- [ ] AC4: Tenant **không thấy** reading của Room khác (privacy)
- [ ] AC5: Nếu tháng hiện tại chưa có reading → hiện:
      "Chủ nhà chưa nhập chỉ số tháng này. Thường nhập đầu tháng sau."
- [ ] AC6: Có section "Lịch sử" nếu Tenant muốn xem reading các tháng trước
      (chỉ của Room mình)
- [ ] AC7: Read-only: Tenant không nhập/sửa gì

**Notes:**

- AC3 shared meter: Tenant thấy được chỉ số tổng, nhưng không biết cách
  phân bổ cụ thể (không thấy số người phòng khác). MVP chỉ hiện thông tin
  cơ bản, đủ minh bạch.
- AC5 message "thường nhập đầu tháng sau" giúp Tenant không hoảng khi
  chưa thấy consumption.
- v1.x: biểu đồ so sánh consumption các tháng, giúp Tenant tự quản lý
  hành vi tiêu dùng.

---

## Open Questions (cần trả lời trước Phase 3)

1. **Reading có cần attach photo (ảnh chụp công tơ) không?**
   - MVP skip (không có storage tích hợp)
   - v1.x: Landlord có thể chụp ảnh làm evidence, lưu S3/local
   - Đáng cân nhắc vì tranh chấp điện nước hay xảy ra

2. **Reading date chung hay riêng trong 1 batch?**
   - US-071 AC2: 1 `reading_date` chung cho cả batch
   - Case thực tế: Landlord đi đọc trong 2 ngày (VD nhà có 2 tầng, đọc tầng
     1 ngày 1/5, tầng 2 ngày 2/5)
   - **Đề xuất MVP**: 1 ngày chung. Nếu cần precise → v1.x cho nhập date per-row.

3. **Shared meter với nhiều Service khác nhau cùng 1 công tơ?**
   - Edge case: 1 công tơ điện dùng chung, chia 1 phần cho WC và 1 phần
     cho hành lang.
   - Thực tế hiếm. MVP skip.

4. **Reading cho Service đã `is_active = false`?**
   - Service tạm tắt (VD: hỏng máy giặt) → không nhập reading
   - US-071 AC2 đã filter `is_active=true` → OK

5. **Ngày đọc có phải = billing_day của Lease không?**
   - Không cần. `reading_date` là ngày Landlord đọc, có thể khác
     `billing_day`. Invoice tính consumption trong khoảng thời gian cụ thể,
     không tính per ngày.
   - Nhưng **consumption thuộc về tháng nào?** Xem Open Q#6.

6. **Rule map reading → tháng billing:**
   - Option A: Reading ngày X thuộc về **tháng chứa ngày X**
     (VD: đọc 1/5 → tháng 5 có consumption 4/4-1/5)
   - Option B: Reading ngày X thuộc về **tháng trước** (VD: đọc 1/5 →
     tháng 4 có consumption 1/4-1/5)
   - Thực tế: Landlord đọc đầu tháng để tính cho tháng trước → **Option B**
   - **Đề xuất chốt: Option B**. Chi tiết logic ở Nhóm 7 (Invoice).

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships (preview):**

```
Service     1──* MeterReading
Room        0──* MeterReading  (chỉ khi Service.scope=all_rooms)
Invoice     1──* InvoiceLineItem
InvoiceLineItem 0──1 MeterReading  (tham chiếu reading nào được dùng để tính line item)
```

**Trường DB dự kiến:**

```
MeterReading:
  id, service_id (FK, NOT NULL),
  room_id (FK, NULLABLE — null nếu Service.scope=selected_rooms),
  reading_value (decimal, >= 0),
  reading_date (date),
  created_at, updated_at, created_by (FK → User role=landlord)

Constraints:
  - IF Service.scope = 'all_rooms' THEN room_id NOT NULL
  - IF Service.scope = 'selected_rooms' THEN room_id NULL
  - UNIQUE(service_id, room_id, reading_date) — 1 công tơ không có 2 reading
    cùng ngày

Indexes:
  - (service_id, room_id, reading_date DESC) — để query "reading gần nhất"
```

**Computed fields (không lưu DB):**

- `MeterReading.previous_value`: query reading trước đó của cùng (service, room)
- `MeterReading.consumption`: current - previous
- `MeterReading.is_editable`: check có Invoice tham chiếu chưa + Payment
- `MeterReading.invoice_ref`: Invoice nào đang dùng reading này (nếu có)

**Query patterns chính:**

```sql
-- Reading gần nhất cho 1 công tơ (để auto-fill số cũ)
SELECT * FROM meter_reading
WHERE service_id = ? AND (room_id = ? OR (room_id IS NULL AND ? IS NULL))
ORDER BY reading_date DESC LIMIT 1;

-- Danh sách reading cần nhập tháng N cho Property
SELECT s.*, r.*
FROM service s
LEFT JOIN room r ON r.property_id = s.property_id
WHERE s.billing_type = 'per_meter'
  AND s.is_active = true
  AND s.property_id = ?;

-- Check reading có editable không
SELECT mr.*, i.status, COUNT(p.id) as payment_count
FROM meter_reading mr
LEFT JOIN invoice_line_item ili ON ili.meter_reading_id = mr.id
LEFT JOIN invoice i ON i.id = ili.invoice_id
LEFT JOIN payment p ON p.invoice_id = i.id
WHERE mr.id = ?
GROUP BY mr.id, i.status;
```

Sẽ finalize ở Phase 3 (Architecture + Database Design).

---

## Summary

| Story  | Title                                                   | Priority | Estimate |
| ------ | ------------------------------------------------------- | -------- | -------- |
| US-070 | Landlord nhập initial reading khi tạo Service per_meter | Must     | M        |
| US-071 | Landlord nhập reading định kỳ (batch per Property)      | Must     | L        |
| US-072 | Landlord xem lịch sử reading                            | Must     | S        |
| US-073 | Landlord sửa reading (với điều kiện)                    | Should   | M        |
| US-074 | Dashboard reminder — chưa xuất Invoice tháng này        | Should   | S        |
| US-075 | Tenant xem consumption của phòng mình                   | Should   | S        |

**Total**: 6 stories (3 Must + 3 Should).
**Estimate**: 1L + 2M + 3S ≈ 1–1.5 sprint.
