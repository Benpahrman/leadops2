---
name: customer-acquisition-discovery
description: >
  Comprehensive discovery and optimization skill for LeadOps customer acquisition.
  Guides the discovery of new high-yield public-records verticals, untapped B2B prospecting channels,
  and inbound growth loops, while systematically auditing and optimizing the current setup
  (Scout micro-scrapes, Zero-Link Touch 1 outreach, email deliverability, sandbox conversion,
  and the $99 Setup Sprint protocol).
---

# Customer Acquisition Discovery & Optimization Skill

This skill governs two complementary imperatives in the LeadOps ecosystem:
1. **Discovery (Expanding the Pie):** Discovering new high-intent verticals, untapped prospecting channels, and innovative acquisition flywheels that generate fresh demand.
2. **Optimization (Sharpening the Spear):** Systematically diagnosing, auditing, and leveling up our existing acquisition setup—from Scout micro-scraping hit rates and Zero-Link deliverability to sandbox preview conversion and $99 Setup Sprint checkout velocity.

Every recommendation, test, and proposal generated through this skill operates under strict production rules: **Zero Mock Data** (live verified filings only), **Alex Persona** (35–55 words plaintext Touch 1), **$99 Setup Sprint** (100% credited to Month 1), and **$\ge 95\%$ Live QA Gate**.

---

## 🧭 Dual-Core Mental Model: Discovery vs. Optimization

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    LEADOPS CUSTOMER ACQUISITION ENGINE                          │
├────────────────────────────────────────┬────────────────────────────────────────┤
│          DISCOVERY VECTORS             │          OPTIMIZATION VECTORS          │
│        "Find New High-Yield Paths"     │       "Maximize Existing Funnel"       │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ • New Verticals & Filing Niches        │ • Scout Micro-Scrape Hit Rate ($\ge 80\%$)│
│ • Alternative Prospecting Channels     │ • Zero-Link Touch 1 Deliverability & Copy│
│ • Partner & Title Referral Loops       │ • Anti-Spam Jitter & Warmup Hygiene    │
│ • Programmatic Inbound Portals         │ • Bespoke Sandbox Preview Conversion   │
│ • Live Docket Party Prospecting        │ • PayPal $99 Sprint Deposit Velocity   │
│ • High-Intent Hiring Signal Scrapers   │ • 3-Min Operator Grace Period & Queue  │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

---

## 🔍 How to Run This Skill

When tasked with discovering new customer acquisition opportunities or optimizing our current setup:

1. **Step 1: Current State Telemetry & Diagnostics**: Inspect active leads, bounce rates, open/reply rates, and micro-scrape pass rates.
2. **Step 2: Apply Discovery Vectors (Section A)**: Identify untapped public-record filing types, new prospect discovery data sources, or new outbound/inbound loops.
3. **Step 3: Apply Optimization Vectors (Section B)**: Audit existing pipelines (`agents/scout_runner.py`, `agents/auto_outreach.py`, `agents/pitcher.py`, `agents/email/`) for bottlenecks, spam hazards, or drop-offs.
4. **Step 4: Objective Prioritization (Acquisition RICE Matrix)**: Score opportunities by Reach, Impact on $99 Deposits, Live Data Confidence, and Implementation Effort.
5. **Step 5: Production Action Blueprint**: Deliver actionable code, templates, scraper schemas, and verification commands.

---

# SECTION A: Discovering New Customer Acquisition Vectors

Use these 4 discovery vectors to unlock high-intent B2B audiences whose revenue directly relies on fast, structured access to public dockets.

---

### Vector 1: Untapped Public-Records Verticals & TAM Matrix

Beyond the core Probate and Tax Lien markets, evaluate high-yield municipal and county filing categories:

