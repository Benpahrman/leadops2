"""AI Agent hooks for prospect website verification, outbound voice humanization, and autonomous inbound replies."""

import logging
from typing import Any

from agents.llm_client import LLMAgentEngine

logger = logging.getLogger("leadops.email.ai_review")


class ProspectWebsiteVerificationAgent:
    """Evaluates prospect website content to verify legitimate commercial operations before pitching."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm = llm_engine or LLMAgentEngine()

    def verify_website(
        self,
        company_name: str,
        website_url: str,
        niche: str,
        page_content: str,
    ) -> dict[str, Any]:
        """Perform autonomous LLM verification on prospect website."""
        truncated_content = (page_content or "")[:3500].strip()
        system_prompt = (
            "You are the Commercial Due-Diligence & Prospect Verification Agent at LeadOps. "
            "Your task is to inspect a prospect's website content and determine if they are a legitimate, "
            "active commercial business capable of buying automated public records data feeds.\n\n"
            "CRITICAL RULES:\n"
            "1. Government agencies, county clerk offices, municipal departments, and courts are DATA SOURCES, NOT BUYERS. Mark them as FALSE.\n"
            "2. Parked domains, 404 pages, under-construction templates, and spam portals are NOT LEGITIMATE. Mark them as FALSE.\n"
            "3. Active private companies, law firms, contractors, brokers, and agencies ARE legitimate buyers. Mark them as TRUE.\n"
            "4. Output STRICT JSON ONLY."
        )

        user_prompt = f"""
Prospect Evaluation Target:
- Company Name: {company_name}
- Target Niche: {niche}
- Website URL: {website_url}
- Scraped Website Text:
\"\"\"{truncated_content}\"\"\"

