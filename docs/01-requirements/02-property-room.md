# User Stories — Nhóm 2: Property & Room

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-17
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **đơn vị quản lý vật lý** của RMS: Nhà (Property) chứa
nhiều Phòng (Room). Đây là **root container** của mọi data khác
(Tenant, Lease, Invoice đều gắn về Room → Property).

**Map với Vision:**

- MVP feature #1: Quản lý nhà (CRUD)
- MVP feature #2: Quản lý phòng theo nhà (CRUD, trạng thái)

**Key decisions (đã chốt):**

| #   | Decision                                                        | Lý do                                         |
| --- | --------------------------------------------------------------- | --------------------------------------------- |
| 1   | 1 Property có đúng 1 `landlord_id` (NOT NULL)                   | MVP không tách chủ/quản lý, v2.x thêm Manager |
| 2   | Room có `display_name` free text + `floor` optional             | Linh hoạt với đủ kiểu đánh số thực tế VN      |
| 3   | Room status auto-derive từ Lease (4 trạng thái)                 | Single source of truth, không lệch dữ liệu    |
| 4   | Asset → ghi `description` free text (MVP)                       | Entity Asset riêng ở v1.x                     |
| 5   | Property: hard delete khi hết Room. Room: soft delete (archive) | Bảo toàn dữ liệu tài chính                    |
| 6   | Service config ở Property level, Room kế thừa                   | Chi tiết ở Nhóm 5 (Service)                   |
| 7   | Shared meter giữa nhiều Room: chia đều (MVP), chia tỷ lệ v1.x   | Chi tiết ở Nhóm 5 (Service)                   |

## Personas liên quan

- **Landlord** (Persona A): primary actor, CRUD mọi thứ
- **Tenant** (Persona B): chỉ xem thông tin phòng mình thuê (read-only)

## Changelog

- **2026-04-17 v0.2**: Fix US-017 — tách rõ Lease active (end_date còn valid)
  vs expired. Thêm cron job daily để chuyển Lease status. Giải quyết mâu
  thuẫn "active Lease nhưng hết hạn".
- **2026-04-17 v0.1**: Draft đầu tiên với 9 stories.

## Dependencies

- **Depends on**: Nhóm 1 (Auth & RBAC) — phải login và có role Landlord
- **Blocks**: Nhóm 3 (Tenant & Lease), Nhóm 5 (Service), Nhóm 6 (Invoice)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

### Room status enum (MVP)

Room.status **derive 1-1 từ Lease.status** (xem Nhóm 4 — Lease Lifecycle).
Không tính lại từ `end_date` để tránh mâu thuẫn giữa 2 enum.

| Room.status     | Khi nào                                                 | Derive từ Lease.status của Lease non-terminal trên Room |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| `vacant`        | Room không có Lease nào, hoặc chỉ có Lease `terminated` | Không có Lease non-terminal                             |
| `occupied`      | Đang cho thuê bình thường                               | Lease.status = `active`                                 |
| `expiring_soon` | Đang cho thuê, sắp hết hạn                              | Lease.status = `expiring_soon`                          |
| `lease_expired` | Hợp đồng hết hạn, Tenant có thể còn ở, chưa xử lý       | Lease.status = `expired`                                |

**Lưu ý naming**: Room dùng `lease_expired` (rõ context "hợp đồng trên phòng đã hết")
trong khi Lease dùng `expired` (rõ context "hợp đồng này đã hết"). Đây là
chủ ý — 2 context khác nhau nên dùng 2 tên khác nhau, nhưng map 1-1.

**Quan trọng**: Room.status là **computed field**, không lưu vào DB.
Tránh bug "status lệch data thật".

**Room.status ứng với Lease.status = `draft`**: Room vẫn `vacant` (Lease
chưa hiệu lực). Xem Nhóm 4 US-050 AC5.

---

## Stories

### US-010: Landlord tạo và xem danh sách nhà trọ

**As a** Landlord
**I want to** tạo nhà trọ mới và xem danh sách các nhà đang quản lý
**So that** tôi có thể tổ chức các điểm cho thuê trong hệ thống

**Priority**: Must
**Estimate**: M
**Depends on**: US-001 (Landlord đăng ký)

