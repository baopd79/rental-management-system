# Phase 2 Review — Detailed Patches

> **Purpose**: Apply these patches to resolve issues identified in `PHASE2-REVIEW.md`.
> **Target executor**: Claude Code in VS Code
> **Scope**: C1, C2 (Critical) + S1-S5 (Should fix) + glossary + CHANGELOG
> **Date**: 2026-04-18

---

## How to Use This File

Each patch below has:

- **File**: exact path to modify
- **Section**: location in file
- **OLD**: exact text to find (use for `str_replace`)
- **NEW**: exact text to replace with
- **Rationale**: why (for reviewer understanding)
- **Verification**: how to confirm patch applied correctly

**Recommended workflow:**

```
1. Apply patches in order (P1 → P12)
2. After each patch, run git diff to verify
3. Do NOT commit until all patches reviewed
4. Final commit message:
   fix(requirements): resolve PHASE2 review issues (C1, C2, S1-S5)
```

**Total patches**: 12

---

## Patch P1: Fix C1 — Room.status derives from Lease.status

**File**: `docs/01-requirements/02-property-room.md`
**Section**: Room status enum table + US-017 AC2

### P1.1 — Update Room status enum table

**OLD:**

```markdown
### Room status enum (MVP)

| Status          | Khi nào                                         | Derive từ                                 |
| --------------- | ----------------------------------------------- | ----------------------------------------- |
| `vacant`        | Chưa có Lease active                            | Không có Lease nào `status=active`        |
| `occupied`      | Đang cho thuê, còn > 30 ngày                    | Lease active, `end_date - today > 30`     |
| `expiring_soon` | Đang cho thuê, còn ≤ 30 ngày                    | Lease active, `0 ≤ end_date - today ≤ 30` |
| `lease_expired` | Lease hết hạn, chưa xử lý (tenant có thể còn ở) | Lease active, `end_date - today < 0`      |

**Quan trọng**: Status là **computed field**, không lưu vào DB.
Tránh bug "status lệch data thật".
```

**NEW:**

```markdown
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
```

**Rationale**: C1 — Loại bỏ mâu thuẫn giữa Nhóm 2 và Nhóm 4. Room.status
giờ là thin derivation từ Lease.status, không còn tính riêng từ `end_date`.

**Verification**:

- [ ] Bảng mới có 4 rows với cột "Derive từ Lease.status"
- [ ] Mention rõ `lease_expired` vs `expired` là chủ ý
- [ ] Mention Lease `draft` → Room `vacant`

---

### P1.2 — Update US-017 AC2

**OLD:**

```markdown
- [ ] AC2: Logic derive (chỉ xét Lease không bị `terminated`):
```

Nếu không có Lease nào còn gắn với Room → 'vacant'

Nếu có Lease với end_date >= today:
days_left = lease.end_date - today > 30 → 'occupied'
≤ 30 → 'expiring_soon'

Nếu có Lease với end_date < today (đã qua hạn):
→ 'lease_expired'

```

```

**NEW:**

```markdown
- [ ] AC2: Logic derive — **map 1-1 từ Lease.status** (Lease non-terminal
      là Lease có `terminated_at IS NULL`):
```

Nếu Room không có Lease non-terminal nào → 'vacant'

Nếu Room có Lease non-terminal:
Lease.status = 'draft' → Room.status = 'vacant'
Lease.status = 'active' → Room.status = 'occupied'
Lease.status = 'expiring_soon' → Room.status = 'expiring_soon'
Lease.status = 'expired' → Room.status = 'lease_expired'

Lease.status = 'terminated' không còn là "non-terminal" → không xét.

```

**Trong đó Lease.status được tính theo công thức ở Nhóm 4** (Lease Lifecycle).
Room.status **không được tính riêng từ end_date** — phải đi qua Lease.status
để tránh lệch giữa 2 nhóm.
```

**Rationale**: C1 — Force Room.status phải query Lease.status, không tự
tính. Single Source of Truth.

**Verification**:

- [ ] AC2 không còn tính `days_left = end_date - today`
- [ ] AC2 map 4 lease statuses sang room statuses
- [ ] AC2 mention Lease `draft` → Room `vacant`

---

### P1.3 — Update US-017 AC5 (remove false cron UPDATE)

**OLD:**

```markdown
- [ ] AC5: Cron job hằng ngày (00:00) tự động chuyển Lease status từ
      `active` → `expired` khi `end_date < today`. Việc này tách logic
      hợp đồng khỏi logic Room status.
```

**NEW:**

```markdown
- [ ] AC5: Lease.status là **computed**, không cần cron UPDATE. Cron daily
      chỉ để trigger notifications khi status đổi (xem Nhóm 4 US-057).
      Room.status cũng computed theo mỗi query, không cron riêng.
```

**Rationale**: S2 — Nhóm 4 đã confirm status là computed, cron chỉ để
notification. Sửa Nhóm 2 để khớp.

**Verification**:

- [ ] AC5 không còn nói cron UPDATE Lease status
- [ ] AC5 reference tới Nhóm 4 US-057

