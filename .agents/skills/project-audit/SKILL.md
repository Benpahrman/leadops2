---
name: project-audit
description: >
  Comprehensive project audit skill for identifying gaps, mishaps, and improvement
  opportunities across UI design, customer flow, UX heuristics, code quality,
  accessibility, error handling, and security. Use this skill when auditing any
  aspect of the project — from frontend UI to backend pipeline quality.
---

# Project Audit Skill

Run a structured, multi-dimensional audit of the project. This skill guides you
through a thorough review of the codebase, UI, customer experience, and
operational readiness — producing a prioritized findings report with actionable
recommendations.

---

## How To Run

When the user asks to audit the project (or any subset of it), follow these
phases in order. Skip phases only if the user explicitly scopes the audit.

---

## Phase 1: Discovery & Inventory

Before auditing, understand what exists.

### 1.1 — Map the Architecture

- List all entry points (servers, CLIs, scripts, cron jobs)
- Identify the frontend stack (Vite, React, Clerk, etc.)
- Identify the backend stack (FastAPI, agents, LLM pipelines, etc.)
- Map data flow: lead ingestion → processing → delivery → billing
- Document external integrations (Clerk, PayPal, LLM providers, Playwright)

### 1.2 — Catalog User-Facing Surfaces

- Dashboard pages and views
- Customer portal / client portal
- Auth flows (sign-up, sign-in, SSO, org management)
- Payment / checkout flows
- Admin / operator views
- Email or notification touchpoints

### 1.3 — Catalog Backend Surfaces

- API endpoints (list all routes in `api.py`, `auth.py`, etc.)
- Background jobs and pipelines (`workflow.py`, `scout_runner.py`, `build_loop.py`)
- Database schema and storage (`storage.py`, `leadops.db`)
- Configuration and environment variables

---

## Phase 2: UI & Visual Design Audit

Use browser tools (Playwright, browser subagent) to visually inspect each
user-facing page. For each page, check:

### 2.1 — Visual Consistency

- [ ] Color palette is cohesive (no clashing or default browser colors)
- [ ] Typography is consistent (font family, sizes, weights, line heights)
- [ ] Spacing and alignment follow a consistent grid/system
- [ ] Icons and imagery are consistent in style and quality
- [ ] Dark/light mode works correctly (if applicable)

### 2.2 — Responsiveness

- [ ] Layout adapts to mobile viewports (360px, 390px)
- [ ] Layout adapts to tablet viewports (768px)
- [ ] Layout adapts to desktop viewports (1280px, 1920px)
- [ ] No horizontal overflow or broken layouts at any viewport
- [ ] Touch targets are adequately sized on mobile (min 44×44px)

### 2.3 — Component Quality

- [ ] Buttons have clear hover, active, focus, and disabled states
- [ ] Forms have proper labels, placeholders, and validation messages
- [ ] Loading states exist for async operations
- [ ] Empty states exist (no data, no results, first-time user)
- [ ] Error states are visually distinct and helpful

### 2.4 — Polish & Delight

- [ ] Micro-animations and transitions are smooth (not jarring)
- [ ] No placeholder text, Lorem ipsum, or TODO visible in production UI
- [ ] Favicon and page titles are set
- [ ] No broken images or missing assets

---

## Phase 3: Customer Flow & Journey Audit

Trace every critical user journey end-to-end. Use browser automation where
possible. For each flow, document:

### 3.1 — Core Flows to Audit

1. **Onboarding Flow**: Sign-up → first action → "aha moment"
2. **Authentication Flow**: Sign-in → session management → sign-out
3. **Lead Management Flow**: View leads → filter/search → take action
4. **Dashboard Flow**: Landing → key metrics → drill-down
5. **Payment Flow**: Select plan → checkout → confirmation → receipt
6. **Portal Flow**: Client accesses portal → views deliverables → provides feedback
7. **Admin Flow**: Operator manages campaigns, users, settings

### 3.2 — Flow Quality Checklist (per flow)

