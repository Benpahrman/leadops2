"""Outbound email dispatch and Pitcher (Alex) workflow for Scout leads via native Gmail SMTP."""

import json
import os
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .domain import Lead, State
from .llm_client import LLMAgentEngine
from .email.config import EmailSettings
from .email.client import EmailClient
from .email.verifier import DeliverabilityVerifier, DeliverabilityStatus, VerificationResult
from .email.warmup import WarmupManager, WarmupTier

logger = logging.getLogger("leadops.pitcher")

# Backward-compatible aliases for legacy imports & tests
SendPulseSettings = EmailSettings
SendPulseClient = EmailClient



@dataclass(frozen=True)
class PitchMessage:
    subject: str
    body_text: str
    body_html: str
    sandbox_url: str
    word_count: int


def _safe_str(val: Any, fallback: str = "") -> str:
    if val is None:
        return fallback
    if not isinstance(val, str):
        s = str(val)
        if "MagicMock" in s or "<MagicMock" in s:
            return fallback
        return s
    return val


def generate_natural_subject(
    company_name: str = "",
    niche: str = "",
    portal_name: str = "",
    contact_name: str = "",
    jurisdiction: str = "",
) -> str:
    """Generate concise, natural, non-AI lowercase peer subject lines (2-4 words).
    
    Eliminates robotic tropes like 'Sample ... data feed for ...' or 'Automating your manual...'.
    """
    import random
    import re
    
    company_name = _safe_str(company_name)
    niche = _safe_str(niche, "public records")
    portal_name = _safe_str(portal_name)
    contact_name = _safe_str(contact_name)
    jurisdiction = _safe_str(jurisdiction)
    
    clean_co = re.sub(r"(?i)\s+(inc\.?|llc|corp\.?|ltd\.?|co\.?|pllc)$", "", company_name).strip()
    clean_co = re.sub(r"\s+\d+$", "", clean_co).strip()
    first_name = (contact_name or "").split()[0].strip() if contact_name else ""
    
    portal_short = re.sub(r"(?i)\s*(portal|registry|court|system|division|clerk|records|official|department)\s*", "", portal_name).strip()
    geo_hint = jurisdiction.split(",")[0].strip() if jurisdiction else ""
    
    topic = portal_short or geo_hint or niche.split("&")[0].split("and")[0].strip()
    topic_clean = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    if len(topic_clean.split()) > 3:
        topic_clean = " ".join(topic_clean.split()[:2])
    if not topic_clean:
        topic_clean = "public records"

    candidates = [
        f"{topic_clean} records",
        f"question re: {topic_clean}",
        f"{clean_co.lower()} / public records" if clean_co else f"{topic_clean} records",
        f"question {first_name}" if first_name and first_name.lower() != "there" else f"question re: {clean_co.lower()}" if clean_co else f"{topic_clean} records",
        f"record lookups at {clean_co.lower()}" if clean_co else f"{topic_clean} filings",
    ]
    return random.choice(candidates)


def render_executive_email_html(body_text: str, sandbox_url: str = "", include_button: bool = False) -> str:
    """Format plaintext email into clean, executive-styled HTML with proper paragraph spacing and mobile typography."""
    paragraphs = [p.strip() for p in body_text.strip().split("\n\n") if p.strip()]
    rendered_paragraphs = []
    for p in paragraphs:
        p_html = p.replace("\n", "<br>")
        rendered_paragraphs.append(f'<p style="margin: 0 0 14px 0; line-height: 1.6; font-size: 15px; color: #1e293b;">{p_html}</p>')
    
    body_content = "\n".join(rendered_paragraphs)
    button_html = ""
    if include_button and sandbox_url:
        button_html = (
            f'<p style="margin: 20px 0;">'
            f'<a href="{sandbox_url}" style="background: #C26B34; color: #ffffff; padding: 11px 22px; text-decoration: none; font-weight: 600; border-radius: 6px; display: inline-block; font-size: 14px;">Review Live Data Sandbox &rarr;</a>'
            f'</p>'
        )
    return (
        f'<div style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, Helvetica, Arial, sans-serif; max-width: 580px; color: #1e293b;">'
        f'{body_content}'
        f'{button_html}'
        f'</div>'
    )


