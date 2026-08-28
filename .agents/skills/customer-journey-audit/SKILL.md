---
name: customer-journey-audit
description: >
  Comprehensive customer journey audit skill for identifying friction points,
  dead-ends, and conversion killers across every stage of an automated system's
  customer lifecycle — from Discovery through Referral. Covers UI/UX copy,
  backend logic, emotional arc, urgency mechanics, trust signals, objection
  handling, and KPIs. Produces a stage-by-stage scored report with prioritized
  fixes, checklists, and narrative analysis. Applicable to any automated product:
  SaaS, B2B outbound, lead delivery, subscription services, or AI-driven pipelines.
---

# Customer Journey Audit Skill

Run a structured, full-lifecycle audit of how your automated system moves a
prospect from first touch to loyal advocate. This skill helps you identify
friction points, broken flows, missing trust signals, and weak copy at every
stage — and tells you exactly what to fix and in what order.

---

## How To Run

When the user asks to audit the customer journey (or a specific stage), follow
these phases in order. Skip phases only if the user explicitly scopes the audit.

---

## Phase 1: Map the Existing Journey

Before auditing, understand what the system currently does.

### 1.1 — Identify All Touchpoints

- **Discovery**: How does a prospect first encounter the product? (cold outreach,
  landing page, SEO, referral, ad, marketplace listing)
- **Activation**: What is the first meaningful action? (claim a sandbox, sign up,
  book a demo, submit a form)
- **Conversion**: What turns a prospect into a paying customer? (checkout, deposit,
  subscription start)
- **Retention**: How is the customer kept active? (delivery cadence, check-ins,
  portal updates, drift monitoring)
- **Expansion**: What upsell paths exist? (tier upgrade, buyout offer, add-on seats)
- **Win-back**: How are churned or stalled prospects re-engaged? (follow-up
  sequences, reactivation offers)
- **Referral**: How do happy customers generate new prospects? (share links,
  testimonials, case studies)

### 1.2 — Map the Backend Flow

- Trace the state machine: what states exist and what triggers transitions?
- Identify automated triggers: emails, webhooks, cron jobs, agent actions
- Identify manual gates: human approval required, founder review, etc.
- List all customer-facing surfaces: landing pages, portal templates, emails,
  notifications, chat interfaces

### 1.3 — Establish the Baseline Metrics (if available)

- Conversion rate at each stage (if tracked)
- Drop-off points (where do prospects go silent?)
- Time-to-convert (how long from first touch to deposit/subscription?)
- Support volume by stage (what questions do prospects repeatedly ask?)

---

## Phase 2: Discovery & Awareness Audit

### 2.1 — First Impression Checklist

- [ ] The value proposition is clear in ≤ 5 seconds on the landing page
- [ ] The hero headline speaks to the prospect's pain, not the product's features
- [ ] There is a single, obvious primary CTA (not 3+ competing buttons)
- [ ] Social proof is visible above the fold (testimonials, logos, case count)
- [ ] No jargon or internal terminology that a new prospect wouldn't understand
- [ ] The page loads in < 3 seconds on mobile

### 2.2 — Discovery Friction Scan

- [ ] Are there broken links or 404s on any discovery surface?
- [ ] Does outreach copy have a specific, personalized hook? (Not generic)
- [ ] Is the reply-to or contact path clear? (No dead-end "do not reply" emails)
- [ ] Are there multiple discovery channels or is the system single-threaded/fragile?

### 2.3 — Discovery Scoring

Rate each item: ✅ Pass | ⚠️ Needs Work | ❌ Fail

---

## Phase 3: Activation Audit

The "aha moment" — the first action that makes the prospect feel value.

### 3.1 — Activation Flow Checklist

- [ ] The first action requires ≤ 3 clicks from landing page
- [ ] Sign-up / claim form has ≤ 5 fields (minimize ask at top of funnel)
- [ ] A personalized sandbox, demo, or preview is generated automatically
  (prospect sees their data/use-case, not generic demo data)
- [ ] Confirmation feedback is immediate and celebratory ("Your sandbox is live!")
- [ ] The next step is explicit — the user is never left wondering "what now?"
- [ ] Activation works without human intervention (fully automated)
- [ ] Error states on the activation form are helpful, not generic ("Email invalid"
  not just a red border)

### 3.2 — Activation Emotional Arc Check

At the end of activation, the prospect should feel:
- **Excited** — they got something real and personalized
- **Safe** — they haven't been asked for money yet
- **Curious** — they want to see what the full product does

Check: Does the current activation flow produce these feelings, or does it feel
like "just another form"?

### 3.3 — Backend Activation Logic Audit

- [ ] Activation events are logged with timestamps
- [ ] Failed activations (errors, timeouts) trigger an alert or retry
- [ ] No activation requires a manual step from the operator to complete
- [ ] The activated state is durable (sandbox persists after browser close)

---

## Phase 4: Conversion Audit

### 4.1 — Conversion Friction Scan