---

### P1.4 — Update US-017 Notes

**OLD:**

```markdown
**Notes:**

- **Tách biệt concept**: `Lease.status` (hợp đồng) và `Room.status` (phòng) là
  2 thứ khác nhau. Lease status đổi qua cron (stored). Room status tính từ
  Lease data (computed).
- Cron job ở AC5 giúp tránh mâu thuẫn "Lease active nhưng end_date đã qua".
  Nếu cron chậm 1 ngày → data tạm lệch nhưng UX không bị ảnh hưởng nghiêm
  trọng (Landlord vẫn thấy cảnh báo qua `lease_expired`).
- AC6 đáp ứng thực tế VN: Lease hết hạn nhưng tenant vẫn ở, tiếp tục trả tiền.
  Hệ thống không được **chặn** Landlord, chỉ **cảnh báo**.
```

**NEW:**

```markdown
**Notes:**

- **2 concept khác nhau nhưng map 1-1**: `Lease.status` (góc nhìn hợp đồng)
  và `Room.status` (góc nhìn phòng). Cả 2 đều **computed**, không lưu DB.
  Room.status query qua Lease.status, không tính riêng.
- Naming khác nhau có chủ ý: Room dùng `lease_expired`, Lease dùng `expired`.
  Lý do: đọc "Room.lease_expired" rõ ngay là "hợp đồng trên phòng này đã hết",
  còn "Lease.expired" là "hợp đồng này đã hết" — mỗi context dùng tên phù hợp.
- AC6 đáp ứng thực tế VN: Lease hết hạn nhưng tenant vẫn ở, tiếp tục trả tiền.
  Hệ thống không được **chặn** Landlord, chỉ **cảnh báo**.
```

**Rationale**: Update Notes để khớp với logic mới ở AC2, AC5.

**Verification**:

- [ ] Notes không còn nói "Lease status đổi qua cron (stored)"
- [ ] Notes giải thích naming khác nhau có chủ ý

---

## Patch P2: Fix C2 — Handle Tenant reactivation in invite flow

**File**: `docs/01-requirements/01-auth-rbac.md`

### P2.1 — Add US-004 AC8

**OLD:**

```markdown
- [ ] AC7: Link chỉ có thể sinh bởi Landlord **sở hữu Property chứa Room
      của Tenant đó** (không cho mời Tenant của người khác)

**Notes:**

- Token là **opaque string** (random), không phải JWT, vì cần single-use
  và revocable qua DB
- MVP không tự gửi email/SMS — Landlord copy link và gửi Zalo thủ công
- v1.x: tích hợp gửi tự động qua email/SMS/Zalo Official Account
```

**NEW:**

```markdown
- [ ] AC7: Link chỉ có thể sinh bởi Landlord **sở hữu Property chứa Room
      của Tenant đó** (không cho mời Tenant của người khác)
- [ ] AC8: **Reactivation case** — nếu Tenant đã có `user_id` (đã từng
      accept invite trước đó, từ Lease cũ đã terminated và Tenant archived,
      giờ được reactivate qua US-030 AC7/AC8):
  - Nút "Gửi lời mời" đổi thành "Kích hoạt lại tài khoản"
  - Click → **không sinh invite token mới** (vì đã có User account)
  - Thay vào đó: unarchive User account + invalidate mọi refresh token cũ
    - gửi link **reset password** (reuse flow US-003) cho Tenant set
      password mới
  - Landlord copy link reset password (không phải invite link) gửi Zalo
    cho Tenant

**Notes:**

- Token là **opaque string** (random), không phải JWT, vì cần single-use
  và revocable qua DB
- MVP không tự gửi email/SMS — Landlord copy link và gửi Zalo thủ công
- v1.x: tích hợp gửi tự động qua email/SMS/Zalo Official Account
- AC8 tái sử dụng flow reset password để không duplicate logic. Tenant
  dùng cùng email cũ, chỉ đổi password.
```

**Rationale**: C2 — Nhóm 3 US-030 AC7/AC8 cho phép reactivate Tenant
archived. Invite flow cần handle case này thay vì tạo User account mới
(sẽ fail vì email đã tồn tại).

**Verification**:

- [ ] US-004 có AC8 về reactivation
- [ ] AC8 reference US-003 (forgot password) và US-030 AC7/AC8
- [ ] Notes giải thích lý do reuse reset password flow

---

### P2.2 — Add US-005 AC6

**OLD:**

```markdown
- [ ] AC5: Auto login + redirect vào dashboard Tenant

**Notes:**

- AC3 che SĐT là pattern an toàn: người có link nhưng không biết SĐT đầy đủ
  sẽ không confirm được → thêm 1 lớp verify
```

**NEW:**

