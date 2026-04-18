# User Stories — Nhóm 5: Service (Dịch vụ)

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-17
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **Service (Dịch vụ)** — các khoản phí ngoài tiền phòng
như điện, nước, internet, rác, giữ xe. Service là **template** để sinh
Invoice hàng tháng (Nhóm 7).

**Map với Vision:**

- MVP feature #4: Cấu hình dịch vụ với nhiều kiểu tính (theo đồng hồ,
  theo đầu người, cố định)

**Key decisions (đã chốt):**

| #   | Decision                                                      | Lý do                                              |
| --- | ------------------------------------------------------------- | -------------------------------------------------- |
| 1   | 3 billing types: `per_meter` / `per_person` / `fixed`         | Đủ cover mọi dịch vụ thực tế ở nhà trọ             |
| 2   | Service config ở Property-level                               | Thực tế không ai muốn mỗi phòng 1 giá dịch vụ      |
| 3   | Service scope: `all_rooms` hoặc `selected_rooms`              | Hỗ trợ case công tơ chung (WC chung 2 phòng)       |
| 4   | `selected_rooms` chỉ cho `per_meter`                          | Thực tế chỉ cần chia công tơ chung, không cần khác |
| 5   | Shared per_meter chia theo **số người** các phòng trong scope | Phù hợp cách tính thực tế                          |
| 6   | Live Service pricing + Invoice snapshot                       | Service là template; Invoice immutable sau khi tạo |
| 7   | Service lifecycle: toggle `is_active` (không xoá)             | Giữ reference cho Invoice cũ                       |
| 8   | Không đổi giá giữa kỳ (áp dụng từ tháng sau)                  | Đơn giản MVP                                       |
| 9   | Unit auto theo billing_type, chỉ nhập cho `per_meter`         | Giảm friction nhập liệu                            |
| 10  | Không per-Lease override ở MVP                                | Work-around bằng `rent_amount` nếu cần             |

## Personas liên quan

- **Landlord** (Persona A): CRUD Service, toggle is_active
- **Tenant** (Persona B): xem Service áp dụng cho phòng mình (read-only)

## Dependencies

- **Depends on**: Nhóm 2 (Property, Room — Service gắn với Property, có
  thể target subset Rooms)
- **Blocks**: Nhóm 6 (Meter Reading — reading gắn với Service `per_meter`),
  Nhóm 7 (Invoice — Invoice generate từ Service)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Core Concepts

### Billing Types

| Type         | Cách tính                         | Ví dụ                   |
| ------------ | --------------------------------- | ----------------------- |
| `per_meter`  | (số_mới − số_cũ) × đơn_giá        | Điện (kWh), nước (m³)   |
| `per_person` | số_người × đơn_giá                | Rác, giữ xe, thang máy  |
| `fixed`      | đơn_giá (cố định / phòng / tháng) | Internet, vệ sinh chung |

### Service Scope

| Scope            | Áp dụng cho                                 | Khi nào dùng                       |
| ---------------- | ------------------------------------------- | ---------------------------------- |
| `all_rooms`      | Tất cả Room trong Property (default)        | 95% Service                        |
| `selected_rooms` | Subset Room được chọn (chỉ cho `per_meter`) | Công tơ chung (WC, hành lang, ...) |

### Invoice Immutability Pattern

**Nguyên tắc cốt lõi:** Invoice phải **immutable** sau khi tạo.

Khi tạo Invoice tháng N:

```
1. Query Service hiện tại (live pricing) → unit_price, billing_type
2. Snapshot vào InvoiceLineItem:
   - service_name: copy từ Service.name (không FK)
   - unit_price: copy giá tại thời điểm
   - quantity: tính theo billing_type
   - amount: unit_price × quantity
3. Invoice lưu độc lập, Service đổi sau không ảnh hưởng
```

**Hệ quả:**

- Landlord đổi giá Service → chỉ Invoice **chưa tạo** bị ảnh hưởng
- Invoice đã tạo **luôn giữ giá tại thời điểm tạo**
- Xoá Service (hoặc tắt is_active) → Invoice cũ vẫn hiển thị đúng

Chi tiết implementation ở Nhóm 7.

---

## Stories

### US-060: Landlord tạo Service (all_rooms)

**As a** Landlord setup nhà trọ mới hoặc thêm dịch vụ
**I want to** tạo Service áp dụng cho tất cả phòng trong nhà
**So that** Invoice hàng tháng tự động tính thêm các khoản phí này

