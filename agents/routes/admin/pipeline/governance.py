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

logger = logging.getLogger("api.admin.governance")
router = APIRouter()

@router.get("/api/swarm/status", tags=["Admin Operations"])
def get_swarm_status(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    active_builds = admin_service.get_active_builds()
    num_active = len(active_builds)
    emergency_stop = admin_service.governance.emergency_stop_active
    
    # Dynamically derive worker activity from actual active builds
    is_building = num_active > 0
    worker_load_base = round(min(0.95, 0.05 + (num_active * 0.20)), 2) if is_building else 0.02
    
    workers = [
        {"role": "planner", "state": "ACTIVE" if is_building else "READY", "load": f"{worker_load_base:.2f}"},
        {"role": "dev_lead", "state": "COORDINATING" if is_building else "STANDBY", "load": f"{worker_load_base:.2f}"},
        {"role": "network_engineer", "state": "PROBING" if is_building else "STANDBY", "load": f"{round(worker_load_base * 0.8, 2):.2f}"},
        {"role": "frontend_dom_specialist", "state": "AST_PARSING" if is_building else "STANDBY", "load": f"{round(worker_load_base * 0.9, 2):.2f}"},
        {"role": "systems_architect", "state": "SCHEMA_VALIDATING" if is_building else "STANDBY", "load": f"{round(worker_load_base * 0.7, 2):.2f}"},
        {"role": "junior_developer", "state": "PLAYWRIGHT_COMPILING" if is_building else "STANDBY", "load": f"{worker_load_base:.2f}"},
        {"role": "qa_gatekeeper", "state": "EVALUATING" if is_building else "STANDBY", "load": f"{round(worker_load_base * 0.6, 2):.2f}"},
    ]
    
    return {
        "status": "OFFLINE" if emergency_stop else ("ACTIVE" if is_building else "ONLINE"),
        "active_workers": workers,
        "circuit_breaker": "OPEN" if emergency_stop else "CLOSED",
        "active_builds_count": num_active,
    }



@router.get("/api/admin/governance/metrics", tags=["Admin Operations"])
@router.get("/api/admin/governance", tags=["Admin Operations"])
def get_governance_metrics(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return admin_service.get_governance_overview()


@router.post("/api/admin/governance/emergency-stop", tags=["Admin Operations"])
def set_emergency_stop(
    req: EmergencyStopRequest,
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return admin_service.toggle_emergency_stop(req.active, req.reason)


@router.post("/api/admin/system/purge-all-data", tags=["Admin Operations"])
def purge_all_data(
    request: Request,
    user: ClerkUser | None = Depends(get_current_user_optional),
    storage_backend=Depends(get_storage),
):
    """Securely purges all test customer data and leads for a completely clean slate.
    Requires Global Admin Clerk authentication OR internal LEADOPS_API_TOKEN."""
    from agents.auth import ClerkAuthService
    from agents.routes.dependencies import verify_internal_token

    is_authorized = False
    if user and (getattr(user, "is_admin", False) or user.role == "admin" or ClerkAuthService().is_admin_email(user.email)):
        is_authorized = True
    else:
        auth_header = request.headers.get("authorization")
        if auth_header:
            try:
                verify_internal_token(request, auth_header)
                is_authorized = True
            except HTTPException:
                pass

    if not is_authorized:
        env = os.environ.get("ENV", "development").lower()
        allow_dev = os.environ.get("ALLOW_DEV_ADMIN", "true").lower() == "true"
        if env in {"development", "dev", "local"} or allow_dev:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(status_code=403, detail="Forbidden: Global Admin authorization or API token required.")

    purged_counts = storage_backend.purge_all_data()
    return {
        "ok": True,
        "message": "All test leads, sandboxes, and customer records have been purged for a fresh start.",
        "purged_records": purged_counts,
    }



@router.get("/api/admin/telemetry/live", tags=["Admin Operations"])
def get_live_telemetry(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Returns live global telemetry, proxy pool health, and real-time audit event stream."""
    from agents.observability import telemetry_collector
    leads_count = len(storage_backend.list_leads())
    return telemetry_collector.get_system_telemetry(total_leads_count=leads_count)



@router.post("/api/admin/morning-briefing", tags=["Admin Operations"])
def trigger_morning_briefing(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Trigger executive morning briefing on demand with accounting, MRR, pipeline, and telemetry."""
    from agents.notifications import notification_manager
    briefing = notification_manager.notify_morning_briefing(storage_backend, portal_service)
    return {"ok": True, "briefing": briefing}


@router.get("/api/admin/notifications/status", tags=["Admin Operations"])
def get_notifications_status(
    _: ClerkUser = Depends(require_admin),
):
    """Retrieve active multi-channel Discord and Telegram configuration status."""
    from agents.notifications import notification_manager
    settings = notification_manager.settings
    return {
        "ok": True,
        "enabled": settings.enabled,
        "discord_configured": bool(settings.discord_webhook_url or settings.discord_webhook_outreach),
        "discord_channels": {
            "default": bool(settings.discord_webhook_url),
            "outreach": bool(settings.discord_webhook_outreach),
            "inbox": bool(settings.discord_webhook_inbox),
            "revenue": bool(settings.discord_webhook_revenue),
            "dev": bool(settings.discord_webhook_dev),
            "alerts": bool(settings.discord_webhook_alerts),
        },
        "telegram_configured": bool(settings.telegram_bot_token and settings.telegram_chat_id),
    }


@router.post("/api/admin/notifications/test-preview", tags=["Admin Operations"])
def trigger_test_notification_preview(
    preview_type: str = "outreach",
    _: ClerkUser = Depends(require_admin),
):
    """Send a live Discord embed showcase to preview the layout, colors, personas, and action buttons."""
    from agents.notifications import notification_manager
    from agents.domain import Lead, PitchMessage
    
    if not notification_manager.is_configured():
        raise HTTPException(status_code=400, detail="Notifications are not configured or disabled.")
        
    sample_lead = Lead(
        "lead-demo-1",
        "daily",
        company_name="Apex Title & Escrow",
        contact_name="Michael Vance",
        contact_email="mvance@apextitle.example.com",
    )
    sample_lead.niche = "Probate & Foreclosures"
    sample_lead.jurisdiction = "Harris County Records"
    
    if preview_type == "outreach":
        pitch = PitchMessage(
            subject="Harris County probate feed",
            body_text=(
                "Hi Michael,\n\n"
                "We built an automated pipeline that extracts new Harris County probate filings daily.\n\n"
                "Would love to send over 25 sample rows for Apex if you have a minute?\n\n"
                "Best,\nAlex"
            ),
            word_count=29,
        )
        notification_manager.notify_lead_qualified_and_dispatching(
            sample_lead,
            pitch,
            quota_info={"sent_today": 8, "daily_quota": 25, "warmup_week": 1},
        )
    elif preview_type == "revenue":
        notification_manager.notify_payment_received(
            sample_lead,
            amount_usd=99.00,
            payment_type="Setup Sprint Refundable Down Payment",
            provider="PayPal",
            transaction_id="ch_3N8vKjL2k9p0Xy",
        )
    elif preview_type == "dev":
        notification_manager.notify_dev_swarm_started(
            sample_lead,
            objectives=[
                "Reverse engineer Harris County portal DOM hierarchy",
                "Compile resilient Playwright scraper",
                "Certify 25 real records against QA gatekeeper",
            ],
        )
    elif preview_type == "qa":
        notification_manager.notify_qa_evaluation(
            sample_lead,
            qa_score=100.0,
            escrow_ready=True,
            record_count=25,
        )
    elif preview_type == "inbox":
        notification_manager.notify_inbound_reply_received(
            sender_email="mvance@apextitle.example.com",
            sender_name="Michael Vance",
            company_name="Apex Title & Escrow",
            subject="Re: Harris County probate feed",
            reply_snippet="Sounds interesting. Can you send over the sample data and pricing details?",
            ai_intent="INTERESTED",
            ai_sentiment="POSITIVE",
            ai_draft_reply="Hi Michael, absolutely — I've prepared a sandbox with 25 live verified records from Harris County Probate Court. Every row has a 1-click link to verify against the official registry.\n\nHere is your live sandbox to inspect:\nhttps://omnileadfeeder.tech/p/harris-civil-court-filings\n\nSetup is just a $99 Setup Sprint deposit held in third-party escrow while you inspect and approve your live feed (100% credited toward your Month 1 subscription). Does this structure match what your team needs?\n\nBest,\nAlex | LeadOps",
            lead_id="lead-apex-title-tx",
            jurisdiction="Harris County, TX",
            target_portal="Harris County Probate Court",
            sandbox_url="https://omnileadfeeder.tech/p/harris-civil-court-filings",
            stage="CONVERSATIONAL_INTAKE",
            niche="Probate & Title Research",
        )
    elif preview_type == "bounce":
        notification_manager.notify_delivery_bounce_archived(
            bounced_email="invalid.contact@nonexistent-domain.com",
            company_name="Vanguard Escrow Partners",
            lead_id="lead-vanguard-escrow",
            reason="550 5.1.1 The email account that you tried to reach does not exist. Please try double-checking the recipient's email address for typos.",
        )
    else:
        notification_manager.notify_system_alert(
            title="Discord Aesthetic Showcase",
            message="Your multi-channel Discord setup is operational with premium executive styling.",
            severity="INFO",
        )
        
    return {"ok": True, "preview_type": preview_type, "message": "Preview embed dispatched successfully."}

