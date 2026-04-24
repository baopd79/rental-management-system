# Wireframe 02 — Landlord Dashboard (Overview)

> **Purpose**: Validate information architecture cho primary daily screen.
> Landlord mở app mỗi ngày sẽ thấy screen này đầu tiên.
> **Covers**: US-004 (overview), cross-cut với US-055 (expiring leases),
> US-082 (overdue invoices), US-076 (invoice reminder)
> **Endpoints**: multiple summary endpoints + filtered lists

---

## Layout (desktop 1280px)

```
+---------------------------------------------------------------------+
| [Logo] RMS                               [Search] [Bell 3] [Avatar] |  <- Top bar
+--------+------------------------------------------------------------+
|        |                                                            |
| Nav    |  Dashboard                                                 |
| -----  |  ----------------------------------------------------------|
| [@]    |                                                            |
| Tổng   |  +-------------+ +-------------+ +-------------+ +--------+|
| quan   |  | 🏠          | | 👤          | | 📄 Hoá đơn | | 💰    ||
|        |  | 3 nhà trọ   | | 47 phòng    | | 12 chưa    | | 8.5M  ||
| 🏠     |  | 47 phòng    | | thuê / 52   | | thanh toán | | VND   ||
| Nhà    |  +-------------+ +-------------+ +-------------+ +--------+|
| trọ    |                                                            |
|        |  Cần chú ý (Needs attention)                               |
| 👥     |  +------------------------------------------------------+ |
| Người  |  | ⚠️ 3 hợp đồng sắp hết hạn trong 30 ngày              | |
| thuê   |  |   - P101 Nguyễn Văn A, hết 20/05/2026 [Xem]         | |
|        |  |   - P203 Trần Thị B, hết 25/05/2026  [Xem]          | |
| 📄     |  |   - P105 Lê Văn C, hết 02/06/2026    [Xem]          | |
| Hoá    |  +------------------------------------------------------+ |
| đơn    |                                                            |
|        |  +------------------------------------------------------+ |
| 💰     |  | 🔴 2 hoá đơn quá hạn                                 | |
| Thanh  |  |   - P101 Tháng 4/2026, 2.5M VND, trễ 5 ngày  [Xem] | |
| toán   |  |   - P203 Tháng 4/2026, 3.2M VND, trễ 3 ngày  [Xem] | |
|        |  +------------------------------------------------------+ |
| ⚙️      |                                                            |
| Cài    |  +------------------------------------------------------+ |
| đặt    |  | ⏰ Nhắc: chưa xuất hoá đơn tháng 5/2026              | |
|        |  |    Nhà Hoàng Cầu (8 phòng)       [Xuất hoá đơn]     | |
|        |  |    Nhà Láng Hạ (12 phòng)        [Xuất hoá đơn]     | |
|        |  +------------------------------------------------------+ |
|        |                                                            |
|        |  Tác vụ nhanh (Quick actions)                              |
|        |  +------------+ +------------+ +------------+ +---------+ |
|        |  | + Thêm     | | 📝 Nhập    | | 📄 Xuất    | | 💰 Ghi ||
|        |  |   hợp đồng | |   công tơ  | |   hoá đơn  | |  thu  ||
|        |  +------------+ +------------+ +------------+ +---------+ |
|        |                                                            |
|        |  Hoạt động gần đây (Recent activity)                       |
|        |  +------------------------------------------------------+ |
|        |  | Hôm nay                                              | |
|        |  | • 10:30 - Ghi thanh toán P205 tháng 4 (2.8M)        | |
|        |  | • 09:15 - Tạo hợp đồng mới P108 (Nguyễn Văn D)      | |
|        |  | Hôm qua                                              | |
|        |  | • 18:42 - Nhập công tơ Nhà Hoàng Cầu (tháng 4)      | |
|        |  | • 14:20 - Xuất hoá đơn Nhà Láng Hạ tháng 4 (12 HĐ)  | |
|        |  +------------------------------------------------------+ |
|        |                                                            |
+--------+------------------------------------------------------------+
```

---

## Zones breakdown

### Zone 1: Top bar (full width, sticky)

- **Logo + app name** (left)
- **Global search** (center, hidden mobile) — search Tenant/Room/Invoice
- **Notifications bell** with unread badge (count from `GET /api/v1/notifications` unread_count)
- **User avatar dropdown** (right) — Profile, Settings, Logout

### Zone 2: Sidebar navigation (left, collapsible)

Icons + labels:
- Tổng quan (Dashboard) — *active state*
- Nhà trọ (Properties)
- Người thuê (Tenants)
- Hoá đơn (Invoices)
- Thanh toán (Payments)
- Cài đặt (Settings)

Nav item có:
- Icon (Lucide icon OK)
- Label (có thể collapse để còn icon)
- Active state (background highlight)

### Zone 3: Main content area

#### 3.1: Stats cards row (4 cards)

Mỗi card:
- Icon top-left
- Big number
- Label
- (Optional) delta vs last period