- [ ] The user can complete the flow without getting stuck
- [ ] Each step has clear navigation (back, next, cancel)
- [ ] Progress indication exists for multi-step flows
- [ ] Success confirmation is shown at completion
- [ ] Error recovery is possible at every step (no dead ends)
- [ ] The flow is achievable in a reasonable number of clicks
- [ ] No redundant or confusing steps
- [ ] CTA (Call to Action) hierarchy is clear — the user knows what to do next

### 3.3 — Edge Cases & Failure Modes

- [ ] What happens with no data? (empty states)
- [ ] What happens with too much data? (pagination, performance)
- [ ] What happens when the network is slow? (loading states, timeouts)
- [ ] What happens on API failure? (error messages, retry options)
- [ ] What happens with invalid input? (validation, sanitization)
- [ ] What happens if the user navigates away mid-flow?

---

## Phase 4: UX Heuristics Audit (Nielsen's 10)

Evaluate the product against Jakob Nielsen's 10 Usability Heuristics:

| # | Heuristic | What to Check |
|---|-----------|---------------|
| 1 | **Visibility of System Status** | Loading indicators, progress bars, success/error toasts, real-time updates |
| 2 | **Match Between System & Real World** | Terminology matches user expectations, not developer jargon |
| 3 | **User Control & Freedom** | Undo/redo, cancel buttons, easy navigation back |
| 4 | **Consistency & Standards** | Same patterns across pages, follows platform conventions |
| 5 | **Error Prevention** | Confirmation dialogs for destructive actions, input constraints |
| 6 | **Recognition Over Recall** | Visible options, contextual help, breadcrumbs |
| 7 | **Flexibility & Efficiency** | Keyboard shortcuts, bulk actions, filters, search |
| 8 | **Aesthetic & Minimalist Design** | No clutter, information hierarchy, whitespace usage |
| 9 | **Help Users Recover from Errors** | Clear error messages with resolution steps, no raw stack traces |
| 10 | **Help & Documentation** | Tooltips, onboarding guides, FAQ, contextual help |

Rate each heuristic: ✅ Pass | ⚠️ Needs Improvement | ❌ Fail

---

## Phase 5: Code Quality & Gap Analysis

### 5.1 — Missing Features & Dead Code

- [ ] Identify features referenced in docs/README but not implemented
- [ ] Identify routes defined but returning placeholder/stub responses
- [ ] Identify imported but unused modules
- [ ] Identify TODO/FIXME/HACK comments (catalog and prioritize)
- [ ] Identify functions that are defined but never called

### 5.2 — Error Handling

- [ ] All API endpoints have try/except with meaningful error responses
- [ ] Database operations handle connection failures and constraint violations
- [ ] External API calls (Clerk, PayPal, LLM providers) have timeout and retry logic
- [ ] Playwright/browser automation has failure recovery
- [ ] Background jobs have dead-letter / failure notification mechanisms
- [ ] No bare `except:` or `except Exception:` that silently swallows errors

### 5.3 — Data Integrity

- [ ] Input validation on all API endpoints (request body, query params)
- [ ] SQL injection prevention (parameterized queries or ORM usage)
- [ ] XSS prevention in any rendered HTML
- [ ] Proper data serialization/deserialization (no raw eval/exec)
- [ ] Database migrations are tracked and reversible

### 5.4 — Configuration & Secrets

