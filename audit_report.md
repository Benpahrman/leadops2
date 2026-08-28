# Project Audit Report — 2026-08-27

## Executive Summary
LeadOps is a FastAPI + SQLite backend with a Clerk-protected Vite SPA frontend and a dependency-free local portal demo. Domain model for lead lifecycle, PayPal escrow/deposit flows, and autonomous Scout/Build loop are implemented. Overall health is functional for demo but shows significant UI inconsistency, accessibility gaps, and production-readiness risks.

Top 3 critical findings:
1. **Security fallback**: `ClerkAuthService` defaults to `mock_clerk_secret_key` when env var missing — allows auth bypass in dev/prod if misconfigured.
2. **UI fragmentation**: Production SPA uses inline styles in `my-clerk-vite-app/src/main.js`; local portal uses separate Georgia-serif stylesheet. No design system, no responsive tests, no accessibility.
3. **Error handling & observability**: 43 `except Exception` blocks, generic catch and `innerHTML` rendering; missing structured error responses, rate limiting, and CSRF protection.

Overall score: 5.5/10

## Scoring
| Category                  | Score | Grade |
|---------------------------|-------|-------|
| UI & Visual Design        | 4/10  | D     |
| Customer Flow & Journeys  | 6/10  | C     |
| UX Heuristics             | 5/10  | F     |
| Code Quality              | 6/10  | C     |
| Accessibility             | 3/10  | F     |
| Security & Ops            | 6/10  | C     |
| **Overall**               | 5/10  | F     |

## Critical Findings (Must Fix)

### 🔴 Critical-1: Auth secret fallback to mock
`agents/auth.py:37` — `self.secret_key = secret_key or os.environ.get("CLERK_SECRET_KEY", "mock_clerk_secret_key")`
Impact: If `CLERK_SECRET_KEY` is unset, service silently uses mock key, allowing unauthenticated access in production.
Fix: Fail fast if secret missing in non-test env; remove mock default.

### 🔴 Critical-2: CORS wildcard mitigation incomplete
`agents/api.py:34-36` removes `*` from origins but logs warning only. No enforcement of strict origin list in production.
Fix: Require `LEADOPS_CORS_ORIGINS` set and validate non-empty; reject requests from unknown origins.

### 🔴 Critical-3: Inline HTML rendering with user data
`my-clerk-vite-app/src/main.js:115-260` builds UI via `innerHTML` using sandbox data directly. XSS risk if sandbox fields contain untrusted content.
Fix: Use DOM APIs or template engine with escaping; sanitize all user-supplied fields before render.

## High Priority (Should Fix Soon)

### 🟠 High-1: UI inconsistency & maintenance burden
- `my-clerk-vite-app/src/main.js` contains ~350 lines of inline style objects.
- `agents/local_portal.py` serves separate HTML with Georgia serif theme.
- No shared design tokens, no CSS framework, no responsive breakpoints tested.
Impact: Brand incoherence, high cost to change UI.
Fix: Extract design system, move styles to CSS modules, unify portal and SPA themes.

### 🟠 High-2: Exception handling is broad
43 occurrences of `except Exception` across agents. Many swallow errors silently e.g., `agents/auth.py:104`, `agents/llm_client.py:29`.
Impact: Debugging difficulty, silent failures in payment/webhook paths.
Fix: Catch specific exceptions, log stack traces, return meaningful error responses.

### 🟠 High-3: Missing input validation
`domain.Leadd.transition` validates state transitions but API routes do not validate request bodies consistently. `agents/routes/portal.py` catches generic exceptions.
Impact: Data integrity risk, potential injection.
Fix: Add Pydantic models for all endpoints, validate fields length/type.

### 🟠 High-4: No rate limiting or CSRF protection
FastAPI app enables CORS with credentials but no rate limiting middleware, no CSRF tokens for state-changing POSTs.
Impact: Abuse risk for PayPal webhook and deposit simulation endpoints.
Fix: Add slowapi/rate limiter, CSRF protection for browser forms.

## Medium Priority (Plan to Fix)

### 🟡 Medium-1: Accessibility baseline missing
- Dynamic UI built via `innerHTML`, no semantic landmarks, no ARIA labels.
- No focus indicators, no keyboard navigation tests.
- Color contrast unverified.
Fix: Add semantic HTML, focus styles, ARIA attributes, run axe-core audits.

### 🟡 Medium-2: Responsive design not verified
`style.css` defines only base colors. Inline styles use fixed widths e.g., `max-width:960px`. No mobile tests.
Fix: Add responsive breakpoints, test 360/768/1280px, ensure touch targets ≥44px.

### 🟡 Medium-3: Logging & observability gaps
`agents/logging_config.py` exists but many modules use print or generic logger. No structured JSON logs, no request IDs.
Fix: Standardize structured logging, correlate requests, add health metrics.

