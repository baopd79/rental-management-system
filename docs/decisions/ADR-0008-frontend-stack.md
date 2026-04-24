# ADR-0008: Frontend Stack

> **Status**: Accepted
> **Date**: 2026-04-25
> **Deciders**: Bảo, Claude (as Senior Architect)
> **Supersedes**: Vision.md Section 7 placeholder ("Frontend: TBD")

---

## Context

Phase 2 chốt 11 MVP features cần UI cho Landlord (primary) và Tenant
(invite-only). Phase 3 Deliverable #8 hoàn thành OpenAPI spec với 71
endpoints. Phase 3 Deliverable #9 yêu cầu chốt frontend stack trước
khi implement Phase 4.

**Constraints ràng buộc chọn stack**:

1. **Portfolio-to-internship goal**: Bảo mục tiêu intern 6-9 tháng tới.
   Stack phải có job market signal cao ở VN.
2. **Solo developer**: Không có design team, không có senior FE mentor.
   Stack phải DX tốt, docs rõ, community mạnh để self-learn.
3. **API-first contract**: Backend OpenAPI 3.0 spec đã ready →
   frontend phải consume type-safe để tránh drift.
4. **Scale MVP**: 5-100 phòng / landlord, <10 concurrent users.
   Không cần hyper-optimize bundle size / SSR / edge runtime.
5. **Extensibility**: MVP web-only, v1.x có thể thêm native mobile
   (React Native), v2.x thêm Manager/Investor roles.
6. **Time to first screen**: Phase 4 implementation sẽ chia sprint
   per feature. Stack phải lean enough để 1 feature xong trong 1 sprint.

---

## Decision

Adopt **React 19 + TypeScript + Vite** làm foundation, bổ sung 10
libraries/tools curated cho từng concern cụ thể (routing, data fetching,
state, UI, forms, HTTP, codegen, testing, linting).

Tổng cộng **11 decisions** được consolidate trong ADR duy nhất này.

---

## Detailed Decisions

### D1. Platform Scope

**Choice**: Web-only cho MVP.

**Alternatives considered**:
- **PWA** (Progressive Web App): thêm offline + install-to-home-screen
- **Native mobile** (React Native / Flutter): native UX per platform

**Rationale**:
- MVP workflow: Landlord ngồi desktop/tablet, Tenant xem invoice qua
  link Zalo mở web mobile → standard web đủ.
- PWA chỉ tăng value khi có offline use case → landlord Nhập meter
  reading ở site không wifi không phải blocker (MVP: làm ở nhà sau).
- Native mobile định hướng v1.x khi có users feedback đủ.

**Consequences**:
- Responsive design (mobile-first) là must-have.
- Không cần service worker, không cần app store signing.

---

### D2. Rendering Mode

**Choice**: SPA (Single Page Application).

**Alternatives considered**:
- **SSR/SSG** (Next.js, Nuxt): server-render first paint, SEO-ready
- **Server-rendered HTML** (HTMX + FastAPI templates): progressive enhancement

**Rationale**:
- RMS là app nội bộ, không cần SEO (không có public marketing page
  trong MVP).
- JWT auth với refresh token rotation (ADR-0007) hoạt động clean với
  SPA: access token in-memory, refresh token trong HttpOnly cookie.
  SSR phức tạp hơn vì phải handle auth context cả server lẫn client.
- HTMX approach loại bỏ option dùng React Native v1.x (HTMX chỉ
  work với HTML response).
- SPA đơn giản nhất cho solo dev.

**Consequences**:
- Phải handle loading states / skeleton UI manually (không có SSR
  fallback).
- SEO không phải vấn đề (invoice/tenant data private).
- Initial bundle size lớn hơn (~200KB gzipped acceptable).

---

### D3. Framework

**Choice**: **React 19** (stable release từ 2025).

**Alternatives considered**:
- **Vue 3**: DX friendly, VN community mạnh
- **Svelte 5**: Compile-time, ít boilerplate
- **SolidJS**: React-like với fine-grained reactivity

