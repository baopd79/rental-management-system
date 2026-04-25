# Phase 3 Frontend Notes — Wireframe gaps + Hi-fi Reference

> **Purpose**: Document open items từ Deliverable #9 Phase 3 → handoff sang
> Phase 4 (Implementation). Đây là living document, update khi new decisions
> xuất hiện trong Phase 4.
>
> **Created**: 2026-04-25 (Phase 3 Chat 5)
> **Scope**: Phase 4 Frontend implementation team reference
> **Not a replacement for**: ADR-0008 (stack), wireframe specs (behavior)

---

## 1. Wireframe Gaps (defer to Phase 4)

5 wireframes đã generate trong Claude Design (2026-04-25). Review session
log ghi nhận **3 issues** cần fix khi implement thật, không block Phase 3
close.

### 1.1. Wireframe 03 — Meter Reading Batch

**Status**: Generated, main content pass review. Action bar chưa confirm.

**Known issues**:
- ⚠️ **Sticky bottom action bar** ("Lưu nháp" + "Lưu và tiếp tục") không
  thấy trong screenshot. Có thể bị cắt viewport hoặc Claude Design thiếu.
- **Action cho Phase 4**: Implement action bar là **must-have**:
  - Position: sticky bottom, full-width, white bg, top border
  - Left: "Lưu nháp" (secondary variant)
  - Right: "Lưu và tiếp tục" (primary variant, disabled nếu 0 inputs)
  - Mobile: stacked full-width 2 buttons

### 1.2. Wireframe 04 — Invoice Preview → Commit

**Status**: Generated, 2 issues detected.

**Issue A — Missing duplicate row P108 in list**:
- Summary nói "7 hoá đơn sẽ tạo" nhưng list chỉ show 6 invoices
  (P101, P102, P104, P105, P106, P107)
- P108 chỉ được nhắc trong warnings card, không hiện trong invoice list
- **Root cause**: Claude Design hiểu "duplicate → skip" là hidden, không
  render row disabled
- **Action cho Phase 4**: Render duplicate invoices trong list với state:
  - Checkbox disabled (không thể toggle on)
  - Grayscale text + opacity 50%
  - Badge: "DUPLICATE — sẽ bỏ qua"
  - Subtitle: "Đã có hoá đơn [INV-2026-04-0005] tạo ngày 28/4" với link
  - Không có expand action (không show line items)
- **Rationale**: User phải thấy explicit skip để verify. Hidden skip =
  silent bug risk khi debug.

**Issue B — Sticky bottom action bar**:
- Giống wireframe 03, không thấy trong screenshot
- **Action cho Phase 4**: Implement sticky bottom bar với:
  - Left: "Huỷ" (secondary) → navigate back, discard preview
  - Right: "Xác nhận xuất **N** hoá đơn" (primary, dynamic count)
  - N = số invoices checked (update realtime khi toggle)
  - Disabled nếu N = 0

### 1.3. Primary button style inconsistency (cross-screen)

**Observation**: 
- Wireframe 01 (Login) dùng **filled dark** primary button
- Wireframe 02-04 dùng **outlined light** primary buttons
- Không consistent

**Decision cho Phase 4**: 
- **Filled dark** = Primary variant (default). Apply cho mọi primary action.
- **Outlined** = Secondary variant. Apply cho Huỷ, Xem chi tiết, etc.
- **Ghost/text** = Tertiary. Apply cho "Xem", "Quên mật khẩu", inline links.

Reference: shadcn/ui default Button variants (default/secondary/outline/ghost).

---

## 2. Dashboard Hi-fi Reference

Bảo upload hi-fi production reference (pbrental.vn/dashboard) làm visual
guide cho Phase 4 implement. **Không phải copy 1:1** — extract UI patterns
+ information architecture, keep RMS brand + spec.

### 2.1. Patterns to adopt from reference

#### A. "Chu kỳ tháng" funnel card

Visualize workflow landlord đang ở bước nào trong tháng:

```
Đọc chỉ số → Tạo hoá đơn → Đã gửi → Đã thu
 32/48 67%    32/48 67%    28/48 58%  22/48 46%
 [━━━━━░░░]   [━━━━━░░░]   [━━━━░░░░] [━━━░░░░░]
```

**Why add**: Wireframe 02 hiện có "Chưa xuất hoá đơn tháng" nhưng không
show explicit progress. Funnel card này = clearer mental model.