**Priority**: Must
**Estimate**: L
**Depends on**: US-011 (Property tồn tại)

**Acceptance Criteria:**

- [ ] AC1: Form tạo Service có các trường chung:
  - `property_id` (bắt buộc, chọn từ Property Landlord sở hữu)
  - `name` (bắt buộc, max 100 ký tự) — VD: "Tiền điện", "Internet",
    "Phí rác"
  - `billing_type` (bắt buộc, radio):
    - `per_meter`: Theo chỉ số đồng hồ
    - `per_person`: Theo số người
    - `fixed`: Cố định / phòng / tháng
  - `unit_price` (bắt buộc, > 0) — đơn giá VND
  - `description` (tuỳ chọn, free text max 200 ký tự) — VD: "Giá điện
    nhà nước + 10%"
  - `is_active` (default = true)
- [ ] AC2: **Trường bổ sung khi `billing_type = per_meter`:**
  - `unit` (bắt buộc, dropdown):
    - `kWh` (default cho điện)
    - `m³` (default cho nước)
    - `khác` → cho Landlord nhập free text max 20 ký tự
- [ ] AC3: **Trường tự động khi `billing_type = per_person`:**
  - `unit` = "người/tháng" (hiển thị read-only, không cho sửa)
- [ ] AC4: **Trường tự động khi `billing_type = fixed`:**
  - `unit` = "tháng" (hiển thị read-only, không cho sửa)
- [ ] AC5: **Scope mặc định = `all_rooms`** (form US-060 không có UI chọn
      phòng). Muốn tạo Service chia chung → dùng form US-061.
- [ ] AC6: Validation:
  - `name` unique trong Property (cùng Property không thể có 2 Service cùng tên)
  - `unit_price > 0`
  - Nếu `billing_type = per_meter` và `unit = "khác"` → unit text không
    được rỗng
- [ ] AC7: Preview đơn giá trước khi submit:
  - `per_meter`: "3.500đ/kWh"
  - `per_person`: "20.000đ/người/tháng"
  - `fixed`: "100.000đ/tháng"
- [ ] AC8: Tạo thành công → redirect về trang danh sách Service với message
      "Đã tạo Service [tên]"
- [ ] AC9: Chỉ Landlord sở hữu Property mới tạo được Service

**Notes:**

- AC1 `name` unique trong Property: cho phép 2 Property khác nhau cùng có
  Service "Tiền điện". Nhưng trong 1 Property, tên phải unique để tránh
  nhầm.
- AC2 dropdown "khác": edge case Landlord có dịch vụ đặc thù
  (VD: "phần", "bộ"). Hiếm nhưng cần.
- AC7 preview là UX quan trọng: Landlord confirm trước khi lưu, tránh
  nhầm `unit_price` (thêm/bớt số 0).
- Service `per_meter` với scope `all_rooms` ngụ ý **mỗi phòng có công tơ
  riêng**. Meter reading (Nhóm 6) sẽ lưu từng phòng.

---

### US-061: Landlord tạo Service `per_meter` chia chung (selected_rooms)

**As a** Landlord có công tơ chung cho nhiều phòng (VD: WC chung, hành lang)
**I want to** tạo Service tính theo 1 công tơ nhưng chia cho các phòng dùng chung
**So that** chi phí được phân bổ công bằng theo số người, không phải cộng
vào rent

**Priority**: Should
**Estimate**: M
**Depends on**: US-060

**Context thực tế:**

Nhà trọ có 5 phòng, trong đó phòng 1 và phòng 2 dùng chung 1 WC. WC có
bóng đèn, quạt hút → tốn điện. Công tơ điện WC chung cho 2 phòng.

- Phòng 1: 1 người
- Phòng 2: 2 người
- Tổng điện WC tháng 5: 20 kWh × 3.500đ = 70.000đ
- Chia: Phòng 1 chịu 70.000 × (1/3) = 23.333đ
- Chia: Phòng 2 chịu 70.000 × (2/3) = 46.667đ

**Acceptance Criteria:**

- [ ] AC1: Form "Tạo Service chia chung" có:
  - Các trường như US-060 AC1 (name, unit_price, description, is_active)
  - `billing_type = per_meter` (cố định, không cho chọn khác)
  - `unit` (dropdown: kWh / m³ / khác)
  - `scope = 'selected_rooms'` (cố định)
  - `applied_rooms` (bắt buộc, multi-select từ Rooms trong Property,
    tối thiểu 2 phòng)
