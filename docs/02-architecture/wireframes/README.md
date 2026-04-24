# Wireframe Specs — RMS Phase 3

> **Purpose**: Text specifications để feed vào Claude Design để generate
> low-fidelity wireframes. Mỗi spec độc lập, copy-paste 1 lần/screen.
>
> **Workflow**:
> 1. Mở Claude Design (claude.ai/design)
> 2. Copy nội dung từ `wireframe-NN-<name>.md` làm prompt
> 3. Iterate qua chat/inline comments
> 4. Export PNG + save vào folder này với tên `wireframe-NN-<name>.png`
> 5. Save share link vào README này cho future reference
>
> **Scope Phase 3**: 5 flows critical MVP. Các CRUD screens đơn giản
> (Property list, Service list, Tenant list, etc.) sẽ làm trong Phase 4
> implementation theo shadcn/ui defaults.

---

## 5 Flows Selected

| # | Flow | Why critical |
|---|---|---|
| 01 | Login + Landlord Dashboard Landing | Entry point, sets visual tone |
| 02 | Landlord Dashboard (overview) | Primary daily screen, info density test |
| 03 | Batch Meter Reading | Most complex data entry, batch-per-property UX |
| 04 | Invoice Preview → Commit | Critical workflow, 2-step pattern |
| 05 | Payment Recording | Simplest, validate form patterns |

---

## Design System Notes (for Claude Design prompts)

Khi generate trong Claude Design, include context:

- **Product**: Rental Management System (RMS) cho Vietnamese landlords
- **Primary user**: Landlord quản lý 5-100 phòng
- **Visual style target**: clean, minimal, data-dense; tone professional
  but approachable. Reference aesthetic: shadcn/ui + Linear-like
  information density
- **Locale**: Vietnamese (vi-VN), currency VND, date format DD/MM/YYYY
- **Breakpoint target**: desktop first (1280px+), tablet secondary (768px)
- **Color mode**: light mode only cho MVP
- **Fidelity**: **low-fidelity wireframe** — grayscale boxes, placeholder
  text, no final styling

---

## Specs

- [01-login-dashboard-entry.md](./01-login-dashboard-entry.md)
- [02-landlord-dashboard.md](./02-landlord-dashboard.md)
- [03-meter-reading-batch.md](./03-meter-reading-batch.md)
- [04-invoice-preview-commit.md](./04-invoice-preview-commit.md)
- [05-payment-recording.md](./05-payment-recording.md)

---

**Generated**: 2026-04-25 (Phase 3 Chat 5)
