from __future__ import annotations

import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel

from agents.auth import ClerkUser, require_admin, get_current_user_optional
from agents.models import Ticket, TicketStatus, TicketPriority, TicketType, CancellationRequest, CancellationStatus
from agents.domain import State, PaymentEvent, Lead
from agents.routes.dependencies import (
    get_storage,
    get_portal_service,
    get_dashboard_service,
    get_admin_service,
)
from ..models import *

logger = logging.getLogger("api.admin.mobile")
router = APIRouter()

@router.get("/api/admin/quick-action", tags=["Admin Mobile Controls"], response_class=HTMLResponse)
def handle_mobile_quick_action(
    request: Request,
    action: str,
    token: str,
    lead_id: Optional[str] = "",
    storage_backend=Depends(get_storage),
):
    """Handle 1-click mobile operator approvals and commands dispatched from Telegram or Discord."""
    from agents.auth import verify_mobile_action_token
    from agents.domain import State, PaymentEvent
    from agents.notifications import notification_manager

    clean_lead_id = (lead_id or "").strip()
    if not verify_mobile_action_token(token, action, clean_lead_id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Invalid or expired mobile authorization token."
        )

    action_lower = action.lower().strip()
    title = "Action Processed"
    description = f"Action '{action}' executed successfully."
    badge_color = "#10B981"  # Emerald default
    status_icon = "✓"

    lead = None
    if clean_lead_id:
        lead = storage_backend.get_lead(clean_lead_id)
        if not lead:
            # Fallback search by slug
            leads = storage_backend.list_leads()
            lead = next((l for l in leads if l.slug == clean_lead_id or l.lead_id == clean_lead_id), None)

    if action_lower in ("approve_pitch", "send_immediately"):
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {clean_lead_id}")

        # Cancel any pending auto-outreach grace timer
        try:
            from agents.auto_outreach import auto_outreach_scheduler
            auto_outreach_scheduler.cancel_dispatch(clean_lead_id, reason="Operator manual mobile dispatch triggered")
        except Exception as e:
            logger.debug(f"Auto-outreach cancel note: {e}")

        from agents.pitcher import PitcherService, PitchMessage, render_sub_60_word_pitch
        pitch = None
        slug = getattr(lead, "slug", "") or lead.lead_id
        if getattr(lead, "outreach_subject", "") and getattr(lead, "outreach_body", ""):
            pitch = PitchMessage(
                subject=lead.outreach_subject,
                body_text=lead.outreach_body,
                body_html=getattr(lead, "outreach_html", "") or f"<p>{lead.outreach_body}</p>",
                sandbox_url=f"https://www.omnileadfeeder.tech/p/{slug}",
                word_count=len((getattr(lead, "outreach_body", "") or "").split()),
            )
        else:
            company = lead.company_name or "Partner"
            pitch = render_sub_60_word_pitch(
                company_name=company,
                niche=getattr(lead, "niche", "Public Records") or "Public Records",
                portal_name=getattr(lead, "target_portal_name", "Official Records Portal") or "Official Records Portal",
                sample_count=4,
                slug=slug,
                contact_name=(getattr(lead, "contact_name", "") or "there").split()[0],
                contact_role=getattr(lead, "contact_role", ""),
            )
            lead.outreach_subject = pitch.subject
            lead.outreach_body = pitch.body_text
            lead.outreach_html = pitch.body_html
            storage_backend.save_lead(lead)

        email = (lead.contact_email or "").strip()
        if not email or "@" not in email:
            title = "Dispatch Halted: Missing Email"
            description = f"Cannot dispatch outreach for <b>{lead.company_name}</b>: No valid recipient email address on file."
            status_icon = "⚠️"
            badge_color = "#F59E0B"
        else:
            from agents.scout_runner import is_office_hours
            is_open, seconds_until_open, msg = is_office_hours()
            force_now = (action_lower == "send_immediately")

            if not is_open and not force_now:
                from agents.auto_outreach import auto_outreach_scheduler
                auto_outreach_scheduler.schedule_lead_for_dispatch(lead, pitch, storage_backend)
                lead.audit_log.append({
                    "from": lead.state.value,
                    "to": lead.state.value,
                    "reason": f"Pitch approved by mobile operator; queued for office hours dispatch at 8:00 AM CST ({msg})",
                })
                storage_backend.save_lead(lead)
                title = "🌙 Pitch Approved — Scheduled for Office Hours"
                description = (
                    f"Cold outreach pitch for <b>{lead.company_name}</b> ({email}) is approved!<br><br>"
                    f"Outbound cold email sending is kept strictly to office hours (8:00 AM - 5:00 PM CST Mon-Fri).<br><br>"
                    f"This email is safely queued and will automatically dispatch at <b>8:00 AM CST</b> with anti-spam jitter."
                )
                status_icon = "⏱️"
                badge_color = "#3B82F6"
                notification_manager.notify_system_alert(
                    "📱 Mobile Pitch Approved (Queued for Office Hours)",
                    f"Founder approved cold outreach for {lead.company_name} ({email}). Queued for 8:00 AM CST office hours dispatch.",
                    severity="INFO",
                )
            else:
                pitcher = PitcherService(storage_backend=storage_backend)
                try:
                    pitcher.approve_and_dispatch(
                        lead=lead,
                        recipient_email=email,
                        recipient_name=lead.contact_name or lead.company_name,
                        pitch=pitch,
                        human_approver="Founder (Mobile Action)",
                        force_out_of_hours=force_now,
                    )
                    storage_backend.save_lead(lead)
                    title = "Outreach Pitch Approved & Dispatched"
                    description = f"Cold outreach pitch for <b>{lead.company_name}</b> ({email}) has been approved and dispatched via native SMTP.<br><br><b>Subject:</b> <i>{pitch.subject}</i>"
                    status_icon = "🚀"
                    badge_color = "#10B981"
                    notification_manager.notify_system_alert(
                        "📱 Mobile Pitch Approved",
                        f"Founder approved cold outreach for {lead.company_name} ({email}) from mobile.",
                        severity="INFO",
                    )
                except Exception as send_err:
                    logger.warning(f"Error during mobile pitch dispatch for {lead.lead_id}: {send_err}")
                    title = "Dispatch Blocked by Quality Gate"
                    description = f"Could not dispatch email for <b>{lead.company_name}</b> ({email}):<br><br><code>{str(send_err)}</code>"
                    status_icon = "⚠️"
                    badge_color = "#EF4444"

    elif action_lower in ("reject_pitch", "cancel_auto_outreach"):
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {clean_lead_id}")

        # Cancel background auto-dispatch timer
        try:
            from agents.auto_outreach import auto_outreach_scheduler
            auto_outreach_scheduler.cancel_dispatch(clean_lead_id, reason="Operator cancelled via mobile link")
        except Exception as e:
            logger.debug(f"Auto-outreach cancel note: {e}")

        lead.state = State.ARCHIVED
        lead.audit_log.append({
            "from": State.PITCH_PENDING_APPROVAL.value,
            "to": State.ARCHIVED.value,
            "reason": "Operator cancelled outreach via mobile action",
            "at": datetime.now(timezone.utc).isoformat(),
        })
        storage_backend.save_lead(lead)
        title = "Outreach Cancelled & Pitch Archived"
        description = f"Outreach for <b>{lead.company_name}</b> ({lead.contact_email}) has been cancelled. No emails will be sent."
        status_icon = "🛑"
        badge_color = "#EF4444"

    elif action_lower == "approve_delivery":
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {clean_lead_id}")
        if getattr(lead, "paypal_vault_id", "") and not lead.final_paid:
            try:
                from agents.billing.paypal_http import PayPalHttpClient
                from agents.billing.paypal_checkout import PayPalCheckout
                checkout = PayPalCheckout.from_environment(PayPalHttpClient())
                checkout.capture_final_milestone_vault(lead)
            except Exception as e:
                logger.warning(f"Manual vault capture notice: {e}")
        lead.transition(State.DELIVERED, "Manual 1-click mobile approval by founder")
        lead.record_payment(PaymentEvent.FINAL_PAID)
        lead.record_payment(PaymentEvent.SUBSCRIPTION_ACTIVE)
        storage_backend.save_lead(lead)
        title = "Live Feed Delivery & Milestone Approved"
        tier_price = (lead.tier.price_cents / 100.0) if getattr(lead, "tier", None) else 250.0
        deposit_usd = float(getattr(lead, "deposit_amount_usd", 99.0) or 99.0)
        final_bal = max(0.0, tier_price - deposit_usd) if getattr(lead, "tier_key", "") != "buyout" else 1500.0
        description = f"Delivery confirmed for <b>{lead.company_name}</b>. Final ${final_bal:.2f} captured and ongoing subscription activated."
        status_icon = "🎉"
        badge_color = "#10B981"

    elif action_lower == "confirm_cancellation":
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {clean_lead_id}")
        lead.subscription_active = False
        storage_backend.save_lead(lead)
        title = "Subscription Cancellation Confirmed"
        description = f"Subscription for <b>{lead.company_name}</b> has been cancelled. Automated billing halted."
        status_icon = "🛑"
        badge_color = "#EF4444"

    elif action_lower == "pause_subscription":
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {clean_lead_id}")
        lead.is_paused = True
        storage_backend.save_lead(lead)
        title = "30-Day Courtesy Pause Granted"
        description = f"Account for <b>{lead.company_name}</b> paused for 30 days without churn."
        status_icon = "⏸️"
        badge_color = "#F59E0B"

    elif action_lower == "pause_prospector":
        os.environ["PROSPECTOR_PAUSED"] = "true"
        title = "Autonomous Prospector Swarm Paused"
        description = "Background continuous prospecting has been paused. No new outreach or sandboxes will be created until resumed."
        status_icon = "⏸️"
        badge_color = "#F59E0B"

    elif action_lower == "resume_prospector":
        os.environ["PROSPECTOR_PAUSED"] = "false"
        title = "Autonomous Prospector Swarm Resumed"
        description = "Continuous prospecting swarm is active and running randomized 30-60 minute discovery cycles."
        status_icon = "▶️"
        badge_color = "#10B981"

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported mobile quick-action: {action}")

    # Return JSON if requested by programmatic client
    if "application/json" in request.headers.get("accept", "").lower():
        return JSONResponse({
            "ok": True,
            "action": action_lower,
            "lead_id": clean_lead_id,
            "title": title,
            "description": description,
        })

    # Mobile-friendly Dark-Mode Executive Confirmation Card
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} • LeadOps</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0B1110;
      color: #E6EAE8;
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}
    .card {{
      background: #141E1C;
      border: 1px solid #233530;
      border-radius: 16px;
      padding: 32px 24px;
      max-width: 440px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }}
    .icon-badge {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: {badge_color}22;
      border: 2px solid {badge_color};
      color: {badge_color};
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: 22px;
      font-weight: 700;
      margin-bottom: 12px;
      color: #FFFFFF;
      letter-spacing: -0.02em;
    }}
    p {{
      font-size: 15px;
      color: #94A3B8;
      line-height: 1.5;
      margin-bottom: 28px;
    }}
    .btn {{
      display: block;
      background: #10B981;
      color: #0B1110;
      font-weight: 600;
      font-size: 15px;
      padding: 14px 20px;
      border-radius: 10px;
      text-decoration: none;
      transition: background 0.2s ease;
    }}
    .btn:hover {{ background: #059669; }}
    .footer {{
      margin-top: 20px;
      font-size: 12px;
      color: #64748B;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-badge">{status_icon}</div>
    <h1>{title}</h1>
    <p>{description}</p>
    <a href="/admin" class="btn">Open Mission Control</a>
    <div class="footer">LeadOps Autonomous Swarm • Mobile Controller</div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html)