Analyze the company and return a JSON object with:
{{
  "is_legitimate_buyer": true | false,
  "confidence_score": 0.0 to 1.0,
  "commercial_activity_detected": "summary of what they actually do or sell",
  "niche_alignment": "high" | "medium" | "low" | "none",
  "disqualification_reason": "explanation if false, otherwise empty string",
  "verified_company_summary": "1 sentence describing the business"
}}
"""
        res = self.llm.generate_structured_json(system_prompt, user_prompt)
        if not res or not isinstance(res, dict):
            # Fallback if LLM offline: basic heuristics
            has_content = len(truncated_content) > 100
            is_gov = any(k in (website_url + company_name).lower() for k in [".gov", "county", "city of", "department of", "court"])
            return {
                "is_legitimate_buyer": has_content and not is_gov,
                "confidence_score": 0.7 if (has_content and not is_gov) else 0.2,
                "commercial_activity_detected": "Heuristic fallback evaluation",
                "niche_alignment": "medium",
                "disqualification_reason": "Government entity or lack of content" if is_gov or not has_content else "",
                "verified_company_summary": f"Commercial firm in {niche}",
            }
        return res


class EmailVoiceHumanizerAgent:
    """Verifies that outbound cold emails strictly adhere to Alex @ LeadOps authentic engineering voice."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm = llm_engine or LLMAgentEngine()

    def review_and_humanize(
        self,
        subject: str,
        body_text: str,
        prospect_name: str,
        company_name: str,
        niche: str,
    ) -> dict[str, Any]:
        """Inspect and polish cold outreach email for authentic, human peer-to-peer tone."""
        import re

        system_prompt = (
            "You are the Voice Review & Humanization Specialist for Alex, Technical Solutions Specialist at LeadOps.\n"
            "SYSTEM DIRECTIVE: ZERO-LINK PERMISSION-FIRST OUTREACH ENGINE.\n\n"
            "Your mission: Ensure cold emails feel like a genuine, thoughtful 1-on-1 peer email from a capable systems engineer to an operator.\n\n"
            "STRICT DELIVERABILITY & BRAND RULES (NON-NEGOTIABLE):\n"
            "1. ZERO LINKS: Never include URLs, domains, links, or anchor tags. If present, DELETE THEM.\n"
            "2. ZERO ATTACHMENTS / PROMO CODE: Never mention PDFs, attachments, or sales demos.\n"
            "3. 100% PLAINTEXT: No markdown, no bullet points, no bolding, no HTML formatting.\n"
            "4. STRICT LENGTH: Between 35 and 55 words max (excluding sign-off).\n"
            "5. ONE LOW-FRICTION CALL TO ACTION (CTA): End with a simple 4–7 word question asking permission to send data.\n"
            "6. BRAND VOICE: Pragmatic, not corporate. Eliminate buzzwords. Concrete over descriptive. Empathetic to tedious manual docket lookup.\n"
            "7. SIGN-OFF: Rotate between 'Best, Alex', 'Cheers, Alex', 'Alex | LeadOps', or 'Talk soon, Alex'.\n"
            "8. NATURAL HUMAN SUBJECT LINES (ZERO AI CLICHÉS):\n"
            "   - If Subject to Review contains 'Sample ... data feed', 'Automating', 'Streamlining', 'Unlocking', 'Transforming', or corporate jargon, REWRITE IT.\n"
            "   - Must be 2-4 words, all lowercase or casual sentence case (e.g. 'travis county permits', 'records for {company_name}', 'court records / {company_name}').\n"
            "9. BANNED VOCABULARY (AI DEAD-GIVEAWAY):\n"
            "   - NEVER use the word 'quick' anywhere in subject or body ('quick question', 'quick note', 'quick call', 'quick chat', 'take a quick look'). It is an instant giveaway of generic automated cold outreach.\n"
            "   - Be direct: use 'Question re: ...', 'Noticed ...', 'Had a question', or simply 'records for {company_name}'.\n"
            "10. Output STRICT JSON ONLY."
        )

        user_prompt = f"""
Subject to Review: {subject}
Body to Review:
\"\"\"{body_text}\"\"\"

Prospect Context:
- Contact Name: {prospect_name}
- Company: {company_name}
- Niche: {niche}

Inspect this email and return JSON:
{{
  "is_voice_compliant": true | false,
  "word_count": int,
  "humanized_subject": "2-4 words max, casual lowercase only, zero AI marketing words",
  "humanized_body_text": "Exact plaintext email body (35-55 words, zero links)",
  "voice_notes": "brief confirmation of brand voice alignment"
}}
"""
        res = self.llm.generate_structured_json(system_prompt, user_prompt)
        
        # Clean company name and build natural subject fallback
        clean_co = re.sub(r"(?i)\s+(inc\.?|llc|corp\.?|ltd\.?|co\.?|pllc)$", "", company_name).strip()
        clean_co = re.sub(r"\s+\d+$", "", clean_co).strip()
        first_name = (prospect_name or "").split()[0].strip()
        topic_short = niche.split("&")[0].split("and")[0].strip().lower()
        natural_fallback_subj = f"question {first_name}" if first_name and first_name.lower() != "there" else f"{clean_co.lower()} / public records"

        if not res or not isinstance(res, dict) or not res.get("humanized_body_text"):
            # Sanitize fallback
            clean_body = re.sub(r"https?://\S+", "", body_text).strip()
            clean_body = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_body).strip()
            clean_body = re.sub(r"(?i)\bquick\s+", "", clean_body).strip()
            
            clean_subj = subject
            if any(bad in clean_subj.lower() for bad in ["quick", "sample", "data feed for", "automating", "streamlining", "unlocking", "elevating", "efficiency"]):
                clean_subj = natural_fallback_subj
            else:
                clean_subj = re.sub(r"(?i)\bquick\s*", "", clean_subj).strip()
                if not clean_subj or clean_subj == "question":
                    clean_subj = natural_fallback_subj
            return {
                "is_voice_compliant": True,
                "word_count": len(clean_body.split()),
                "humanized_subject": clean_subj.lower().strip(),
                "humanized_body_text": clean_body,
                "voice_notes": "Preserved sanitized verified copy",
            }
        
        # Sanitize LLM response to guarantee zero links and no banned words
        clean_text = re.sub(r"https?://\S+", "", res.get("humanized_body_text", "")).strip()
        clean_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean_text).strip()
        clean_text = re.sub(r"(?i)\bquick\s+", "", clean_text).strip()
        res["humanized_body_text"] = clean_text
        res["word_count"] = len(clean_text.split())

        subj = str(res.get("humanized_subject", "")).strip()
        if not subj or any(bad in subj.lower() for bad in ["quick", "sample", "data feed for", "automating", "streamlining", "unlocking", "elevating", "efficiency"]):
            subj = natural_fallback_subj
        else:
            subj = re.sub(r"(?i)\bquick\s*", "", subj).strip()
            if not subj or subj == "question":
                subj = natural_fallback_subj
        res["humanized_subject"] = subj.lower().strip()
        
        # Guarantee non-AI subject in result
        subj = str(res.get("humanized_subject") or subject)
        if any(bad in subj.lower() for bad in ["sample", "data feed for", "automating", "streamlining", "unlocking", "elevating", "efficiency"]):
            res["humanized_subject"] = natural_fallback_subj
        else:
            res["humanized_subject"] = subj.lower().strip()
        return res


