# User Stories — Nhóm 3: Tenant & Occupant

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-17
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **người sử dụng phòng**: Tenant (người đứng tên hợp đồng,
có tài khoản login) và Occupant (người ở cùng, không có account).

**Map với Vision:**

- MVP feature #3: Quản lý khách thuê theo phòng (CRUD, thông tin cơ bản,
  số lượng người, khách thuê đại diện)

**Key decisions (đã chốt):**

| #   | Decision                                             | Lý do                                 |
| --- | ---------------------------------------------------- | ------------------------------------- |
| 1   | Tách Tenant và Occupant thành 2 entity riêng         | Concept khác nhau: có/không account   |
| 2   | Tenant có tài khoản (User record), Occupant không có | Phù hợp invite flow ở US-004          |
| 3   | 1 Lease chỉ có 1 Tenant đại diện                     | Đơn giản MVP. Co-sign contract → v2.x |
| 4   | Tenant/Occupant soft delete (archive) khi dọn đi     | Bảo toàn audit trail, Invoice lịch sử |
| 5   | Tenant status auto-derive: `active` / `moved_out`    | Single Source of Truth từ Lease       |
| 6   | Tenant được tạo **trước khi** có Lease               | Landlord có thể nhập info rồi mới ký  |

## Personas liên quan

- **Landlord** (Persona A): CRUD Tenant + Occupant
- **Tenant** (Persona B): xem/sửa thông tin cá nhân của mình, xem Occupant

## Dependencies

- **Depends on**: Nhóm 1 (Auth — để invite Tenant), Nhóm 2 (Room — Tenant
  gắn với Room)
- **Blocks**: Nhóm 4 (Lease — Lease cần Tenant), Nhóm 6 (Invoice — Invoice
  gắn với Tenant)

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

### Concept: Tenant vs Occupant

|                   | Tenant                              | Occupant                        |
| ----------------- | ----------------------------------- | ------------------------------- |
| **Định nghĩa**    | Người ký hợp đồng, đứng tên pháp lý | Người ở cùng, không ký hợp đồng |
| **Có tài khoản?** | Có (User role=tenant)               | Không                           |
| **Số lượng/Room** | 1 per active Lease                  | 0–n, tuỳ Room                   |
| **Invite flow?**  | Có (US-004)                         | Không                           |
| **Thấy Invoice?** | Có                                  | Không (chỉ Tenant thấy)         |
| **Báo hỏng hóc?** | Có (v1.x)                           | Không                           |

**Ví dụ thực tế**: Phòng 101 có 3 người ở:

- Minh → **Tenant** (đứng tên, có app)
- Hùng (bạn Minh) → **Occupant**
- Lan (vợ Minh) → **Occupant**

### Tenant status (computed, không lưu DB)

| Status      | Khi nào                                                 |
| ----------- | ------------------------------------------------------- |
| `active`    | Đang có Lease không terminated gắn với Tenant           |
| `moved_out` | Đã có `archived_at`, tất cả Lease đã terminated/expired |
| `pending`   | Đã tạo record nhưng chưa ký Lease nào (vừa tạo)         |

---

## Stories

### US-030: Landlord tạo Tenant record

**As a** Landlord chuẩn bị cho 1 người thuê mới vào phòng
**I want to** tạo record Tenant với thông tin cơ bản
**So that** tôi có thể ký hợp đồng và mời họ vào app

**Priority**: Must
**Estimate**: M
**Depends on**: US-014 (Room phải tồn tại)

**Acceptance Criteria:**

- [ ] AC1: Form tạo Tenant có các trường:
  - `full_name` (bắt buộc, max 100 ký tự)
  - `phone` (bắt buộc, unique theo Landlord, định dạng VN)
  - `email` (tuỳ chọn, unique theo Landlord nếu có)
  - `id_card_number` (tuỳ chọn, max 12 ký tự) — CCCD/CMND
  - `birth_date` (tuỳ chọn)
  - `hometown` (tuỳ chọn, free text) — quê quán để đăng ký tạm trú
  - `note` (tuỳ chọn, free text max 500 ký tự)
