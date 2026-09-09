"""County Filing Party Extractor Engine for LeadOps Scout.

Turns every public records scrape into a high-ROI B2B discovery opportunity.
Extracts filing attorneys, law firms, title agencies, escrow officers, and secured lenders
directly from docket records already scraped by the system, turning filing parties into
qualified prospects with built-in contextual proof of need.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .llm_client import LLMAgentEngine, is_disallowed_buyer
from .tools.web_search import search_company_intelligence, find_linkedin_decision_maker, search_web
from .tools.web_fetcher import extract_contact_info_from_url
from .logging_config import get_logger

logger = get_logger("county_filing_extractor")

# Common docket field aliases across county and state portals
ATTORNEY_FIELDS = [
    "attorney_name", "attorney", "counsel", "lawyer", "atty_name", "atty",
    "attorney_of_record", "counsel_for_petitioner", "filing_attorney"
]
LAW_FIRM_FIELDS = [
    "law_firm", "firm_name", "firm", "attorney_firm", "legal_counsel",
    "counsel_firm", "representing_firm"
]
FILING_PARTY_FIELDS = [
    "filing_party", "petitioner", "applicant", "claimant", "secured_party",
    "grantor", "grantee", "plaintiff", "contractor_name", "business_name",
    "legal_name", "company_name", "title_company", "escrow_company"
]
CASE_NUMBER_FIELDS = [
    "case_number", "docket_number", "record_id", "permit_number", "license_number",
    "filing_number", "instrument_number", "document_number", "id"
]
DATE_FIELDS = [
    "filing_date", "issue_date", "created_date", "date_issued", "date",
    "current_license_valid_from", "valid_from_date"
]


@dataclass
class DiscoveredFilingEntity:
    """A commercial entity discovered as a filing party on a public court or county docket."""
    entity_name: str
    attorney_name: str = ""
    entity_type: str = "law_firm"  # law_firm, title_company, equipment_lender, contractor
    filing_case_number: str = ""
    filing_date: str = ""
    matter_description: str = ""
    portal_name: str = ""
    jurisdiction: str = ""
    source_record_url: str = ""
    filing_frequency: int = 1
    raw_record: dict[str, Any] = field(default_factory=dict)


class CountyFilingPartyExtractor:
    """Autonomous engine that extracts commercial prospects from scraped public records."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm_engine = llm_engine or LLMAgentEngine()

    def extract_candidates_from_records(
        self,
        records: list[dict[str, Any]],
        portal_name: str = "County Public Records",
        jurisdiction: str = "Regional Jurisdiction",
        source_url: str = "",
    ) -> list[DiscoveredFilingEntity]:
        """Inspect scraped records and extract commercial entities filing petitions, liens, or permits."""
        if not records:
            return []

        candidates: list[DiscoveredFilingEntity] = []
        seen_names: dict[str, DiscoveredFilingEntity] = {}

        for rec in records:
            # 1. Look for explicit structured fields
            found_attorney = ""
            for af in ATTORNEY_FIELDS:
                val = str(rec.get(af, "")).strip()
                if val and val.lower() not in ["none", "n/a", "unknown", "pro se", "self-represented"]:
                    found_attorney = val
                    break

            found_firm = ""
            for lf in LAW_FIRM_FIELDS:
                val = str(rec.get(lf, "")).strip()
                if val and val.lower() not in ["none", "n/a", "unknown"]:
                    found_firm = val
                    break

            found_party = ""
            for pf in FILING_PARTY_FIELDS:
                val = str(rec.get(pf, "")).strip()
                if val and val.lower() not in ["none", "n/a", "unknown"]:
                    found_party = val
                    break

            # 2. Extract docket case number and filing date
            case_no = ""
            for cf in CASE_NUMBER_FIELDS:
                val = str(rec.get(cf, "")).strip()
                if val:
                    case_no = val
                    break

            filing_date = ""
            for df in DATE_FIELDS:
                val = str(rec.get(df, "")).strip()
                if val:
                    filing_date = val[:10]
                    break

            # Matter description or work details
            matter_desc = (
                str(rec.get("work_description") or rec.get("details") or rec.get("title") or rec.get("category") or "")
            ).strip()

            # 3. Determine candidate business name
            candidate_name = found_firm or found_party or (found_attorney if "law" in found_attorney.lower() or "llc" in found_attorney.lower() else "")
            entity_type = "law_firm"

            if not candidate_name and found_attorney:
                # If only individual attorney name is present, pair with Law Practice
                candidate_name = f"{found_attorney} Legal Practice"

            # Fallback: Parse unstructured text in details or title if no explicit field matched
            if not candidate_name and matter_desc:
                candidate_name, found_attorney, entity_type = self._parse_unstructured_filing_party(matter_desc)

            if not candidate_name:
                continue

            # Clean name
            candidate_name = self._sanitize_entity_name(candidate_name)
            if not candidate_name or len(candidate_name) < 3:
                continue

            # STRICT GATE: Filter out government bodies, courts, municipalities
            if is_disallowed_buyer(candidate_name, "", ""):
                continue

            # Classify entity type
            norm_c = candidate_name.lower()
            if any(w in norm_c for w in ["title", "abstract", "escrow", "settlement"]):
                entity_type = "title_company"
            elif any(w in norm_c for w in ["capital", "lending", "credit", "finance", "equipment"]):
                entity_type = "equipment_lender"
            elif any(w in norm_c for w in ["builder", "construction", "contracting", "roofing", "electric"]):
                entity_type = "contractor"
            else:
                entity_type = "law_firm"

            norm_key = candidate_name.lower()
            if norm_key in seen_names:
                seen_names[norm_key].filing_frequency += 1
                continue

            discovered = DiscoveredFilingEntity(
                entity_name=candidate_name,
                attorney_name=found_attorney,
                entity_type=entity_type,
                filing_case_number=case_no,
                filing_date=filing_date,
                matter_description=matter_desc[:120],
                portal_name=portal_name,
                jurisdiction=jurisdiction,
                source_record_url=rec.get("source_url") or source_url,
                raw_record=rec,
            )
            seen_names[norm_key] = discovered
            candidates.append(discovered)

        # Sort by filing frequency (highest active filers first)
        candidates.sort(key=lambda c: c.filing_frequency, reverse=True)
        logger.info(f"🏛️ [COUNTY FILING EXTRACTOR] Discovered {len(candidates)} commercial filing entities from {len(records)} records")
        return candidates

    def _parse_unstructured_filing_party(self, text: str) -> tuple[str, str, str]:
        """Extract filing parties from unstructured docket descriptions via regex."""
        # Pattern 1: Attorney / Counsel: Name [Law Firm]
        m = re.search(r"(?:attorney|counsel|atty|rep by|filed by)[:\s]+([A-Z][a-zA-Z\s,\.\-&]+?)(?:;|\.|\n|$|\()", text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            if len(raw) > 3 and not is_disallowed_buyer(raw, "", ""):
                return raw, raw, "law_firm"

        # Pattern 2: Company LLC / PC / PLLC / Inc
        m_corp = re.search(r"\b([A-Z][a-zA-Z0-9\s&]+?\b(?:LLC|P\.?C\.?|PLLC|Inc\.?|Corp\.?|Law Firm|Law Offices|Title Co|Abstract))\b", text)
        if m_corp:
            raw_corp = m_corp.group(1).strip()
            if len(raw_corp) > 4 and not is_disallowed_buyer(raw_corp, "", ""):
                return raw_corp, "", "law_firm"

        return "", "", "law_firm"

    def _sanitize_entity_name(self, name: str) -> str:
        """Strip docket prefix noise and formatting artifacts."""
        clean = re.sub(r"(?i)^(in re|matter of|estate of|state of|city of|vs\.?|v\.)\s+", "", name).strip()
        clean = re.sub(r"(?i)\s*(petitioner|applicant|claimant|attorney of record|plaintiff|secured party)\b.*$", "", clean).strip()
        clean = re.sub(r"\s+", " ", clean).strip(" ,.-")
        return clean

    def enrich_filing_prospect(
        self,
        entity: DiscoveredFilingEntity,
        existing_companies: set[str] | None = None,
    ) -> dict[str, Any] | None:
        """Enrich a discovered filing entity with corporate domain, verified contacts, and contextual proof pitch."""
        existing = existing_companies or set()
        if entity.entity_name.lower() in existing:
            return None

        logger.info(f"🔎 [ENRICHING FILING PROSPECT] {entity.entity_name} ({entity.entity_type}) | Case: {entity.filing_case_number}")

        # 1. Search for official corporate domain
        intel = search_company_intelligence(entity.entity_name)
        website = intel.get("website", "")
        if not website or "http" not in website:
            raw_hits = search_web(f'"{entity.entity_name}" official website {entity.jurisdiction}', max_results=3)
            for h in raw_hits:
                url = h.get("url", "")
                if not is_disallowed_buyer(h.get("title", ""), url, ""):
                    website = url
                    break

        if not website:
            logger.warning(f"❌ [COUNTY EXTRACTOR] Could not find corporate website for '{entity.entity_name}'")
            return None

        # 2. Extract verified corporate contact emails and phone numbers
        contact_info = extract_contact_info_from_url(website)
        raw_emails = contact_info.get("emails", [])
        verified_email = contact_info.get("verified_email") or (raw_emails[0] if raw_emails else "")
        verified_phone = contact_info.get("verified_phone") or (contact_info.get("phones")[0] if contact_info.get("phones") else "")

        # 3. Locate managing attorney or executive decision maker on LinkedIn
        linkedin_contact = None
        if entity.attorney_name and len(entity.attorney_name.split()) >= 2:
            contact_name = entity.attorney_name
            contact_role = "Attorney of Record / Managing Partner"
            linkedin_contact = find_linkedin_decision_maker(entity.attorney_name, domain_hint=website)
        else:
            linkedin_contact = find_linkedin_decision_maker(entity.entity_name, domain_hint=website)
            contact_name = (linkedin_contact and linkedin_contact.get("name")) or "Managing Partner / Operations Director"
            contact_role = (linkedin_contact and linkedin_contact.get("role")) or "Managing Partner"

        linkedin_url = (linkedin_contact and linkedin_contact.get("linkedin_url")) or ""

        # 4. Generate Proof-First Outreach Pitch
        proof_hook = self._generate_proof_hook(entity)

        return {
            "company_name": entity.entity_name,
            "contact_name": contact_name,
            "contact_role": contact_role,
            "contact_email": verified_email,
            "contact_phone": verified_phone,
            "linkedin_url": linkedin_url,
            "website": website,
            "discovery_channel": "COUNTY_FILING_PARTY",
            "niche": f"Legal & Court Docket Administration ({entity.entity_type.replace('_', ' ').title()})",
            "pain_point": f"Manual monitoring and daily docket extraction from {entity.portal_name}.",
            "target_url": entity.source_record_url,
            "portal_name": entity.portal_name,
            "jurisdiction": entity.jurisdiction,
            "filing_case_number": entity.filing_case_number,
            "filing_date": entity.filing_date,
            "matter_description": entity.matter_description,
            "proof_hook": proof_hook,
            "suggested_fields": list(entity.raw_record.keys()) if entity.raw_record else ["case_number", "filing_date", "matter", "status"],
            "tier_key": "daily",
            "pitch_subject": proof_hook["subject"],
            "pitch_body": proof_hook["body"],
        }

    def _generate_proof_hook(self, entity: DiscoveredFilingEntity) -> dict[str, str]:
        """Craft an irresistible, sub-50-word curiosity outreach hook referencing their exact docket filing."""
        case_ref = f"matter #{entity.filing_case_number}" if entity.filing_case_number else "recent dockets"
        court_ref = entity.portal_name or "county public records"

        subject = f"{entity.portal_name.split()[0].lower()} filings for {entity.entity_name.split()[0]}"
        
        body = (
            f"Hi {entity.attorney_name or 'Team'},\n\n"
            f"Saw your firm filed {case_ref} in {court_ref}.\n\n"
            f"Curious — does your staff still pull new daily dockets and recordings manually? "
            f"We built an automated feed that monitors and extracts newly posted filings every morning at 8 AM.\n\n"
            f"Built a live interactive preview for your team here:\n"
            f"{{sandbox_url}}\n\n"
            f"Worth a quick look?\n"
            f"Alex | LeadOps Automation Engineering"
        )

        return {
            "subject": subject,
            "body": body,
            "case_ref": case_ref,
            "court_ref": court_ref,
        }
