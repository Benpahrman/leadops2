"""State Bar Association Directory Prospector for LeadOps Scout.

Discovers verified attorneys and law practices directly from official State Bar directories
(State Bar of Texas, State Bar of California, The Florida Bar, Illinois ARDC, etc.).
Targets high-value practice areas: Probate & Estate Planning, Real Estate & Title, Commercial Litigation.
"""

import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .llm_client import LLMAgentEngine, is_disallowed_buyer
from .tools.web_search import search_web, search_company_intelligence, find_linkedin_decision_maker
from .tools.web_fetcher import extract_contact_info_from_url
from .logging_config import get_logger

logger = get_logger("state_bar_prospector")

STATE_BAR_CONFIGS: dict[str, dict[str, Any]] = {
    "TX": {
        "state_name": "Texas",
        "bar_name": "State Bar of Texas",
        "search_domain": "texasbar.com",
        "default_portal": {
            "portal_name": "Harris County District Clerk & Probate Court",
            "target_url": "https://www.cclerk.hctx.net/",
            "jurisdiction": "Harris County, TX (Houston)",
            "dataset_key": "harris-foreclosure",
        },
    },
    "CA": {
        "state_name": "California",
        "bar_name": "State Bar of California",
        "search_domain": "calbar.ca.gov",
        "default_portal": {
            "portal_name": "Los Angeles Superior Court Probate Division",
            "target_url": "https://www.lacourt.org/division/probate/probate.aspx",
            "jurisdiction": "Los Angeles County, CA",
            "dataset_key": "cook-county-probate",
        },
    },
    "FL": {
        "state_name": "Florida",
        "bar_name": "The Florida Bar",
        "search_domain": "floridabar.org",
        "default_portal": {
            "portal_name": "Orange County Comptroller & Clerk Registry",
            "target_url": "https://www.occompt.com/",
            "jurisdiction": "Orange County, FL (Orlando)",
            "dataset_key": "orange-foreclosure",
        },
    },
    "IL": {
        "state_name": "Illinois",
        "bar_name": "Illinois State Bar Association & ARDC",
        "search_domain": "isba.org",
        "default_portal": {
            "portal_name": "Cook County Probate Division Court Portal",
            "target_url": "https://www.cookcountyclerkofcourt.org/",
            "jurisdiction": "Cook County, IL (Chicago)",
            "dataset_key": "cook-county-probate",
        },
    },
    "GA": {
        "state_name": "Georgia",
        "bar_name": "State Bar of Georgia",
        "search_domain": "gabar.org",
        "default_portal": {
            "portal_name": "Probate Court of Fulton County",
            "target_url": "https://www.fultoncountyga.gov/probatecourt",
            "jurisdiction": "Fulton County, GA (Atlanta)",
            "dataset_key": "fulton-probate",
        },
    },
}

PRACTICE_AREAS = [
    "Probate and Estate Administration",
    "Real Estate and Title Law",
    "Trust and Asset Protection",
    "Commercial Real Estate and Liens",
    "Creditor Rights and Foreclosure",
]


@dataclass
class DiscoveredBarAttorney:
    """An attorney discovered via public state bar association directory."""
    attorney_name: str
    firm_name: str
    state: str
    practice_area: str
    bar_number: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    profile_url: str = ""
    target_portal: dict[str, Any] = field(default_factory=dict)


