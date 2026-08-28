---
name: automated-workflow-designer
description: >
  Brainstorming and design skill for building automated customer workflows on
  any system. Builds on customer-journey-audit findings to translate friction
  points and gaps into concrete, sequenced automation blueprints. Covers
  trigger/action/condition thinking, engagement sequence design, simplification
  patterns, and channel selection. Produces a ready-to-implement workflow spec
  with pseudocode, timing diagrams, and copy templates for any customer lifecycle
  stage. Works for SaaS, B2B outbound, lead delivery, subscription services,
  or AI-driven pipelines.
---

# Automated Workflow Designer Skill

Use this skill after running `customer-journey-audit` (or independently) to
brainstorm, map, and spec out automation that reduces friction, creates customers,
and keeps them engaged — all without requiring human intervention per touchpoint.

---

## Core Mental Model: The TAC Framework

Every automation is built from three primitives:

```
TRIGGER → ACTION → CONDITION
```

- **TRIGGER**: Something that happened (event, time, state change, user action, silence)
- **ACTION**: What the system does in response (email, state change, SMS, webhook, task)
- **CONDITION**: Rules that gate the action (is this user eligible? was this done before?)

Think in TAC chains. Complex workflows are just multiple TAC steps linked together.

---

## How to Run This Skill

1. Read the `customer-journey-audit` findings (or run it first)
2. Walk each **Gap Stage** from the audit
3. For each gap: brainstorm TAC chains that fill it
4. Select the highest-impact workflows and spec them out fully
5. Output a **Workflow Blueprint** per automation
6. Output a **Master Workflow Registry** at the end

---

## Phase 1: Gap Inventory

Before brainstorming, list every stage with a gap. Pull from `journey_audit_report.md`
or assess fresh. For each stage, note:

- What should be happening automatically that isn't?
- What human step can be replaced by a trigger?
- What silence (no action) is an opportunity for engagement?

### Gap Inventory Template

| Stage | What's Missing | Trigger Opportunity | Priority |
|-------|---------------|---------------------|----------|
| Discovery | | | |
| Activation | | | |
| Conversion | | | |
| Retention | | | |
| Expansion | | | |
| Win-back | | | |
| Referral | | | |

---

## Phase 2: Brainstorm Mode — The 7 Automation Categories

For every gap, brainstorm across all 7 categories. Not every category applies
to every gap — but forcing yourself through all 7 often uncovers non-obvious
solutions.

### Category 1 — TIME-BASED TRIGGERS
*"Something should happen N hours/days after an event."*

Examples:
- 24h after sandbox created → follow-up email if no checkout
- 48h after deposit paid → "build started" status update to customer
- 7 days after delivery → "how is the data working for you?" check-in
- 14 days of silence → churn detection alert

Brainstorm questions:
- What window of time after each event represents a healthy vs. unhealthy customer?
- What would you say to a customer 1h, 24h, 72h, 7d, 30d after each event?
- Where is silence the loudest signal?

---

### Category 2 — STATE-CHANGE TRIGGERS
*"When a domain object moves from state A to state B, something should happen."*

Map every state transition in your state machine and ask: "What should the
customer/operator see/feel/receive when this happens?"

| Transition | Who gets notified? | What message? | What next step? |
|-----------|-------------------|---------------|----------------|
| PROSPECTING → DEPOSIT_PAID | Customer + Operator | | |
| DEV_BUILDING → ESCROW_PREVIEW | Customer | | |
| ESCROW_PREVIEW → FINAL_PAID | Customer | | |
| FINAL_PAID → DELIVERED | Customer | | |
| DELIVERED → WARRANTY_ACTIVE | Customer | | |
| Any → BLOCKED_NEEDS_REVIEW | Operator | | |

---

### Category 3 — BEHAVIOR-BASED TRIGGERS
*"The customer did something (or didn't do something)."*

Positive behaviors to amplify:
- Opened the sandbox → push to checkout sooner
- Exported CSV → they're serious; fast-track to deposit CTA
- Used the chat → they're engaged; respond with a personalized follow-up
- Logged into the dashboard → they're active; show upsell

Negative behaviors to catch:
- Opened the portal but never clicked checkout → re-engagement sequence
- Had a delivery but never logged into dashboard to view it → "did you see your records?" nudge
- PayPal checkout window opened but not completed → cart abandonment recovery

---

### Category 4 — THRESHOLD-BASED TRIGGERS
*"Something crossed a number threshold."*

