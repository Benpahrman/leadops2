# LeadOps Remediation Plan

Date: 2026-08-27
Source: audit_report.md

## Goals
Eliminate critical security risks, harden auth/RBAC, remove XSS vectors, improve error handling and UI consistency.

## Phase A — Critical Security Fixes

### A1. Remove mock Clerk secret fallback
File: agents/auth.py
Change: Fail fast if CLERK_SECRET_KEY missing in non-test env.
Effort: S

### A2. Server-side RBAC for founder view
File: agents/routes/admin.py, agents/auth.py
Change: Move ADMIN_EMAILS check from client JS to server middleware. Reject admin endpoints unless user email in allowlist.
Effort: S

### A3. XSS mitigation for SPA
File: my-clerk-vite-app/src/main.js
Change: Stop using innerHTML with sandbox data. Use textContent / DOM APIs or escape helper. Sanitize company_name, contact_email, source_url.
Effort: M

## Phase B — High Priority Hardening

### B1. Strict CORS enforcement
File: agents/api.py
Change: Require LEADOPS_CORS_ORIGINS set; error on wildcard; log rejected origins.
Effort: S

### B2. Input validation
Add Pydantic models for all mutable routes in agents/routes/*.py
Effort: M

### B3. Error handling hygiene
Replace broad except Exception with specific exceptions; log stack traces.
Effort: M

## Phase C — Quality & Consistency

### C1. Design system extraction
Move inline styles from main.js to CSS modules; unify local portal theme.
Effort: M

### C2. Rate limiting & CSRF
Add slowapi middleware and CSRF tokens for state-changing POST.
Effort: M

## Execution Order
A1 → A2 → A3 → B1 → B2 → B3 → C1 → C2

Success criteria:
- Auth fails closed when secret missing
- Admin endpoints reject non-allowlist users server-side
- No innerHTML with unsanitized data
- All tests pass: python -m unittest discover -s tests -v