Cards content:
1. **Nhà trọ**: `3 nhà`, subtitle `47 phòng`
2. **Tỷ lệ lấp đầy**: `47/52 phòng` = `90%`
3. **Hoá đơn chưa thanh toán**: `12 invoice` (includes partial)
4. **Doanh thu tháng**: `8.5M VND` received

#### 3.2: "Cần chú ý" section (Needs attention)

Ba nhóm alerts với icon khác nhau:

**A. Expiring leases** (yellow warning)
- Title: "⚠️ X hợp đồng sắp hết hạn trong 30 ngày"
- List: max 3 items với `[Xem]` action
- Click → route to Lease detail

**B. Overdue invoices** (red alert)
- Title: "🔴 X hoá đơn quá hạn"
- List: max 5 items với amount + days overdue + `[Xem]`
- Click → route to Invoice detail

**C. Pending monthly billing** (blue info)
- Title: "⏰ Chưa xuất hoá đơn tháng <month>/<year>"
- List: per property với room count + `[Xuất hoá đơn]` button
- Click button → route to Invoice batch preview screen (wireframe 04)

#### 3.3: Quick actions row (4 buttons)

Primary actions, icon + label:
- `+ Thêm hợp đồng` → Lease create
- `📝 Nhập công tơ` → Meter reading batch (wireframe 03)
- `📄 Xuất hoá đơn` → Invoice batch preview (wireframe 04)
- `💰 Ghi thu` → navigate to invoice selection for payment

#### 3.4: Recent activity feed

Grouped by day:
- **Hôm nay** (Today)
- **Hôm qua** (Yesterday)
- **<N> ngày trước** (older, collapse after 5 items)

Each item: time · action description · (optional) link

Feed nguồn: audit log filtered by current landlord (last 10 events).

---

## States

| State | What shows |
|---|---|
| Initial load | Skeleton loaders cho stats cards + list sections |
| Empty (new landlord) | Stats = 0, no alerts, CTA "Tạo nhà trọ đầu tiên" |
| Loaded | Full content as layout |
| Partial error | Individual section shows error, others load OK |

---

## API calls (parallel on mount)

```
GET /api/v1/properties?page=1&limit=100         # count + rooms
GET /api/v1/leases?status__in=expiring_soon     # expiring alert
GET /api/v1/invoices?status__in=unpaid,partial&overdue=true  # overdue
GET /api/v1/notifications?is_read=false         # badge count
GET /api/v1/audit-logs?limit=10                 # activity feed
```

Note: "Chưa xuất hoá đơn tháng này" logic = computed client-side
(compare billing_day of current month vs existing invoices).

---

## Claude Design Prompt (copy-paste below)

```
Create a low-fidelity wireframe for a landlord dashboard in "RMS"
(Rental Management System for Vietnamese landlords).

Layout (desktop 1280x900):

1. Top bar (sticky, full width):
   - Left: logo placeholder + "RMS" text
   - Center: search input with placeholder "Tìm kiếm..."
   - Right: bell icon with badge "3", avatar circle

2. Left sidebar (220px wide, icon + label nav):
   - "Tổng quan" (active, highlighted)
   - "Nhà trọ"
   - "Người thuê"
   - "Hoá đơn"
   - "Thanh toán"
   - "Cài đặt"

3. Main content:
   a. Page title "Dashboard"
   b. Row of 4 stats cards:
      - "3 nhà trọ / 47 phòng"
      - "47/52 phòng cho thuê (90%)"
      - "12 hoá đơn chưa thanh toán"
      - "8.5M VND doanh thu tháng này"
   c. Section "Cần chú ý" with 3 alert cards stacked:
      - Yellow: "3 hợp đồng sắp hết hạn" with 3 list items + [Xem]
      - Red: "2 hoá đơn quá hạn" with 2 list items + amount + [Xem]
      - Blue: "Chưa xuất hoá đơn tháng 5/2026" with 2 property
        rows + [Xuất hoá đơn] buttons
   d. Section "Tác vụ nhanh": 4 icon+label cards:
      - "+ Thêm hợp đồng"
      - "📝 Nhập công tơ"
      - "📄 Xuất hoá đơn"
      - "💰 Ghi thu"
   e. Section "Hoạt động gần đây" (feed grouped by day):
      - "Hôm nay" header + 2 items with time + description
      - "Hôm qua" header + 2 items

Style: low-fidelity wireframe, grayscale, placeholder text
for data, boxes for icons, clean hierarchy with clear section
dividers. Reference shadcn/ui information density. No colors
except minimal accent for alert severity (can use grayscale
with different border weights instead of colors).

Locale: Vietnamese UI as shown.
```

---

## Acceptance Criteria

- [ ] Top bar visible with logo, search, bell, avatar
- [ ] Sidebar visible with 6 nav items, "Tổng quan" active
- [ ] 4 stats cards in single row
- [ ] "Cần chú ý" section with 3 distinct alert cards
- [ ] "Tác vụ nhanh" section with 4 action cards
- [ ] "Hoạt động gần đây" section with day grouping
- [ ] Information density comparable to Linear/Notion (not sparse)
- [ ] Grayscale, no decorative elements
- [ ] Hierarchical typography (size + weight differentiation)

---

**Export**: Save as `02-dashboard.png` in this folder.
