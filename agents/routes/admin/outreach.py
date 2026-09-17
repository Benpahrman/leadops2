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
from agents.scraper_catalog import (
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


@router.post("/api/admin/scout/run", tags=["Admin Operations"])
@router.post("/api/admin/scout/trigger-run", tags=["Admin Operations"])
def trigger_scout_run(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    try:
        from agents.scout_runner import ScoutBackgroundWorker
        worker = ScoutBackgroundWorker(storage=storage_backend, portal=portal_service)
        return worker.discover_next_candidate()
    except Exception as exc:
        logger.error(f"Scout run failed: {exc}", exc_info=True)
        return {
            "ok": False,
            "status": "SCOUT_ERROR",
            "message": f"Scout execution error: {str(exc)}",
            "reason": str(exc),
        }


@router.get("/api/admin/scout/status", tags=["Admin Operations"])
def get_scout_status(
    request: Request,
    _: ClerkUser = Depends(require_admin),
):
    supervisor = getattr(request.app.state, "scout_supervisor", None)
    if not supervisor:
        return {"phase": "UNAVAILABLE", "message": "Scout supervisor is not configured"}
    return supervisor.status()


@router.post("/api/admin/scout/toggle-24-7", tags=["Admin Operations"])
def toggle_scout_24_7(
    req: Toggle247Request,
    request: Request,
    _: ClerkUser = Depends(require_admin),
):
    """Toggle Scout supervisor 24/7 all-day prospecting on or off."""
    supervisor = getattr(request.app.state, "scout_supervisor", None)
    if not supervisor:
        return {"ok": False, "message": "Scout supervisor is not configured", "run_24_7": req.enabled}
    stat = supervisor.set_24_7_mode(req.enabled)
    return {"ok": True, "run_24_7": supervisor.run_24_7, "status": stat}


@router.get("/api/admin/auto-outreach/status", tags=["Admin Operations"])
def get_auto_outreach_status(
    _: ClerkUser = Depends(require_admin),
):
    from agents.auto_outreach import auto_outreach_scheduler
    return auto_outreach_scheduler.get_status()


@router.post("/api/admin/auto-outreach/toggle", tags=["Admin Operations"])
def toggle_auto_outreach(
    req: ToggleAutoOutreachRequest,
    _: ClerkUser = Depends(require_admin),
):
    from agents.auto_outreach import auto_outreach_scheduler
    auto_outreach_scheduler.set_enabled(req.enabled)
    return {"ok": True, "enabled": auto_outreach_scheduler.is_enabled}


@router.post("/api/admin/scout/trigger-web-scout", tags=["Admin Operations"])
def trigger_web_scout_run(
    req: Optional[TriggerWebScoutRequest] = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    try:
        niche = req.niche.strip() if req and req.niche and req.niche.strip() else None
        channel = req.channel.strip() if req and req.channel and req.channel.strip() else None
        run_until_found = req.run_until_found if req and req.run_until_found is not None else True
        max_attempts = req.max_attempts if req and req.max_attempts is not None else 4

        # High-ROI structured channels (county_filing_party, state_bar, sos_entity,
        # local_business) are handled by ScoutBackgroundWorker which has the full
        # multi-channel dispatch logic. If niche/search is provided, B2BWebScoutWorker is used.
        HIGH_ROI_CHANNELS = {"county_filing_party", "state_bar", "sos_entity", "local_business"}
        if niche:
            # User specified an explicit search query or niche -> hunt with B2BWebScoutWorker until found
            from agents.scout_runner import B2BWebScoutWorker
            web_worker = B2BWebScoutWorker(storage=storage_backend, portal=portal_service)
            return web_worker.discover_next_candidate(
                custom_niche=niche,
                run_until_found=run_until_found,
                max_attempts=max_attempts,
            )

        if channel in HIGH_ROI_CHANNELS or (channel is None and not niche):
            from agents.scout_runner import ScoutBackgroundWorker
            worker = ScoutBackgroundWorker(storage=storage_backend, portal=portal_service)
            return worker.discover_next_candidate(
                channel=channel,
                run_until_found=run_until_found,
                max_attempts=max_attempts,
            )

        # Explicit niche brainstorm path — use B2B web scout
        from agents.scout_runner import B2BWebScoutWorker
        web_worker = B2BWebScoutWorker(storage=storage_backend, portal=portal_service)
        return web_worker.discover_next_candidate(
            custom_niche=niche,
            run_until_found=run_until_found,
            max_attempts=max_attempts,
        )
    except Exception as exc:
        logger.error(f"Web scout trigger failed: {exc}", exc_info=True)
        return {
            "ok": False,
            "status": "SCOUT_ERROR",
            "message": f"Scout execution error: {str(exc)}",
            "reason": str(exc),
        }


@router.post("/api/admin/scout/batch-scout", tags=["Admin Operations"])
def trigger_batch_scout_run(
    req: Optional[BatchScoutRequest] = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Ramp up scouting: Trigger multi-lead batch discovery across high-ROI channels."""
    try:
        count = min(max(req.count if req and req.count else 3, 1), 5)
        channel = req.channel.strip() if req and req.channel and req.channel.strip() else None
        niche = req.niche.strip() if req and req.niche and req.niche.strip() else None

        from agents.scout_runner import ScoutBackgroundWorker
        worker = ScoutBackgroundWorker(storage=storage_backend, portal=portal_service)
        return worker.discover_batch_candidates(count=count, channel=channel, niche=niche)
    except Exception as exc:
        logger.error(f"Batch scout failed: {exc}", exc_info=True)
        return {
            "ok": False,
            "status": "BATCH_SCOUT_ERROR",
            "message": f"Batch scout error: {str(exc)}",
            "reason": str(exc),
        }


@router.get("/api/admin/scout/county-orchestrator/status", tags=["Admin Operations"])
def get_county_orchestrator_status(
    _: ClerkUser = Depends(require_admin),
):
    """Retrieve current 50-state and county-by-county orchestrator progress, active jurisdiction, and stats."""
    from agents.national_county_orchestrator import get_national_county_orchestrator
    orchestrator = get_national_county_orchestrator()
    active = orchestrator.get_active_jurisdiction()
    full_state = orchestrator.state.to_dict()
    return {
        "ok": True,
        "active_jurisdiction": active,
        "orchestrator_state": full_state,
    }


@router.post("/api/admin/scout/county-orchestrator/advance", tags=["Admin Operations"])
def advance_county_orchestrator_cursor(
    _: ClerkUser = Depends(require_admin),
):
    """Manually advance the national prospecting cursor to the next county/state."""
    from agents.national_county_orchestrator import get_national_county_orchestrator
    orchestrator = get_national_county_orchestrator()
    new_active = orchestrator.advance_cursor()
    return {
        "ok": True,
        "message": f"Orchestrator cursor advanced to {new_active['county_name']}, {new_active['state_code']}",
        "active_jurisdiction": new_active,
    }


@router.post("/api/admin/scout/county-orchestrator/set-focus", tags=["Admin Operations"])
def set_county_orchestrator_state_focus(
    req: SetStateFocusRequest,
    _: ClerkUser = Depends(require_admin),
):
    """Lock scouting to a specific state (e.g. 'WA', 'TX', 'FL') or unlock for 50-state sweep (null/empty)."""
    from agents.national_county_orchestrator import get_national_county_orchestrator
    orchestrator = get_national_county_orchestrator()
    active = orchestrator.set_state_focus(req.state_code)
    mode = f"locked to {req.state_code.upper()}" if req.state_code else "unlocked (50-state national sweep)"
    return {
        "ok": True,
        "message": f"State focus {mode}",
        "active_jurisdiction": active,
    }


@router.get("/api/admin/prospector/status", tags=["High-Volume Prospector"])
def get_prospector_status_endpoint(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Retrieve 14-day campaign status, office hours telemetry, and deduplication statistics."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    return engine.get_status()


@router.post("/api/admin/prospector/start", tags=["High-Volume Prospector"])
def start_prospector_campaign_endpoint(
    req: Optional[StartProspectorRequest] = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Start or restart the 14-day high-volume autonomous prospecting campaign."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    duration = req.duration_days if req and req.duration_days else 14
    volume = req.volume_per_cycle if req and req.volume_per_cycle else 3
    channels = req.channels if req and req.channels else None
    return engine.start_campaign(duration_days=duration, volume_per_cycle=volume, channels=channels)


@router.post("/api/admin/prospector/pause", tags=["High-Volume Prospector"])
def pause_prospector_campaign_endpoint(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Pause the continuous high-volume prospecting campaign loop."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    return engine.pause_campaign()


@router.post("/api/admin/prospector/resume", tags=["High-Volume Prospector"])
def resume_prospector_campaign_endpoint(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Resume the 14-day high-volume prospecting campaign loop."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    return engine.resume_campaign()


@router.post("/api/admin/prospector/toggle-24-7", tags=["High-Volume Prospector"])
def toggle_prospector_24_7(
    req: Toggle247Request,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Toggle High-Volume Prospector 24/7 all-day prospecting on or off."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    stat = engine.set_24_7_mode(req.enabled)
    return {"ok": True, "run_24_7": engine.run_24_7, "status": stat}


@router.post("/api/admin/prospector/trigger-burst", tags=["High-Volume Prospector"])
async def trigger_prospector_burst_endpoint(
    req: Optional[TriggerProspectorBurstRequest] = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Execute an immediate high-volume discovery pass with real-time audit journey."""
    from agents.high_volume_prospector import get_high_volume_prospector
    engine = get_high_volume_prospector(storage=storage_backend, portal=portal_service)
    count = req.count if req and req.count else 3
    channel = req.channel if req and req.channel else None
    return await engine.trigger_burst(count=count, channel=channel)


@router.post("/api/admin/prospector/refresh-freshness/{lead_id}", tags=["High-Volume Prospector"])
def refresh_lead_freshness_endpoint(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Pre-outreach same-day freshness verification gate: Re-scrapes and injects fresh same-day filings."""
    lead = storage_backend.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
    from agents.pitcher import ensure_fresh_records_for_lead
    return ensure_fresh_records_for_lead(
        lead=lead,
        portal_service=portal_service,
        storage_backend=storage_backend,
        max_age_hours=24,
    )


@router.post("/api/admin/prospector/batch-refresh-stale", tags=["High-Volume Prospector"])
def batch_refresh_stale_backlog_endpoint(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Sweep all vetted backlog leads and refresh any stale sandbox records before outreach launch."""
    from agents.pitcher import ensure_fresh_records_for_lead
    leads = storage_backend.list_leads()
    backlog = [
        l for l in leads
        if l.state in (State.REVIEW, State.PITCH_PENDING_APPROVAL, State.PROSPECTING)
    ]
    refreshed = 0
    checked = 0
    results = []
    for l in backlog:
        checked += 1
        res = ensure_fresh_records_for_lead(
            lead=l,
            portal_service=portal_service,
            storage_backend=storage_backend,
            max_age_hours=24,
        )
        if res.get("refreshed"):
            refreshed += 1
        results.append({
            "lead_id": l.lead_id,
            "company_name": l.company_name,
            "refreshed": res.get("refreshed", False),
            "record_count": res.get("record_count", 0),
        })

    return {
        "ok": True,
        "checked_count": checked,
        "refreshed_count": refreshed,
        "results": results,
        "message": f"Freshness sweep complete: {refreshed}/{checked} stale sandboxes refreshed with same-day filings.",
    }


@router.post("/api/admin/leads/{lead_id}/enrich", tags=["Admin Operations"])
def re_enrich_lead_endpoint(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Deep Research: On-demand live re-enrichment of lead with deep operational & market intelligence."""
    try:
        from agents.scout_runner import ScoutBackgroundWorker
        worker = ScoutBackgroundWorker(storage=storage_backend, portal=portal_service)
        return worker.re_enrich_lead(lead_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error(f"Re-enrichment failed for {lead_id}: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Enrichment error: {str(exc)}")


@router.post("/api/admin/auto-outreach/flush", tags=["Admin Operations"])
def trigger_outreach_flush(
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Flush pending outreach queue immediately across inboxes with anti-spam jitter."""
    from agents.auto_outreach import auto_outreach_scheduler
    from agents.notifications import notification_manager
    import threading

    threading.Thread(
        target=auto_outreach_scheduler.flush_pending_office_hours_queue,
        args=(storage_backend, notification_manager),
        daemon=True,
        name="manual-outreach-flush",
    ).start()

    return {
        "ok": True,
        "message": "Outreach dispatch worker triggered. Processing pending pitches with anti-spam human jitter.",
    }


@router.get("/api/admin/outreach/sequencer/status", tags=["Admin Operations"])
def get_sequencer_status(
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Retrieve telemetry on multi-touch cold outreach sequencer."""
    from agents.email.sequencer import ColdOutreachSequencer
    from agents.domain import State

    sequencer = ColdOutreachSequencer(storage_backend=storage_backend)
    eligible = sequencer.find_eligible_leads()
    all_leads = storage_backend.list_leads() if hasattr(storage_backend, "list_leads") else []

    touch_1_count = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) == 1)
    touch_2_count = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) == 2)
    touch_3_count = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) >= 3)
    replied_count = sum(1 for l in all_leads if getattr(l, "outreach_replied", False))

    return {
        "ok": True,
        "active_sequences": touch_1_count + touch_2_count,
        "touch_1_count": touch_1_count,
        "touch_2_count": touch_2_count,
        "touch_3_completed_count": touch_3_count,
        "replied_count": replied_count,
        "eligible_for_dispatch_now": [
            {
                "lead_id": item["lead"].lead_id,
                "company_name": getattr(item["lead"], "company_name", ""),
                "contact_email": getattr(item["lead"], "contact_email", ""),
                "target_touch": item["target_touch"],
                "next_outreach_at": getattr(item["lead"], "next_outreach_at", ""),
                "county": getattr(item["lead"], "county", ""),
                "city": getattr(item["lead"], "city", ""),
            }
            for item in eligible
        ],
    }


@router.post("/api/admin/outreach/sequencer/tick", tags=["Admin Operations"])
def trigger_sequencer_tick(
    storage_backend=Depends(get_storage),
    user: ClerkUser = Depends(require_admin),
):
    """Manually advance multi-touch cold outreach sequences for eligible leads."""
    from agents.email.sequencer import ColdOutreachSequencer

    sequencer = ColdOutreachSequencer(storage_backend=storage_backend)
    dispatches = sequencer.tick_sequence()
    return {
        "ok": True,
        "dispatches_count": len(dispatches),
        "dispatches": dispatches,
    }


@router.post("/api/admin/leads/{lead_id}/enrich-contact", tags=["Admin Operations"])
def enrich_lead_contact(
    lead_id: str,
    admin_service=Depends(get_admin_service),
    _: ClerkUser = Depends(require_admin),
):
    """Trigger the Contact Enricher Researcher Agent to find and verify alternative contacts for a lead."""
    res = admin_service.enrich_and_recover_lead(lead_id)
    return res


@router.get("/api/admin/leads/archived", tags=["Admin Operations"])
def get_archived_leads(
    admin_service=Depends(get_admin_service),
    _: ClerkUser = Depends(require_admin),
):
    """Retrieve all archived leads with failure reasons and recovery history."""
    archived = admin_service.get_archived_leads()
    return {"ok": True, "count": len(archived), "leads": archived}
