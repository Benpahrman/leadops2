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

logger = logging.getLogger("api.admin.kanban")
router = APIRouter()

@router.get("/api/admin/pipeline", tags=["Admin Operations"])
def get_pipeline_kanban(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    try:
        kanban_res = admin_service.get_pipeline_kanban()
        all_leads = []
        cols = kanban_res.get("columns", {}) if isinstance(kanban_res, dict) else {}
        for col_list in cols.values():
            if isinstance(col_list, list):
                for item in col_list:
                    if item.get("state") != "ARCHIVED":
                        all_leads.append(item)

        return {
            "leads": all_leads,
            "pipeline": all_leads,
            "kanban": kanban_res,
            "archived": kanban_res.get("archived", []) if isinstance(kanban_res, dict) else [],
            "archived_count": kanban_res.get("archived_count", 0) if isinstance(kanban_res, dict) else 0,
            "telemetry": admin_service.get_sandbox_telemetry(),
        }
    except Exception as e:
        logger.error(f"Failed to fetch pipeline kanban: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to load pipeline: {e}")



@router.delete("/api/admin/leads/{lead_id}", tags=["Admin Operations"])
def delete_lead(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    success = storage_backend.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found or already deleted.")
    return {"ok": True, "message": f"Lead {lead_id} deleted successfully."}



@router.get("/api/admin/all-companies", tags=["Admin Operations"])
def get_all_companies(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Returns all client companies and leads for Founder Mission Control."""
    leads = storage_backend.list_leads()
    sandboxes = storage_backend.list_sandboxes()
    
    result = []
    seen_slugs = set()
    for sb in sandboxes:
        slug = sb.slug
        if slug not in seen_slugs:
            seen_slugs.add(slug)
            result.append({
                "slug": slug,
                "lead_id": sb.lead.lead_id,
                "company_name": getattr(sb.lead, "company_name", "") or sb.lead.lead_id,
                "contact_email": getattr(sb.lead, "contact_email", ""),
                "jurisdiction": getattr(sb.lead, "jurisdiction", ""),
                "state": sb.lead.state.value,
                "tier": sb.lead.tier.name,
                "deposit_paid": sb.lead.deposit_paid,
                "qa_score": sb.lead.qa_score,
                "subscription_active": getattr(sb.lead, "subscription_active", False),
            })
    return {"companies": result, "total": len(result)}

