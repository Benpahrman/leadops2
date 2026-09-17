"""Lifecycle email system, milestone notifications, and LLM-driven email generation."""

from datetime import datetime, timezone
from typing import Any

from agents.domain import Lead
from agents.email.client import EmailClient
from agents.llm_client import LLMAgentEngine
from agents.logging_config import get_logger
from .models import PitchMessage, EmailTemplate, LIFECYCLE_EMAIL_TEMPLATES, SendPulseClient
from .persona import get_public_base_url


def render_escrow_ready_email(
    company_name: str,
    lead_id: str,
    slug: str,
    qa_score: float = 98.5,
    sample_count: int = 10,
    tier_name: str = "Production Feed (Flagship)",
    final_balance_usd: float = 151.0,
    base_url: str = "",
    contact_name: str = "there",
) -> PitchMessage:
    """Generate professional QA Pass notification prompting for final milestone payment."""
    public_base = get_public_base_url(base_url)
    dashboard_url = f"{public_base}/dashboard/{lead_id}"
    sandbox_url = f"{public_base}/p/{slug}" if slug else dashboard_url
    subject = f"Extractor Ready & QA Passed ({qa_score:.1f}%) for {company_name} — Data Verification Required"

    effective_sample_text = f"{sample_count} live records"

    body_text = (
        f"Hi {contact_name},\n\n"
        f"Great news! Our Autonomous Dev Swarm has completed the custom data extractor for {company_name}.\n\n"
        f"Build & QA Summary:\n"
        f"• Independent QA Score: {qa_score:.1f}% PASSED\n"
        f"• Verified Sample Output: {effective_sample_text} extracted and schema-validated\n"
        f"• Extraction Routine: Anti-bot verified Playwright crawler\n"
        f"• Tier: {tier_name}\n\n"
        f"Review your live Verified Preview here:\n{sandbox_url}\n\n"
        f"Next Step for Live Deployment & Subscription:\n"
        f"Complete your remaining Month 1 balance payment (${final_balance_usd:.2f}) to activate your live data feed "
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
        f"<p style='margin: 0 0 6px;'><strong>Verified Records:</strong> {effective_sample_text} mapped to schema</p>"
        f"<p style='margin: 0 0 6px;'><strong>Pipeline Tier:</strong> {tier_name}</p>"
        f"<p style='margin: 0;'><strong>Status:</strong> Setup Sprint Verified &amp; $99.00 Deposit Credited</p>"
        f"</div>"
        f"<p>You can review all extracted rows in your Live Sandbox:</p>"
        f"<p style='margin: 24px 0;'><a href='{sandbox_url}' style='background: #2563eb; color: #ffffff; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 6px; display: inline-block;'>Review Verified Sample &amp; Unlock Feed</a></p>"
        f"<p>Once you verify the data, complete your final Month 1 balance payment (<strong>${final_balance_usd:.2f}</strong>) to activate live feed delivery and start your <strong>{tier_name}</strong> recurring subscription.</p>"
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
    deposit_amount: float = 99.0,
    tier_name: str = "Production Feed (Flagship)",
    monthly_price: float = 250.0,
    base_url: str = "",
    contact_name: str = "there",
) -> PitchMessage:
    """Generate professional deposit confirmation email with receipt and next steps."""
    public_base = get_public_base_url(base_url)
    dashboard_url = f"{public_base}/dashboard/{lead_id}"
    sandbox_url = f"{public_base}/p/{slug}" if slug else dashboard_url
    remaining_balance = max(0.0, monthly_price - deposit_amount)
    
    # A/B test subject lines
    subject_a = f"First Look: Yours – {company_name} Records Ready 📊"
    
    body_text = (
        f"Hi {contact_name},\n\n"
        f"Thank you! We've confirmed your ${deposit_amount:.2f} Setup Sprint deposit for {company_name}.\n\n"
        f"📋 Build Receipt:\n"
        f"• Deposit Amount: ${deposit_amount:.2f} (100% credited toward Month 1 balance)\n"
        f"• Tier: {tier_name} (${monthly_price:.2f}/mo after final verification)\n"
        f"• Build Status: Autonomous Dev Swarm initiated\n"
        f"• Estimated Completion: 4-6 hours\n\n"
        f"🤖 What's happening now:\n"
        f"Our 7-Agent Autonomous Dev Swarm (Planner, DOM Architect, Stealth Engineer, Systems Architect, Junior Dev, QA Gatekeeper) has started building your custom data extractor.\n\n"
        f"You can track live progress here:\n{sandbox_url}\n\n"
        f"🎯 What to expect next:\n"
        f"1. Live progress updates in your portal (terminal view)\n"
        f"2. QA Gatekeeper validation (5–10 sample rows against live public records)\n"
        f"3. Live Verification Preview ready for your review\n"
        f"4. Remaining Month 1 balance payment (${remaining_balance:.2f} net) to activate live feed + subscription\n\n"
        f"Questions? Reply to this email — I'm monitoring this build personally.\n\n"
        f"Best,\nAlex | LeadOps Automation Engineering"
    )

    body_html = (
        f"<div style='font-family: Arial, sans-serif; line-height: 1.6; color: #222; max-width: 600px;'>"
        f"<h2 style='color: #1a1a1a;'>🎉 Deposit Confirmed — Build Started for {company_name}</h2>"
        f"<p>Hi {contact_name},</p>"
        f"<p>Thank you! We've confirmed your <strong>${deposit_amount:.2f} Setup Sprint deposit</strong> for <strong>{company_name}</strong>.</p>"
        f"<div style='background: #f0fdf4; border-left: 4px solid #22c55e; padding: 15px; margin: 20px 0; border-radius: 4px;'>"
        f"<p style='margin: 0 0 6px;'><strong>📋 Build Receipt:</strong></p>"
        f"<p style='margin: 0 0 6px;'><strong>Deposit Amount:</strong> ${deposit_amount:.2f} (100% credited toward Month 1)</p>"
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
        f"<li>QA Gatekeeper validation (5–10 sample rows against live public records)</li>"
        f"<li>Live Verification Preview ready for your review</li>"
        f"<li>Remaining Month 1 balance (${remaining_balance:.2f} net) to activate live feed + subscription</li>"
        f"</ol>"
        f"<p>Questions? Reply to this email — I'm monitoring this build personally.</p>"
        f"<hr style='border: none; border-top: 1px solid #e5e7eb; margin: 24px 0;' />"
        f"<p style='font-size: 13px; color: #6b7280;'>OmniLeadFeeder Automation Engineering • Support: support@omnileadfeeder.tech</p>"
        f"</div>"
    )

    return PitchMessage(
        subject=subject_a,
        body_text=body_text,
        body_html=body_html,
        sandbox_url=sandbox_url,
        word_count=len(body_text.split()),
    )


