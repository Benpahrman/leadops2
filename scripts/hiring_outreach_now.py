"""Immediate Hiring-Intent Outreach Dispatcher.

Enables instant, same-day outreach to companies hiring for manual data roles
WITHOUT waiting for 14-day email warming cycles.

Outreach Vectors Available Immediately:
1. Website Contact Forms: Submits role-specific permission hook via prospect's own web server. 100% deliverability.
2. LinkedIn InMail / Connection Notes: Formats sub-300-char invitation note referencing their job listing.
3. Career / Recruiter Inquiries: Formats message for jobs@ or contact@ emails on their hiring portal.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.hiring_intent_prospector import HiringIntentProspector
from agents.website_form_submitter import WebsiteContactFormSubmitter
from agents.tools.geo_county_resolver import GeoCountyResolver
from agents.logging_config import get_logger

logger = get_logger("hiring_outreach_now")


def format_linkedin_connection_note(company_name: str, job_title: str, county: str) -> str:
    """Format a sub-300-character LinkedIn connection note referencing the open role."""
    note = (
        f"Hi! Saw your team is hiring a {job_title} in {county}. "
        f"We build automated 8 AM morning feeds that stream court filings & permits directly into spreadsheets. "
        f"Saved our partners 20+ hrs/wk before hiring. Mind if I send a 2-min preview?"
    )
    # Ensure under 300 char LinkedIn invite limit
    if len(note) > 295:
        note = (
            f"Hi! Saw you're hiring a {job_title} in {county}. "
            f"We build 8 AM morning docket feeds that stream filings into spreadsheets. "
            f"Saves 20+ hrs/wk of manual lookups. Mind if I send a quick preview?"
        )
    return note


async def run_hiring_outreach(
    location: str = "King County, WA",
    roles: list[str] | None = None,
    max_targets: int = 5,
    submit_forms: bool = False,
    dry_run: bool = True,
):
    print("\n" + "=" * 75)
    print(f"🚀 [SAME-DAY OUTREACH] Mining Hiring Signals in '{location}'")
    print("   Bypassing 14-day email warming via Website Contact Forms & LinkedIn")
    print("=" * 75 + "\n")

    target_roles = roles or [
        "Permit Coordinator",
        "Docket Clerk",
        "Title Searcher",
        "Data Entry Specialist",
    ]

    prospector = HiringIntentProspector()
    submitter = WebsiteContactFormSubmitter()

    print(f"🔎 Scanning active job requisitions for: {', '.join(target_roles)}...")
    prospects = prospector.discover_hiring_companies(
        location=location,
        target_roles=target_roles,
        max_results=max_targets,
    )

    if not prospects:
        print(f"⚠️ No active requisitions found for {location}. Try a broader metro like 'Seattle WA' or 'Spokane WA'.")
        return []

    print(f"\n✓ Found {len(prospects)} high-intent SMBs hiring for manual data roles:")

    results = []

    for idx, p in enumerate(prospects, 1):
        print("\n" + "-" * 75)
        print(f"[{idx}/{len(prospects)}] 🏢 {p.company_name.upper()}")
        print(f"   Role Posted:   '{p.job_title}' ({p.vertical})")
        print(f"   Location:      {p.location}")
        print(f"   Website:       {p.website or 'Not yet identified'}")
        if p.contact_email:
            print(f"   Contact Email: {p.contact_email}")
        if p.phone:
            print(f"   Phone:         {p.phone}")
        if p.job_url:
            print(f"   Job Post URL:  {p.job_url}")

        pitch = prospector.format_hiring_intent_pitch(p, county_or_city=location)
        linkedin_note = format_linkedin_connection_note(p.company_name, p.job_title, location)

        print("\n   📋 [OUTREACH VECTORS READY TODAY]:")

        # Vector 1: Website Contact Form
        print(f"   ► Vector 1: Website Contact Form (100% Deliverability, Zero Warmup Required)")
        form_result = None
        if p.website:
            if submit_forms or dry_run:
                print(f"      Probing contact page on {p.website}...")
                form_result = await submitter.submit_contact_form(
                    website_url=p.website,
                    niche=p.vertical,
                    county_or_city=location,
                    custom_message=pitch["body"],
                    dry_run=not submit_forms,  # If submit_forms is True, dry_run is False
                )
                status_icon = "✓" if form_result.success or form_result.status == "DRY_RUN" else "⚠️"
                print(f"      [{status_icon}] Form Status: {form_result.status} at {form_result.contact_url}")
                if submit_forms and form_result.success:
                    print(f"      🎉 Form submitted live to {p.company_name}!")
        else:
            print(f"      ⚠️ Website URL missing; look up via Google: 'https://www.google.com/search?q={p.company_name}+{location}'")

        # Vector 2: LinkedIn Connection / InMail
        print(f"\n   ► Vector 2: LinkedIn InMail / Connection Invite ({len(linkedin_note)} chars)")
        print(f'      "{linkedin_note}"')

        # Vector 3: Cold Email / Recruiter Note
        print(f"\n   ► Vector 3: Direct Email Subject & Hook ({len(pitch['body'].split())} words)")
        print(f"      Subject: {pitch['subject']}")
        print(f"      Body:\n{pitch['body']}")

        results.append({
            "company_name": p.company_name,
            "job_title": p.job_title,
            "location": p.location,
            "website": p.website,
            "contact_email": p.contact_email,
            "phone": p.phone,
            "pitch_body": pitch["body"],
            "linkedin_note": linkedin_note,
            "form_submission": form_result.to_dict() if form_result else None,
        })

    print("\n" + "=" * 75)
    print(f"🎯 Outreach Summary: Processed {len(results)} prospects in '{location}'.")
    if not submit_forms:
        print("💡 NOTE: Ran in preview mode. To submit live contact forms, pass '--live'.")
    print("=" * 75 + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="Run immediate hiring-intent outreach without email warming")
    parser.add_argument("--location", type=str, default="Seattle WA", help="Target city or county (e.g. 'Seattle WA', 'Pierce County')")
    parser.add_argument("--role", type=str, default=None, help="Target role (e.g. 'Permit Coordinator', 'Docket Clerk')")
    parser.add_argument("--limit", type=int, default=3, help="Max number of prospects to process")
    parser.add_argument("--live", action="store_true", help="Submit contact forms live (default is dry-run preview)")
    args = parser.parse_args()

    roles = [args.role] if args.role else None
    asyncio.run(run_hiring_outreach(
        location=args.location,
        roles=roles,
        max_targets=args.limit,
        submit_forms=args.live,
        dry_run=not args.live,
    ))


if __name__ == "__main__":
    main()