```markdown
- [ ] AC5: Auto login + redirect vào dashboard Tenant
- [ ] AC6: **Edge case guard** — nếu token valid nhưng Tenant đã có
      `user_id` (shouldn't happen nếu US-004 AC8 đúng, nhưng phòng bug):
  - Không tạo User account mới
  - Hiển thị message: "Tài khoản đã tồn tại. Vui lòng dùng chức năng
    'Quên mật khẩu' để đặt lại mật khẩu."
  - Redirect sang trang login + forgot password

**Notes:**

- AC3 che SĐT là pattern an toàn: người có link nhưng không biết SĐT đầy đủ
  sẽ không confirm được → thêm 1 lớp verify
- AC6 là defense-in-depth: flow đúng (US-004 AC8) sẽ dùng reset password
  cho reactivation, không phải invite token. Nhưng nếu dev vô tình để token
  invite được sinh cho Tenant đã có User account → AC6 catch case đó.
```

**Rationale**: C2 — Defensive check trong US-005 để tránh bug "tạo User
trùng email".

**Verification**:

- [ ] US-005 có AC6 về edge case
- [ ] AC6 redirect sang forgot password flow
- [ ] Notes giải thích defense-in-depth

---

### P2.3 — Update US-004 Depends on

**OLD:**

```markdown
**Priority**: Must
**Estimate**: M
**Depends on**: US-001, US-030 (Tenant CRUD — nhóm sau)
```

**NEW:**

```markdown
**Priority**: Must
**Estimate**: M
**Depends on**: US-001, US-003 (forgot password — reuse cho reactivation),
US-030 (Tenant CRUD)
```

**Rationale**: Thêm dependency rõ ràng US-003 vì US-004 AC8 reuse flow
đó.

**Verification**:

- [ ] US-004 Depends on có US-003

---

## Patch P3: Fix S2 — Consolidate cron jobs

**File**: `docs/01-requirements/04-lease.md`
**Section**: US-057 Acceptance Criteria

### P3.1 — Update US-057 AC1 to be the single cron definition

**OLD:**

```markdown
**Acceptance Criteria:**

- [ ] AC1: Cron job chạy **mỗi ngày lúc 00:05** (cùng cron với Tenant status,
      Nhóm 3)
- [ ] AC2: Logic cron (pseudo-code):
```

FOR each Lease WHERE terminated_at IS NULL:
IF today < start_date: computed_status = 'draft'
ELSE IF today <= end_date - 30 days: computed_status = 'active'
ELSE IF today <= end_date: computed_status = 'expiring_soon'
ELSE: computed_status = 'expired'

```

```

**NEW:**

```markdown
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

```

**Rationale**: S2 — Làm rõ đây là cron duy nhất, không phải nhiều cron.

**Verification**:

- [ ] AC1 nói rõ "cron job duy nhất"
- [ ] AC1 mention sẽ có kiến trúc tổng ở cuối file

---

### P3.2 — Add cron architecture to Ghi chú kiến trúc

**OLD:**

```markdown
## Ghi chú kiến trúc cho Phase 3

**Entity Relationships (preview):**
```

**NEW:**

```markdown
## Ghi chú kiến trúc cho Phase 3

**Daily Status Maintenance Cron** (kiến trúc tổng):
```

┌────────────────────────────────────────────┐
│ Cron: 00:05 daily │
├────────────────────────────────────────────┤
│ Task 1: Check Lease status transitions │
│ - Trigger notifications khi đổi status │
│ - KHÔNG UPDATE DB (status computed) │
│ │
│ Task 2: Check Tenant status transitions │
│ - Trigger notifications │
│ - KHÔNG UPDATE DB (status computed) │
│ │
│ Task 3: Room status │
│ - Không cần check (derive từ Lease) │
│ │
│ Task 4: Future v1.x — invoice reminders, │
│ notification delivery, etc. │
├────────────────────────────────────────────┤
│ Output: Log file (count + errors) │
│ Property: Idempotent (chạy 2 lần = 1 lần) │
└────────────────────────────────────────────┘

```

**Lưu ý**: MVP không có notification thật (email/push), nên cron task 1-3
gần như no-op về side effects. Nhưng giữ structure để v1.x plug notification
vào dễ dàng. Xem Phase 3 ADR "Cron job architecture" để chi tiết.

**Entity Relationships (preview):**
```

**Rationale**: S2 — Document tổng kiến trúc cron ở 1 chỗ, reference từ
các nhóm khác.

**Verification**:

- [ ] Section có ASCII diagram cron architecture
- [ ] Mention MVP chưa có notification thật

---

## Patch P4: Fix S2 — Add Tenant cron story

**File**: `docs/01-requirements/03-tenant.md`
**Section**: Insert new US after US-036, before US-037

### P4.1 — Add new US-036b: Tenant status cron

**INSERT AFTER** (find this text):

```markdown
- Flow này **chỉ áp dụng khi đổi người đại diện**. Trường hợp 1 Tenant
  dọn đi hoàn toàn (không ai ở lại) → dùng flow thường: terminate Lease
  (Nhóm 4) + archive Tenant (US-033).

---

### US-037: Tenant xem và sửa thông tin cá nhân của mình
```

**INSERT THIS BEFORE `### US-037`:**

