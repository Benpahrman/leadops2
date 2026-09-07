# LeadOps Brand Voice & Design Guidelines

This system guide defines the tone of voice, visual identity, UI design principles, and copy standards for **LeadOps**. It covers both external client communication (Alex, outreach, sales sandboxes) and internal technical interfaces (Mission Control dashboard, customer portals).

---

### Part 1: Brand Voice & Editorial Guidelines

LeadOps speaks like an exceptionally capable systems engineer who understands real-world operations. We are not a corporate marketing agency, and we are not an aggressive sales boiler room. We write with candor, technical precision, and understated confidence.

#### 1. Core Voice Pillars

* **Pragmatic, Not Corporate:** Speak like a peer solving an operational headache, not an enterprise sales rep booking a demo. Eliminate buzzwords like *synergy, revolutionary, cutting-edge,* and *holistic*.
* **Concrete Over Descriptive:** Name the exact portal, the filing date, the error code, and the row count. Specific facts provide the color.
* **Low-Friction & Respectful:** Keep messages short enough to read on an iPhone without scrolling. Never disguise sales intent or trick the user into an unwanted call.
* **Empathetic to Tedium:** We respect the grind of legal researchers, title searchers, and acquisitions analysts. Acknowledge how bad manual public-records navigation actually is without sounding patronizing.

#### 2. Communication Contrast Matrix

| Instead of Writing (Corporate/Fluff) | Write (The LeadOps Standard) |
| --- | --- |
| "Our state-of-the-art AI pipeline revolutionizes data extraction." | "We scrape the county docket daily at 6:00 AM and drop clean CSVs in your sheet by 8:00 AM." |
| "Please find attached our comprehensive product brochure." | "We extracted today’s filings into a clean sheet—mind if I send over the link?" |
| "Let’s schedule a 15-minute sync to align on your data synergies." | "Here are 5 live rows from Cook County. If you want this daily, lock it in here." |
| "Due to unexpected architectural anomalies, extraction failed." | "Cloudflare Turnstile blocked the runner at 6:15 AM; proxy rotators are retrying." |

#### 3. Agent Personality Specs

* **Alex (Client Concierge):** Direct, warm, concise, and helpful. Always signs emails as `Alex | LeadOps` or `Alex`. Never sends more than 3 sentences in an inbound reply unless delivering technical documentation.
* **Intake System Copy:** Helpful and assumption-first. Avoid interrogation forms. Use positive confirmation: *"We did the research first—review these assumptions and continue when they look right."*
* **Retainer & Health Warnings:** Clear, factual, and actionable. State what broke (e.g., *"Table DOM altered on Harris County Portal"*) and the automated remediation window.

---

### Part 2: Visual Identity & Color System

The visual design is inspired by high-density industrial control terminals, modern code editors, and clean legal ledgers. It feels utilitarian, grounded, and engineered.

#### 1. Color Palette

* **Forest Deep (Primary Accent / Contrast):** `#15251F`
  *Usage:* Headers, primary buttons, terminal card headers.
* **Pine Slate (Terminal Surface / Secondary):** `#24483B`
  *Usage:* Table headers, active stepper borders, active tabs.
* **Industrial Ochre (Call-to-Action / Escrow Accent):** `#C26B34`
  *Usage:* Checkout buttons, Deploy Feed triggers, high-intent callouts.
* **Canvas Muted (Background Base):** `#EDF2EC`
  *Usage:* Dashboard body, neutral page background.
* **Card Surface White:** `#FFFFFF`
  *Usage:* Foreground data panels, interactive tables, input boxes.
* **Border Neutral:** `#C5D0C8`
  *Usage:* 1px structural container borders.
* **Subtle Box Drop Shadow:** `#D7E0D8` (or solid offset `4px 4px 0px #15251F`)
  *Usage:* Brutalist-style hard shadows on elevated sandbox panels.

#### 2. Typography

* **Headings & Display:** `Georgia`, `Charter`, or editorial serif equivalents. Provides an authoritative, legal-ledger look that appeals to probate, municipal, and real-estate operators.
* **Body Text:** Clean System Sans-Serif (`Inter`, `-apple-system`, `system-ui`). Highly readable at small, high-density sizes.
* **Code & Telemetry:** Monospace (`JetBrains Mono`, `Fira Code`, `ui-monospace`). Used for row counts, slug paths, status indicators, and field keys.

---

### Part 3: UI Scaffolding & Component Standards

#### 1. Layout & Density

* **High Information Density:** Dashboards and sandboxes display tabular data clearly without unnecessary negative space.
* **Zero Modal Traps:** Use inline editable assumptions rather than multi-step wizard dialogs.
* **Fixed 1px Borders & Hard Shadows:** Interfaces use deliberate `1px solid #C5D0C8` borders with 0px or 4px subtle rounded corners for a clean, precision-engineered feel.

#### 2. Core UI Components

**The Data Sandbox Card:**
```text
┌────────────────────────────────────────────────────────────────────────┐
│ 🎯 Target: Cook County Probate (Daily 6:00 AM Sync)                   │
├────────────────────────────────────────────────────────────────────────┤
│ Case Number    │ Decedent Name      │ Filing Date │ Est. Value         │
├────────────────┼────────────────────┼─────────────┼────────────────────┤
│ 2026-P-008912  │ ELEANOR V. VANCE   │ 2026-08-25  │ $420,000           │
└────────────────────────────────────────────────────────────────────────┘
```
* Interactive hover states on table rows.
* One-click CSV export always visible above the fold.

**Build Progress Steppers (Customer Safe):**
* Avoid exposing raw code exceptions or developer stack traces.
* Use 4 standardized sequential milestones:
  - `NETWORK_ENGINEER`: Checking permitted source connectivity.
  - `FRONTEND_DOM`: Mapping the source portal structure.
  - `SYSTEMS_ARCHITECT`: Validating data and runtime contracts.
  - `QA_GATEKEEPER`: Running 25-row Docker sandbox verification.

**Escrow & Pricing Badges:**
* Always state total setup and milestone splits clearly:
  `Weekly: $250/mo` | `Daily: $500/mo` | `AI / Heavy: $850/mo` | `Buyout: $1,500 one-time`
* Milestone badges: `50% Deposit (Locks Build)` → `50% Escrow (Unlocks Full Pipeline)`.

---

### Part 4: Technical & Deliverability Copy Standards

#### 1. Email Outbound Deliverability Rule
* **Never use hyperlinked text** like "Click here" or "View document" in cold introductory messages.
* **Never send attachments** (PDFs, mock invoices, screenshots).
* Keep raw character count low and maintain a high ratio of text-to-whitespace.
* Word count: strictly between 35 and 55 words max.

#### 2. Client Portal CTA Buttons
* Primary Action: `Deploy Feed` or `Activate Daily Feed`
* Review Action: `Looks right, continue`
* Verification Action: `Approve 25-Row Preview & Unlock Feed`
* Download Action: `Export Free CSV`
