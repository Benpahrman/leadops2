"""Autonomous B2B Web Scout worker: finds commercial businesses and municipal portals via web search."""

import os
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Any

from agents.domain import State
from agents.portal import PortalService
from agents.storage import StorageBackend
from agents.llm import LLMAgentEngine, is_disallowed_buyer
from agents.swarm.datasets import AUTHENTIC_REGISTRY_DATASETS
from agents.scout.scout_pipeline import ScoutPortalPipeline

logger = logging.getLogger("leadops.scout.web")


@dataclass
class B2BWebScoutWorker:
    """Autonomous B2B Web Scout: Brainstorms niches, searches DuckDuckGo for matching firms/portals, fetches, enriches, and creates sandboxes."""

    storage: StorageBackend
    portal: PortalService
    llm_engine: LLMAgentEngine = field(default_factory=LLMAgentEngine)

    def discover_next_candidate(
        self,
        custom_niche: str | None = None,
        run_until_found: bool = True,
        max_attempts: int = 12,
    ) -> dict[str, Any]:
        """Runs the multi-step web search lead discovery and ingestion pipeline, looping until a new lead is found."""
        from agents.tools.web_search import search_web
        from agents.tools.web_fetcher import extract_contact_info_from_url, extract_portal_sample_data

        # Step 1: Brainstorm niche/queries
        logger.info("🧠 [WEB SCOUT] Starting B2B Web search discovery...")
        brainstorm = self.llm_engine.run_web_scout_brainstorm_agent(custom_keyword=custom_niche)
        niche = brainstorm.get("niche", custom_niche or "B2B Lead Operations Services")
        company_query = brainstorm.get("company_search_query") or (f"top {custom_niche} companies" if custom_niche else "commercial title companies Texas")
        portal_query = brainstorm.get("portal_search_query") or (f"{custom_niche} public records portal" if custom_niche else "Texas public records portal")
        jurisdiction = brainstorm.get("jurisdiction", "Nationwide")

        logger.info(f"🧠 [WEB SCOUT] Niche: '{niche}' | Company Search: '{company_query}' | Portal Search: '{portal_query}'")

        # Step 2: Search for real commercial companies (filter out .gov, municipal, court domains)
        raw_company_hits = search_web(company_query, max_results=10)
        company_hits = [h for h in raw_company_hits if not is_disallowed_buyer(h.get("title", ""), h.get("url", ""), "")]
        if not company_hits and not run_until_found:
            logger.warning("❌ [WEB SCOUT] No private commercial B2B companies found matching search query.")
            return {"ok": False, "reason": "No private commercial companies found matching search query."}

        # Step 3: Search for relevant portals
        portal_hits = search_web(portal_query, max_results=4)
        top_portal = portal_hits[0] if portal_hits else {"title": f"{niche} Public Registry Portal", "url": "https://data.gov"}
        portal_url = top_portal.get("url", "")
        live_records_data = {"records": [], "fields": []}
        if portal_url and "google.com" not in portal_url and "duckduckgo.com" not in portal_url:
            try:
                live_records_data = extract_portal_sample_data(portal_url, max_records=25)
            except Exception as e:
                logger.warning(f"⚠️ [WEB SCOUT] Portal sample data extraction failed: {e}")

        # Build list of query batches if run_until_found is active
        query_batches = [(company_query, company_hits)]
        if run_until_found and custom_niche:
            clean_kw = custom_niche.strip()
            variations = [
                f"commercial {clean_kw} businesses",
                f"top {clean_kw} contractors and firms",
                f"{clean_kw} operators",
                f"{clean_kw} companies official",
            ]
            for v in variations:
                if v != company_query and len(query_batches) < max_attempts:
                    query_batches.append((v, None))

        existing_leads = self.storage.list_leads() if self.storage else []
        existing_companies = {
            (getattr(l, "company_name", "") or "").lower().strip()
            for l in existing_leads
        }
        existing_domains = {
            getattr(l, "website", "").lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ").split("/")[0]
            for l in existing_leads
            if getattr(l, "website", "")
        }

        last_rejection_reason = "No private commercial companies found matching search query."

        # Step 4: Iterate through candidates and query variations until a new qualified lead is created
        for q, preloaded_hits in query_batches:
            if preloaded_hits is not None:
                current_hits = preloaded_hits
            else:
                raw_hits = search_web(q, max_results=10)
                current_hits = [h for h in raw_hits if not is_disallowed_buyer(h.get("title", ""), h.get("url", ""), "")]

            if not current_hits:
                continue

            for top_company in current_hits:
                cand_title = top_company.get("title", "")
                company_domain = top_company.get("url", "")
                norm_cand_title = cand_title.lower().strip()
                parsed_host = company_domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/ ").split("/")[0]

                # Deduplication check against existing companies
                if norm_cand_title in existing_companies or any(c in norm_cand_title for c in existing_companies if len(c) > 4):
                    logger.info(f"⏭️ [WEB SCOUT DEDUP] Skipping duplicate company: {cand_title}")
                    last_rejection_reason = f"Company '{cand_title}' already exists in pipeline."
                    if not run_until_found:
                        return {"ok": False, "status": "DUPLICATE_COMPANY", "reason": last_rejection_reason}
                    continue

                if parsed_host and parsed_host in existing_domains:
                    logger.info(f"⏭️ [WEB SCOUT DEDUP] Skipping duplicate domain: {parsed_host}")
                    last_rejection_reason = f"Domain '{parsed_host}' already exists in pipeline."
                    if not run_until_found:
                        return {"ok": False, "status": "DUPLICATE_COMPANY", "reason": last_rejection_reason}
                    continue

                # Crawl contact info
                contact_info = {}
                if company_domain:
                    try:
                        contact_info = extract_contact_info_from_url(company_domain)
                    except Exception as e:
                        logger.warning(f"⚠️ [WEB SCOUT] Contact crawl failed for {company_domain}: {e}")

                # Dossier synthesis
                dossier = self.llm_engine.run_web_scout_dossier_agent(
                    niche=niche,
                    company_hits=[top_company] + [h for h in company_hits if h != top_company],
                    portal_hits=portal_hits,
                    contact_info=contact_info,
                    live_records=live_records_data.get("records") or []
                )

                company_name = dossier.get("company_name") or top_company.get("title", "Lone Star Commercial Capital")
                contact_name = dossier.get("contact_name") or "Operations Director"
                contact_role = dossier.get("contact_role") or "Director of Operations"
                website = dossier.get("website") or contact_info.get("website") or company_domain
                from agents.tools.email_finder import is_directory_or_portal
                if is_directory_or_portal(website):
                    logger.warning(f"⚠️ [WEB SCOUT] Candidate website '{website}' is an aggregator/directory portal. Stripping directory domain.")
                    website = ""

                # Sourcing & Email Discovery Waterfall
                raw_web_emails = contact_info.get("emails") or []
                contact_email = contact_info.get("verified_email", "") or (raw_web_emails[0] if raw_web_emails else "")
                if (not contact_email or "@" not in contact_email or any(contact_email.lower().endswith(f"@{d}") for d in ("company.com", "example.com", "testcompany.com", "domain.com"))) and not os.environ.get("PYTEST_CURRENT_TEST"):
                    from agents.tools.email_finder import discover_verified_email
                    logger.info(f"📧 [WEB SCOUT RESCUE] No raw web email for '{company_name}' — activating Email Finder waterfall")
                    finder_res = discover_verified_email(
                        company_name=company_name,
                        website_url=website,
                        contact_name=contact_name,
                        contact_role=contact_role,
                        hunter_api_key=os.environ.get("HUNTER_API_KEY", ""),
                        apollo_api_key=os.environ.get("APOLLO_API_KEY", ""),
                    )
                    if finder_res.get("ok") and finder_res.get("email"):
                        contact_email = finder_res["email"]
                        logger.info(f"✅ [WEB SCOUT RESCUE] Found deliverable email: {contact_email} (source: {finder_res.get('source')})")

                if not contact_email or "@" not in contact_email or any(contact_email.lower().endswith(f"@{d}") for d in ("company.com", "example.com", "testcompany.com", "domain.com")):
                    logger.warning(f"❌ [WEB SCOUT] Rejected candidate '{company_name}': No genuine contact email discovered on website {website}.")
                    last_rejection_reason = f"No genuine contact email discovered on {website}"
                    if not run_until_found:
                        return {
                            "ok": False,
                            "status": "REJECTED_NO_VERIFIED_EMAIL",
                            "reason": last_rejection_reason,
                        }
                    continue

                # Deduplication check against storage contacted history
                if self.storage and hasattr(self.storage, "is_recipient_or_domain_contacted"):
                    if self.storage.is_recipient_or_domain_contacted(
                        email=contact_email,
                        domain=website,
                        company_name=company_name,
                        within_days=45,
                    ):
                        logger.info(f"⏭️ [WEB SCOUT DEDUPLICATION] Company '{company_name}' / domain '{website}' already contacted within 45 days. Skipping duplicate.")
                        last_rejection_reason = f"Company '{company_name}' already contacted within 45 days."
                        if not run_until_found:
                            return {
                                "ok": False,
                                "status": "DUPLICATE_COMPANY",
                                "reason": last_rejection_reason,
                            }
                        continue

                # Deliverability pre-flight verification
                from agents.email.verifier import DeliverabilityVerifier, DeliverabilityStatus
                verifier = DeliverabilityVerifier(
                    probe_smtp=not bool(os.environ.get("PYTEST_CURRENT_TEST")),
                    allow_business_roles=True,
                    probe_catchall=True,
                )
                is_role_account = False
                is_catchall = False
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    v_res = verifier.verify(contact_email)
                    if not v_res.is_safe_to_send or v_res.status != DeliverabilityStatus.DELIVERABLE:
                        logger.warning(f"❌ [WEB SCOUT REJECTED] Contact email '{contact_email}' is undeliverable or risky ({v_res.status.value}): {v_res.reason}")
                        last_rejection_reason = f"Contact email {contact_email} failed deliverability check ({v_res.status.value}): {v_res.reason}"
                        if not run_until_found:
                            return {
                                "ok": False,
                                "status": "REJECTED_UNDELIVERABLE_EMAIL",
                                "reason": last_rejection_reason,
                            }
                        continue
                    is_role_account = v_res.is_role_account
                    is_catchall = v_res.is_catchall

                contact_phone = dossier.get("contact_phone") or contact_info.get("verified_phone", "")
                pain_point = dossier.get("pain_point") or "Needs automated tracking of new records to eliminate manual entry."
                target_url = dossier.get("target_url") or portal_url
                portal_name = dossier.get("portal_name") or top_portal.get("title", "Public Registry Portal")
                jurisdiction = dossier.get("jurisdiction") or jurisdiction
                suggested_fields = dossier.get("suggested_fields") or live_records_data.get("fields") or ["record_id", "date", "status"]
                tier_key = dossier.get("tier_key") or "weekly"
                clean_portal_short = re.sub(r"(?i)\s*(portal|registry|court|system|division|clerk|records)\s*", "", portal_name).strip() or portal_name
                default_natural_subj = f"{clean_portal_short.lower()} records"
                pitch_subject = dossier.get("pitch_subject") or default_natural_subj
                if any(ai_w in pitch_subject.lower() for ai_w in ["quick", "automating", "streamlining", "sample", "data feed for", "unlocking", "elevating", "efficiency"]):
                    pitch_subject = default_natural_subj
                pitch_body = dossier.get("pitch_body") or "Hi, we can stream public records to your team automatically."

                # STRICT BUYER GATE: Government departments are NOT commercial buyers
                if is_disallowed_buyer(company_name, website, contact_email):
                    logger.warning(f"❌ [WEB SCOUT REJECTED] Discarding government candidate '{company_name}' ({contact_email}).")
                    last_rejection_reason = f"Government entity '{company_name}' cannot be qualified as a commercial buyer."
                    if not run_until_found:
                        return {
                            "ok": False,
                            "status": "REJECTED_GOVERNMENT_ENTITY",
                            "reason": last_rejection_reason,
                        }
                    continue

                # Live or catalog sample data
                records = dossier.get("live_extracted_records") or live_records_data.get("records") or []
                if not records:
                    lookup_text = f"{portal_name} {niche}".lower()
                    fallback_ds = None
                    for ds_key, ds_entry in AUTHENTIC_REGISTRY_DATASETS.items():
                        ds_tags = f"{ds_entry.get('portal_name','')} {ds_entry.get('jurisdiction','')}".lower()
                        if any(kw in lookup_text or kw in ds_tags for kw in ["probate", "foreclosure", "ucc", "permit", "lien", "tax", "medical", "defense", "entity"]):
                            fallback_ds = ds_entry
                            break
                    if not fallback_ds:
                        fallback_ds = list(AUTHENTIC_REGISTRY_DATASETS.values())[0]
                    records = list(fallback_ds.get("sample_data", []))[:25]

                target = {
                    "company_name": company_name,
                    "contact_name": contact_name,
                    "contact_role": contact_role,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                    "website": website,
                    "niche": niche,
                    "pain_point": pain_point,
                    "target_url": target_url,
                    "portal_name": portal_name,
                    "jurisdiction": jurisdiction,
                    "suggested_fields": suggested_fields,
                    "tier_key": tier_key,
                    "sample_data": records[:25],
                    "pitch_subject": pitch_subject,
                    "pitch_body": pitch_body,
                    "is_role_account": is_role_account,
                    "is_catchall": is_catchall,
                }

                clean_company = re.sub(r"[^a-z0-9]+", "-", target["company_name"].lower()).strip("-")
                lead_id = f"lead-{clean_company}-{int(time.time() * 1000)}"

                logger.info(f"🎯 [WEB SCOUT AI TARGET IDENTIFIED] Qualified Buyer: {target['company_name']}")

                # Scout Pipeline Ingestion & Sandbox Generation
                scout_pipe = ScoutPortalPipeline(self.portal)
                candidate = scout_pipe.publish_candidate(
                    company_name=target["company_name"],
                    lead_id=lead_id,
                    evidence=[{"url": target["target_url"], "title": target["portal_name"]}],
                    source_url=target["target_url"],
                    sample_rows=target["sample_data"],
                    research={
                        "niche": target["niche"],
                        "niche_confidence": "high",
                        "jurisdiction": target["jurisdiction"],
                        "portal_name": target["portal_name"],
                        "portal_url": target["target_url"],
                        "suggested_fields": target["suggested_fields"],
                        "recommended_tier": target["tier_key"],
                        "delivery_destination": "Google Sheets",
                        "contact_name": target["contact_name"],
                        "contact_role": target["contact_role"],
                        "contact_email": target["contact_email"],
                        "contact_phone": target["contact_phone"],
                        "website": target["website"],
                        "pain_point": target["pain_point"],
                    },
                    tier_key=target["tier_key"],
                )

                # Enrich lead in database
                lead = self.storage.get_lead(candidate.lead_id)
                if lead:
                    lead.contact_name = target["contact_name"]
                    lead.contact_role = target["contact_role"]
                    lead.contact_email = target["contact_email"]
                    lead.contact_phone = target["contact_phone"]
                    lead.target_portal_name = target["portal_name"]
                    lead.niche = target["niche"]
                    
                    lead.outreach_subject = target["pitch_subject"]
                    lead.outreach_body = target["pitch_body"]
                    if lead.state == State.PROSPECTING:
                        lead.transition(State.REVIEW, "Web scout discovery completed")
                    if lead.state == State.REVIEW:
                        lead.transition(State.PITCH_PENDING_APPROVAL, "Web scout pitch prepared for operator review")
                    self.storage.save_lead(lead)

                    try:
                        from agents.notifications import notification_manager
                        from agents.auto_outreach import auto_outreach_scheduler
                        from agents.pitcher import PitchMessage

                        web_pitch = PitchMessage(
                            subject=lead.outreach_subject,
                            body_text=lead.outreach_body,
                            body_html=getattr(lead, "outreach_html", "") or f"<p>{lead.outreach_body}</p>",
                            sandbox_url=f"https://www.omnileadfeeder.tech/p/{candidate.slug}",
                            word_count=len((getattr(lead, "outreach_body", "") or "").split()),
                        )

                        auto_outreach_scheduler.schedule_lead_for_dispatch(
                            lead=lead,
                            pitch=web_pitch,
                            storage_backend=self.storage,
                            notifier=notification_manager,
                        )

                        notification_manager.notify_lead_qualified_and_dispatching(
                            lead=lead,
                            pitch=web_pitch,
                            grace_period_seconds=auto_outreach_scheduler.grace_period_seconds,
                        )
                    except Exception as notify_err:
                        logger.warning(f"Web scout notification dispatch notice: {notify_err}")

                return {
                    "ok": True,
                    "company_name": target["company_name"],
                    "slug": candidate.slug,
                    "lead_id": candidate.lead_id,
                    "jurisdiction": target["jurisdiction"],
                    "portal_name": target["portal_name"],
                    "record_count": len(target["sample_data"])
                }

        return {
            "ok": False,
            "status": "NO_QUALIFIED_LEAD_FOUND",
            "reason": last_rejection_reason,
        }
