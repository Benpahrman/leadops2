# Scout Runner Package

The **Scout Runner** package powers autonomous B2B lead discovery across national county registries, municipal court dockets, and local commercial filings.

---

## Architecture & Modularization (ADR-0002)

The monolithic `agents/scout_runner.py` (2,274 LOC) has been cleanly decomposed into modular domain units behind an identical, 100% backward-compatible facade (`agents/scout_runner/__init__.py`):

```
agents/scout_runner/
├── __init__.py                     # Unified re-export for runner & all specialist engines
├── catalog.py                      # VERTICAL_CATALOG: 10+ high-yield public record verticals
├── worker.py                       # ScoutBackgroundWorker: B2B prospector, WAF verification
├── supervisor.py                   # ScoutAutomationSupervisor: bounded cycles, office hours
├── web_scout.py                    # B2BWebScoutWorker: search, contact crawling & enrichment
├── cli.py                          # Command-line interface runner & micro-scrape probe
├── national_county_orchestrator.py # 3,000+ US counties crawler
├── state_bar_prospector.py         # Bar association legal scrapers
├── sos_entity_prospector.py        # Secretary of State registry crawler
├── contact_enricher_agent.py       # Decision-maker email/LinkedIn finder
├── county_filing_extractor.py      # Court docket party extractor
├── high_volume_prospector.py       # High-volume batch campaign prospector
├── hiring_intent_prospector.py     # Clerk job posting detector
├── local_business_prospector.py    # Local municipal business discovery
├── niche_brainstormer_agent.py     # Niche vertical ideation agent
├── scout_pipeline.py               # Candidate verification & sandbox publisher
├── wa_county_orchestrator.py       # Washington state county orchestrator
├── website_form_submitter.py       # Web contact form submitter fallback
└── README.md                       # Living architectural specification
```

---

## Key Core Directives Enforced

1. **Same-Day Freshness Gate:**
   - Scout micro-scrapes must pull real live records where $\ge 80\%$ carry filing dates matching `current_date` (or the previous business day before 08:00).
2. **Deterministic Deduplication:**
   - 45-day anti-duplicate cooldown prevents emailing or re-prospecting the same domain or company.
3. **Office Hours Window:**
   - Cold outreach dispatch is strictly restricted to business office hours (8:00 AM – 5:00 PM CST, Monday through Friday).
