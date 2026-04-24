# Wireframe 01 — Login + Landlord Dashboard Entry

> **Purpose**: Validate login flow + first impression khi landlord login thành công.
> **Covers**: US-001, US-003
> **Endpoints**: `POST /api/v1/auth/login`, `GET /api/v1/users/me`, redirect to dashboard

---

## Screen 1A: Login Page

### Layout

```
+---------------------------------------------------+
|                                                   |
|              [LOGO / App Name]                    |
|                                                   |
|       "Hệ thống quản lý nhà trọ"                 |
|       (tagline: "Ít công cụ, nhiều hiệu quả")    |
|                                                   |
|       +-----------------------------------+       |
|       | Đăng nhập                         |       |
|       +-----------------------------------+       |
|       |                                   |       |
|       | Email                             |       |
|       | [_______________________________] |       |
|       |                                   |       |
|       | Mật khẩu                          |       |
|       | [_______________________________] |       |
|       |                   [Quên mật khẩu?]|       |
|       |                                   |       |
|       | [ Đăng nhập ] (primary button)   |       |
|       |                                   |       |
|       +-----------------------------------+       |
|                                                   |
|       "Chưa có tài khoản? [Đăng ký]"             |
|                                                   |
+---------------------------------------------------+
```

### Components

- **Center card** (max-width: 400px) on neutral background
- **Logo** placeholder (SVG, square, top center)
- **Tagline** (subtitle below logo)
- **Form card** with border and padding:
  - Card title: "Đăng nhập"
  - Email input (full width, label above)
  - Password input (full width, label above, type=password)
  - "Quên mật khẩu?" link (right-aligned, below password)
  - Primary button: "Đăng nhập" (full width)
- **Footer link**: "Chưa có tài khoản? [Đăng ký]"

### States

| State | What shows |
|---|---|
| Default | Empty form, button disabled until both fields filled |
| Typing | Button enabled when email + password both non-empty |
| Loading | Button shows spinner, text "Đang đăng nhập..." |
| Error | Red alert above form: "Email hoặc mật khẩu không đúng" |
| Locked | Red alert: "Tài khoản tạm khóa. Thử lại sau 5 phút" |

### Interactions

- **Click "Đăng nhập"** → `POST /api/v1/auth/login` với `{email, password}`
  - 200 → save tokens → `GET /api/v1/users/me` → route to `/dashboard`
  - 401 → show error state
  - 429 → show locked state
- **Click "Quên mật khẩu?"** → route to `/forgot-password` (separate wireframe, not covered)
- **Click "Đăng ký"** → route to `/signup` (separate wireframe, not covered)

---

## Screen 1B: Dashboard Entry (first screen after login)

*See `02-landlord-dashboard.md` cho spec đầy đủ. Screen 1B = same as Dashboard main.*

---

## Claude Design Prompt (copy-paste below)

```
Create a low-fidelity wireframe for a login page for "RMS — Rental
Management System", a SaaS tool for Vietnamese landlords managing
5-100 rental rooms.

Layout:
- Centered card on neutral background, max-width 400px
- Above the card: logo placeholder (square, centered) + app name
  "RMS" + tagline "Hệ thống quản lý nhà trọ" + subtitle "Ít công
  cụ, nhiều hiệu quả"
- Card contains:
  - Title: "Đăng nhập"
  - Email input field with label "Email"
  - Password input field with label "Mật khẩu"
  - Right-aligned link: "Quên mật khẩu?"
  - Primary full-width button: "Đăng nhập"
- Below card: "Chưa có tài khoản? [Đăng ký]" link

Style: low-fidelity wireframe, grayscale only, placeholder boxes
for logo, sans-serif font, clean minimal aesthetic similar to
shadcn/ui. No colors, no gradients, no shadows beyond basic card
border.

Locale: Vietnamese UI strings as shown above.

Generate desktop size (1280x800). Show the empty default state.
```

---

## Acceptance Criteria cho wireframe output

- [ ] Layout centered, card visible
- [ ] 2 input fields labeled (Email, Mật khẩu)
- [ ] "Quên mật khẩu?" link visible and right-aligned
- [ ] Primary button "Đăng nhập" full-width in card
- [ ] Logo placeholder visible above card
- [ ] Tagline text visible
- [ ] Footer signup link visible
- [ ] No unnecessary visual elements (no illustrations, no marketing copy)
- [ ] Grayscale only

---

**Export**: Save as `01-login.png` in this folder.
