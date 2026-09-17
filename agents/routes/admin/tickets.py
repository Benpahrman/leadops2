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


@router.get("/api/admin/tickets", tags=["Admin Operations"])
def list_tickets(
    lead_id: str | None = None,
    status: str | None = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """List all tickets with optional filtering."""
    tickets = storage_backend.list_tickets(lead_id)
    
    if status:
        tickets = [t for t in tickets if t.status.value == status]
    
    return {
        "tickets": [
            {
                "ticket_id": t.ticket_id,
                "lead_id": t.lead_id,
                "ticket_type": t.ticket_type.value,
                "status": t.status.value,
                "priority": t.priority.value,
                "title": t.title,
                "description": t.description,
                "assignee": t.assignee,
                "sla_deadline": t.sla_deadline.isoformat() if t.sla_deadline else None,
                "sla_breached": t.sla_breached,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
                "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            }
            for t in tickets
        ],
        "total": len(tickets),
    }


@router.post("/api/admin/tickets", tags=["Admin Operations"])
def create_ticket(
    req: CreateTicketRequest,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Create a new ticket with SLA deadline."""
    import uuid
    from datetime import datetime, timedelta
    
    ticket = Ticket(
        ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
        lead_id=req.lead_id,
        ticket_type=TicketType(req.ticket_type),
        status=TicketStatus.OPEN,
        priority=TicketPriority(req.priority),
        title=req.title,
        description=req.description,
        assignee=req.assignee,
        sla_deadline=datetime.utcnow() + timedelta(hours=req.sla_hours),
        sla_breached=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    storage_backend.save_ticket(ticket)

    # Alert operator of support ticket / complaint
    try:
        from agents.notifications import notification_manager
        lead = storage_backend.get_lead(ticket.lead_id) if hasattr(storage_backend, "get_lead") else None
        notification_manager.notify_complaint_or_ticket(ticket, lead)
    except Exception as notif_err:
        logger.warning(f"Ticket notification notice: {notif_err}")

    return {
        "ticket_id": ticket.ticket_id,
        "lead_id": ticket.lead_id,
        "ticket_type": ticket.ticket_type.value,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "title": ticket.title,
        "sla_deadline": ticket.sla_deadline.isoformat(),
        "created_at": ticket.created_at.isoformat(),
    }


@router.get("/api/admin/tickets/{ticket_id}", tags=["Admin Operations"])
def get_ticket(
    ticket_id: str,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Get a single ticket by ID."""
    ticket = storage_backend.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {
        "ticket_id": ticket.ticket_id,
        "lead_id": ticket.lead_id,
        "ticket_type": ticket.ticket_type.value,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "title": ticket.title,
        "description": ticket.description,
        "assignee": ticket.assignee,
        "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        "sla_breached": ticket.sla_breached,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
    }


@router.patch("/api/admin/tickets/{ticket_id}", tags=["Admin Operations"])
def update_ticket(
    ticket_id: str,
    req: UpdateTicketRequest,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Update ticket status, priority, assignee, or SLA."""
    ticket = storage_backend.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if req.status:
        ticket.status = TicketStatus(req.status)
        if req.status == "resolved":
            ticket.resolved_at = datetime.utcnow()
    if req.priority:
        ticket.priority = TicketPriority(req.priority)
    if req.assignee is not None:
        ticket.assignee = req.assignee
    if req.sla_hours is not None:
        ticket.sla_deadline = datetime.utcnow() + timedelta(hours=req.sla_hours)
    
    ticket.updated_at = datetime.utcnow()
    storage_backend.save_ticket(ticket)
    
    return {
        "ticket_id": ticket.ticket_id,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "assignee": ticket.assignee,
        "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
        "updated_at": ticket.updated_at.isoformat(),
    }


@router.get("/api/admin/sla/breaches", tags=["Admin Operations"])
def get_sla_breaches(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Get all tickets that have breached or are about to breach SLA."""
    from datetime import datetime
    
    tickets = storage_backend.list_tickets()
    now = datetime.utcnow()
    
    breached = []
    at_risk = []
    
    for t in tickets:
        if t.sla_deadline:
            if t.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
                if now > t.sla_deadline:
                    t.sla_breached = 1
                    storage_backend.save_ticket(t)
                    breached.append(t)
                elif (t.sla_deadline - now).total_seconds() < 3600:  # 1 hour warning
                    at_risk.append(t)
    
    return {
        "breached": [
            {
                "ticket_id": t.ticket_id,
                "lead_id": t.lead_id,
                "title": t.title,
                "sla_deadline": t.sla_deadline.isoformat(),
                "hours_overdue": round((now - t.sla_deadline).total_seconds() / 3600, 1),
                "assignee": t.assignee,
            }
            for t in breached
        ],
        "at_risk": [
            {
                "ticket_id": t.ticket_id,
                "lead_id": t.lead_id,
                "title": t.title,
                "sla_deadline": t.sla_deadline.isoformat(),
                "minutes_remaining": round((t.sla_deadline - now).total_seconds() / 60, 0),
                "assignee": t.assignee,
            }
            for t in at_risk
        ],
    }


@router.get("/api/admin/cancellations", tags=["Admin Operations"])
def list_cancellations(
    lead_id: str | None = None,
    status: str | None = None,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """List all cancellation requests."""
    requests = storage_backend.list_cancellation_requests(lead_id)
    
    if status:
        requests = [r for r in requests if r.status.value == status]
    
    return {
        "cancellations": [
            {
                "request_id": r.request_id,
                "lead_id": r.lead_id,
                "user_email": r.user_email,
                "reason": r.reason,
                "status": r.status.value,
                "refund_amount": r.refund_amount,
                "processed_by": r.processed_by,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "processed_at": r.processed_at.isoformat() if r.processed_at else None,
            }
            for r in requests
        ],
        "total": len(requests),
    }


@router.post("/api/admin/cancellations/{request_id}/action", tags=["Admin Operations"])
def process_cancellation(
    request_id: str,
    req: CancellationActionRequest,
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
):
    """Approve or reject a cancellation request."""
    cancellation = storage_backend.get_cancellation_request(request_id)
    if not cancellation:
        raise HTTPException(status_code=404, detail="Cancellation request not found")
    
    if req.action == "approve":
        cancellation.status = CancellationStatus.APPROVED
        cancellation.refund_amount = req.refund_amount
    elif req.action == "reject":
        cancellation.status = CancellationStatus.REJECTED
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")
    
    cancellation.processed_by = req.processed_by
    cancellation.processed_at = datetime.utcnow()
    cancellation.updated_at = datetime.utcnow()
    storage_backend.save_cancellation_request(cancellation)
    
    return {
        "request_id": cancellation.request_id,
        "status": cancellation.status.value,
        "refund_amount": cancellation.refund_amount,
        "processed_by": cancellation.processed_by,
        "processed_at": cancellation.processed_at.isoformat(),
    }