```markdown
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
ELSE IF exists terminated/expired Leases: status = 'moved_out' -- edge case
ELSE: status = 'pending' -- chưa có Lease nào

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
```

**Rationale**: S2 — Thêm US-036b để Tenant cron có home rõ ràng, không
phải "ngầm hiểu".

**Verification**:

- [ ] File có US-036b với đầy đủ AC1-AC5
- [ ] US-036b reference Nhóm 4 US-057

---

### P4.2 — Update Summary table

**OLD:**

```markdown
## Summary
```

**Search for the summary table** (should be near end of file) và update
nếu có bảng summary — thêm row cho US-036b. Nếu file không có summary
table thì skip patch này.

**Rationale**: Consistency.

---

## Patch P5: Fix S3 — Add Open Question about multi-role

**File**: `docs/01-requirements/01-auth-rbac.md`
**Section**: Open Questions

**OLD:**

```markdown
## Open Questions (cần trả lời trước khi vào Phase 3)

1. **Refresh token rotation**: áp dụng hay không? (security vs complexity)
2. **Lưu refresh token ở đâu** phía client? (httpOnly cookie vs localStorage)
3. **Email service**: tự host SMTP hay dùng SaaS (Resend, SendGrid free tier)?
4. **Rate limiting** (US-002 AC4, US-006 AC6): in-memory hay Redis?
5. **Session limit**: 1 user login được bao nhiêu device cùng lúc?
   (MVP có thể unlimited, v1.x cân nhắc)
```

**NEW:**

```markdown
## Open Questions (cần trả lời trước khi vào Phase 3)

1. **Refresh token rotation**: áp dụng hay không? (security vs complexity)
2. **Lưu refresh token ở đâu** phía client? (httpOnly cookie vs localStorage)
3. **Email service**: tự host SMTP hay dùng SaaS (Resend, SendGrid free tier)?
4. **Rate limiting** (US-002 AC4, US-006 AC6): in-memory hay Redis?
5. **Session limit**: 1 user login được bao nhiêu device cùng lúc?
   (MVP có thể unlimited, v1.x cân nhắc)
6. **Multi-role per user**: 1 User account có thể vừa là Landlord vừa là
   Tenant không? (Case: Bảo cho thuê nhà mình, đồng thời đi thuê nhà người
   khác cũng trên app này)
   - Option A: 1 user = 1 role (MVP, đơn giản). Bảo phải tạo 2 account
     riêng với 2 email khác nhau nếu muốn cả 2 vai trò.
   - Option B: User có `roles: list[Role]` (phức tạp, cần logic role
     switcher ở UI).
   - Option C: Tách User (auth) khỏi Profile (Landlord/Tenant record).
     1 auth user có N profile khác nhau.
   - **Đề xuất MVP: Option A**. Simpler, match 99% use cases.
7. **Landlord/Tenant relationship với User**:
   - Landlord: `User.role = 'landlord'` → 1-1 với User record (không có
     Landlord entity riêng)
   - Tenant: có Tenant entity riêng (domain), có thể `user_id = NULL`
     (chưa invite), có thể `user_id` trỏ đến User role=tenant (đã invite)
   - **Pattern khác nhau có lý do**: Landlord always has account; Tenant
     may or may not (Landlord có thể track Tenant không biết công nghệ)
```

**Rationale**: S3 — Document rõ design decision về user-tenant
relationship và multi-role.

**Verification**:

- [ ] Open Questions có câu 6 (multi-role) và câu 7 (user-tenant pattern)

---

## Patch P6: Fix S4 — Clarify Tenant also uses US-002 login

**File**: `docs/01-requirements/01-auth-rbac.md`
**Section**: US-002 Notes

**OLD:**

```markdown
**Notes:**

- Rate limiting (AC4) có thể dùng trong-memory cho MVP, Redis cho v1.x
```

**NEW:**

```markdown
**Notes:**

- Rate limiting (AC4) có thể dùng trong-memory cho MVP, Redis cho v1.x
- **US-002 cover cả Landlord và Tenant login**: cùng endpoint `POST /auth/login`,
  cùng UI form. Sự khác biệt duy nhất là `role` trong JWT payload (xem
  US-009). Tenant account được tạo qua flow invite (US-005), sau đó login
  bằng email + password tự set.
```

**Rationale**: S4 — Clarify US-002 là shared login cho cả 2 role.

**Verification**:

- [ ] Notes mention Tenant cũng dùng US-002

---

## Patch P7: Fix S1 — Document lifecycle field naming convention

**File**: `docs/01-requirements/PHASE2-REVIEW.md`
**Section**: Action Items (để track cho Phase 3)

Đây là patch **không sửa stories**, chỉ thêm note cho tương lai. Kiểm tra
nếu `PHASE2-REVIEW.md` đã có section Action Items với item "Phase 3 ADR:
Naming convention" → skip patch này. Nếu chưa, thêm vào.

