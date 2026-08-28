import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from ..auth import ClerkUser, require_admin
from ..models import Ticket, TicketStatus, TicketPriority, TicketType, CancellationRequest, CancellationStatus
from ..scout_runner import ScoutBackgroundWorker
from .dependencies import (
    get_storage,
    get_portal_service,
    get_dashboard_service,
    get_admin_service,
)
from .templates import render_admin_html

logger = logging.getLogger("api.admin")

router = APIRouter()

# Request Models
class OverrideStateRequest(BaseModel):
    target_state: str
    founder_reason: str = "Manual founder intervention"

class OverrideQARequest(BaseModel):
    qa_score: float
    justification: str = "Founder verified edge-case QA pass"

class EmergencyStopRequest(BaseModel):
    active: bool
    reason: str = "Global operational emergency pause"

# Ticket Request Models
class CreateTicketRequest(BaseModel):
    lead_id: str
    ticket_type: str = "selector_repair"
    priority: str = "high"
    title: str
    description: str = ""
    assignee: Optional[str] = None
    sla_hours: int = 4

class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    sla_hours: Optional[int] = None

class CancellationActionRequest(BaseModel):
    action: str  # "approve" or "reject"
    refund_amount: Optional[float] = None
    processed_by: str

@router.get("/admin", response_class=HTMLResponse, tags=["Admin Mission Control"])
@router.get("/admin/control", response_class=HTMLResponse, tags=["Admin Mission Control"])
def admin_mission_control_page(_: ClerkUser = Depends(require_admin)):
    return render_admin_html()

@router.get("/api/swarm/status", tags=["Admin Operations"])
def get_swarm_status(admin_service=Depends(get_admin_service)):
    return {
        "status": "ONLINE",
        "active_workers": [
            {"role": "planner", "state": "READY", "load": "0.12"},
            {"role": "dev_lead", "state": "COORDINATING", "load": "0.25"},
            {"role": "network_engineer", "state": "PASSIVE_PROBING", "load": "0.18"},
            {"role": "frontend_dom_specialist", "state": "AST_PARSING", "load": "0.34"},
            {"role": "systems_architect", "state": "SCHEMA_VALIDATING", "load": "0.22"},
            {"role": "junior_developer", "state": "PLAYWRIGHT_COMPILING", "load": "0.41"},
            {"role": "qa_gatekeeper", "state": "ESCROW_EVALUATING", "load": "0.15"},
        ],
        "circuit_breaker": "CLOSED" if not admin_service.governance.emergency_stop_active else "OPEN",
        "active_builds_count": len(admin_service.get_active_builds()),
    }

@router.get("/api/admin/pipeline", tags=["Admin Operations"])
def get_pipeline_kanban(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return {
        "kanban": admin_service.get_pipeline_kanban(),
        "telemetry": admin_service.get_sandbox_telemetry(),
    }

@router.post("/api/admin/leads/{lead_id}/advance", tags=["Admin Operations"])
def advance_lead_state(
    lead_id: str,
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    try:
        return admin_service.advance_lead_state(lead_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/admin/scout/trigger-run", tags=["Admin Operations"])
def trigger_scout_run(
    _: ClerkUser = Depends(require_admin),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    worker = ScoutBackgroundWorker(storage=storage_backend, portal=portal_service)
    return worker.discover_next_candidate()

@router.post("/api/admin/leads/{lead_id}/override-transition", tags=["Admin Operations"])
def override_lead_transition(
    lead_id: str,
    req: OverrideStateRequest,
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    try:
        return admin_service.override_lead_state(lead_id, req.target_state, req.founder_reason)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/admin/swarm/active-builds", tags=["Admin Operations"])
def get_swarm_active_builds(
    _: ClerkUser = Depends(require_admin),
    admin_service=Depends(get_admin_service),
):
    return {"active_jobs": admin_service.get_active_builds()}

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

@router.get("/api/admin/governance/metrics", tags=["Admin Operations"])
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


# Ticket Management Routes
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


# SLA Monitoring
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


# Cancellation Request Management
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
