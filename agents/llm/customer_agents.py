"""
agents/llm/customer_agents.py - Prospect and customer lifecycle agent execution methods.
Covers Alex Persona Chat, Schema Column Suggestion, Cold Outreach Pitcher, and Inbound Sequencer.
"""
import json
import os
import re
from typing import Any, Optional, Dict, List
from .buyer_gate import is_disallowed_buyer
from ..logging_config import get_logger

logger = get_logger("llm_customer_agents")


class CustomerAgentsMixin:
    """Mixin providing customer-facing agents and lifecycle communications."""

    def draft_lifecycle_email(
        self,
        lead_info: dict[str, Any],
        template_name: str = "outreach_pitch",
        tone: str = "human_peer",
        custom_instruction: str = "",
    ) -> dict[str, str]:
        """Draft a contextual, non-templated cold or lifecycle email using live LLM."""
        company = lead_info.get("company_name", "your team")
        contact_name = lead_info.get("contact_name", "there")
        portal = lead_info.get("target_portal_name") or lead_info.get("jurisdiction") or "public records registry"
        niche = lead_info.get("niche", "public data tracking")
        pain = lead_info.get("commercial_pain") or lead_info.get("operational_friction") or "pulling filings by hand every morning"
        specialty = lead_info.get("business_specialty") or lead_info.get("human_observation") or f"active work in {niche}"
        sandbox_url = lead_info.get("sandbox_url") or lead_info.get("checkout_url") or "#"
        sample_count = lead_info.get("sample_count", 25)

        system_prompt = (
            "You are Alex, Senior Technical Solutions Specialist at LeadOps. "
            "You write authentic 1-on-1 peer emails from one human solutions engineer to another. "
            "NEVER sound like a marketer, automated bot, or generic sales rep. "
            "Rules:\n"
            "1. NO buzzwords: Banned words: 'speed-to-lead', 'game changer', 'streamline', 'leverage', 'cutting-edge', 'delighted'.\n"
            "2. Be concise: Under 70 words total.\n"
            "3. Reference their actual company, portal, and specific operational pain point.\n"
            "4. Include their live sandbox link.\n"
            "5. Close with a natural, low-pressure binary question (e.g. 'Worth having these stream over each morning, or is your team already tracking them in-house?').\n"
            "6. Sign off: Best,\nAlex | LeadOps\n"
            "Output JSON ONLY: {'subject': '...', 'body': '...'}"
        )

        user_prompt = (
            f"Stage / Intent: {template_name}\n"
            f"Tone: {tone}\n"
            f"Target Company: {company}\n"
            f"Contact: {contact_name}\n"
            f"Target Portal: {portal}\n"
            f"Specialty / Observation: {specialty}\n"
            f"Friction: {pain}\n"
            f"Verified Live Records: {sample_count}\n"
            f"Live Sandbox Link: {sandbox_url}\n"
        )
        if custom_instruction:
            user_prompt += f"\nOperator Custom Instruction: {custom_instruction}\n"

        res = self.generate_completion(system_prompt, user_prompt, temperature=0.35, max_tokens=700)
        if res and "{" in res and "}" in res:
            try:
                start = res.find("{")
                end = res.rfind("}") + 1
                parsed = json.loads(res[start:end])
                if parsed.get("subject") and parsed.get("body"):
                    return parsed
            except Exception as ex:
                logger.debug(f"JSON parsing fallback for pitch generation: {ex}")

        if res:
            subject = f"{portal.lower()} filings for {company}"
            return {"subject": subject, "body": res}

        return {
            "subject": f"{portal.lower()} filings for {company}",
            "body": (
                f"Hi {contact_name},\n\n"
                f"Saw {company}'s work in {niche}. We put together a live feed tracking new {portal} dockets daily so your team doesn't have to pull records manually.\n\n"
                f"Already indexed {sample_count} live records here:\n{sandbox_url}\n\n"
                f"Would it be helpful to stream these daily, or are you all set in-house?\n\n"
                f"Best,\nAlex | LeadOps"
            ),
        }

    def chat_with_alex(
        self,
        message: str,
        context: dict[str, Any],
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> str:
        """Live conversational response for Alex Solutions Engineer.
        
        Strictly adheres to brand guidelines:
        - Consultative, human, technical discovery (principal systems engineer to operator).
        - Dynamic, personalized per customer: NEVER repeats canned replies or fixed phrases.
        - Full memory of running conversation history.
        - Ground truth: $99 Setup Sprint deposit (100% money back before verification, 100% credited toward Month 1), $250-$500/mo ongoing sync,
          verified live records with 1-click proof URLs, Google Sheets / Webhook sync.
        """
        target_source = context.get("source_url", "the public records portal")
        system_prompt = (
            "You are Alex, Lead Solutions Architect at LeadOps / OmniLeadFeeder.\n"
            "You are having an ongoing, live conversation with a customer exploring their custom public records data feed.\n\n"
            "BRAND & COMMUNICATION GUIDELINES:\n"
            "1. TONE & PERSONA: Warm, pragmatic, highly technical, and consultative—like a principal systems engineer doing live requirements discovery. Zero corporate buzzwords or pushy sales pressure.\n"
            "2. DYNAMIC & PERSONALIZED: Do NOT use canned or repetitive responses. Every reply must be uniquely formulated for this specific customer, taking into account their company name, niche, jurisdiction, and exact questions.\n"
            "3. CONVERSATION LOG AWARENESS: You have access to the running conversation log. Build on prior points naturally. If you already introduced yourself or explained something earlier, DO NOT repeat yourself—progress the discussion forward.\n"
            "4. ACCURATE TECHNICAL POLICIES:\n"
            "   - Setup Sprint Deposit: $99 Setup Sprint Deposit (100% credited toward Month 1 balance). 100% refunded if the 5–10 row live verified sample does not pass our >=95% QA accuracy gate. NEVER use confusing escrow terminology; explain it simply as a $99 credit-backed setup sprint.\n"
            "   - Commercial Pricing Tiers: Starter Docket Feed ($150/mo, weekly), Production Feed Flagship ($250/mo, daily 6:00 AM UTC), Enterprise Swarm ($590/mo, continuous/hourly). Cancel anytime (no annual lock-in). Clients can also buy out the scraper code.\n"
            "   - Zero Mock Data: All data is scraped fresh from official county/court dockets, each with a 1-click live verification URL.\n"
            f"   - Target Docket / Portal Verification: We currently target {target_source}. If the customer mentions the source URL or portal, confirm whether this is the exact docket/registry they want, or invite them to provide their preferred county court or registry link.\n"
            "   - Delivery: Daily 6:00 AM UTC pushes via Webhook (JSON POST to CRM/Make/Zapier), direct Google Sheets sync, or CSV dashboard exports.\n"
            "5. LENGTH: 2 to 4 concise, impactful sentences. Always end with an insightful, low-friction technical clarifying question when relevant."
        )

        history_lines = []
        if conversation_history:
            for item in conversation_history[-10:]:
                sender = item.get("sender", "user")
                role = "Customer" if sender in ("user", "customer") else "Alex (You)"
                text = item.get("message") or item.get("text") or ""
                if text:
                    history_lines.append(f"{role}: {text}")

        prompt_sections = [f"Target Feed Context:\n{json.dumps(context, indent=2)}"]
        if history_lines:
            prompt_sections.append("Running Conversation Log:\n" + "\n".join(history_lines))
        prompt_sections.append(f"New Customer Message:\n{message}")

        user_prompt = "\n\n".join(prompt_sections)
        res = self.generate_completion(system_prompt, user_prompt, temperature=0.6, max_tokens=350)
        if not res:
            company = context.get("company_name", "your team")
            jurisdiction = context.get("jurisdiction", "county records")
            msg_lower = message.lower()
            if any(k in msg_lower for k in ["field", "column", "data", "schema", "attorney", "parcel"]):
                return f"Great question on the schema for {company}. I can definitely tailor those exact columns into your {jurisdiction} pipeline. Are there specific legal descriptions or parcel identifiers you need cross-referenced?"
            elif any(k in msg_lower for k in ["webhook", "sheet", "crm", "zapier", "delivery", "export"]):
                return f"We stream freshly verified {jurisdiction} records every morning at 6:00 AM UTC straight into your Google Sheet or a custom JSON webhook endpoint. Which CRM or database are you planning to pipe this into?"
            elif any(k in msg_lower for k in ["price", "cost", "down payment", "guarantee", "refund", "deposit"]):
                return f"We offer a 100% risk-free setup: your $99 down payment is fully refundable if our QA Gatekeeper doesn't prove ≥95% accuracy on 25 live rows from {jurisdiction} within 24 hours (100% credited toward Month 1). Ongoing sync is $250–$500/mo, cancel anytime."
            elif any(k in msg_lower for k in ["hi", "hello", "hey", "who are you", "help"]):
                return f"Hey there! I'm Alex from LeadOps engineering. I'm actively monitoring live filings from {jurisdiction}—what specific case types or filing categories does {company} want to capture?"
            return f"Understood! I've noted that requirement for our dev swarm working on {company}'s {jurisdiction} feed. Is there a specific daily delivery cadence or webhook destination you'd like us to configure?"
        return res

    def suggest_schema_columns(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """AI Assistant suggests domain-specific public record columns for a jurisdiction."""
        company_name = context.get("company_name", "Client")
        jurisdiction = context.get("jurisdiction", "County Portal")
        niche = context.get("niche", "Public Records")
        current_fields = context.get("current_fields", [])

        system_prompt = (
            "You are Alex, Principal Lead Solutions Engineer at LeadOps. "
            "Suggest 4 to 6 high-value extra public record data columns for this specific jurisdiction and niche. "
            "Return ONLY a JSON array of objects with keys: 'field_name' (lowercase snake_case), 'label' (human Title Case), 'description' (concise value explanation)."
        )
        user_prompt = (
            f"Company: {company_name}\n"
            f"Jurisdiction/Portal: {jurisdiction}\n"
            f"Niche: {niche}\n"
            f"Currently Selected Fields: {', '.join(current_fields)}\n\n"
            f"Suggest 4-6 unlisted high-value columns that title attorneys, investors, or operators frequently need from this registry."
        )

        res = self.generate_completion(system_prompt, user_prompt, temperature=0.3, max_tokens=600)
        if res and "[" in res and "]" in res:
            try:
                start = res.find("[")
                end = res.rfind("]") + 1
                parsed = json.loads(res[start:end])
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

        # Intelligent domain-aware fallbacks
        j_lower = (jurisdiction + " " + niche).lower()
        if "probate" in j_lower or "estate" in j_lower:
            return [
                {"field_name": "date_of_death", "label": "Date of Death", "description": "Verified decedent date of passing for timeline analysis"},
                {"field_name": "parcel_id", "label": "Property Parcel ID", "description": "Cross-referenced county tax assessor parcel number"},
                {"field_name": "executor_address", "label": "Executor / Personal Rep Address", "description": "Mailing address for appointed representative"},
                {"field_name": "bond_amount", "label": "Surety Bond Amount", "description": "Court-mandated administrator bond valuation"},
                {"field_name": "probate_judge", "label": "Presiding Probate Judge", "description": "Assigned division magistrate or judge"},
            ]
        elif "permit" in j_lower or "construction" in j_lower:
            return [
                {"field_name": "contractor_license_no", "label": "Contractor License #", "description": "State licensing board identifier"},
                {"field_name": "square_footage", "label": "Total Square Footage", "description": "Permitted building gross floor area"},
                {"field_name": "estimated_valuation", "label": "Permit Job Valuation", "description": "Declared project cost on application"},
                {"field_name": "inspection_date", "label": "Final Inspection Date", "description": "Target completion and certificate of occupancy date"},
            ]
        elif "tax" in j_lower or "lien" in j_lower:
            return [
                {"field_name": "tax_year", "label": "Delinquent Tax Year", "description": "Tax assessment period under lien"},
                {"field_name": "parcel_legal_desc", "label": "Legal Description", "description": "Subdivision lot & block legal definition"},
                {"field_name": "redemption_deadline", "label": "Statutory Redemption Deadline", "description": "Final date for owner redemption"},
                {"field_name": "assessed_land_value", "label": "Assessed Land Valuation", "description": "Certified county appraiser land value"},
            ]
        else:
            return [
                {"field_name": "parcel_id", "label": "Tax Parcel ID", "description": "Official county parcel number"},
                {"field_name": "document_recording_ref", "label": "Book & Page / Instrument #", "description": "County clerk official recording reference"},
                {"field_name": "party_address", "label": "Primary Party Address", "description": "Verified physical or mailing address"},
                {"field_name": "statutory_deadline", "label": "Filing Deadline / Hearing Date", "description": "Scheduled docket appearance or expiration"},
            ]

    def extract_records_from_web_content(
        self,
        text_content: str,
        source_url: str = "",
        data_goal: str = "",
        jurisdiction: str = "",
        max_records: int = 10,
    ) -> list[dict[str, Any]]:
        """Scout Extractor Agent: Extract authentic structured records from live target portal text."""
        if not text_content or not text_content.strip():
            return []

        system_prompt = (
            "You are the Scout Extraction AI Agent for LeadOps. "
            f"Your mission is to extract between 5 and {max_records} authentic, structured public data records from the provided web page text.\n\n"
            "STRICT PRODUCTION REQUIREMENTS:\n"
            "1. NO MOCK DATA. Extract ONLY actual entities, values, dates, case numbers, names, and information present in the text.\n"
            "2. Normalize the extracted fields into consistent keys (e.g. record_id, filing_date, party_name, status, description, address, jurisdiction).\n"
            "3. Return ONLY a JSON array of objects: [{\"field1\": \"val1\", ...}]. No explanation, no markdown formatting outside JSON."
        )
        user_prompt = (
            f"Source URL: {source_url}\n"
            f"Target Jurisdiction: {jurisdiction}\n"
            f"Target Data Goal: {data_goal}\n\n"
            f"Web Page Content:\n{text_content[:7500]}\n\n"
            f"Extract between 5 and {max_records} real structured records:"
        )

        res = self.generate_completion(system_prompt, user_prompt, temperature=0.2, max_tokens=1500)
        if res and "[" in res and "]" in res:
            try:
                start = res.find("[")
                end = res.rfind("]") + 1
                records = json.loads(res[start:end])
                if isinstance(records, list) and len(records) > 0:
                    clean_records = []
                    for r in records[:max_records]:
                        if isinstance(r, dict) and any(str(v).strip() for v in r.values()):
                            clean_records.append({str(k).strip(): str(v).strip() for k, v in r.items()})
                    if len(clean_records) >= 3:
                        logger.info(f"✓ [LLM EXTRACTOR] Successfully extracted {len(clean_records)} records from {source_url}")
                        return clean_records
            except Exception as e:
                logger.warning(f"Failed parsing LLM extraction output: {e}")
        return []

    def run_pitcher_agent(
        self,
        lead_info: dict[str, Any],
        sandbox_url: str = "",
    ) -> dict[str, Any]:
        import random
        import re

        # Dynamic Variation Engine rotations
        angles = [
            "Option A (Direct Pain): Highlight the frustration of morning docket lookups and manual portal pagination.",
            "Option B (Peer Observation): Note that other researchers in their specific county waste 5–10 hours a week pulling these same records.",
            "Option C (The Pure Gift): State matter-of-factly that you already ran an extraction on their local court records and parsed them into a spreadsheet.",
            "Option D (Time-to-Lead Hook): Focus on the value of receiving new filings first thing in the morning rather than checking midday.",
        ]
        tones = [
            "Pragmatic & Casual: Like an engineer emailing another operator.",
            "Observant & Helpful: Friendly, brief, direct.",
            "Low-Key Peer: No corporate greeting; gets straight to the point.",
        ]
        sign_offs = [
            "Best, Alex",
            "Cheers, Alex",
            "Alex | LeadOps",
            "Talk soon, Alex",
        ]

        selected_angle = random.choice(angles)
        selected_tone = random.choice(tones)
        selected_sign_off = random.choice(sign_offs)

        system_prompt = (
            "SYSTEM DIRECTIVE: ZERO-LINK PERMISSION-FIRST OUTREACH ENGINE\n\n"
            "You generate bespoke, ultra-short (35–55 words) B2B cold emails designed to secure a reply. "
            "Every email must feel handwritten, natural, and distinct. Never use buzzwords, corporate boilerplate, or standard cold email tropes.\n\n"
            "### STRICT DELIVERABILITY RULES (NON-NEGOTIABLE)\n"
            "1. ZERO LINKS: Never include URLs, domains, links, or anchor tags.\n"
            "2. ZERO ATTACHMENTS / PROMO CODE: Never mention PDFs, attachments, or sales demos.\n"
            "3. 100% PLAINTEXT: No markdown, no bullet points, no bolding, no HTML formatting.\n"
            "4. STRICT LENGTH: Between 35 and 55 words max (excluding sign-off).\n"
            "5. ONE LOW-FRICTION CALL TO ACTION (CTA): End with a simple 4–7 word question asking permission to send the data.\n"
            "6. NATURAL HUMAN SUBJECT LINES (ZERO AI CLICHÉS):\n"
            "   - NEVER write robotic phrases like 'Sample ... data feed for ...', 'Automating your...', 'Streamlining...', 'Unlocking...', 'Transforming...'.\n"
            "   - Strictly 2–4 words max. Must be all-lowercase or casual sentence case.\n"
            "   - Must sound like an engineer or operator writing a direct, thoughtful 1-on-1 note.\n"
            "   - Authentic examples: 'travis county permits', 'records for {company_name}', 'harris county deeds', 'cook county filings', 'question re: {portal}'.\n"
            "   - BANNED WORD: NEVER use the word 'quick' anywhere in subject or body ('quick question', 'quick note', 'quick call', 'quick chat', etc.). It is an instant giveaway of automated cold outreach.\n\n"
            f"### DYNAMIC VARIATION FOR THIS DRAFT:\n"
            f"- Angle: {selected_angle}\n"
            f"- Tone: {selected_tone}\n"
            f"- Sign-Off: Use '{selected_sign_off}'\n\n"
            "### OUTPUT FORMAT\n"
            "Emit ONLY valid JSON:\n"
            "{\n"
            '  "subject": "2-4 words max, casual lowercase only, zero marketing words",\n'
            '  "body": "Exact plaintext email body"\n'
            "}"
        )

        user_prompt = (
            f"Input Prospect Data:\n"
            f"- first_name: {lead_info.get('contact_name', 'there')}\n"
            f"- company_name: {lead_info.get('company_name')}\n"
            f"- niche: {lead_info.get('niche')}\n"
            f"- jurisdiction: {lead_info.get('jurisdiction') or lead_info.get('portal_name')}\n"
            f"- target_portal: {lead_info.get('portal_name')}\n"
            f"- record_type: {lead_info.get('niche', 'public records')}\n\n"
            f"Generate the exact zero-link cold outreach email JSON now:"
        )

        res = self.generate_completion(system_prompt, user_prompt, temperature=0.4, max_tokens=300)
        if res and "{" in res and "}" in res:
            try:
                start = res.find("{")
                end = res.rfind("}") + 1
                pitch_data = json.loads(res[start:end])
                raw_body = pitch_data.get("body") or pitch_data.get("body_text", "")
                
                # Sanitize: Strip any accidental URLs, markdown links, or banned words
                clean_body = re.sub(r"https?://\S+", "", raw_body).strip()
                clean_body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_body).strip()
                clean_body = re.sub(r"(?i)\bquick\s+", "", clean_body).strip()

                words = len(clean_body.split())
                raw_subject = pitch_data.get("subject", "").strip()
                # Anti-AI subject sanitizer
                clean_portal = re.sub(r"(?i)\s*(portal|registry|court|system|division|clerk|records)\s*", "", str(lead_info.get('portal_name', ''))).strip() or "public records"
                clean_fn = (lead_info.get('contact_name') or '').strip()
                fallback_subject = f"question {clean_fn}" if clean_fn and clean_fn.lower() != 'there' else f"{clean_portal.lower()} records"
                
                if not raw_subject or any(bad in raw_subject.lower() for bad in ["quick", "sample", "data feed for", "automating", "streamlining", "unlocking", "elevating", "efficiency"]):
                    subject = fallback_subject
                else:
                    subject = re.sub(r"(?i)\bquick\s*", "", raw_subject).lower().strip()
                    if not subject or subject == "question":
                        subject = fallback_subject

                # Build clean HTML representation matching brand guidelines (Pine Slate / Forest Deep)
                html_paragraphs = "".join(f"<p style='margin: 0 0 14px 0;'>{p.strip()}</p>" for p in clean_body.split("\n\n") if p.strip())
                body_html = (
                    f"<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Inter', Segoe UI, sans-serif; "
                    f"color: #15251F; max-width: 580px; line-height: 1.55; font-size: 15px;\">"
                    f"{html_paragraphs}"
                    f"</div>"
                )

                return {
                    "subject": subject,
                    "body_text": clean_body,
                    "body_html": body_html,
                    "word_count": words,
                    "angle_used": selected_angle,
                }
            except (json.JSONDecodeError, ValueError):
                pass

        # Robust zero-link Touch 1 fallback matching brand & persona guidelines
        clean_portal = re.sub(r"(?i)\s*(portal|registry|court|system|division|clerk|records)\s*", "", str(lead_info.get('portal_name', ''))).strip() or "public records"
        clean_fn = (lead_info.get("contact_name") or "there").split()[0].strip() or "there"
        comp = lead_info.get("company_name") or "your team"
        fallback_subject = f"records for {comp}" if len(comp) < 20 else f"{clean_portal.lower()} records"
        fallback_body = (
            f"Hi {clean_fn},\n\n"
            f"We pulled this morning's new filings for {comp} from the local registry and formatted them cleanly into a spreadsheet.\n\n"
            f"Mind if I send the link over to review?\n\n"
            f"{selected_sign_off}"
        )
        html_paragraphs = "".join(f"<p style='margin: 0 0 14px 0;'>{p.strip()}</p>" for p in fallback_body.split("\n\n") if p.strip())
        return {
            "subject": fallback_subject,
            "body_text": fallback_body,
            "body_html": (
                f"<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Inter', Segoe UI, sans-serif; "
                f"color: #15251F; max-width: 580px; line-height: 1.55; font-size: 15px;\">"
                f"{html_paragraphs}"
                f"</div>"
            ),
            "word_count": len(fallback_body.split()),
            "angle_used": selected_angle,
        }

    def run_sequencer_agent(
        self,
        lead_info: dict[str, Any],
        touch_number: int,
        prior_subject: str = "",
        prior_body: str = "",
    ) -> dict[str, Any]:
        """AI Sequencer Agent: Generates authentic, humanized, peer-to-peer follow-up copy for Touch 2 (bump) and Touch 3 (breakup).
        
        Strict Rules:
        - Written from Alex (Technical Solutions at LeadOps) speaking to an operations peer.
        - Strictly 18 to 32 words max (excluding sign-off). Never exceed 34 words.
        - ZERO links, zero attachments, 100% plaintext.
        - Banned vocabulary: NEVER use 'quick' ('quick bump', 'quick question', 'quick follow up').
        - Natural in-thread reply subject: Re: <prior_subject>.
        """
        import random
        import re

        clean_co = re.sub(r"(?i)\s+(inc\.?|llc|corp\.?|ltd\.?|co\.?|pllc)$", "", str(lead_info.get("company_name", "your team"))).strip()
        first_name = (lead_info.get("contact_name") or "there").split()[0].strip() or "there"
        county = lead_info.get("county") or lead_info.get("jurisdiction") or "local"
        if county and "County" not in county and county.lower() != "local":
            county = f"{county} County"

        sign_offs = [
            "Best,\nAlex | LeadOps",
            "Cheers,\nAlex | LeadOps",
            "Best,\nAlex",
        ]
        selected_sign_off = random.choice(sign_offs)

        if touch_number == 2:
            touch_context = (
                f"TOUCH 2 (Day 4 In-Thread Fresh Filings Bump):\n"
                f"- Purpose: Casual follow-up from an engineer/operator.\n"
                f"- Context: We freshly indexed this morning's new {county} filings for {clean_co}.\n"
                f"- Low-friction offer: Ask if they'd like today's updated spreadsheet or if they already have docket lookups handled in-house.\n"
                f"- Target length: 20–28 words."
            )
        elif touch_number == 3:
            touch_context = (
                f"TOUCH 3 (Day 8 In-Thread Breakup & Standing Resource):\n"
                f"- Purpose: Low-pressure, respectful close.\n"
                f"- Context: Assume they already have docket extraction handled in-house.\n"
                f"- Standing resource: If they ever need automated morning {county} filings before 8 AM, reach out anytime.\n"
                f"- Target length: 20–28 words."
            )
        else:
            return {}

        system_prompt = (
            "SYSTEM DIRECTIVE: HUMANIZED PEER-TO-PEER SEQUENCE ENGINE (ALEX @ LEADOPS)\n\n"
            "You write authentic, humanized 1-on-1 follow-up cold emails for an automated public records feed service. "
            "You write as Alex, a systems engineer, chatting with an operations peer. "
            "You are direct, casual, pragmatic, and helpful. Never sound like an SDR, a marketer, or an AI.\n\n"
            "STRICT RULES (NON-NEGOTIABLE):\n"
            "1. LENGTH: Strictly 18 to 32 words max (excluding sign-off). Never exceed 34 words.\n"
            "2. ZERO LINKS: No URLs, no domains, no tracking links.\n"
            "3. ZERO JARGON: No corporate buzzwords ('streamline', 'synergy', 'transform', 'unlock', 'game-changer').\n"
            "4. BANNED WORD: NEVER use the word 'quick' anywhere ('quick question', 'quick bump', 'quick follow up', 'quick note').\n"
            "5. 100% PLAINTEXT: No markdown, bolding, bullet points, or HTML.\n"
            f"6. SIGN-OFF: End exactly with:\n{selected_sign_off}\n\n"
            f"{touch_context}\n\n"
            "OUTPUT FORMAT: Emit ONLY valid JSON:\n"
            "{\n"
            '  "body": "Exact plaintext email body"\n'
            "}"
        )

        user_prompt = (
            f"Prospect Details:\n"
            f"- Contact First Name: {first_name}\n"
            f"- Company Name: {clean_co}\n"
            f"- County / Jurisdiction: {county}\n"
            f"- Prior Touch Subject: {prior_subject}\n\n"
            f"Generate the exact Touch {touch_number} email JSON now:"
        )

        res = self.generate_completion(system_prompt, user_prompt, temperature=0.35, max_tokens=180)
        if res and "{" in res and "}" in res:
            try:
                start = res.find("{")
                end = res.rfind("}") + 1
                data = json.loads(res[start:end])
                raw_body = data.get("body") or data.get("body_text", "")
                
                # Sanitize: Strip links, markdown, and banned words
                clean_body = re.sub(r"https?://\S+", "", raw_body).strip()
                clean_body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_body).strip()
                clean_body = re.sub(r"(?i)\bquick\s*", "", clean_body).strip()
                
                # Clean in-thread reply subject
                clean_subj = re.sub(r"(?i)^(re:\s*)+", "", (prior_subject or "update").strip()).strip()
                reply_subj = f"Re: {clean_subj}" if clean_subj else "Re: update"
                
                words = clean_body.split()
                if len(words) > 35:
                    if touch_number == 2:
                        clean_body = (
                            f"Hi {first_name},\n\n"
                            f"Following up — we indexed this morning's new {county} filings. "
                            f"Want me to send the updated spreadsheet, or are you all set in-house?\n\n"
                            f"{selected_sign_off}"
                        )
                    else:
                        clean_body = (
                            f"Hi {first_name},\n\n"
                            f"Assuming you have this handled in-house. "
                            f"If you ever need daily {county} filings before 8 AM, reach out anytime.\n\n"
                            f"{selected_sign_off}"
                        )
                    words = clean_body.split()

                return {
                    "touch_number": touch_number,
                    "subject": reply_subj,
                    "body_text": clean_body,
                    "word_count": len(words),
                    "is_humanized_peer": True,
                }
            except (json.JSONDecodeError, ValueError):
                pass
        return {}

    def run_voice_review_and_humanizer_agent(
        self,
        subject: str,
        body_text: str,
        prospect_name: str,
        company_name: str,
        niche: str,
    ) -> dict[str, Any]:
        """Ensure outbound email conforms strictly to Alex @ LeadOps authentic engineering voice."""
        from agents.email.ai_review import EmailVoiceHumanizerAgent
        agent = EmailVoiceHumanizerAgent(self)
        return agent.review_and_humanize(subject, body_text, prospect_name, company_name, niche)

    def run_inbound_reply_agent(
        self,
        inbound_text: str,
        inbound_subject: str,
        lead_context: dict[str, Any],
        sandbox_url: str = "",
    ) -> dict[str, Any]:
        """Analyze prospect reply to outreach and formulate tailored response."""
        from agents.email.ai_review import InboundReplyAgent
        agent = InboundReplyAgent(self)
        return agent.process_inbound_reply(inbound_text, inbound_subject, lead_context, sandbox_url)