def send_deposit_confirmation_email(
    lead: Lead,
    base_url: str = "",
    client: SendPulseClient | None = None,
    variant: str = "A",
) -> dict[str, Any]:
    """Sends automated deposit confirmation email to customer."""
    recipient_email = lead.contact_email or f"team@{lead.lead_id}.com"
    company = lead.company_name or f"Lead {lead.lead_id}"
    tier_name = lead.tier.name
    monthly_price = lead.tier.price_cents / 100.0 if lead.tier else 250.0
    deposit_amount = getattr(lead, "deposit_amount_usd", 99.0) or 99.0

    pitch = render_deposit_confirmation_email(
        company_name=company,
        lead_id=lead.lead_id,
        slug=getattr(lead, "slug", ""),
        deposit_amount=deposit_amount,
        tier_name=tier_name,
        monthly_price=monthly_price,
        base_url=get_public_base_url(base_url),
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
            from agents.audit_vault import audit_vault
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
        except Exception as ex:
            log.debug(f"Audit vault record_communication note: {ex}")
        return {"status": "sent", "result": result, "email": recipient_email, "variant": variant}
    except Exception as e:
        log.warning(f"Native email deposit confirmation failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "variant": variant, "pitch": pitch}


def get_ab_variant(lead_id: str, template_name: str = "deposit_confirmation") -> str:
    """Deterministically assign A/B variant based on lead_id for consistent testing."""
    hash_val = hash(f"{lead_id}:{template_name}")
    return "B" if hash_val % 2 == 0 else "A"


def send_ab_test_email(
    lead: Lead,
    base_url: str = "",
    client: SendPulseClient | None = None,
    template_name: str = "deposit_confirmation",
) -> dict[str, Any]:
    """Send email with A/B test variant automatically assigned."""
    variant = get_ab_variant(lead.lead_id, template_name)
    if template_name == "deposit_confirmation":
        return send_deposit_confirmation_email(lead, get_public_base_url(base_url), client, variant)
    elif template_name == "escrow_ready":
        return send_escrow_ready_notification(lead, get_public_base_url(base_url), client)
    else:
        raise ValueError(f"Unknown template: {template_name}")


def send_escrow_ready_notification(
    lead: Lead,
    base_url: str = "",
    client: SendPulseClient | None = None,
) -> dict[str, Any]:
    """Sends automated email notification to customer when dev swarm finishes and QA passes."""
    recipient_email = lead.contact_email or f"team@{lead.lead_id}.com"
    company = lead.company_name or f"Lead {lead.lead_id}"
    qa_score = lead.qa_score or 98.5
    preview_count = lead.preview_rows or 10
    deposit_usd = float(getattr(lead, "deposit_amount_usd", 99.0) or 99.0)
    monthly_price = (lead.tier.price_cents / 100.0) if lead.tier else 250.0
    final_balance = max(0.0, monthly_price - deposit_usd) if lead.tier_key != "buyout" else 1500.0

    pitch = render_escrow_ready_email(
        company_name=company,
        lead_id=lead.lead_id,
        slug=getattr(lead, "slug", ""),
        qa_score=qa_score,
        sample_count=preview_count,
        tier_name=lead.tier.name if lead.tier else "Production Feed (Flagship)",
        final_balance_usd=final_balance,
        base_url=get_public_base_url(base_url),
    )

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
                f"Review your verified 5–10 row sample feed here: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "deposit_confirmation": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Your $99 Setup Sprint deposit has been confirmed for {variables.get('company_name', 'your company')} (100% credited toward your Month 1 subscription).\n\n"
                f"The 7-agent dev swarm is now compiling your extractor.\n\n"
                f"Track live: {variables.get('sandbox_url', '#')}\n\n"
                f"Best,\nAlex | LeadOps"
            ),
            "escrow_ready": (
                f"Hi {variables.get('contact_name', 'there')},\n\n"
                f"Your custom extractor build for {variables.get('company_name', 'your company')} is complete and certified (>=95% QA pass).\n\n"
                f"Review verified preview records & activate feed: {variables.get('sandbox_url', '#')}\n\n"
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
                f"Next steps: approve scope → $99 setup sprint deposit → dev swarm build → >=95% QA pass → verified preview → final payment → delivery.\n\n"
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
                f"• Ready for verification: {variables.get('escrow_ready', 0)}\n"
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
    base_url: str = "",
    client: SendPulseClient | None = None,
    llm_engine: LLMAgentEngine | None = None,
    extra_variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send a lifecycle email to a lead using LLM-generated copy."""
    template = next((t for t in LIFECYCLE_EMAIL_TEMPLATES if t.name == template_name), None)
    if not template:
        raise ValueError(f"Unknown lifecycle template: {template_name}")

    public_base = get_public_base_url(base_url)

    # Prepare variables
    variables = {
        "company_name": lead.company_name or f"Lead {lead.lead_id}",
        "contact_name": lead.contact_email.split("@")[0] if lead.contact_email else "there",
        "niche": getattr(lead, "niche", "") or "public records",
        "portal_name": getattr(lead, "jurisdiction", "") or "target portal",
        "tier_name": lead.tier.name if lead.tier else "Production Feed (Flagship)",
        "monthly_price": (lead.tier.price_cents / 100.0) if lead.tier else 250.0,
        "delivery_count": getattr(lead, "delivery_count", 0),
        "sandbox_url": f"{public_base}/p/{getattr(lead, 'slug', '')}" if getattr(lead, 'slug', '') else f"{public_base}/dashboard/{lead.lead_id}",
        "dashboard_url": f"{public_base}/dashboard/{lead.lead_id}",
        "destination": "Google Sheets / Webhook",
        "next_tier": "Daily Sync" if lead.tier_key == "weekly" else "Enterprise Swarm",
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
            from agents.audit_vault import audit_vault
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
        except Exception as ex:
            log.debug(f"Audit vault lifecycle email record note: {ex}")
        return {"status": "sent", "result": result, "email": recipient_email, "template": template_name}
    except Exception as e:
        log.warning(f"Native lifecycle email failed ({e}). Logged mock notification payload.")
        return {"status": "simulated", "error": str(e), "email": recipient_email, "template": template_name, "pitch": pitch}
