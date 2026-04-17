# Phase 2 — Gate Review (Level 2: Full Requirements Review)

> **Review Date**: 2026-04-18
> **Phase Status**: 5/8 groups drafted
> **Reviewer**: Claude (as Senior Engineer)
> **Review Scope**: Level 2 — Cross-reference, RBAC, Data flow, Naming convention
> **Approver**: Bảo
> **Resolution Status**: Patches applied via PHASE2-REVIEW-PATCHES.md on 2026-04-18

---

## Executive Summary

**Overall Health**: 🟢 Good — ready to proceed to Nhóm 6 với một số follow-up.

**Completed Groups:**

| # | Group | Stories | Status | File |
|---|---|---|---|---|
| 1 | Auth & RBAC | 8 (US-001 → US-009, skip US-006) | DRAFT | `01-auth-rbac.md` |
| 2 | Property & Room | 9 (US-010 → US-018) | DRAFT | `02-property-room.md` |
| 3 | Tenant & Occupant | 9 (US-030 → US-038) | DRAFT | `03-tenant.md` |
| 4 | Lease | 10 (US-050 → US-059) | DRAFT | `04-lease.md` |
| 5 | Service | 7 (US-060 → US-066) | DRAFT | `05-service.md` |

**Pending Groups:**

| # | Group | Expected Stories | Blocking? |
|---|---|---|---|
| 6 | Meter Reading | ~5-6 | Nhóm 7 |
| 7 | Invoice | ~8-10 | Nhóm 8 |
| 8 | Payment | ~4-5 | none |

**Total stories drafted**: 43 / ~60 expected (~72%)

**Findings Summary:**
- 🔴 **Critical**: 2 issues
- 🟡 **Should fix**: 5 issues
- 🟢 **Nice to have**: 3 observations
- ✅ **Strengths**: 4 patterns done well

---

## 1. Critical Issues (🔴 Must fix before Nhóm 6)

### 🔴 C1: US-017 (Room status) mâu thuẫn với Lease status definitions

**Location**: `02-property-room.md` US-017 AC2 vs `04-lease.md` Lease Lifecycle

**Vấn đề:**

Nhóm 2 US-017 AC2 define Room status derive từ Lease:

```
> 30 ngày  → 'occupied'
≤ 30 ngày  → 'expiring_soon'
end_date < today → 'lease_expired'
```

Nhưng Nhóm 4 define Lease.status với mốc thời gian **khác**:

```
active        → start_date ≤ today ≤ (end_date - 30 days)
expiring_soon → (end_date - 30 days) < today ≤ end_date
expired       → today > end_date
```

**Conflict cụ thể:**

Tình huống: Lease end_date = 30/6, today = 25/6. Còn 5 ngày.
- Theo Nhóm 2: Room.status = `expiring_soon` ✓
- Theo Nhóm 4: Lease.status = `expiring_soon` ✓

OK trường hợp này khớp. Nhưng:

Tình huống: Lease end_date = 30/6, today = 1/7. Quá hạn 1 ngày.
- Theo Nhóm 2: Room.status = `lease_expired`
- Theo Nhóm 4: Lease.status = `expired` (KHÔNG có `lease_expired`)

**Naming inconsistency:** Room gọi là `lease_expired`, Lease gọi là `expired`.

**Impact:**
- Code sau này sẽ confuse: `if room.status == 'lease_expired'` vs `if lease.status == 'expired'`
- Developer dễ viết bug: map sai giữa 2 enum
- UX confuse: badge Room hiện "Hợp đồng hết hạn" màu đỏ, badge Lease cùng lúc hiện "Đã hết hạn" — 2 chỗ gọi tên khác

**Recommendation:**

**Option A**: Unify naming. Room.status = `lease_expired` → đổi Lease.status = `expired` → cả 2 chỗ dùng cùng enum.

**Option B**: Room.status derive 1-1 từ Lease.status:
```
Lease.status = 'active'         → Room.status = 'occupied'
Lease.status = 'expiring_soon'  → Room.status = 'expiring_soon'
Lease.status = 'expired'        → Room.status = 'lease_expired' (Room context rõ hơn)
Lease.status = 'terminated'     → Room.status = 'vacant' (nếu không có Lease khác)
không có Lease                  → Room.status = 'vacant'
```