- [ ] AC2: Validation:
  - Phải chọn ≥ 2 phòng (1 phòng thì dùng US-060 all_rooms cho gọn, hoặc
    tạo Service riêng cho phòng đó)
  - Các phòng được chọn phải thuộc cùng Property
  - `name` unique trong Property (như US-060 AC6)
- [ ] AC3: UI preview rõ ràng:
  - "Service này sẽ tính từ 1 công tơ duy nhất"
  - "Chia đều theo số người các phòng được chọn: [phòng 1, phòng 2]"
  - "Invoice mỗi phòng hiển thị số tiền được phân bổ"
- [ ] AC4: Tạo thành công → lưu Service với `scope = 'selected_rooms'`,
      `applied_rooms = [room_ids]`
- [ ] AC5: Logic phân bổ khi tính Invoice (chi tiết Nhóm 7, chỉ note ở đây):
  ```
  Tổng tiền = (số_mới − số_cũ) × unit_price
  Tổng số người = SUM(số_người_các_phòng_được_chọn)
  Mỗi phòng chịu = Tổng tiền × (số_người_phòng / Tổng số người)
  ```
- [ ] AC6: Nếu có phòng trống (0 người) trong `applied_rooms` tại tháng tính
      → **phòng trống không chịu phí**, chia cho các phòng còn người
- [ ] AC7: Nếu **tất cả** phòng trong scope đều trống → không tạo InvoiceLineItem
      cho tháng đó (tổng số người = 0, không chia được)

**Notes:**

- AC2 tối thiểu 2 phòng: nếu chỉ 1 phòng dùng công tơ riêng → không phải
  "chia chung", dùng US-060 all_rooms + scope tự thành 1 phòng (hoặc tạo
  Service riêng theo phòng đó — nhưng MVP không hỗ trợ scope = 1 phòng
  cụ thể, đây là edge case hiếm).
- AC6 rule "phòng trống không chịu phí": **chốt MVP**. Alternative: chia
  đều theo số phòng (bất kể trống/có người). Cách hiện tại công bằng hơn
  vì điện WC thực tế do người dùng mới tốn.
- AC7 edge case: hiếm xảy ra (cả 2 phòng cùng trống 1 tháng) nhưng phải handle.
- Meter reading (Nhóm 6) cần biết Service này chỉ có 1 công tơ chung
  (không phải mỗi phòng 1 công tơ). Sẽ detail ở Nhóm 6.

---

### US-062: Landlord xem danh sách Service

**As a** Landlord
**I want to** xem tất cả Service đã cấu hình cho Property
**So that** tôi biết phòng thuê của tôi đang thu những khoản gì

**Priority**: Must
**Estimate**: S
**Depends on**: US-060

**Acceptance Criteria:**

- [ ] AC1: Trang danh sách Service của 1 Property hiển thị:
  - Tên Service
  - `billing_type` (badge: "Theo chỉ số" / "Theo người" / "Cố định")
  - Đơn giá + unit ("3.500đ/kWh", "20.000đ/người/tháng", "100.000đ/tháng")
  - Scope: "Tất cả phòng" (all_rooms) hoặc "Phòng [1, 2]" (selected_rooms)
  - `is_active` (badge: "Đang áp dụng" / "Tạm dừng")
- [ ] AC2: Default sort: `is_active DESC`, sau đó `created_at ASC`
      (Service đang áp dụng hiện trước, cái tạo trước lên trước)
- [ ] AC3: Filter:
  - Theo `billing_type`
  - Theo `is_active` (chỉ active / chỉ inactive / tất cả)
- [ ] AC4: Click vào Service → trang chi tiết hiển thị:
  - Tất cả field
  - Số Invoice đã tạo có dùng Service này (tham khảo, không block gì)
  - Nút "Sửa", "Tắt/Bật", "Xoá" (tuỳ điều kiện — xem US-063, US-064, US-065)
- [ ] AC5: Nếu Property chưa có Service nào → empty state thân thiện:
      "Chưa có dịch vụ nào. Tạo Service đầu tiên →"
- [ ] AC6: Chỉ Landlord sở hữu Property mới xem được

**Notes:**