- [ ] AC2: Phone unique **trong phạm vi Landlord** (1 Landlord không thể có
      2 Tenant cùng SĐT). Landlord khác có Tenant cùng SĐT → OK
- [ ] AC3: Email nếu có thì cũng unique **trong phạm vi Landlord**
- [ ] AC4: Tenant tạo xong có status `pending` (chưa gắn Lease)
- [ ] AC5: Tenant chưa có User account — account được tạo sau khi invite
      (US-005) chấp nhận
- [ ] AC6: Chỉ Landlord có quyền tạo Tenant cho Room trong Property của mình
- [ ] AC7: **Auto-suggest khi trùng phone**: khi Landlord nhập phone trùng
      với Tenant archived (cùng Landlord) → hiện dialog:
      _"SĐT này trùng với Tenant cũ [tên] (đã dọn đi [ngày]). Bạn muốn:_
      _[A] Kích hoạt lại và gán vào phòng mới_
      _[B] Tạo Tenant mới (trường hợp SĐT được cấp lại cho người khác)_
      _[C] Huỷ, nhập lại SĐT"_
- [ ] AC8: Nếu chọn [A] (kích hoạt lại) → `is_archived=false`, giữ nguyên
      `user_id` cũ (nếu có), invite token cũ đã expire sẽ không được tái sử dụng

**Notes:**

- SĐT/email unique trong **phạm vi Landlord + active**: constraint là
  `UNIQUE(landlord_id, phone) WHERE is_archived = false`. Tenant archived
  không tính vào unique check. Nhờ vậy Tenant cũ có thể cùng SĐT với
  Tenant mới không xung đột.
- Tenant chưa gắn với Room ở bước này. Việc gắn xảy ra khi tạo Lease
  (Nhóm 4). Điều này cho phép Landlord nhập info Tenant trước khi quyết
  định gán phòng nào.
- Alternative: Có thể bỏ bước "tạo Tenant độc lập", yêu cầu tạo Tenant
  ngay trong flow tạo Lease. MVP chọn cách linh hoạt hơn.
- Case Tenant quay lại thuê: AC7/AC8 giải quyết. Data lịch sử (Invoice cũ)
  vẫn gắn với Tenant cũ nếu kích hoạt lại — Tenant thấy được lịch sử
  thuê trước.

---

### US-031: Landlord xem danh sách và chi tiết Tenant

**As a** Landlord
**I want to** xem danh sách tất cả Tenant đang quản lý và chi tiết từng người
**So that** tôi có thể tra cứu nhanh khi cần

**Priority**: Must
**Estimate**: S
**Depends on**: US-030

**Acceptance Criteria:**

- [ ] AC1: Trang danh sách hiển thị: full_name, phone, Room đang ở (nếu có),
      status (active / moved_out / pending), invite status (chưa gửi /
      đã gửi / đã active)
- [ ] AC2: Mặc định chỉ hiện Tenant **chưa archived**. Có filter
      "Hiện Tenant đã dọn đi" để xem history
- [ ] AC3: Filter theo Property / Room / Status
- [ ] AC4: Tìm kiếm theo full_name hoặc phone (server-side với LIKE)
- [ ] AC5: Trang chi tiết hiển thị:
  - Thông tin cá nhân (tất cả field từ US-030)
  - Room hiện tại (nếu có), link sang trang Room
  - Lease hiện tại (nếu có), link sang Lease
  - Lịch sử Lease (các Lease cũ nếu có)
  - Danh sách Occupant (nếu có)
  - Invite status + nút "Mời/Gửi lại"
  - Lịch sử Invoice của Tenant (link)
- [ ] AC6: Chỉ Landlord sở hữu mới xem được Tenant của mình (RBAC)

---