**Khuyến nghị: Option B** — giữ naming khác nhau có chủ ý (Room context khác Lease context) nhưng map rõ ràng 1-1. Update US-017 AC2 để reference Lease.status thay vì tính lại từ date.

**Action:**
- [ ] Update `02-property-room.md` US-017 AC2 để derive từ Lease.status
- [ ] Cross-reference với `04-lease.md` Lease Lifecycle
- [ ] Update `glossary.md` để clarify 2 status là khác nhau về context

---

### 🔴 C2: Invite flow (US-004/US-005) không handle case Tenant đã tồn tại User record

**Location**: `01-auth-rbac.md` US-004, US-005

**Vấn đề:**

Nhóm 3 US-030 AC7/AC8 cho phép "kích hoạt lại" Tenant archived (reactivate).
Nếu Tenant cũ đã có `user_id` (đã từng accept invite) và bị archived →
reactivate thì User record cũ còn đó.

Nhóm 1 US-004 chỉ handle "Tenant chưa có User account". Không có AC cho case:
- Tenant reactivated, đã có User record cũ
- Landlord click "Mời vào app" → có sinh invite token mới không?
- Nếu click → Tenant click link → US-005 AC4 "tạo User account" fail vì
  đã tồn tại?

**Impact:**
- Bug runtime khi Tenant cũ quay lại thuê
- Logic mơ hồ: password cũ có giữ không? Tenant có login được luôn không?

**Recommendation:**

Thêm AC vào US-004 và US-005:

**US-004 AC mới:**
```
AC8: Nếu Tenant đã có User record (`user_id IS NOT NULL`, trường hợp
     reactivate từ archived):
     - Không sinh invite token mới
     - Nút "Mời vào app" đổi thành "Reactivate account"
     - Click → unarchive User + invalidate session cũ (nếu có) + gửi
       forgot-password link để Tenant set password mới
```

**US-005 AC mới:**
```
AC6: Nếu Tenant đã có User account → redirect sang flow forgot password
     thay vì tạo account mới
```

**Action:**
- [ ] Update `01-auth-rbac.md` US-004, US-005 với case reactivation
- [ ] Update `03-tenant.md` US-030 AC8 reference flow mới
- [ ] Cân nhắc: có nên tách riêng US "Reactivate Tenant account" không?

---

## 2. Should Fix Issues (🟡 Nên fix trước khi close Phase 2)

### 🟡 S1: Inconsistent naming: `is_archived` vs `is_active`

**Location**: Cross-cutting

| Entity | Field | Meaning |
|---|---|---|
| Room | `is_archived` | Soft delete marker |
| Tenant | `is_archived` | Soft delete marker |
| Occupant | `moved_out_date` (không có is_archived) | Moved out marker |
| Service | `is_active` | Enable/disable marker (không phải soft delete) |
| User | (chưa định nghĩa) | ? |

**Vấn đề:** Service dùng `is_active` nghĩa "đang bật/tắt" — **không phải soft delete**. Nhưng dev mới đọc code có thể nhầm lẫn với `is_archived` ở Room/Tenant.

**Recommendation:**

Giữ nguyên 2 concept nhưng document rõ trong Phase 3 ADR:

| Concept | Field name | Semantics | Entities |
|---|---|---|---|
| Soft delete | `is_archived` + `archived_at` | Record "đi", không còn active trong flow | Room, Tenant |
| Feature toggle | `is_active` | Record tồn tại, tạm bật/tắt | Service |

**Action:**
- [ ] Viết ADR-0001 "Naming convention for lifecycle fields" khi vào Phase 3
- [ ] Không cần sửa stories hiện tại, chỉ cần document

---

### 🟡 S2: Cron job design pattern chưa thống nhất

**Location**: `03-tenant.md` (implicit), `04-lease.md` US-057, `02-property-room.md` US-017 AC5

**Vấn đề:**

3 chỗ nhắc đến cron daily nhưng mô tả khác nhau:

1. **Nhóm 2 US-017 AC5**: "Cron job hằng ngày (00:00) tự động chuyển Lease status từ `active` → `expired`"
   - Nhưng Nhóm 4 nói Lease.status là **computed**, không lưu DB!