**Rationale**:
- Job market VN: React dominant ở posting intern (>80% mentions theo
  survey TopDev/ITViec 2025-2026).
- Ecosystem cho admin-style UI (table/form/modal) mature nhất qua
  shadcn/ui, TanStack, React Hook Form.
- Migration path sang React Native v2.x clean (share ~30-50% logic).
- Claude Code generation quality cao nhất với React (training data).
- Vue equally good technically nhưng job value thấp hơn ở VN;
  Svelte/Solid ecosystem đuối cho complex forms/tables.

**Consequences**:
- Phải học React hooks pattern (`useState`, `useEffect`, `useMemo`,
  custom hooks).
- React 19 features (Actions, `use` hook) mới → một số tutorial cũ
  dùng React 18 patterns có thể lệch.

---

### D4. Language

**Choice**: **TypeScript** (strict mode) từ đầu.

**Alternatives considered**:
- **JavaScript** thuần: nhanh hơn setup, ít boilerplate
- **JS với JSDoc typing**: hybrid, type hints qua comment

**Rationale**:
- OpenAPI spec → auto-generate TypeScript types qua `openapi-typescript`
  → end-to-end type-safe Backend ↔ Frontend.
- Backend đã Pydantic strict typing; FE dynamic sẽ drift sau 2-3
  sprint.
- Portfolio projects có TS compete tốt hơn (signal senior thinking).
- Strict mode từ đầu dễ hơn thêm sau: `strict: true`, `noImplicitAny`,
  `strictNullChecks`, `noUncheckedIndexedAccess`.

**Consequences**:
- Learning curve: generics, discriminated unions, utility types.
- Build step bắt buộc (nhưng Vite xử lý trong-memory).
- Refactor safer: rename symbol propagate qua entire codebase.

---

### D5. Build Tool

**Choice**: **Vite 6+**.

**Alternatives considered**:
- **Next.js** (App Router / Pages): metaframework, SSR built-in
- **Create React App** (CRA): legacy, deprecated 2023
- **Rsbuild** (ByteDance): Rspack-based, faster but smaller community
- **Parcel**: zero-config nhưng ecosystem nhỏ

**Rationale**:
- Vite là de-facto standard cho React SPA 2026.
- Dev server <500ms startup, HMR instant.
- Production build qua Rollup (tree-shaking tốt).
- Config minimal, extend qua plugin.
- Next.js over-kill cho SPA (đã chọn SPA ở D2).

**Consequences**:
- Config file: `vite.config.ts` (~30 lines max cho MVP).
- Env var: `import.meta.env.VITE_*` thay vì `process.env.*`.
- Test runner pair tốt nhất: Vitest (cùng underlying transformer).

---

### D6. Routing

**Choice**: **React Router v7** (library mode, không framework mode).

**Alternatives considered**:
- **TanStack Router**: type-safe params, file-based routing
- **Wouter**: tiny alternative (<2KB)
- **React Router v7 framework mode**: Remix-style full-stack

**Rationale**:
- React Router v7 (tháng 12/2024 release) unify Remix API → mature,
  battle-tested.
- Data loader pattern (`loader`, `action`) tích hợp với TanStack
  Query dễ.
- Library mode = SPA-only, không cần server runtime (khớp D2).
- TanStack Router technically tốt hơn về types nhưng ecosystem nhỏ
  hơn, ít tutorial VN.
- Wouter thiếu data loader → phải tự handle trong component.

**Consequences**:
- Nested routes qua `<Outlet />` pattern.
- Route config tập trung (recommend: `src/routes.tsx`).
- Type params: dùng utility `z.object({id: z.string().uuid()}).parse(useParams())`
  vì React Router không type-infer params.

---

### D7. Server State / Data Fetching

**Choice**: **TanStack Query v5** (formerly React Query).

