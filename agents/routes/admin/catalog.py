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


@router.get("/api/admin/swarm/active-builds", tags=["Admin Operations"])
def get_swarm_active_builds(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return {"active_jobs": admin_service.get_active_builds()}


@router.post("/api/admin/leads/{lead_id}/swarm", tags=["Admin Operations"])
@router.post("/api/admin/swarm/{lead_id}/launch", tags=["Admin Operations"])
def launch_dev_swarm(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Triggers or retries the 7-agent autonomous dev swarm on a paid lead in the background."""
    lead = storage_backend.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    import threading
    import asyncio
    from agents.domain import State, PaymentEvent
    from agents.workflow import run_autonomous_dev_team
    from agents.websocket import progress_manager
    
    slug = getattr(lead, "slug", "") or lead.lead_id
    if lead.state == State.PROSPECTING:
        lead.transition(State.REVIEW, "Admin fast-track to SOW")
    if lead.state == State.REVIEW:
        lead.transition(State.CONVERSATIONAL_INTAKE, "Admin fast-track to SOW")
    if lead.state == State.PITCH_PENDING_APPROVAL:
        lead.transition(State.OUTREACH_SENT, "Admin fast-track to SOW")
    if lead.state == State.OUTREACH_SENT:
        lead.transition(State.CONVERSATIONAL_INTAKE, "Admin fast-track to SOW")
    if lead.state == State.CONVERSATIONAL_INTAKE:
        lead.transition(State.SOW_GENERATED, "Admin fast-track to SOW")
    if lead.state == State.SOW_GENERATED:
        lead.record_payment(PaymentEvent.DEPOSIT_PAID)
    else:
        lead.deposit_paid = True
    if lead.state == State.DEPOSIT_PAID:
        lead.transition(State.DEV_BUILDING, "Admin launched dev swarm")
    elif lead.state == State.BLOCKED_NEEDS_REVIEW:
        lead.transition(State.DEV_BUILDING, "Admin retried build")
    sandbox = None
    try:
        sandboxes = storage_backend.list_sandboxes()
        sandbox = next((s for s in sandboxes if getattr(s, "lead", None) and s.lead.lead_id == lead_id), None)
    except Exception as ex:
        logger.debug(f"Storage backend list_sandboxes note: {ex}")
    if not sandbox and hasattr(portal_service, "get_sandbox") and (lead.slug or lead_id):
        try:
            sandbox = portal_service.get_sandbox(lead.slug or lead_id)
        except Exception as ex:
            logger.debug(f"Portal service get_sandbox note: {ex}")

    def _run_swarm_bg():
        try:
            logger.info(f"🤖 [ADMIN SWARM LAUNCH] Starting build for {lead.lead_id} ({slug})...")
            def progress_cb(state, progress, message, details=None):
                asyncio.run(progress_manager.send_progress(slug, state or State.DEV_BUILDING, progress, message, details))
            
            run_autonomous_dev_team(lead, slug=slug, portal=portal_service, progress_callback=progress_cb)
            storage_backend.save_lead(lead)
            if sandbox:
                storage_backend.save_sandbox(sandbox)
            asyncio.run(progress_manager.send_complete(slug, True, lead.state))
        except Exception as e:
            logger.error(f"Admin swarm launch error for {lead_id}: {e}")
            asyncio.run(progress_manager.send_complete(slug, False, error=str(e)))
            
    threading.Thread(target=_run_swarm_bg, daemon=True).start()
    return {
        "ok": True,
        "lead_id": lead.lead_id,
        "slug": slug,
        "state": lead.state.value,
        "message": f"Autonomous Dev Swarm ignited for {lead.company_name or lead.lead_id}"
    }


@router.post("/api/admin/swarm/{lead_id}/override-qa", tags=["Admin Operations"])
def override_qa_gate(
    lead_id: str,
    req: OverrideQARequest,
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    try:
        return admin_service.override_qa_score(lead_id, req.qa_score, req.justification)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/admin/delivery/daily-grid", tags=["Admin Operations"])
def get_daily_grid(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return admin_service.get_daily_execution_grid()


@router.post("/api/admin/delivery/{lead_id}/run-now", tags=["Admin Operations"])
def trigger_delivery_run(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    dashboard_service=Depends(get_dashboard_service),
):
    try:
        return dashboard_service.trigger_manual_sync(lead_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/admin/scrapers", tags=["Admin Operations"])
def list_scrapers(
    search: str = "",
    refresh: bool = False,
    _: ClerkUser = Depends(require_admin),
):
    """Retrieve catalog of all production scrapers, code paths, and output datasets."""
    catalog = get_catalog(refresh=refresh)
    if search:
        catalog = search_catalog(search, catalog)
    return {
        "ok": True,
        "total": len(catalog),
        "with_code": sum(1 for c in catalog if c.get("has_scraper_code")),
        "with_output": sum(1 for c in catalog if c.get("has_output_data")),
        "scrapers": catalog,
    }


@router.get("/api/admin/scrapers/{lead_id}/code", tags=["Admin Operations"])
def get_scraper_code(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
):
    """Fetch the full Python source code of the scraper (portal_scraper.py or entry.py)."""
    code = get_scraper_source_code(lead_id)
    if not code:
        raise HTTPException(status_code=404, detail=f"No scraper code found for lead: {lead_id}")
    return PlainTextResponse(code, media_type="text/plain; charset=utf-8")


@router.get("/api/admin/scrapers/{lead_id}/output", tags=["Admin Operations"])
def get_scraper_output(
    lead_id: str,
    format: str = "json",
    _: ClerkUser = Depends(require_admin),
):
    """Fetch the latest extracted records as JSON or CSV download."""
    data = get_scraper_output_data(lead_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No output dataset found for lead: {lead_id}")

    if format.lower() == "csv":
        import io
        output_stream = io.StringIO()
        if data and isinstance(data[0], dict):
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(output_stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        csv_content = output_stream.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{lead_id}_data.csv"'}
        )

    return {
        "ok": True,
        "lead_id": lead_id,
        "rows_count": len(data),
        "data": data,
    }


@router.post("/api/admin/scrapers/{lead_id}/run", tags=["Admin Operations"])
def run_scraper_on_demand(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
):
    """Trigger on-demand execution of the scraper and return extracted rows."""
    result = execute_scraper_on_demand(lead_id)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=result.get("error", "Execution failed"))
    return result