- [ ] No hardcoded secrets, API keys, or passwords in source code
- [ ] `.env.example` documents all required environment variables
- [ ] Sensitive config uses proper secret management
- [ ] Default values are safe (don't expose debug mode in production)

### 5.5 — Testing Gaps

- [ ] Unit test coverage for critical business logic
- [ ] Integration tests for API endpoints
- [ ] End-to-end tests for critical user flows
- [ ] Test fixtures and mocks are realistic
- [ ] CI/CD pipeline runs tests before deploy

---

## Phase 6: Accessibility Audit (WCAG 2.2)

### 6.1 — Perceivable

- [ ] All images have meaningful alt text
- [ ] Color is not the only means of conveying information
- [ ] Sufficient color contrast ratios (4.5:1 for normal text, 3:1 for large)
- [ ] Text is resizable up to 200% without loss of content
- [ ] No content flashes more than 3 times per second

### 6.2 — Operable

- [ ] All interactive elements are keyboard-accessible
- [ ] Visible focus indicators on all focusable elements
- [ ] No keyboard traps
- [ ] Skip navigation links exist
- [ ] Form inputs have associated labels

### 6.3 — Understandable

- [ ] Language attribute set on `<html>` element
- [ ] Error messages identify the field and describe the error
- [ ] Labels and instructions are provided for user input
- [ ] Navigation is consistent across pages

### 6.4 — Robust

- [ ] Valid HTML (no unclosed tags, proper nesting)
- [ ] ARIA attributes used correctly (not overused)
- [ ] Works with screen readers (test with NVDA or VoiceOver)
- [ ] Semantic HTML elements used appropriately

---

## Phase 7: Security & Operational Readiness

### 7.1 — Authentication & Authorization

- [ ] Auth tokens validated on every protected route
- [ ] Session expiration and refresh logic works correctly
- [ ] Role-based access control (RBAC) enforced
- [ ] CORS configuration is restrictive (not wildcard `*`)
- [ ] CSRF protection on state-changing operations

### 7.2 — Operational

- [ ] Logging is structured and meaningful (not just print statements)
- [ ] Health check endpoints exist
- [ ] Graceful shutdown handling
- [ ] Rate limiting on public endpoints
- [ ] Database connection pooling configured

---

## Phase 8: Report & Prioritize

### Output Format

Produce a findings report as a markdown artifact (`audit_report.md`) with:

```markdown
# Project Audit Report — [Date]

## Executive Summary
Brief overview of project health, top 3 critical findings, overall score.

## Scoring
| Category                  | Score | Grade |
|---------------------------|-------|-------|
| UI & Visual Design        | X/10  | A-F   |
| Customer Flow & Journeys  | X/10  | A-F   |
| UX Heuristics             | X/10  | A-F   |
| Code Quality              | X/10  | A-F   |
| Accessibility             | X/10  | A-F   |
| Security & Ops            | X/10  | A-F   |
| **Overall**               | X/10  | A-F   |

## Critical Findings (Must Fix)
Findings that block launch or cause data loss, security vulnerabilities, 
or broken user flows.

## High Priority (Should Fix Soon)
Findings that significantly degrade user experience or code quality.

## Medium Priority (Plan to Fix)
Findings that affect polish, consistency, or maintainability.

## Low Priority (Nice to Have)
Findings that are cosmetic or minor quality-of-life improvements.

## Detailed Findings by Category
### UI & Visual Design
### Customer Flow & Journeys
### UX Heuristics (Nielsen's 10)
### Code Quality & Gaps
### Accessibility
### Security & Ops

## Recommended Action Plan
Ordered list of recommended next steps with effort estimates.
```

### Severity Definitions

| Severity | Definition | Example |
|----------|-----------|---------|
| 🔴 Critical | Blocks launch, data loss, security hole | Unauthenticated admin access |
| 🟠 High | Major UX issue, broken flow, data integrity risk | Checkout flow fails silently |
| 🟡 Medium | Noticeable quality issue, inconsistency | Missing loading states |
| 🟢 Low | Polish, cosmetic, nice-to-have | Button hover color slightly off |

---

## Tips for Running This Audit

1. **Use browser automation** to capture screenshots of every page/state
2. **Use `grep_search`** to find TODOs, FIXMEs, bare excepts, hardcoded secrets
3. **Use `view_file`** to read through critical code paths
4. **Run the app** and interact with it via browser subagent
5. **Check the database** for schema completeness
6. **Cross-reference** the README and docs with actual implementation
7. **Take screenshots** at each step for the audit report
