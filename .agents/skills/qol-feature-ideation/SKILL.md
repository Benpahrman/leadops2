---
name: qol-feature-ideation
description: >
  Systematic ideation, auditing, and design skill for Quality of Life (QoL)
  enhancements, operator ergonomics, user delight papercut fixes, and breakthrough
  product features. Covers developer/operator tooling, React UI micro-interactions,
  autonomous swarm visibility, zero-mock live data workflows, and RICE-prioritized
  production-ready specs.
---

# Quality of Life (QoL) Improvements & Feature Ideation Skill

Use this skill to uncover friction, eliminate operator toil, fix customer papercuts,
and brainstorm high-leverage product features across the full stack.

This skill operates under strict production engineering standards:
- **Zero Mock Data**: Every proposal must hook into live database records, real API endpoints, and live agent telemetry.
- **Clean Architecture**: UI/UX features live strictly in the React frontend; business logic and agent orchestrations live in the backend/swarm services.
- **Production Complete**: Generates actionable, end-to-end specifications—including UI layouts, Pydantic schemas, database queries, and agent triggers.

---

## Core Mental Model: Papercuts vs. Levers

```
┌────────────────────────────────────────────────────────┐
│               THE VALUE ENHANCEMENT ENGINE              │
├───────────────────────────┬────────────────────────────┤
│   QUALITY OF LIFE (QoL)   │    BREAKTHROUGH FEATURES   │
│  "Remove the friction"    │    "Multiply the power"    │
├───────────────────────────┼────────────────────────────┤
│ • Reduce clicks / taps    │ • Autonomous AI automation │
│ • Instant feedback / Cmd+K│ • Smart predictive models  │
│ • Clear live observability│ • Multi-channel workflows  │
│ • Graceful self-healing   │ • Client value dashboards  │
│ • Operator ergonomics     │ • Monetization accelerators│
└───────────────────────────┴────────────────────────────┘
```

- **Quality of Life (QoL)**: Eliminates friction, frustration, cognitive load, and repetitive manual micro-tasks. QoL turns a functional product into a delightful, professional tool.
- **Breakthrough Features**: Introduces new autonomous capabilities, revenue vectors, or intelligence layers that unlock step-function improvements in business metrics.

---

## How to Run This Skill

When running an ideation or QoL session:

1. **Phase 1: Friction & Papercut Diagnostics (The 360° Audit)**: Inspect current system state, logs, UI components, and operator workflows.
2. **Phase 2: QoL Ideation across the 6 Ergonomic Vectors**: Brainstorm targeted friction-killers.
3. **Phase 3: Breakthrough Feature Ideation across the 4 Growth Vectors**: Generate strategic feature concepts.
4. **Phase 4: Objective Scoring & Prioritization (RICE Matrix)**: Filter and rank ideas.
5. **Phase 5: Production Blueprint Delivery**: Produce complete, implementation-ready specifications.

---

## Phase 1: Friction & Papercut Diagnostics (The 360° Audit)

Run a rapid diagnostic across the 4 primary operational surfaces:

### 1.1 — Developer & Operator Ergonomics
- [ ] Are common debugging workflows trapped behind manual database queries or log grepping?
- [ ] Can an operator trigger, replay, or inspect a lead/task with a single command or button?
- [ ] Are environment variables and secret configurations transparently validated on startup?
- [ ] Are test commands fast, targeted, and self-cleaning?
- [ ] Are error traces easy to correlate between frontend request, backend endpoint, and agent sub-task?

### 1.2 — User & Client Interface Papercuts
- [ ] Does table filtering or search reset unexpectedly on navigation?
- [ ] Is there keyboard accessibility for power users (e.g., `Cmd+K` / `Ctrl+K` command palette)?
- [ ] Are there empty states that guide the user on what action to take next?
- [ ] Are loading states responsive with skeletons or indicators, or do elements jump around?
- [ ] Can users execute bulk actions (e.g., bulk approve, bulk export, bulk archive) without repetitive clicks?
- [ ] Are status badges color-coded intuitively with clear tooltips explaining the state?

### 1.3 — Autonomous AI & Swarm Friction
- [ ] Can operators see what an agent is doing *right now* (live thought trace, tool call, status)?
- [ ] Is token consumption, execution latency, and cost per run visible per lead or campaign?
- [ ] If an agent encounters a rate limit or failure, does it auto-retry transparently with exponential backoff?
- [ ] Is there a human-in-the-loop override toggle to adjust prompt instructions or approve sensitive actions?
- [ ] Are fallback models cleanly configured when primary LLMs hit rate limits?

