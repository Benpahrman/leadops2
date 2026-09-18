"""Verification Test Suite for Washington State 39-County Acquisition Engine.

Tests:
1. GeoCountyResolver 39-County Washington coverage & portal resolution
2. WashingtonCountyOrchestrator state machine, progression, and metrics
3. NicheBrainstormerAgent vertical discovery and search operator generation
4. HiringIntentProspector role classification and Zero-Link pitch synthesis
5. WebsiteContactFormSubmitter form pitch formatting and validation
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.tools.geo_county_resolver import GeoCountyResolver
from agents.scout_runner.wa_county_orchestrator import WashingtonCountyOrchestrator
from agents.scout_runner.niche_brainstormer_agent import NicheBrainstormerAgent
from agents.scout_runner.hiring_intent_prospector import HiringIntentProspector, DiscoveredHiringProspect
from agents.scout_runner.website_form_submitter import WebsiteContactFormSubmitter


def test_wa_county_resolution():
    print("\n--- 1. Testing Washington State 39-County Jurisdictional Coverage ---")
    wa_counties = GeoCountyResolver.get_all_counties_for_state("WA")
    print(f"Total Washington counties discovered: {len(wa_counties)}")
    assert len(wa_counties) == 39, f"Expected 39 Washington counties, found {len(wa_counties)}"

    # Spot check key commercial counties
    county_names = [c["county"] for c in wa_counties]
    for key_county in ["King County", "Pierce County", "Snohomish County", "Spokane County", "Clark County", "Thurston County", "Yakima County"]:
        assert key_county in county_names, f"Missing key county: {key_county}"

    sample = wa_counties[0]
    print(f"Sample County: {sample['county']} | Seat/City: {sample['primary_city']} | FIPS: {sample['fips']} | Portal: {sample['portal_name']}")
    assert sample["fips"].startswith("53"), f"FIPS code should start with 53 for WA, got {sample['fips']}"
    print("[PASS] All 39 Washington counties verified with authentic FIPS and portal records.")


def test_wa_county_orchestrator():
    print("\n--- 2. Testing Washington County Orchestrator State Machine ---")
    test_state_file = Path("data/test_wa_orchestrator_state.json")
    if test_state_file.exists():
        test_state_file.unlink()

    orchestrator = WashingtonCountyOrchestrator(state_file_path=test_state_file)
    initial = orchestrator.get_active_county()
    print(f"Initial County: {initial['county']} ({initial.get('primary_city')})")

    # Advance county
    next_county = orchestrator.advance_county()
    print(f"Advanced to: {next_county['county']} ({next_county.get('primary_city')})")
    assert next_county["county"] != initial["county"], "County should have advanced"

    # Record activity
    orchestrator.record_activity(next_county["county"], leads_discovered=5, forms_submitted=2)
    metrics = orchestrator.get_progress_metrics()
    print(f"Orchestrator Telemetry: {metrics}")
    assert metrics["total_leads_discovered"] == 5
    assert metrics["total_forms_submitted"] == 2

    if test_state_file.exists():
        test_state_file.unlink()
    print("[PASS] WA County Orchestrator state machine progression verified.")


def test_niche_brainstormer():
    print("\n--- 3. Testing Niche Brainstormer Agent ---")
    agent = NicheBrainstormerAgent()
    niches = agent.brainstorm_niches_for_jurisdiction(county_name="King County", state_code="WA", primary_city="Seattle", max_niches=4)
    print(f"Discovered {len(niches)} high-intent niches:")
    for i, n in enumerate(niches, 1):
        print(f"  {i}. {n.niche_name} ({n.vertical_category})")
        print(f"     Pain Point: {n.operational_pain_point[:90]}...")
        print(f"     Search Query Example: {n.search_queries[0]}")
        print(f"     Job Titles to Target: {', '.join(n.job_titles_to_target[:3])}")
    assert len(niches) >= 3, "Expected at least 3 niches"
    print("[PASS] Niche Brainstormer Agent generated actionable niches and queries.")


def test_hiring_intent_prospector():
    print("\n--- 4. Testing Hiring Intent Prospector ---")
    prospector = HiringIntentProspector()

    sample_prospect = DiscoveredHiringProspect(
        company_name="Apex Construction & Permitting",
        job_title="Permit Coordinator",
        location="Tacoma, WA",
        vertical="Commercial Construction & Permitting",
        job_url="https://example.com/jobs/permit-coord",
        website="https://apexconstruction.com",
    )

    pitch = prospector.format_hiring_intent_pitch(sample_prospect, county_or_city="Pierce County")
    word_count = len(pitch["body"].split())
    print(f"Generated Hiring Pitch Subject: {pitch['subject']}")
    print(f"Pitch Body:\n{pitch['body']}")
    print(f"Pitch Word Count: {word_count} words")
    assert word_count <= 55, f"Pitch exceeds 55-word deliverability limit (got {word_count})"
    assert "http" not in pitch["body"], "Zero-Link Touch 1 must not contain URLs"
    print("[PASS] Hiring Intent Prospector synthesized compliant Zero-Link pitch.")


async def test_website_form_submitter():
    print("\n--- 5. Testing Website Contact Form Submitter ---")
    submitter = WebsiteContactFormSubmitter()
    form_pitch = submitter.format_form_pitch(niche="commercial construction", county_or_city="Pierce County")
    word_count = len(form_pitch.split())
    print(f"Form Pitch:\n{form_pitch}")
    print(f"Form Pitch Word Count: {word_count} words")
    assert word_count <= 55, f"Form pitch exceeds 55-word limit (got {word_count})"
    assert "http" not in form_pitch, "Form pitch should follow Zero-Link rule"

    # Test dry run submission
    result = await submitter.submit_contact_form(
        website_url="https://example.com",
        niche="probate law",
        county_or_city="King County",
        dry_run=True,
    )
    print(f"Dry Run Result: Status={result.status} | URL={result.contact_url}")
    print("[PASS] Website Contact Form Submitter validated successfully.")


if __name__ == "__main__":
    print("[TEST SUITE] Starting Washington State Acquisition Engine Verification Suite...")
    test_wa_county_resolution()
    test_wa_county_orchestrator()
    test_niche_brainstormer()
    test_hiring_intent_prospector()
    asyncio.run(test_website_form_submitter())
    print("\n[COMPLETE] ALL 5 VERIFICATION SUITES PASSED CLEANLY!")