**Implement Phase 4**: 
- Component: 4 progress cards trong grid
- Data: tính từ endpoints:
  - Đọc chỉ số: `count(meter_readings WHERE billing_month=X)` / `count(active_rooms)`
  - Tạo hoá đơn: `count(invoices WHERE billing_month=X AND voided_at IS NULL)` / same denom
  - Đã gửi: same + `sent_at IS NOT NULL` (future field — defer MVP)
  - Đã thu: `count(invoices WHERE status='paid')` / same denom

**MVP simplification**: MVP không có "sent_at" tracking (delivery in-app
only). Card 3 = skip, chỉ render 3 cards (Đọc / Tạo / Thu).

#### B. Month navigator top-right

```
[◀] Tháng 4/2026 [▶]
```

Cho phép landlord xem dashboard quá khứ (ví dụ so sánh T4/2026 vs T3/2026).

**Why add**: Wireframe 02 implicit current month — không cho phép rewind.

**Implement Phase 4**:
- Component: shadcn/ui Select hoặc custom month picker
- Default: current month
- URL sync: `/dashboard?month=2026-04` để share/bookmark
- All queries dashboard filter by selected month

#### C. Stats card delta indicator

```
Doanh thu tháng
127.2 trđ
↑ 8.4% so với tháng trước
```

**Why add**: Trend context cho landlord hiểu doanh thu đang growing/shrinking.

**Implement Phase 4**: 
- Optional cho MVP (không blocking)
- Compute: `(current - previous) / previous * 100`
- Icon: ↑ green nếu positive, ↓ red nếu negative, — nếu flat
- Hover tooltip: absolute delta "+10.2 trđ"

#### D. "Nhà trọ của bạn" per-property table

```
TÊN NHÀ           PHÒNG   LẤP ĐẦY          DOANH THU THÁNG
Trợ Hưng Phú     16/18   [━━━━━━━░] 89%   48.6trđ
Nhà trọ Quận 7   18/20   [━━━━━━━━] 90%   57.2trđ
...
```

**Why add**: Dashboard hiện show aggregate ("3 nhà, 47 phòng"). Per-property
breakdown cho landlord biết nhà nào đang hot/cold.

**Implement Phase 4**:
- Component: shadcn/ui Table với progress bar cell
- Max display: 5 rows + "Xem tất cả (N)" link → full page `/properties`
- Row click → navigate property detail
- Sort: default by revenue DESC

#### E. Hợp đồng sắp hết hạn với day counter badge

```
┌──────┐
│  12  │ Vũ Thanh Mai · HP-105         [Gia hạn]
│ NGÀY │ Hết hạn 01/05/2026
└──────┘
```

**Why add**: Visual urgency mạnh hơn text "hết 20/05/2026" của wireframe 02.

**Implement Phase 4**:
- Badge color grading:
  - ≤ 7 ngày: red background
  - 8-14 ngày: yellow
  - 15-30 ngày: blue
- [Gia hạn] button → route to lease renewal flow (Phase 4 implement)

#### F. Sidebar split với section headers

```
VẬN HÀNH          <- uppercase section header, small gray
  🏠 Tổng quan
  📋 Nhà trọ (3)
  🚪 Phòng (48)
  👥 Khách thuê (67)
  📄 Hợp đồng
  🧾 Hoá đơn (6)  <- red badge

HỆ THỐNG
  ⚡ Dịch vụ
  📊 Báo cáo
```

**Why add**: Flat 6-item nav của wireframe 02 OK cho MVP, nhưng section
grouping scale tốt hơn khi thêm nav items v1.x (Manager, Investor roles).

**Implement Phase 4**:
- 2 sections: "VẬN HÀNH" (daily operations) + "HỆ THỐNG" (settings/reports)
- Item count badge cạnh label (fetch từ counts endpoints)
- Red badge nếu count có urgency (unpaid invoices, overdue)
- MVP nav items mapping:
  - **VẬN HÀNH**: Tổng quan, Nhà trọ, Phòng, Người thuê, Hợp đồng, Hoá đơn
  - **HỆ THỐNG**: Dịch vụ, Cài đặt (Báo cáo defer v1.x)

#### G. Top-level primary action "+ Tạo hoá đơn"

Button primary ở top bar (không phải chỉ trong "Tác vụ nhanh" grid).

**Why add**: Xuất hoá đơn là action critical nhất trong workflow landlord.
Top placement = always accessible, không cần scroll.

**Implement Phase 4**:
- Top bar right side, cạnh bell icon
- Click → route to `/invoices/preview` với property picker
- Shortcut: `N` hoặc `Ctrl+N` (nice-to-have)

#### H. Global search với keyboard shortcut

```
🔍 Tìm phòng, khách, hoá đơn...          [⌘K]
```

