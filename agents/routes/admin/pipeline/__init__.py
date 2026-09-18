"""
agents.routes.admin.pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Decomposed admin pipeline routers:
- kanban.py: Lead listing, filtering, and pipeline overview
- lifecycle.py: State transitions, manual overrides, deliverability verification
- governance.py: Emergency stops, system purges, live telemetry, and briefing triggers
- artifacts.py: Client artifacts, audit trails, and chargeback defense dossiers
- mobile_actions.py: 1-click mobile operator approvals from notifications
"""
from fastapi import APIRouter
from .kanban import router as kanban_router
from .lifecycle import router as lifecycle_router
from .governance import router as governance_router
from .artifacts import router as artifacts_router
from .mobile_actions import router as mobile_router

router = APIRouter()
router.include_router(kanban_router)
router.include_router(lifecycle_router)
router.include_router(governance_router)
router.include_router(artifacts_router)
router.include_router(mobile_router)

__all__ = ["router"]