**Acceptance Criteria:**

- [ ] AC1: Form tạo Property có các trường:
  - `name` (bắt buộc, max 100 ký tự) — VD: "Nhà trọ 123 Trần Hưng Đạo"
  - `address` (bắt buộc, max 255 ký tự)
  - `description` (tuỳ chọn, free text, max 1000 ký tự)
- [ ] AC2: Property tạo thành công → gán `landlord_id = current_user.id`
- [ ] AC3: Trang danh sách hiển thị cards/rows với: tên nhà, địa chỉ,
      số phòng tổng, số phòng trống, số phòng sắp hết hạn
- [ ] AC4: Landlord chỉ thấy Property **do chính mình tạo** (RBAC từ US-009)
- [ ] AC5: Danh sách sort theo `created_at DESC` mặc định (mới nhất trên đầu)
- [ ] AC6: Có tìm kiếm theo tên (client-side với MVP, server-side v1.x)
- [ ] AC7: Click vào 1 Property → điều hướng sang trang chi tiết (danh sách Room)

**Notes:**

- MVP chưa cần pagination (giả định 1 Landlord có < 20 nhà)
- Thống kê AC3 (số phòng trống...) compute từ Room data

---

### US-011: Landlord xem chi tiết nhà trọ

**As a** Landlord
**I want to** xem thông tin chi tiết của 1 nhà trọ cùng danh sách phòng trong đó
**So that** tôi có thể nắm tình trạng tổng thể của nhà này

**Priority**: Must
**Estimate**: S
**Depends on**: US-010

**Acceptance Criteria:**

- [ ] AC1: Trang chi tiết Property hiển thị:
  - Thông tin cơ bản: tên, địa chỉ, description
  - Thống kê nhanh: tổng phòng, đang thuê, trống, sắp hết hạn, hết hạn
  - Danh sách Room với: display_name, tầng, diện tích, giá thuê, status (badge màu)
- [ ] AC2: Badge trạng thái dùng màu phân biệt:
  - `vacant`: xám
  - `occupied`: xanh lá
  - `expiring_soon`: vàng
  - `lease_expired`: đỏ
- [ ] AC3: Có filter Room theo status (checkbox: Trống / Đang thuê / Sắp hết / Hết hạn)
- [ ] AC4: Có sort Room theo: display_name (A→Z), giá thuê, status
- [ ] AC5: Nếu Property không thuộc Landlord đang login → trả 403
- [ ] AC6: Nếu Property không tồn tại hoặc đã bị xoá → trả 404

---

### US-012: Landlord cập nhật thông tin nhà trọ

**As a** Landlord
**I want to** sửa tên, địa chỉ, mô tả của nhà trọ
**So that** thông tin luôn chính xác khi thực tế thay đổi

**Priority**: Must
**Estimate**: S
**Depends on**: US-010

**Acceptance Criteria:**

- [ ] AC1: Có nút "Sửa" trên trang chi tiết Property
- [ ] AC2: Form sửa pre-fill với data hiện tại, cho phép edit các trường
      như US-010 AC1
- [ ] AC3: Validate như tạo mới (bắt buộc, max length)
- [ ] AC4: Chỉ Landlord sở hữu Property mới được sửa (RBAC)
- [ ] AC5: Lưu thành công → refresh trang chi tiết với data mới
- [ ] AC6: Không ảnh hưởng đến Room, Lease, Invoice hiện có

---

### US-013: Landlord xoá nhà trọ

**As a** Landlord
**I want to** xoá nhà trọ không còn quản lý
**So that** danh sách của tôi gọn gàng, không nhầm lẫn

**Priority**: Must
**Estimate**: S
**Depends on**: US-010

**Acceptance Criteria:**

- [ ] AC1: Có nút "Xoá nhà trọ" trên trang chi tiết Property
- [ ] AC2: **Chặn xoá** nếu Property còn chứa bất kỳ Room nào (kể cả Room archived)
- [ ] AC3: Nếu bị chặn → dialog báo: "Nhà trọ đang có X phòng. Vui lòng xoá
      hoặc lưu trữ các phòng trước."
- [ ] AC4: Nếu không còn Room → dialog confirm: "Bạn chắc chắn muốn xoá nhà
      trọ này? Hành động không thể hoàn tác."