**Alternatives considered**:
- **SWR** (Vercel): simpler API, nhỏ hơn
- **RTK Query** (Redux Toolkit): tích hợp Redux
- **Raw fetch + Context**: minimal, reinvent wheel

**Rationale**:
- TanStack Query là industry standard cho async data (caching,
  refetching, optimistic updates, pagination, infinite scroll).
- Stale-while-revalidate pattern built-in → invoice list không cần
  re-fetch sau navigate.
- DevTools browser extension xuất sắc.
- SWR simpler nhưng thiếu mutations ecosystem, pagination phải tự viết.
- RTK Query đòi Redux → đối nghịch D8 (Zustand).

**Consequences**:
- Mọi API call wrap trong `useQuery` / `useMutation` hook.
- Cache key convention: `['invoices', { landlordId, status, page }]`.
- Prefetch pattern: route loader call `queryClient.prefetchQuery()`.

---

### D8. Client State

**Choice**: **Zustand v5**.

**Alternatives considered**:
- **Redux Toolkit**: standard enterprise
- **Jotai**: atomic state
- **Valtio**: proxy-based
- **React Context**: built-in

**Rationale**:
- RMS có **very little client-only state**: auth token, current
  user profile, UI prefs (sidebar collapsed, theme). 90% state là
  server state (do TanStack Query quản lý).
- Zustand minimal API: `create(set => ({...}))`, không provider.
- Bundle <1KB, TypeScript-first.
- Redux Toolkit overkill: không có complex state machine, không
  cần middleware/thunks.
- Context performance issue: mọi consumer re-render khi state đổi.
- Jotai atomic model hay nhưng learning curve cao.

**Consequences**:
- Store recommend: `useAuthStore` (token, user), `useUIStore`
  (sidebar, theme). Chỉ ~2-3 stores MVP.
- Persist sử dụng middleware `zustand/middleware/persist` nếu cần
  (ví dụ: theme preference).

---

### D9. UI Library

**Choice**: **shadcn/ui + Tailwind CSS v4**.

**Alternatives considered**:
- **Material UI (MUI)**: Google Material design
- **Ant Design**: Alibaba, enterprise-heavy
- **Chakra UI**: simpler than MUI
- **Mantine**: all-in-one
- **Headless UI + custom Tailwind**: max flexibility

**Rationale**:
- shadcn/ui **không phải library** — là collection of copy-paste
  components built trên Radix UI (accessibility) + Tailwind (styling).
- Ownership: code components nằm trong `src/components/ui/`, bạn
  own tất cả → customize vô tư, không lock vendor.
- Ecosystem: TanStack Table, React Hook Form, Zod đều có shadcn
  templates sẵn.
- Aesthetic: minimal, modern, professional (phù hợp portfolio).
- Accessibility: Radix handle ARIA attributes, keyboard nav tự động.
- Tailwind v4 (2025): CSS-first config, faster build.
- MUI/AntD bundle lớn (>500KB), design opinionated khó match RMS
  brand.

**Consequences**:
- Phải học Tailwind utility classes (~1 tuần intensive).
- Setup qua CLI: `npx shadcn@latest init` rồi add components theo
  nhu cầu: `npx shadcn@latest add button table form dialog`.
- Theme qua CSS variables: `--primary`, `--background` trong
  `app.css`.
- Dark mode: built-in qua Tailwind `dark:` modifier.

---

### D10. Form Handling

**Choice**: **React Hook Form + Zod**.

**Alternatives considered**:
- **Formik**: older standard, slower
- **TanStack Form**: new, type-safe nhưng chưa stable v1
- **Native HTML form + useState**: minimal, reinvent wheel

**Rationale**:
- React Hook Form: uncontrolled input → ít re-render, performant
  với form có 20+ fields (ví dụ: Meter Reading batch form).
- Zod schema validation: share giữa frontend + codegen từ OpenAPI.
- Tích hợp shadcn/ui Form primitive (`<Form>`, `<FormField>`,
  `<FormMessage>`) smooth.
