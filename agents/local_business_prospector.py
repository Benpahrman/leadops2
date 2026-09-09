"""Local Business & Maps Discovery Prospector for LeadOps Scout.

Discovers established regional title companies, escrow settlement offices, and probate attorneys
by mining local search indexes and map directories by metro market and county.
Pulls verified phone numbers, corporate domains, and physical addresses, then crawls domains
for executive decision-makers.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .llm_client import LLMAgentEngine, is_disallowed_buyer
from .tools.web_search import search_web, search_company_intelligence, find_linkedin_decision_maker
from .tools.web_fetcher import extract_contact_info_from_url
from .logging_config import get_logger

logger = get_logger("local_business_prospector")

TARGET_METROS = [
    {"city": "Dallas", "state": "TX", "county": "Dallas County", "portal_name": "Dallas County Clerk & Deeds Registry", "portal_url": "https://www.dallascounty.org/government/county-clerk/"},
    {"city": "Houston", "state": "TX", "county": "Harris County", "portal_name": "Harris County District Clerk & County Clerk", "portal_url": "https://www.cclerk.hctx.net/"},
    {"city": "Orlando", "state": "FL", "county": "Orange County", "portal_name": "Orange County Comptroller & Clerk Registry", "portal_url": "https://www.occompt.com/"},
    {"city": "Chicago", "state": "IL", "county": "Cook County", "portal_name": "Cook County Probate Division Court Portal", "portal_url": "https://www.cookcountyclerkofcourt.org/"},
    {"city": "Atlanta", "state": "GA", "county": "Fulton County", "portal_name": "Probate Court of Fulton County", "portal_url": "https://www.fultoncountyga.gov/probatecourt"},
    {"city": "Phoenix", "state": "AZ", "county": "Maricopa County", "portal_name": "Maricopa County Treasurer & Assessor", "portal_url": "https://treasurer.maricopa.gov/"},
]

LOCAL_NICHES = [
    "Title Company",
    "Probate Law Firm",
    "Real Estate Escrow Agency",
    "Commercial Abstractor",
]


@dataclass
class DiscoveredLocalBusiness:
    """A local commercial business discovered via maps or local directory search."""
    business_name: str
    city: str
    state: str
    county: str
    category: str
    website: str = ""
    phone: str = ""
    address: str = ""
    source_query: str = ""
    portal_info: dict[str, Any] = field(default_factory=dict)


class LocalBusinessProspector:
    """Autonomous prospector that mines local business and map directories for regional operators."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def discover_local_operators(
        self,
        city: str = "Houston",
        state: str = "TX",
        category: str = "Title Company",
        max_results: int = 5,
    ) -> list[DiscoveredLocalBusiness]:
        """Search local directories and map indexes for active commercial operators in a target city."""
        logger.info(f"📍 [LOCAL MAP SCOUT] Searching local directories for '{category}' in {city}, {state}...")

        # Match metro config if available
        matched_metro = next(
            (m for m in TARGET_METROS if m["city"].lower() == city.lower() and m["state"].lower() == state.lower()),
            {"city": city, "state": state, "county": f"{city} County", "portal_name": f"{city} County Public Records", "portal_url": "https://data.gov"}
        )

        queries = [
            f'"{category}" "{city}" "{state}" local business directory phone address',
            f'top rated "{category}" in "{city}, {state}" official website',
            f'independent "{category}" offices "{city}" "{state}"',
        ]

        discovered: list[DiscoveredLocalBusiness] = []
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

                b_name, b_phone, b_addr = self._parse_local_entry(title, snippet, category)
                if not b_name:
                    continue

                if is_disallowed_buyer(b_name, url, ""):
                    continue

                norm_b = b_name.lower()
                if norm_b in seen_names or any(w in norm_b for w in ["best", "top 10", "yelp", "yellowpages", "mapquest", "chamber of commerce"]):
                    continue

                seen_names.add(norm_b)
                discovered.append(DiscoveredLocalBusiness(
                    business_name=b_name,
                    city=city,
                    state=state,
                    county=matched_metro.get("county", f"{city} County"),
                    category=category,
                    website=url if "http" in url and not any(d in url for d in ["yelp.com", "yellowpages.com", "google.com", "bing.com"]) else "",
                    phone=b_phone,
                    address=b_addr,
                    source_query=q,
                    portal_info=matched_metro,
                ))

        logger.info(f"✓ [LOCAL MAP SCOUT] Discovered {len(discovered)} local operators in {city}, {state}")
        return discovered

    def _parse_local_entry(self, title: str, snippet: str, category: str) -> tuple[str, str, str]:
        """Parse local business name, telephone, and address from search snippet."""
        clean_title = re.split(r"[:\|\-–•]", title)[0].strip()
        clean_title = re.sub(r"(?i)\s*(in|near)\s+.*$", "", clean_title).strip()

        # Phone extraction
        m_phone = re.search(r"\(?\b([2-9]\d{2})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b", snippet)
        phone = f"({m_phone.group(1)}) {m_phone.group(2)}-{m_phone.group(3)}" if m_phone else ""

        # Address extraction
        m_addr = re.search(r"\b\d+\s+[A-Za-z0-9\s,\.]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Rd|Road|Pkwy|Parkway|Ste|Suite)\b", snippet, re.IGNORECASE)
        address = m_addr.group(0).strip() if m_addr else ""

        return clean_title, phone, address

    def enrich_local_prospect(
        self,
        business: DiscoveredLocalBusiness,
        existing_companies: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Enrich local business operator with corporate domain, decision-maker, and geo-targeted pitch."""
        existing = existing_companies or set()
        if business.business_name.lower() in existing:
            return None

        # 1. Search for official website if not already present
        website = business.website
        if not website:
            intel = search_company_intelligence(business.business_name)
            website = intel.get("website", "")
            if not website or "http" not in website:
                hits = search_web(f'"{business.business_name}" official website {business.city} {business.state}', max_results=3)
                for h in hits:
                    url = h.get("url", "")
                    if not is_disallowed_buyer(h.get("title", ""), url, "") and not any(d in url for d in ["yelp.com", "yellowpages.com"]):
                        website = url
                        break

        if not website:
            return None

        # 2. Extract verified contacts
        contact_info = extract_contact_info_from_url(website)
        raw_emails = contact_info.get("emails", [])
        verified_email = contact_info.get("verified_email") or (raw_emails[0] if raw_emails else "")
        verified_phone = business.phone or contact_info.get("verified_phone") or (contact_info.get("phones")[0] if contact_info.get("phones") else "")

        # 3. Decision maker lookup
        linkedin_contact = find_linkedin_decision_maker(business.business_name, domain_hint=website)
        contact_name = (linkedin_contact and linkedin_contact.get("name")) or "Operations Director"
        contact_role = (linkedin_contact and linkedin_contact.get("role")) or "Managing Director / Principal"
        linkedin_url = (linkedin_contact and linkedin_contact.get("linkedin_url")) or ""

        portal = business.portal_info
        portal_name = portal.get("portal_name", f"{business.county} Public Records Portal")
        portal_url = portal.get("portal_url", "https://data.gov")

        # 4. Construct local market geo-targeted pitch
        subject = f"{business.city.lower()} public recordings for {business.business_name.split()[0]}"
        body = (
            f"Hi {contact_name.split()[0] if contact_name != 'Operations Director' else 'Team'},\n\n"
            f"Saw your {business.category.lower()} practice serving the {business.city} area.\n\n"
            f"Curious — does your staff still manually pull newly recorded deeds, liens, and probate filings from {portal_name}? "
            f"We build automated feeds that deliver newly indexed county records straight to your spreadsheet every weekday morning at 8 AM.\n\n"
            f"Built an interactive data sandbox populated with live local recordings here:\n"
            f"{{sandbox_url}}\n\n"
            f"Worth a 2-minute look to save 10+ hours of staff time each week?\n"
            f"Alex | LeadOps Automation Engineering"
        )

        return {
            "company_name": business.business_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": verified_email,
            "contact_phone": verified_phone,
            "linkedin_url": linkedin_url,
            "website": website,
            "discovery_channel": "GOOGLE_MAPS_LOCAL",
            "niche": f"Regional {business.category} Operations",
            "pain_point": f"Manual daily record pulling and deed examination from {portal_name}.",
            "target_url": portal_url,
            "portal_name": portal_name,
            "jurisdiction": f"{business.city}, {business.county}, {business.state}",
            "local_address": business.address,
            "suggested_fields": ["document_id", "recording_date", "grantor", "grantee", "document_type", "source_url"],
            "tier_key": "daily",
            "pitch_subject": subject,
            "pitch_body": body,
        }
