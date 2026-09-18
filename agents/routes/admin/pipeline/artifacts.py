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

logger = logging.getLogger("api.admin.artifacts")
router = APIRouter()

@router.get("/api/admin/leads/{lead_id}/artifacts", tags=["Admin Operations"])
def get_lead_artifacts(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
):
    """Fetch the list of all persisted artifacts in the client's dedicated folder."""
    from agents.client_artifacts import artifact_store
    artifacts = artifact_store.list_client_artifacts(lead_id)
    return {
        "ok": True,
        "lead_id": lead_id,
        "total_artifacts": len(artifacts),
        "artifacts": artifacts,
    }


@router.get("/api/admin/leads/{lead_id}/audit-trail", tags=["Admin Operations"])
def get_lead_audit_trail(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Fetch the full chronological audit trail and AI agent action history for a client."""
    from agents.client_artifacts import artifact_store
    from agents.integrations.audit_vault import audit_vault
    trail = artifact_store.get_audit_trail(lead_id)
    terms = audit_vault.get_terms_acceptance(lead_id)
    comms = audit_vault.get_communications_log(lead_id)
    payments = audit_vault.get_payment_records(lead_id)
    deliveries = audit_vault.get_deliveries_ledger(lead_id)

    # Fallback to database audit_log if disk artifact trail is empty
    if not trail and storage_backend:
        lead = storage_backend.get_lead(lead_id)
        if lead and lead.audit_log:
            trail = []
            for ev in lead.audit_log:
                if isinstance(ev, dict):
                    frm = ev.get("from", "")
                    to_st = ev.get("to", "")
                    action = f"{frm} ➔ {to_st}" if frm and to_st else (ev.get("action") or ev.get("event") or "State Transition")
                    trail.append({
                        "action": action,
                        "timestamp": ev.get("at") or ev.get("timestamp") or datetime.now(timezone.utc).isoformat(),
                        "detail": ev.get("reason") or ev.get("detail") or "Automated lifecycle transition",
                        "metadata": ev,
                    })

    return {
        "ok": True,
        "lead_id": lead_id,
        "total_events": len(trail),
        "audit_trail": trail,
        "terms_acceptance": terms,
        "communications_count": len(comms),
        "payments_count": len(payments),
        "deliveries_count": len(deliveries),
    }


@router.get("/api/admin/leads/{lead_id}/chargeback-dossier", tags=["Admin Operations"])
def get_admin_chargeback_dossier(
    lead_id: str,
    format: str = "json",
    _: ClerkUser = Depends(require_admin),
):
    """Generate and retrieve the formal legal Chargeback Dispute Defense Dossier for a client."""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    from agents.integrations.audit_vault import audit_vault

    dossier = audit_vault.generate_chargeback_defense_dossier(lead_id)

    if format.lower() == "html":
        html_path = Path(dossier["html_path"])
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
    elif format.lower() == "markdown":
        md_path = Path(dossier["markdown_path"])
        if md_path.exists():
            return HTMLResponse(content=f"<pre>{md_path.read_text(encoding='utf-8')}</pre>")

    return {"ok": True, "dossier": dossier}