Do `PHASE2-REVIEW.md` chỉ được tạo mới trong session này, Claude Code sẽ
cần file này trước khi patch. Skip if not exists, Bảo tự tạo từ
`/mnt/user-data/outputs/PHASE2-REVIEW.md`.

**Verification**: `PHASE2-REVIEW.md` exists in repo.

---

## Patch P8: Update glossary with missing terms

**File**: `docs/00-overview/glossary.md`

### P8.1 — Add Occupant to Entities table

**OLD:**

```markdown
| Tiếng Việt    | English (code) | Định nghĩa                                                   | Phase |
| ------------- | -------------- | ------------------------------------------------------------ | ----- |
| Nhà trọ       | Property       | Một toà nhà / dãy trọ. Thuộc về 1 Landlord.                  | MVP   |
| Phòng         | Room           | Đơn vị cho thuê nhỏ nhất, thuộc 1 Property.                  | MVP   |
| Hợp đồng      | Lease          | Thoả thuận thuê giữa Landlord và Tenant cho 1 Room.          | MVP   |
| Dịch vụ       | Service        | Khoản phí ngoài tiền phòng: điện, nước, internet, rác...     | MVP   |
| Chỉ số        | Meter Reading  | Số đọc từ đồng hồ điện/nước tại 1 thời điểm.                 | MVP   |
| Hoá đơn       | Invoice        | Bảng tính tiền hàng tháng cho 1 Room (tiền phòng + dịch vụ). | MVP   |
| Thanh toán    | Payment        | Giao dịch trả tiền cho 1 Invoice.                            | MVP   |
| Tiền cọc      | Deposit        | Tiền đặt cọc khi ký hợp đồng.                                | MVP   |
| Tiền phòng    | Rent           | Giá thuê phòng cố định hàng tháng.                           | MVP   |
| Kỳ thanh toán | Billing Period | Chu kỳ tính tiền, thường là 1 tháng.                         | MVP   |
| Tài sản       | Asset          | Đồ đạc / thiết bị thuộc phòng hoặc nhà.                      | v1.x  |
```

**NEW:**

```markdown
| Tiếng Việt    | English (code) | Định nghĩa                                                             | Phase |
| ------------- | -------------- | ---------------------------------------------------------------------- | ----- |
| Nhà trọ       | Property       | Một toà nhà / dãy trọ. Thuộc về 1 Landlord.                            | MVP   |
| Phòng         | Room           | Đơn vị cho thuê nhỏ nhất, thuộc 1 Property.                            | MVP   |
| Hợp đồng      | Lease          | Thoả thuận thuê giữa Landlord và Tenant cho 1 Room.                    | MVP   |
| Dịch vụ       | Service        | Khoản phí ngoài tiền phòng: điện, nước, internet, rác...               | MVP   |
| Chỉ số        | Meter Reading  | Số đọc từ đồng hồ điện/nước tại 1 thời điểm.                           | MVP   |
| Hoá đơn       | Invoice        | Bảng tính tiền hàng tháng cho 1 Room (tiền phòng + dịch vụ).           | MVP   |
| Thanh toán    | Payment        | Giao dịch trả tiền cho 1 Invoice.                                      | MVP   |
| Tiền cọc      | Deposit        | Tiền đặt cọc khi ký hợp đồng.                                          | MVP   |
| Tiền phòng    | Rent           | Giá thuê phòng cố định hàng tháng.                                     | MVP   |
| Kỳ thanh toán | Billing Period | Chu kỳ tính tiền, thường là 1 tháng.                                   | MVP   |
| Người ở cùng  | Occupant       | Người ở chung phòng với Tenant, không ký hợp đồng, không có tài khoản. | MVP   |
| Tài sản       | Asset          | Đồ đạc / thiết bị thuộc phòng hoặc nhà.                                | v1.x  |
```

**Rationale**: Add Occupant to glossary (defined in Nhóm 3 but missing).

**Verification**:

- [ ] Row "Người ở cùng | Occupant" exists between Billing Period and Asset

---

### P8.2 — Add billing_type enum section

**OLD:**

```markdown
## Trạng thái (Statuses)
```

**NEW:**

```markdown
## Billing Types (Kiểu tính dịch vụ)

| Value        | Vietnamese          | Cách tính                         | Ví dụ                   |
| ------------ | ------------------- | --------------------------------- | ----------------------- |
| `per_meter`  | Theo chỉ số đồng hồ | (số_mới − số_cũ) × đơn_giá        | Điện (kWh), nước (m³)   |
| `per_person` | Theo đầu người      | số_người × đơn_giá                | Rác, giữ xe, thang máy  |
| `fixed`      | Cố định             | đơn_giá (cố định / phòng / tháng) | Internet, vệ sinh chung |

## Service Scope

| Value            | Áp dụng cho                                 |
| ---------------- | ------------------------------------------- |
| `all_rooms`      | Tất cả Room trong Property (default)        |
| `selected_rooms` | Subset Room được chọn (chỉ cho `per_meter`) |

## Trạng thái (Statuses)
```

**Rationale**: Add billing_type and scope enums to glossary (Nhóm 5).