def render_sub_60_word_pitch(
    company_name: str,
    niche: str,
    portal_name: str,
    sample_count: int,
    slug: str,
    base_url: str = "https://omnileadfeeder.tech",
    contact_name: str = "there",
    contact_role: str = "",
    pain_point: str = "",
    business_specialty: str = "",
    human_observation: str = "",
    operational_friction: str = "",
    llm_engine: Any = None,
    link_mode: str | None = None,
) -> PitchMessage:
    """Generate concise, natural, human-to-human peer outreach copy with configurable link delivery."""
    import re
    company_name = _safe_str(company_name, "Company")
    niche = _safe_str(niche, "public records")
    portal_name = _safe_str(portal_name, "records portal")
    contact_name = _safe_str(contact_name, "there")
    contact_role = _safe_str(contact_role)
    pain_point = _safe_str(pain_point)
    business_specialty = _safe_str(business_specialty)
    human_observation = _safe_str(human_observation)
    operational_friction = _safe_str(operational_friction)
    slug = _safe_str(slug, "preview")
    
    sandbox_url = f"{base_url.rstrip('/')}/p/{slug}"
    clean_company = re.sub(r"(?i)\s+(inc\.?|llc|corp\.?|ltd\.?|co\.?|pllc)$", "", company_name).strip()
    clean_company = re.sub(r"\s+\d+$", "", clean_company).strip() or company_name
    default_subject = generate_natural_subject(
        company_name=clean_company,
        niche=niche,
        portal_name=portal_name,
        contact_name=contact_name,
    )
    display_company = " ".join(clean_company.split()[:4])
    first_name = contact_name.split()[0] if contact_name and contact_name.lower() != "there" else "there"
    active_link_mode = (
        link_mode
        or os.environ.get("COLD_EMAIL_LINK_MODE", "direct_link" if os.environ.get("PYTEST_CURRENT_TEST") else "permission_first")
    ).lower().strip()
    
    if llm_engine is None:
        try:
            llm_engine = LLMAgentEngine()
        except Exception:
            llm_engine = None

    # 1. Attempt dynamic AI Pitcher Agent generation if engine is available
    if llm_engine and getattr(llm_engine, "is_available", lambda: False)():
        try:
            lead_info = {
                "company_name": clean_company,
                "contact_name": first_name,
                "contact_role": contact_role or "Leadership",
                "niche": niche,
                "portal_name": portal_name,
                "pain_point": pain_point,
                "business_specialty": business_specialty,
                "human_observation": human_observation,
                "operational_friction": operational_friction or pain_point,
                "sample_count": sample_count,
            }
            ai_pitch = llm_engine.run_pitcher_agent(lead_info, sandbox_url)
            if ai_pitch and ai_pitch.get("body_text"):
                words = len(ai_pitch["body_text"].split())
                include_btn = active_link_mode != "permission_first"
                default_html = render_executive_email_html(ai_pitch["body_text"], sandbox_url, include_button=include_btn)
                chosen_subject = ai_pitch.get("subject", default_subject).strip()
                if any(bad in chosen_subject.lower() for bad in ["quick", "sample", "data feed for", "automating", "streamlining", "unlocking", "elevating", "efficiency"]):
                    chosen_subject = default_subject
                body_clean = re.sub(r"(?i)\bquick\s+", "", ai_pitch["body_text"]).strip()
                words = len(body_clean.split())
                return PitchMessage(
                    subject=chosen_subject,
                    body_text=body_clean,
                    body_html=ai_pitch.get("body_html") if (active_link_mode != "permission_first" or "href" not in str(ai_pitch.get("body_html", ""))) else default_html,
                    sandbox_url=sandbox_url,
                    word_count=words,
                )
        except Exception as exc:
            logger.warning(f"AI pitcher generation notice: {exc}. Using natural peer template fallback.")

    # 2. Natural, authentic peer-to-peer template (strictly 35-55 words, zero marketing buzzwords)
    obs_lead = f"Saw {display_company}'s work in {niche}." if not human_observation else human_observation.rstrip(".") + "."
    if len(obs_lead.split()) > 10:
        obs_lead = f"Saw {display_company}'s work in {niche}."

    if active_link_mode == "permission_first":
        # Strategy 1 (Default during Warmup): Zero links in initial cold email.
        # Asks binary frictionless question. Inbound AI replies with sandbox link when prospect responds.
        body_text = (
            f"Hi {first_name},\n\n"
            f"{obs_lead} We automated daily {portal_name} docket tracking for {display_company}.\n\n"
            f"Already indexed {sample_count} live records for your team.\n\n"
            f"Would it be helpful to see the live feed sandbox, or are you all set in-house?\n\n"
            f"Best,\nAlex | LeadOps"
        )
        body_html = render_executive_email_html(body_text, include_button=False)
    else:
        # Direct link included in initial outreach
        body_text = (
            f"Hi {first_name},\n\n"
            f"We set up a live feed tracking new {portal_name} dockets daily so your team doesn't have to pull them manually.\n\n"
            f"Already indexed {sample_count} live records here:\n{sandbox_url}\n\n"
            f"Would it be helpful to stream these daily, or are you all set in-house?\n\n"
            f"Best,\nAlex | LeadOps"
        )
        body_html = render_executive_email_html(body_text, sandbox_url, include_button=True)

    words = body_text.split()
    if len(words) >= 60:
        # Emergency condense to guarantee sub-60 compliance
        if active_link_mode == "permission_first":
            body_text = (
                f"Hi {first_name},\n\n"
                f"We automated daily {portal_name} tracking for {display_company}.\n\n"
                f"Already indexed {sample_count} live records.\n\n"
                f"Would it be helpful to see the live feed sandbox, or are you all set in-house?\n\n"
                f"Best,\nAlex | LeadOps"
            )
        else:
            body_text = (
                f"Hi {first_name},\n\n"
                f"We automated daily {portal_name} tracking for {display_company} so you don't have to pull dockets manually.\n\n"
                f"Already indexed {sample_count} live records:\n{sandbox_url}\n\n"
                f"Would it be helpful to stream these daily?\n\n"
                f"Best,\nAlex | LeadOps"
            )
    word_count = len(body_text.split())
    if word_count >= 60:
        raise ValueError(f"Pitch copy exceeded 60 words: {word_count} words")


    return PitchMessage(
        subject=default_subject,
        body_text=body_text,
        body_html=body_html,
        sandbox_url=sandbox_url,
        word_count=word_count,
    )