- [ ] AC5: Xác nhận xoá → hard delete Property trong DB
- [ ] AC6: Chỉ Landlord sở hữu Property mới được xoá (RBAC)

**Notes:**

- Hard delete được phép vì Property không có **dữ liệu tài chính trực tiếp**
  (Invoice gắn với Room, không gắn trực tiếp với Property).
- Nếu v2.x có Investor (Property có thể có nhiều bên liên quan), cần review
  lại policy này.

---

### US-014: Landlord tạo phòng trong nhà trọ

**As a** Landlord
**I want to** thêm phòng vào nhà trọ của mình
**So that** tôi có thể bắt đầu quản lý việc cho thuê từng phòng

**Priority**: Must
**Estimate**: M
**Depends on**: US-010

**Acceptance Criteria:**

- [ ] AC1: Từ trang chi tiết Property, có nút "Thêm phòng"
- [ ] AC2: Form tạo Room có các trường:
  - `display_name` (bắt buộc, max 50 ký tự) — VD: "101", "A1", "G-01"
  - `floor` (tuỳ chọn, int) — dùng để filter/sort
  - `area_m2` (tuỳ chọn, decimal ≥ 0) — diện tích phòng
  - `monthly_rent` (bắt buộc, int ≥ 0) — giá thuê VND/tháng
  - `max_occupants` (tuỳ chọn, int ≥ 1) — số người tối đa được ở
  - `description` (tuỳ chọn, free text max 1000 ký tự) — ghi chú tài sản,
    tiện nghi, lưu ý
- [ ] AC3: `display_name` phải **unique trong 1 Property**
      (2 phòng cùng nhà không được cùng tên)
- [ ] AC4: Sai unique → báo "Tên phòng đã tồn tại trong nhà này"
- [ ] AC5: Room mới tạo mặc định `status = vacant`, `is_archived = false`
- [ ] AC6: Chỉ Landlord sở hữu Property mới được thêm Room (RBAC)

**Notes:**

- `description` là nơi Landlord ghi tài sản trong phòng cho MVP
  ("Có máy lạnh, giường, tủ lạnh"). v1.x sẽ tách Asset entity riêng.
- `max_occupants` dùng sau khi có Tenant management (để validate số người
  không vượt quá giới hạn).

---

### US-015: Landlord xem chi tiết và cập nhật phòng

**As a** Landlord
**I want to** xem và sửa thông tin 1 phòng
**So that** dữ liệu phản ánh đúng thực tế khi có thay đổi (giá thuê, diện tích...)

**Priority**: Must
**Estimate**: S
**Depends on**: US-014

**Acceptance Criteria:**

- [ ] AC1: Trang chi tiết Room hiển thị:
  - Tất cả field đã nhập ở US-014
  - Status hiện tại (badge màu)
  - Tenant đang thuê (nếu có) — link sang Nhóm 3
  - Lease hiện tại (nếu có) — link sang Nhóm 3
  - Lịch sử meter reading gần đây (nếu có) — link sang Nhóm 5
- [ ] AC2: Có nút "Sửa" mở form edit với data pre-filled
- [ ] AC3: Validate giống tạo mới (US-014 AC2, AC3)
- [ ] AC4: **Cảnh báo** (không chặn) nếu Landlord đổi `monthly_rent` khi
      Room đang có Lease active: "Lease hiện tại vẫn áp dụng giá cũ.
      Giá mới sẽ áp dụng cho Lease tiếp theo."
- [ ] AC5: Không được đổi `property_id` (di chuyển phòng sang nhà khác) ở MVP
- [ ] AC6: Chỉ Landlord sở hữu mới sửa được (RBAC)

**Notes:**

- AC4 phản ánh nguyên tắc: **Lease = snapshot contract**, giá thuê đã ký
  thì giữ nguyên đến hết hạn. Đổi giá phòng không retroactive áp dụng.

---

### US-016: Landlord lưu trữ (archive) phòng

**As a** Landlord
**I want to** "archive" phòng không còn cho thuê thay vì xoá thật
**So that** lịch sử Lease/Invoice cũ vẫn tra cứu được khi cần

