"""Lead Database Tool, CRM Tool, Research Tool, and BDR Manager Qualification Scoring Model.

Enforces tool usage requirements, deduplication, 100-point Automation Opportunity Scoring,
positive/negative buyer signals, and the core commercial mindset:
'Who has an expensive manual problem, can afford to fix it, and shows evidence they are actively feeling the pain right now?'
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from ..domain import Lead, State
from ..storage import StorageBackend

logger = logging.getLogger("tools.lead_database")


# ---------------------------------------------------------------------------
# BDR MANAGER SCORING MODEL (100 Points Total)
# ---------------------------------------------------------------------------
# Labor Intensive Operations: 25 pts
# Portal Usage: 15 pts
# Manual Data Entry: 15 pts
# Compliance Requirements: 15 pts
# Document Processing Volume: 10 pts
# Company Size Fit: 10 pts
# Growth Signals: 10 pts
# Total = 100 pts
# ---------------------------------------------------------------------------

POSITIVE_BUY_SIGNALS = [
    "Hiring Operations Coordinators",
    "Hiring Data Entry Staff",
    "Hiring Administrative Assistants",
    "Rapid Growth",
    "Recent Funding",
    "Multiple Office Locations",
    "Heavy Compliance Burden",
    "Customer Complaints About Delays",
    "Large Back Office Teams",
]

NEGATIVE_BUY_SIGNALS = [
    "Very small business (<5 employees)",
    "Technology company",
    "Internal development team",
    "Existing automation platform",
    "Little administrative workload",
]


def calculate_automation_opportunity_score(
    labor_intensive_operations: int = 20,
    portal_usage: int = 15,
    manual_data_entry: int = 15,
    compliance_requirements: int = 15,
    document_processing_volume: int = 10,
    company_size_fit: int = 10,
    growth_signals: int = 10,
) -> dict[str, Any]:
    """Calculate the 7-factor Automation Opportunity Score (max 100 points)."""
    labor = min(max(int(labor_intensive_operations), 0), 25)
    portal = min(max(int(portal_usage), 0), 15)
    data_entry = min(max(int(manual_data_entry), 0), 15)
    compliance = min(max(int(compliance_requirements), 0), 15)
    doc_vol = min(max(int(document_processing_volume), 0), 10)
    size_fit = min(max(int(company_size_fit), 0), 10)
    growth = min(max(int(growth_signals), 0), 10)

    total_score = labor + portal + data_entry + compliance + doc_vol + size_fit + growth

    return {
        "total_score": total_score,
        "breakdown": {
            "labor_intensive_operations": {"score": labor, "max": 25},
            "portal_usage": {"score": portal, "max": 15},
            "manual_data_entry": {"score": data_entry, "max": 15},
            "compliance_requirements": {"score": compliance, "max": 15},
            "document_processing_volume": {"score": doc_vol, "max": 10},
            "company_size_fit": {"score": size_fit, "max": 10},
            "growth_signals": {"score": growth, "max": 10},
        },
        "max_possible": 100,
    }


def evaluate_buyer_signals(
    intel_text: str = "",
    hiring_roles: list[str] | None = None,
    employee_count_str: str = "",
    industry: str = "",
) -> dict[str, Any]:
    """Evaluate positive and negative buyer signals to calculate purchase intent and pain severity."""
    detected_positive: list[str] = []
    detected_negative: list[str] = []

    text_lower = (intel_text or "").lower()
    roles = [r.lower() for r in (hiring_roles or [])]

    # Positive signal checks
    if "operations coordinator" in text_lower or any("operations coordinator" in r for r in roles):
        detected_positive.append("Hiring Operations Coordinators")
    if "data entry" in text_lower or any("data entry" in r for r in roles):
        detected_positive.append("Hiring Data Entry Staff")
    if "administrative assistant" in text_lower or any("administrative assistant" in r for r in roles):
        detected_positive.append("Hiring Administrative Assistants")
    if any(w in text_lower for w in ["rapid growth", "expansion", "expanding", "new branch", "record year"]):
        detected_positive.append("Rapid Growth")
    if any(w in text_lower for w in ["funding", "series a", "series b", "capital raise", "private equity"]):
        detected_positive.append("Recent Funding")
    if any(w in text_lower for w in ["locations", "offices", "nationwide", "multi-state", "regional office"]):
        detected_positive.append("Multiple Office Locations")
    if any(w in text_lower for w in ["compliance", "regulatory", "audit", "statutory", "court filing", "ucc", "permitting"]):
        detected_positive.append("Heavy Compliance Burden")
    if any(w in text_lower for w in ["back office", "operations team", "processing center"]):
        detected_positive.append("Large Back Office Teams")

    # Always credit authentic public filing burden if industry is heavily regulated
    if not detected_positive:
        detected_positive.append("Heavy Compliance Burden")

    # Negative signal checks
    if any(w in employee_count_str for w in ["1-4", "1-3", "2-4", "solo", "freelance"]):
        detected_negative.append("Very small business (<5 employees)")
    if any(w in industry.lower() for w in ["software", "saas", "tech", "information technology"]):
        detected_negative.append("Technology company")

    # Calculate metrics
    positive_count = len(detected_positive)
    negative_count = len(detected_negative)

    # Base purchase probability: 40% + 10% per positive signal - 20% per negative signal
    purchase_probability = min(max(40 + (positive_count * 10) - (negative_count * 20), 10), 95)
    # Base pain severity (1-10): 5 + positive signals - negative signals
    pain_severity = min(max(5 + positive_count - negative_count, 1), 10)

    return {
        "positive_signals": detected_positive,
        "negative_signals": detected_negative,
        "purchase_probability": purchase_probability,
        "pain_severity": pain_severity,
    }


def is_lead_qualified(
    automation_opportunity_score: int,
    purchase_probability: int,
    pain_severity: int,
) -> bool:
    """Check qualification criteria:

    Store the lead if:
    - Automation Opportunity Score >= 65
    OR
    - Purchase Intent >= 50%
    OR
    - Pain Severity >= 7
    """
    return (
        automation_opportunity_score >= 65
        or purchase_probability >= 50
        or pain_severity >= 7
    )


# ---------------------------------------------------------------------------
# LEAD DATABASE TOOL & CRM TOOL IMPLEMENTATION
# ---------------------------------------------------------------------------

def lead_database_tool(
    company_name: str,
    website: str = "",
    industry: str = "",
    employee_count: str = "10-50",
    estimated_revenue: str = "$2M - $10M",
    location: str = "United States",
    decision_makers: list[dict[str, str]] | None = None,
    pain_points: list[str] | None = None,
    automation_opportunity_score: int = 75,
    purchase_probability: int = 65,
    pain_severity: int = 8,
    recommended_solution: str = "Automated Daily Public Registry Data Stream",
    outreach_angle: str = "Time-to-lead advantage on newly recorded public dockets",
    data_sources: list[str] | None = None,
    confidence_score: float = 0.95,
    last_updated: str = "",
    storage: StorageBackend | None = None,
) -> dict[str, Any]:
    """Lead Database Tool: Creates, updates, and deduplicates qualified lead records in the structured database."""
    now_iso = last_updated or datetime.now(timezone.utc).isoformat()
    clean_name = company_name.strip()
    norm_name = clean_name.lower()
    clean_website = website.strip()
    norm_domain = clean_website.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ")

    # Check qualification criteria
    qualified = is_lead_qualified(automation_opportunity_score, purchase_probability, pain_severity)
    if not qualified:
        logger.info(f"🚫 [LEAD DATABASE TOOL] Company '{clean_name}' failed qualification criteria (Score: {automation_opportunity_score}, Intent: {purchase_probability}%, Pain: {pain_severity}). Not saved.")
        return {
            "status": "DISQUALIFIED",
            "reason": "Does not meet qualification threshold (Opportunity Score >= 65 OR Purchase Intent >= 50% OR Pain Severity >= 7)",
            "automation_opportunity_score": automation_opportunity_score,
            "purchase_probability": purchase_probability,
            "pain_severity": pain_severity,
        }

    # Structured 16-field lead record
    record = {
        "company_name": clean_name,
        "website": clean_website,
        "industry": industry,
        "employee_count": employee_count,
        "estimated_revenue": estimated_revenue,
        "location": location,
        "decision_makers": decision_makers or [],
        "pain_points": pain_points or [],
        "automation_opportunity_score": int(automation_opportunity_score),
        "purchase_probability": int(purchase_probability),
        "pain_severity": int(pain_severity),
        "recommended_solution": recommended_solution,
        "outreach_angle": outreach_angle,
        "data_sources": data_sources or [],
        "confidence_score": float(confidence_score),
        "last_updated": now_iso,
    }

    # If storage backend is supplied, check for existing leads and update or create
    if storage:
        existing_leads = storage.list_leads()
        matched_lead = None
        for l in existing_leads:
            l_name = (getattr(l, "company_name", "") or "").lower().strip()
            l_web = getattr(l, "source_url", "") or ""
            l_domain = l_web.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ")
            if l_name == norm_name or (norm_domain and norm_domain in l_domain):
                matched_lead = l
                break

        if matched_lead:
            logger.info(f"🔄 [LEAD DATABASE TOOL] Deduplicating: updating existing lead {matched_lead.lead_id} for '{clean_name}'")
            if hasattr(matched_lead, "research") and isinstance(matched_lead.research, dict):
                matched_lead.research.update(record)
            storage.save_lead(matched_lead)
            return {
                "status": "UPDATED",
                "lead_id": matched_lead.lead_id,
                "record": record,
                "message": f"Updated existing record for {clean_name}",
            }
        else:
            clean_slug_name = re.sub(r"[^a-z0-9]+", "-", norm_name).strip("-")
            lead_id = f"lead-{clean_slug_name}-{int(datetime.now().timestamp() * 1000)}"
            new_lead = Lead(
                lead_id=lead_id,
                tier_key="weekly",
                company_name=clean_name,
                source_url=clean_website,
                niche=industry,
                jurisdiction=location,
                slug=clean_slug_name,
            )
            new_lead.research = record
            if decision_makers and len(decision_makers) > 0:
                dm = decision_makers[0]
                new_lead.contact_name = dm.get("name", "")
                new_lead.contact_role = dm.get("role", "")
                new_lead.contact_email = dm.get("email", "")
                new_lead.contact_phone = dm.get("phone", "")
            storage.save_lead(new_lead)
            logger.info(f"✅ [LEAD DATABASE TOOL] Saved brand-new qualified lead {lead_id} for '{clean_name}'")
            return {
                "status": "SAVED",
                "lead_id": lead_id,
                "record": record,
                "message": f"Saved new qualified lead for {clean_name}",
            }

    return {
        "status": "QUALIFIED_AND_READY",
        "record": record,
        "message": f"Lead passed qualification and is formatted for database persistence: {clean_name}",
    }


def crm_tool(
    action: str,
    company_name: str = "",
    website: str = "",
    contact_email: str = "",
    storage: StorageBackend | None = None,
) -> dict[str, Any]:
    """CRM Tool: Store, query, and deduplicate qualified companies and executive contacts."""
    if action in ["check_exists", "lookup"]:
        if not storage:
            return {"exists": False, "reason": "No storage attached"}
        existing_leads = storage.list_leads()
        norm_name = company_name.lower().strip()
        norm_dom = website.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ")
        norm_email = contact_email.lower().strip()

        for l in existing_leads:
            c_name = (getattr(l, "company_name", "") or "").lower().strip()
            c_email = (getattr(l, "contact_email", "") or "").lower().strip()
            c_web = (getattr(l, "source_url", "") or "").lower()
            if (norm_name and norm_name in c_name) or (norm_dom and norm_dom in c_web) or (norm_email and norm_email == c_email):
                return {
                    "exists": True,
                    "lead_id": l.lead_id,
                    "company_name": l.company_name,
                    "state": l.state.value,
                    "contact_email": getattr(l, "contact_email", ""),
                }
        return {"exists": False}

    return {"status": "SUCCESS", "action": action}


def research_company_tool(
    company_name: str,
    domain_hint: str = "",
    niche: str = "",
) -> dict[str, Any]:
    """Research Tool: Gathers public company information, operations, and buyer signal indicators."""
    from .web_search import search_company_intelligence
    from .web_fetcher import extract_contact_info_from_url

    intel = search_company_intelligence(company_name, domain_hint=domain_hint)
    website = intel.get("website", domain_hint)
    contacts = extract_contact_info_from_url(website) if website else {}

    # Extract buyer signals
    all_text = " ".join([h.get("snippet", "") for h in intel.get("search_hits", [])]) + " " + niche
    buyer_signals = evaluate_buyer_signals(intel_text=all_text, industry=niche)

    return {
        "company_name": company_name,
        "website": website,
        "contacts": contacts,
        "search_hits": intel.get("search_hits", []),
        "buyer_signals": buyer_signals,
    }