### 1.4 — Data & Telemetry Ergonomics
- [ ] Are stale data views automatically refreshed via WebSocket, SSE, or intelligent polling?
- [ ] Are dead-letter queue items or failed jobs visible and retryable with one click?
- [ ] Does the UI handle transient network drops gracefully with optimistic UI and auto-reconnect?

---

## Phase 2: QoL Ideation across the 6 Ergonomic Vectors

For any system area identified with friction, apply the 6 Ergonomic Vectors:

### Vector 1: Speed & Keystroke Reducers
- **Command Palette (`Cmd+K`)**: Instant search across leads, campaigns, settings, and agent actions.
- **Sticky Filters & URL State Sync**: Search terms, page numbers, and active tabs synced to URL query parameters so links can be bookmarked and refreshed without losing state.
- **Smart Presets**: One-click filters for "Needs Review", "High Value", "Failed in last 24h", "Active Swarms".
- **Quick-Action Drawers**: Slide-over panels to view or edit details without navigating away from tables.

### Vector 2: Clarity & Observability
- **Live Agent Activity Stream**: Real-time heartbeat indicator showing active workers, current processing queue, and completed jobs.
- **Step-by-Step Execution Trace Modal**: Click on any lead to see the exact timeline: Lead Ingestion → Enrichment → AI Evaluation → Delivery → Confirmation.
- **Live Throughput Counters**: Visual counter badges showing leads processed today, conversion rate, and active agent threads.

### Vector 3: Confidence & Safety Guardrails
- **Dry-Run / Preview Mode**: Allow operators to simulate an outbound campaign or agent run before executing live emails/webhooks.
- **Optimistic UI with Rollback**: Instant UI feedback when archiving or tagging, with immediate rollback and toast alert if the API call fails.
- **Destructive Action Confirmation Drawers**: Instead of generic browser `alert()` or `confirm()`, use clear modals showing affected record counts and consequences.

### Vector 4: Micro-Task Automation
- **Auto-Deduplication**: Intelligent fuzzy matching on lead email, phone, or company domain with inline duplicate warnings.
- **Auto-Tagging & Smart Classification**: AI agents auto-categorizing records on ingestion into clear buckets (e.g., `B2B-Enterprise`, `Local-SMB`, `High-Intent`).
- **Bulk Batch Transitions**: Multi-select table rows to reassign, change status, export CSV, or re-run enrichment in one click.

### Vector 5: Resilience & Self-Healing
- **Contextual Error Remediation**: Instead of raw `500 Internal Server Error`, display actionable resolution cards (e.g., *"Missing SendGrid API Key. Click here to configure"*).
- **Auto-Reconnecting Network State**: Banner alerting user of offline state with automatic replay queue once reconnected.
- **Idempotent Retries**: Retry buttons that guarantee safe re-execution without duplicate lead delivery or duplicate charges.

### Vector 6: Customization & Focus
- **View Density Toggles**: Switch between Compact (high-information table view for power operators) and Cozy (card view with visual previews).
- **Column Visibility Selector**: Persist user column choices in local storage.
- **Dark/Light Mode Perfection**: Flawless contrast adhering to WCAG 2.1 AA standards.

---

## Phase 3: Breakthrough Feature Ideation Engine

Brainstorm high-leverage product features across the 4 Growth Vectors:

### Vector A: Autonomous AI Value Multipliers
- **AI Lead Intent Scoring**: Real-time 0-100 scoring based on web signals, company headcount, tech stack, and recent hiring news.
- **Dynamic Personalized Outreach Generator**: Agents drafting 3 tailored outreach angles per lead, citing specific company news or pain points.
- **Competitive Intelligence Radar**: Agent background monitors alerting when a prospect switches tools or posts relevant job openings.
- **Autonomous Lead Healing**: If a contact email bounces or phone is invalid, agent autonomously re-searches alternate verified contacts.

### Vector B: Customer Lifecycle & Conversion Accelerators
- **Interactive Lead Delivery Portal**: Secure, authenticated client portal where buyers can rate lead quality (Thumbs up/down), triggering instant agent retraining.
- **Automated ROI Recap Digest**: Weekly scheduled email/PDF to clients summarizing: *"LeadOps generated 42 verified appointments worth an estimated $38,000 this week"*.
- **Self-Serve Custom Swarm Configurator**: Visual node-based or step-by-step wizard allowing users to configure custom scraping and filtering rules.

### Vector C: Operator & Mission Control Features
- **Swarm Topology Visualizer**: Real-time canvas diagram showing active worker containers, queue depths, throughput, and error rates.
- **Agent Sandbox & Prompt Lab**: In-app playground allowing operators to test prompts against live sample records before pushing to production agents.
- **Usage & Cost Metering Engine**: Detailed breakdown of LLM token spend, scraping proxy costs, and infrastructure utilization per campaign.