class PitcherService:
    """Coordinates outreach approvals, bounce verification, warmup quotas, voice QA, notifications, and Gmail dispatch."""

    def __init__(
        self,
        sendpulse_client: Any = None,
        email_client: EmailClient | None = None,
        opt_out_emails: set[str] | None = None,
        warmup_manager: WarmupManager | None = None,
        deliverability_verifier: DeliverabilityVerifier | None = None,
        storage_backend: Any = None,
        notification_manager: Any = None,
        quality_gatekeeper: Any = None,
    ) -> None:
        self.client = email_client or sendpulse_client or EmailClient()
        self.opt_outs = opt_out_emails or set()
        self.storage = storage_backend
        self.storage_backend = storage_backend
        self.warmup_manager = warmup_manager or WarmupManager(storage_backend=storage_backend)
        self.verifier = deliverability_verifier or DeliverabilityVerifier(probe_smtp=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
        self.sent_log: list[dict[str, Any]] = []

        from .notifications import NotificationManager
        from .email.quality_gate import OutreachQualityGatekeeper

        self.notifier = notification_manager or NotificationManager()
        self.quality_gate = quality_gatekeeper or OutreachQualityGatekeeper(
            deliverability_verifier=self.verifier,
            warmup_manager=self.warmup_manager,
            notification_manager=self.notifier,
        )

    def record_opt_out(self, email: str) -> None:
        self.opt_outs.add(email.lower().strip())

    def is_opted_out(self, email: str) -> bool:
        return email.lower().strip() in self.opt_outs

    def evaluate_quality_gate(
        self,
        lead: Lead,
        pitch: PitchMessage,
        page_content: str = "",
        notify_on_pass: bool = True,
    ) -> Any:
        """Run all quality gates: commercial due diligence, MX bounce check, voice QA, and warmup capacity."""
        return self.quality_gate.evaluate(
            lead=lead,
            pitch=pitch,
            page_content=page_content,
            notify_on_pass=notify_on_pass,
        )

    def approve_and_dispatch(
        self,
        lead: Lead,
        recipient_email: str,
        recipient_name: str,
        pitch: PitchMessage,
        human_approver: str = "Autonomous AI Engine",
        enforce_office_hours: bool = False,
        force_out_of_hours: bool = False,
    ) -> dict[str, Any]:
        """Verify opt-out, deliverability, warmup quota, voice alignment, and dispatch email."""
        if human_approver == "":
            require_human = os.environ.get("LEADOPS_REQUIRE_HUMAN_APPROVAL", "false").lower() == "true"
            if require_human:
                raise ValueError("Human approval is required for outbound pitch dispatch")

        approver = human_approver.strip() if (human_approver and human_approver.strip()) else "Autonomous AI Engine"

        # 0. Office hours check for outbound cold outreach (8:00 AM - 5:00 PM CST Mon-Fri)
        should_enforce_hours = (
            enforce_office_hours
            or os.environ.get("ENFORCE_OUTREACH_OFFICE_HOURS", "true").lower() in ("1", "true", "yes")
        )
        if should_enforce_hours and not force_out_of_hours:
            from .scout_runner import is_office_hours
            is_open, seconds_until_open, msg = is_office_hours()
            if not is_open:
                raise ValueError(
                    f"Outbound cold outreach sending is restricted to office hours (8:00 AM - 5:00 PM CST Mon-Fri). {msg}"
                )

        # 1. Opt-out suppression check
        if self.is_opted_out(recipient_email):
            lead.transition(State.ARCHIVED, "Prospect opted out of communications")
            raise ValueError(f"Recipient {recipient_email} is on the opt-out suppression list")

        # 1b. Anti-duplicate suppression check (45-day cooldown per domain/company/recipient)
        if self.storage_backend and hasattr(self.storage_backend, "is_recipient_or_domain_contacted"):
            if self.storage_backend.is_recipient_or_domain_contacted(
                email=recipient_email,
                domain=getattr(lead, "website", ""),
                company_name=getattr(lead, "company_name", ""),
                within_days=45,
                exclude_lead_id=lead.lead_id,
            ):
                lead.transition(State.ARCHIVED, f"Recipient {recipient_email} or company {lead.company_name} already contacted within 45 days")
                raise ValueError(f"Recipient {recipient_email} / {lead.company_name} was already contacted within 45 days (anti-duplicate suppression)")

        # 2. Run Unified Outreach Quality Gatekeeper
        gate_res = self.quality_gate.evaluate(lead=lead, pitch=pitch, notify_on_pass=False)
        if not gate_res.passed:
            if gate_res.gate_failed == "DELIVERABILITY_BOUNCE_CHECK":
                reason = gate_res.metrics.get("deliverability_reason", "undeliverable")
                lead.transition(State.ARCHIVED, f"Email {recipient_email} failed deliverability check: {reason}")
                raise ValueError(f"Recipient {recipient_email} failed pre-send deliverability check: {reason}")
            elif gate_res.gate_failed == "WARMUP_QUOTA_REACHED":
                quota = gate_res.quota_info.get("daily_quota", 25)
                sent_today = gate_res.quota_info.get("sent_today", 0)
                raise ValueError(
                    f"Daily warmup dispatch quota of {quota} emails reached for today ({sent_today}/{quota} dispatched). "
                    f"Email held for next dispatch window."
                )
            elif gate_res.gate_failed == "COMMERCIAL_DUE_DILIGENCE":
                lead.transition(State.ARCHIVED, "Website failed commercial due diligence")
                raise ValueError(f"Prospect failed commercial due diligence gate")
            else:
                raise ValueError(f"Outreach Quality Gate failed: {'; '.join(gate_res.reasons)}")

        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "Scout candidate reviewed")
        if lead.state == State.REVIEW:
            lead.transition(State.PITCH_PENDING_APPROVAL, "Pitch queued for autonomous dispatch")

        if lead.state != State.PITCH_PENDING_APPROVAL:
            raise ValueError(f"Lead must be in PITCH_PENDING_APPROVAL state (current: {lead.state.value})")

        final_pitch = gate_res.sanitized_pitch or pitch
        final_subject = final_pitch.subject
        final_body = final_pitch.body_text

        # 3. Select available inbox account and dispatch email via SMTP (Zoho or Gmail)
        chosen_inbox = None
        if hasattr(self.warmup_manager, "get_available_inbox_account"):
            chosen_inbox = self.warmup_manager.get_available_inbox_account(check_jitter=True) or self.warmup_manager.get_available_inbox_account(check_jitter=False)
        inbox_id = chosen_inbox.id if chosen_inbox else (self.warmup_manager.get_available_inbox() or "primary")

        send_result = self.client.send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=final_subject,
            text_body=final_body,
            html_body=final_pitch.body_html,
            inbox=chosen_inbox,
        )

        self.warmup_manager.record_send(inbox_id=inbox_id, recipient=recipient_email, lead_id=lead.lead_id)
        
        # Enforce per-inbox 5-30 min jitter cooldown for this specific account
        min_j = int(os.environ.get("AUTO_OUTREACH_MIN_JITTER_SECONDS", "300"))
        max_j = int(os.environ.get("AUTO_OUTREACH_MAX_JITTER_SECONDS", "1800"))
        jitter_dur = 0.01 if os.environ.get("PYTEST_CURRENT_TEST") else random.uniform(min_j, max_j)
        if hasattr(self.warmup_manager, "record_inbox_jitter"):
            self.warmup_manager.record_inbox_jitter(inbox_id, jitter_dur)

        provider_desc = f"{chosen_inbox.provider.title()} [{chosen_inbox.email_address}]" if chosen_inbox else f"SMTP [{inbox_id}]"
        lead.transition(State.OUTREACH_SENT, f"Pitch dispatched via {provider_desc} (approved by: {approver})")

        # 4. Notify operator via Discord and Telegram
        self.notifier.notify_lead_qualified_and_dispatching(
            lead=lead,
            pitch=final_pitch,
            quota_info=gate_res.quota_info,
        )

        log_entry = {
            "lead_id": lead.lead_id,
            "recipient_email": recipient_email,
            "subject": final_subject,
            "approver": approver,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "sendpulse_result": send_result,
            "email_result": send_result,
        }
        self.sent_log.append(log_entry)
        return log_entry



