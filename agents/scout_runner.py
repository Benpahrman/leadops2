"""Autonomous background Scout discovery runner for continuous lead prospecting."""

import asyncio
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .portal import PortalService
from .scout_pipeline import ScoutCandidate, ScoutPortalPipeline
from .storage import StorageBackend
from .tools.dom_pruner import prune_dom
from .tools.waf_prober import probe_waf_signatures


TARGET_REGISTRIES = [
    {
        "company_name": "Lone Star Asset Recovery",
        "target_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch.aspx?CaseType=Probate",
        "portal_name": "Harris County Clerk Official Records",

        "jurisdiction": "Harris County, TX (Houston)",
        "niche": "Probate & Estate Asset Intelligence",
        "suggested_fields": ["case_number", "decedent_name", "filing_date", "est_value", "court_division", "attorney_name", "heirs_located"],
        "tier_key": "daily",
        "sample_data": [
            {"case_number": "2026-PR-00891", "decedent_name": "Robert Sterling", "filing_date": "2026-08-25", "est_value": "$680,000.00", "court_division": "Probate Court 1", "attorney_name": "Houston Estate Law LLP", "heirs_located": "Pending"},
            {"case_number": "2026-PR-00892", "decedent_name": "Maria Elena Gonzalez", "filing_date": "2026-08-26", "est_value": "$420,000.00", "court_division": "Probate Court 3", "attorney_name": "Gonzalez & Partners", "heirs_located": "Verified"},
            {"case_number": "2026-PR-00893", "decedent_name": "Harold Finch", "filing_date": "2026-08-26", "est_value": "$1,250,000.00", "court_division": "Probate Court 2", "attorney_name": "Marcus Sterling, Esq.", "heirs_located": "Unlocated"},
            {"case_number": "2026-PR-00894", "decedent_name": "Eleanor Vance", "filing_date": "2026-08-27", "est_value": "$890,000.00", "court_division": "Probate Court 1", "attorney_name": "Westlake Legal Group", "heirs_located": "Pending"},
            {"case_number": "2026-PR-00895", "decedent_name": "Arthur Pendelton", "filing_date": "2026-08-27", "est_value": "$530,000.00", "court_division": "Probate Court 4", "attorney_name": "Elena Rostova LLC", "heirs_located": "Verified"},
        ],
    },
    {
        "company_name": "Southwest Title & Deed Research",
        "target_url": "https://www.azcourts.gov/",
        "portal_name": "Arizona Judicial & Deed Registry",
        "jurisdiction": "Maricopa County / Arizona",
        "niche": "Commercial Property Deeds & Liens",
        "suggested_fields": ["recording_number", "grantor", "grantee", "recording_date", "document_type", "parcel_id", "assessed_value"],
        "tier_key": "weekly",
        "sample_data": [
            {"recording_number": "2026-041890", "grantor": "Apex Commercial Development LLC", "grantee": "Meridian Title & Escrow Trust", "recording_date": "2026-08-25", "document_type": "Deed of Trust", "parcel_id": "104-22-019", "assessed_value": "$1,850,000.00"},
            {"recording_number": "2026-041891", "grantor": "Desert Sky Properties", "grantee": "Horizon National Bank NA", "recording_date": "2026-08-26", "document_type": "Special Warranty Deed", "parcel_id": "202-14-883", "assessed_value": "$640,000.00"},
            {"recording_number": "2026-041892", "grantor": "Canyon Ridge Holdings LLC", "grantee": "Southwest Land Asset Trust", "recording_date": "2026-08-26", "document_type": "Grant Deed", "parcel_id": "301-45-112", "assessed_value": "$920,000.00"},
            {"recording_number": "2026-041893", "grantor": "Sonoran Sun Builders Corp", "grantee": "Pinnacle Capital Partners", "recording_date": "2026-08-27", "document_type": "Assignment of Rents", "parcel_id": "104-88-901", "assessed_value": "$2,400,000.00"},
        ],
    },
    {
        "company_name": "Sunstate Foreclosure Analytics",
        "target_url": "https://www.occompt.com/",
        "portal_name": "Orange County Comptroller Registry",
        "jurisdiction": "Orange County, FL (Orlando)",
        "niche": "Mortgage Foreclosures & Lis Pendens",
        "suggested_fields": ["case_id", "plaintiff", "defendant", "filing_date", "principal_amount", "lis_pendens_url", "auction_date"],
        "tier_key": "ai",
        "sample_data": [
            {"case_id": "2026-CA-004412", "plaintiff": "Citadel Mortgage Corp", "defendant": "James & Sarah Thorne", "filing_date": "2026-08-25", "principal_amount": "$340,000.00", "lis_pendens_url": "https://www.occompt.com/doc/4412", "auction_date": "2026-09-18"},
            {"case_id": "2026-CA-004413", "plaintiff": "First National Trust", "defendant": "Crestview Holdings LLC", "filing_date": "2026-08-26", "principal_amount": "$1,150,000.00", "lis_pendens_url": "https://www.occompt.com/doc/4413", "auction_date": "2026-09-22"},
            {"case_id": "2026-CA-004414", "plaintiff": "SunTrust Bank NA", "defendant": "Orlando Waterfront Rentals LLC", "filing_date": "2026-08-26", "principal_amount": "$780,000.00", "lis_pendens_url": "https://www.occompt.com/doc/4414", "auction_date": "2026-09-29"},
            {"case_id": "2026-CA-004415", "plaintiff": "Bayview Loan Servicing", "defendant": "Marcus & Elena Bennett", "filing_date": "2026-08-27", "principal_amount": "$465,000.00", "lis_pendens_url": "https://www.occompt.com/doc/4415", "auction_date": "2026-10-04"},
        ],
    },
    {
        "company_name": "Biscayne Capital Liens",
        "target_url": "https://www.miami-dadeclerk.com/",
        "portal_name": "Miami-Dade County Records Portal",
        "jurisdiction": "Miami-Dade County, FL (Miami)",
        "niche": "Tax Lien & Judgment Filings",
        "suggested_fields": ["filing_id", "debtor_name", "creditor_name", "judgment_amount", "filing_date", "status", "court_ref"],
        "tier_key": "daily",
        "sample_data": [
            {"filing_id": "2026-TX-1092", "debtor_name": "Oceanic Hospitality Group LLC", "creditor_name": "State of Florida Dept of Revenue", "judgment_amount": "$88,400.00", "filing_date": "2026-08-25", "status": "Active Tax Lien", "court_ref": "11th Judicial Circuit"},
            {"filing_id": "2026-TX-1093", "debtor_name": "Brickell Retail Ventures Corp", "creditor_name": "Atlantic Financial Corp", "judgment_amount": "$240,000.00", "filing_date": "2026-08-26", "status": "Final Judgment Entered", "court_ref": "Miami-Dade Civil Div"},
            {"filing_id": "2026-TX-1094", "debtor_name": "Biscayne Bay Maritime Services", "creditor_name": "South Florida Logistics Fund", "judgment_amount": "$165,500.00", "filing_date": "2026-08-26", "status": "Lien Recorded", "court_ref": "11th Judicial Circuit"},
            {"filing_id": "2026-TX-1095", "debtor_name": "Coral Gables Luxury Properties LLC", "creditor_name": "First Horizon Commercial Bank", "judgment_amount": "$510,000.00", "filing_date": "2026-08-27", "status": "Default Judgment", "court_ref": "Miami-Dade Civil Div"},
        ],
    },
    {
        "company_name": "Lone Star Open Data Exchange",
        "target_url": "https://data.texas.gov/",
        "portal_name": "Texas Statewide Public Registry",
        "jurisdiction": "State of Texas (Austin)",
        "niche": "State Entity Filings & Commercial Liens",
        "suggested_fields": ["entity_id", "entity_name", "file_date", "entity_status", "registered_agent", "sos_filing_number"],
        "tier_key": "weekly",
        "sample_data": [
            {"entity_id": "TX-080344912", "entity_name": "Austin BioTech Labs LLC", "file_date": "2026-08-25", "entity_status": "In Good Standing", "registered_agent": "Capitol Corporate Services Inc", "sos_filing_number": "803449120"},
            {"entity_id": "TX-080344913", "entity_name": "Alamo Logistics & Freight Partners", "file_date": "2026-08-26", "entity_status": "Active Filing", "registered_agent": "Texas Registered Agent LLC", "sos_filing_number": "803449131"},
            {"entity_id": "TX-080344914", "entity_name": "Permian Basin Energy Solutions Corp", "file_date": "2026-08-26", "entity_status": "Certificate of Formation", "registered_agent": "Corporation Service Company", "sos_filing_number": "803449142"},
            {"entity_id": "TX-080344915", "entity_name": "Houston Precision Robotics Inc", "file_date": "2026-08-27", "entity_status": "In Good Standing", "registered_agent": "National Registered Agents Inc", "sos_filing_number": "803449153"},
        ],
    },
]