- AC4 "số Invoice đã dùng": đây là chỉ số tham khảo để Landlord biết
  Service này quan trọng thế nào. Không affect logic gì.
- v1.x có thể thêm: tổng doanh thu từ Service này, biểu đồ theo tháng.

---

### US-063: Landlord sửa Service

**As a** Landlord khi giá điện/nước tăng hoặc muốn đổi tên Service
**I want to** sửa thông tin Service hiện tại
**So that** Invoice tháng sau được tính theo giá mới, hoặc tên hiển thị
rõ hơn

**Priority**: Must
**Estimate**: S
**Depends on**: US-060

**Acceptance Criteria:**

- [ ] AC1: Form sửa Service pre-fill data hiện tại
- [ ] AC2: Cho phép sửa:
  - `name`
  - `unit_price` (cảnh báo: xem AC5)
  - `description`
  - `unit` (chỉ khi `billing_type = per_meter`)
  - `applied_rooms` (chỉ khi `scope = selected_rooms`, với điều kiện AC6)
- [ ] AC3: **Không cho sửa**:
  - `property_id`, `billing_type`, `scope` (nếu muốn đổi → xoá và tạo mới)
- [ ] AC4: Validation như US-060 AC6
- [ ] AC5: **Khi sửa `unit_price`**, hiện dialog cảnh báo:
  - "Giá mới chỉ áp dụng cho Invoice được tạo từ thời điểm này trở đi.
    Invoice cũ vẫn giữ giá cũ. Bạn chắc chắn muốn đổi giá không?"
  - Có checkbox: "Tôi hiểu Invoice cũ không bị ảnh hưởng"
  - Phải check mới cho submit
- [ ] AC6: **Khi sửa `applied_rooms`** (selected_rooms Service), hiện cảnh báo:
  - "Thay đổi phòng áp dụng chỉ có hiệu lực từ kỳ tính tiếp theo. Invoice
    tháng hiện tại vẫn giữ phân bổ cũ."
- [ ] AC7: Audit log: ghi lại ai sửa, sửa gì, lúc nào (MVP log DB)
- [ ] AC8: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC3 không cho đổi `billing_type`: logic tính toán khác nhau, đổi type
  giữa chừng sẽ làm loạn. Muốn đổi → tạo Service mới, tắt Service cũ.
- AC5 cảnh báo quan trọng: đây là **Invoice immutability pattern** thể hiện
  ở UI. Landlord phải hiểu rõ trước khi đổi giá.
- AC7 audit log: để khi có tranh chấp "sao tháng 5 tính 3500 nhưng tháng
  6 lên 4000?", Landlord tra được lịch sử.

---

### US-064: Landlord bật/tắt Service (toggle is_active)

**As a** Landlord khi tạm ngừng một dịch vụ (VD: hỏng máy giặt không sửa)
**I want to** tắt Service mà không mất dữ liệu lịch sử
**So that** Invoice tháng sau không tính Service này, nhưng Invoice cũ
vẫn xem được

**Priority**: Must
**Estimate**: S
**Depends on**: US-060

**Acceptance Criteria:**

- [ ] AC1: Nút "Tắt" / "Bật" trên trang chi tiết Service
- [ ] AC2: Click "Tắt" → confirm:
  - "Tắt Service [tên]? Invoice tháng sau sẽ không tính Service này nữa.
    Invoice đã tạo không bị ảnh hưởng."
  - Set `is_active = false`
- [ ] AC3: Click "Bật" → set `is_active = true`, không cần confirm (thao tác
      nhẹ, dễ undo)
- [ ] AC4: Service `is_active = false` vẫn hiển thị trong danh sách
      (với badge "Tạm dừng")
- [ ] AC5: Invoice tạo mới **bỏ qua** Service có `is_active = false`
      (chi tiết Nhóm 7)
- [ ] AC6: Service `is_active = false` **không sửa/xoá được** — phải bật lại
      trước (rule để tránh nhầm: Service đang tắt thường bị quên, Landlord
      vô tình sửa/xoá khi không biết đang tắt)
- [ ] AC7: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- AC6 design choice: bắt Landlord bật trước rồi mới thao tác → buộc phải
  thấy status hiện tại. Alternative: cho phép thao tác cả khi tắt, nhưng
  rủi ro nhầm cao hơn.
- `is_active` là field DB duy nhất quyết định Service có hiệu lực hay không.
  Không có concept "archived" riêng — giảm state phức tạp.