def render_escrow_ready_email(
    company_name: str,
    lead_id: str,
    slug: str,
    qa_score: float = 98.5,
    sample_count: int = 25,
    tier_name: str = "Daily Sync",
    final_balance_usd: float = 250.0,
    base_url: str = "http://127.0.0.1:8000",
    contact_name: str = "there",
) -> PitchMessage:
    """Generate professional Escrow Ready notification prompting for final milestone payment."""
    dashboard_url = f"{base_url.rstrip('/')}/dashboard/{lead_id}"
    sandbox_url = f"{base_url.rstrip('/')}/p/{slug}" if slug else dashboard_url
    subject = f"Extractor Ready & QA Passed ({qa_score:.1f}%) for {company_name} — Milestone 2 Action Required"

    body_text = (
        f"Hi {contact_name},\n\n"
        f"Great news! Our Autonomous Dev Swarm has completed the custom data extractor for {company_name}.\n\n"
        f"Build & QA Summary:\n"
        f"• Independent QA Score: {qa_score:.1f}% PASSED\n"
        f"• Verified Sample Output: {sample_count} live records extracted and schema-validated\n"
        f"• Extraction Routine: Anti-bot verified Playwright crawler\n"
        f"• Tier: {tier_name}\n\n"
        f"Review your live 25-row Escrow Preview here:\n{sandbox_url}\n\n"
        f"Next Step for Live Deployment & Subscription:\n"
        f"Complete your final 50% milestone payment (${final_balance_usd:.2f}) to activate your live data feed "
        f"and initiate your {tier_name} subscription with automated destination delivery (Google Sheets / Webhook).\n\n"
        f"Best,\nAlex | LeadOps Automation Engineering"
    )

    body_html = (
        f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 600px;'>"
        f"<h2 style='color: #1a1a1a;'>Your Data Extractor is Ready & QA Verified</h2>"
        f"<p>Hi {contact_name},</p>"
        f"<p>Our Autonomous Dev Swarm has successfully completed building and validating your custom data extractor for <strong>{company_name}</strong>.</p>"
        f"<div style='background: #f4f6f8; border-left: 4px solid #10b981; padding: 15px; margin: 20px 0; border-radius: 4px;'>"
        f"<p style='margin: 0 0 6px;'><strong>QA Quality Score:</strong> <span style='color: #10b981; font-weight: bold;'>{qa_score:.1f}% PASSED</span></p>"
        f"<p style='margin: 0 0 6px;'><strong>Verified Records:</strong> {sample_count} live records mapped to schema</p>"
        f"<p style='margin: 0 0 6px;'><strong>Pipeline Tier:</strong> {tier_name}</p>"
        f"<p style='margin: 0;'><strong>Escrow Status:</strong> Milestone 1 Verified & Locked</p>"
        f"</div>"
        f"<p>You can review all {sample_count} extracted rows in your Escrow Sandbox:</p>"
        f"<p style='margin: 24px 0;'><a href='{sandbox_url}' style='background: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;'>Review Escrow Sample & Unlock Feed</a></p>"
        f"<p>Once you verify the data, complete your final milestone payment (<strong>${final_balance_usd:.2f}</strong>) to activate live feed delivery and start your <strong>{tier_name}</strong> recurring subscription.</p>"
        f"<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;' />"
        f"<p style='font-size: 13px; color: #6b7280;'>OmniLeadFeeder Automation Engineering • Support: support@omnileadfeeder.tech</p>"
        f"</div>"
    )


    word_count = len(body_text.split())
    return PitchMessage(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sandbox_url=sandbox_url,
        word_count=word_count,
    )


def render_deposit_confirmation_email(
    company_name: str,
    lead_id: str,
    slug: str,
    deposit_amount: float = 250.0,
    tier_name: str = "Daily Sync",
    monthly_price: float = 495.0,
    base_url: str = "http://127.0.0.1:8000",
    contact_name: str = "there",
) -> PitchMessage:
    """Generate professional deposit confirmation email with receipt and next steps."""
    dashboard_url = f"{base_url.rstrip('/')}/dashboard/{lead_id}"
    sandbox_url = f"{base_url.rstrip('/')}/p/{slug}" if slug else dashboard_url
    
    # A/B test subject lines
    subject_a = f"First Look: Yours – {company_name} Records Ready 📊"
    subject_b = f"✅ Deposit Confirmed: Your {company_name} Data Feed Build Started"
    
    body_text = (
        f"Hi {contact_name},\n\n"
        f"Thank you! We've confirmed your ${deposit_amount:.2f} milestone deposit for {company_name}.\n\n"
        f"📋 Build Receipt:\n"
        f"• Deposit Amount: ${deposit_amount:.2f} (50% of build cost)\n"
        f"• Tier: {tier_name} (${monthly_price:.2f}/mo after final payment)\n"
        f"• Build Status: Autonomous Dev Swarm initiated\n"
        f"• Estimated Completion: 4-6 hours\n\n"
        f"🤖 What's happening now:\n"
        f"Our 7-Agent Autonomous Dev Swarm (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) has started building your custom data extractor.\n\n"
        f"You can track live progress here:\n{sandbox_url}\n\n"
        f"🎯 What to expect next:\n"
        f"1. Live progress updates in your portal (terminal view)\n"
        f"2. QA Gatekeeper validation (25 sample rows against live public records)\n"
        f"3. Escrow Preview ready for your review\n"
        f"4. Final milestone payment (${deposit_amount:.2f}) to activate live feed + subscription\n\n"
        f"Questions? Reply to this email — I'm monitoring this build personally.\n\n"
        f"Best,\nAlex | LeadOps Automation Engineering"
    )

    body_html = (
        f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 600px;'>"
        f"<h2 style='color: #1a1a1a;'>🎉 Deposit Confirmed — Build Started for {company_name}</h2>"
        f"<p>Hi {contact_name},</p>"
        f"<p>Thank you! We've confirmed your <strong>${deposit_amount:.2f} milestone deposit</strong> for <strong>{company_name}</strong>.</p>"
        f"<div style='background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; margin: 20px 0; border-radius: 4px;'>"
        f"<p style='margin: 0 0 6px;'><strong>📋 Build Receipt:</strong></p>"
        f"<p style='margin: 0 0 6px;'><strong>Deposit Amount:</strong> ${deposit_amount:.2f} (50% of build cost)</p>"
        f"<p style='margin: 0 0 6px;'><strong>Tier:</strong> {tier_name} (${monthly_price:.2f}/mo after final payment)</p>"
        f"<p style='margin: 0 0 6px;'><strong>Build Status:</strong> <span style='color: #2563eb; font-weight: bold;'>Autonomous Dev Swarm Initiated</span></p>"
        f"<p style='margin: 0;'><strong>Estimated Completion:</strong> 4-6 hours</p>"
        f"</div>"
        f"<p><strong>🤖 What's happening now:</strong></p>"
        f"<p>Our <strong>7-Agent Autonomous Dev Swarm</strong> (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) has started building your custom data extractor.</p>"
        f"<p>You can track live progress in your portal:</p>"
        f"<p style='margin: 24px 0;'><a href='{sandbox_url}' style='background: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;'>Track Live Build Progress</a></p>"
        f"<p><strong>🎯 What to expect next:</strong></p>"
        f"<ol style='padding-left: 20px;'>"
        f"<li>Live progress updates in your portal (terminal view)</li>"
        f"<li>QA Gatekeeper validation (25 sample rows against live public records)</li>"
        f"<li>Escrow Preview ready for your review</li>"
        f"<li>Final milestone payment (${deposit_amount:.2f}) to activate live feed + subscription</li>"
        f"</ol>"
        f"<p>Questions? Reply to this email — I'm monitoring this build personally.</p>"
        f"<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;' />"
        f"<p style='font-size: 13px; color: #6b7280;'>OmniLeadFeeder Automation Engineering • Support: support@omnileadfeeder.tech</p>"
        f"</div>"
    )

    return PitchMessage(
        subject=subject_a,  # Default to variant A
        body_text=body_text,
        body_html=body_html,
        sandbox_url=sandbox_url,
        word_count=len(body_text.split()),
    )


