"""Autonomous Contact Enricher Researcher Agent for LeadOps.

Investigates leads that failed pre-send deliverability checks (bad email, bounce,
syntax error, disposable domain) or 45-day contact suppression warnings.
Discovers alternative corporate decision-makers (Managing Partners, Founders,
Operations Directors) via live web searches, team page scrapes, and email permutation
heuristics, verifies them using DeliverabilityVerifier SMTP probes, and rehabilitates
valid leads back to active pipeline stages.
"""

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from .domain import Lead, State
from .email.verifier import DeliverabilityVerifier, DeliverabilityStatus
from .llm_client import LLMAgentEngine, is_disallowed_buyer
from .tools.web_search import search_web, search_company_intelligence, find_linkedin_decision_maker
from .tools.web_fetcher import extract_contact_info_from_url
from .tools.email_finder import construct_email_patterns, dork_search_email
from .logging_config import get_logger

logger = get_logger("contact_enricher_agent")


class ContactEnricherResearcherAgent:
    """Autonomous AI Agent that audits, researches, and rescues leads with broken or suppressed contacts."""

    def __init__(
        self,
        llm_engine: LLMAgentEngine | None = None,
        verifier: DeliverabilityVerifier | None = None,
    ):
        self.llm_engine = llm_engine or LLMAgentEngine()
        self.verifier = verifier or DeliverabilityVerifier(
            probe_smtp=not bool(os.environ.get("PYTEST_CURRENT_TEST")),
            probe_web=True,
            timeout_seconds=4.0,
            allow_business_roles=True,
        )

    def extract_domain_from_lead(self, lead: Lead) -> str:
        """Extract clean root domain from lead website or contact email."""
        website = (getattr(lead, "website", "") or "").strip()
        if website:
            parsed = urlparse(website if "://" in website else f"https://{website}")
            netloc = parsed.netloc.lower().replace("www.", "").strip()
            if netloc and "." in netloc:
                return netloc

        email = (getattr(lead, "contact_email", "") or "").strip()
        if "@" in email:
            domain = email.split("@")[-1].lower().strip()
            if domain and "." in domain and domain not in ("example.com", "company.com", "domain.com", "test.com"):
                return domain

        # Fallback to slug domain heuristic
        slug = getattr(lead, "slug", "") or lead.lead_id or ""
        clean_slug = slug.replace("lead-", "").split("-")[0]
        return f"{clean_slug}.com" if clean_slug else ""

    def research_alternative_contacts(
        self,
        company_name: str,
        domain: str,
        website_url: str = "",
    ) -> list[dict[str, str]]:
        """Deep research to discover executive decision makers and corporate emails."""
        candidates: list[dict[str, str]] = []
        seen_emails: set[str] = set()

        # 1. Deep scan official website if available
        target_site = website_url or (f"https://{domain}" if domain else "")
        if target_site and not is_disallowed_buyer(company_name, target_site):
            try:
                scanned_info = extract_contact_info_from_url(target_site)
                # Extracted decision makers with titles
                for dm in scanned_info.get("decision_makers", []):
                    dm_name = dm.get("name", "").strip()
                    dm_role = dm.get("role", "Executive").strip()
                    if dm_name:
                        candidates.append({
                            "name": dm_name,
                            "role": dm_role,
                            "email": "",
                            "source": "website_leadership_page",
                        })

                # Extracted emails from contact pages
                for raw_email in scanned_info.get("all_emails", []):
                    clean_e = raw_email.strip().lower()
                    if clean_e and clean_e not in seen_emails and not any(r in clean_e for r in ["noreply", "privacy", "optout"]):
                        seen_emails.add(clean_e)
                        candidates.append({
                            "name": company_name,
                            "role": "General Inquiries / Operations",
                            "email": clean_e,
                            "source": "website_contact_page",
                        })
            except Exception as scan_err:
                logger.debug(f"Website contact scan note for {target_site}: {scan_err}")

        # 2. LinkedIn Decision-Maker Search
        try:
            li_intel = find_linkedin_decision_maker(company_name=company_name, domain_hint=domain)
            if li_intel and li_intel.get("name"):
                candidates.append({
                    "name": li_intel["name"],
                    "role": li_intel.get("title", "Managing Partner / Founder"),
                    "email": "",
                    "source": "linkedin_profile",
                })
        except Exception as li_err:
            logger.debug(f"LinkedIn discovery note for {company_name}: {li_err}")

        # 3. Google/Bing Search Dork Queries
        if domain:
            try:
                dork_emails = dork_search_email(company_name, domain)
                for de in dork_emails:
                    clean_de = de.strip().lower()
                    if clean_de and clean_de not in seen_emails:
                        seen_emails.add(clean_de)
                        candidates.append({
                            "name": company_name,
                            "role": "Operations / Staff",
                            "email": clean_de,
                            "source": "search_dork",
                        })
            except Exception as dork_err:
                logger.debug(f"Search dork discovery note for {domain}: {dork_err}")

        # 4. Synthesize candidate email patterns for discovered named executives
        final_candidates: list[dict[str, str]] = []
        for c in candidates:
            c_name = c["name"]
            c_email = c["email"]
            if not c_email and domain:
                parts = [p for p in re.split(r"\s+", c_name) if p.isalpha()]
                if len(parts) >= 2:
                    first, last = parts[0], parts[-1]
                    patterns = construct_email_patterns(first, last, domain)
                    for pat in patterns[:4]:  # Top 4 most likely patterns
                        final_candidates.append({
                            "name": c_name,
                            "role": c["role"],
                            "email": pat,
                            "source": f"{c['source']}_pattern_synth",
                        })
                elif len(parts) == 1:
                    final_candidates.append({
                        "name": c_name,
                        "role": c["role"],
                        "email": f"{parts[0].lower()}@{domain}",
                        "source": f"{c['source']}_pattern_synth",
                    })
            elif c_email:
                final_candidates.append(c)

        # Fallback role-based patterns if zero executive emails were found
        if not final_candidates and domain:
            for role_prefix in ["info", "contact", "operations", "admin", "team"]:
                final_candidates.append({
                    "name": company_name,
                    "role": f"{role_prefix.title()} Department",
                    "email": f"{role_prefix}@{domain}",
                    "source": "domain_role_fallback",
                })

        return final_candidates

    def enrich_and_recover_lead(
        self,
        lead: Lead,
        storage_backend: Any = None,
    ) -> dict[str, Any]:
        """Execute autonomous research to rescue and rehabilitate an archived or failing lead."""
        logger.info(f"🔎 [CONTACT ENRICHER AGENT] Starting recovery research for lead '{lead.lead_id}' ({lead.company_name})")

        old_email = (lead.contact_email or "").strip().lower()
        domain = self.extract_domain_from_lead(lead)
        website = getattr(lead, "website", "") or (f"https://{domain}" if domain else "")

        if not domain and not lead.company_name:
            logger.warning(f"❌ [CONTACT ENRICHER AGENT] Lead {lead.lead_id} lacks both company name and domain. Cannot research.")
            return {"ok": False, "recovered": False, "reason": "Missing company name and website domain"}

        # Step 1: Discover candidate alternative contacts
        candidate_pool = self.research_alternative_contacts(
            company_name=lead.company_name,
            domain=domain,
            website_url=website,
        )

        logger.info(f"🔍 [CONTACT ENRICHER AGENT] Discovered {len(candidate_pool)} potential contact candidates for {lead.company_name}")

        # Step 2: Layered deliverability verification on candidate emails
        verified_candidates: list[dict[str, Any]] = []
        for cand in candidate_pool:
            cand_email = (cand.get("email") or "").strip().lower()
            if not cand_email or cand_email == old_email:
                continue

            # Check 45-day anti-duplicate suppression if storage backend is present
            if storage_backend and hasattr(storage_backend, "is_recipient_or_domain_contacted"):
                if storage_backend.is_recipient_or_domain_contacted(
                    email=cand_email,
                    within_days=45,
                    exclude_lead_id=lead.lead_id,
                ):
                    logger.debug(f"Candidate {cand_email} was contacted within 45 days. Skipping.")
                    continue

            # Run pre-send deliverability check
            v_res = self.verifier.verify(cand_email)
            if v_res.is_safe_to_send or v_res.status == DeliverabilityStatus.DELIVERABLE:
                cand_copy = dict(cand)
                cand_copy["verification_reason"] = v_res.reason
                cand_copy["mx_records"] = v_res.mx_records
                verified_candidates.append(cand_copy)
                logger.info(f"✅ [CONTACT ENRICHER AGENT] Verified deliverable candidate: {cand_email} ({cand['name']}, {cand['role']})")
                if len(verified_candidates) >= 3:
                    break

        if not verified_candidates:
            logger.warning(f"⚠️ [CONTACT ENRICHER AGENT] Zero deliverable candidate contacts verified for {lead.company_name}. Lead remains ARCHIVED.")
            lead.research["contact_enricher_recovery"] = {
                "attempted_at": datetime.now(timezone.utc).isoformat(),
                "status": "FAILED_NO_DELIVERABLE_FOUND",
                "attempted_pool_size": len(candidate_pool),
                "domain": domain,
            }
            lead.log_event("CONTACT_ENRICHMENT_FAILED", f"ContactEnricherResearcherAgent scanned {len(candidate_pool)} candidates; none passed deliverability.")
            if storage_backend:
                if hasattr(storage_backend, "save_lead"):
                    storage_backend.save_lead(lead)
                elif hasattr(storage_backend, "update_lead"):
                    storage_backend.update_lead(lead)
            return {
                "ok": True,
                "recovered": False,
                "lead_id": lead.lead_id,
                "reason": "Exhaustive research completed: no active, deliverable mailbox found",
            }

        # Step 3: LLM Reasoning to select the highest-converting authority
        best_candidate = verified_candidates[0]
        if len(verified_candidates) > 1 and self.llm_engine.is_available():
            try:
                system_prompt = (
                    "You are the LeadOps Contact Enricher Researcher Agent. Your objective is to review "
                    "verified candidate contacts for a commercial B2B sales prospect and select the decision maker "
                    "with the highest authority to approve automated data feeds (e.g. Managing Partner, Founder, "
                    "President, Chief Operations Officer).\n\n"
                    "Respond with a JSON object: {\"selected_index\": 0, \"reasoning\": \"brief explanation\"}"
                )
                user_prompt = (
                    f"Company: {lead.company_name}\n"
                    f"Niche: {lead.niche}\n"
                    f"Previous Broken/Suppressed Email: {old_email}\n\n"
                    f"Verified Candidates:\n"
                    + json.dumps(verified_candidates, indent=2)
                )
                llm_resp = self.llm_engine.generate_completion(system_prompt, user_prompt, temperature=0.1)
                match = re.search(r"\{.*\}", llm_resp, re.DOTALL)
                if match:
                    parsed = json.loads(match.group(0))
                    idx = int(parsed.get("selected_index", 0))
                    if 0 <= idx < len(verified_candidates):
                        best_candidate = verified_candidates[idx]
                        best_candidate["llm_reasoning"] = parsed.get("reasoning", "")
            except Exception as llm_err:
                logger.debug(f"LLM selection fallback: {llm_err}")

        # Step 4: Rehabilitate lead with verified contact
        new_email = best_candidate["email"]
        new_name = best_candidate["name"]
        new_role = best_candidate["role"]

        lead.contact_email = new_email
        lead.contact_name = new_name
        lead.contact_role = new_role

        # Regenerate personalized outreach subject & body for the new decision maker
        first_name = new_name.split()[0] if new_name else "there"
        portal_name = getattr(lead, "target_portal_name", "") or getattr(lead, "jurisdiction", "County Portal") or "County Portal"
        clean_company = re.sub(r"(?i)\s+(inc\.?|llc|corp\.?|ltd\.?|co\.?|pllc)$", "", lead.company_name).strip() or lead.company_name
        from .pitcher import render_sub_60_word_pitch
        pitch = render_sub_60_word_pitch(
            company_name=clean_company,
            niche=getattr(lead, "niche", "Public Records") or "Public Records",
            portal_name=portal_name,
            sample_count=getattr(lead, "preview_rows", 10) or 10,
            slug=lead.slug,
            contact_name=first_name,
            contact_role=new_role or getattr(lead, "contact_role", "Operations"),
            llm_engine=self.llm_engine,
        )
        lead.outreach_subject = pitch.subject
        lead.outreach_body = pitch.body_text
        lead.outreach_html = pitch.body_html

        lead.research["contact_enricher_recovery"] = {
            "recovered_at": datetime.now(timezone.utc).isoformat(),
            "previous_email": old_email,
            "new_email": new_email,
            "new_name": new_name,
            "new_role": new_role,
            "source": best_candidate.get("source", "contact_enricher_agent"),
            "llm_reasoning": best_candidate.get("llm_reasoning", "Verified deliverable mailbox"),
        }

        lead.log_event(
            "CONTACT_RECOVERED",
            f"ContactEnricherResearcherAgent recovered verified deliverable contact: {new_email} ({new_name}, {new_role})",
        )

        # Transition lead back to active pipeline
        if lead.state == State.ARCHIVED:
            lead.transition(State.REVIEW, "Contact email rehabilitated by ContactEnricherResearcherAgent")

        if storage_backend:
            if hasattr(storage_backend, "save_lead"):
                storage_backend.save_lead(lead)
            elif hasattr(storage_backend, "update_lead"):
                storage_backend.update_lead(lead)

        logger.info(
            f"🎉 [CONTACT ENRICHER AGENT] Successfully rehabilitated lead '{lead.lead_id}'! "
            f"Updated contact: {new_email} ({new_name}) -> State: {lead.state.value}"
        )

        # Trigger autonomous copywriter & auto-outreach scheduling for the rehabilitated lead in background
        if storage_backend:
            try:
                import threading
                from .auto_outreach import auto_outreach_scheduler
                threading.Thread(
                    target=auto_outreach_scheduler.auto_prepare_review_pitches,
                    args=(storage_backend, None, self.llm_engine),
                    daemon=True,
                    name="contact-enricher-auto-pitch",
                ).start()
            except Exception as auto_err:
                logger.debug(f"Auto-outreach dispatch trigger note for rehabilitated lead: {auto_err}")

        return {
            "ok": True,
            "recovered": True,
            "lead_id": lead.lead_id,
            "company_name": lead.company_name,
            "new_email": new_email,
            "new_name": new_name,
            "new_role": new_role,
            "new_state": lead.state.value,
            "source": best_candidate.get("source", ""),
            "message": f"Successfully rehabilitated {lead.company_name} with verified contact {new_email}.",
        }