class StateBarProspector:
    """Autonomous prospector that mines public State Bar directories for legal decision-makers."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def discover_attorneys(
        self,
        state_code: str = "TX",
        practice_area: str = "Probate and Estate Administration",
        max_results: int = 5,
    ) -> list[DiscoveredBarAttorney]:
        """Search public state bar directories for attorneys in high-value data-consuming practices."""
        cfg = STATE_BAR_CONFIGS.get(state_code.upper(), STATE_BAR_CONFIGS["TX"])
        bar_domain = cfg["search_domain"]
        state_name = cfg["state_name"]

        logger.info(f"⚖️ [STATE BAR PROSPECTOR] Searching {cfg['bar_name']} for {practice_area} practitioners...")

        # Search queries targeting official bar listings and accredited attorney directories
        queries = [
            f'site:{bar_domain} "{practice_area}" attorney lawyer active member',
            f'site:{bar_domain} "Find a Lawyer" "{practice_area}" {state_name}',
            f'"{cfg["bar_name"]}" "{practice_area}" law firm attorney {state_name}',
        ]

        discovered: list[DiscoveredBarAttorney] = []
        seen_names: set[str] = set()

        for q in queries:
            if len(discovered) >= max_results:
                break
            hits = search_web(q, max_results=max_results * 2)
            for h in hits:
                if len(discovered) >= max_results:
                    break
                title = h.get("title", "")
                url = h.get("url", "")
                snippet = h.get("snippet", "")

                attorney_name, firm_name, bar_no = self._parse_attorney_entry(title, snippet)
                if not attorney_name:
                    continue

                clean_name = attorney_name.strip().title()
                if clean_name.lower() in seen_names or is_disallowed_buyer(clean_name, "", ""):
                    continue

                seen_names.add(clean_name.lower())
                discovered.append(DiscoveredBarAttorney(
                    attorney_name=clean_name,
                    firm_name=firm_name or f"{clean_name} Law Group",
                    state=state_code.upper(),
                    practice_area=practice_area,
                    bar_number=bar_no,
                    profile_url=url,
                    target_portal=cfg["default_portal"],
                ))

        logger.info(f"✓ [STATE BAR PROSPECTOR] Found {len(discovered)} verified attorneys from {cfg['bar_name']}")
        return discovered

    def _parse_attorney_entry(self, title: str, snippet: str) -> tuple[str, str, str]:
        """Parse attorney name, firm, and bar number from directory listing."""
        # Clean title
        clean = re.sub(r"(?i)\s*\|\s*(State Bar|Find a Lawyer|Directory|Lawyer Profile).*$", "", title).strip()
        parts = [p.strip() for p in re.split(r"\s*[-–—|]\s*", clean) if p.strip()]

        attorney_name = ""
        firm_name = ""
        bar_no = ""

        # Extract Bar # from snippet if present
        m_bar = re.search(r"(?:bar\s*(?:no|number|#)?[:\s]+)(\d{5,10})", snippet, re.IGNORECASE)
        if m_bar:
            bar_no = m_bar.group(1)

        if len(parts) >= 2:
            candidate_p1 = parts[0]
            candidate_p2 = parts[1]
            words1 = candidate_p1.split()
            if 2 <= len(words1) <= 4 and not any(w in candidate_p1.lower() for w in ["search", "lawyer", "attorneys", "home"]):
                attorney_name = candidate_p1
                firm_name = candidate_p2 if "law" in candidate_p2.lower() or "llc" in candidate_p2.lower() or "pc" in candidate_p2.lower() else ""
        elif len(parts) == 1:
            words = parts[0].split()
            if 2 <= len(words) <= 4 and not any(w in parts[0].lower() for w in ["search", "directory", "attorneys"]):
                attorney_name = parts[0]

        return attorney_name, firm_name, bar_no

    def enrich_bar_prospect(
        self,
        attorney: DiscoveredBarAttorney,
        existing_companies: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Enrich state bar attorney with verified firm domain, contacts, and tailored outreach hook."""
        existing = existing_companies or set()
        if attorney.firm_name.lower() in existing or attorney.attorney_name.lower() in existing:
            return None

        # 1. Search for official law firm domain
        firm_query = f'"{attorney.firm_name}" "{attorney.attorney_name}" {attorney.state} attorney website'
        intel = search_company_intelligence(attorney.firm_name)
        website = intel.get("website", "")
        if not website or "http" not in website:
            hits = search_web(firm_query, max_results=3)
            for h in hits:
                url = h.get("url", "")
                if not is_disallowed_buyer(h.get("title", ""), url, ""):
                    website = url
                    break

        if not website:
            return None

        # 2. Extract verified contacts
        contact_info = extract_contact_info_from_url(website)
        raw_emails = contact_info.get("emails", [])
        verified_email = contact_info.get("verified_email") or (raw_emails[0] if raw_emails else "")
        verified_phone = contact_info.get("verified_phone") or (contact_info.get("phones")[0] if contact_info.get("phones") else "")

        # 3. Locate LinkedIn profile
        linkedin_contact = find_linkedin_decision_maker(attorney.attorney_name, domain_hint=website)
        linkedin_url = (linkedin_contact and linkedin_contact.get("linkedin_url")) or ""

        target_portal = attorney.target_portal
        portal_name = target_portal.get("portal_name", "County Probate & Civil Records")
        portal_url = target_portal.get("target_url", "https://data.gov")
        jurisdiction = target_portal.get("jurisdiction", f"{attorney.state} Statewide")

        # 4. Construct high-converting Bar Attorney pitch
        clean_first = attorney.attorney_name.split()[0]
        subject = f"{attorney.practice_area.split()[0].lower()} docket feeds for {attorney.firm_name.split()[0]}"
        body = (
            f"Hi {clean_first},\n\n"
            f"Saw your practice listed with the {STATE_BAR_CONFIGS.get(attorney.state, {}).get('bar_name', 'State Bar')} "
            f"focusing on {attorney.practice_area}.\n\n"
            f"Curious — how does your team track newly filed petitions and estate asset recordings in {portal_name}? "
            f"We build automated feeds that deliver new docket filings directly to your inbox/sheets each morning at 8 AM.\n\n"
            f"Here is a live preview sandbox configured for your jurisdiction:\n"
            f"{{sandbox_url}}\n\n"
            f"Worth a 2-minute look?\n"
            f"Alex | LeadOps Automation Engineering"
        )

        return {
            "company_name": attorney.firm_name,
            "contact_name": attorney.attorney_name,
            "contact_role": "Managing Partner / Attorney at Law",
            "contact_email": verified_email,
            "contact_phone": verified_phone,
            "linkedin_url": linkedin_url,
            "website": website,
            "discovery_channel": "STATE_BAR_DIRECTORY",
            "niche": attorney.practice_area,
            "pain_point": f"Manual monitoring and daily pulling of newly recorded court dockets from {portal_name}.",
            "target_url": portal_url,
            "portal_name": portal_name,
            "jurisdiction": jurisdiction,
            "bar_number": attorney.bar_number,
            "suggested_fields": ["case_number", "filing_date", "matter_title", "status", "source_url"],
            "tier_key": "daily",
            "pitch_subject": subject,
            "pitch_body": body,
        }