- Formik maintained ít, v3 chưa ra.
- TanStack Form v1 chưa release (alpha) → không chọn cho production.

**Consequences**:
- Pattern: `const form = useForm<Schema>({resolver: zodResolver(schema)})`.
- Error display: `form.formState.errors.fieldName` → `<FormMessage>`.
- Async validation: Zod `.refine()` + `useQuery` hybrid.

---

### D11. HTTP Client

**Choice**: **ky** (fetch wrapper).

**Alternatives considered**:
- **axios**: standard, feature-rich
- **Raw fetch**: no dependency
- **got** (Node-only, loại)
- **Redaxios**: axios API với fetch underneath

**Rationale**:
- ky: tiny (~5KB), built trên fetch, modern (ES modules, promises).
- Built-in retry, timeout, hooks (before/after request/response) →
  refresh token rotation handle clean ở hook.
- axios bundle lớn hơn (~13KB), legacy XMLHttpRequest base, ít
  relevant với fetch era.
- Raw fetch thiếu: no retry, no timeout, verbose error handling.

**Consequences**:
- Tạo instance central: `src/api/client.ts` với `ky.create({prefixUrl, hooks})`.
- Hook `beforeRequest` inject Authorization header từ Zustand auth store.
- Hook `beforeError` catch 401 → trigger refresh token flow → retry
  original request.

---

### D12. API Codegen (OpenAPI)

**Choice**: **openapi-typescript + openapi-fetch**.

**Alternatives considered**:
- **orval**: generate TanStack Query hooks tự động
- **openapi-generator-cli**: Java-based, heavy
- **hey-api/openapi-ts**: fork của openapi-typescript-codegen
- **Manual types**: write types by hand

**Rationale**:
- openapi-typescript: zero runtime, generate `type` definitions
  từ `openapi.yaml` → import qua `paths['/api/v1/invoices']`.
- openapi-fetch: tiny (~2KB) wrapper dùng types đó.
- orval auto-generate query hooks nhưng:
  - Tight couple với TanStack Query → khó customize
  - Re-generate lớn khi API đổi
  - Bạn nên tự viết hooks để learn pattern (portfolio goal)
- Manual types drift sau 2-3 API changes.

**Consequences**:
- Script `pnpm run codegen`: `openapi-typescript ../backend/openapi.yaml
  -o src/api/schema.ts`.
- API client: `const client = createClient<paths>({baseUrl})`.
- Type-safe request/response: `const {data} = await client.GET('/api/v1/invoices',
  {params: {query: {status: 'unpaid'}}})`.

---

### D13. Testing

**Choice**: **Vitest + React Testing Library + MSW (Mock Service Worker)**.

**Alternatives considered**:
- **Jest + RTL**: standard nhưng ESM setup phức tạp
- **Playwright Component Testing**: real browser, slower
- **Cypress Component Testing**: legacy, bị Playwright lấn
- **Vitest Browser Mode**: real browser + Vitest DX (preview feature)

**Rationale**:
- Vitest: Jest-compatible API, faster (Vite transformer), native ESM.
- React Testing Library: de-facto standard, test user behavior
  không test implementation.
- MSW: mock HTTP ở service worker level → test components với
  realistic network.
- Jest slower, ESM hack qua `ts-jest` flaky.
- Playwright CT real browser tốt cho E2E nhưng overkill cho unit.

**Consequences**:
- Config: `vitest.config.ts` (share với Vite config).
- Test file: `*.test.tsx` co-located với component.
- MSW handlers: `src/mocks/handlers.ts` → generate từ openapi.yaml
  qua `@mswjs/source`.
- Coverage: target >70% cho hooks, >50% cho components.

**Scope**: E2E tests (Playwright) **không** trong Phase 4 MVP.
Defer to Phase 5.

---

### D14. Linter / Formatter

**Choice**: **ESLint v9 (flat config) + Prettier**.

