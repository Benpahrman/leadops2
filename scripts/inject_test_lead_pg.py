import os
import sys
import time

from agents.domain import Lead, State
from agents.portal import PortalService
from agents.storage import create_storage_backend

def main():
    storage = create_storage_backend()
    portal = PortalService(storage=storage)

    lead_id = f"lead-pahrman-intel-{int(time.time())}"
    company_name = "Pahrman Asset Intelligence"
    contact_email = "benpahrman@gmail.com"
    target_url = "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate"
    jurisdiction = "Harris County, TX (Houston)"

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

    print("SUCCESS: Lead injected")
    print(f"SLUG:{slug}")
    print(f"LEAD_ID:{lead_id}")

if __name__ == "__main__":
    main()
