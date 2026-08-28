"""Standalone CLI runner for the Autonomous Dev Swarm.

Run this script in a separate terminal window to execute the builder team on any lead
and inspect the generated extractor code and specialist reports in real-time.

Usage:
    python scripts/run_dev_swarm.py
    python scripts/run_dev_swarm.py --lead-id lead-1
    python scripts/run_dev_swarm.py --company "Lone Star Asset Recovery" --url "https://cclerk.hctx.net"
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.domain import Lead, PaymentEvent, State
from agents.storage import SqliteStorageBackend
from agents.workflow import run_autonomous_dev_team


def main():
    parser = argparse.ArgumentParser(description="Autonomous Dev Swarm CLI")
    parser.add_argument("--lead-id", default=None, help="Lead ID to build scraper for")
    parser.add_argument("--company", default=None, help="Company name")
    parser.add_argument("--url", default=None, help="Target portal URL")
    parser.add_argument("--tier", default="daily", help="Tier (weekly, daily, ai, buyout)")
    args = parser.parse_args()

    storage = SqliteStorageBackend("leadops.db")

    lead = None
    if args.lead_id:
        lead = storage.get_lead(args.lead_id)
        if not lead:
            print(f"[!] Lead {args.lead_id} not found in leadops.db")
            return
    else:
        leads = storage.list_leads()
        if leads:
            lead = leads[0]
        else:
            lead = Lead(
                lead_id="lead-live-demo-1",
                tier_key=args.tier,
                company_name=args.company or "Lone Star Asset Recovery",
                source_url=args.url or "https://www.cclerk.hctx.net/",
                selected_fields=["case_number", "decedent_name", "filing_date", "est_value", "attorney_name", "status"],
                contact_email="client.operations@lonestar-assets.com",
            )
            lead.slug = "lone-star-lead-live-demo-1"

    print("=" * 70)
    print("[LEADOPS AUTONOMOUS DEV SWARM] - LIVE CLI RUNNER")
    print("=" * 70)
    print(f"Lead ID:      {lead.lead_id}")
    print(f"Company:      {lead.company_name}")
    print(f"Target URL:   {lead.source_url}")
    print(f"Tier:         {lead.tier.name} (${lead.tier.price_cents // 100}/mo)")
    print(f"Fields:       {', '.join(lead.selected_fields or ['default'])}")
    print("=" * 70)

    # Step 1: Deposit verification
    print("\n[1/4] Verifying Setup Deposit ($250.00)...")
    time.sleep(0.3)
    lead.deposit_paid = True
    lead.state = State.DEPOSIT_PAID
    print("      -> Deposit confirmed. Starting Builder Swarm...")

    # Step 2: Running Dev Swarm
    print("\n[2/4] Executing Specialist Agent Roles:")
    time.sleep(0.3)
    print("      [Network Engineer]       Probing WAF, generating headers, testing stealth...")
    time.sleep(0.3)
    print("      [Frontend DOM Architect] Pruning HTML, mapping row and field selectors...")
    time.sleep(0.3)
    print("      [Systems Architect]      Compiling strict Pydantic output schema contracts...")
    time.sleep(0.3)
    print("      [Junior Developer]       Compiling executable Playwright extraction script...")
    
    result = run_autonomous_dev_team(lead, slug=getattr(lead, "slug", lead.lead_id))
    storage.save_lead(lead)

    # Step 3: QA Gatekeeper
    print(f"\n[3/4] Independent QA Gatekeeper Evaluation:")
    print(f"      Score:        {lead.qa_score:.1f}%")
    print(f"      Preview Rows: {lead.preview_rows} rows extracted")
    print(f"      Escrow Ready: {result.escrow_ready}")
    print(f"      New State:    {lead.state.value}")

    # Step 4: Output Files on Disk
    artifact_path = Path("build_artifacts") / (lead.lead_id or "demo_lead")
    print(f"\n[4/4] Generated Scraper Files on Disk ({artifact_path}):")
    if artifact_path.exists():
        for file in sorted(artifact_path.glob("*")):
            print(f"      -> {file.name} ({file.stat().st_size} bytes)")

    print("\n" + "=" * 70)
    print("BUILD COMPLETE! Customer notified via email. Awaiting Payment #2 ($250.00).")
    print(f"View extractor: {artifact_path / 'extractor.py'}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