**Verification**:

- [ ] Section "Billing Types" and "Service Scope" added before "Trạng thái"

---

### P8.3 — Update Statuses section with full enums

**OLD:**

```markdown
## Trạng thái (Statuses)

| Entity  | Status        | Nghĩa                                  |
| ------- | ------------- | -------------------------------------- |
| Room    | vacant        | Phòng trống, sẵn sàng cho thuê         |
| Room    | occupied      | Đang có người thuê                     |
| Room    | expiring_soon | Hợp đồng sắp hết hạn (derive từ Lease) |
| Invoice | unpaid        | Chưa thanh toán                        |
| Invoice | partial       | Đã trả một phần                        |
| Invoice | paid          | Đã thanh toán đủ                       |
| Lease   | active        | Đang hiệu lực                          |
| Lease   | expiring_soon | Sắp hết hạn (ví dụ: còn ≤ 30 ngày)     |
| Lease   | expired       | Đã hết hạn                             |
| Lease   | terminated    | Chấm dứt sớm                           |
```

**NEW:**

```markdown
## Trạng thái (Statuses)

**Lưu ý**: Tất cả status dưới đây đều là **computed fields** (trừ
`Lease.terminated` qua `terminated_at`). Không lưu DB, tính khi query.

### Room Status (derive 1-1 từ Lease.status)

| Status          | Nghĩa                                    | Ứng với Lease.status                            |
| --------------- | ---------------------------------------- | ----------------------------------------------- |
| `vacant`        | Phòng trống, sẵn sàng cho thuê           | không có Lease, hoặc `draft`, hoặc `terminated` |
| `occupied`      | Đang có người thuê                       | `active`                                        |
| `expiring_soon` | Hợp đồng sắp hết hạn (còn ≤ 30 ngày)     | `expiring_soon`                                 |
| `lease_expired` | Hợp đồng đã hết hạn, Tenant có thể còn ở | `expired`                                       |

### Lease Status

| Status          | Nghĩa                                                   |
| --------------- | ------------------------------------------------------- |
| `draft`         | Đã tạo nhưng chưa đến start_date                        |
| `active`        | Đang hiệu lực (start_date ≤ today ≤ end_date - 30 days) |
| `expiring_soon` | Sắp hết hạn (còn ≤ 30 ngày đến end_date)                |
| `expired`       | Đã qua end_date, chưa terminated                        |
| `terminated`    | Chấm dứt sớm (có `terminated_at`)                       |

### Tenant Status

| Status      | Nghĩa                                 |
| ----------- | ------------------------------------- |
| `pending`   | Đã tạo record nhưng chưa ký Lease nào |
| `active`    | Đang có Lease không terminated        |
| `moved_out` | Đã archive, tất cả Lease đã kết thúc  |

### Invoice Status

| Status    | Nghĩa            |
| --------- | ---------------- |
| `unpaid`  | Chưa thanh toán  |
| `partial` | Đã trả một phần  |
| `paid`    | Đã thanh toán đủ |

### Deposit Status (field của Lease)

| Status      | Nghĩa                                   |
| ----------- | --------------------------------------- |
| `held`      | Đang giữ cọc (default khi tạo Lease)    |
| `returned`  | Đã trả lại (đủ hoặc 1 phần sau khi trừ) |
| `forfeited` | Mất cọc toàn bộ (Tenant vi phạm)        |
| `deducted`  | Lấy cọc bù nợ                           |
```

**Rationale**: Complete all status enums in 1 place for easy reference.

**Verification**:

- [ ] 5 sub-sections: Room, Lease, Tenant, Invoice, Deposit statuses
- [ ] Room status table shows mapping to Lease status
- [ ] Lease có đủ 5 statuses (draft, active, expiring_soon, expired, terminated)

---

## Patch P9: Update CHANGELOG for Nhóm 4

**File**: `CHANGELOG.md`
**Section**: [Unreleased] section, insert new version entry

**OLD:**

```markdown
## [Unreleased]

### In Progress — Phase 2: Requirements

- Nhóm 4 (Lease): chưa bắt đầu
- Nhóm 5 (Service): chưa bắt đầu
- Nhóm 6 (Meter Reading): chưa bắt đầu
- Nhóm 7 (Invoice): chưa bắt đầu
- Nhóm 8 (Payment): chưa bắt đầu
```

**NEW:**