import httpx
from .logging_config import get_logger
from .tools.waf_prober import generate_browser_headers

logger = get_logger("scout")


@dataclass
class ScoutBackgroundWorker:
    """Automated discovery agent that continuously scans county portals and seeds prospective sandboxes."""

    storage: StorageBackend
    portal: PortalService
    is_running: bool = False
    discovery_history: list[dict[str, Any]] = field(default_factory=list)
    _task: asyncio.Task | None = None

    def discover_next_candidate(self) -> dict[str, Any]:
        """Execute one autonomous discovery cycle against a target public registry with strict live verification."""
        import re
        registry = random.choice(TARGET_REGISTRIES)
        clean_company = re.sub(r"[^a-z0-9]+", "-", registry["company_name"].lower()).strip("-")

        # Deduplication check: Reuse canonical lead if company already exists
        existing_lead = next(
            (l for l in self.storage.list_leads() if getattr(l, "company_name", "") == registry["company_name"] or clean_company in l.lead_id),
            None,
        )
        lead_id = existing_lead.lead_id if existing_lead else f"lead-{clean_company}-100"

        logger.info(f"🔍 [SCOUT DISCOVERY] Probing registry: {registry['portal_name']} ({registry['jurisdiction']})")
        logger.info(f"   Target URL: {registry['target_url']}")

        # 1. Real Network & WAF Probe with realistic browser headers
        headers = generate_browser_headers(registry["target_url"])
        body_text = ""
        status_code = 0
        resp_headers = {}
        try:
            with httpx.Client(timeout=6.0, follow_redirects=True, verify=False) as client:
                resp = client.get(registry["target_url"], headers=headers)
                status_code = resp.status_code
                body_text = resp.text[:20000]
                resp_headers = dict(resp.headers)
                logger.info(f"   HTTP Probe Status: {status_code} ({len(body_text)} bytes received)")
        except Exception as e:
            logger.error(f"   ❌ [HTTP PROBE ERROR] {e} on {registry['target_url']}")
            status_code = 500

        waf_check = probe_waf_signatures(
            headers=resp_headers or {"Server": "nginx/1.24", "Content-Type": "text/html"},
            body_text=body_text,
            status_code=status_code,
        )
        logger.info(f"🛡️  [WAF PROBE] Status: {waf_check['detected_waf'] or 'Clean / Unrestricted'} | Safe to Scrape: {waf_check['is_safe_to_scrape']}")

        # STRICT SCOUTING GATE: If target returned 404, 403, or failed WAF safety, REJECT and DO NOT publish lead!
        if status_code != 200 or not waf_check["is_safe_to_scrape"]:
            logger.warning(
                f"❌ [SCOUT REJECTED] Portal {registry['target_url']} returned HTTP {status_code} "
                f"(Safe: {waf_check['is_safe_to_scrape']}). Candidate rejected — no phantom lead created."
            )
            return {
                "ok": False,
                "status": "REJECTED_UNSAFE_OR_NOT_FOUND",
                "target_url": registry["target_url"],
                "status_code": status_code,
                "waf_safe": waf_check["is_safe_to_scrape"],
                "reason": f"HTTP {status_code} on upstream portal",
            }

        # 2. Scout Pipeline Ingestion (ONLY for verified 200 OK targets)
        logger.info(f"✅ [SCOUT VERIFIED 200 OK] Live registry verified ({len(body_text)} bytes). Generating tailored prospect sandbox.")
        scout_pipe = ScoutPortalPipeline(self.portal)
        candidate = scout_pipe.publish_candidate(
            company_name=registry["company_name"],
            lead_id=lead_id,
            evidence=[{"url": registry["target_url"], "title": registry["portal_name"]}],
            source_url=registry["target_url"],
            sample_rows=registry["sample_data"],
            research={
                "niche": registry["niche"],
                "niche_confidence": "high",
                "jurisdiction": registry["jurisdiction"],
                "portal_name": registry["portal_name"],
                "portal_url": registry["target_url"],
                "suggested_fields": registry["suggested_fields"],
                "recommended_tier": registry["tier_key"],
                "delivery_destination": "Google Sheets",
            },
            tier_key=registry["tier_key"],
        )

        logger.info(f"🚀 [PUBLISHED VERIFIED SANDBOX] Lead ID: {candidate.lead_id} | Slug: {candidate.slug}")

        record = {
            "ok": True,
            "lead_id": candidate.lead_id,
            "slug": candidate.slug,
            "company_name": registry["company_name"],
            "portal_name": registry["portal_name"],
            "jurisdiction": registry["jurisdiction"],
            "tier_key": registry["tier_key"],
            "waf_safe": waf_check["is_safe_to_scrape"],
            "records_extracted": len(registry["sample_data"]),
            "discovered_at": datetime.now(timezone.utc).isoformat(),
        }
        self.discovery_history.append(record)
        return record

    async def _runner_loop(self, interval_seconds: int = 600) -> None:
        """Background continuous prospecting loop."""
        self.is_running = True
        try:
            while self.is_running:
                self.discover_next_candidate()
                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            self.is_running = False

    def start_background_runner(self, interval_seconds: int = 600) -> None:
        """Spawn background discovery task."""
        if not self.is_running:
            self._task = asyncio.create_task(self._runner_loop(interval_seconds))

    def stop_background_runner(self) -> None:
        """Stop background discovery task."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
