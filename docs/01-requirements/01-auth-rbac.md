# User Stories — Nhóm 1: Auth & RBAC

> **Status**: DRAFT — chờ Bảo review
> **Last updated**: 2026-04-17
> **Phase**: 2 — Requirements
> **Author**: Claude (as Senior Engineer)
> **Reviewer**: Bảo

---

## Overview

Nhóm này định nghĩa **cách user vào được hệ thống**: đăng ký, đăng nhập,
phân quyền, khôi phục tài khoản.

**Map với Vision**:

- MVP feature #10 (Authentication)
- MVP feature #11 (RBAC: Landlord + Tenant)

**Key decisions (đã chốt):**

| #   | Decision                                                    | Lý do                               |
| --- | ----------------------------------------------------------- | ----------------------------------- |
| 1   | Landlord self-signup qua email + password                   | Pattern SaaS chuẩn                  |
| 2   | Tenant **không** self-signup — Landlord mời qua invite link | Đúng Persona B (bị động)            |
| 3   | Invite token: single-use, TTL 7 ngày, lưu DB (stateful)     | Revocable, trackable                |
| 4   | Forgot password qua email (pattern giống invite token)      | Chuẩn SaaS, dùng lại pattern        |
| 5   | RBAC 2 role (Landlord, Tenant), thiết kế mở                 | Mở rộng Manager/Investor sau        |
| 6   | Tenant mất link → gọi Landlord resend (không self-service)  | YAGNI — MVP scale nhỏ, v1.x mới cần |

## Changelog

- **2026-04-17 v0.2**: Bỏ US-006 (Tenant tự request link mới) — đẩy v1.x.
  Lý do: MVP scale nhỏ, flow "Landlord bấm Gửi lại" ở US-004 AC5 đã đủ.
- **2026-04-17 v0.1**: Draft đầu tiên với 9 stories.

## Personas liên quan

- **Landlord** (Persona A): primary actor cho signup, login, invite, forgot password
- **Tenant** (Persona B): secondary actor, chỉ nhận invite và login

## Dependencies

- **Depends on**: không (nhóm nền tảng, chạy đầu tiên)
- **Blocks**: tất cả các nhóm khác (Property, Room, Tenant management, Invoice...)
  đều cần user đăng nhập trước khi thao tác

## Legend

- **Priority**: `Must` (MVP bắt buộc) / `Should` (nên có) / `Could` (nice-to-have)
- **Estimate**: `S` (≤ 1 ngày) / `M` (1–3 ngày) / `L` (3–5 ngày)

---

## Stories

### US-001: Landlord đăng ký tài khoản

**As a** chủ nhà trọ muốn dùng RMS
**I want to** tự tạo tài khoản bằng email và password
**So that** tôi có thể bắt đầu quản lý nhà trọ của mình trên hệ thống

**Priority**: Must
**Estimate**: M
**Depends on**: none

**Acceptance Criteria:**

- [ ] AC1: Form đăng ký có các trường: email, password, họ tên, số điện thoại
- [ ] AC2: Email phải đúng định dạng và chưa tồn tại trong hệ thống
- [ ] AC3: Password tối thiểu 8 ký tự, có chữ và số (validate client + server)
- [ ] AC4: Số điện thoại đúng định dạng VN (10 số, bắt đầu 0)
- [ ] AC5: Sau khi đăng ký thành công, user có role = `Landlord` và được
      chuyển vào trang chủ (đã login)
- [ ] AC6: Password được hash (bcrypt/argon2) trước khi lưu DB
- [ ] AC7: Error message rõ ràng (tiếng Việt) khi vi phạm AC2–AC4

**Notes:**

- Email verification chưa có trong MVP → v1.x
- Register tự động login ngay (không cần step confirm)

---

### US-002: Landlord đăng nhập

**As a** Landlord đã có tài khoản
**I want to** đăng nhập bằng email + password
**So that** tôi có thể truy cập dữ liệu nhà trọ của mình

**Priority**: Must
**Estimate**: S
**Depends on**: US-001

**Acceptance Criteria:**

- [ ] AC1: Form login có 2 trường: email, password
- [ ] AC2: Nếu đúng → nhận JWT access token (TTL 60 phút) + refresh token
      (TTL 7 ngày)
- [ ] AC3: Nếu sai → message chung chung: "Email hoặc password không đúng"
      (không tiết lộ trường nào sai, chống user enumeration)
- [ ] AC4: Sai 5 lần trong 15 phút → lock account 15 phút
- [ ] AC5: Response login trả về thông tin user (không bao gồm password hash)
      và token

**Notes:**