Examples:
- QA score reaches 95 → automatically unlock escrow preview and notify customer
- Delivery #3 completed → trigger buyout offer (proven value, now pitch ownership)
- Customer has used 14/15 allowed fields → "you're at your field limit; upgrade for 25"
- Drift incident count reaches 2 in 30 days → proactive customer notification + SLA check

---

### Category 5 — EXTERNAL EVENT TRIGGERS
*"Something in the outside world happened."*

Examples:
- PayPal webhook fires `PAYMENT.CAPTURE.COMPLETED` → advance lead state, send receipt
- County portal schema changes (drift detected) → pause delivery, alert operator, notify customer
- Google Sheets API returns 401 → delivery failure email to customer + retry queue
- Scout discovers a new matching prospect → automatically generate sandbox, queue outreach

---

### Category 6 — SEQUENCE / DRIP TRIGGERS
*"A series of messages sent at scheduled intervals, starting from a trigger event."*

Design each sequence as a decision tree:
```
Event → Email 1 → [Opened?]
    → Yes → Wait 2 days → Email 2 (deeper value)
    → No  → Wait 1 day  → Resend Email 1 (different subject)
                        → [Opened?]
                            → Yes → Email 2
                            → No  → Wait 3 days → Archive or Pivot
```

Sequences to design for LeadOps:
- **Post-Sandbox Sequence** (discovery → activation gap)
- **Post-Deposit Sequence** (conversion → retention gap)
- **Post-Delivery Sequence** (retention → expansion gap)
- **Win-Back Sequence** (churn detection → re-engagement)
- **Referral Sequence** (post-delivery #3 → referral ask)

---

### Category 7 — PERSONALIZATION TRIGGERS
*"The message changes based on who the customer is."*

Every workflow should ask: what do we know about this customer that makes
the message more specific?

Available data points in LeadOps:
- `company_name`, `contact_email`
- `tier_key` (weekly/daily/ai/buyout)
- `jurisdiction` (county/state)
- `niche` (probate, liens, etc.)
- `selected_fields` (what they asked for)
- `qa_score`, `preview_rows`
- `deposit_paid`, `final_paid`, `subscription_active`
- `state` (current lifecycle stage)
- `audit_log` (history of state transitions with timestamps)

Use these to personalize:
- Subject lines: `f"{niche} records from {jurisdiction} — your {delivery_cadence} feed is ready"`
- Body copy: Reference specific data the customer asked for
- CTAs: Match the tier ("Your Weekly Sync delivered 47 new records this Monday")

---

## Phase 3: Workflow Spec Template

For each automation you decide to build, complete this spec:

```markdown
## Workflow: [Name]

**Purpose:** [1 sentence — what gap does this fill?]
**Stage:** [Discovery / Activation / Conversion / Retention / Expansion / Win-back / Referral]
**Revenue Impact:** [Estimated impact: unblocks $X, reduces churn by Y%, etc.]
**Effort:** [XS / S / M / L]

### Trigger
- **Type:** [Time-based / State-change / Behavior / Threshold / External / Sequence / Personalized]
- **Condition:** [Exact trigger condition — what must be true?]
- **Source:** [What system produces this event? State machine? Webhook? Cron? User action?]

### Eligibility Check (Conditions)
Before the action runs, verify:
- [ ] Condition 1
- [ ] Condition 2
- [ ] Not already sent this workflow to this customer (idempotency)

### Action(s)
1. **Action 1:** [Email / State change / Webhook / API call / Internal alert]
   - Channel: [SendPulse / Portal notification / Slack / etc.]
   - Timing: [Immediate / Delayed N minutes/hours]
   - Template: [Paste subject + body template below]

2. **Action 2:** [If chained]

### Branch Logic
- If [condition]: → do [action A]
- Else: → do [action B] or wait N days

### Copy Template
**Subject:** [Subject line with merge fields]
**Body:**
```
[Message body — keep under 100 words for email, under 160 chars for SMS]
```

### Success Metric
- How do you know this automation is working?
- What does a good open rate / conversion rate look like?

### Implementation Notes
- File to modify: [e.g. agents/pitcher.py, run_server.py]
- New function/class needed: [Yes/No — describe]
- Dependencies: [SendPulse credentials, PayPal webhook, etc.]
```

---

## Phase 4: The 12 Universal Automation Blueprints

These are the most impactful automations for any customer-facing system.
Adapt them to the specific product, then fill in the Workflow Spec template.

---

### Blueprint 1 — The Magic Link Activation

**What:** When a new prospect is identified, automatically generate a personalized
experience (sandbox, demo, preview) and send a single magic link.

**TAC:**
- **Trigger:** New lead created (Scout discovery or manual import)
- **Action:** Generate sandbox → send personalized email with sandbox URL
- **Condition:** Lead is in PROSPECTING or REVIEW state; not previously emailed

**Copy pattern:**
> Subject: `[N] [niche] records from [county] — pulled for [company_name]`
> Body: Hi [name], we extracted a sample of [N] recent [niche] records
> from [county] for [company_name]. Review your free preview: [magic link]

**LeadOps implementation:** Already partially built in `pitcher.py`. Needs
Scout-to-email automation wiring so pitches fire without manual approval.

---

### Blueprint 2 — The Abandoned Sandbox Recovery

**What:** If a prospect opens the sandbox but doesn't reach checkout within 24h,
send a follow-up email with a specific hook from their data.

**TAC:**
- **Trigger:** Sandbox created + 24h elapsed + checkout not completed
- **Action:** Send follow-up email referencing the prospect's county/niche
- **Condition:** `state in {PROSPECTING, REVIEW, OUTREACH_SENT}` + sandbox visited

**Copy pattern:**
> Subject: `Still thinking about those [county] [niche] records?`
> Body: Hi [name], your free preview of [N] [niche] cases from [county]
> expires in 48 hours. Reply with any questions and I'll jump on a quick
> call to walk you through the delivery setup.

---

### Blueprint 3 — The Deposit Confirmation + What's Next

**What:** Immediately after deposit paid, send a confirmation email with a clear
24-48h build timeline and the customer's unique dashboard URL.

**TAC:**
- **Trigger:** `PAYMENT.CAPTURE.COMPLETED` webhook + `custom_id = "deposit"`
- **Action:** Advance state to `DEPOSIT_PAID` + send confirmation email
- **Condition:** `record_webhook_event(event_id)` returns True (idempotent)

**Copy pattern:**
> Subject: `✅ Deposit received — your [county] feed is being built`
> Body: [name], your $250 deposit for the [company_name] automated feed
> is confirmed. Our build team is now extracting and validating your
> [niche] records from [county]. You'll receive a preview within 24 hours.
> Track your build: [dashboard URL]

---

### Blueprint 4 — The Build Progress Heartbeat

**What:** Send a progress update every 8h during the build phase so the customer
feels informed, not abandoned.

**TAC:**
- **Trigger:** Cron every 8h while `state == DEV_BUILDING`
- **Action:** Send build status email with current agent phase (Planner / Builder / QA)
- **Condition:** Not more than 3 heartbeats sent total; state still DEV_BUILDING

**Copy pattern:**
> Subject: `[company_name] feed — build update (QA in progress)`
> Body: Quick update: your data feed is passing QA verification now.
> We'll send you a preview link as soon as we hit 95% accuracy threshold.
> No action needed from you.

---

### Blueprint 5 — The Escrow Preview Celebration

**What:** When QA passes 95% and 25 preview rows are ready, send a "your preview
is live" email with the preview link and a clear "approve to finalize" CTA.

**TAC:**
- **Trigger:** `state → ESCROW_PREVIEW` (state transition)
- **Action:** Send "your preview is ready" email + in-portal notification
- **Condition:** `qa_score >= 95` and `preview_rows == 25`

**Copy pattern:**
> Subject: `🎉 Your [county] data preview is live — approve to unlock delivery`
> Body: [name], your automated [niche] feed passed QA with a 97% accuracy
> score. Your 25 verified preview records are ready to review:
> [preview URL]. Approve now to authorize final delivery and activate your
> subscription.

---

### Blueprint 6 — The Delivery Confirmation

**What:** After every successful delivery run, send a delivery receipt with a
record count and delivery destination.

**TAC:**
- **Trigger:** `DeliveryWorkflow.run()` completes successfully
- **Action:** Send delivery receipt email via SendPulse
- **Condition:** Delivery result is non-empty (rows > 0)

**Copy pattern:**
> Subject: `✅ [N] new [niche] records delivered — [weekday], [date]`
> Body: Your automated feed delivered [N] new [county] [niche] records
> to your Google Sheet at 6:02 AM UTC. Next delivery: [next date].
> View your dashboard: [URL]

---

### Blueprint 7 — The Drift Alert (Customer-Facing)

**What:** If a drift incident is detected before delivery, proactively notify the
customer before they notice a missed or late delivery.

**TAC:**
- **Trigger:** `DriftIncident` created with severity `HIGH` or `CRITICAL`
- **Action:** Send proactive notification email to customer + internal alert
- **Condition:** Incident not already notified (`incident.status == "OPEN"`)

**Copy pattern:**
> Subject: `[county] feed — maintenance notice (resolved within 4 hours)`
> Body: [name], our monitoring system detected a change in the [county]
> public records portal. Your feed is temporarily paused while our system
> adapts. We'll confirm resolution within 4 hours. No action needed from you.

---

### Blueprint 8 — The Upsell Trigger (After Delivery #3)

**What:** After the 3rd successful delivery, offer the customer an upgrade to a
higher tier or the buyout option.

**TAC:**
- **Trigger:** Delivery count reaches 3 for a customer on `weekly` or `daily` tier
- **Action:** Send "you're getting value — ready to scale?" email
- **Condition:** `tier_key != "ai"` and `tier_key != "buyout"`; not previously offered

**Copy pattern (weekly → daily upgrade):**
> Subject: `Getting value from your weekly feed? Here's how to 5x the volume`
> Body: [name], you've now received 3 weekly deliveries of verified
> [niche] records from [county]. For just $250/mo more, you can upgrade to
> daily delivery — 5x the records, same setup, zero extra work. Want me
> to activate the upgrade?

**Copy pattern (any tier → buyout):**
> Subject: `Own your [county] extractor outright — one-time $1,500`
> Body: After 3 successful deliveries, you clearly have a winning data
> source. For $1,500 (one-time), you can own the complete extraction
> codebase and run it yourself forever. No monthly fees, no dependency on us.
> Interested? Reply and we'll set it up this week.

---

### Blueprint 9 — The Churn Detection + Win-Back Sequence

**What:** Detect customers who haven't logged into the portal in 14 days and
trigger a 3-email re-engagement sequence.

**TAC chain:**

```
DAY 0:  Portal login event (last seen timestamp)
DAY 14: Cron detects no login in 14 days → Email 1 (value re-hook)
DAY 17: No click/open on Email 1 → Email 2 (objection address)
DAY 21: No click/open on Email 2 → Email 3 (limited offer)
DAY 25: No response → Flag for ARCHIVED; stop sequence
```

**Email 1 (Day 14) — Value Re-hook:**
> Subject: `[N] new [niche] records have piled up — want a recap?`
> Body: [name], [N] new [county] [niche] records have been delivered
> since you last checked in. Here's what you've been getting automatically:
> [delivery summary]. Your dashboard: [URL]

**Email 2 (Day 17) — Objection Address:**
> Subject: `Everything OK with your [county] feed?`
> Body: [name], just checking in — is there anything about the data or
> delivery that isn't working for your workflow? I can adjust the schema,
> change the destination, or pause deliveries if you need a break. Just reply.

**Email 3 (Day 21) — Limited Offer:**
> Subject: `Price lock offer: keep your [county] rate for 12 months`
> Body: [name], I want to make sure your [niche] data pipeline keeps
> running. If you stay active this week, I'll lock in your current rate
> for the next 12 months — no increases, even as we expand coverage.
> Reply "YES" and I'll activate the lock.

---

### Blueprint 10 — The Referral Ask

**What:** After the 1st successful delivery, ask the customer if they know anyone
else who could use the same feed.

**TAC:**
- **Trigger:** `state == DELIVERED` + delivery count reaches 1
- **Action:** Send referral ask email with a specific, niche-relevant prompt
- **Condition:** Not previously sent referral ask to this customer

**Copy pattern:**
> Subject: `Know another [niche] firm in [state]?`
> Body: [name], glad to see your [county] data feed is running smoothly.
> Quick ask: do you know any other [title companies / law firms / investors]
> in [state] who manually pull [niche] records from county portals?
> If so, I'd love to build them a free preview — and I'll give you one
> free month of service for every referral that converts. Just forward
> this email with their name.

---

### Blueprint 11 — The Scope Approval Automation

**What:** When a customer chats with Alex and requests a schema change, automatically
generate a scope update confirmation and route it for approval without human
intervention.

**TAC:**
- **Trigger:** Chat message processed + schema fields updated
- **Action:** Auto-generate updated field list → send "confirm your updated schema" email
- **Condition:** Field count <= tier max_fields

**Copy pattern:**
> Subject: `Confirm your updated [niche] schema — [N] fields selected`
> Body: [name], here's your updated data schema for the [county] feed:
> [field list]. Reply "CONFIRMED" to lock this in and apply it to your
> next delivery. Any changes? Just reply with edits.

---

### Blueprint 12 — The Operator Morning Briefing

**What:** Every morning, send the operator a summary of overnight events: new leads,
pending approvals, build statuses, drift incidents, and revenue events.

**TAC:**
- **Trigger:** Cron at 7:00 AM local time every weekday
- **Action:** Query all leads, build a digest email, send to operator
- **Condition:** Always (unconditional daily briefing)

**Briefing sections:**
1. 🆕 New sandboxes created overnight (Scout discoveries)
2. ⏳ Leads awaiting outreach approval
3. 💳 Payments received / pending
4. 🔨 Builds in progress + ETA
5. ⚠️ Drift incidents open
6. ✅ Deliveries completed overnight
7. 📉 Customers flagged for churn risk

---

## Phase 5: Workflow Registry Output

After brainstorming and speccing, produce a registry document:

```markdown
# Workflow Registry — [System Name]

## Active Workflows
| ID | Name | Stage | Trigger Type | Status | Effort |
|----|------|-------|--------------|--------|--------|
| W01 | Magic Link Activation | Discovery | State-change | ✅ Built | — |
| W02 | Abandoned Sandbox Recovery | Activation | Time-based | 🔲 Needed | S |
...

## Workflow Dependency Map
[Which workflows depend on other workflows being built first?]

## Channel Coverage
| Channel | Workflows Using It | Status |
|---------|-------------------|--------|
| SendPulse Email | W01, W02, W03... | ✅ Configured |
| In-portal notification | W05 | 🔲 Not built |
| Operator Slack/email alert | W12 | 🔲 Not built |

## Trigger Coverage
| Trigger Type | Covered By | Gaps |
|-------------|-----------|------|
| State transitions | W01, W05 | DEV_BUILDING has no outbound trigger |
| Time-based | W02, W09 | No 24h sandbox expiry |
| Webhooks | W03 | PayPal SUBSCRIPTION events uncovered |
```

---

## Phase 6: Simplification Pass

After designing all workflows, run a simplification pass:

### Consolidation Check
- Can any 2 workflows be merged into 1? (e.g. Deposit Confirmation + Build Heartbeat #1)
- Are any two workflows sending to the same customer within 24h? (fatigue risk)
- Is any workflow redundant with an existing manual process?

### Fatigue Check
- Map the maximum number of emails a customer can receive in one week
- If > 4 emails/week: consolidate or space out
- Every email should feel like help, not noise

### Channel Diversification
Not all engagement has to be email. For each workflow, ask:
- Could this be an in-portal notification instead? (less intrusive)
- Could this be a dashboard badge/counter? (passive engagement)
- Could this be a webhook to the customer's Slack? (high-value customers)
- Could this be a Google Sheet annotation? (delivery-context)

### "Would I Want to Receive This?" Test
For each workflow, read the email as the customer. Ask:
- Is this useful to me right now?
- Does this tell me something I didn't already know?
- Is the ask clear and easy to complete?
- Would I feel annoyed or grateful to receive this?

If the answer is "annoyed" — cut it, delay it, or make it more specific.

---

## Output Format

Produce two artifacts:

### 1. `workflow_brainstorm.md`
A creative dump of all brainstormed automation ideas, organized by stage,
with rough TAC sketches. This is the working doc — not polished.

### 2. `workflow_registry.md`
The final spec document containing:
- Completed Workflow Spec Template for each selected automation
- Priority-ordered implementation list
- Channel coverage map
- Dependency map
- Estimated effort and revenue impact per workflow

---

## Integration with Customer Journey Audit

This skill is designed to be run **after** `customer-journey-audit`:

1. Pull the **Gap Inventory** from the audit report
2. For each gap rated 🔴 or 🟠, design at least one workflow using Phase 2-3 above
3. For each gap rated 🟡, brainstorm at least one automation idea
4. Reference the audit's **Narrative Analysis** to ensure the emotional arc is
   correct — automation should make customers feel informed and valued, not spammed

The audit tells you **where** the problems are.
This skill tells you **what to build** to fix them.
