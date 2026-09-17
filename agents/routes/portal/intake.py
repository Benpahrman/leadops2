"""Portal intake, CSRF token, field selection, scope approval, and cancellation endpoints."""

import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...auth import ClerkUser, get_current_user
from ...domain import Lead, State
from ..dependencies import (
    get_storage,
    get_portal_service,
    get_llm_engine,
    verify_csrf_token,
    generate_csrf_token,
)
from .helpers import scrape_live_sample_records_for_target
from .models import (
    SelectFieldsRequest,
    RecordEventRequest,
    CancellationRequestModel,
    PipelineInitializeRequest,
)
from .sandboxes import get_sandbox_payload, validate_slug

logger = logging.getLogger("api.portal.intake")

router = APIRouter()


@router.get("/api/csrf-token", tags=["Portal API"])
def get_csrf_token(
    request: Request,
    user: ClerkUser = Depends(get_current_user),
):
    """Get HMAC-based CSRF token for the current user."""
    token = generate_csrf_token(request, user.user_id)
    return {"csrf_token": token}


@router.post("/api/sandbox/{slug}/fields", tags=["Portal API"])
def select_fields(
    slug: str,
    req: SelectFieldsRequest,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Select desired extraction columns for this client's docket pipeline."""
    logger.debug("SELECT_FIELDS: slug=%s, user=%s, req=%s", slug, user, req)
    logger.info(f"SELECT_FIELDS: slug={slug}, user={user.email if user else None}, req_fields={req.fields if req else None}")
    slug = validate_slug(slug)
    try:
        portal_service.select_fields(slug, req.fields)
        return get_sandbox_payload(slug, portal_service, storage_backend)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/sandbox/{slug}/scope", tags=["Portal API"])
def approve_scope(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Lock scope and transition lead from REVIEW to SOW_GENERATED."""
    slug = validate_slug(slug)
    try:
        portal_service.approve_scope(slug)
        return get_sandbox_payload(slug, portal_service, storage_backend)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/pipeline/initialize", tags=["Portal API"])
def initialize_custom_pipeline(
    req: PipelineInitializeRequest,
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
    llm_engine=Depends(get_llm_engine),
):
    """Register a new prospect company, harvest 5-10 live records from their target URL, and generate a verified sandbox."""
    clean_company = req.company_name.strip()
    if not clean_company:
        raise HTTPException(status_code=400, detail="Company name is required")
    if not req.contact_email or "@" not in req.contact_email:
        raise HTTPException(status_code=400, detail="Valid work email is required")

    # Generate a unique clean slug from company name
    slug_base = re.sub(r"[^a-z0-9]+", "-", clean_company.lower()).strip("-")
    if not slug_base:
        slug_base = "custom-feed"
    slug = f"lead-{slug_base}"
    lead_id = slug

    # Actively harvest 5 to 10 live records directly from the target portal URL
    live_records, effective_source_url, detected_fields = scrape_live_sample_records_for_target(
        target_url=req.target_url,
        jurisdiction=req.jurisdiction,
        data_goal=req.data_goal,
        slug=slug,
        llm_engine=llm_engine,
    )

    # Check if lead already exists or create new one
    lead = storage_backend.get_lead(lead_id) if storage_backend else None
    if not lead:
        lead = Lead(
            lead_id=lead_id,
            tier_key=req.tier_key or "daily",
            company_name=clean_company,
            contact_email=req.contact_email.lower().strip(),
            jurisdiction=req.jurisdiction.strip() or f"{clean_company} Public Registry",
            source_url=effective_source_url,
            slug=slug,
            state=State.REVIEW,
            custom_goal=req.data_goal.strip(),
            preferred_destination=req.preferred_destination,
            selected_fields=detected_fields,
        )
        if storage_backend:
            storage_backend.save_lead(lead)
    else:
        lead.company_name = clean_company
        lead.contact_email = req.contact_email.lower().strip()
        if req.jurisdiction:
            lead.jurisdiction = req.jurisdiction.strip()
        lead.source_url = effective_source_url
        if req.tier_key:
            lead.tier_key = req.tier_key
        if detected_fields:
            lead.selected_fields = detected_fields
        if storage_backend:
            storage_backend.save_lead(lead)

    # Ensure a verified sandbox exists populated with the freshly scraped live records
    sandbox = None
    try:
        sandbox = portal_service.get_sandbox(slug)
    except KeyError:
        pass

    if not sandbox and storage_backend:
        sandbox = storage_backend.get_sandbox(slug)

    if not sandbox:
        from ...portal import Sandbox
        sandbox = Sandbox(
            slug=slug,
            lead=lead,
            rows=live_records,
            source_url=effective_source_url,
        )
        portal_service._sandboxes[slug] = sandbox
    else:
        sandbox.lead = lead
        sandbox.rows = live_records
        sandbox.source_url = effective_source_url

    if storage_backend:
        storage_backend.save_sandbox(sandbox)
        storage_backend.save_lead(lead)
        if lead.contact_email:
            try:
                import threading
                from ...auto_outreach import auto_outreach_scheduler
                threading.Thread(
                    target=auto_outreach_scheduler.auto_prepare_review_pitches,
                    args=(storage_backend, None, llm_engine),
                    daemon=True,
                    name="portal-auto-pitch-generator",
                ).start()
            except Exception as auto_pitch_err:
                logger.debug(f"Portal auto-pitch dispatch note: {auto_pitch_err}")

    return {
        "ok": True,
        "lead_id": lead.lead_id,
        "slug": slug,
        "sandbox_url": f"/p/{slug}",
        "dashboard_url": f"/dashboard/{lead.lead_id}",
        "company_name": clean_company,
        "tier": lead.tier.name,
        "jurisdiction": lead.jurisdiction,
        "source_url": effective_source_url,
        "sample_records": live_records[:10],
        "fields": detected_fields or (list(live_records[0].keys()) if live_records else []),
        "record_count": len(live_records),
    }


@router.post("/api/sandbox/{slug}/events", tags=["Portal API"])
def record_event(
    slug: str,
    req: RecordEventRequest,
    portal_service=Depends(get_portal_service),
):
    """Record user analytics interaction events on a sandbox."""
    try:
        portal_service.record_interaction(slug, req.event)
        return {"ok": True}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/sandbox/{slug}/cancel", tags=["Portal API"])
def request_cancellation(
    slug: str,
    req: CancellationRequestModel,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
):
    """Self-serve cancellation request."""
    slug = validate_slug(slug)
    try:
        result = portal_service.request_cancellation(slug, user.email, req.reason)

        # Alert operator of cancellation request
        try:
            from ...notifications import notification_manager
            sandbox = portal_service.get_sandbox(slug) if hasattr(portal_service, "get_sandbox") else None
            lead = getattr(sandbox, "lead", None)
            notification_manager.notify_cancellation_requested(
                lead=lead or slug,
                reason=req.reason,
                user_email=user.email,
            )
        except Exception as notif_err:
            logger.warning(f"Cancellation notification notice: {notif_err}")

        return {"ok": True, **result}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
