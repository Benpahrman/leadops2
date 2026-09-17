"""Presentation & UI routes for LeadOps portal.

Adheres to ADR-0003 by decoupling backend API logic from frontend HTML presentation,
providing safe fallback rendering for local testing while pointing callers to the React SPA.
"""

import logging
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse

from ...auth import ClerkUser, get_current_user_optional
from ..dependencies import get_storage, get_portal_service
from ..templates import (
    render_portal_html,
    render_landing_html,
    render_operator_bio_html,
    render_terms_html,
)
from .helpers import build_sandbox_payload, ensure_demo_sandbox

logger = logging.getLogger("api.portal.ui")

router = APIRouter()


@router.get("/", response_class=HTMLResponse, tags=["Portal UI"])
def index(
    user: ClerkUser | None = Depends(get_current_user_optional),
):
    """Serves the LeadOps product landing page or redirects to React SPA."""
    spa_url = os.environ.get("REACT_SPA_URL", "").rstrip("/")
    if spa_url and not os.environ.get("PYTEST_CURRENT_TEST"):
        return RedirectResponse(url=f"{spa_url}/", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return render_landing_html()


@router.get("/p/{slug}", response_class=HTMLResponse, tags=["Portal UI"])
def portal_view(
    slug: str,
    ref: str | None = None,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Serves the bespoke customer sandbox portal view."""
    logger.info(f"PORTAL_VIEW: START slug={slug}, user={user.email if user else 'anonymous'}")
    try:
        sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
        lead = sandbox.lead
        lead.last_login_at = datetime.now(timezone.utc).isoformat()
        if ref and not getattr(lead, "referred_by", ""):
            lead.referred_by = ref
        storage_backend.save_lead(lead)
        
        payload = build_sandbox_payload(slug, portal_service, storage_backend)
        return render_portal_html(slug, lead_data=payload)
    except Exception as e:
        logger.error(f"PORTAL_VIEW: Exception for slug {slug}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/about/alex", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/operator", response_class=HTMLResponse, tags=["Portal UI"])
def operator_bio_page(
    user: ClerkUser | None = Depends(get_current_user_optional),
):
    """Operator bio page for trust signal."""
    return render_operator_bio_html()


@router.get("/terms", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/privacy", response_class=HTMLResponse, tags=["Portal UI"])
def terms_page():
    """Terms of Service and Privacy Policy document."""
    return render_terms_html()


@router.get("/get-started", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/build", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/pipeline/new", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/checkout/success", response_class=HTMLResponse, tags=["Portal UI"])
@router.get("/checkout/cancel", response_class=HTMLResponse, tags=["Portal UI"])
def frontend_flow_pages():
    """Serves the React Single Page App for intake and checkout lifecycle flows."""
    return render_landing_html()