### Vector D: Monetization & Expansion Mechanisms
- **Credit Top-Up & Auto-Refill Guardrails**: Real-time balance tracker with automatic refill triggers when credits drop below threshold.
- **Tiered SLA Guarantees**: Differentiated queue priorities (Standard vs. Instant Fast-Track delivery).
- **Referral & Shareable Campaign Links**: One-click share links for campaigns with automated commission tracking.

---

## Phase 4: Scoring & Prioritization (RICE Matrix)

Evaluate every QoL idea and feature using the **RICE** framework:

$$\text{Score} = \frac{\text{Reach} \times \text{Impact} \times \text{Confidence}}{\text{Effort}}$$

| Dimension | Scale | Description |
|-----------|-------|-------------|
| **Reach (R)** | 1 - 10 | Percentage of users or workflows impacted weekly (10 = all operators/users every session). |
| **Impact (I)** | 0.5 - 3 | 3 = Massive delight/revenue, 2 = High impact, 1 = Moderate, 0.5 = Minor polish. |
| **Confidence (C)**| 50% - 100% | Certainty of technical feasibility and value realization (100% = proven pattern). |
| **Effort (E)** | 1 - 5 | Engineering effort in person-days (1 = < 1 day, 2 = 2-3 days, 5 = > 1 week). |

### Priority Quadrant Matrix

```
       HIGH IMPACT
            ▲
   BIG BETS │ QUICK WINS
   (Plan)   │ (DO FIRST!)
────────────┼────────────► LOW EFFORT
 TIME SINKS │ FILL-INS
  (Avoid)   │ (When idle)
            ▼
       LOW IMPACT
```

---

## Phase 5: Production Blueprint Delivery Template

When outputting an ideation session or feature proposal, use this structured blueprint:

```markdown
# [Feature / QoL Name]: Production Specification

## 1. Executive Summary & Problem Statement
- **User Story**: As a [Role], I want to [Action], so that [Outcome].
- **Friction Solved**: [Current manual toil or missing capability].
- **RICE Score**: Reach: [X] | Impact: [X] | Confidence: [X]% | Effort: [X] => **Score: [Total]**
- **Quadrant**: [Quick Win / Big Bet / Fill-In]

## 2. Frontend Architecture & UI/UX Spec (React)
- **Target Location**: `frontend/src/components/...` or `frontend/src/pages/...`
- **Component Hierarchy**:
  - `<MainView>`
    - `<HeaderActions>` (Cmd+K trigger, filters)
    - `<DataGrid>` (Live records, sortable, virtualized)
    - `<DetailDrawer>` (Contextual inspection, live agent trace)
- **State Management**: React Query / SWR / Zustand for live data caching.
- **Design Tokens**: Standardized CSS variables (colors, typography, spacing, border-radius).
- **Keyboard Shortcuts**: `[Key combo]` -> [Triggered action].

## 3. Backend & Data Contract (FastAPI + Live DB)
- **Zero Mock Rule**: Direct queries against PostgreSQL / SQLite database.
- **Endpoints**:
  - `GET /api/v1/...` -> Fetches real live records with pagination & filters.
  - `POST /api/v1/...` -> Executes action, returns updated state.
- **Pydantic Schema**:
  ```python
  class FeatureRequest(BaseModel):
      id: UUID
      ...
  ```
- **Database Migration**: Schema updates (if required) via Alembic.

## 4. AI Agent & Swarm Integration (If Applicable)
- **Agent Role**: [Specific autonomous agent].
- **Trigger Hook**: [EventBus / Service Bus / API Trigger].
- **Tools Provided**: [List of tools exposed to agent].
- **Failure Boundary**: [Retry policy, circuit breaker, human alert threshold].

## 5. Production Readiness & Verification Checklist
- [ ] No hardcoded mock data (live DB records verified).
- [ ] Responsive UI verified on mobile (390px) and desktop (1440px).
- [ ] Loading, error, and empty states fully implemented.
- [ ] API routes protected with auth validation.
- [ ] Automated tests passing (unit + integration).
```

---

## Golden Rules for Execution

1. **Never Propose Mocking in Production**: Always wire to live schemas, actual endpoints, and real data models.
2. **Respect the Stack Boundary**: React handles the presentation and interactive user delight. Python / FastAPI / Swarm handles data, LLM calls, and async background workers.
3. **Solve the Most Painful 20% First**: 80% of operator frustration usually comes from 3 papercuts: slow search, lack of execution visibility, and lost filter state. Fix those before building complex wizards.
4. **Make Autonomous Systems Visible**: If an AI agent does work in the background, make its progress, decisions, and outcomes transparent to the human operator.