2. **Nhóm 3**: nhắc "cron daily cho Tenant status" nhưng không có US riêng

3. **Nhóm 4 US-057**: Cron 00:05 cho Lease transition, mô tả đầy đủ nhất

**Contradictions:**

- Nhóm 2 nói cron **UPDATE** Lease.status (implies stored)
- Nhóm 4 nói Lease.status là **computed**, cron chỉ để trigger notifications
- Nhóm 3 không có US riêng cho cron Tenant

**Impact:**
- Dev không biết cron làm gì thật sự
- Phase 3 Architecture sẽ khó design đúng

**Recommendation:**

Consolidate thành **1 cron job duy nhất** với nhiều sub-tasks:

```
Daily Status Maintenance Cron (00:05):
  1. Check Lease transitions → trigger notifications (no DB update)
  2. Check Tenant status changes → trigger notifications
  3. Room status: không cần (computed on query)
  4. Log: số records checked, notifications triggered
```

**Action:**
- [ ] Fix `02-property-room.md` US-017 AC5: remove "UPDATE Lease status", thay bằng reference US-057
- [ ] Viết thêm US trong Nhóm 3 cho Tenant status cron (hoặc gộp vào US-057)
- [ ] Ở Phase 3: viết ADR "Cron job architecture"

---

### 🟡 S3: User-Tenant relationship mơ hồ

**Location**: `03-tenant.md` DB preview

**Vấn đề:**

```
Tenant:
  id, landlord_id (FK → User role=landlord),
  user_id (FK → User role=tenant, nullable),
  ...
```

Câu hỏi chưa trả lời:
- Nếu Landlord cũng là User (có account riêng), tại sao `landlord_id` không là `user_id` với role scope?
- User có thể vừa là Landlord vừa là Tenant không? (VD: Bảo cho thuê nhà mình, đồng thời đi thuê nhà người khác)
- FK constraint với role check: làm thế nào để đảm bảo `landlord_id` FK vào User có role=landlord?

**Impact:**
- Phase 3 DB design sẽ phải làm lại nếu case "1 user 2 role" thành sự thật
- Security concern: cross-role data leakage

**Recommendation:**

Thêm vào Open Questions của Nhóm 1:

```
Q: User có thể có nhiều role không?
  Option A: 1 user = 1 role (MVP, đơn giản)
  Option B: User có list roles[]  (phức tạp)
  Option C: Tách User (auth) và Profile (Landlord/Tenant record)
```

**Khuyến nghị MVP**: Option A. Bảo có thể đăng ký 2 account riêng nếu cần
(1 email Landlord, 1 email Tenant).

**Action:**
- [ ] Thêm Open Question vào `01-auth-rbac.md`
- [ ] Confirm với Bảo: 1 user 1 role cho MVP?

---

### 🟡 S4: Vision feature #8 (Tenant view hoá đơn) chưa có US dedicated

**Location**: Vision scope vs current stories

**Vision MVP features map:**

| # | Vision Feature | Stories covering |
|---|---|---|
| 1 | Quản lý nhà | US-010 → US-013 |
| 2 | Quản lý phòng | US-014 → US-017 |
| 3 | Quản lý khách thuê | US-030 → US-036 |
| 4 | Cấu hình dịch vụ | US-060 → US-066 |
| 5 | Ghi chỉ số điện/nước | **Nhóm 6 (pending)** |
| 6 | Tự động tính hoá đơn | **Nhóm 7 (pending)** |
| 7 | Xem hoá đơn | **Nhóm 7 (pending)** |
| 8 | Đánh dấu thanh toán | **Nhóm 8 (pending)** |
| 9 | Hợp đồng cơ bản | US-050 → US-059 |
| 10 | Authentication | US-001 → US-007 |
| 11 | RBAC | US-009 |

**Observation:** Tất cả features đã có plan rõ. Không miss feature nào.

**Nhưng:** Tenant-facing stories phân tán:
- US-018 (xem phòng) — Nhóm 2
- US-037, US-038 (xem profile, Occupant) — Nhóm 3
- US-059 (xem Lease) — Nhóm 4
- US-066 (xem Service) — Nhóm 5

