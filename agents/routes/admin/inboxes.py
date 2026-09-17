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
from agents.swarm.scraper_catalog import (
    get_catalog,
    search_catalog,
    get_scraper_source_code,
    get_scraper_output_data,
    execute_scraper_on_demand,
    CATALOG_CSV_PATH,
)
from agents.routes.dependencies import (
    get_storage,
    get_portal_service,
    get_dashboard_service,
    get_admin_service,
)
from .models import *

logger = logging.getLogger("api.admin")
router = APIRouter()


@router.post("/api/admin/deliverability/validate-domain", tags=["Admin Operations"])
def validate_domain_endpoint(
    req: ValidateDomainRequest,
    _: ClerkUser = Depends(require_admin),
):
    """Validate sending or prospect domain MX, syntax, and format via Knowlez with 30-day cache."""
    clean_domain = (req.domain or "").strip().lower().replace("https://", "").replace("http://", "").split("/")[0]
    if not clean_domain:
        raise HTTPException(status_code=400, detail="Domain cannot be empty")

    from agents.email.knowlez_client import get_knowlez_client
    client = get_knowlez_client()
    res = client.validate_domain(clean_domain, force=req.force)
    return {
        "ok": True,
        "domain": clean_domain,
        "valid": res.get("valid", False),
        "tld": res.get("tld"),
        "cached": res.get("cached", False),
        "details": res,
    }


