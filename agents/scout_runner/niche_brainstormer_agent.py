"""Niche Brainstormer Swarm Agent for LeadOps.

Autonomous LLM-driven specialist that discovers high-intent SMB verticals,
identifies manual docket/records bottlenecks, generates search operators,
and extracts hiring-intent job titles for any Washington county or target jurisdiction.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from agents.llm import LLMAgentEngine
from agents.logging_config import get_logger

logger = get_logger("niche_brainstormer")


@dataclass
class BrainstormedNiche:
    """A discovered commercial niche with actionable operational intelligence."""
    niche_name: str
    vertical_category: str
    target_buyer: str
    operational_pain_point: str
    job_titles_to_target: list[str] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)
    county_portal_data_types: list[str] = field(default_factory=list)
    estimated_manual_hours_wasted_weekly: int = 10
    recommended_feed_tier: str = "Production Feed ($250/mo)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "niche_name": self.niche_name,
            "vertical_category": self.vertical_category,
            "target_buyer": self.target_buyer,
            "operational_pain_point": self.operational_pain_point,
            "job_titles_to_target": self.job_titles_to_target,
            "search_queries": self.search_queries,
            "county_portal_data_types": self.county_portal_data_types,
            "estimated_manual_hours_wasted_weekly": self.estimated_manual_hours_wasted_weekly,
            "recommended_feed_tier": self.recommended_feed_tier,
        }


# Authoritative Washington State Baseline Niches (grounded in authentic WA county operations)
WA_BASELINE_NICHES = [
    {
        "niche_name": "Probate Litigation & Estate Administration",
        "vertical_category": "Legal & Estate Settlement",
        "target_buyer": "Probate litigation attorneys, estate administrators, trust liquidators",
        "operational_pain_point": (
            "Paralegals and legal intake staff manually refresh superior court dockets daily "
            "to identify newly filed probate petitions, death certificates, and creditor notices. "
            "Manual searching causes 24-48 hour delays in identifying contested estates."
        ),
        "job_titles_to_target": [
            "Probate Paralegal",
            "Docket Clerk",
            "Court Records Researcher",
            "Legal Intake Specialist",
            "Estate Planning Assistant",
        ],
        "search_queries": [
            '"{county}" "probate attorney" official website phone',
            'top estate planning lawyer "{city}" WA court filings',
            'independent probate law firm "{county}" Washington',
            'estate settlement administrator "{city}" WA',
        ],
        "county_portal_data_types": [
            "Probate Petitions",
            "Letters Testamentary",
            "Creditor Claims",
            "Small Estate Affidavits",
        ],
        "estimated_manual_hours_wasted_weekly": 12,
        "recommended_feed_tier": "Production Feed ($250/mo)",
    },
    {
        "niche_name": "Commercial Construction Subcontractors & Suppliers",
        "vertical_category": "Commercial Construction & Trades",
        "target_buyer": "Commercial HVAC, electrical, plumbing subcontractors, and lumber/concrete suppliers",
        "operational_pain_point": (
            "Estimators and project coordinators check municipal building permit portals weekly "
            "to discover newly approved commercial builds and tenant improvements before general "
            "contractors award subcontracts. Missing a permit notice loses a $50k-$200k bid opportunity."
        ),
        "job_titles_to_target": [
            "Permit Coordinator",
            "Permit Expeditor",
            "Construction Project Coordinator",
            "Subcontract Administrator",
            "Commercial Estimator",
        ],
        "search_queries": [
            'commercial electrical contractor "{city}" WA',
            'commercial HVAC contractor "{county}" Washington',
            'building material supplier "{city}" WA phone address',
            'commercial concrete contractor "{county}" WA',
        ],
        "county_portal_data_types": [
            "Commercial Building Permits",
            "Grading & Site Development Permits",
            "Tenant Improvement Permits",
            "Plan Review Approvals",
        ],
        "estimated_manual_hours_wasted_weekly": 15,
        "recommended_feed_tier": "Production Feed ($250/mo)",
    },
    {
        "niche_name": "Mechanic's Lien Claimants & Material Factoring",
        "vertical_category": "Construction Finance & Material Supply",
        "target_buyer": "Lumber yards, equipment rental firms, roofing suppliers, and construction litigators",
        "operational_pain_point": (
            "Under RCW 60.04 (Washington Mechanic's Lien Statute), material suppliers and contractors "
            "have strict 90-day statutory deadlines to record liens for unpaid work. Credit managers "
            "spend hours searching county auditor records to verify property ownership and prior encumbrances."
        ),
        "job_titles_to_target": [
            "Lien Coordinator",
            "Credit & Collections Specialist",
            "Public Records Specialist",
            "Construction Accounts Receivable Specialist",
        ],
        "search_queries": [
            'building material supplier "{county}" WA',
            'construction litigation attorney "{city}" WA',
            'commercial equipment rental "{city}" Washington',
            'lumber and building supply "{county}" WA official website',
        ],
        "county_portal_data_types": [
            "Mechanic's Liens",
            "Pre-Claim Notices",
            "Notice of Intent to Lien",
            "Lien Satisfaction & Release",
        ],
        "estimated_manual_hours_wasted_weekly": 8,
        "recommended_feed_tier": "Production Feed ($250/mo)",
    },
    {
        "niche_name": "Pre-Foreclosure & Distressed Asset Real Estate",
        "vertical_category": "Real Estate Investment & Acquisitions",
        "target_buyer": "Boutique private equity real estate firms, distressed asset buyers, property renovators",
        "operational_pain_point": (
            "Acquisition analysts manually download county auditor records to find Notice of Trustee Sales "
            "(NOTS) and Lis Pendens filings. Latency means competitors reach homeowners first during statutory "
            "cure periods."
        ),
        "job_titles_to_target": [
            "Acquisitions Analyst",
            "Real Estate Research Specialist",
            "Foreclosure Specialist",
            "Data Entry Specialist - Real Estate",
        ],
        "search_queries": [
            'real estate acquisitions "{county}" WA',
            'distressed property buyers "{city}" Washington',
            'real estate investment firm "{city}" WA official website',
            'commercial property acquisitions "{county}" WA',
        ],
        "county_portal_data_types": [
            "Notice of Trustee Sale (NOTS)",
            "Lis Pendens",
            "Sheriff's Deed",
            "Treasurer Delinquent Tax Foreclosure",
        ],
        "estimated_manual_hours_wasted_weekly": 14,
        "recommended_feed_tier": "Production Feed ($250/mo)",
    },
    {
        "niche_name": "Emergency Restoration & Code Compliance Remediation",
        "vertical_category": "Environmental & Property Restoration",
        "target_buyer": "Water/fire damage restoration companies, mold remediation, structural demolition firms",
        "operational_pain_point": (
            "Business development staff manually inspect municipal code enforcement violations, "
            "red-tag unsafe structure notices, and fire incident logs. Getting automated morning alerts "
            "allows immediate emergency outreach to affected property owners."
        ),
        "job_titles_to_target": [
            "Restoration Project Coordinator",
            "Emergency Response Coordinator",
            "Disaster Recovery Intake Specialist",
        ],
        "search_queries": [
            'water damage restoration "{city}" WA 24/7',
            'fire damage restoration "{county}" Washington',
            'asbestos abatement contractor "{city}" WA',
            'structural remediation services "{county}" WA',
        ],
        "county_portal_data_types": [
            "Unsafe Structure Citations",
            "Code Compliance Violations",
            "Emergency Demolition Orders",
            "Environmental Health Citations",
        ],
        "estimated_manual_hours_wasted_weekly": 10,
        "recommended_feed_tier": "Starter Docket Feed ($150/mo)",
    },
    {
        "niche_name": "Title Abstractors & Escrow Settlement Agencies",
        "vertical_category": "Real Estate Title & Escrow",
        "target_buyer": "Independent regional title companies, escrow closers, real estate abstractors",
        "operational_pain_point": (
            "Title examiners pull deeds of trust, easements, judgments, and covenants manually "
            "from county recording databases for every transaction, costing $35-$50 per manual search."
        ),
        "job_titles_to_target": [
            "Title Examiner",
            "Title Searcher",
            "Title Abstractor",
            "Escrow Assistant",
            "Public Records Specialist",
        ],
        "search_queries": [
            'independent title company "{city}" WA',
            'escrow closing agency "{county}" Washington',
            'title insurance agency "{city}" WA official website',
        ],
        "county_portal_data_types": [
            "Deeds of Trust",
            "Statutory Warranty Deeds",
            "Civil Judgments",
            "Easements & Covenants",
        ],
        "estimated_manual_hours_wasted_weekly": 16,
        "recommended_feed_tier": "Production Feed ($250/mo)",
    },
]


class NicheBrainstormerAgent:
    """Autonomous agent that generates high-intent SMB niches and search parameters."""

    def __init__(self, llm_engine: Optional[LLMAgentEngine] = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def brainstorm_niches_for_jurisdiction(
        self,
        county_name: str = "King County",
        state_code: str = "WA",
        primary_city: str = "Seattle",
        max_niches: int = 5,
    ) -> list[BrainstormedNiche]:
        """Brainstorm specialized niches for a target county using LLM reasoning with baseline fallback."""
        logger.info(f"💡 [NICHE BRAINSTORMER] Generating high-intent niches for {county_name}, {state_code} (City: {primary_city})...")

        llm_niches = self._generate_llm_niches(county_name, state_code, primary_city)
        if llm_niches:
            logger.info(f"✓ [NICHE BRAINSTORMER] LLM synthesized {len(llm_niches)} custom niches for {county_name}")
            return llm_niches[:max_niches]

        # Use curated authentic baseline tailored for this county and city
        logger.info(f"ℹ️ [NICHE BRAINSTORMER] Deploying authenticated Washington baseline niches for {county_name}")
        tailored: list[BrainstormedNiche] = []
        for b in WA_BASELINE_NICHES[:max_niches]:
            # Interpolate county and city into search queries
            custom_queries = [
                q.replace("{county}", county_name).replace("{city}", primary_city or county_name.replace(" County", ""))
                for q in b["search_queries"]
            ]
            tailored.append(BrainstormedNiche(
                niche_name=b["niche_name"],
                vertical_category=b["vertical_category"],
                target_buyer=b["target_buyer"],
                operational_pain_point=b["operational_pain_point"],
                job_titles_to_target=list(b["job_titles_to_target"]),
                search_queries=custom_queries,
                county_portal_data_types=list(b["county_portal_data_types"]),
                estimated_manual_hours_wasted_weekly=b["estimated_manual_hours_wasted_weekly"],
                recommended_feed_tier=b["recommended_feed_tier"],
            ))

        return tailored

    def _generate_llm_niches(
        self,
        county_name: str,
        state_code: str,
        primary_city: str,
    ) -> list[BrainstormedNiche]:
        """Ask LLM to brainstorm fresh, high-intent SMB data consumer niches."""
        if not self.llm_engine.is_available():
            return []

        system_prompt = (
            "You are the LeadOps Swarm Niche Discovery Specialist. "
            "LeadOps sells automated daily public-records data feeds ($150-$250/mo) that pull dockets, permits, "
            "and liens from county auditor and court portals every morning at 8 AM, replacing manual staff data entry. "
            "Your job is to identify specific commercial B2B niches in a given US county that suffer from manual docket pulling. "
            "You must return a valid JSON array of objects with NO markdown and NO extra commentary."
        )

        user_prompt = f"""