**Priority**: Must
**Estimate**: M
**Depends on**: US-014

**Acceptance Criteria:**

- [ ] AC1: Có nút "Lưu trữ" trên trang chi tiết Room (thay vì "Xoá")
- [ ] AC2: **Chặn archive** nếu:
  - Room có Lease active (phải terminate Lease trước)
  - Room có Invoice `unpaid` hoặc `partial`
- [ ] AC3: Bị chặn → hiện dialog liệt kê lý do cụ thể
      (VD: "Còn 2 hoá đơn chưa thanh toán, còn 1 hợp đồng đang hiệu lực")
- [ ] AC4: Có thể archive → confirm dialog "Phòng sẽ không hiện trong danh
      sách chính, nhưng lịch sử vẫn xem được. Có thể hoàn tác bất kỳ lúc nào."
- [ ] AC5: Archive thành công → set `is_archived = true`, ẩn khỏi danh sách
      Room mặc định của Property
- [ ] AC6: Có filter "Hiện phòng đã lưu trữ" trên trang chi tiết Property
      để xem Room archived
- [ ] AC7: Có nút "Khôi phục" trên Room archived → set `is_archived = false`

**Notes:**

- Soft delete pattern quan trọng vì dữ liệu tài chính (Invoice, Payment)
  phải audit được. Dù Room "biến mất" khỏi UI, Invoice cũ vẫn phải xem được.
- Không có "hard delete" Room ở MVP. Nếu cần xoá thật (nhập nhầm) → v1.x
  cân nhắc, nhưng phải check không có bất kỳ Lease/Invoice nào từng tồn tại.

---

### US-017: Hệ thống tự động tính Room status

**As a** hệ thống RMS
**I want to** tự động xác định status của mỗi Room dựa vào Lease data
**So that** Landlord luôn thấy trạng thái chính xác, không phải update thủ công

**Priority**: Must
**Estimate**: M
**Depends on**: US-014, Nhóm 4 (Lease)

**Acceptance Criteria:**

- [ ] AC1: Status được **tính khi query** (computed field), không lưu DB
- [ ] AC2: Logic derive — **map 1-1 từ Lease.status** (Lease non-terminal
      là Lease có `terminated_at IS NULL`):

  ```
  Nếu Room không có Lease non-terminal nào → 'vacant'

  Nếu Room có Lease non-terminal:
  Lease.status = 'draft'          → Room.status = 'vacant'
  Lease.status = 'active'         → Room.status = 'occupied'
  Lease.status = 'expiring_soon'  → Room.status = 'expiring_soon'
  Lease.status = 'expired'        → Room.status = 'lease_expired'

  Lease.status = 'terminated' không còn là "non-terminal" → không xét.
  ```

**Trong đó Lease.status được tính theo công thức ở Nhóm 4** (Lease Lifecycle).
Room.status **không được tính riêng từ end_date** — phải đi qua Lease.status
để tránh lệch giữa 2 nhóm.

- [ ] AC3: Business rule: mỗi Room chỉ có **1 Lease không terminated** tại
      một thời điểm. Nếu data có > 1 (do lỗi) → log warning, lấy Lease có
      `end_date` xa nhất làm Lease hiện tại
- [ ] AC4: Khi tạo/gia hạn/chấm dứt Lease → status Room tự cập nhật ngay
      (không cần action riêng vì computed)
- [ ] AC5: Lease.status là **computed**, không cần cron UPDATE. Cron daily
      chỉ để trigger notifications khi status đổi (xem Nhóm 4 US-057).
      Room.status cũng computed theo mỗi query, không cron riêng.
- [ ] AC6: Room ở status `lease_expired` vẫn được phép tạo Invoice tháng
      tiếp theo, nhưng UI phải hiện cảnh báo đỏ: "Hợp đồng đã hết hạn từ
      ngày X. Cân nhắc gia hạn hoặc chấm dứt."

**Notes:**

- **2 concept khác nhau nhưng map 1-1**: `Lease.status` (góc nhìn hợp đồng)
  và `Room.status` (góc nhìn phòng). Cả 2 đều **computed**, không lưu DB.
  Room.status query qua Lease.status, không tính riêng.