- Rate limiting (AC4) có thể dùng trong-memory cho MVP, Redis cho v1.x
- **US-002 cover cả Landlord và Tenant login**: cùng endpoint `POST /auth/login`,
  cùng UI form. Sự khác biệt duy nhất là `role` trong JWT payload (xem
  US-009). Tenant account được tạo qua flow invite (US-005), sau đó login
  bằng email + password tự set.

---

### US-003: Landlord quên password, reset qua email

**As a** Landlord quên mật khẩu
**I want to** nhận link reset qua email và tự set password mới
**So that** tôi có thể lấy lại quyền truy cập mà không cần hỗ trợ thủ công

**Priority**: Must
**Estimate**: M
**Depends on**: US-001

**Acceptance Criteria:**

- [ ] AC1: Trang "Forgot password" có 1 trường nhập email
- [ ] AC2: Sau khi submit, hệ thống luôn trả response "Nếu email tồn tại,
      link đã được gửi" (không xác nhận có/không, chống user enumeration)
- [ ] AC3: Nếu email tồn tại → sinh reset token (random, opaque, 32+ ký tự),
      lưu DB với `expires_at = now() + 1h`, gửi email chứa link
- [ ] AC4: Link có dạng `{base_url}/reset-password?token=xxx`
- [ ] AC5: Token **single-use**: sau khi dùng thành công → đánh dấu `used_at`
- [ ] AC6: Token hết hạn → trang báo "Link đã hết hạn, vui lòng yêu cầu lại"
- [ ] AC7: Form reset yêu cầu nhập password mới 2 lần, validate như US-001 AC3
- [ ] AC8: Sau khi reset thành công → invalidate tất cả refresh token cũ
      của user này (force logout mọi device)
- [ ] AC9: Request reset mới → invalidate token reset cũ chưa dùng

**Notes:**

- Email service cho MVP có thể dùng SMTP free (Gmail SMTP, Mailtrap dev)
- AC8 quan trọng về security: nếu account bị hijack, reset password sẽ
  đuổi attacker ra khỏi mọi session

---

### US-004: Landlord mời Tenant vào hệ thống

**As a** Landlord đã tạo Tenant record trong app
**I want to** sinh một invite link cho Tenant đó
**So that** Tenant có thể tự kích hoạt tài khoản và xem thông tin phòng mình

**Priority**: Must
**Estimate**: M
**Depends on**: US-001, US-003 (forgot password — reuse cho reactivation),
US-030 (Tenant CRUD)

**Acceptance Criteria:**

- [ ] AC1: Từ màn hình chi tiết Tenant, Landlord có nút "Gửi lời mời" / "Mời vào app"
- [ ] AC2: Click nút → sinh invite token (random 32+ ký tự), lưu DB với
      `tenant_id`, `expires_at = now() + 7 days`, `used_at = null`
- [ ] AC3: UI hiện link hoàn chỉnh (`{base_url}/invite/accept?token=xxx`)
      với nút "Copy link" để Landlord paste vào Zalo
- [ ] AC4: Nếu Tenant đã có active invite token → nút đổi thành "Gửi lại"
- [ ] AC5: Bấm "Gửi lại" → invalidate token cũ (set `used_at` hoặc xoá),
      sinh token mới, hiện link mới
- [ ] AC6: Nếu Landlord chỉnh sửa SĐT hoặc email của Tenant → tất cả invite
      token active của Tenant đó bị invalidate tự động
- [ ] AC7: Link chỉ có thể sinh bởi Landlord **sở hữu Property chứa Room
      của Tenant đó** (không cho mời Tenant của người khác)
- [ ] AC8: **Reactivation case** — nếu Tenant đã có `user_id` (đã từng
      accept invite trước đó, từ Lease cũ đã terminated và Tenant archived,
      giờ được reactivate qua US-030 AC7/AC8):
  - Nút "Gửi lời mời" đổi thành "Kích hoạt lại tài khoản"
  - Click → **không sinh invite token mới** (vì đã có User account)
  - Thay vào đó: unarchive User account + invalidate mọi refresh token cũ
    + gửi link **reset password** (reuse flow US-003) cho Tenant set
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

---

### US-005: Tenant kích hoạt tài khoản qua invite link

**As a** Tenant nhận được invite link từ Landlord
**I want to** click link và tự set password
**So that** tôi có thể đăng nhập và xem hoá đơn phòng mình

**Priority**: Must
**Estimate**: M
**Depends on**: US-004

**Acceptance Criteria:**

- [ ] AC1: Click link → hệ thống validate token:
  - Token tồn tại trong DB?
  - `used_at` = null?
  - `expires_at` > now?
  - Tenant record còn tồn tại?
- [ ] AC2: Nếu token invalid (bất kỳ lý do nào) → hiện trang "Link không hợp lệ
      hoặc đã hết hạn" với nút "Yêu cầu link mới" (xem US-006)