### US-032: Landlord cập nhật thông tin Tenant

**As a** Landlord
**I want to** sửa thông tin Tenant khi thực tế thay đổi
**So that** dữ liệu luôn đúng (VD: Tenant đổi SĐT)

**Priority**: Must
**Estimate**: S
**Depends on**: US-030

**Acceptance Criteria:**

- [ ] AC1: Form sửa pre-fill data hiện tại, cho phép edit các trường từ US-030 AC1
- [ ] AC2: Validate unique phone/email như khi tạo mới (US-030 AC2, AC3)
- [ ] AC3: **Nếu đổi phone hoặc email** của Tenant có active invite token
      → invalidate token cũ, Landlord phải "Gửi lại" (logic US-004 AC6)
- [ ] AC4: Nếu Tenant đã có User account → sync email sang User record
      (để login bằng email mới)
- [ ] AC5: Chỉ Landlord sở hữu mới sửa được

**Notes:**

- AC3 đã xuất hiện ở US-004 AC6. Nhắc lại ở đây để đảm bảo behavior nhất quán.

---

### US-033: Landlord lưu trữ (archive) Tenant khi dọn đi

**As a** Landlord
**I want to** đánh dấu Tenant đã dọn đi
**So that** danh sách chính không bị lộn xộn, nhưng lịch sử vẫn xem được

**Priority**: Must
**Estimate**: M
**Depends on**: US-030

**Acceptance Criteria:**

- [ ] AC1: Có nút "Đã dọn đi" trên trang chi tiết Tenant
- [ ] AC2: **Chặn archive** nếu:
  - Tenant còn Lease active (phải terminate Lease trước — xem Nhóm 4)
  - Tenant còn Invoice `unpaid` hoặc `partial`
- [ ] AC3: Bị chặn → hiện dialog liệt kê cụ thể lý do
- [ ] AC4: Có thể archive → dialog nhập `move_out_date` (default today) +
      confirm
- [ ] AC5: Archive thành công:
  - Set `is_archived = true`
  - Set `archived_at = now()`
  - Set `move_out_date` theo input
  - Invalidate User account gắn với Tenant (không cho login nữa)
  - Ẩn khỏi danh sách chính
- [ ] AC6: Có filter "Hiện Tenant đã dọn đi" để xem archived list
- [ ] AC7: Có thể unarchive (khôi phục) nếu nhầm — `is_archived = false`,
      reactivate User account

**Notes:**

- AC5 invalidate User account: đây là security step quan trọng. Nếu Tenant
  dọn đi mà account vẫn login được → họ có thể xem Invoice/Lease cũ
  không còn thuộc phạm vi của mình. Tuỳ policy, v1.x có thể cho phép xem
  read-only history.
- Archive **không xoá** Lease/Invoice history — những cái đó gắn với
  Tenant record, tiếp tục tồn tại.

---

### US-034: Landlord thêm Occupant cho Tenant

**As a** Landlord
**I want to** ghi nhận những người ở cùng với Tenant đại diện
**So that** tôi biết chính xác bao nhiêu người ở trong phòng, phục vụ tính
dịch vụ theo đầu người và đăng ký tạm trú

**Priority**: Should
**Estimate**: M
**Depends on**: US-030

**Acceptance Criteria:**

- [ ] AC1: Trên trang chi tiết Tenant, có section "Người ở cùng" với nút
      "Thêm người ở cùng"
- [ ] AC2: Form Occupant đơn giản hơn Tenant:
  - `full_name` (bắt buộc)
  - `phone` (tuỳ chọn — có thể người ở cùng không có số riêng)
  - `id_card_number` (tuỳ chọn)
  - `relationship` (tuỳ chọn, VD: "bạn", "vợ", "con", "anh/em")
  - `moved_in_date` (bắt buộc, default = today) — ngày bắt đầu ở cùng
  - `note` (tuỳ chọn, free text)
