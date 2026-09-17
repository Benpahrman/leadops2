"""Master portal router package aggregating domain sub-routers.

Modularized under ADR-0002 into:
- sandboxes: Sandbox search, details, column suggestions, evidence dossiers
- intake: CSRF token, field selection, scope approval, pipeline init, cancellations
- chat: Real-time Alex persona dialogue and inbound email webhook
- checkout: PayPal $99 deposit sprint, backlog unlock, and final balance milestone
- ui: ADR-0003 presentation layer with React SPA redirects and template fallback
"""

import logging
from fastapi import APIRouter

from .sandboxes import router as sandboxes_router, validate_slug, get_sandbox_payload
from .intake import router as intake_router
from .chat import router as chat_router
from .checkout import router as checkout_router
from .ui import router as ui_router

from .helpers import (
    ensure_demo_sandbox,
    build_sandbox_payload,
    _pull_fresh_live_rows,
    _resolve_dataset_key_for_slug,
    scrape_live_sample_records_for_target,
)
from .models import (
    SelectFieldsRequest,
    RecordEventRequest,
    ChatMessageRequest,
    InboundEmailWebhookRequest,
    CancellationRequestModel,
    PipelineInitializeRequest,
)

logger = logging.getLogger("api.portal")

router = APIRouter()

# Include all sub-routers
router.include_router(sandboxes_router)
router.include_router(intake_router)
router.include_router(chat_router)
router.include_router(checkout_router)
router.include_router(ui_router)

__all__ = [
    "router",
    "validate_slug",
    "get_sandbox_payload",
    "ensure_demo_sandbox",
    "build_sandbox_payload",
    "_pull_fresh_live_rows",
    "_resolve_dataset_key_for_slug",
    "scrape_live_sample_records_for_target",
    "SelectFieldsRequest",
    "RecordEventRequest",
    "ChatMessageRequest",
    "InboundEmailWebhookRequest",
    "CancellationRequestModel",
    "PipelineInitializeRequest",
]