```markdown
## [Unreleased]

### In Progress — Phase 2: Requirements

- Nhóm 6 (Meter Reading): chưa bắt đầu
- Nhóm 7 (Invoice): chưa bắt đầu
- Nhóm 8 (Payment): chưa bắt đầu

## [0.4.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 5) DRAFT

### Added

- **Nhóm 5: Service** (`docs/01-requirements/05-service.md`)
  - 7 user stories (US-060 → US-066)
  - 3 billing types: per_meter / per_person / fixed
  - Service scope: all_rooms (default) / selected_rooms (cho công tơ chung)
  - Shared per_meter chia theo số người các phòng trong scope
  - Toggle is_active thay cho hard/soft delete
  - Unit auto theo billing_type (chỉ per_meter mới nhập)

### Decisions

- Service là template, không phải entity sống
- Invoice Immutability Pattern: Invoice snapshot giá tại thời điểm tạo,
  Service đổi sau không ảnh hưởng Invoice cũ
- Service config ở Property-level (không có Room-level)
- Không per-Lease override ở MVP
- Không đổi giá giữa kỳ (áp dụng từ tháng sau)
- Phòng trống trong shared meter không chịu phí

## [0.3.0] – 2026-04-17 — Phase 2: Requirements (Nhóm 4) DRAFT

### Added

- **Nhóm 4: Lease** (`docs/01-requirements/04-lease.md`)
  - 10 user stories (US-050 → US-059)
  - Strict single-active: 1 Room chỉ có 1 Lease active
  - 5 status: draft / active / expiring_soon / expired / terminated
  - Status computed (trừ terminated lưu terminated_at)
  - Pro-rata universal: rent = rent_amount × days_occupied / days_in_month
  - Deposit 4 status: held / returned / forfeited / deducted
  - Renewal = tạo Lease mới với renewed_from_lease_id link
  - Rollover deposit: dùng returned + amount=0 + note (không thêm status mới)
  - Grace period expired: vẫn tính Invoice theo rent cũ

### Decisions

- Landlord dùng start_date/terminated_date làm công cụ chính sách
  (không có field billing_mode riêng)
- Lease active gần immutable: chỉ sửa note + end_date
- Deposit là trạng thái của Lease, không phải giao dịch (không tạo Payment)
- Terminate và settle deposit tách 2 step riêng
- Auto-archive Tenant khi settle deposit xong
```

**Rationale**: CHANGELOG thiếu entry cho Nhóm 4, 5. Thêm vào để phản ánh
tiến độ thực.

**Verification**:

- [ ] Có entries 0.3.0 (Nhóm 4) và 0.4.0 (Nhóm 5)
- [ ] [Unreleased] chỉ còn Nhóm 6, 7, 8

---

## Patch P10: Add PHASE2 Review entry to CHANGELOG

**File**: `CHANGELOG.md`
**Section**: Insert new version entry after 0.4.0

**OLD** (sau khi P9 đã apply):

```markdown
## [0.4.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 5) DRAFT
```

**NEW** (insert version 0.4.1 BEFORE 0.4.0):

```markdown
## [0.4.1] – 2026-04-18 — Phase 2 Gate Review (Mid-phase)

### Added

- **Phase 2 Review** (`docs/01-requirements/PHASE2-REVIEW.md`)
  - Full cross-reference review of Nhóm 1-5
  - Identified 2 Critical issues (C1, C2), 5 Should-fix (S1-S5),
    3 Observations (N1-N3), 4 Strengths
- **Phase 2 Review Patches** (`docs/01-requirements/PHASE2-REVIEW-PATCHES.md`)
  - Detailed before/after patches for Claude Code execution

### Fixed (from review)

- **C1**: Unified Room.status derivation — now maps 1-1 from Lease.status
  instead of computing from end_date independently
  - `02-property-room.md` US-017 AC2, AC5
- **C2**: Handled Tenant reactivation in invite flow — reuse forgot password
  flow instead of creating duplicate User account
  - `01-auth-rbac.md` US-004 AC8, US-005 AC6
- **S2**: Consolidated cron jobs into single "Daily Status Maintenance Cron"
  - `04-lease.md` US-057 AC1, architecture section
  - `03-tenant.md` US-036b added
- **S3**: Documented multi-role user as Open Question
  - `01-auth-rbac.md` Open Questions #6, #7
- **S4**: Clarified US-002 covers both Landlord and Tenant login
  - `01-auth-rbac.md` US-002 Notes

### Updated

- `glossary.md`: Added Occupant, billing_type, Service scope,
  full status enums for Room/Lease/Tenant/Invoice/Deposit

## [0.4.0] – 2026-04-18 — Phase 2: Requirements (Nhóm 5) DRAFT
```

**Rationale**: Track review as a distinct milestone in CHANGELOG.

**Verification**:

- [ ] Version 0.4.1 exists between Unreleased and 0.4.0
- [ ] Lists all fixes applied

---

## Patch P11: Status tag update in review file

**File**: `docs/01-requirements/PHASE2-REVIEW.md`
**Section**: Top of file

**OLD:**

```markdown
# Phase 2 — Gate Review (Level 2: Full Requirements Review)

> **Review Date**: 2026-04-18
> **Phase Status**: 5/8 groups drafted
> **Reviewer**: Claude (as Senior Engineer)
> **Review Scope**: Level 2 — Cross-reference, RBAC, Data flow, Naming convention
> **Approver**: Bảo
```

**NEW:**