- [ ] AC3: Validate: tổng số (Tenant + Occupants đang ở `moved_out_date IS NULL`)
      không được vượt quá `Room.max_occupants` (nếu có set)
- [ ] AC4: Nếu vi phạm AC3 → báo lỗi: "Phòng này giới hạn X người, hiện đã
      có Y người"
- [ ] AC5: Occupant **không có User account**, không invite, không login
- [ ] AC6: Số Occupant đếm được trong stats Tenant/Room
      (VD: "Phòng 101: 1 Tenant + 2 người ở cùng = 3 người")
- [ ] AC7: Chỉ Landlord sở hữu Property mới thao tác được

**Notes:**

- AC3 validate tổng **có tính cả Tenant**, không chỉ Occupants.
- Occupant đơn giản ở MVP vì chỉ để Landlord biết thông tin. Không có
  quyền hạn, không có action. v1.x có thể mở: Occupant báo hỏng hóc, xem
  hoá đơn... nhưng phải có User account riêng.
- `moved_in_date` và `moved_out_date` (xem US-035) được lưu ngay MVP dù
  MVP billing dùng **snapshot cuối tháng** (đếm người active cuối tháng).
  v1.x upgrade sang **pro-rata** (tính theo số ngày ở thực tế) mà không
  cần migrate schema.
- AC7 per_person snapshot: MVP lấy **số người tại thời điểm tạo Invoice**
  (không phải cuối tháng). Lý do: Invoice thường xuất đầu tháng, lúc đó
  chưa biết Occupant sẽ đổi thế nào cuối tháng. Chấp nhận sai số nhỏ nếu
  Occupant đổi giữa tháng. v1.x pro-rata theo moved_in/moved_out_date.

---

### US-035: Landlord cập nhật hoặc đánh dấu Occupant dọn đi

**As a** Landlord
**I want to** cập nhật thông tin Occupant hoặc đánh dấu họ đã dọn đi
**So that** số lượng người ở cùng luôn chính xác, và Invoice tháng sau
không còn tính phí cho người đã đi

**Priority**: Should
**Estimate**: S
**Depends on**: US-034

**Acceptance Criteria:**

- [ ] AC1: Trên danh sách Occupant có nút "Sửa" / "Đánh dấu dọn đi" cho mỗi người
- [ ] AC2: **Sửa**: form pre-fill data hiện tại, validate như tạo mới
      (không cho sửa `moved_in_date` nếu đã có Invoice tính trên ngày này)
- [ ] AC3: **Đánh dấu dọn đi** (soft): set `moved_out_date = today` (hoặc
      Landlord chọn date khác). Occupant không hiện trong danh sách active
      nhưng vẫn lưu DB.
- [ ] AC4: **Xoá thật (hard delete)** chỉ cho phép khi Occupant có
      `moved_in_date = today` và chưa có Invoice nào tính qua ngày đó
      (trường hợp nhập nhầm, chưa có hệ quả)
- [ ] AC5: Có filter "Hiện người đã dọn đi" trên danh sách Occupant
- [ ] AC6: Confirm dialog khi đánh dấu dọn đi: "Xác nhận [tên] đã dọn đi
      ngày [date]? Hoá đơn sau ngày này sẽ không tính [tên] nữa."
- [ ] AC7: Có thể "undo" (xoá `moved_out_date`) trong 7 ngày nếu nhập sai

**Notes:**

- Thay đổi từ MVP đầu (hard delete) sang **soft delete** vì cần lưu
  timeline cho billing. Lý do: nếu xoá Occupant thật, Invoice tháng trước
  đã tính dịch vụ per_person cho người đó sẽ mất reference → sai audit.
- AC4 hard delete chỉ cho case nhập nhầm, chưa có hệ quả billing.
- v1.x pro-rata sẽ dùng `moved_in_date` và `moved_out_date` để tính
  chính xác theo số ngày ở.

---

### US-036: Landlord đổi Tenant đại diện (promote Occupant lên Tenant)