**Alternatives considered**:
- **Biome**: all-in-one, Rust-based, faster
- **Deno fmt**: good but Deno-only ecosystem
- **Rome** (deprecated, became Biome)

**Rationale**:
- ESLint ecosystem mature (TypeScript-ESLint, react-hooks rules,
  jsx-a11y).
- Prettier handle formatting cross-language (YAML, MD, JSON).
- Biome chưa đủ plugins (no React hooks rules, no TypeScript lint
  parity với `@typescript-eslint`).
- ESLint v9 flat config cleaner than v8 `.eslintrc`.

**Consequences**:
- Config: `eslint.config.js` (flat), `.prettierrc.json`.
- Plugins: `@typescript-eslint`, `eslint-plugin-react-hooks`,
  `eslint-plugin-jsx-a11y`, `eslint-plugin-tanstack-query`.
- IDE integration: VS Code ESLint + Prettier extensions.
- Pre-commit hook: `lint-staged` + `husky` chạy lint+format trên
  staged files.

---

### D15. Package Manager

**Choice**: **pnpm v10**.

**Alternatives considered**:
- **npm**: default, slow, duplicated deps
- **yarn**: faster than npm, ecosystem split
- **Bun**: faster, new runtime + package manager combo

**Rationale**:
- pnpm: disk-efficient (content-addressable store), strict
  dependency resolution (ít phantom deps).
- Workspace native (cần khi Phase 5 monorepo).
- Bun chưa stable hoàn toàn cho Windows, ecosystem compat issues
  với một số Vite plugins.

**Consequences**:
- Lockfile: `pnpm-lock.yaml`.
- Install: `pnpm install`, add: `pnpm add <pkg>`, script: `pnpm dev`.
- CI cache key: hash of `pnpm-lock.yaml`.

---

## Final Stack Summary

| Layer | Tech | Version |
|---|---|---|
| Package manager | pnpm | 10+ |
| Language | TypeScript | 5.7+ (strict) |
| Build tool | Vite | 6+ |
| Framework | React | 19 |
| Routing | React Router (library mode) | 7+ |
| Server state | TanStack Query | 5+ |
| Client state | Zustand | 5+ |
| Styling | Tailwind CSS | 4+ |
| UI components | shadcn/ui (Radix + Tailwind) | latest |
| Forms | React Hook Form + Zod | RHF 7+, Zod 3+ |
| HTTP client | ky | 1+ |
| API codegen | openapi-typescript + openapi-fetch | latest |
| Testing | Vitest + React Testing Library + MSW | latest |
| Lint/format | ESLint 9 flat + Prettier 3 | latest |

---

## Project Structure (recommended)

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts              # ky instance + hooks
│   │   ├── schema.ts              # Auto-generated from openapi.yaml
│   │   └── queries/               # TanStack Query hooks per domain
│   │       ├── useInvoices.ts
│   │       ├── useLeases.ts
│   │       └── ...
│   ├── components/
│   │   ├── ui/                    # shadcn/ui generated components
│   │   ├── forms/                 # Reusable form components
│   │   └── layouts/               # AppShell, AuthLayout, etc.
│   ├── features/                  # Domain features (vertical slice)
│   │   ├── auth/
│   │   ├── properties/
│   │   ├── rooms/
│   │   ├── tenants/
│   │   ├── leases/
│   │   ├── services/
│   │   ├── meter-readings/
│   │   ├── invoices/
│   │   └── payments/
│   ├── hooks/                     # Shared custom hooks
│   ├── lib/                       # Utilities (date, currency, validation)
│   ├── stores/                    # Zustand stores
│   │   ├── auth.ts
│   │   └── ui.ts
│   ├── routes.tsx                 # React Router config
│   ├── main.tsx                   # Entry point
│   └── app.css                    # Tailwind + CSS vars
├── public/
├── tests/
│   ├── setup.ts
│   └── mocks/                     # MSW handlers
├── eslint.config.js
├── tailwind.config.ts
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── package.json
└── pnpm-lock.yaml
```

---

## Setup Commands (Phase 4 kickoff)

```bash
# Tạo project
pnpm create vite@latest frontend -- --template react-ts
cd frontend