```markdown
# Phase 2 — Gate Review (Level 2: Full Requirements Review)

> **Review Date**: 2026-04-18
> **Phase Status**: 5/8 groups drafted
> **Reviewer**: Claude (as Senior Engineer)
> **Review Scope**: Level 2 — Cross-reference, RBAC, Data flow, Naming convention
> **Approver**: Bảo
> **Resolution Status**: Patches applied via PHASE2-REVIEW-PATCHES.md on 2026-04-18
```

**Rationale**: Signal that review has been actioned.

**Verification**:

- [ ] Frontmatter has "Resolution Status" line

---

## Patch P12: Mark resolved items in review file

**File**: `docs/01-requirements/PHASE2-REVIEW.md`
**Section**: Action Items Summary

**OLD:**

```markdown
### Before Nhóm 6 (Must)

1. [ ] **Fix C1**: Update `02-property-room.md` US-017 AC2 để derive Room.status từ Lease.status 1-1
2. [ ] Update `glossary.md` để document cả Room và Lease status enums

### Before Phase 2 close (Should)

3. [ ] **Fix C2**: Add reactivation flow vào US-004, US-005
4. [ ] **Fix S1**: Không cần sửa stories, ghi ADR-0001 ở Phase 3
5. [ ] **Fix S2**: Consolidate cron jobs, fix `02-property-room.md` US-017 AC5
6. [ ] **Fix S3**: Add Open Question về multi-role vào `01-auth-rbac.md`
7. [ ] Update `glossary.md` thêm Occupant, billing_type
```

**NEW:**

```markdown
### Before Nhóm 6 (Must)

1. [x] **Fix C1**: Update `02-property-room.md` US-017 AC2 để derive Room.status từ Lease.status 1-1 ✅ 2026-04-18
2. [x] Update `glossary.md` để document cả Room và Lease status enums ✅ 2026-04-18

### Before Phase 2 close (Should)

3. [x] **Fix C2**: Add reactivation flow vào US-004, US-005 ✅ 2026-04-18
4. [ ] **Fix S1**: Không cần sửa stories, ghi ADR-0001 ở Phase 3 (deferred to Phase 3)
5. [x] **Fix S2**: Consolidate cron jobs, fix `02-property-room.md` US-017 AC5 ✅ 2026-04-18
6. [x] **Fix S3**: Add Open Question về multi-role vào `01-auth-rbac.md` ✅ 2026-04-18
7. [x] Update `glossary.md` thêm Occupant, billing_type ✅ 2026-04-18
```

**Rationale**: Mark action items as done for tracking.

**Verification**:

- [ ] Items 1, 2, 3, 5, 6, 7 marked with [x] and ✅

---

## Verification Checklist (run after all patches applied)

```bash
# 1. Check no orphan references
grep -r "lease_expired" docs/ --include="*.md"
# Expected: references in 02-property-room.md (Room.status) and glossary.md

grep -r "Lease.status.*expired" docs/ --include="*.md"
# Expected: references in 04-lease.md (without "lease_" prefix)

# 2. Check cron references point to US-057
grep -rn "cron" docs/01-requirements/ --include="*.md"
# Expected: US-017 references US-057; US-036b references US-057

# 3. Check reactivation flow
grep -n "reactivat\|kích hoạt lại" docs/01-requirements/01-auth-rbac.md
# Expected: matches in US-004 AC8, US-005 AC6

# 4. Check glossary has new entries
grep -E "Occupant|per_meter|per_person|fixed" docs/00-overview/glossary.md
# Expected: multiple matches

# 5. Check CHANGELOG has 0.4.0 and 0.4.1
grep -E "^## \[0\.4" CHANGELOG.md
# Expected: 2 lines (0.4.0 and 0.4.1)
```

## Commit Message Template

```
fix(requirements): resolve PHASE2 review issues (C1, C2, S1-S5)

Applied 12 patches from PHASE2-REVIEW-PATCHES.md:

Critical fixes:
- C1: Unified Room.status to derive 1-1 from Lease.status, eliminating
  naming and logic conflict between Nhóm 2 and Nhóm 4.
- C2: Added reactivation flow for Tenant accounts using forgot password
  pattern, preventing duplicate User record creation.

Should-fix:
- S2: Consolidated cron jobs into single "Daily Status Maintenance Cron"
  architecture.
- S3: Documented multi-role user question in Auth Open Questions.
- S4: Clarified US-002 login covers both Landlord and Tenant.

Documentation:
- Updated glossary.md with Occupant, billing_type enums, scope, and all
  status enums for Room/Lease/Tenant/Invoice/Deposit.
- Added CHANGELOG entries for Nhóm 4, 5, and review milestone 0.4.1.

Files changed:
- docs/00-overview/glossary.md
- docs/01-requirements/01-auth-rbac.md
- docs/01-requirements/02-property-room.md
- docs/01-requirements/03-tenant.md
- docs/01-requirements/04-lease.md
- docs/01-requirements/PHASE2-REVIEW.md
- CHANGELOG.md

Deferred to Phase 3:
- S1 (naming convention ADR-0001)
- N1 (audit log architecture)
- N2 (notification framework)

Ref: PHASE2-REVIEW.md
```