**As a** Landlord khi Tenant đại diện dọn đi nhưng Occupant muốn ở lại
**I want to** chuyển 1 Occupant thành Tenant đại diện mới
**So that** phòng không bị trống, không phải ký lại từ đầu, flow liền mạch

**Priority**: Must
**Estimate**: L
**Depends on**: US-030, US-034, Nhóm 4 (Lease)

**Context (thực tế VN):**

Phòng 101 có Tenant "Minh" + Occupant "Lan" (vợ Minh). Minh dọn đi,
Lan ở lại. Landlord cần:

- Chấm dứt Lease với Minh
- Lan trở thành người đại diện mới
- Ký Lease mới với Lan
- Lan được mời vào app

**Acceptance Criteria:**

- [ ] AC1: Trên mỗi Occupant, có nút "Đổi làm đại diện"
- [ ] AC2: Click → hiện wizard 3 bước:
  - Step 1: Chọn lý do và ngày hiệu lực
    (VD: "Tenant đại diện dọn đi", `effective_date = today`)
  - Step 2: Review: hiển thị action sẽ thực hiện
    - Terminate Lease hiện tại của Tenant cũ (ngày = effective_date)
    - Archive Tenant cũ (nếu không còn Lease active khác)
    - Copy data Occupant → tạo Tenant mới (name, phone, id_card, relationship
      → không copy vì Occupant relationship dành cho Tenant cũ)
    - Tạo Lease mới với Tenant mới (Landlord nhập: start_date, end_date, rent,
      deposit — mặc định copy từ Lease cũ)
    - Xoá Occupant record cũ (vì đã "lên chức" Tenant)
  - Step 3: Confirm + invite mới cho Tenant mới (flow US-004)
- [ ] AC3: Validation trước khi thực hiện:
  - Tenant cũ **không còn Invoice unpaid** → cảnh báo, nhưng vẫn cho
    tiếp tục (nợ cũ vẫn thuộc Tenant cũ, không chuyển sang người mới)
  - Occupant được chọn **chưa có Tenant record riêng** (trường hợp edge
    case: Landlord đã tạo Tenant khác cho Occupant này ở nhà khác)
- [ ] AC4: **Deposit xử lý**:
  - Deposit cũ vẫn thuộc về Tenant cũ (họ có quyền đòi lại)
  - Lease mới có thể nhập deposit mới hoặc 0
  - Landlord tự thoả thuận với tenant ngoài app về chuyển deposit
  - App chỉ ghi nhận trạng thái, không xử lý tiền (MVP scope)
- [ ] AC5: Nếu thực hiện thành công → log operation vào audit trail
      (v1.x có UI xem, MVP chỉ log DB)
- [ ] AC6: Transaction: tất cả thay đổi trong 1 DB transaction, rollback
      nếu có lỗi ở bất kỳ bước nào

**Notes:**

- Đây là **case phức tạp nhất** trong MVP Tenant management, đáng estimate L.
- v1.x có thể mở rộng:
  - Chuyển deposit tự động nếu Landlord confirm
  - Gửi notification tự động cho cả Tenant cũ + mới
  - Cho Tenant cũ + mới chat/xác nhận giao dịch
- Flow này **chỉ áp dụng khi đổi người đại diện**. Trường hợp 1 Tenant
  dọn đi hoàn toàn (không ai ở lại) → dùng flow thường: terminate Lease
  (Nhóm 4) + archive Tenant (US-033).

---

### US-036b: Tenant status auto-transition (cron daily)

**As a** hệ thống (cron job)
**I want to** kiểm tra Tenant status mỗi ngày để trigger notifications
**So that** Landlord được cảnh báo khi Tenant status đổi (VD: Lease expire)

**Priority**: Must
**Estimate**: S (leverage cron đã có ở Nhóm 4 US-057)
**Depends on**: US-030, Nhóm 4 US-057

**Acceptance Criteria:**

