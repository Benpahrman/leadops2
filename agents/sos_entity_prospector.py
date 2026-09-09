"""Secretary of State (SOS) Business Entity Discovery Prospector for LeadOps Scout.

Mines state corporate registries (Texas SOS, Florida Sunbiz, Delaware Division of Corporations,
California SOS) for newly registered commercial title agencies, abstractors, settlement services,
and boutique law firms. Newly formed firms have fresh operational budgets and urgently need
automated docket feeds to jumpstart production.
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

logger = get_logger("sos_entity_prospector")

TARGET_ENTITY_KEYWORDS = [
    "Title Agency", "Title Company", "Abstract & Title", "Settlement Services",
    "Escrow Services", "Equipment Finance", "Asset Lending", "Legal PLLC"
]

SOS_REGISTRY_CONFIGS: dict[str, dict[str, Any]] = {
    "TX": {
        "state_name": "Texas",
        "sos_name": "Texas Secretary of State Business Registry",
        "search_domain": "sos.state.tx.us",
        "portal_url": "https://www.sos.state.tx.us/corp/entity.shtml",
        "default_portal": {
            "portal_name": "Texas Secretary of State Corporate & UCC Registry",
            "target_url": "https://data.texas.gov/",
            "jurisdiction": "State of Texas (Austin)",
            "dataset_key": "texas-open-data",
        }
    },
    "FL": {
        "state_name": "Florida",
        "sos_name": "Florida Sunbiz Division of Corporations",
        "search_domain": "sunbiz.org",
        "portal_url": "https://search.sunbiz.org/",
        "default_portal": {
            "portal_name": "Orange County Comptroller & Clerk Registry",
            "target_url": "https://www.occompt.com/",
            "jurisdiction": "Orange County, FL (Orlando)",
            "dataset_key": "orange-foreclosure",
        }
    },
    "DE": {
        "state_name": "Delaware",
        "sos_name": "Delaware Division of Corporations & Revenue",
        "search_domain": "corp.delaware.gov",
        "portal_url": "https://data.delaware.gov/Economic-Development/Delaware-Business-Licenses/5zy2-grhr",
        "default_portal": {
            "portal_name": "Delaware Corporate & Business License Registry",
            "target_url": "https://data.delaware.gov/resource/5zy2-grhr.json",
            "jurisdiction": "State of Delaware",
            "dataset_key": "state-ucc-filings",
        }
    },
    "CA": {
        "state_name": "California",
        "sos_name": "California Secretary of State BizFile",
        "search_domain": "bizfileonline.sos.ca.gov",
        "portal_url": "https://bizfileonline.sos.ca.gov/",
        "default_portal": {
            "portal_name": "California Business & Corporate Filings",
            "target_url": "https://data.ca.gov/",
            "jurisdiction": "State of California (Sacramento)",
            "dataset_key": "texas-open-data",
        }
    }
}


@dataclass
class DiscoveredSOSEntity:
    """A newly registered commercial entity discovered via Secretary of State filing."""
    company_name: str
    state: str
    entity_type: str
    filing_date: str = ""
    registered_agent: str = ""
    filing_number: str = ""
    jurisdiction: str = ""
    registry_url: str = ""


class SOSEntityProspector:
    """Autonomous prospector that queries state corporate registries for newly formed commercial buyers."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def discover_new_registrations(
        self,
        state_code: str = "TX",
        keyword: str = "Title Company",
        max_results: int = 5,
    ) -> list[DiscoveredSOSEntity]:
        """Search state corporate registries for recently registered firms."""
        cfg = SOS_REGISTRY_CONFIGS.get(state_code.upper(), SOS_REGISTRY_CONFIGS["TX"])
        state_name = cfg["state_name"]

        logger.info(f"🏢 [SOS ENTITY PROSPECTOR] Searching {cfg['sos_name']} for newly formed '{keyword}' entities...")

        queries = [
            f'site:{cfg["search_domain"]} "{keyword}" LLC OR Inc registered entity',
            f'"{cfg["sos_name"]}" "{keyword}" "formation date" OR "registered" {state_name}',
            f'newly registered "{keyword}" "{state_name}" LLC filing',
        ]

        discovered: list[DiscoveredSOSEntity] = []
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

                company_name, agent, file_no = self._parse_entity_listing(title, snippet, keyword)
                if not company_name:
                    continue

                norm_name = company_name.lower()
                if norm_name in seen_names or is_disallowed_buyer(company_name, "", ""):
                    continue

                seen_names.add(norm_name)
                discovered.append(DiscoveredSOSEntity(
                    company_name=company_name,
                    state=state_code.upper(),
                    entity_type=keyword,
                    registered_agent=agent,
                    filing_number=file_no,
                    jurisdiction=f"{state_name} Statewide",
                    registry_url=url,
                ))

        logger.info(f"✓ [SOS ENTITY PROSPECTOR] Discovered {len(discovered)} commercial entities from {cfg['sos_name']}")
        return discovered

    def _parse_entity_listing(self, title: str, snippet: str, keyword: str) -> tuple[str, str, str]:
        """Parse corporate entity name, registered agent, and file number."""
        clean_title = re.sub(r"(?i)\s*\|\s*(Secretary of State|Sunbiz|Corp Division|Entity Details).*$", "", title).strip()
        parts = [p.strip() for p in re.split(r"\s*[-–—|]\s*", clean_title) if p.strip()]

        company_name = ""
        agent = ""
        file_no = ""

        # Check for registered agent
        m_agent = re.search(r"(?:registered agent|agent for service)[:\s]+([A-Z][a-zA-Z\s,\.\-]+?)(?:;|\.|\n|$)", snippet, re.IGNORECASE)
        if m_agent:
            agent = m_agent.group(1).strip()

        # Check for filing or filing ID
        m_fileno = re.search(r"(?:filing|file|entity|charter)\s*(?:#|no|number)?[:\s]+([A-Z0-9\-]+)", snippet, re.IGNORECASE)
        if m_fileno:
            file_no = m_fileno.group(1).strip()

        if parts:
            c_candidate = parts[0]
            # Ensure entity indicator
            if any(w in c_candidate.lower() for w in ["llc", "inc", "title", "escrow", "services", "group", "pllc", "corp"]):
                company_name = c_candidate
            elif len(parts) > 1 and any(w in parts[1].lower() for w in ["llc", "inc", "title", "escrow", "services"]):
                company_name = parts[1]
            else:
                company_name = f"{c_candidate} {keyword}"

        return company_name, agent, file_no

    def enrich_sos_prospect(
        self,
        entity: DiscoveredSOSEntity,
        existing_companies: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Enrich newly formed entity with corporate domain, decision-maker, and launch pitch."""
        existing = existing_companies or set()
        if entity.company_name.lower() in existing:
            return None

        # 1. Search for official company domain
        intel = search_company_intelligence(entity.company_name)
        website = intel.get("website", "")
        if not website or "http" not in website:
            hits = search_web(f'"{entity.company_name}" official website {entity.state}', max_results=3)
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

        # 3. Decision maker lookup
        lookup_name = entity.registered_agent or entity.company_name
        linkedin_contact = find_linkedin_decision_maker(lookup_name, domain_hint=website)
        contact_name = (linkedin_contact and linkedin_contact.get("name")) or (entity.registered_agent if len(entity.registered_agent.split()) in [2, 3] else "Operations Director")
        contact_role = (linkedin_contact and linkedin_contact.get("role")) or "Managing Director / Principal"
        linkedin_url = (linkedin_contact and linkedin_contact.get("linkedin_url")) or ""

        cfg = SOS_REGISTRY_CONFIGS.get(entity.state, SOS_REGISTRY_CONFIGS["TX"])
        default_portal = cfg["default_portal"]

        # 4. Construct pitch tailored to new operations onboarding
        subject = f"{entity.entity_type.lower()} public records feed for {entity.company_name.split()[0]}"
        body = (
            f"Hi {contact_name.split()[0]},\n\n"
            f"Saw {entity.company_name} registered for {entity.entity_type} operations in {entity.state}.\n\n"
            f"Curious — as you ramp up daily processing, does your team plan to pull county property and lien records manually? "
            f"We build automated feeds that deliver newly filed documents and dockets straight to your pipeline every morning.\n\n"
            f"Configured an interactive data sandbox for your jurisdiction here:\n"
            f"{{sandbox_url}}\n\n"
            f"Worth a quick look as you set up operations?\n"
            f"Alex | LeadOps Automation Engineering"
        )

        return {
            "company_name": entity.company_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": verified_email,
            "contact_phone": verified_phone,
            "linkedin_url": linkedin_url,
            "website": website,
            "discovery_channel": "SOS_NEW_BUSINESS",
            "niche": f"Commercial Operations ({entity.entity_type})",
            "pain_point": f"Setting up automated daily public record feeds for newly registered operations in {entity.state}.",
            "target_url": default_portal["target_url"],
            "portal_name": default_portal["portal_name"],
            "jurisdiction": entity.jurisdiction,
            "filing_number": entity.filing_number,
            "suggested_fields": ["entity_id", "recording_date", "document_type", "status", "source_url"],
            "tier_key": "weekly",
            "pitch_subject": subject,
            "pitch_body": body,
        }