Identify 4 highly lucrative SMB niches in {county_name}, {state_code} (primary city: {primary_city})
that rely on daily or weekly public county filings.

For each niche, provide:
- niche_name (e.g. 'Commercial Roofing Permitting & Subcontractors')
- vertical_category (e.g. 'Construction & Permitting')
- target_buyer (who makes the purchase decision)
- operational_pain_point (what they do manually and why it costs them time or deals)
- job_titles_to_target (list of 3-5 job titles they hire for manual data entry or coordination)
- search_queries (list of 3 precise web search strings to find these businesses in {county_name})
- county_portal_data_types (list of 3 filing types they need from the county recorder/court)
- estimated_manual_hours_wasted_weekly (integer 5-20)
- recommended_feed_tier (either 'Starter Docket Feed ($150/mo)' or 'Production Feed ($250/mo)')

Respond ONLY with a JSON array.
"""

        try:
            raw = self.llm_engine.generate_completion(system_prompt, user_prompt, temperature=0.3, max_tokens=1800)
            if not raw:
                return []

            # Clean JSON markdown fences
            clean = re.sub(r"^```json\s*", "", raw.strip())
            clean = re.sub(r"\s*```$", "", clean)
            match = re.search(r"\[\s*\{.*\}\s*\]", clean, re.DOTALL)
            if match:
                clean = match.group(0)

            data = json.loads(clean)
            if not isinstance(data, list):
                return []

            results = []
            for item in data:
                results.append(BrainstormedNiche(
                    niche_name=item.get("niche_name", "Public Records Consumer"),
                    vertical_category=item.get("vertical_category", "Commercial Services"),
                    target_buyer=item.get("target_buyer", "Operations Director"),
                    operational_pain_point=item.get("operational_pain_point", "Manual data entry overhead"),
                    job_titles_to_target=item.get("job_titles_to_target", ["Data Entry Specialist"]),
                    search_queries=item.get("search_queries", [f'"{county_name}" commercial business']),
                    county_portal_data_types=item.get("county_portal_data_types", ["Public Dockets"]),
                    estimated_manual_hours_wasted_weekly=int(item.get("estimated_manual_hours_wasted_weekly", 10)),
                    recommended_feed_tier=item.get("recommended_feed_tier", "Production Feed ($250/mo)"),
                ))
            return results
        except Exception as e:
            logger.debug(f"LLM niche brainstorming parse notice: {e}")
            return []