---

### US-065: Landlord xoá Service (chỉ khi chưa dùng)

**As a** Landlord tạo nhầm Service (sai tên, sai billing_type)
**I want to** xoá Service khi chưa có Invoice nào tham chiếu
**So that** data sạch, không cần để lại Service rác

**Priority**: Could
**Estimate**: S
**Depends on**: US-060

**Acceptance Criteria:**

- [ ] AC1: Nút "Xoá" chỉ hiện khi:
  - Service chưa được dùng bởi **bất kỳ Invoice nào** (query
    `COUNT(InvoiceLineItem WHERE service_id = ?) == 0`)
  - Và Service chưa được dùng bởi **bất kỳ Meter Reading nào** (nếu là
    `per_meter`)
  - Và `is_active = true` (phải bật lại trước nếu đang tắt — xem US-064 AC6)
- [ ] AC2: Click "Xoá" → confirm dialog: "Xoá Service [tên]? Hành động
      không thể hoàn tác."
- [ ] AC3: Xoá thành công → hard delete Service record
- [ ] AC4: Nếu Service đã được dùng → nút "Xoá" disabled với tooltip:
      "Không thể xoá Service đã có Invoice tham chiếu. Dùng 'Tắt' để
      ngừng áp dụng."
- [ ] AC5: Chỉ Landlord sở hữu thực hiện được

**Notes:**

- Hard delete chỉ cho case "tạo nhầm, chưa có hệ quả".
- 99% case Landlord sẽ dùng **Tắt** (US-064) thay vì xoá. US-065 ưu tiên
  thấp vì edge case hiếm.
- Priority `Could`: có thể skip hoàn toàn ở sprint đầu, add sau nếu Bảo
  cần.

---

### US-066: Tenant xem Service áp dụng cho phòng mình

**As a** Tenant đã login
**I want to** xem danh sách các khoản phí dịch vụ áp dụng cho phòng tôi đang thuê
**So that** tôi biết Invoice hàng tháng được tính từ đâu, minh bạch

**Priority**: Must
**Estimate**: S
**Depends on**: US-060, US-005 (Tenant login)

**Acceptance Criteria:**

