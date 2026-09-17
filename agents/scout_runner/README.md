# Scout Runner Package

The **Scout Runner** package powers autonomous B2B lead discovery across national county registries, municipal court dockets, and local commercial filings.

---

## Architecture & Modularization (ADR-0002)

The monolithic `agents/scout_runner.py` (2,274 LOC) has been cleanly decomposed into modular domain units behind an identical, 100% backward-compatible facade (`agents/scout_runner/__init__.py`):

```
agents/scout_runner/
├── __init__.py           # Barrel re-export preserving identical public API
├── catalog.py            # VERTICAL_CATALOG: 10+ high-yield public record verticals
├── worker.py             # ScoutBackgroundWorker: B2B prospector, WAF verification, lead qualification
├── supervisor.py         # ScoutAutomationSupervisor: bounded cycles, rate-limits, office hours
├── web_scout.py          # B2BWebScoutWorker: DuckDuckGo search, contact crawling & enrichment
├── cli.py                # Command-line interface runner & micro-scrape probe
└── README.md             # Living architectural specification
```

---

## Key Core Directives Enforced

1. **Same-Day Freshness Gate:**
   - Scout micro-scrapes must pull real live records where $\ge 80\%$ carry filing dates matching `current_date` (or the previous business day before 08:00).
2. **Deterministic Deduplication:**
   - 45-day anti-duplicate cooldown prevents emailing or re-prospecting the same domain or company.
3. **Office Hours Window:**
   - Cold outreach dispatch is strictly restricted to business office hours (8:00 AM – 5:00 PM CST, Monday through Friday).
