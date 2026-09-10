#!/usr/bin/env python3
"""Scraper & Output Catalog Generator and CLI Explorer.

Scans build_artifacts/, indexes all generated scrapers, their source code,
and their extracted datasets (JSON/CSV), and generates:
  - build_artifacts/scrapers_catalog.json
  - build_artifacts/SCRAPERS_INDEX.md
  - build_artifacts/scrapers_catalog.csv

Provides an interactive CLI for finding scrapers and outputs instantly.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.scraper_catalog import (
    BASE_DIR,
    BUILD_ARTIFACTS_DIR,
    CATALOG_CSV_PATH,
    CATALOG_JSON_PATH,
    CATALOG_MD_PATH,
    build_catalog,
    get_catalog,
    get_scraper_output_data,
    get_scraper_source_code,
    load_json,
    search_catalog,
    write_catalog_files,
)

# UTF-8 terminal encoding support for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception as _ex:
        _reconfig_err = str(_ex)


def print_table(results):
    if not results:
        print("No matching scrapers found.")
        return

    print(f"\n{'COMPANY':<35} | {'PORTAL':<25} | {'RECORDS':<8} | {'SCRAPER CODE':<32} | {'OUTPUT PATH'}")
    print("-" * 125)
    for r in results:
        comp = (r['company_name'][:33] + '..') if len(r['company_name']) > 35 else r['company_name']
        portal = (r['portal_name'][:23] + '..') if len(r['portal_name']) > 25 else (r['portal_name'] or r['portal_url'][:25] or '—')
        records = str(r['output_records_count']) if r['has_output_data'] else "—"
        code = r['scraper_code_path'] or "None"
        out = r['primary_output_path'] or "None"
        print(f"{comp:<35} | {portal:<25} | {records:<8} | {code:<32} | {out}")
    print(f"\nTotal shown: {len(results)}\n")


def print_detail(item):
    print("\n" + "=" * 80)
    print(f" SCRAPER PROFILE: {item['company_name']}")
    print("=" * 80)
    print(f"  Lead ID:            {item['lead_id']}")
    print(f"  Folder Path:        {item['folder_path']}")
    print(f"  Target Portal:      {item['portal_name']} ({item['portal_url']})")
    print(f"  Pain Point:         {item['commercial_pain']}")
    print(f"  QA / Status:        {item['qa_status']}")
    if item["qualification_score"]:
        print(f"  BDR Qual Score:     {item['qualification_score']}/100")
    print(f"  Scraper Code:       {item['scraper_code_path'] or 'NOT FOUND'} ({item['scraper_size_bytes']} bytes)")
    print(f"  Standalone Entry:   {item['entry_path'] or 'NOT FOUND'}")
    print(f"  Output Records:     {item['output_records_count']} rows ({item['output_type']})")
    print(f"  Primary Output:     {item['primary_output_path'] or 'NONE'}")
    if item["sample_fields"]:
        print(f"  Sample Fields:      {', '.join(item['sample_fields'])}")
    print(f"  Last Updated:       {item['updated_at']}")

    # Preview output rows if available
    data = get_scraper_output_data(item["lead_id"])
    if data and isinstance(data, list) and data:
        print("\n  Sample Output Record Preview (1st row):")
        print("  " + "-" * 60)
        sample_row = data[0]
        for k, v in list(sample_row.items())[:6]:
            print(f"    {k:<20}: {v}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="LeadOps Scraper & Output Catalog Explorer")
    parser.add_argument("--refresh", action="store_true", help="Rebuild catalog index files from disk")
    parser.add_argument("--search", "-s", type=str, default="", help="Search scrapers by company, URL, or lead ID")
    parser.add_argument("--show", type=str, default="", help="Display full details and output sample for a lead ID")
    parser.add_argument("--json", action="store_true", help="Output search results in raw JSON format")
    args = parser.parse_args()

    if args.refresh or not CATALOG_JSON_PATH.exists():
        print("🔄 Scanning build_artifacts/ and indexing scrapers...")
        catalog = get_catalog(refresh=True)
        print(f"✅ Catalog updated! {len(catalog)} scrapers indexed.")
        print(f"   - Markdown: {CATALOG_MD_PATH}")
        print(f"   - JSON:     {CATALOG_JSON_PATH}")
        print(f"   - CSV:      {CATALOG_CSV_PATH}")
    else:
        catalog = get_catalog(refresh=False)

    if args.show:
        match = next((c for c in catalog if c["lead_id"] == args.show or args.show.lower() in c["company_name"].lower()), None)
        if match:
            print_detail(match)
        else:
            print(f"Scraper not found for '{args.show}'.")
        return

    if args.search:
        results = search_catalog(args.search, catalog)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print(f"🔍 Search results for '{args.search}':")
            print_table(results)
        return

    if not args.refresh:
        print_table(catalog[:25])
        if len(catalog) > 25:
            print(f"... and {len(catalog) - 25} more scrapers. Use --search <term> or open build_artifacts/SCRAPERS_INDEX.md")


if __name__ == "__main__":
    main()