# Core deps
pnpm add react-router @tanstack/react-query zustand
pnpm add ky openapi-fetch
pnpm add react-hook-form @hookform/resolvers zod

# UI (shadcn/ui setup)
pnpm add tailwindcss@next @tailwindcss/vite
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button card dialog form input label select table tabs toast

# Dev deps
pnpm add -D openapi-typescript msw
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
pnpm add -D eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser
pnpm add -D eslint-plugin-react-hooks eslint-plugin-jsx-a11y eslint-plugin-tanstack-query
pnpm add -D prettier eslint-config-prettier
pnpm add -D husky lint-staged

# Codegen script in package.json
# "scripts": {
#   "codegen": "openapi-typescript ../docs/04-api/openapi.yaml -o src/api/schema.ts"
# }
```

---

## Consequences

### Positive

- **Type-safe end-to-end**: OpenAPI → TS types → compile-time catch
  API drift.
- **Modern DX**: Vite HMR, Vitest fast tests, shadcn/ui copy-paste.
- **Ownership**: shadcn/ui components nằm trong repo → không vendor lock.
- **Portfolio value cao**: Stack là industry standard 2026 cho React SPA.
- **Migration path**: React → React Native v2.x khả thi (logic share).
- **Consistent với backend**: Zod ↔ Pydantic cùng philosophy (schema-first
  validation).

### Negative / Trade-offs

- **Learning curve lớn**: Bảo phải học Tailwind (~1 tuần) + TanStack
  Query (~3-5 ngày) + React Hook Form (~2 ngày) + TypeScript advanced
  (~2 tuần) trước khi productive.
- **Bundle size**: ~250KB gzipped (React + Router + Query + Zustand +
  shadcn). Không vấn đề với internal app, sẽ là concern khi mở public.
- **Không có SSR**: SEO và social sharing preview (og:image dynamic)
  không support. OK vì app private.
- **Dependency count cao**: ~20 direct deps → update cadence phải
  disciplined (recommend Renovate/Dependabot monthly).

### Neutral

- **pnpm không phải default**: Một số tutorial dùng npm/yarn; Bảo cần
  translate commands. Trivial.
- **ESLint flat config**: Một số plugin chưa migrate sang v9; mostly
  resolved cuối 2024.
- **React 19 features**: `use` hook, Actions API còn mới; Bảo sẽ gặp
  tutorial React 18 patterns → cần đọc docs chính thức.

---

## Open Questions (defer to Phase 4)

1. **Mobile strategy v1.x**: React Native vs Expo vs Capacitor wrap
   của web app. Decide khi có user feedback MVP.
2. **Internationalization (i18n)**: MVP Vietnamese-only. Nếu v1.x thêm
   English: react-i18next vs LinguiJS.
3. **Analytics**: MVP không có. v1.x: PostHog self-hosted hoặc Plausible.
4. **Error tracking**: MVP console.error + server log. v1.x: Sentry.
5. **State persistence**: Auth token persist qua refresh? Recommend
   HttpOnly cookie (đã decide ADR-0007). Theme + UI prefs:
   localStorage qua Zustand persist middleware.

---

## References

- React 19 release notes: https://react.dev/blog/2024/12/05/react-19
- Vite 6: https://vite.dev/
- React Router v7: https://reactrouter.com/
- TanStack Query v5: https://tanstack.com/query/latest
- shadcn/ui: https://ui.shadcn.com/
- openapi-typescript: https://openapi-ts.dev/
- ADR-0007 (JWT + refresh token rotation) — related auth pattern
- Phase 3 ERD + OpenAPI spec — source of truth cho type generation

---

**ADR-0008 End.**