- Naming khác nhau có chủ ý: Room dùng `lease_expired`, Lease dùng `expired`.
  Lý do: đọc "Room.lease_expired" rõ ngay là "hợp đồng trên phòng này đã hết",
  còn "Lease.expired" là "hợp đồng này đã hết" — mỗi context dùng tên phù hợp.
- AC6 đáp ứng thực tế VN: Lease hết hạn nhưng tenant vẫn ở, tiếp tục trả tiền.
  Hệ thống không được **chặn** Landlord, chỉ **cảnh báo**.

---

### US-018: Tenant xem thông tin phòng mình thuê

**As a** Tenant đã login
**I want to** xem thông tin phòng mình đang thuê
**So that** tôi biết rõ giá thuê, diện tích, thông tin nhà mình đang ở

**Priority**: Must
**Estimate**: S
**Depends on**: US-005 (Tenant kích hoạt account), US-014

**Acceptance Criteria:**

- [ ] AC1: Sau khi Tenant login → dashboard hiển thị thẻ "Phòng của tôi"
- [ ] AC2: Thông tin hiển thị:
  - Tên phòng, tầng, diện tích
  - Giá thuê/tháng (theo Lease hiện tại, không phải theo Room.monthly_rent)
  - Tên + địa chỉ Property
  - Description (tiện nghi, tài sản)
  - Status Lease (còn bao nhiêu ngày)
- [ ] AC3: Tenant **không thấy** thông tin Landlord đầy đủ (chỉ tên + SĐT)
- [ ] AC4: Tenant **không thấy** các Room khác trong cùng Property
- [ ] AC5: Read-only: Tenant không có nút sửa bất kỳ field nào
- [ ] AC6: Nếu Tenant chưa có Lease nào → hiện: "Chưa có phòng được gán.
      Vui lòng liên hệ Landlord."

**Notes:**

- AC2 dùng giá từ Lease vì giá đã ký với Tenant là cố định, không đổi theo
  `Room.monthly_rent` nếu Landlord cập nhật.
- AC3, AC4 là privacy: Tenant không cần biết Landlord sở hữu mấy nhà,
  Tenant khác là ai.

---

## Open Questions (cần trả lời trước khi vào Phase 3)

1. **Room có photos không?** — MVP có lẽ skip (chỉ description). v1.x thêm.
2. **Giới hạn số Property/Room mỗi Landlord?** — Có cần quota không? MVP
   có thể unlimited, monitor sau.
3. **Bulk create Room?** — Landlord có 50 phòng, tạo từng cái mỗi lần sẽ mệt.
   MVP làm thủ công, v1.x có thể import CSV hoặc "Tạo nhanh 10 phòng giống nhau".
4. **Property có sub-property không?** (nhà phân nhiều tầng, mỗi tầng là một
   "sub-property") — MVP không, v2.x cân nhắc nếu có user thật yêu cầu.
5. **Landlord có thể chuyển ownership Property cho Landlord khác không?**
   — MVP không. v2.x liên quan Manager/Investor.

## Mapping sang Functional Requirements (sẽ viết ở file tổng hợp sau)

```
FR-PROP-001: Property.landlord_id là FK sang User, NOT NULL
FR-PROP-002: Property xoá được CHỈ KHI không còn Room liên kết
FR-ROOM-001: Room.display_name unique trong scope property_id
FR-ROOM-002: Room status là computed field, không lưu DB
FR-ROOM-003: Room archive (soft delete) bảo toàn Lease/Invoice lịch sử
...
```

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships (preview):**

```
User (Landlord) 1──* Property
Property         1──* Room
Room             1──* Lease  (nhiều Lease theo thời gian, chỉ 1 active)
Room             0──1 current_lease  (computed)
Room             *──* SharedMeter  (v1.x, nhóm Service sẽ bàn)
```

**Trường DB dự kiến:**

```
Property:
  id, landlord_id (FK), name, address, description,
  created_at, updated_at

Room:
  id, property_id (FK), display_name, floor, area_m2,
  monthly_rent, max_occupants, description, is_archived,
  created_at, updated_at
  UNIQUE(property_id, display_name)
```

Sẽ finalize ở Phase 3 (Architecture + Database Design).
