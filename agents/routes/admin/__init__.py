"""
agents.routes.admin
~~~~~~~~~~~~~~~~~~~

Master router aggregating all admin sub-routers:
- pipeline.py (Kanban, transitions, purge, emergency stop)
- tickets.py (Tickets CRUD, SLA breaches, cancellations)
- catalog.py (Scraper catalog, on-demand runs, daily delivery grid)
- outreach.py (Scout runs, auto-outreach, county orchestrators)
- inboxes.py (Inboxes, warmup cycles, deliverability audits, OAuth)

Conforms to:
- ADR-0002: Strangler Fig De-monolithization Protocol
- ADR-0003: Backend-Frontend Boundary Decoupling
"""

from __future__ import annotations

import os
import logging
from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from agents.auth import require_admin, ClerkUser
from .models import *
from .pipeline import router as pipeline_router
from .tickets import router as tickets_router
from .catalog import router as catalog_router
from .outreach import router as outreach_router
from .inboxes import router as inboxes_router

logger = logging.getLogger("api.admin")

router = APIRouter()

# Mount all sub-routers
router.include_router(pipeline_router)
router.include_router(tickets_router)
router.include_router(catalog_router)
router.include_router(outreach_router)
router.include_router(inboxes_router)

# ADR-0003: Strict Backend-Frontend Decoupling (Directive: use react frontend for the website)
@router.get("/admin", tags=["Admin Mission Control"])
@router.get("/admin/control", tags=["Admin Mission Control"])
def admin_mission_control_page(user: ClerkUser = Depends(require_admin)):
    """
    Enforces strict backend-frontend decoupling.
    Redirects operator to the React Vite SPA frontend (/admin).
    """
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=f"{frontend_url}/admin", status_code=307)


__all__ = [
    "router",
    "require_admin",
    "OverrideStateRequest",
    "OverrideQARequest",
    "EmergencyStopRequest",
    "CreateTicketRequest",
    "UpdateTicketRequest",
    "CancellationActionRequest",
    "VerifyDeliverabilityRequest",
    "BatchVerifyDeliverabilityRequest",
    "ValidateDomainRequest",
    "ToggleAutoOutreachRequest",
    "TriggerWebScoutRequest",
    "BatchScoutRequest",
    "SetStateFocusRequest",
    "StartProspectorRequest",
    "TriggerProspectorBurstRequest",
    "SendLifecycleEmailRequest",
    "DraftEmailRequest",
    "InboxUpsertRequest",
    "WarmupStartRequest",
    "AddWarmupTargetRequest",
    "RunComprehensiveAuditRequest",
    "RblCheckRequest",
    "ContentAuditRequest",
    "RunDeliverabilityAuditRequest",
    "VerifyEmailRequest",
]
