"""Hiring Intent Prospector for LeadOps Swarm.

Scans live job boards and requisition feeds for small and medium businesses (SMBs)
actively recruiting for manual data entry, docket clerks, title searchers,
and permit coordinators.

Companies actively hiring for these positions are paying $40k-$65k/year for manual
data extraction; LeadOps' automated morning feed ($150-$250/mo) saves 90% of that cost.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from agents.llm_client import LLMAgentEngine, is_disallowed_buyer
from agents.logging_config import get_logger
from agents.tools.web_search import search_job_board_intent, search_company_intelligence
from agents.tools.web_fetcher import extract_contact_info_from_url

logger = get_logger("hiring_intent_prospector")

# Target Job Titles by Vertical
ROLE_CATALOG = {
    "Legal & Estate Administration": [
        "Docket Clerk",
        "Court Records Researcher",
        "Probate Paralegal",
        "Legal Intake Specialist",
        "Case Intake Specialist",
    ],
    "Real Estate Title & Escrow": [
        "Title Searcher",
        "Title Examiner",
        "Public Records Specialist",
        "Abstractor",
        "Escrow Assistant",
    ],
    "Commercial Construction & Permitting": [
        "Permit Coordinator",
        "Permit Expeditor",
        "Construction Project Coordinator",
        "Subcontract Administrator",
    ],
    "Commercial SMB Operations": [
        "Data Entry Specialist",
        "Records Coordinator",
        "Document Processing Specialist",
        "Data Entry Clerk",
    ],
}


@dataclass
class DiscoveredHiringProspect:
    """A business discovered via an active job posting for a manual data role."""
    company_name: str
    job_title: str
    location: str
    vertical: str
    job_url: str
    job_snippet: str = ""
    website: str = ""
    domain: str = ""
    phone: str = ""
    contact_email: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_pitch_context(self) -> dict[str, str]:
        """Generate custom pitch variables referencing their exact open role."""
        return {
            "company_name": self.company_name,
            "job_title": self.job_title,
            "location": self.location,
            "vertical": self.vertical,
            "website": self.website,
        }


class HiringIntentProspector:
    """Autonomous prospector that mines job postings for companies with manual data pain."""

    def __init__(self, llm_engine: Optional[LLMAgentEngine] = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def discover_hiring_companies(
        self,
        location: str = "Seattle WA",
        target_roles: Optional[list[str]] = None,
        max_results: int = 5,
    ) -> list[DiscoveredHiringProspect]:
        """Search live job boards for SMBs hiring manual data entry or records staff in a target metro."""
        logger.info(f"🔎 [HIRING SCOUT] Scanning job requisitions in '{location}' for manual data roles...")

        roles_to_scan = target_roles or [
            "Permit Coordinator",
            "Docket Clerk",
            "Title Searcher",
            "Public Records Specialist",
            "Court Records Researcher",
            "Data Entry Specialist",
        ]

        discovered: list[DiscoveredHiringProspect] = []
        seen_companies: set[str] = set()

        for role in roles_to_scan:
            if len(discovered) >= max_results:
                break

            try:
                hits = search_job_board_intent(keywords=role, location=location)
                for h in hits:
                    if len(discovered) >= max_results:
                        break

                    c_name = h.get("company_name", "").strip()
                    clean_name = re.sub(r"(?i)\s+(inc|llc|corp|co|pllc|ltd)\.?$", "", c_name).strip()
                    norm_name = clean_name.lower()

                    if not clean_name or norm_name in seen_companies:
                        continue
                    if is_disallowed_buyer(clean_name, h.get("job_url", ""), ""):
                        continue

                    # Classify vertical
                    vertical = self._classify_role_vertical(h.get("job_title", role))

                    seen_companies.add(norm_name)
                    discovered.append(DiscoveredHiringProspect(
                        company_name=clean_name,
                        job_title=h.get("job_title", role),
                        location=h.get("location", location),
                        vertical=vertical,
                        job_url=h.get("job_url", ""),
                        job_snippet=h.get("snippet", ""),
                    ))
                    logger.info(f"✓ [HIRING HIT] {clean_name} is hiring '{h.get('job_title', role)}' in {h.get('location', location)}")

            except Exception as e:
                logger.debug(f"Job board query for role '{role}' in '{location}' note: {e}")

        # Enrich discovered prospects with company websites and domains
        enriched = [self.enrich_prospect(p) for p in discovered]
        logger.info(f"✓ [HIRING SCOUT] Discovered & enriched {len(enriched)} active hiring SMBs in '{location}'")
        return enriched

    def enrich_prospect(self, prospect: DiscoveredHiringProspect) -> DiscoveredHiringProspect:
        """Find official website, domain, and phone number for a discovered hiring company."""
        if prospect.website and prospect.domain:
            return prospect

        try:
            intel = search_company_intelligence(prospect.company_name, prospect.location)
            if intel.get("website"):
                raw_ws = intel["website"].strip()
                if "." in raw_ws and "/" not in raw_ws.split(".")[0]:
                    if not raw_ws.startswith("http"):
                        raw_ws = f"https://{raw_ws}"
                    prospect.website = raw_ws
                    # Extract domain
                    m_dom = re.search(r"https?://(?:www\.)?([^/]+)", prospect.website)
                    prospect.domain = m_dom.group(1).lower() if m_dom else ""

            if intel.get("phone"):
                prospect.phone = intel["phone"]

            # If website was found, attempt contact page scrape for phone / email
            if prospect.website:
                c_info = extract_contact_info_from_url(prospect.website)
                if not prospect.phone and c_info.get("phones"):
                    prospect.phone = c_info["phones"][0]
                if not prospect.contact_email and c_info.get("emails"):
                    prospect.contact_email = c_info["emails"][0]

        except Exception as e:
            logger.debug(f"Company enrichment note for {prospect.company_name}: {e}")

        return prospect

    def format_hiring_intent_pitch(
        self,
        prospect: DiscoveredHiringProspect,
        county_or_city: str = "",
    ) -> dict[str, str]:
        """Generate Zero-Link sub-50-word permission-first outreach hook referencing their open requisition."""
        loc = county_or_city or prospect.location or "your area"
        role = prospect.job_title

        short_company = prospect.company_name.split()[0] if len(prospect.company_name.split()) > 2 else prospect.company_name
        subject = f"{role} role at {short_company}"
        body = (
            f"Hi Team,\n\n"
            f"Saw you're hiring a {role} in {loc}.\n\n"
            f"Curious — if your team pulls local county dockets or permits manually, "
            f"would an automated 8 AM morning sheet feed help save hours?\n\n"
            f"Mind if I send over a 2-minute live preview?\n\n"
            f"Alex | LeadOps"
        )
        return {"subject": subject, "body": body}

    def _classify_role_vertical(self, job_title: str) -> str:
        """Classify job title into commercial vertical."""
        jt = job_title.lower()
        if any(w in jt for w in ["docket", "probate", "court", "legal", "law", "paralegal"]):
            return "Legal & Estate Administration"
        if any(w in jt for w in ["permit", "construction", "hvac", "roofing", "contractor"]):
            return "Commercial Construction & Permitting"
        if any(w in jt for w in ["title", "escrow", "abstractor", "lien"]):
            return "Real Estate Title & Escrow"
        return "Commercial SMB Operations"