**Why add**: Power user shortcut, signal professional tool.

**Implement Phase 4**:
- Component: shadcn/ui Command palette (`cmdk` library)
- Keyboard: `Cmd+K` (Mac) / `Ctrl+K` (Windows)
- Search scope: Room, Tenant, Invoice, Lease (future: Property)
- Endpoint: `GET /api/v1/search?q=X` (add to OpenAPI spec Phase 4 hoặc
  client-side filter cho MVP nếu data nhỏ)

#### I. Personalized greeting

```
Chào buổi sáng, Bảo 👋
Tổng quan tháng 4/2026
Cập nhật lúc 08:42, 19/04/2026
```

**Why add**: Small humanization touch. Wireframe 02 đã có "Xin chào, Anh Nam"
nhưng có thể enhance với time-of-day aware ("Chào buổi sáng" vs "Chào buổi tối").

**Implement Phase 4**:
- Time-aware greeting:
  - 5-11h: "Chào buổi sáng"
  - 11-13h: "Chào buổi trưa"
  - 13-18h: "Chào buổi chiều"
  - 18-22h: "Chào buổi tối"
  - 22-5h: "Chào đêm khuya"
- "Cập nhật lúc X" = `dataUpdatedAt` từ TanStack Query, format relative

### 2.2. Patterns from wireframe 02 to KEEP (reference thiếu)

Đừng bỏ những patterns sau khi port styles:

1. **"Cần chú ý" alert section** — 3 alert cards (expiring leases, overdue
   invoices, monthly billing reminder). Reference không có, **phải giữ**.
2. **"Tác vụ nhanh" quick actions grid** — 4 actions. Reference chỉ có
   "+ Tạo hoá đơn" top right. Giữ grid bottom-left cho discoverability.
3. **"Hoạt động gần đây" feed** — Recent activity log. Reference không có.
   **MVP keep** cho portfolio signal; có thể defer v1.x nếu time-constrained.

### 2.3. Decisions cần chốt Phase 4

Khi implement, Phase 4 dev team phải decide:

| Topic | Options | Recommendation |
|---|---|---|
| Funnel card position | Top / mid / bottom | **Mid** (sau stats, trước alerts) |
| Per-property table | Dashboard hay Properties page? | **Dashboard** (5 rows) + "Xem tất cả" link |
| Activity feed | Keep / defer v1.x | **Keep** portfolio signal |
| Month navigator | Always visible / collapsed | **Always visible** top-right |
| Global search | MVP client-side / server-side | **MVP server-side** (endpoint mới) |

### 2.4. Visual language convention

Adopt từ reference (để UI coherent):

| Element | Style |
|---|---|
| Stat card titles | UPPERCASE, small, gray-500 |
| Stat values | Large, bold, dark |
| Progress bars | `h-2 rounded-full bg-muted` với fill |
| Progress colors | Blue (in-progress), Green (done), Red (overdue) |
| Day counter badges | Square box, large number, "NGÀY" label below |
| Section dividers | `bg-white rounded-xl border shadow-sm p-6` |
| Sidebar headers | UPPERCASE, text-xs, gray-500, tracking-wide |
| Sidebar items | `rounded-lg hover:bg-gray-100` với icon+label |
| Active nav item | `bg-primary/10 text-primary` |
| Red urgency badges | `bg-red-500 text-white rounded-full text-xs` |

---

## 3. What's NOT in this document

- **Specific pixel-level styling**: Phase 4 implement với shadcn/ui defaults,
  không cần pixel spec
- **Component library choice**: Đã chốt ở ADR-0008 (shadcn/ui + Tailwind)
- **State management pattern**: Đã chốt ở ADR-0008 (Zustand + TanStack Query)
- **API endpoints**: Đã chốt ở Deliverable #8 OpenAPI spec
- **Design system tokens**: Define khi Phase 4 setup Tailwind theme

---

## 4. Related Files

- `docs/decisions/ADR-0008-frontend-stack.md` — Stack decisions
- `docs/02-architecture/wireframes/README.md` — Wireframe index
- `docs/02-architecture/wireframes/01-05-*.md` — Wireframe specs
- `docs/02-architecture/wireframes/01-05-*.png` — Wireframe images (Claude Design output)
- `docs/04-api/openapi.yaml` — API contract

---

## 5. Log

| Date | Author | Change |
|---|---|---|
| 2026-04-25 | Bảo + Claude | Initial document. 3 wireframe gaps + dashboard hi-fi reference notes. |

---

**End of Phase 3 Frontend Notes.**
