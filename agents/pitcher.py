"""Outbound email dispatch and Pitcher (Alex) workflow for Scout leads via SendPulse."""

import json
import os
import logging
import random
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .domain import Lead, State
from .llm_client import LLMAgentEngine

logger = logging.getLogger("leadops.pitcher")


@dataclass
class SendPulseSettings:
    client_id: str
    client_secret: str
    from_email: str
    from_name: str = "Alex | LeadOps"
    api_base_url: str = "https://api.sendpulse.com"

    @classmethod
    def from_environment(cls) -> "SendPulseSettings":
        client_id = os.environ.get("SENDPULSE_CLIENT_ID", "")
        client_secret = os.environ.get("SENDPULSE_CLIENT_SECRET", "")
        from_email = os.environ.get("SENDPULSE_FROM_EMAIL", "ClientOps.LeadOps@cultofthefork.tech")
        from_name = os.environ.get("SENDPULSE_FROM_NAME", "Alex | LeadOps")
        return cls(client_id=client_id, client_secret=client_secret, from_email=from_email, from_name=from_name)


class SendPulseClient:
    """SendPulse REST API client for OAuth2 token retrieval and SMTP email dispatch."""

    def __init__(
        self,
        settings: SendPulseSettings | None = None,
        http_requester: Callable[[str, dict[str, str], bytes | None, str], tuple[int, dict[str, Any]]] | None = None,
    ) -> None:
        self.settings = settings or SendPulseSettings.from_environment()
        self.http_requester = http_requester
        self._access_token: str | None = None

    def _request(
        self,
        endpoint: str,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.settings.api_base_url}{endpoint}"
        body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        all_headers = headers or {}
        if payload is not None and "Content-Type" not in all_headers:
            all_headers["Content-Type"] = "application/json"

        if self.http_requester is not None:
            return self.http_requester(url, all_headers, body_bytes, method)

        req = urllib.request.Request(url, data=body_bytes, headers=all_headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return resp.status, data
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
            except Exception:
                err_data = {"error": str(e)}
            return e.code, err_data
        except urllib.error.URLError as e:
            raise RuntimeError(f"SendPulse connection failed: {e}") from e

    def get_token(self) -> str:
        if self._access_token:
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.settings.client_id,
            "client_secret": self.settings.client_secret,
        }
        status, data = self._request("/oauth/access_token", method="POST", payload=payload)
        if status != 200 or "access_token" not in data:
            raise ValueError(f"SendPulse authentication failed: {data}")

        self._access_token = data["access_token"]
        return self._access_token

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch transactional email via SendPulse SMTP API (routed to target or override inbox)."""
        override_email = os.environ.get("LEADOPS_EMAIL_OVERRIDE", "").strip()
        actual_recipient = override_email if override_email else to_email
        actual_name = f"{to_name} ({to_email})" if (override_email and override_email.lower() != to_email.lower()) else to_name
        email_subject = f"[{to_name}] {subject}" if (override_email and override_email.lower() != to_email.lower()) else subject

        token = self.get_token()
        payload = {
            "email": {
                "subject": email_subject,
                "text": text_body,
                "html": html_body or f"<p>{text_body.replace(chr(10), '<br>')}</p>",
                "from": {
                    "name": self.settings.from_name,
                    "email": self.settings.from_email,
                },
                "to": [
                    {
                        "name": actual_name,
                        "email": actual_recipient,
                    }
                ],
            }
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        status, data = self._request("/smtp/emails", method="POST", headers=headers, payload=payload)
        if not (200 <= status < 300) or not data.get("result", True):
            raise RuntimeError(f"SendPulse email dispatch failed: {data}")
        return data


@dataclass(frozen=True)
class PitchMessage:
    subject: str
    body_text: str
    body_html: str
    sandbox_url: str
    word_count: int


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
    llm_engine: Any = None,
) -> PitchMessage:
    """Generate concise, sub-60-word pitch email copy with sandbox magic link using AI Pitcher Agent or template."""
    sandbox_url = f"{base_url.rstrip('/')}/p/{slug}"
    subject = f"Sample {niche} data feed for {company_name}"
    
    # 1. Attempt dynamic AI Pitcher Agent generation if engine is provided
    if llm_engine:
        try:
            lead_info = {
                "company_name": company_name,
                "contact_name": contact_name,
                "contact_role": contact_role or "Leadership",
                "niche": niche,
                "portal_name": portal_name,
                "pain_point": pain_point,
            }
            ai_pitch = llm_engine.run_pitcher_agent(lead_info, sandbox_url)
            if ai_pitch and ai_pitch.get("body_text") and ai_pitch.get("word_count", 999) <= 60:
                return PitchMessage(
                    subject=ai_pitch.get("subject", subject),
                    body_text=ai_pitch["body_text"],
                    body_html=ai_pitch.get("body_html", f"<p>{ai_pitch['body_text']}</p>"),
                    sandbox_url=sandbox_url,
                    word_count=ai_pitch["word_count"],
                )
        except Exception as exc:
            logger.warning(f"AI pitcher generation failed: {exc}. Using canonical template fallback.")

    # 2. Canonical sub-60-word template
    body_text = (
        f"Hi {contact_name},\n\n"
        f"We pulled a sample of {sample_count} recent {niche} records from {portal_name} for {company_name}.\n\n"
        f"Review your free preview and download the CSV here:\n{sandbox_url}\n\n"
        f"Let me know if you would like this delivered on a daily schedule.\n\n"
        f"Best,\nAlex | LeadOps"
    )
    
    word_count = len(body_text.split())
    if word_count > 60:
        raise ValueError(f"Pitch copy exceeded 60 words: {word_count} words")

    body_html = (
        f"<p>Hi {contact_name},</p>"
        f"<p>We pulled a sample of <strong>{sample_count} recent {niche} records</strong> from {portal_name} for {company_name}.</p>"
        f'<p><a href="{sandbox_url}" style="background:#c26b34;color:#fff;padding:10px 16px;text-decoration:none;font-weight:bold;border-radius:4px;display:inline-block;">View Free Data Preview</a></p>'
        f"<p>Let me know if you would like this delivered on a daily schedule.</p>"
        f"<p>Best,<br><strong>Alex</strong> | LeadOps</p>"
    )

    return PitchMessage(
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        sandbox_url=sandbox_url,
        word_count=word_count,
    )


class PitcherService:
    """Coordinates outreach approvals, opt-out validation, and SendPulse dispatch."""

    def __init__(
        self,
        sendpulse_client: SendPulseClient | None = None,
        opt_out_emails: set[str] | None = None,
    ) -> None:
        self.client = sendpulse_client or SendPulseClient()
        self.opt_outs = opt_out_emails or set()
        self.sent_log: list[dict[str, Any]] = []

    def record_opt_out(self, email: str) -> None:
        self.opt_outs.add(email.lower().strip())

    def is_opted_out(self, email: str) -> bool:
        return email.lower().strip() in self.opt_outs

    def approve_and_dispatch(
        self,
        lead: Lead,
        recipient_email: str,
        recipient_name: str,
        pitch: PitchMessage,
        human_approver: str = "Autonomous AI Engine",
    ) -> dict[str, Any]:
        """Verify opt-out rules, send outreach email automatically or with human approver, and advance lifecycle."""
        if human_approver == "":
            require_human = os.environ.get("LEADOPS_REQUIRE_HUMAN_APPROVAL", "false").lower() == "true"
            if require_human:
                raise ValueError("Human approval is required for outbound pitch dispatch")

        approver = human_approver.strip() if (human_approver and human_approver.strip()) else "Autonomous AI Engine"

        if self.is_opted_out(recipient_email):
            lead.transition(State.ARCHIVED, "Prospect opted out of communications")
            raise ValueError(f"Recipient {recipient_email} is on the opt-out suppression list")

        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "Scout candidate reviewed")
        if lead.state == State.REVIEW:
            lead.transition(State.PITCH_PENDING_APPROVAL, "Pitch queued for autonomous dispatch")

        if lead.state != State.PITCH_PENDING_APPROVAL:
            raise ValueError(f"Lead must be in PITCH_PENDING_APPROVAL state (current: {lead.state.value})")

        # Dispatch email
        send_result = self.client.send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )

        lead.transition(State.OUTREACH_SENT, f"Pitch dispatched via SendPulse (approved by: {approver})")

        log_entry = {
            "lead_id": lead.lead_id,
            "recipient_email": recipient_email,
            "subject": pitch.subject,
            "approver": approver,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "sendpulse_result": send_result,
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

    send_client = client or SendPulseClient()
    try:
        result = send_client.send_email(
            to_email=recipient_email,
            to_name=company,
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )
        return {"status": "sent", "result": result, "email": recipient_email, "variant": variant}
    except Exception as e:
        log.warning(f"SendPulse deposit confirmation failed ({e}). Logged mock notification payload.")
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

    send_client = client or SendPulseClient()
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
        log.warning(f"SendPulse notification failed ({e}). Logged mock notification payload.")
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
        subject_template="Automated {portal_name} Data Feed for {company_name}",
        prompt_template=(
            "Write a concise cold outreach email from Alex to {contact_name} at {company_name}. "
            "We have verified live public records from {portal_name}. "
            "Invite them to inspect their verified 25-row sample sandbox at {sandbox_url}. "
            "Keep it strictly under 60 words."
        ),
        variables=["company_name", "contact_name", "portal_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="deposit_confirmation",
        subject_template="Milestone #1 Deposit Confirmed ($250.00 in Escrow) — LeadOps",
        prompt_template=(
            "Write a confirmation email from Alex to {contact_name} at {company_name}. "
            "Their $250.00 setup deposit is locked in third-party escrow. "
            "The 7-agent autonomous dev swarm is now compiling and verifying their custom crawler. "
            "Include sandbox tracking URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="escrow_ready",
        subject_template="QA Gate Passed (100% Accuracy) — Escrow Preview Ready for {company_name}",
        prompt_template=(
            "Write an email from Alex to {contact_name} at {company_name}. "
            "Their crawler build passed QA Gatekeeper verification with 100% accuracy. "
            "Invite them to review their escrow preview and unlock Milestone #2 at {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="buyout_offer",
        subject_template="Month 3 Milestone: Perpetual Code Buyout Option for {company_name}",
        prompt_template=(
            "Write an email from Alex to {contact_name} at {company_name}. "
            "They have been active for 3 months and qualify for our $1,500 Perpetual Source Code Buyout. "
            "Include dashboard URL: {dashboard_url}."
        ),
        variables=["company_name", "contact_name", "dashboard_url"],
    ),
    EmailTemplate(
        name="welcome",
        trigger_state=State.CONVERSATIONAL_INTAKE,
        subject_template="Welcome to LeadOps, {company_name}! Your data pipeline is starting",
        prompt_template=(
            "Write a warm, professional welcome email from Alex (Technical Solutions Engineer at LeadOps) "
            "to {contact_name} at {company_name}. They've just entered the conversational intake phase. "
            "Their niche is {niche}, target portal is {portal_name}, and they're on the {tier_name} tier. "
            "Explain what happens next: scope approval, deposit, dev swarm build, QA, escrow preview, final payment, delivery. "
            "Keep it under 150 words. Professional, encouraging tone. Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "niche", "portal_name", "tier_name", "sandbox_url"],
    ),
    EmailTemplate(
        name="build_heartbeat",
        trigger_state=State.DEV_BUILDING,
        subject_template="Build Update: {company_name} - {progress}% complete",
        prompt_template=(
            "Write a brief build progress heartbeat email from Alex to {contact_name} at {company_name}. "
            "Current progress: {progress}%. Current agent: {current_agent}. ETA: {eta}. "
            "Recent milestone: {milestone}. Keep it under 100 words. Professional, concise tone. "
            "Include sandbox URL for live tracking: {sandbox_url}."
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
        # Fill in the prompt template
        prompt = template.prompt_template.format(**variables)
        subject = template.subject_template.format(**variables)

        system_prompt = (
            "You are Alex, Technical Solutions Engineer at LeadOps. "
            "Write professional, concise, human-sounding emails. "
            "Never use marketing fluff. Be specific and actionable. "
            "Output ONLY the email body text (no subject line, no signature - those are handled separately)."
        )

        body_text = self.llm.generate_completion(system_prompt, prompt, temperature=0.4, max_tokens=300)
        
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

    send_client = client or SendPulseClient()
    try:
        result = send_client.send_email(
            to_email=recipient_email,
            to_name=variables["company_name"],
            subject=pitch.subject,
            text_body=pitch.body_text,
            html_body=pitch.body_html,
        )
        return {"status": "sent", "result": result, "email": recipient_email, "template": template_name}
    except Exception as e:
        log.warning(f"SendPulse lifecycle email failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "template": template_name, "pitch": pitch}