### 🟡 Medium-4: Test coverage unknown
Tests exist in `tests/` but no coverage report. Unit tests for domain exist; integration tests for PayPal webhooks may be mock-only.
Fix: Run `pytest --cov`, target >80% for domain, payments, auth.

## Low Priority (Nice to Have)

### 🟢 Low-1: Placeholder UI states
No empty states for zero leads, no skeleton loaders.
Fix: Add empty state components.

### 🟢 Low-2: Micro-interactions
No transitions; buttons lack hover/active states in SPA.
Fix: Add subtle transitions.

### 🟢 Low-3: Documentation drift
README describes features but some routes referenced may be stale. No OpenAPI tags for all routes.
Fix: Keep docs in sync, add docstrings.

## Detailed Findings by Category

### UI & Visual Design
- Color palette cohesive in dark theme but duplicated via inline styles.
- Typography inconsistent: system-ui in SPA vs Georgia serif in local portal.
- Spacing inconsistent due to inline style objects.
- No dark/light mode toggle.
- No responsive verification.
- Buttons have hover states via inline `:hover` not defined; relies on browser defaults.
- Loading states absent for fetch calls except console log.
- No favicon in SPA? `index.html` references `/favicon.svg` — file not confirmed.
- `agents/local_portal.py` uses fixed layout, media query at 650px only.

### Customer Flow & Journeys
**Onboarding**: Clerk sign-in works, founder detection via email list `ADMIN_EMAILS` hardcoded in `main.js:15`.
**Auth flow**: Session token fetched, attached to headers. Sign-out works.
**Lead Management**: Founder can switch companies via buttons; client sees only own lead.
**Payment flow**: Deposit simulation button calls `POST /api/sandbox/{slug}/pay-deposit`. Real PayPal checkout requires credentials.
**Portal flow**: Client portal URL constructed but opens public portal; unclear separation.
Edge cases: No handling for network failure beyond console.log.
Success confirmation shown via UI updates but no toast.

### UX Heuristics (Nielsen's 10)
1. Visibility of System Status: ⚠️ Needs Improvement — no progress toasts
2. Match Between System & Real World: ✅ Pass — terminology clear
3. User Control & Freedom: ✅ Pass — sign out present
4. Consistency & Standards: ❌ Fail — inline styles vs portal
5. Error Prevention: ⚠️ Needs Improvement — no confirmation dialogs for destructive actions
6. Recognition Over Recall: ✅ Pass — company switcher visible
7. Flexibility & Efficiency: ⚠️ Needs Improvement — no keyboard shortcuts
8. Aesthetic & Minimalist Design: ⚠️ Needs Improvement — cluttered inline UI
9. Help Users Recover from Errors: ❌ Fail — generic catch, no retry UI
10. Help & Documentation: ⚠️ Needs Improvement — no in-app help

### Code Quality & Gaps
- Domain model well-defined with state machine in `agents/domain.py`.
- Storage backend supports migrations for columns.
- TODO/FIXME comments: none in code.
- Dead code: `agents/pitcher.py` SendPulse integration appears unused.
- Error handling: broad excepts, no dead-letter for background jobs.
- Data integrity: SQLite with parameterized queries, good.
- Secrets: No hardcoded secrets found; env var usage correct except mock fallback.
- Testing gaps: No E2E tests for Clerk flows.

### Accessibility
- Perceivable: No alt text, color-only information in milestone badges.
- Operable: Dynamic UI via innerHTML may break keyboard focus.
- Understandable: Language attribute set in `index.html`.
- Robust: Valid HTML in static files; dynamic content not validated.

### Security & Ops
- Auth tokens validated per request via Clerk service.
- Role-based access: founder vs client via email check client-side — should be server enforced.
- CORS configured with whitelist, wildcard stripped.
- No rate limiting.
- Health check at `/health` exposes `emergency_stop_active`.
- Logging configured but not structured.
- Database file `leadops.db` committed? Not in .gitignore listing; ensure ignored.
- PayPal webhook verification implemented in `agents/paypal_webhook.py`.

## Recommended Action Plan
1. Remove mock secret fallback and enforce env vars in production — effort S
2. Sanitize dynamic UI rendering, move styles to CSS modules — effort M
3. Add Pydantic validation for all API routes — effort M
4. Replace broad `except Exception` with specific handling and logging — effort M
5. Add rate limiting + CSRF protection — effort S
6. Implement accessibility audit with axe-core and fix critical issues — effort M
7. Unify design system between SPA and local portal — effort L
8. Add coverage reporting and E2E tests for critical flows — effort L
9. Add structured logging and request tracing — effort S
10. Enforce server-side RBAC for founder view — effort S