- [ ] AC1: Chạy **chung cron với Nhóm 4 US-057** (00:05 daily), không phải
      cron riêng
- [ ] AC2: Logic (pseudo-code):
  ```
  FOR each Tenant WHERE is_archived = false:
    IF count(active Leases of tenant) > 0: status = 'active'
    ELSE IF exists terminated/expired Leases: status = 'moved_out'  -- edge case
    ELSE: status = 'pending'  -- chưa có Lease nào
  ```
- [ ] AC3: Tenant.status là **computed**, không UPDATE DB. Cron chỉ để
      trigger notifications khi status đổi (v1.x)
- [ ] AC4: Side effects MVP: cập nhật dashboard widget (US-058 kiểu) nếu có
- [ ] AC5: Cron idempotent

**Notes:**

- Story này nhỏ vì logic chính đã ở Nhóm 4 US-057. Chỉ là 1 task thêm vào
  cùng cron.
- MVP notification chưa có → task này gần như no-op. Giữ để v1.x plug.

---

### US-037: Tenant xem và sửa thông tin cá nhân của mình

**As a** Tenant đã login
**I want to** xem và sửa thông tin cá nhân (phone, email, ...) của chính tôi
**So that** Landlord có thông tin chính xác khi cần liên lạc

**Priority**: Should
**Estimate**: M
**Depends on**: US-005 (Tenant login), US-030

**Acceptance Criteria:**

- [ ] AC1: Trang "Tài khoản" / "Hồ sơ" của Tenant hiển thị thông tin cá nhân
- [ ] AC2: Tenant có thể **sửa**:
  - `full_name`
  - `phone` (nhưng phải re-verify — xem AC5)
  - `birth_date`
  - `hometown`
  - Password (qua flow change password riêng — v1.x)
- [ ] AC3: Tenant **không thể sửa**:
  - `email` (vì gắn với User.email, đổi email = đổi login)
  - `id_card_number` (chỉ Landlord sửa được, vì có giá trị pháp lý)
  - `note` của Landlord ghi về mình
- [ ] AC4: Sau khi sửa → Landlord **được thông báo** (v1.x) hoặc thấy thay
      đổi lần tới vào app
- [ ] AC5: Đổi phone → gửi OTP về phone cũ + mới để verify (v1.x, MVP skip
      và cho update trực tiếp)

**Notes:**

- AC3: email read-only ở MVP là **đơn giản hóa**. v1.x thêm flow đổi email
  (gửi confirm link về email mới).
- AC5: OTP skip ở MVP vì chưa tích hợp SMS. Chấp nhận risk nhỏ: Tenant
  đổi phone sai chính tả → không ảnh hưởng login (email là primary).

---

### US-038: Tenant xem danh sách Occupant của mình

**As a** Tenant
**I want to** xem những người ở cùng mà Landlord đã ghi nhận
**So that** tôi biết record của Landlord có đúng với thực tế không, liên hệ
Landlord nếu có sai sót

**Priority**: Should
**Estimate**: S
**Depends on**: US-034, US-037

**Acceptance Criteria:**

- [ ] AC1: Trong trang "Hồ sơ" của Tenant, có section "Người ở cùng"
- [ ] AC2: Hiển thị danh sách Occupant do Landlord tạo (read-only):
      full_name, relationship, moved_in_date
- [ ] AC3: Tenant **không sửa/xoá/thêm** được Occupant (chỉ Landlord làm)
- [ ] AC4: Nếu muốn thay đổi → Tenant phải liên hệ Landlord (hiển thị SĐT
      Landlord)

**Notes:**

- Upgrade từ `Could` lên `Should` (2026-04-17) vì effort thấp mà giá trị
  minh bạch rõ — giảm nhầm lẫn giữa Landlord và Tenant về số người ở cùng.
- v1.x có thể cho Tenant "đề xuất" thêm Occupant → Landlord approve.

---

## Open Questions (cần trả lời trước khi vào Phase 3)

