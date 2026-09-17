"""Domain models and email template definitions for the Pitcher module."""

from dataclasses import dataclass, field
from typing import Any

from agents.domain import State
from agents.email.config import EmailSettings
from agents.email.client import EmailClient

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
LIFECYCLE_EMAIL_TEMPLATES: list[EmailTemplate] = [
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
        subject_template="Down payment confirmed & build underway for {company_name} [LeadOps]",
        prompt_template=(
            "Write a clear, friendly confirmation email from Alex at LeadOps to {contact_name} at {company_name}. "
            "Confirm their $99.00 refundable setup down payment is safely received (100% credited toward Month 1). "
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
            "Invite them to review their live customer preview and approve delivery at {sandbox_url}. Keep it conversational and concise."
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
        subject_template="LeadOps 100% Refundable Deposit & 95% QA Guarantee for {company_name}",
        prompt_template=(
            "Write a reassuring check-in email from Alex to {contact_name} at {company_name}. "
            "They set up their sandbox 7 days ago. Address objections: explain our 95% QA accuracy guarantee "
            "and highlight that their $99 setup sprint down payment is 100% refundable if QA fails, and 100% credited to Month 1. "
            "Never use confusing escrow terminology. Keep it under 100 words. Reassuring, professional tone. "
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
            "is scheduled to expire and be archived. Offer a final opportunity to secure their setup for a $99 deposit before deletion. "
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
    EmailTemplate(
        name="abandoned_sandbox",
        trigger_condition="sandbox_viewed_24h_no_checkout",
        subject_template="Still looking at those {jurisdiction} {niche} records?",
        prompt_template=(
            "Write a friendly, specific follow-up email from Alex to {contact_name} at {company_name}. "
            "They viewed their live data preview sandbox for {niche} records from {jurisdiction} but haven't "
            "started the checkout process. Let them know new filings have been added since their last visit. "
            "Offer to walk them through the delivery setup in 5 minutes. "
            "Keep it under 80 words. Warm, helpful, specific tone. "
            "Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "niche", "jurisdiction", "sandbox_url"],
    ),
    EmailTemplate(
        name="cart_abandonment",
        trigger_condition="checkout_initiated_2h_no_capture",
        subject_template="Your {jurisdiction} data feed is ready for setup — just one step left",
        prompt_template=(
            "Write a reassuring follow-up email from Alex to {contact_name} at {company_name}. "
            "They started the checkout process for their {niche} data pipeline from {jurisdiction} "
            "but didn't complete payment. Reassure them: the $99 Setup Sprint down payment is 100% credited to Month 1, "
            "and 100% refundable if our extractor doesn't meet 95% QA accuracy within 24 hours. Zero risk. "
            "Never use confusing escrow terminology. Keep it under 90 words. Reassuring, low-pressure tone. "
            "Include sandbox URL: {sandbox_url}."
        ),
        variables=["company_name", "contact_name", "niche", "jurisdiction", "sandbox_url"],
    ),
]