| Vertical / Filing Type | Primary Buyers | Target Municipal / County Portal | High-Value Extracted Fields | Urgency / Time-to-Value |
| :--- | :--- | :--- | :--- | :--- |
| **Lis Pendens & Foreclosure Filings** | Pre-foreclosure investors, private equity real estate funds, distressed debt attorneys | County Clerk & Recorder / Registry of Deeds | Case #, Borrower, Lender/Trustee, Recording Date, Legal Description, Principal Balance | **Ultra-High** (Borrowers have 30–90 day statutory cure periods) |
| **Mechanic's Liens & Claims** | Commercial subcontractors, material suppliers, factoring lenders, lien release bond brokers | County Recorder / Auditor | Lienor, Property Owner, General Contractor, Claim Amount, Property Address, Filing Date | **High** (Subcontractors racing against 90-day enforcement deadlines) |
| **Municipal Code Violations & Unsafe Structures** | Distressed wholesale investors, commercial demolition/remediation contractors | City Open Data, Code Compliance Portals (Accela, EnerGov) | Case #, Violation Type, Hearing Date, Parcel APN, Owner of Record, Inspector Remarks | **High** (Property owners facing escalating per-day municipal fines) |
| **Commercial Building Permits & Plan Approvals** | Subcontractors, commercial MEP firms, commercial insurance brokers, equipment rental | City Building & Safety Departments | Permit #, Valuation ($), Contractor Name, Project Type, Square Footage, Issue Date | **Medium-High** (Subcontractors bidding on new commercial buildouts) |
| **Liquor License Applications & Transfers** | Point-of-Sale vendors, beverage distributors, commercial hospitality brokers | State Alcohol Beverage Commission (ABC) / City Licensing | License #, Business Entity, Trade Name, Premises Address, License Class, Status Date | **High** (New venues spending $50k–$250k on buildout and equipment) |
| **Chapter 7 & 11 Bankruptcy Asset Filings** | Distressed debt buyers, insolvency litigators, liquidators | Federal PACER / CM-ECF (Regional District Courts) | Case #, Debtor Name, Chapter Type, Filing Date, Trustee Name, Assets Range | **Medium** (High institutional budgets, strict legal workflows) |
| **Tax Sale Surplus / Overage Recovery** | Asset recovery specialists, surplus funds attorneys, forensic investigators | County Treasurer / Chancery Court Surplus Lists | Foreclosure Case #, Prior Owner, Sale Price, Winning Bid, Surplus Balance | **Ultra-High** (Time-limited claim window before escheatment to county) |

#### Vertical Feasibility Scoring Formula
Before committing engineering resources to a new vertical, score it:
$$\text{Feasibility Score} = \frac{\text{Daily Filing Volume} \times \text{Urgency (1-5)} \times \text{Buyer Willingness-to-Pay (\$)}}{\text{Scraping Difficulty (1-5)}}$$
* If $\text{Feasibility Score} \ge 250$, greenlight live micro-scrape viability test.

---

### Vector 2: New Prospect Discovery Mechanisms (Beyond Current Prospectors)

LeadOps currently queries Secretary of State registries, State Bar directories, and local business listings. Expand discovery via these automated mechanisms:

1. **The "Docket Party" Reverse Prospector:**
   - **Logic:** Query the target court or county portal for the past 30 days of filings. Extract the recurring `Attorney of Record`, `Law Firm`, or `Plaintiff/Claimant` entities.
   - **Advantage:** Guarantees 100% relevance. The prospect *already files in this exact court every single week*.
   - **Action:** Build `agents/docket_party_prospector.py` to aggregate the top 20 most active filing parties per county.

2. **Job Posting Intent Signal Scraper:**
   - **Logic:** Scrape Indeed, LinkedIn, and ZipRecruiter for regional job postings containing keywords: `"Docket Clerk"`, `"Court Records Researcher"`, `"Public Records Specialist"`, `"Paralegal - Filings"`.
   - **Advantage:** Companies hiring for these roles are actively spending $40,000–$65,000/yr on manual docket entry. A $250/mo automated daily feed represents an immediate 90% cost savings.
   - **Action:** Build `agents/hiring_intent_prospector.py` to identify firms with manual filing pain.

3. **Permit Applicant & Contractor Registry Cross-Referencing:**
   - **Logic:** Cross-reference licensed general contractors and subcontractors against commercial permit issuances in target metros.
   - **Advantage:** Pinpoints active commercial contractors currently bidding or mobilising on projects.