- [ ] AC3: Nếu token valid → hiện form hoàn tất đăng ký:
  - Email (pre-filled từ Tenant record, không sửa được)
  - Password mới (2 lần, validate như US-001 AC3)
  - Xác nhận SĐT (hiển thị che một phần, VD `090****567`)
    để Tenant confirm đúng người
- [ ] AC4: Submit form → tạo User account với role = `Tenant`, link với
      Tenant record, set password hash, đánh dấu token `used_at = now()`
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

---

### US-007: User đăng xuất

**As a** user đang đăng nhập
**I want to** đăng xuất khỏi hệ thống
**So that** không ai khác dùng được tài khoản của tôi trên device này

**Priority**: Must
**Estimate**: S
**Depends on**: US-002, US-005

**Acceptance Criteria:**

- [ ] AC1: Có nút "Đăng xuất" trong menu tài khoản
- [ ] AC2: Click → invalidate refresh token hiện tại (remove khỏi DB/storage)
- [ ] AC3: Xoá access token và refresh token ở client (localStorage/cookie)
- [ ] AC4: Redirect về trang login

---

### US-008: Refresh JWT access token

**As a** user có session đang dùng
**I want to** token tự động được làm mới khi sắp hết hạn
**So that** tôi không bị đá ra giữa lúc đang dùng app

**Priority**: Must
**Estimate**: M
**Depends on**: US-002

**Acceptance Criteria:**

- [ ] AC1: Endpoint `POST /auth/refresh` nhận refresh token (qua httpOnly cookie
      hoặc body)
- [ ] AC2: Validate refresh token:
  - Còn trong DB (chưa revoke)?
  - Chưa hết hạn (< 7 ngày kể từ lúc login)?
- [ ] AC3: Nếu valid → sinh access token mới (TTL 60 phút), không đổi refresh
      token (hoặc áp dụng refresh token rotation, chốt sau)
- [ ] AC4: Nếu invalid → trả 401, client phải login lại
- [ ] AC5: Frontend interceptor: khi API trả 401 → gọi refresh 1 lần → retry
      request gốc

**Notes:**

- **Refresh token rotation** (cấp refresh mới mỗi lần) bảo mật hơn nhưng
  phức tạp hơn. Quyết định ở Phase 3 (Architecture).
- Refresh token lưu ở đâu (cookie vs localStorage) — quyết định ở Phase 3.

---

### US-009: RBAC — phân quyền theo role

**As a** hệ thống RMS
**I want to** chỉ cho mỗi user thao tác trên dữ liệu của đúng phạm vi role
**So that** Landlord không xem được data của Landlord khác, Tenant không
sửa được gì ngoài thông tin cá nhân

**Priority**: Must
**Estimate**: M
**Depends on**: US-001, US-005

**Acceptance Criteria:**

- [ ] AC1: Mỗi User có field `role` (enum: `landlord`, `tenant`)
- [ ] AC2: JWT payload chứa `user_id` và `role`
- [ ] AC3: Tất cả endpoint yêu cầu authentication (trừ register, login,
      reset password, invite accept)
- [ ] AC4: Landlord chỉ có thể CRUD trên Property/Room/Tenant/Invoice/Lease
      **do chính mình tạo** (scoped by `owner_id`)
- [ ] AC5: Tenant chỉ có thể:
  - Xem thông tin phòng mình thuê
  - Xem hoá đơn của mình
  - Xem hợp đồng của mình
  - Không có quyền tạo/sửa/xoá bất kỳ resource nào (trừ profile cá nhân ở v1.x)
- [ ] AC6: Nếu user truy cập resource không thuộc quyền → trả `403 Forbidden`
- [ ] AC7: Thiết kế code RBAC phải mở: thêm role mới (`manager`, `investor`)
      chỉ cần thêm enum + permission mapping, không phải viết lại logic

**Notes:**

- AC7 là **kiến trúc quan trọng** — sẽ làm rõ hơn ở Phase 2 (một ADR riêng
  về RBAC strategy: role-based vs permission-based vs policy-based)
- MVP: role-based đơn giản. v1.x+: có thể chuyển sang permission-based.

---

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

## Mapping sang Functional Requirements (sẽ viết ở file tiếp theo)

Sau khi approve stories này, ta sẽ dịch sang FR theo format:

```
FR-AUTH-001: Hệ thống phải hash password bằng bcrypt cost ≥ 12 (từ US-001 AC6)
FR-AUTH-002: JWT access token phải có TTL = 60 phút (từ US-002 AC2)
...
```

FR là **phát biểu kỹ thuật dành cho dev**, còn User Story là **phát biểu
giá trị dành cho user**. Cùng nội dung, khác góc nhìn.