- [ ] AC1: Trên trang chủ Tenant, có section "Dịch vụ áp dụng" hiển thị:
  - Tên Service
  - `billing_type` (với label dễ hiểu: "Theo chỉ số đồng hồ" / "Theo số
    người" / "Cố định")
  - Đơn giá + unit
  - Ghi chú đặc biệt cho `selected_rooms`: "Chia chung với phòng [X, Y]
    theo số người"
- [ ] AC2: Chỉ hiển thị Service:
  - `is_active = true`
  - Và Room của Tenant nằm trong scope của Service (all_rooms hoặc
    Room ∈ applied_rooms)
- [ ] AC3: Không hiển thị Service đã tắt (tránh nhầm lẫn Tenant nghĩ còn
      thu phí)
- [ ] AC4: Không hiển thị `description` (nội bộ của Landlord, có thể chứa
      thông tin không nên show)
- [ ] AC5: Có link "Xem Invoice chi tiết" → trang Invoice (Nhóm 7)

**Notes:**

- AC4 cân nhắc: `description` có thể hữu ích cho Tenant ("giá nhà nước +
  10%" để Tenant hiểu tại sao giá điện cao hơn EVN). Tuy nhiên MVP ẩn để
  an toàn. v1.x có thể thêm field `description_public` riêng.
- Tenant **không thấy** Service không áp dụng cho phòng mình (VD: phòng 1
  không thấy "Điện WC chia với phòng 2, 3").

---

## Open Questions (cần trả lời trước Phase 3)

1. **Price history/audit**: MVP chỉ log khi sửa (US-063 AC7). v1.x có cần
   UI xem lịch sử giá không?
   - Đề xuất: **Có, ở v1.x**. Landlord muốn biết "giá điện tôi đã đổi
     khi nào, từ đâu đến đâu".

2. **Service description cho Tenant**: có cần `description_public` riêng
   không?
   - Đề xuất: **MVP bỏ qua**. v1.x add nếu Tenant phản ánh.

3. **Shared meter với phòng trống (US-061 AC6)**: rule "phòng trống không
   chịu phí" có đúng với mọi case không?
   - Case tranh luận: Landlord muốn phòng trống vẫn chia phí để áp lực
     Tenant sớm lấp phòng?
   - Đề xuất: **MVP giữ rule "phòng trống không chịu"** (công bằng hơn).
     Landlord có thể override bằng cách... không có. Đây là rule cứng.

4. **Service `per_person` với Occupant moved_in/out giữa tháng**: MVP dùng
   snapshot cuối tháng (đếm người active cuối tháng). Đã quyết ở Nhóm 3
   (US-034 Notes).

5. **Tên Service trùng nhau sau khi 1 cái tắt**: VD tắt "Tiền điện" cũ,
   tạo "Tiền điện" mới. Có cho phép không?
   - AC6 của US-060 nói unique trong Property → block. Nhưng AC6 có check
     `is_active` không?
   - Đề xuất: **Unique cả active + inactive**. Ép Landlord phải xoá cái cũ
     hoặc đổi tên. Giảm nhầm lẫn.

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships (preview):**

```
Property      1──* Service
Service       0──* ServiceRoom (junction, chỉ khi scope=selected_rooms)
Room          0──* ServiceRoom

Service       1──* InvoiceLineItem  (nhưng qua snapshot, không FK cứng)
Service       1──* MeterReading  (chỉ per_meter)
```

**Trường DB dự kiến:**

```
Service:
  id, property_id (FK),
  name, description,
  billing_type (enum: per_meter / per_person / fixed),
  unit_price (decimal),
  unit (string, nullable — auto nếu per_person/fixed),
  scope (enum: all_rooms / selected_rooms, default 'all_rooms'),
  is_active (bool, default true),
  created_at, updated_at

  UNIQUE(property_id, name)

ServiceRoom:  (junction table, chỉ tồn tại khi scope=selected_rooms)
  service_id (FK), room_id (FK)
  PRIMARY KEY (service_id, room_id)
```

**Logic phân bổ (pseudo-code, detail ở Nhóm 7):**

```python
def calculate_service_amount_for_room(service, room, month):
    if service.billing_type == 'fixed':
        return service.unit_price

    if service.billing_type == 'per_person':
        n = count_active_persons(room, month)  # Tenant + Occupants
        return service.unit_price * n

    if service.billing_type == 'per_meter':
        if service.scope == 'all_rooms':
            # Meter riêng từng phòng
            reading = get_meter_reading(service, room, month)
            return service.unit_price * (reading.new - reading.old)

        if service.scope == 'selected_rooms':
            # Meter chung, chia theo số người
            total_consumption = get_shared_meter_reading(service, month)
            total_amount = service.unit_price * total_consumption

            all_persons = sum(
                count_active_persons(r, month)
                for r in service.applied_rooms
                if count_active_persons(r, month) > 0
            )

            if all_persons == 0:
                return 0  # Không chia được

            room_persons = count_active_persons(room, month)
            return total_amount * (room_persons / all_persons)
```

**Invoice snapshot pattern (detail Nhóm 7):**

```
InvoiceLineItem:
  id, invoice_id (FK),
  service_id (FK, để trace nhưng không dùng cho logic),
  service_name_snapshot (string),     -- copy tại thời điểm tạo
  billing_type_snapshot (enum),        -- copy
  unit_price_snapshot (decimal),       -- copy (quan trọng nhất)
  unit_snapshot (string),              -- copy
  quantity (decimal),                   -- số lượng (kWh, người, 1 cho fixed)
  amount (decimal)                      -- unit_price × quantity
```

Sẽ finalize ở Phase 3 (Architecture + Database Design).

---

## Summary

| Story  | Title                                       | Priority | Estimate |
| ------ | ------------------------------------------- | -------- | -------- |
| US-060 | Landlord tạo Service (all_rooms)            | Must     | L        |
| US-061 | Landlord tạo Service per_meter chia chung   | Should   | M        |
| US-062 | Landlord xem danh sách Service              | Must     | S        |
| US-063 | Landlord sửa Service                        | Must     | S        |
| US-064 | Landlord bật/tắt Service (toggle is_active) | Must     | S        |
| US-065 | Landlord xoá Service (chỉ khi chưa dùng)    | Could    | S        |
| US-066 | Tenant xem Service áp dụng cho phòng mình   | Must     | S        |

**Total**: 7 stories (5 Must + 1 Should + 1 Could).
**Estimate**: 1L + 1M + 5S ≈ 1.5 sprint.