1. **Co-sign contract** (2 người cùng đứng tên hợp đồng, cùng chịu trách
   nhiệm pháp lý) — MVP không, v2.x. Case thực tế: cặp vợ chồng đều muốn
   đứng tên.
2. **Tenant có thể self-update avatar/photo?** — MVP skip, v1.x.
3. **Bulk import Tenant từ Excel?** — Bảo có 50 Tenant đang quản lý bằng
   Excel, nhập tay từng người sẽ mệt. MVP làm tay, v1.x có thể add import CSV.
4. **Giới hạn số Tenant/Landlord?** — MVP unlimited, monitor sau.
5. **Billing logic khi Occupant thay đổi giữa tháng**: MVP chọn **snapshot
   cuối tháng** (đếm người active cuối tháng), v1.x upgrade **pro-rata**
   theo `moved_in_date` / `moved_out_date`. Cần confirm với Bảo ở Nhóm 7
   (Invoice).

## Data Retention Policy (draft)

Theo Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân, RMS phải có policy
rõ ràng về việc lưu trữ và xoá thông tin Tenant.

**Draft policy cho MVP:**

| Data                               | Retention                              | Khi nào xoá                                |
| ---------------------------------- | -------------------------------------- | ------------------------------------------ |
| Tenant name, phone, email (active) | Chừng nào còn Lease hoặc chưa archived | N/A                                        |
| Tenant archived (đầy đủ PII)       | 5 năm sau `move_out_date`              | Job auto chạy mỗi tháng                    |
| Tenant archived (sau 5 năm)        | Anonymize (xoá PII, giữ ID)            | Giữ vĩnh viễn để Invoice history không mất |
| Occupant archived                  | Giữ cùng vòng đời với Tenant cha       | Xoá khi Tenant cha anonymize               |
| Invoice, Payment, Lease            | 10 năm (theo Luật Kế toán VN)          | Chưa xử lý ở MVP                           |

**User consent (thêm vào flow accept invite — US-005):**

Khi Tenant set password và accept invite, có checkbox bắt buộc:

> _"Tôi đồng ý với việc RMS lưu trữ thông tin cá nhân của tôi trong thời
> gian thuê phòng và 5 năm sau khi chấm dứt hợp đồng cho mục đích pháp lý
> và lưu trữ tài chính, theo Nghị định 13/2023/NĐ-CP."_

**Right to Erasure:**

- MVP: không implement (Tenant muốn xoá → gọi Landlord → Landlord email admin)
- v2.x: Tenant có nút "Yêu cầu xoá dữ liệu" → hệ thống anonymize PII, giữ
  record với pseudonym để Invoice history không mất reference

**Cảnh báo**: Policy này là **draft**, chưa review pháp lý. Trước khi go
production với user thật → consult luật sư Việt Nam để đảm bảo đúng luật.

## Ghi chú kiến trúc cho Phase 3

**Entity Relationships (preview):**

```
User (role=tenant) 1──1 Tenant  (User chỉ tạo sau khi invite accept)
Tenant             1──* Occupant
Tenant             1──* Lease  (lịch sử Lease của 1 Tenant)
Tenant             0──1 current_lease  (computed: Lease không terminated)
Room               1──* Tenant  (qua Lease, không trực tiếp)
```

**Trường DB dự kiến:**

```
Tenant:
  id, landlord_id (FK → User role=landlord),
  user_id (FK → User role=tenant, nullable — null khi chưa invite accept),
  full_name, phone, email, id_card_number, birth_date, hometown, note,
  is_archived, archived_at, move_out_date,
  created_at, updated_at
  UNIQUE(landlord_id, phone)
  UNIQUE(landlord_id, email) WHERE email IS NOT NULL

Occupant:
  id, tenant_id (FK), full_name, phone, id_card_number, relationship, note,
  created_at, updated_at
```

Sẽ finalize ở Phase 3 (Architecture + Database Design).