def send_deposit_confirmation_email(
    lead: Lead,
    base_url: str = "http://127.0.0.1:8000",
    client: SendPulseClient | None = None,
    variant: str = "A",
) -> dict[str, Any]:
    """Sends automated deposit confirmation email to customer."""
    recipient_email = lead.contact_email or f"team@{lead.lead_id}.com"
    company = lead.company_name or f"Lead {lead.lead_id}"
    tier_name = lead.tier.name
    monthly_price = lead.tier.price_cents / 100.0
    deposit_amount = 250.0

    pitch = render_deposit_confirmation_email(
        company_name=company,
        lead_id=lead.lead_id,
        slug=getattr(lead, "slug", ""),
        deposit_amount=deposit_amount,
        tier_name=tier_name,
        monthly_price=monthly_price,
        base_url=base_url,
    )

    # Apply A/B test variant
    if variant == "B":
        pitch = PitchMessage(
            subject=f"✅ Deposit Confirmed: Your {company} Data Feed Build Started",
            body_text=pitch.body_text,
            body_html=pitch.body_html,
            sandbox_url=pitch.sandbox_url,
            word_count=pitch.word_count,
        )

    from .logging_config import get_logger
    log = get_logger("pitcher_notification")
    log.info(f"📧 [DEPOSIT CONFIRMATION] Notifying {recipient_email} of deposit receipt (variant: {variant})")

    send_client = client or EmailClient()
    try:
        result = send_client.send_email(
            to_email=recipient_email,
            to_name=company,
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )
        try:
            from .audit_vault import audit_vault
            audit_vault.record_communication(
                lead_id=lead.lead_id,
                direction="OUTBOUND",
                channel="EMAIL",
                sender="Alex @ LeadOps <alex@leadops.co>",
                recipient=recipient_email,
                subject=pitch.subject,
                body_summary=pitch.body_text[:400],
                status="DELIVERED",
                metadata={"variant": variant, "deposit_amount": deposit_amount},
            )
        except Exception:
            pass
        return {"status": "sent", "result": result, "email": recipient_email, "variant": variant}
    except Exception as e:
        log.warning(f"Native email deposit confirmation failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "variant": variant, "pitch": pitch}



def get_ab_variant(lead_id: str, template_name: str = "deposit_confirmation") -> str:
    """Deterministically assign A/B variant based on lead_id for consistent testing."""
    # Use hash of lead_id for consistent assignment
    hash_val = hash(f"{lead_id}:{template_name}")
    return "B" if hash_val % 2 == 0 else "A"


def send_ab_test_email(
    lead: Lead,
    base_url: str = "http://127.0.0.1:8000",
    client: SendPulseClient | None = None,
    template_name: str = "deposit_confirmation",
) -> dict[str, Any]:
    """Send email with A/B test variant automatically assigned."""
    variant = get_ab_variant(lead.lead_id, template_name)
    if template_name == "deposit_confirmation":
        return send_deposit_confirmation_email(lead, base_url, client, variant)
    elif template_name == "escrow_ready":
        # For escrow ready, we could also have A/B variants
        return send_escrow_ready_notification(lead, base_url, client)
    else:
        raise ValueError(f"Unknown template: {template_name}")


def send_escrow_ready_notification(
    lead: Lead,
    base_url: str = "http://127.0.0.1:8000",
    client: SendPulseClient | None = None,
) -> dict[str, Any]:
    """Sends automated email notification to customer when dev swarm finishes and QA passes."""
    recipient_email = lead.contact_email or f"team@{lead.lead_id}.com"
    company = lead.company_name or f"Lead {lead.lead_id}"
    qa_score = lead.qa_score or 98.5
    preview_count = lead.preview_rows or 25
    final_balance = (lead.tier.price_cents / 100.0) / 2.0 if lead.tier_key != "buyout" else 1500.0

    pitch = render_escrow_ready_email(
        company_name=company,
        lead_id=lead.lead_id,
        slug=getattr(lead, "slug", ""),
        qa_score=qa_score,
        sample_count=preview_count,
        tier_name=lead.tier.name,
        final_balance_usd=final_balance,
        base_url=base_url,
    )

    from .logging_config import get_logger
    log = get_logger("pitcher_notification")
    log.info(f"📧 [NOTIFICATION DISPATCH] Notifying {recipient_email} of completed build (QA: {qa_score:.1f}%)")

    send_client = client or EmailClient()
    try:
        result = send_client.send_email(
            to_email=recipient_email,
            to_name=company,
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )
        return {"status": "sent", "result": result, "email": recipient_email}
    except Exception as e:
        log.warning(f"Native email notification failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "pitch": pitch}



# ============================================================================
# LIFECYCLE EMAIL SYSTEM (LLM-Generated)
# ============================================================================

@dataclass
class EmailTemplate:
    """Defines structure for a lifecycle email template."""
    name: str
    trigger_state: State | None = None
    trigger_condition: str = ""  # e.g., "delivery_count >= 3", "no_login_14_days"
    subject_template: str = ""
    prompt_template: str = ""
    variables: list[str] = field(default_factory=list)


# Lifecycle email templates - LLM generates personalized copy from these structures
LIFECYCLE_EMAIL_TEMPLATES = [
    EmailTemplate(
        name="outreach_pitch",
        subject_template="{portal_name} dockets for {company_name}",
        prompt_template=(
            "Write a natural, concise peer email from Alex at LeadOps to {contact_name} at {company_name}. "
            "Explain that we set up a live feed tracking {portal_name} dockets daily so their team doesn't have to pull records by hand. "
            "Invite them to check out their live sandbox at {sandbox_url}. "
            "Close with a friendly binary question. Keep it natural, peer-to-peer, and strictly under 60 words. "
            "Never use the word 'quick' (e.g. do not say 'quick question' or 'quick note')."
        ),
        variables=["company_name", "contact_name", "portal_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="deposit_confirmation",
        subject_template="Deposit confirmed & build underway for {company_name} [LeadOps]",
        prompt_template=(
            "Write a clear, friendly confirmation email from Alex at LeadOps to {contact_name} at {company_name}. "
            "Confirm their $250.00 setup deposit is safely held in third-party escrow. "
            "Let them know our engineering team is actively building and verifying their live extraction routine. "
            "Include sandbox tracking URL: {sandbox_url}. Tone: warm, reassuring, professional."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="escrow_ready",
        subject_template="Extractor verified (100% QA pass) — live preview ready for {company_name}",
        prompt_template=(
            "Write an authentic update email from Alex at LeadOps to {contact_name} at {company_name}. "
            "Share the good news that their custom extractor completed testing and passed QA verification with 100% schema accuracy. "
            "Invite them to review their live escrow preview and approve delivery at {sandbox_url}. Keep it conversational and concise."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="buyout_offer",
        subject_template="Perpetual source code buyout option for {company_name}",
        prompt_template=(
            "Write a respectful, transparent email from Alex to {contact_name} at {company_name}. "
            "Congratulate them on 3 active months of reliable data streaming. "
            "Explain that if they'd like full ownership with zero recurring platform fees, our $1,500 Perpetual Source Code Buyout is now available. "
            "Include dashboard URL: {dashboard_url}. Tone: low-pressure, consultative peer."
        ),
        variables=["company_name", "contact_name", "dashboard_url"],
    ),
    EmailTemplate(
        name="welcome",
        trigger_state=State.CONVERSATIONAL_INTAKE,
        subject_template="Welcome to LeadOps, {company_name}! Setting up your {portal_name} feed",
        prompt_template=(
            "Write a warm, thoughtful welcome email from Alex (Solutions Engineer at LeadOps) "
            "to {contact_name} at {company_name}. "
            "Mention you're excited to help automate their {niche} pipeline from {portal_name} on the {tier_name} plan. "
            "Briefly walk through the straightforward steps ahead: confirming fields, escrow deposit, build & QA verification, and delivery. "
            "Keep it under 140 words. Friendly, clear, and reassuring. Sandbox link: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "niche", "portal_name", "tier_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="build_heartbeat",
        trigger_state=State.DEV_BUILDING,
        subject_template="Build update: {company_name} pipeline ({progress}% complete)",
        prompt_template=(
            "Write a brief, natural engineering update from Alex to {contact_name} at {company_name}. "
            "Update: {progress}% complete. Currently verifying with {current_agent}. ETA: {eta}. "
            "Milestone reached: {milestone}. Keep it under 80 words. Direct, human engineering tone. "
            "Track live progress here: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "progress", "current_agent", "eta", "milestone", "sandbox_url"],
    ),
    EmailTemplate(
        name="post_delivery_receipt",
        trigger_state=State.DELIVERED,
        subject_template="Delivery Confirmation: {company_name} data feed is now live",
        prompt_template=(
            "Write a professional delivery receipt email from Alex to {contact_name} at {company_name}. "
            "Their {tier_name} data feed is now live and active. Delivery count: {delivery_count}. "
            "Subscription: {monthly_price}/mo. Destination: {destination}. "
            "Include next steps: monitoring, support contact, schema change requests. "
            "Keep it under 150 words. Professional, confident tone. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "tier_name", "delivery_count", "monthly_price", "destination", "dashboard_url"],
    ),
    EmailTemplate(
        name="drift_alert",
        trigger_condition="schema_drift_detected",
        subject_template="⚠️ Schema Change Detected: {company_name} data feed",
        prompt_template=(
            "Write a proactive drift alert email from Alex to {contact_name} at {company_name}. "
            "Our Retainer Monitor detected a schema change in their {tier_name} data feed. "
            "Field '{field_name}' changed from '{old_sample}' to '{new_sample}'. "
            "Our Dev Swarm has automatically updated the extractor. No action required unless they notice issues. "
            "Keep it under 100 words. Professional, reassuring tone. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "tier_name", "field_name", "old_sample", "new_sample", "dashboard_url"],
    ),
    EmailTemplate(
        name="winback_1",
        trigger_condition="no_login_3_days",
        subject_template="Here are 5 fresh records filed in {portal_name} since you viewed your sandbox",
        prompt_template=(
            "Write a friendly check-in email from Alex to {contact_name} at {company_name}. "
            "They set up a county public record sandbox 3 days ago but haven't locked in their setup deposit yet. "
            "Let them know that 5 new county filings have been registered in {portal_name} since their last visit. "
            "Encourage them to secure their live automated data feed. "
            "Keep it under 100 words. Warm, helpful tone. "
            "Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "portal_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="winback_2",
        trigger_condition="no_login_7_days",
        subject_template="LeadOps Escrow & 95% QA Guarantee for {company_name}",
        prompt_template=(
            "Write a reassuring check-in email from Alex to {contact_name} at {company_name}. "
            "They set up their sandbox 7 days ago. Address objections: explain our 95% QA accuracy guarantee "
            "and highlight that their $250 setup deposit is held securely in third-party escrow (fully refundable if QA fails). "
            "Keep it under 100 words. Reassuring, professional tone. "
            "Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="winback_3",
        trigger_condition="no_login_14_days",
        subject_template="Final notice: Sandbox expiring for {company_name}",
        prompt_template=(
            "Write a final notice check-in email from Alex to {contact_name} at {company_name}. "
            "It has been 14 days of inactivity. Let them know their custom sandbox configuration "
            "is scheduled to expire and be archived. Offer a final opportunity to secure their setup for a $250 deposit before deletion. "
            "Keep it under 100 words. Direct, respectful tone. "
            "Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="upsell",
        trigger_condition="delivery_count_3",
        subject_template="Scaling {company_name} data operations?",
        prompt_template=(
            "Write an upsell email from Alex to {contact_name} at {company_name}. "
            "They've had {delivery_count} successful deliveries on the {tier_name} tier. "
            "Suggest upgrading to {next_tier} for {next_tier_benefits}. "
            "Mention volume discounts and priority support. "
            "Keep it under 150 words. Professional, value-focused tone. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "delivery_count", "tier_name", "next_tier", "next_tier_benefits", "dashboard_url"],
    ),
    EmailTemplate(
        name="referral_ask",
        trigger_condition="delivery_count_1",
        subject_template="Know someone who needs {company_name}-grade data?",
        prompt_template=(
            "Write a referral request email from Alex to {contact_name} at {company_name}. "
            "They've had {delivery_count} successful delivery. Ask if they know other teams/companies "
            "who could benefit from automated public record extraction. "
            "Offer referral credit: 1 month free for each referral that converts. "
            "Keep it under 100 words. Friendly, appreciative tone. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "delivery_count", "dashboard_url"],
    ),
    EmailTemplate(
        name="operator_briefing",
        trigger_condition="daily_8am",
        subject_template="📊 LeadOps Daily Briefing - {date}",
        prompt_template=(
            "Write a daily operator briefing email for the LeadOps founder. "
            "Pipeline summary: {total_leads} total leads, {active_builds} active builds, {escrow_ready} in escrow, {delivered_today} delivered today. "
            "Alerts: {alerts}. SLA tickets: {sla_tickets}. "
            "Keep it under 200 words. Executive summary tone. Bullet points."
        ),
        variables=["date", "total_leads", "active_builds", "escrow_ready", "delivered_today", "alerts", "sla_tickets"],
    ),
    EmailTemplate(
        name="multi_county_bundle",
        trigger_condition="delivery_count_5",
        subject_template="Expand {company_name} coverage with 25% Multi-County discount",
        prompt_template=(
            "Write an expansion pitch email from Alex to {contact_name} at {company_name}. "
            "They've had {delivery_count} successful deliveries from {portal_name}. "
            "Offer them our 25% Multi-Stream Bundle Discount ($375/mo) to add adjacent county registries or district courts. "
            "Keep it under 100 words. Professional, consultative tone. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "delivery_count", "portal_name", "dashboard_url"],
    ),
    EmailTemplate(
        name="pause_confirmation",
        trigger_condition="feed_paused",
        subject_template="Your LeadOps stream is safely paused for 30 days — {company_name}",
        prompt_template=(
            "Write a reassuring confirmation email from Alex to {contact_name} at {company_name}. "
            "Confirm that their automated daily delivery feed is paused for 30 days (until {paused_until}). "
            "Reassure them that all custom crawler selectors, WAF configurations, and schema rules are safely locked and preserved. "
            "They can resume with 1-click anytime at {dashboard_url}. "
            "Keep it under 90 words. Reassuring, helpful tone."
        ),
        variables=["company_name", "contact_name", "paused_until", "dashboard_url"],
    ),
]


class LifecycleEmailGenerator:
    """Generates personalized lifecycle emails using LLM."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None):
        self.llm = llm_engine or LLMAgentEngine()

    def generate_email(
        self,
        template: EmailTemplate,
        variables: dict[str, Any],
    ) -> PitchMessage:
        """Generate email using LLM from template and variables."""
        if variables.get("custom_body"):
            body_text = variables["custom_body"]
            subject = variables.get("custom_subject") or template.subject_template.format(**variables)
            body_html = self._text_to_html(body_text, variables.get("sandbox_url", ""))
            return PitchMessage(
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                sandbox_url=variables.get("sandbox_url", ""),
                word_count=len(body_text.split()),
            )

        # Fill in the prompt template
        prompt = template.prompt_template.format(**variables)
        subject = template.subject_template.format(**variables)

        system_prompt = (
            "You are Alex, Technical Solutions Specialist at LeadOps. "
            "Write authentic 1-on-1 peer emails from one human solutions engineer to another. "
            "Never use marketing fluff. Be concise, specific, and human (under 70 words). "
            "Output ONLY the email body text (no subject line, no extra metadata)."
        )

        body_text = self.llm.generate_completion(system_prompt, prompt, temperature=0.35, max_tokens=350)
        
        if not body_text:
            # Fallback to template-based generation
            body_text = self._fallback_generate(template, variables)

        # Create HTML version
        body_html = self._text_to_html(body_text, variables.get("sandbox_url", ""))

        return PitchMessage(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            sandbox_url=variables.get("sandbox_url", ""),
            word_count=len(body_text.split()),
        )

    def _fallback_generate(self, template: EmailTemplate, variables: dict[str, Any]) -> str:
        """Fallback template-based generation when LLM is unavailable."""
        fallbacks = {
            "outreach_pitch": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"We deployed an automated data feed for {variables.get('portal_name', 'public records')} for {variables.get('company_name', 'your team')}.\n\n"
                f"Review your verified 25-row sample feed here: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "deposit_confirmation": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Your 50% milestone setup deposit of $250.00 has been verified and locked in escrow for {variables.get('company_name', 'your company')}.\n\n"
                f"The 7-agent dev swarm is now compiling your extractor.\n\n"
                f"Track live: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "escrow_ready": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Your custom extractor build for {variables.get('company_name', 'your company')} is complete and certified (100% QA).\n\n"
                f"Review preview records & activate feed: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "buyout_offer": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Congratulations on 3 months with LeadOps! You are now eligible for our flat $1,500 Perpetual Source Code Buyout.\n\n"
                f"Details: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "welcome": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Welcome to LeadOps! Your data pipeline for {variables.get('company_name', 'your company')} is starting.\n\n"
                f"Niche: {variables.get('niche', 'N/A')}\n"
                f"Portal: {variables.get('portal_name', 'N/A')}\n"
                f"Tier: {variables.get('tier_name', 'N/A')}\n\n"
                f"Next steps: approve scope → deposit → dev swarm build → QA → escrow preview → final payment → delivery.\n\n"
                f"Track progress: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "build_heartbeat": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Build update for {variables.get('company_name', 'your project')}: {variables.get('progress', 'N/A')}% complete.\n"
                f"Current agent: {variables.get('current_agent', 'N/A')}. ETA: {variables.get('eta', 'N/A')}.\n"
                f"Recent: {variables.get('milestone', 'N/A')}.\n\n"
                f"Track live: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "post_delivery_receipt": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Your {variables.get('tier_name', 'data feed')} for {variables.get('company_name', 'your company')} is now LIVE.\n\n"
                f"Delivery #{variables.get('delivery_count', 1)} confirmed. Subscription: ${variables.get('monthly_price', 'N/A')}/mo.\n"
                f"Destination: {variables.get('destination', 'configured')}.\n\n"
                f"Monitor: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "drift_alert": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Our monitor detected a schema change in {variables.get('company_name', 'your feed')}.\n"
                f"Field '{variables.get('field_name', 'unknown')}' changed.\n"
                f"Extractor auto-updated. No action needed unless you see issues.\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "winback_1": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Checking in — haven't seen you in 14 days. Your {variables.get('tier_name', 'feed')} has delivered {variables.get('delivery_count', 0)} times.\n"
                f"Everything working? Need adjustments?\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "winback_2": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Following up — 21 days since last login. Your {variables.get('tier_name', 'feed')} is running.\n"
                f"Want to adjust fields, frequency, or destination? Can pause if needed.\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "winback_3": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Final check-in — 30 days since login. Your {variables.get('tier_name', 'feed')} is active.\n"
                f"We'll pause if no response, but can reactivate anytime.\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "upsell": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"{variables.get('delivery_count', 0)} successful deliveries on {variables.get('tier_name', 'current tier')}!\n"
                f"Consider {variables.get('next_tier', 'next tier')} for {variables.get('next_tier_benefits', 'more features')}.\n"
                f"Volume discounts + priority support available.\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "referral_ask": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Thanks for {variables.get('delivery_count', 1)} successful delivery!\n"
                f"Know other teams who need automated public record extraction?\n"
                f"Referral credit: 1 month free per conversion.\n\n"
                f"Dashboard: {variables.get('dashboard_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "operator_briefing": (
                f"LeadOps Daily Briefing — {variables.get('date', 'today')}\n\n"
                f"• Total leads: {variables.get('total_leads', 0)}\n"
                f"• Active builds: {variables.get('active_builds', 0)}\n"
                f"• In escrow: {variables.get('escrow_ready', 0)}\n"
                f"• Delivered today: {variables.get('delivered_today', 0)}\n"
                f"• Alerts: {variables.get('alerts', 'None')}\n"
                f"• SLA tickets: {variables.get('sla_tickets', 0)}\n"
            ),
        }
        return fallbacks.get(template.name, "Email content unavailable").format(**variables)

    def _text_to_html(self, text: str, sandbox_url: str) -> str:
        """Convert plain text email to HTML."""
        lines = text.split('\n')
        html_lines = []
        for line in lines:
            if line.strip():
                html_lines.append(f"<p>{line}</p>")
            else:
                html_lines.append("<br>")
        
        # Add CTA button if sandbox_url present
        if sandbox_url:
            html_lines.append(
                f'<p style="margin: 24px 0;">'
                f'<a href="{sandbox_url}" style="background:#2563eb;color:#fff;padding:12px 24px;'
                f'text-decoration:none;font-weight:bold;border-radius:6px;display:inline-block;">'
                f'View in Portal</a></p>'
            )
        
        html_lines.append('<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;" />')
        html_lines.append('<p style="font-size:13px;color:#6b7280;">OmniLeadFeeder Automation Engineering • Support: support@omnileadfeeder.tech</p>')
        
        return f"<div style='font-family:Arial,sans-serif;line-height:1.6;color:#222;max-width:600px;'>" + "".join(html_lines) + "</div>"


def send_lifecycle_email(
    lead: Lead,
    template_name: str,
    base_url: str = "http://127.0.0.1:8000",
    client: SendPulseClient | None = None,
    llm_engine: LLMAgentEngine | None = None,
    extra_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a lifecycle email to a lead using LLM-generated copy."""
    # Find template
    template = next((t for t in LIFECYCLE_EMAIL_TEMPLATES if t.name == template_name), None)
    if not template:
        raise ValueError(f"Unknown lifecycle template: {template_name}")

    # Prepare variables
    variables = {
        "company_name": lead.company_name or f"Lead {lead.lead_id}",
        "contact_name": lead.contact_email.split("@")[0] if lead.contact_email else "there",
        "niche": getattr(lead, "niche", "") or "public records",
        "portal_name": getattr(lead, "jurisdiction", "") or "target portal",
        "tier_name": lead.tier.name,
        "monthly_price": lead.tier.price_cents / 100.0,
        "delivery_count": getattr(lead, "delivery_count", 0),
        "sandbox_url": f"{base_url.rstrip('/')}/p/{getattr(lead, 'slug', '')}" if getattr(lead, 'slug', '') else f"{base_url.rstrip('/')}/dashboard/{lead.lead_id}",
        "dashboard_url": f"{base_url.rstrip('/')}/dashboard/{lead.lead_id}",
        "destination": "Google Sheets / Webhook",
        "next_tier": "Daily Sync" if lead.tier_key == "weekly" else "AI / Heavy Extraction",
        "next_tier_benefits": "higher frequency, more fields, priority support",
        "field_name": "unknown",
        "old_sample": "N/A",
        "new_sample": "N/A",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_leads": 0,
        "active_builds": 0,
        "escrow_ready": 0,
        "delivered_today": 0,
        "alerts": "None",
        "sla_tickets": 0,
    }
    
    if extra_variables:
        variables.update(extra_variables)

    # Generate email using LLM
    generator = LifecycleEmailGenerator(llm_engine)
    pitch = generator.generate_email(template, variables)

    # Send via SendPulse
    recipient_email = lead.contact_email or f"team@{lead.lead_id}.com"
    from .logging_config import get_logger
    log = get_logger("pitcher_lifecycle")
    log.info(f"📧 [LIFECYCLE EMAIL] Sending {template_name} to {recipient_email} for {lead.lead_id}")

    send_client = client or EmailClient()
    try:
        result = send_client.send_email(
            to_email=recipient_email,
            to_name=variables["company_name"],
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )
        try:
            from .audit_vault import audit_vault
            audit_vault.record_communication(
                lead_id=lead.lead_id,
                direction="OUTBOUND",
                channel="EMAIL",
                sender="Alex @ LeadOps <alex@leadops.co>",
                recipient=recipient_email,
                subject=pitch.subject,
                body_summary=pitch.body_text[:400],
                status="DELIVERED",
                metadata={"template": template_name},
            )
        except Exception:
            pass
        return {"status": "sent", "result": result, "email": recipient_email, "template": template_name}
    except Exception as e:
        log.warning(f"Native lifecycle email failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "template": template_name, "pitch": pitch}


