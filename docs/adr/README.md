# 🏛️ Architecture Decision Records (ADRs)

This directory serves as the definitive registry of Architectural Decision Records for the LeadOps Swarm and Client Portal platform. ADRs capture significant architectural decisions, their context, consequences, trade-offs, and alternatives considered.

---

## 📋 ADR Registry

| ADR | Title | Status | Date | Core Scope |
| :--- | :--- | :---: | :---: | :--- |
| [ADR-0001](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0001-zero-mock-live-data-architecture.md) | Zero-Mock Live Data Architecture | **Accepted** | 2026-09-16 | Strict prohibition of mock data in production; same-day live scraping gates; deterministic data freshness. |
| [ADR-0002](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0002-strangler-fig-modularization-protocol.md) | Strangler Fig De-monolithization Protocol | **Accepted** | 2026-09-16 | Standard for decomposing God files into cohesive domain packages behind zero-breaking-change facades. |
| [ADR-0003](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0003-backend-frontend-boundary-decoupling.md) | Backend-Frontend Boundary Decoupling | **Accepted** | 2026-09-16 | Deprecation of server-rendered HTML in FastAPI in favor of React Vite client; REST/SSE API boundary. |
| [ADR-0004](file:///c:/Users/ben/Documents/leadops2/docs/adr/ADR-0004-multi-channel-notifications-and-component-decomposition.md) | Multi-Channel Notifications & Component Decomposition | **Accepted** | 2026-09-16 | Modularization of notifications engine into domain modules; extraction of React admin modals. |

---

## 📝 Creating a New ADR

To propose or document a new architectural decision:
1. Copy the template from [.agents/skills/code-organization-modularization-refactor/references/documentation_standards.md](file:///c:/Users/ben/Documents/leadops2/.agents/skills/code-organization-modularization-refactor/references/documentation_standards.md).
2. Assign the next sequential number (`ADR-0004-*.md`).
3. Document Context, Decision, Consequences (Positive & Negative), Alternatives Considered, and Verification.
4. Update this registry table.