Khi Tenant dùng app, họ không biết các tính năng này thuộc "Nhóm" nào. Lược lại tổng hợp **Tenant journey** đầy đủ:

1. Accept invite (US-005)
2. Login (US-002 — nhưng chỉ cover Landlord, cần extend cho Tenant)
3. View dashboard với: phòng, Lease, Service, Occupants
4. View Invoice (Nhóm 7 pending)
5. Update profile (US-037)

**Recommendation:**

Sau khi xong Nhóm 7, 8 → viết 1 doc riêng `TENANT-JOURNEY.md` map toàn bộ touchpoints của Tenant.

**Action:**
- [ ] Add to backlog: viết `TENANT-JOURNEY.md` ở cuối Phase 2
- [ ] Update `01-auth-rbac.md` US-002: clarify Tenant cũng dùng cùng endpoint login

---

### 🟡 S5: US-066 (Tenant xem Service) có thể refactor chung với dashboard

**Location**: `05-service.md` US-066

**Observation:** US-066 là "section trên dashboard Tenant", nhưng chưa có US nào define full dashboard Tenant. Có nguy cơ:
- Mỗi nhóm design 1 mảnh dashboard riêng → UI rời rạc
- Tenant journey thiếu holistic view

**Recommendation:**

Ở Phase 3 (Architecture), cần 1 wireframe/mockup tổng cho Tenant dashboard.
Hiện tại giữ nguyên các US, nhưng note để Phase 3 consolidate.

**Action:**
- [ ] Note trong Phase 3 checklist: design Tenant dashboard holistic

---

## 3. Nice to Have (🟢 Observations)

### 🟢 N1: Audit log mentioned nhiều nơi nhưng chưa có design

**Locations:**
- US-004, US-052, US-063: đều nhắc "audit log: ghi lại ai sửa, khi nào"
- Không có US riêng, không có table design

**Observation:** Audit log là **cross-cutting concern**. Nên có ADR riêng ở Phase 3.

**Suggested ADR topics:**
- Audit scope: mọi write operation hay chỉ critical?
- Storage: cùng DB hay separate?
- Retention: bao lâu?

Không cần fix ngay, note cho Phase 3.

---

### 🟢 N2: Notification pattern lặp lại nhiều lần

**Locations:**
- US-057 AC4: Lease status change → notification (v1.x)
- US-058: Dashboard widget "Hợp đồng cần chú ý"
- US-032 AC4: "Landlord được thông báo khi Tenant sửa info"

**Observation:** Tất cả đều defer đến v1.x, nhưng có thể design pattern chung:

```
NotificationChannel:
  - in_app_badge (MVP)
  - email (v1.x)
  - push_notification (v1.x)
  - zalo_oa (v2.x)

NotificationTrigger:
  - lease_expiring_soon
  - lease_expired
  - tenant_info_updated
  - invoice_created
  - invoice_overdue
  ...
```

**Observation only** — không cần action ngay, note cho v1.x planning.

---

### 🟢 N3: Priority distribution hơi Must-heavy

**Stats:**

| Priority | Count | % |
|---|---|---|
| Must | 33 | 77% |
| Should | 8 | 19% |
| Could | 2 | 5% |

**Observation:** 77% Must có thể overload MVP scope. So sánh với tiêu chuẩn industry (50-60% Must cho MVP), đang hơi aggressive.

**Suggestion for consideration:**

Cân nhắc demote một số Must → Should:
- US-022 audit log features (nếu có) → Should
- US-054 (Renewal) — đã là Should ✓
- US-007 logout — có thể là Should (MVP minimal: browser tab close = logout)

Không cần action ngay, note để khi plan sprint Bảo cân đối.

---

## 4. Strengths (✅ Patterns done well)

### ✅ P1: Invoice Immutability Pattern — internalized sớm

Phát hiện ở Nhóm 5 (Q3 thảo luận), áp dụng rõ ở US-063 AC5, US-064 AC5. Pattern này sẽ là **xương sống** của Nhóm 7 (Invoice). Ghi nhận Bảo đã nắm pattern chỉ qua 1 câu tư duy về Tenant đổi tên.

### ✅ P2: Computed status pattern nhất quán