4. **Multi-Jurisdiction Expansion Mapping:**
   - **Logic:** When an existing client converts in County A, auto-discover all peer firms operating in adjacent Counties B, C, and D within the same state.
   - **Advantage:** Re-uses the existing scraper architecture with zero incremental code changes.

---

### Vector 3: Alternative Outreach & Conversion Channels

1. **Compliant LinkedIn Operator Outreach Habit (10/day):**
   - External persona (Alex) connects with local Managing Partners, Docket Clerks, or Operations Directors.
   - **Touch 1 Connection Note (< 300 chars, strictly no sales pitch):**
     > *"Hi [First Name], saw your practice covers [County] dockets. We track newly posted court filings across the county daily — wanted to connect. Best, Alex"*
   - **Touch 2 (Only upon acceptance):** Share the bespoke sandbox link.

2. **Title & Escrow Agency Referral Channel:**
   - Regional title agencies and settlement attorneys review dockets for every closing.
   - Offer an automated daily "Lien & Lis Pendens Alert Feed" branded for their agency, plus a 15% recurring referral credit for onboarding their investor clients.

3. **Direct-Mail Postcard Sandbox Trigger (High-Value Enterprise Targets):**
   - For top-tier litigators or enterprise funds that block cold email, send a clean, minimal 4x6 postcard:
     - Front: *"Today's [County] Court Filings for [Firm Name]"*
     - Back: QR code pointing directly to `portal.leadops.io/p/{slug}` + short message from Alex.

---

### Vector 4: Product-Led & Inbound Acquisition Flywheels

1. **The "County Portal Health Index" (Public Inbound Tool):**
   - Host an open, fast tool at `portal.leadops.io/portal-status` or `/court-health`.
   - Shows live freshness metrics, average posting delays, and downtime across 500+ county courts.
   - CTA: *"Enter your firm's email to get today's 5 sample filings delivered instantly in a private sandbox."*

2. **Weekly Municipal Filing Digest (Free Niche Newsletter):**
   - Publish a weekly public summary of top filings (e.g., *"Top 10 Commercial Liens Filed in Harris County This Week"*).
   - Bottom CTA: *"Need daily 6:00 AM Google Sheets delivery for your pipeline? Start the $99 Setup Sprint (100% Credited to Month 1)."*

3. **The "3rd Delivery" Client Referral Engine:**
   - Automatically triggered on the client's 3rd successful daily morning data delivery:
     > *"Hi [First Name], hope the daily [County] filings are saving your team hours. Know another firm in [Neighboring County] that could use this? Refer them and we'll credit $50 to your next month's invoice."*

---

# SECTION B: Systematically Auditing & Improving the Current Setup

Use this checklist and diagnostic methodology to continuously tune the operational pipeline.

---

## 🛠️ Audit Surface 1: Scout Micro-Scrape Hit Rate & Freshness SLA

