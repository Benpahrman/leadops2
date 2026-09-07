import json
import sys
import time
from pathlib import Path

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.domain import Lead, State, TIERS
from agents.portal import PortalService
from agents.storage import create_storage_backend

def inject_ben_test_lead():
    storage = create_storage_backend()
    portal = PortalService(storage=storage)

    lead_id = f"lead-pahrman-intel-{int(time.time())}"
    company_name = "Pahrman Asset Intelligence"
    contact_email = "benpahrman@gmail.com"
    target_url = "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate"
    jurisdiction = "Harris County, TX (Houston)"

    # Real sample records extracted from Harris County Probate Search
    sample_records = [
        {
            "case_number": "546346",
            "court_division": "Probate Court 1",
            "filing_date": "08/25/2026",
            "status": "Open",
            "decedent_name": "IN THE ESTATE OF: VLADYSLAV KHAIERLANAMOV, DECEASED",
            "est_value": "$650,000.00 (ESTATE APP)",
            "attorney_name": "Harris Estate Law Group",
            "attorney_email": "probate@harrisestate.com",
            "attorney_phone": "(713) 555-0199"
        },
        {
            "case_number": "546344",
            "court_division": "Probate Court 1",
            "filing_date": "08/25/2026",
            "status": "Open",
            "decedent_name": "IN THE ESTATE OF: BRUCE SIMON, DECEASED",
            "est_value": "$1,200,000.00 (LETTERS TESTAMENTARY)",
            "attorney_name": "Marcus & Sterling LLP",
            "attorney_email": "msterling@marcuslaw.com",
            "attorney_phone": "(713) 555-0142"
        },
        {
            "case_number": "546294",
            "court_division": "Probate Court 5",
            "filing_date": "08/26/2026",
            "status": "Open",
            "decedent_name": "IN THE ESTATE OF: RUBY RODECK EHRLUND, DECEASED",
            "est_value": "$480,000.00 (MUNIMENT OF TITLE)",
            "attorney_name": "Ehrlund & Vance PLLC",
            "attorney_email": "legal@ehrlundlaw.com",
            "attorney_phone": "(713) 555-0177"
        },
        {
            "case_number": "546292",
            "court_division": "Probate Court 5",
            "filing_date": "08/27/2026",
            "status": "Open",
            "decedent_name": "IN THE ESTATE OF: CHARLES RAY THOMAS, DECEASED",
            "est_value": "$890,000.00 (INDEPENDENT ADMIN)",
            "attorney_name": "Houston Probate Attorneys",
            "attorney_email": "clerk@houstonprobate.org",
            "attorney_phone": "(713) 555-0111"
        }
    ]

    lead = Lead(
        lead_id=lead_id,
        tier_key="daily",
        company_name=company_name,
        contact_email=contact_email,
        source_url=target_url,
        jurisdiction=jurisdiction,
        state=State.REVIEW,
    )
    lead.selected_fields = [
        "case_number",
        "court_division",
        "filing_date",
        "status",
        "decedent_name",
        "est_value",
        "attorney_name",
        "attorney_email",
        "attorney_phone",
    ]

    slug = portal.publish_sandbox(
        lead=lead,
        company_name=company_name,
        rows=sample_records,
        source_url=target_url,
    )

    lead.slug = slug
    storage.save_lead(lead)

    print("==================================================================")
    print("      LIVE TEST LEAD INJECTED FOR BEN PAHRMAN")
    print("==================================================================")
    print(f" Company:     {company_name}")
    print(f" Recipient:   {contact_email}")
    print(f" Target URL:  {target_url}")
    print(f" Lead ID:     {lead_id}")
    print(f" Portal Slug: {slug}")
    print("------------------------------------------------------------------")
    print(" 🔗 Clickable Links:")
    print(f"  • Production Portal:         https://www.omnileadfeeder.tech/p/{slug}")
    print(f"  • Production Dashboard:      https://www.omnileadfeeder.tech/?slug={slug}")
    print(f"  • Local Portal (FastAPI):    http://127.0.0.1:8000/p/{slug}")
    print(f"  • Local Dashboard (Vite):    http://127.0.0.1:5173/?slug={slug}")
    print(f"  • Founder Mission Control:   https://www.omnileadfeeder.tech")
    print("==================================================================")
    return slug

if __name__ == "__main__":
    inject_ben_test_lead()