Room.status, Tenant.status, Lease.status đều là computed — không lưu DB (trừ `terminated_at` cho Lease). Pattern này:
- Tránh bug "status lệch data thật"
- Simplify UPDATE logic
- Centralize business rule ở 1 chỗ (compute function)

Áp dụng ở 3 nhóm khác nhau → đã thành convention của project.

### ✅ P3: Landlord dùng date fields làm công cụ chính sách

Thể hiện ở Nhóm 4 pro-rata (start_date, terminated_date). Nguyên tắc
**"đẩy flexibility ra input thay vì business logic"** đã được Bảo nắm và
áp dụng nhất quán.

### ✅ P4: Dependency chain clean

Không có circular dependency giữa các nhóm:
```
Nhóm 1 (Auth) ──→ Nhóm 2 (Property) ──→ Nhóm 3 (Tenant) ──→ Nhóm 4 (Lease)
                      └──→ Nhóm 5 (Service)
                                          └──→ Nhóm 4 ──→ Nhóm 6 (Meter) ──→ Nhóm 7 (Invoice) ──→ Nhóm 8 (Payment)
```

Mỗi nhóm có "Depends on" và "Blocks" rõ ràng → implementation order đã clear.

---

## 5. Data Flow Verification

### Landlord journey (end-to-end)

```
1. Signup (US-001) ✓
2. Login (US-002) ✓
3. Create Property (US-010) ✓
4. Create Room (US-014) ✓
5. Create Service (US-060/US-061) ✓
6. Create Tenant (US-030) ✓
7. Invite Tenant (US-004) ✓
8. Create Lease (US-050) ✓
9. [Nhóm 6] Record meter reading → PENDING
10. [Nhóm 7] Generate invoice → PENDING
11. [Nhóm 8] Mark payment → PENDING
12. Terminate Lease (US-055) ✓
13. Settle deposit (US-056) ✓
14. Archive Tenant (US-033) — auto triggered by US-056 ✓
```

**Assessment:** Flow liền mạch cho 8/11 steps. 3 steps pending trong Nhóm 6-8.

### Tenant journey (end-to-end)

```
1. Receive invite link (US-004 — Landlord triggers) ✓
2. Accept invite + set password (US-005) ✓
3. Login (US-002 — chưa confirm covered cho Tenant, see S4) 🟡
4. View dashboard:
   - View Room (US-018) ✓
   - View Lease (US-059) ✓
   - View Occupants (US-038) ✓
   - View Services (US-066) ✓
   - View Invoices → PENDING Nhóm 7
5. View profile (US-037) ✓
6. Update profile (US-037) ✓
```

**Assessment:** Tenant journey cơ bản đã cover, chỉ thiếu Invoice view.

---

## 6. Terminology Alignment (Glossary Check)

**Glossary terms and their usage:**

| Glossary Term (VI/EN) | Used consistently? | Notes |
|---|---|---|
| Property / Nhà trọ | ✓ | |
| Room / Phòng | ✓ | |
| Lease / Hợp đồng | ✓ | |
| Service / Dịch vụ | ✓ | |
| Meter Reading / Chỉ số | Chưa dùng (pending Nhóm 6) | |
| Invoice / Hoá đơn | Chưa dùng (pending Nhóm 7) | |
| Payment / Thanh toán | Chưa dùng (pending Nhóm 8) | |
| Deposit / Tiền cọc | ✓ | |
| Rent / Tiền phòng | ✓ | |
| Landlord / Chủ nhà | ✓ | |
| Tenant / Người thuê | ✓ | |

**Missing from glossary** (nên add):
- Occupant — người ở cùng (định nghĩa trong Nhóm 3 nhưng chưa vào glossary)
- billing_type values (per_meter / per_person / fixed)
- Lease status values (draft / active / expiring_soon / expired / terminated)

**Action:**
- [ ] Update `glossary.md` thêm Occupant, billing_type, status enums

---

## 7. Readiness Checklist for Nhóm 6 (Meter Reading)

Trước khi bắt đầu Nhóm 6, các prerequisites:

- [x] Service.billing_type = 'per_meter' được định nghĩa (Nhóm 5)
- [x] Service.scope (all_rooms / selected_rooms) được định nghĩa (Nhóm 5)
- [x] Invoice Immutability Pattern được document (Nhóm 5)
- [x] Lease lifecycle (để biết reading gắn với Lease active nào) (Nhóm 4)
- [ ] **Blocker**: Fix C1 (Room/Lease status naming) — ảnh hưởng query "Room nào cần đọc chỉ số tháng này"
- [ ] **Blocker**: Fix C2 (invite reactivation) — không ảnh hưởng trực tiếp Nhóm 6 nhưng gây nợ tech
- [ ] Open questions Nhóm 4-5 đã chốt hết (Bảo confirm)

**Recommendation:** Fix C1 trước khi sang Nhóm 6. C2 có thể defer đến cuối Phase 2.

---

## 8. Action Items Summary

**Priority order:**

### Before Nhóm 6 (Must)

1. [x] **Fix C1**: Update `02-property-room.md` US-017 AC2 để derive Room.status từ Lease.status 1-1 ✅ 2026-04-18
2. [x] Update `glossary.md` để document cả Room và Lease status enums ✅ 2026-04-18

### Before Phase 2 close (Should)

3. [x] **Fix C2**: Add reactivation flow vào US-004, US-005 ✅ 2026-04-18
4. [ ] **Fix S1**: Không cần sửa stories, ghi ADR-0001 ở Phase 3 (deferred to Phase 3)
5. [x] **Fix S2**: Consolidate cron jobs, fix `02-property-room.md` US-017 AC5 ✅ 2026-04-18
6. [x] **Fix S3**: Add Open Question về multi-role vào `01-auth-rbac.md` ✅ 2026-04-18
7. [x] Update `glossary.md` thêm Occupant, billing_type ✅ 2026-04-18

### After Phase 2 close (Nice)

8. [ ] Viết `TENANT-JOURNEY.md` map toàn bộ touchpoints của Tenant
9. [ ] Phase 3 ADR: Audit log architecture
10. [ ] Phase 3 ADR: Notification framework
11. [ ] Phase 3 ADR: Naming convention (is_archived vs is_active)
12. [ ] Cân nhắc demote một số `Must` → `Should` khi plan sprint

---

## 9. Sign-off Criteria

Phase 2 có thể close khi:

- [x] 8/8 nhóm có stories draft
- [ ] Tất cả Critical issues (🔴) đã fix
- [ ] Tất cả Open Questions trong mỗi nhóm đã chốt
- [ ] Glossary đầy đủ terms
- [ ] CHANGELOG đầy đủ
- [ ] Bảo review và approve toàn bộ

**Current status**: 5/8 nhóm → **~62% ready for Phase 2 close**.

---

## Appendix: Stories Count Summary

| Nhóm | Stories | Must | Should | Could | L | M | S |
|---|---|---|---|---|---|---|---|
| 1. Auth | 8 | 8 | 0 | 0 | 0 | 5 | 3 |
| 2. Property | 9 | 8 | 1 | 0 | 0 | 5 | 4 |
| 3. Tenant | 9 | 5 | 3 | 1 | 1 | 3 | 5 |
| 4. Lease | 10 | 7 | 3 | 0 | 3 | 4 | 3 |
| 5. Service | 7 | 5 | 1 | 1 | 1 | 1 | 5 |
| **Total** | **43** | **33** | **8** | **2** | **5** | **18** | **20** |

**Estimate** (S=0.5 day, M=2 days, L=4 days):
- Total: 20×0.5 + 18×2 + 5×4 = **66 dev-days** ≈ 13 weeks solo
- Plus Nhóm 6-8 (~17 stories, ~25 dev-days) → **~91 dev-days** ≈ 18 weeks

Vision ước lượng "8–10 sprint" (10 tuần). Actual có thể **gấp 1.8x** estimate ban đầu. Cần Bảo cân nhắc:
- Scope cut (demote Must → Should)
- Extend timeline (OK nếu side project)
- Parallelize (impossible với solo dev)

---

## Review Sign-off

- [ ] Reviewed by Bảo: _______________
- [ ] Date: _______________
- [ ] Action items approved: _______________
- [ ] Ready to proceed to Nhóm 6: _______________