The same-day freshness gate ($\ge 80\%$ records matching today's business date) is the foundational gatekeeper of our pipeline.

### Diagnostic Checklist
- [ ] **Portal Maintenance Windows:** Does the scraper account for county courts that batch-update filings at 5:00 PM rather than throughout the business day?
- [ ] **Weekend & Holiday Logic:** Does `is_office_hours()` in `agents/scout_runner.py` correctly recognize federal and state court holidays (e.g., Presidents' Day, Memorial Day, Juneteenth) and look back to the previous business day?
- [ ] **Anti-Bot Resilience:** Are requests to portals protected by Cloudflare/Incapsula utilizing headless browser sessions with dynamic fingerprinting rather than plain `httpx`/`requests`?
- [ ] **DOM Drift Detection:** Is `agents/drift_monitor.py` running its 5:30 AM pre-check to catch selector drift before outbound batches run?

### Key Optimizations
1. **Adaptive Scraping Cadence:** When scraping courts with evening batch-dumps, adjust Scout runs to 07:00 AM recipient time so Touch 1 references yesterday's completed docket.
2. **Selector Fallback Heuristics:** Implement secondary and tertiary CSS/XPath selectors in `agents/scraper_catalog.py` so single-attribute changes do not halt discovery.

---

## ✉️ Audit Surface 2: Deliverability, Domain Hygiene & Spam Assessment

LeadOps' deliverability relies on zero-link Touch 1 outreach, human jitter, and mailbox warmup.

### Diagnostic Checklist
- [ ] **DNS Authentication:** Are SPF, DKIM, DMARC (`p=reject` or `p=quarantine`), and BIMI records actively verified across all sending subdomains?
- [ ] **Warmup Tier Enforcement:** Is `agents/email/warmup.py` strictly enforcing daily send caps per dedicated mailbox?
  - Tier 1 (Days 1–7): $\le 10$/day
  - Tier 2 (Days 8–14): $\le 25$/day
  - Tier 3 (Days 15–30): $\le 50$/day
  - Tier 4 (Established): $\le 100$/day
- [ ] **Humanized Jitter:** Is `AutoOutreachScheduler` enforcing 5–20 minute (300–1200s) delays between successive dispatches to avoid spam tripwires?
- [ ] **Plaintext Compliance:** Does the Touch 1 generator strictly emit `text/plain` with zero HTML markup, zero tracking pixels, zero images, and zero attachments?
- [ ] **Word Count Guardrail:** Is Touch 1 strictly between **35 and 55 words**? Any email $>55$ words must be rejected by the pre-send validator.

### Prohibited Spam Triggers to Audit & Eliminate
- [ ] Generic marketing words: *"revolutionary"*, *"guaranteed"*, *"discount"*, *"affordable"*, *"special offer"*.
- [ ] Hyperlinked URLs in Touch 1 (must remain ZERO links).
- [ ] Fake urgency: *"urgent"*, *"act now"*, *"limited time"*.
- [ ] Non-local send times: Sending outside the 8:00 AM – 5:00 PM local window of the recipient.

---

## 🎯 Audit Surface 3: Touch 1 Copy & Subject Line Optimization

Subject lines and opening hooks determine open and reply rates.

### Approved High-Converting Subject Formulas
* `filings for [clean_county]` (Current baseline: ~38% open rate)
* `[first_name] - quick question` (Natural peer-to-peer: ~42% open rate)
* `[clean_county] court records` (Informational: ~35% open rate)
* `quick question regarding [clean_county] filings` (Permission hook: ~40% open rate)

### Continuous Copy Experiments
| Variant | Angle | Sample Hook | Target Metric |
| :--- | :--- | :--- | :--- |
| **Control** | Spreadsheet gift | *"Pulled today's [probate/lien] filings into a clean spreadsheet for our team. Mind if I send the link?"* | Reply Rate $>15\%$ |
| **Docket Specific** | Exact filing reference | *"Saw your firm filed matter in [Court] this morning. We automated the daily docket pull. Mind if I send the link?"* | Reply Rate $>22\%$ |
| **Time-Savings** | Staff hours angle | *"We automated the morning [County] docket pull so paralegals don't have to search manually. Mind if I send over the link to see today's filings?"* | Reply Rate $>18\%$ |

---

## 📱 Audit Surface 4: Operator Grace Period & Queue Ergonomics

The 3-minute grace period protects outbound quality without requiring manual dispatch.

### Diagnostic Checklist
- [ ] **Discord / Telegram Webhook Health:** Are dispatch cards rendering cleanly on mobile with formatted prospect details, scraped record counts, and copy previews?
- [ ] **1-Tap Actions:** Do the `[🛑 Reject / Cancel]` and `[⚡ Send Immediately]` callback buttons respond in $<500\text{ms}$?
- [ ] **Dead-Letter Handling:** If an email fails SMTP dispatch, is it automatically captured in `failed_outreach` with clear error reasons (e.g., `MX_LOOKUP_FAILED`, `MAILBOX_FULL`)?
- [ ] **Auto-Pruning:** Are invalid domains, bouncebacks, and opt-outs immediately flagged to prevent future outreach?

---

## 💻 Audit Surface 5: Sandbox Preview & $99 Setup Sprint Conversion

The bespoke preview environment (`portal.leadops.io/p/{slug}`) is where interest converts to paid sprints.

### Diagnostic Checklist
- [ ] **Page Load Speed:** Does the unauthenticated sandbox load in $<2.0\text{s}$ over 4G mobile connections?
- [ ] **Live Data Prominence:** Are the 5–10 real, same-day scraped records immediately visible above the fold without requiring a login?
- [ ] **Field Confidence Scores:** Does each field mapping display an explicit confidence badge ($\ge 90\%$) showing how Scout extracted it?
- [ ] **Copy & Clarity:** Is the $99 Setup Sprint clearly explained as **100% Credited to Month 1** with **$\ge 95\%$ QA Pass Guarantee**?
- [ ] **No Escrow Terms:** Verify zero instances of the retired term "escrow" exist in frontend or API copy.
- [ ] **Frictionless Checkout:** Does the PayPal button launch the verified server-side order modal with 1 click?

---

# 📊 Objective Prioritization Framework: Acquisition RICE

When evaluating multiple customer acquisition opportunities or setup fixes, calculate the **Acquisition RICE Score**:

$$\text{RICE Score} = \frac{\text{Reach (Prospects/mo)} \times \text{Impact on \$99 Sprints (1-5)} \times \text{Live Data Confidence (0.1 - 1.0)}}{\text{Effort (Engineering Days)}}$$

### Scoring Rubrics
* **Reach:** Estimated number of target prospects available in this jurisdiction or channel per month.
* **Impact:** 
  - `5`: Unlocks immediate high-ticket contracts or $>25\%$ increase in $99 deposits.
  - `3`: Noticeable increase in reply or click-through rates.
  - `1`: Minor operational improvement.
* **Live Data Confidence:**
  - `1.0`: Portal is open, automated micro-scrapes verified, same-day data available.
  - `0.7`: Portal has CAPTCHA or requires session cookies; bypass verified.
  - `0.3`: Portal requires manual phone calls or paid paywall; high uncertainty.
* **Effort:** Estimated engineering days to build, test, and containerize.

---

# ⚡ Operator Runbook & Verification Commands

Use these CLI tools to audit the acquisition setup and test new discovery avenues:

```bash
# 1. Audit Deliverability & Domain Authentication
python -m agents.email.deliverability_tester --domain "leadops.io" --check-all

# 2. Run Scout Micro-Scrape Viability Test on a New County Portal
python -m agents.scout_runner --jurisdiction "Dallas County" --vertical "mechanics_liens" --limit 10

# 3. Audit Active Grace Period Queue & Webhook Telemetry
python -m agents.auto_outreach --status --inspect-queue

# 4. Dry-Run Auto-Outreach with Discord Notification (Zero Email Sent)
python -m agents.auto_outreach --dry-run --lead-id "lead_test_001"

# 5. Verify Touch 1 Copy Compliance (Word Count, Plaintext, Zero Links)
python -m agents.email.quality_gate --validate-copy --touch 1

# 6. Test Bespoke Sandbox Slug Generation & Preview Endpoint
curl -X GET http://localhost:8000/api/portal/preview/test-slug-001
```

---

## 🔒 Compliance & Quality Gatekeeper

Every discovery experiment and setup improvement must pass these non-negotiable checks:
- [ ] **Zero Synthetic / Mock Data:** All test datasets, sandbox previews, and candidate pitches contain 100% live public filings.
- [ ] **Touch 1 Deliverability:** Plaintext only, 35–55 words, 0 links, permission-first question.
- [ ] **Commercial Integrity:** $99 Setup Sprint Deposit is 100% credited to Month 1; verified server-side PayPal order.
- [ ] **Alex External Persona:** All outbound emails and touchpoints represent Alex with a human, low-friction tone.
- [ ] **Independent QA Authority:** $\ge 95\%$ schema pass rate required before unlocking the customer verification view.