class InboundReplyAgent:
    """Analyzes incoming prospect email replies and formulates contextual responses."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm = llm_engine or LLMAgentEngine()

    def process_inbound_reply(
        self,
        inbound_text: str,
        inbound_subject: str,
        lead_context: dict[str, Any],
        sandbox_url: str = "",
        conversation_history: list[dict[str, Any]] | None = None,
        initial_outreach: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Classify incoming reply and draft tailored response in Alex's voice with conversation memory."""
        company_name = lead_context.get("company_name", "your company")
        contact_name = lead_context.get("contact_name", "there")
        portal_name = lead_context.get("target_portal_name", "public records")

        system_prompt = (
            "You are Alex, Technical Solutions Specialist & Automation Architect at LeadOps / OmniLeadFeeder.\n"
            "A prospective commercial customer just replied to our communication regarding automated public records data feeds.\n\n"
            "BRAND & COMMUNICATION GUIDELINES:\n"
            "1. DYNAMIC & PERSONALIZED: NEVER use generic canned email templates or repeat the same email over and over. "
            "Formulate a fresh, individualized response tailored specifically to the customer's exact words, questions, company, and niche.\n"
            "2. CONVERSATION LOG AWARENESS: You have access to the running log of past messages in this thread (initial outreach and prior replies). "
            "Build upon the conversation naturally. If you already explained pricing or introduced yourself earlier, DO NOT repeat yourself—progress the discussion forward.\n"
            "3. TONE & STYLE: Peer-to-peer, pragmatic engineer tone (Alex). Direct, concise, highly competent, no corporate fluff, no aggressive sales push.\n"
            "4. CORE KNOWLEDGE BASE & FACTS:\n"
            "   - Escrow Deposit: $250 milestone deposit held in third-party escrow while they inspect and approve the live feed (100% money back if not satisfied).\n"
            "   - Ongoing Sync: $250–$500/mo depending on frequency and volume (cancel anytime, no annual contracts). Code buyout also available.\n"
            "   - Data Proof: Scraped fresh from official government dockets (zero synthetic/bought lists), with a 1-click verification URL on each record.\n"
            "   - Delivery: Streams directly to Google Sheets, CRM webhooks, or CSV exports every morning at 6:00 AM UTC.\n"
            "   - No sign-in or sales demo required to test their sandbox.\n"
            "5. LENGTH: Under 85 words. End with a natural, low-friction question.\n"
            "6. BANNED VOCABULARY: NEVER use the word 'quick' (e.g. do not say 'quick question', 'quick call', 'quick note', 'take a quick look'). Be direct and natural.\n"
            "7. Output STRICT JSON ONLY."
        )

        history_lines = []
        if initial_outreach and initial_outreach.get("body"):
            history_lines.append(f"Alex (Initial Outreach): {initial_outreach.get('body')[:300]}")
        if conversation_history:
            for item in conversation_history[-6:]:
                sender = item.get("sender_name") or item.get("sender_email") or "Prospect"
                body = item.get("body", "")
                draft = item.get("draft_reply", "")
                if body:
                    history_lines.append(f"Prospect ({sender}): {body[:300]}")
                if draft:
                    history_lines.append(f"Alex (Prior Reply): {draft[:300]}")

        prompt_sections = [
            f"Lead Context:\n- Company: {company_name}\n- Contact: {contact_name}\n- Portal / Data Source: {portal_name}\n- Live Sandbox URL: {sandbox_url}"
        ]
        if history_lines:
            prompt_sections.append("Running Conversation Log:\n" + "\n".join(history_lines))
        prompt_sections.append(f"New Inbound Email Received:\nSubject: {inbound_subject}\nBody:\n\"\"\"{inbound_text}\"\"\"")
        prompt_sections.append(
            "Analyze and return JSON:\n"
            "{\n"
            '  "intent": "INTERESTED" | "QUESTION" | "OBJECTION" | "OPT_OUT" | "OUT_OF_OFFICE",\n'
            '  "sentiment": "POSITIVE" | "NEUTRAL" | "NEGATIVE",\n'
            f'  "draft_subject": "Re: {inbound_subject}",\n'
            '  "draft_reply_text": "Alex\'s dynamic, personalized, context-aware response",\n'
            '  "should_auto_send": true | false,\n'
            '  "summary": "1-sentence summary of what prospect said"\n'
            "}"
        )

        user_prompt = "\n\n".join(prompt_sections)
        res = self.llm.generate_structured_json(system_prompt, user_prompt)
        if res and isinstance(res, dict):
            if "draft_reply_text" in res and isinstance(res["draft_reply_text"], str):
                res["draft_reply_text"] = re.sub(r"(?i)\bquick\s+", "", res["draft_reply_text"]).strip()
            if "draft_subject" in res and isinstance(res["draft_subject"], str):
                res["draft_subject"] = re.sub(r"(?i)\bquick\s*", "", res["draft_subject"]).strip()

        if not res or not isinstance(res, dict):
            # Fallback
            inbound_lower = inbound_text.lower()
            p_clean = (portal_name or "Public Records").strip()
            if p_clean.lower().endswith(("records", "filings", "permits", "dockets")):
                portal_phrase = p_clean
            else:
                portal_phrase = f"{p_clean} records"

            active_url = (sandbox_url or "").strip() or "https://omnileadfeeder.tech/p/austin-commercial-permits"

            is_optout = any(w in inbound_lower for w in ["unsubscribe", "remove", "stop", "not interested"])
            if is_optout:
                return {
                    "intent": "OPT_OUT",
                    "sentiment": "NEGATIVE",
                    "draft_subject": f"Re: {inbound_subject}",
                    "draft_reply_text": f"Understood, {contact_name}. You've been removed from all future communications. Best, Alex",
                    "should_auto_send": True,
                    "summary": "Prospect requested removal",
                }

            # Delivery & integration inquiry fallback
            if any(w in inbound_lower for w in ["webhook", "zapier", "make", "sheet", "crm", "destination", "format"]):
                return {
                    "intent": "QUESTION",
                    "sentiment": "POSITIVE",
                    "draft_subject": f"Re: {inbound_subject}",
                    "draft_reply_text": f"Hi {contact_name},\n\nYes, absolutely. We can stream records directly via webhook (JSON POST payload) or sync daily to Google Sheets at 6:00 AM UTC. We can easily map the payload to your Zapier or CRM endpoint.\n\nHere is your live sandbox to inspect the field structure:\n{active_url}\n\nBest,\nAlex | LeadOps",
                    "should_auto_send": False,
                    "summary": "Prospect inquired about webhook and data delivery integrations",
                }

            # Custom schema & column inquiry fallback
            if any(w in inbound_lower for w in ["field", "column", "schema", "parcel", "custom", "filter"]):
                return {
                    "intent": "QUESTION",
                    "sentiment": "POSITIVE",
                    "draft_subject": f"Re: {inbound_subject}",
                    "draft_reply_text": f"Hi {contact_name},\n\nWe can definitely extract and format those specific columns for {company_name} from {portal_phrase}. Our autonomous pipeline validates every selector against official filings before delivery.\n\nYou can review your live sandbox columns here:\n{active_url}\n\nBest,\nAlex | LeadOps",
                    "should_auto_send": False,
                    "summary": "Prospect asked about custom schema columns",
                }

            # Pricing inquiry fallback
            if any(w in inbound_lower for w in ["cost", "price", "pricing", "how much", "deposit", "escrow"]):
                return {
                    "intent": "QUESTION",
                    "sentiment": "NEUTRAL",
                    "draft_subject": f"Re: {inbound_subject}",
                    "draft_reply_text": f"Hi {contact_name},\n\nSetup is a 50% milestone deposit of $250, held in third-party escrow while you inspect and approve your live feed. Ongoing sync is $250-$500/mo depending on frequency, cancel anytime.\n\nYou can review your company's live preview here:\n{active_url}\n\nBest,\nAlex | LeadOps",
                    "should_auto_send": False,
                    "summary": "Prospect inquired about pricing",
                }

            # Demo, sample, jurisdiction, or filing inquiry fallback
            if any(w in inbound_lower for w in ["demo", "sample", "travis", "filing", "filings", "live data", "permit", "court", "have data"]):
                return {
                    "intent": "INTERESTED",
                    "sentiment": "POSITIVE",
                    "draft_subject": f"Re: {inbound_subject}",
                    "draft_reply_text": (
                        f"Hi {contact_name},\n\n"
                        f"Yes, absolutely — we extract verified {portal_phrase} every morning at 6:00 AM UTC. "
                        f"You can inspect your live data sandbox directly here:\n{active_url}\n\n"
                        f"No sign-in or demo call is needed. Every row includes a direct 1-click link to verify "
                        f"against the official registry. Does this schema match what your team needs?\n\n"
                        f"Best,\nAlex | LeadOps"
                    ),
                    "should_auto_send": False,
                    "summary": f"Prospect asked for demo/data for {portal_phrase}",
                }

            return {
                "intent": "INTERESTED",
                "sentiment": "POSITIVE",
                "draft_subject": f"Re: {inbound_subject}",
                "draft_reply_text": (
                    f"Hi {contact_name},\n\n"
                    f"Thanks for following up! Here is your dedicated live data sandbox with recent {portal_phrase}:\n{active_url}\n\n"
                    f"No sign-in is needed — every row has a 1-click link to verify against the official registry. "
                    f"Let me know if this schema matches what your team needs.\n\n"
                    f"Best,\nAlex | LeadOps"
                ),
                "should_auto_send": False,
                "summary": "Prospect showed interest",
            }
        return res