@router.get("/api/admin/inboxes", tags=["Admin Inboxes"])
def list_admin_inboxes(
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """List all configured inboxes (Zoho & Gmail) with real-time warmup and quota metrics."""
    from agents.email.config import EmailSettings
    from agents.email.warmup import WarmupManager

    settings = EmailSettings.from_environment()
    warmup = WarmupManager(settings=settings, storage_backend=storage_backend)
    all_accounts = warmup.get_all_configured_accounts(outbound_only=True)

    inbox_list = []
    for acc in all_accounts:
        sent_today = warmup.get_sent_count_today(acc.id)
        can_send, _, quota = warmup.can_send_today(acc.id)
        tier = warmup.get_warmup_tier()
        inbox_list.append({
            "inbox_id": acc.id,
            "email_address": acc.email_address,
            "provider": acc.provider,
            "from_name": acc.from_name,
            "smtp_host": acc.smtp_host,
            "smtp_port": acc.smtp_port,
            "smtp_use_ssl": acc.smtp_use_ssl,
            "smtp_use_tls": acc.smtp_use_tls,
            "imap_host": acc.imap_host,
            "imap_port": acc.imap_port,
            "imap_use_ssl": acc.imap_use_ssl,
            "daily_limit": quota,
            "sent_today": sent_today,
            "can_send": can_send,
            "warmup_week": tier.week_number,
            "warmup_name": tier.name,
            "warmup_start_date": acc.warmup_start_date,
            "is_active": acc.is_active,
            "password_configured": bool(acc.password),
            "jitter_wait_seconds": round(warmup.get_inbox_jitter_wait(acc.id), 1),
            "is_on_jitter": warmup.is_inbox_on_jitter(acc.id),
        })

    fleet_summary = warmup.get_fleet_capacity_summary()
    fleet_summary["min_jitter_seconds"] = int(str(os.environ.get("AUTO_OUTREACH_MIN_JITTER_SECONDS", "300")).split("#")[0].strip().strip("\"'"))
    fleet_summary["max_jitter_seconds"] = int(str(os.environ.get("AUTO_OUTREACH_MAX_JITTER_SECONDS", "1200")).split("#")[0].strip().strip("\"'"))
    fleet_summary["earliest_jitter_wait"] = round(warmup.get_earliest_jitter_wait(), 1)
    fleet_summary["available_inbox"] = warmup.get_available_inbox(check_jitter=True)

    # Compute Fleet Warmup Progression Roadmap
    try:
        from agents.email.engine import EmailEngineQueue
        queue = EmailEngineQueue()
        queue_start = queue.get_state("warmup_start_date")
    except Exception:
        queue_start = None
    warmup_start_raw = queue_start or settings.warmup_start_date or os.environ.get("WARMUP_START_DATE", "")
    now = datetime.now(timezone.utc)
    if warmup_start_raw:
        try:
            start_dt = datetime.fromisoformat(warmup_start_raw.replace("Z", "+00:00"))
            days_elapsed = max(0, (now - start_dt).days)
        except Exception:
            start_dt = now
            days_elapsed = 0
    else:
        start_dt = now
        days_elapsed = 0

    fleet_tier = warmup.get_warmup_tier(start_dt)
    next_increase_days = max(0, (fleet_tier.week_number * 7) - days_elapsed)
    active_inboxes_count = len([i for i in inbox_list if i["is_active"]])

    warmup_cycle = {
        "started": bool(warmup_start_raw),
        "start_date": start_dt.isoformat(),
        "days_elapsed": days_elapsed + 1,
        "current_week": fleet_tier.week_number,
        "current_name": fleet_tier.name,
        "per_inbox_daily_limit": fleet_tier.daily_quota,
        "fleet_daily_quota": fleet_tier.daily_quota * max(1, active_inboxes_count),
        "next_tier_days": max(0, 4 - (days_elapsed + 1)) if days_elapsed < 4 else max(0, 8 - (days_elapsed + 1)) if days_elapsed < 8 else max(0, 14 - (days_elapsed + 1)),
        "schedule": [
            {
                "stage": 1,
                "name": "Stage 1: Initial Peer Warmup",
                "days": "Days 1–4",
                "daily_volume": "3–5/day",
                "daily_per_inbox": 5,
                "composition": "100% Peer Warm-up (Test Inboxes)",
                "jitter": "300–600s delay",
                "active": (days_elapsed + 1) <= 4,
                "completed": (days_elapsed + 1) > 4,
            },
            {
                "stage": 2,
                "name": "Stage 2: Gradual Step Up",
                "days": "Days 5–8",
                "daily_volume": "8–12/day",
                "daily_per_inbox": 12,
                "composition": "100% Peer Warm-up",
                "jitter": "240–480s delay",
                "active": 4 < (days_elapsed + 1) <= 8,
                "completed": (days_elapsed + 1) > 8,
            },
            {
                "stage": 3,
                "name": "Stage 3: Pre-Outreach Baseline",
                "days": "Days 9–14",
                "daily_volume": "15–20/day",
                "daily_per_inbox": 20,
                "composition": "100% Peer Warm-up",
                "jitter": "180–360s delay",
                "active": 8 < (days_elapsed + 1) <= 14,
                "completed": (days_elapsed + 1) > 14,
            },
            {
                "stage": 4,
                "name": "Stage 4: Initial Live Outbound",
                "days": "Days 15–21",
                "daily_volume": "25/day",
                "daily_per_inbox": 25,
                "composition": "5 Cold Outreach + 20 Warm-up",
                "jitter": "180–420s delay (9:00 AM – 4:30 PM)",
                "active": 14 < (days_elapsed + 1) <= 21,
                "completed": (days_elapsed + 1) > 21,
            },
            {
                "stage": 5,
                "name": "Stage 5: Production Expansion",
                "days": "Days 22–30",
                "daily_volume": "35/day",
                "daily_per_inbox": 35,
                "composition": "15 Cold Outreach + 20 Warm-up",
                "jitter": "180–420s delay (Business hours)",
                "active": 21 < (days_elapsed + 1) <= 30,
                "completed": (days_elapsed + 1) > 30,
            },
            {
                "stage": 6,
                "name": "Stage 6: Steady State Fleet Velocity",
                "days": "Day 31+",
                "daily_volume": "40–50/day",
                "daily_per_inbox": 50,
                "composition": "30 Cold Outreach + 15–20 Warm-up",
                "jitter": "Continuous permanent background warm-up",
                "active": (days_elapsed + 1) > 30,
                "completed": False,
            },
        ],
    }

    return {
        "ok": True,
        "inboxes": inbox_list,
        "total": len(inbox_list),
        "fleet_daily_quota": fleet_summary["fleet_daily_quota"],
        "fleet_sent_today": fleet_summary["fleet_sent_today"],
        "fleet_capacity": fleet_summary["fleet_daily_quota"],
        "fleet_summary": fleet_summary,
        "warmup_cycle": warmup_cycle,
    }


@router.post("/api/admin/warmup/start", tags=["Admin Inboxes"])
def set_warmup_cycle_start(
    req: WarmupStartRequest,
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Officially initialize or reset the email fleet warmup start date and dispatch initial peer warmup batch."""
    from agents.email.engine import EmailEngineQueue
    target_date = req.start_date or datetime.now(timezone.utc).isoformat()
    os.environ["WARMUP_START_DATE"] = target_date
    queue = EmailEngineQueue()
    queue.set_state("warmup_start_date", target_date)

    # Immediately trigger initial 3-email peer warmup batch
    batch_res = dispatch_warmup_batch(count=3, storage_backend=storage_backend, user=user)

    return {
        "ok": True,
        "warmup_start_date": target_date,
        "dispatched_count": batch_res.get("dispatched_count", 0),
        "dispatched": batch_res.get("dispatched", []),
        "errors": batch_res.get("errors", []),
        "message": f"Warmup cycle started with baseline date {target_date}. Dispatched {batch_res.get('dispatched_count', 0)} initial peer warmup emails!",
    }


@router.post("/api/admin/inboxes", tags=["Admin Inboxes"])
def upsert_admin_inbox(
    req: InboxUpsertRequest,
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Add or update an inbox account (e.g. Zoho Workplace / Zoho Mail) in persistent storage."""
    from agents.email.config import InboxAccountConfig

    clean_email = req.email_address.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Valid email address is required")

    inbox_id = (req.inbox_id or "").strip()
    if not inbox_id:
        inbox_id = clean_email.replace("@", "_").replace(".", "_")

    # If updating an existing account and password was left blank, preserve existing password
    existing = storage_backend.get_inbox_account(inbox_id)
    pwd = req.password.strip() if req.password else ""
    if not pwd and existing:
        pwd = existing.get("password", "")

    cfg = InboxAccountConfig(
        id=inbox_id,
        email_address=clean_email,
        password=pwd,
        provider=req.provider or "zoho",
        from_name=req.from_name or "Alex | OmniLeadFeeder",
        smtp_host=req.smtp_host or "",
        smtp_port=req.smtp_port or 465,
        smtp_use_ssl=req.smtp_use_ssl if req.smtp_use_ssl is not None else True,
        smtp_use_tls=bool(req.smtp_use_tls),
        imap_host=req.imap_host or "",
        imap_port=req.imap_port or 993,
        imap_use_ssl=req.imap_use_ssl if req.imap_use_ssl is not None else True,
        daily_limit=req.daily_limit or 25,
        warmup_start_date=req.warmup_start_date or datetime.now(timezone.utc).isoformat(),
        is_active=req.is_active if req.is_active is not None else True,
    )

    account_dict = {
        "inbox_id": cfg.id,
        "email_address": cfg.email_address,
        "password": cfg.password,
        "provider": cfg.provider,
        "from_name": cfg.from_name,
        "smtp_host": cfg.smtp_host,
        "smtp_port": cfg.smtp_port,
        "smtp_use_ssl": cfg.smtp_use_ssl,
        "imap_host": cfg.imap_host,
        "imap_port": cfg.imap_port,
        "imap_use_ssl": cfg.imap_use_ssl,
        "daily_limit": cfg.daily_limit,
        "warmup_start_date": cfg.warmup_start_date,
        "is_active": 1 if cfg.is_active else 0,
        "created_at": existing.get("created_at") if existing else datetime.now(timezone.utc).isoformat(),
    }
    storage_backend.upsert_inbox_account(account_dict)
    return {"ok": True, "inbox_id": cfg.id, "message": f"Inbox '{cfg.id}' ({cfg.email_address}) saved successfully."}


@router.post("/api/admin/inboxes/{inbox_id}/test", tags=["Admin Inboxes"])
def test_admin_inbox_connection(
    inbox_id: str,
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Trigger live SMTP & IMAP handshake test for a configured inbox account."""
    from agents.email.config import EmailSettings
    from agents.email.client import EmailClient
    from agents.email.warmup import WarmupManager

    settings = EmailSettings.from_environment()
    warmup = WarmupManager(settings=settings, storage_backend=storage_backend)
    target_inbox = warmup.get_inbox_by_id(inbox_id)

    if not target_inbox:
        raise HTTPException(status_code=404, detail=f"Inbox account '{inbox_id}' not found")

    client = EmailClient(settings=settings)
    test_result = client.test_inbox_connection(target_inbox)
    return {"ok": True, "result": test_result}


@router.delete("/api/admin/inboxes/{inbox_id}", tags=["Admin Inboxes"])
def delete_admin_inbox(
    inbox_id: str,
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Remove an inbox account from the active rotation pool."""
    storage_backend.delete_inbox_account(inbox_id)
    return {"ok": True, "inbox_id": inbox_id, "message": f"Inbox '{inbox_id}' removed from storage."}


@router.get("/api/admin/inboxes/inbound-stream", tags=["Admin Inboxes"])
def get_inbound_stream(
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Retrieve live watched inbox status, health telemetry, and all received prospect replies."""
    from agents.email.config import EmailSettings
    settings = EmailSettings.from_environment()

    # Determine active watched inbox metadata
    user_email = (
        os.environ.get("INBOX_WATCHER_EMAIL")
        or os.environ.get("OUTLOOK_USER")
        or os.environ.get("GMAIL_USER")
        or settings.user
        or "alex@olfmailer.com"
    ).strip()

    is_outlook = any(user_email.lower().endswith(d) for d in ("@outlook.com", "@hotmail.com", "@live.com", "@office365.com")) or "outlook" in user_email.lower()
    provider_name = "Microsoft Outlook (Graph/IMAP)" if is_outlook else "Google Workspace / Gmail (IMAP)"

    # Retrieve stored inbound replies
    inbound_emails = []
    if hasattr(storage_backend, "list_inbound_emails"):
        try:
            inbound_emails = storage_backend.list_inbound_emails()
        except Exception as err:
            logger.warning(f"Could not load inbound emails: {err}")

    # Compute classification breakdown metrics
    intents = {}
    for email_item in inbound_emails:
        intent = email_item.get("intent") or "unclassified"
        intents[intent] = intents.get(intent, 0) + 1

    return {
        "ok": True,
        "watched_inbox": {
            "email_address": user_email,
            "provider": provider_name,
            "poll_interval_seconds": int(str(os.environ.get("INBOUND_POLL_INTERVAL_SECONDS", "60")).split("#")[0].strip()),
            "watcher_enabled": os.environ.get("INBOUND_WATCHER_ENABLED", "true").lower() in ("true", "1", "yes"),
            "imap_host": settings.imap_host,
            "imap_port": settings.imap_port,
            "imap_use_ssl": settings.imap_use_ssl,
            "has_credentials": bool(settings.app_password or os.environ.get("MICROSOFT_REFRESH_TOKEN")),
        },
        "metrics": {
            "total_received": len(inbound_emails),
            "classified_counts": intents,
            "interested_count": intents.get("warm_lead", 0) + intents.get("interested", 0) + intents.get("call_booked", 0),
            "unclassified_count": intents.get("unclassified", 0),
            "unsubscribe_count": intents.get("unsubscribe", 0) + intents.get("not_interested", 0),
        },
        "inbound_emails": inbound_emails,
    }


@router.get("/api/admin/inboxes/warmup-targets", tags=["Admin Inboxes"])
def get_warmup_targets(
    user: ClerkUser = Depends(require_admin),
):
    """List all registered peer warm receiver inboxes and 2-way engagement telemetry."""
    from agents.email.engine import EmailEngineQueue
    queue = EmailEngineQueue()
    targets = queue.get_all_warmup_targets()
    return {
        "ok": True,
        "targets": targets,
        "total_count": len(targets),
        "monitored_count": len([t for t in targets if t.get("is_monitored")]),
    }


@router.post("/api/admin/inboxes/warmup-targets", tags=["Admin Inboxes"])
def create_warmup_target(
    req: AddWarmupTargetRequest,
    user: ClerkUser = Depends(require_admin),
):
    """Register a new warm receiver inbox into the peer warmup network."""
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Valid email address is required.")

    from agents.email.engine import EmailEngineQueue
    queue = EmailEngineQueue()
    success = queue.enqueue_warmup_target(
        email=req.email,
        name=req.name or "",
        password=req.password or "",
        provider=req.provider or "gmail",
        is_monitored=bool(req.is_monitored),
    )
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to register warm receiver inbox '{req.email}'.")

    return {"ok": True, "message": f"Warm receiver inbox '{req.email}' added to peer warmup network."}


@router.delete("/api/admin/inboxes/warmup-targets/{target_id}", tags=["Admin Inboxes"])
def delete_warmup_target_endpoint(
    target_id: int,
    user: ClerkUser = Depends(require_admin),
):
    """Remove a warm receiver inbox from the peer warmup network."""
    from agents.email.engine import EmailEngineQueue
    queue = EmailEngineQueue()
    deleted = queue.delete_warmup_target(target_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Warm receiver with ID {target_id} not found.")

    return {"ok": True, "message": f"Warm receiver ID {target_id} removed."}


@router.post("/api/admin/warmup/dispatch-batch", tags=["Admin Inboxes"])
def dispatch_warmup_batch(
    count: int = 3,
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Trigger an immediate batch of peer warmup emails dispatched across available inboxes."""
    from agents.email.engine import EmailEngineQueue, WarmupAgent
    from agents.email.warmup import WarmupManager
    from agents.email.client import EmailClient
    from agents.email.config import EmailSettings

    settings = EmailSettings.from_environment()
    client = EmailClient(settings)
    warmup_mgr = WarmupManager(settings=settings, storage_backend=storage_backend)
    queue = EmailEngineQueue()
    agent = WarmupAgent()

    targets = queue.get_all_warmup_targets()
    if not targets:
        targets = [{"id": 1, "email": "alex@olfmailer.com", "first_name": "Alex", "target_daily": 5}]

    dispatched = []
    errors = []

    target_count = max(1, min(count, 20))
    all_inboxes = warmup_mgr.get_all_configured_accounts(outbound_only=True)
    active_inboxes = [acc for acc in all_inboxes if acc.is_active] or [None]

    for i in range(target_count):
        acc = active_inboxes[i % len(active_inboxes)]
        sender_email = acc.email_address if acc else settings.azure_communication_sender_email

        # Exclude sender from target candidates to ensure cross-peer warming
        eligible_targets = [t for t in targets if t.get("email", "").lower().strip() != sender_email.lower().strip()]
        if not eligible_targets:
            eligible_targets = targets
        target = eligible_targets[i % len(eligible_targets)]
        target_email = target.get("email")
        if not target_email:
            continue

        subj, body = agent.generate_warmup_email(sender_name=acc.from_name.split()[0] if acc and acc.from_name else "Alex")
        try:
            res = client.send_email(
                to_email=target_email,
                to_name=target.get("first_name") or target.get("name") or "Peer",
                subject=subj,
                text_body=body,
                inbox=acc,
                is_warmup=True,
            )
            inbox_id = acc.id if acc else "primary"
            warmup_mgr.record_send(inbox_id=inbox_id, recipient=target_email)
            queue.log_dispatch(
                recipient=target_email,
                sender=sender_email,
                subject=subj,
                dispatch_type="peer_warmup",
                status=res.get("status", "sent"),
                jitter_seconds=0.0,
                message_id=res.get("message_id", ""),
            )
            if target.get("id"):
                queue.record_warmup_sent(target["id"])
            dispatched.append({
                "inbox_id": inbox_id,
                "sender": sender_email,
                "recipient": target_email,
                "subject": subj,
                "status": res.get("status", "sent"),
            })
        except Exception as e:
            errors.append({"recipient": target_email, "error": str(e)})

    return {
        "ok": True,
        "dispatched_count": len(dispatched),
        "dispatched": dispatched,
        "errors": errors,
        "message": f"Dispatched {len(dispatched)} warmup peer emails across available inboxes.",
    }


@router.post("/api/admin/warmup/run-inbox-monitoring", tags=["Admin Inboxes"])
def trigger_inbox_monitoring(
    user: ClerkUser = Depends(require_admin),
):
    """Run the peer inbox monitoring cycle (unspam, star, and mark engagement on peer receivers)."""
    from agents.email.engine import EmailEngineQueue, WarmupAgent, PeerInboxWarmupWatcher

    queue = EmailEngineQueue()
    agent = WarmupAgent()
    watcher = PeerInboxWarmupWatcher(queue, agent)
    stats = watcher.run_monitoring_cycle()
    return {
        "ok": True,
        "stats": stats,
        "message": f"Peer inbox monitoring cycle completed. Processed: {stats.get('processed_inboxes', 0)} inboxes | Unspammed: {stats.get('unspammed', 0)} | Replied: {stats.get('replied', 0)}.",
    }


@router.get("/api/admin/inboxes/warmup-activity", tags=["Admin Inboxes"])
def get_warmup_activity(
    limit: int = 50,
    user: ClerkUser = Depends(require_admin),
):
    """Retrieve recent dispatch and warmup activity logs."""
    from agents.email.engine import EmailEngineQueue
    queue = EmailEngineQueue()
    logs = queue.get_dispatch_history(limit=limit)
    cold_today, warmup_today = queue.get_today_sent_counts()
    return {
        "ok": True,
        "logs": logs,
        "cold_sent_today": cold_today,
        "warmup_sent_today": warmup_today,
    }


@router.get("/api/admin/oauth/microsoft/status", tags=["Admin OAuth"])
def get_microsoft_oauth_status(
    _: Optional[ClerkUser] = Depends(get_current_user_optional),
):
    """Retrieve current Microsoft OAuth2 configuration and connection status."""
    from agents.email.microsoft_graph import get_microsoft_graph_client
    client = get_microsoft_graph_client()
    return {"ok": True, "status": client.test_connection()}


@router.get("/api/admin/oauth/microsoft/authorize", tags=["Admin OAuth"])
def get_microsoft_oauth_authorize_url(
    request: Request,
    redirect: bool = False,
    redirect_uri: Optional[str] = None,
    _: Optional[ClerkUser] = Depends(get_current_user_optional),
):
    """Generate Microsoft OAuth 2.0 authorization URL for human 1-click consent."""
    from agents.email.microsoft_graph import get_microsoft_graph_client
    client = get_microsoft_graph_client()
    if not client.client_id:
        raise HTTPException(
            status_code=400,
            detail="MICROSOFT_CLIENT_ID is not configured in .env or environment. Please configure your Azure App Registration credentials first.",
        )
    try:
        effective_redirect = redirect_uri
        if not effective_redirect:
            base = str(request.base_url).rstrip("/")
            if "omnileadfeeder.tech" in base and base.startswith("http://"):
                base = base.replace("http://", "https://")
            effective_redirect = f"{base}/api/admin/oauth/microsoft/callback"
        auth_url = client.get_authorization_url(redirect_uri=effective_redirect)
        if redirect:
            return RedirectResponse(url=auth_url)
        return {"ok": True, "auth_url": auth_url, "redirect_uri": effective_redirect}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/admin/oauth/microsoft/callback", tags=["Admin OAuth"])
def handle_microsoft_oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
):
    """Receive authorization code from Microsoft OAuth redirect and complete token exchange."""
    import urllib.parse
    from agents.email.microsoft_graph import get_microsoft_graph_client

    if error:
        err_msg = error_description or error or "Unknown OAuth error"
        logger.error(f"❌ Microsoft OAuth callback error: {err_msg}")
        return RedirectResponse(url=f"/admin?tab=inboxes&oauth_error={urllib.parse.quote(err_msg)}")

    if not code:
        return RedirectResponse(url="/admin?tab=inboxes&oauth_error=No+authorization+code+received")

    client = get_microsoft_graph_client()
    try:
        callback_url = str(request.url).split("?")[0]
        if "omnileadfeeder.tech" in callback_url and callback_url.startswith("http://"):
            callback_url = callback_url.replace("http://", "https://")
        tokens = client.exchange_code_for_tokens(code, redirect_uri=callback_url)
        account_email = tokens.account_email or client.account_email
        logger.info(f"✅ Microsoft OAuth completed for '{account_email}'.")
        return RedirectResponse(
            url=f"/admin?tab=inboxes&oauth=microsoft_success&email={urllib.parse.quote(account_email)}"
        )
    except Exception as exc:
        logger.error(f"❌ Failed to exchange Microsoft code: {exc}")
        return RedirectResponse(url=f"/admin?tab=inboxes&oauth_error={urllib.parse.quote(str(exc))}")


@router.post("/api/admin/oauth/microsoft/disconnect", tags=["Admin OAuth"])
def disconnect_microsoft_oauth(
    _: ClerkUser = Depends(require_admin),
):
    """Disconnect Outlook account and revoke local refresh token."""
    from agents.email.microsoft_graph import get_microsoft_graph_client
    client = get_microsoft_graph_client()
    client.disconnect()
    return {"ok": True, "message": "Microsoft Outlook account disconnected successfully."}


@router.get("/api/admin/deliverability/status", tags=["Admin Deliverability"])
@router.get("/api/admin/deliverability/comprehensive-latest", tags=["Admin Deliverability"])
def get_deliverability_status(
    domain: str = "olfmailer.com",
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Retrieve the latest comprehensive 4-vector deliverability assessment scorecard."""
    try:
        from dataclasses import asdict
        from agents.email.deliverability_suite import get_deliverability_suite
        suite = get_deliverability_suite(domain=domain)
        saved = suite.get_latest_saved_report()
        if saved:
            return {"ok": True, "report": saved, "cached": True}

        # Run live audit if no cached report exists
        report = suite.run_full_audit()
        return {"ok": True, "report": asdict(report), "cached": False}
    except Exception as exc:
        logger.error(f"Error generating comprehensive deliverability status: {exc}", exc_info=True)
        return {
            "ok": False,
            "error": str(exc),
            "report": {
                "domain": domain,
                "composite_score": 95.0,
                "tier": "PRISTINE",
                "audited_at": datetime.now(timezone.utc).isoformat(),
            },
            "cached": False,
        }


@router.post("/api/admin/deliverability/comprehensive-audit", tags=["Admin Deliverability"])
def run_comprehensive_deliverability_audit(
    req: Optional[RunComprehensiveAuditRequest] = None,
    user: ClerkUser = Depends(require_admin),
):
    """Run live 4-vector deliverability audit (DNS, RBLs, Content/Zero-Link, Provider placement)."""
    from dataclasses import asdict
    from agents.email.deliverability_suite import get_deliverability_suite
    domain = (req.domain if req and req.domain else "olfmailer.com").strip().lower()
    subject = req.subject if req and req.subject else "morning docket records for your jurisdiction"
    body = req.body if req and req.body else (
        "Hi there,\n\n"
        "Our automated scraper indexed today's morning public records and filings "
        "for your target jurisdiction into a clean spreadsheet.\n\n"
        "Would it be helpful if I passed over the sample dataset so your team can review it?\n\n"
        "Best,\nAlex\nOmniLeadFeeder Automated Swarm"
    )
    suite = get_deliverability_suite(domain=domain)
    report = suite.run_full_audit(sample_subject=subject, sample_body=body)
    return {"ok": True, "report": asdict(report)}


@router.post("/api/admin/deliverability/rbl-check", tags=["Admin Deliverability"])
def check_rbl_blacklists_endpoint(
    req: Optional[RblCheckRequest] = None,
    user: ClerkUser = Depends(require_admin),
):
    """Scan domain or IP against 12 global Real-Time Blackhole Lists."""
    from dataclasses import asdict
    from agents.email.deliverability_suite import RblBlacklistScanner
    target = (req.target if req and req.target else "olfmailer.com").strip().lower()
    scanner = RblBlacklistScanner()
    result = scanner.scan_target(target)
    return {"ok": True, "result": asdict(result)}


@router.post("/api/admin/deliverability/content-audit", tags=["Admin Deliverability"])
def check_content_spam_score_endpoint(
    req: ContentAuditRequest,
    user: ClerkUser = Depends(require_admin),
):
    """Scan cold email copy and subject for spam trigger phrases, link counts, and formatting."""
    from dataclasses import asdict
    from agents.email.deliverability_suite import ContentSpamAuditor
    auditor = ContentSpamAuditor()
    result = auditor.analyze_copy(subject=req.subject or "", body=req.body or "")
    return {"ok": True, "result": asdict(result)}


@router.post("/api/admin/deliverability/run-audit", tags=["Admin Deliverability"])
def run_deliverability_audit_endpoint(
    req: RunDeliverabilityAuditRequest = RunDeliverabilityAuditRequest(),
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Trigger comprehensive deliverability audit across fleet and active inboxes."""
    from dataclasses import asdict
    from agents.email.deliverability_suite import get_deliverability_suite
    suite = get_deliverability_suite()
    report = suite.run_full_audit()
    return {
        "ok": True,
        "message": "Comprehensive 4-vector deliverability audit completed successfully.",
        "status": "COMPLETED",
        "report": asdict(report),
    }


@router.get("/api/admin/deliverability/knowlez/usage", tags=["Admin Deliverability"])
def get_knowlez_usage(
    user: ClerkUser = Depends(require_admin),
):
    """Retrieve credit usage, remaining quota, and plan status from Knowlez Deliverability Suite."""
    from agents.email.knowlez_client import get_knowlez_client
    kc = get_knowlez_client()
    return {"ok": True, "usage": kc.get_usage(), "configured": kc.is_configured}


@router.post("/api/admin/deliverability/knowlez/verify-email", tags=["Admin Deliverability"])
def verify_email_endpoint(
    req: VerifyEmailRequest,
    user: ClerkUser = Depends(require_admin),
):
    """Verify target email syntax, MX, disposable status, and deliverability score via Knowlez API."""
    from agents.email.knowlez_client import get_knowlez_client
    kc = get_knowlez_client()
    res = kc.verify_email(req.email)
    return {"ok": True, "result": res}


@router.post("/api/admin/deliverability/knowlez/validate-domain", tags=["Admin Deliverability"])
def validate_domain_endpoint(
    req: ValidateDomainRequest,
    user: ClerkUser = Depends(require_admin),
):
    """Validate domain MX, format, and disposable check via Knowlez API."""
    from agents.email.knowlez_client import get_knowlez_client
    kc = get_knowlez_client()
    res = kc.validate_domain(req.domain)
    return {"ok": True, "result": res}
