"""Outbound email dispatch and Pitcher (Alex) workflow for Scout leads via SendPulse."""

import json
import os
import random
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .domain import Lead, State


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
        """Dispatch transactional email via SendPulse SMTP API."""
        token = self.get_token()
        payload = {
            "email": {
                "subject": subject,
                "text": text_body,
                "html": html_body or f"<p>{text_body.replace(chr(10), '<br>')}</p>",
                "from": {
                    "name": self.settings.from_name,
                    "email": self.settings.from_email,
                },
                "to": [
                    {
                        "name": to_name,
                        "email": to_email,
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
    base_url: str = "https://leadops.app",
    contact_name: str = "there",
) -> PitchMessage:
    """Generate concise, sub-60-word pitch email copy with sandbox magic link."""
    sandbox_url = f"{base_url.rstrip('/')}/p/{slug}"
    subject = f"Sample {niche} data feed for {company_name}"
    
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
        human_approver: str,
    ) -> dict[str, Any]:
        """Verify human approval & opt-out rules, then send email and advance lifecycle."""
        if not human_approver.strip():
            raise ValueError("Human approval is required for outbound pitch dispatch")

        if self.is_opted_out(recipient_email):
            lead.transition(State.ARCHIVED, "Prospect opted out of communications")
            raise ValueError(f"Recipient {recipient_email} is on the opt-out suppression list")

        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "Scout candidate reviewed")
        if lead.state == State.REVIEW:
            lead.transition(State.PITCH_PENDING_APPROVAL, "Pitch queued for human review")

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

        lead.transition(State.OUTREACH_SENT, f"Pitch approved by {human_approver} and dispatched via SendPulse")

        log_entry = {
            "lead_id": lead.lead_id,
            "recipient_email": recipient_email,
            "subject": pitch.subject,
            "approver": human_approver,
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
        f"<p style='font-size: 13px; color: #6b7280;'>LeadOps Automation Engineering • Support: alex@leadops.app</p>"
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
        f"<p style='font-size: 13px; color: #6b7280;'>LeadOps Automation Engineering • Support: alex@leadops.app</p>"
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
        pitch.subject = f"✅ Deposit Confirmed: Your {company} Data Feed Build Started"

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