- [ ] The price is shown before the CTA (no surprise at checkout)
- [ ] The checkout flow is ≤ 3 steps
- [ ] The deposit/payment amount and what it covers is crystal clear
- [ ] There is a visible guarantee or refund policy (reduces perceived risk)
- [ ] Payment errors are caught and explained clearly (not just a generic failure)
- [ ] A success state is shown immediately after payment (confirmation page + email)
- [ ] The post-payment next step is explicit ("Your build starts in 24 hours")

### 4.2 — Urgency & Scarcity Mechanics Audit

Legitimate urgency creates action; fake urgency destroys trust. Check:

- [ ] **Time-based urgency**: Is there a real deadline? (e.g. "Sandbox expires in 48h")
  If so, is it actually enforced in the backend?
- [ ] **Slot-based scarcity**: Is there a real capacity limit? (e.g. "3 of 5 slots
  remaining this month") If so, is it actually tracked?
- [ ] **Social proof urgency**: Are recent customer actions visible? ("2 companies
  claimed a sandbox this week in your county")
- [ ] ⚠️ **Anti-pattern check**: Are any urgency claims fabricated or not enforced?
  (This destroys trust when customers discover it)

### 4.3 — Trust Signals at Conversion Checklist

- [ ] Company/operator identity is verifiable (LinkedIn, about page, email domain)
- [ ] Sample data is real (from the prospect's actual target source, not synthetic)
- [ ] Payment processor is recognized (PayPal, Stripe — not a custom form)
- [ ] A clear Statement of Work or service contract is shown before payment
- [ ] Privacy policy / data handling policy is linked

### 4.4 — Objection Handling Inventory

For each common objection, verify there is a visible answer on the conversion page
or in the outreach sequence:

| Objection | Current Answer | Gap? |
|-----------|---------------|------|
| "How do I know the data is real?" | | |
| "What if the data quality is bad?" | | |
| "What happens if I want to cancel?" | | |
| "Why should I trust you?" | | |
| "Is this legal / compliant?" | | |
| "What if my county portal changes?" | | |

---

## Phase 5: Retention Audit

### 5.1 — Retention Touchpoints Checklist

- [ ] Customer receives a delivery confirmation on every scheduled delivery
- [ ] Customer has a self-serve portal to check delivery status (no "email us" required)
- [ ] Delivery failures trigger immediate notification + ETA for resolution
- [ ] Customer can see historical deliveries (audit trail visible in portal)
- [ ] Regular "value reminder" touchpoints exist (monthly report, milestone email)
- [ ] Subscription renewal is automated with pre-renewal notification (≥ 7 days notice)

### 5.2 — Drift & Decay Detection

- [ ] A monitoring system detects when the data source changes (site redesign,
  schema change, WAF upgrade)
- [ ] Drift is caught before the customer notices a bad delivery
- [ ] The customer is proactively notified of any disruption with a resolution timeline
- [ ] There is a defined SLA for delivery failures (e.g. "resolved within 24 hours")

### 5.3 — Retention Emotional Arc

The retained customer should feel:
- **Confident** — deliveries arrive as promised, on schedule
- **Informed** — they always know what's happening
- **Valued** — they feel like a priority, not a ticket number

---

## Phase 6: Expansion Audit

### 6.1 — Upsell Path Checklist

- [ ] The next tier or upgrade is visible in the portal (not hidden)
- [ ] The upgrade benefit is concrete ("Get 25 fields instead of 15, plus daily delivery")
- [ ] The upgrade CTA appears at the right moment (after a successful delivery, not
  immediately after signup)
- [ ] A buyout/ownership option is presented to long-term subscribers as a milestone offer
- [ ] Price delta is shown ("Upgrade for just $250/mo more")

### 6.2 — Expansion Timing Check

- [ ] Upsell offers are triggered by usage events (high field usage, high open rate)
  not just by time elapsed
- [ ] No upsell is shown to a customer who hasn't yet received their first delivery

---

## Phase 7: Win-Back Audit

### 7.1 — Churn Signal Detection

- [ ] The system detects when a customer goes quiet (no portal logins, no responses)
- [ ] Churn signals trigger an automated follow-up sequence (not manual)
- [ ] The follow-up sequence has a specific value hook, not just "checking in"

### 7.2 — Win-Back Sequence Checklist

- [ ] Email 1 (Day 3 of silence): Check-in with a new data sample or insight
- [ ] Email 2 (Day 7): Specific objection address ("Worried about X? Here's how we handle it")
- [ ] Email 3 (Day 14): A time-limited offer or price lock ("Lock in your current rate for 6 months")
- [ ] After Email 3: Archive the prospect, don't spam

---

## Phase 8: Referral Audit

### 8.1 — Referral Mechanism Checklist

- [ ] There is a defined moment to ask for a referral (after first successful delivery)
- [ ] The referral ask is specific ("Know another title company in Texas?")
- [ ] There is a referral incentive (discount, free month, commission)
- [ ] The referral path is easy (shareable link, pre-filled email template)
- [ ] Referral tracking is in place (attribution to referrer)

---

## Phase 9: Dead-End Detection

Scan every automated flow for dead-ends — states where a user can get stuck with
no path forward.

### 9.1 — Dead-End Checklist

- [ ] Every error page has a recovery path (retry button, contact link, back button)
- [ ] Every automated email has a reply path (not "do-not-reply" address)
- [ ] Every waiting state has a status indicator ("Your build is in progress, ETA 24h")
- [ ] Payment failure states show what to do next (try again, contact support)
- [ ] Session expiry is handled gracefully (redirect to login, not blank page)
- [ ] API timeouts surface a user-friendly message, not a raw error or blank screen
- [ ] Background job failures notify the operator (not just silently logged)

### 9.2 — State Machine Dead-End Scan

For each state in the backend state machine, verify:
- There is at least one forward transition (no permanent terminal states except "ARCHIVED")
- The `BLOCKED_NEEDS_REVIEW` state has an automated operator notification
- No state has been in place for > 48 hours without a trigger or human review flag

---

## Phase 10: Copy & Messaging Audit

### 10.1 — Copy Quality Checklist

For every customer-facing surface (landing page, portal, emails, notifications):

- [ ] **Clarity**: Can a non-technical person understand this in 5 seconds?
- [ ] **Specificity**: Uses concrete numbers/outcomes, not vague promises
  ("25 verified probate cases per week" not "lots of leads")
- [ ] **Active voice**: "We deliver your data every Monday" not "Data is delivered"
- [ ] **Emotional resonance**: Addresses fear, desire, or urgency relevant to the
  prospect's situation
- [ ] **CTA clarity**: Every page/email has one clear next action
- [ ] **No orphan copy**: No text that references features not yet built

### 10.2 — Subject Line & Outreach Audit

Score each outreach touchpoint:

| Touchpoint | Subject / Hook | Personalized? | Clear CTA? | Grade |
|------------|---------------|---------------|------------|-------|
| Cold email 1 | | | | |
| Follow-up email | | | | |
| Sandbox notification | | | | |
| Deposit confirmation | | | | |
| Delivery notification | | | | |
| Churn re-engagement | | | | |

---

## Phase 11: Metrics & KPIs Checklist

For each stage, verify the system tracks the minimum viable metrics:

| Stage | Metric to Track | Currently Tracked? |
|-------|----------------|-------------------|
| Discovery | Outreach open rate, click rate | |
| Activation | Sandbox claim rate, time-to-activate | |
| Conversion | Deposit conversion rate, checkout abandonment | |
| Retention | Delivery success rate, portal login frequency | |
| Expansion | Upsell acceptance rate | |
| Win-back | Re-engagement rate within 14 days | |
| Referral | Referrals per customer, referral conversion rate | |

---

## Phase 12: Report & Prioritize

### Output Format

Produce a findings report as a markdown artifact (`journey_audit_report.md`) with:

```markdown
# Customer Journey Audit Report — [Date]

## Executive Summary
Overall journey health, top 3 friction killers, overall conversion arc score.

## Stage-by-Stage Scores
| Stage       | Score | Grade | Top Issue |
|-------------|-------|-------|-----------|
| Discovery   | X/10  | A-F   |           |
| Activation  | X/10  | A-F   |           |
| Conversion  | X/10  | A-F   |           |
| Retention   | X/10  | A-F   |           |
| Expansion   | X/10  | A-F   |           |
| Win-back    | X/10  | A-F   |           |
| Referral    | X/10  | A-F   |           |
| **Overall** | X/10  | A-F   |           |

## Critical Friction Points (Fix First)
Findings that directly block conversion or cause customer churn.

## High Priority Fixes
Findings that significantly reduce conversion rate or increase drop-off.

## Medium Priority Improvements
Findings that reduce trust, add unnecessary steps, or weaken messaging.

## Low Priority Polish
Nice-to-have improvements that add delight without removing friction.

## Narrative Analysis
Stage-by-stage narrative: what the customer experiences, where they feel
friction, what their emotional state is, and what needs to change.

## Recommended Action Plan
Ordered list of fixes with effort estimates and expected impact on conversion.
```

### Severity Definitions

| Severity | Definition | Example |
|----------|-----------|---------|
| 🔴 Critical | Blocks conversion or causes immediate churn | Checkout errors silently, no recovery path |
| 🟠 High | Major friction that increases drop-off rate | Activation requires 7 fields to fill |
| 🟡 Medium | Reduces trust or adds unnecessary steps | No confirmation email after deposit |
| 🟢 Low | Reduces delight or polish | Generic email subject line |

---

## Tips for Running This Audit

1. **Read the codebase**: Check state machines, route handlers, and templates for
   logic gaps that create dead-ends
2. **Read the copy**: Open every template (HTML, email, notification) and read it as
   the customer would
3. **Trace every flow**: Manually walk each journey stage, noting every click,
   every wait, every decision point
4. **Use browser automation**: Capture screenshots of every customer-facing page
5. **Check timing**: Measure the time between stages — long delays are hidden friction
6. **Interview the operator**: Ask "What questions do customers ask most often?"
   — these are the friction points the system hasn't solved yet
7. **Compare to benchmark**: Reference world-class examples (Stripe, Linear,
   Notion onboarding) for each stage
