# Rental Management System (RMS)

> Hệ thống quản lý cho thuê và vận hành phòng trọ.
> Portfolio project → production-grade SaaS.

## Status

- **Phase**: 0 – Bootstrap / 1 – Vision (in progress)
- **Sprint cadence**: 1 tuần
- **Owner**: Bảo
- **Started**: 2026-04

## Documentation Map

| Folder                    | Nội dung                                               |
| ------------------------- | ------------------------------------------------------ |
| `docs/00-overview/`       | Vision, scope, glossary                                |
| `docs/01-requirements/`   | User stories, Functional & Non-functional requirements |
| `docs/02-architecture/`   | System architecture, tech stack                        |
| `docs/03-database/`       | ERD, schema, migration strategy                        |
| `docs/04-api/`            | API specification (OpenAPI)                            |
| `docs/05-implementation/` | Sprint logs, module notes                              |
| `docs/06-testing/`        | Test strategy, coverage reports                        |
| `docs/07-deployment/`     | CI/CD, infrastructure, runbooks                        |
| `docs/decisions/`         | Architecture Decision Records (ADRs)                   |
| `CHANGELOG.md`            | Versioned log of notable changes                       |

## Workflow Convention

1. Mỗi quyết định kiến trúc → viết 1 ADR trong `docs/decisions/`
2. Mỗi sprint → 1 file trong `docs/05-implementation/sprint-XX.md`
3. Cuối sprint → cập nhật `CHANGELOG.md`
4. Branch: `main` (stable) · `develop` (integration) · `feature/xxx` · `fix/xxx`

## Tech Stack (tentative — sẽ chốt ở Phase 3)

- Backend: FastAPI + SQLModel + PostgreSQL + Alembic
- Auth: JWT + RBAC
- Infra: Docker + Docker Compose
- Frontend: _TBD_
