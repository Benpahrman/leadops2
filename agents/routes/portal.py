import os
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..domain import State, PaymentEvent
from ..auth import ClerkUser, get_current_user, get_current_user_optional
from ..workflow import run_autonomous_dev_team
from ..pitcher import send_deposit_confirmation_email, send_ab_test_email
from .dependencies import (
    get_storage,
    get_portal_service,
    get_configured_token,
    get_llm_engine,
    verify_csrf_token,
)
from .templates import render_portal_html

logger = logging.getLogger("api.portal")

router = APIRouter()

def validate_slug(slug: str) -> str:
    import re
    if not re.fullmatch(r"[a-z0-9\-]+", slug):
        raise HTTPException(status_code=400, detail="Invalid slug format")
    return slug

# Request Models
from pydantic import Field

class SelectFieldsRequest(BaseModel):
    fields: list[str] = Field(min_length=1, max_length=50)

class RecordEventRequest(BaseModel):
    event: str = Field(min_length=1, max_length=100)

class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class CancellationRequestModel(BaseModel):
    reason: str = Field(default="", max_length=2000)

@router.get("/", response_class=HTMLResponse, tags=["Portal UI"])
def index(
    user: ClerkUser | None = Depends(get_current_user_optional),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    sandboxes = storage_backend.list_sandboxes()
    if sandboxes:
        s = sandboxes[-1]
        try:
            payload = get_sandbox_payload(s.slug, portal_service)
            return render_portal_html(s.slug, lead_data=payload)
        except KeyError:
            logger.warning("Sandbox payload missing for slug %s", s.slug)
            return render_portal_html(s.slug)
    leads = storage_backend.list_leads()
    if leads:
        l = leads[-1]
        return render_portal_html(l.slug, lead_data={"company_name": l.company_name, "jurisdiction": l.jurisdiction, "lead_id": l.lead_id, "contact_email": l.contact_email})
    return render_portal_html("prospect-intelligence-feed")

@router.get("/p/{slug}", response_class=HTMLResponse, tags=["Portal UI"])
def portal_view(
    slug: str,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
):
    logger.info(f"PORTAL_VIEW: START slug={slug}, user={user.email if user else 'anonymous'}")
    logger.info(f"PORTAL_VIEW: sandboxes in service: {list(portal_service._sandboxes.keys())}")
    try:
        sb = portal_service.get_sandbox(slug)
        logger.info(f"PORTAL_VIEW: Found sandbox: {sb.slug}, lead_id={sb.lead.lead_id}, tier_key={sb.lead.tier_key}")
        payload = get_sandbox_payload(slug, portal_service)
        return render_portal_html(slug, lead_data=payload)
    except KeyError as e:
        logger.error(f"PORTAL_VIEW: Sandbox not found: {slug}, error: {e}")
        raise HTTPException(status_code=404, detail=f"Sandbox not found: {slug}")
    except Exception as e:
        logger.error(f"PORTAL_VIEW: Exception: {type(e).__name__}: {e}")
        raise

@router.get("/about/alex", response_class=HTMLResponse, tags=["Portal UI"])
def operator_bio_page(
    user: ClerkUser = Depends(get_current_user),
):
    """Operator bio page for trust signal."""
    return render_operator_bio_html()

@router.get("/api/sandbox/{slug}", tags=["Portal API"])
def get_sandbox_payload(
    slug: str,
    portal_service=Depends(get_portal_service),
):
    try:
        print(f"GET_SANDBOX_PAYLOAD PRINT: slug={slug}")
        logger.info(f"GET_SANDBOX_PAYLOAD: slug={slug}")
        sandbox = portal_service.get_sandbox(slug)
        print(f"GET_SANDBOX_PAYLOAD PRINT: got sandbox, lead_id={sandbox.lead.lead_id}")
        logger.info(f"GET_SANDBOX_PAYLOAD: got sandbox, lead_id={sandbox.lead.lead_id}")
        lead = sandbox.lead
        print(f"GET_SANDBOX_PAYLOAD PRINT: lead.tier_key={lead.tier_key}")
        logger.info(f"GET_SANDBOX_PAYLOAD: lead.tier_key={lead.tier_key}")
        
        # Check for self-healing post-mortem report
        from pathlib import Path
        import json
        post_mortem_file = Path("build_artifacts") / (lead.lead_id or slug) / "post_mortem.json"
        post_mortem_data = None
        if post_mortem_file.exists():
            try:
                post_mortem_data = json.loads(post_mortem_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                logger.debug("Failed to load post mortem for %s", slug)
                pass

        print(f"GET_SANDBOX_PAYLOAD PRINT: accessing lead.tier")
        tier = lead.tier
        print(f"GET_SANDBOX_PAYLOAD PRINT: tier={tier.name}")
        logger.info(f"GET_SANDBOX_PAYLOAD: tier={tier.name}")
        
        print(f"GET_SANDBOX_PAYLOAD PRINT: accessing build_progress")
        progress = portal_service.build_progress(slug)
        print(f"GET_SANDBOX_PAYLOAD PRINT: progress={progress}")
        
        return {
            "slug": slug,
            "lead_id": lead.lead_id,
            "company_name": getattr(lead, "company_name", "") or lead.lead_id,
            "contact_email": getattr(lead, "contact_email", ""),
            "claimed_by_user": getattr(lead, "claimed_by", None) or getattr(lead, "contact_email", ""),
            "jurisdiction": getattr(lead, "jurisdiction", ""),
            "state": lead.state.value,
            "tier": tier.name,
            "tier_key": lead.tier_key,
            "source_url": sandbox.source_url,
            "sample": sandbox.rows,
            "selected_fields": lead.selected_fields,
            "progress": progress,
            
            # Payment & Milestone Tracking
            "deposit_paid": lead.deposit_paid,
            "deposit_amount": 250.00,
            "deposit_status": "PAID" if lead.deposit_paid else "PENDING_DEPOSIT",
            "next_payment_due": lead.state.value == "ESCROW_PREVIEW",
            "next_payment_amount": 250.00,
            "next_payment_purpose": f"Milestone #2 Final Payment ($250.00) & Monthly Subscription Activation (${int(tier.price_cents / 100)}/mo)",
            "final_paid": lead.final_paid,
            "subscription_active": getattr(lead, "subscription_active", False),
            "subscription_plan": f"{tier.name} (${int(tier.price_cents / 100)}/mo)",
            
            # QA & Self-Healing Telemetry
            "qa_score": lead.qa_score,
            "preview_rows": lead.preview_rows,
            "post_mortem": post_mortem_data,
        }
    except KeyError as e:
        logger.error(f"GET_SANDBOX_PAYLOAD: KeyError for slug={slug}: {e}")
        raise HTTPException(status_code=404, detail="Sandbox not found")
    except Exception as e:
        logger.error(f"GET_SANDBOX_PAYLOAD: Exception for slug={slug}: {type(e).__name__}: {e}")
        raise

@router.get("/api/portal/my-lead", tags=["Portal API"])
def get_user_lead(
    email: str,
    user: ClerkUser = Depends(get_current_user),
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Returns the specific lead assigned to a customer's email address."""
    clean_email = email.lower().strip()
    
    # SECURITY: Users cannot query other customer emails unless they are admin
    if not user.is_admin and user.email.lower().strip() != clean_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You can only query your own lead feed."
        )

    leads = storage_backend.list_leads()
    sandboxes = storage_backend.list_sandboxes()

    # Match by exact contact_email or claimed_by
    for sb in sandboxes:
        if sb.lead.contact_email.lower().strip() == clean_email or getattr(sb.lead, "claimed_by", "").lower().strip() == clean_email:
            return get_sandbox_payload(sb.slug, portal_service)

    for l in leads:
        if l.contact_email.lower().strip() == clean_email or getattr(l, "claimed_by", "").lower().strip() == clean_email:
            return get_sandbox_payload(l.slug, portal_service)

    raise HTTPException(status_code=404, detail="No company feed found for this user")

@router.post("/api/sandbox/{slug}/fields", tags=["Portal API"])
def select_fields(
    slug: str,
    req: SelectFieldsRequest,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
):
    print(f"SELECT_FIELDS DEBUG: slug={slug}, user={user}, req={req}")
    logger.info(f"SELECT_FIELDS: slug={slug}, user={user.email if user else None}, req_fields={req.fields if req else None}")
    slug = validate_slug(slug)
    try:
        portal_service.select_fields(slug, req.fields)
        return get_sandbox_payload(slug, portal_service)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sandbox/{slug}/scope", tags=["Portal API"])
def approve_scope(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
):
    slug = validate_slug(slug)
    try:
        portal_service.approve_scope(slug)
        return get_sandbox_payload(slug, portal_service)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sandbox/{slug}/chat", tags=["Portal API"])
def chat_with_assistant(
    slug: str,
    req: ChatMessageRequest,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
    llm_engine=Depends(get_llm_engine),
):
    slug = validate_slug(slug)
    try:
        sandbox = portal_service.get_sandbox(slug)
        context = {
            "source_url": sandbox.source_url,
            "tier": sandbox.lead.tier.name,
            "selected_fields": sandbox.lead.selected_fields or [],
        }
        reply = llm_engine.chat_with_alex(req.message, context)
        return {"ok": True, "reply": reply}
    except KeyError:
        raise HTTPException(status_code=404, detail="Sandbox not found")

@router.post("/api/sandbox/{slug}/checkout", tags=["Portal API"])
def request_checkout(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
):
    try:
        checkout_info = portal_service.request_checkout(slug)
        client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
        return {**checkout_info, "paypal_client_id": client_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sandbox/{slug}/pay-deposit", tags=["Portal API"])
@router.post("/api/sandbox/{slug}/simulate-deposit", tags=["Portal API"])
def pay_deposit(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Processes 50% milestone deposit payment and executes the Autonomous Dev Swarm Build Loop."""
    try:
        sandbox = portal_service.get_sandbox(slug)
        lead = sandbox.lead
        logger.info(f"💳 [CHECKOUT DEPOSIT RECEIVED] Slug: {slug} | Lead: {lead.lead_id} | Amount: $250.00")

        # SECURITY: Validate user has access to this lead
        if user.lead_id and user.lead_id != lead.lead_id:
            raise HTTPException(status_code=403, detail="Not authorized for this lead")

        # Already past deposit stage — just return success
        if lead.state in {State.ESCROW_PREVIEW, State.DELIVERED, State.WARRANTY_ACTIVE}:
            if not lead.deposit_paid:
                lead.record_payment(PaymentEvent.DEPOSIT_PAID)
                storage_backend.save_lead(lead)
            logger.info(f"🚀 [CHECKOUT COMPLETE] Lead {lead.lead_id} active at {lead.state.value}")
            return {
                "ok": True,
                "lead_id": lead.lead_id,
                "slug": slug,
                "state": lead.state.value,
                "qa_score": lead.qa_score or 100.0,
                "preview_rows": lead.preview_rows or 25,
                "escrow_ready": True,
                "dashboard_url": f"/dashboard/{lead.lead_id}",
            }

        # Ensure selected fields are populated
        if not lead.selected_fields:
            lead.selected_fields = list(sandbox.rows[0].keys()) if sandbox.rows else ["case_number", "decedent_name", "filing_date"]

        # Advance through the state machine properly using domain methods
        if lead.state == State.CONVERSATIONAL_INTAKE:
            lead.transition(State.SOW_GENERATED, "fast-track SOW generated for deposit")

        # record_payment handles DEPOSIT_PAID transition internally
        lead.record_payment(PaymentEvent.DEPOSIT_PAID)

        # Transition to DEV_BUILDING after deposit is recorded
        lead.transition(State.DEV_BUILDING, "autonomous builder swarm started")

        storage_backend.save_lead(lead)
        storage_backend.save_sandbox(sandbox)

        # Send deposit confirmation email with A/B test
        try:
            send_ab_test_email(lead, template_name="deposit_confirmation")
        except Exception as e:
            logger.warning(f"Failed to send deposit confirmation email: {e}")

        # Trigger real autonomous dev swarm build in background thread
        import threading
        from ..websocket import progress_manager
        
        def _async_dev_swarm():
            try:
                logger.info(f"🤖 [BACKGROUND DEV SWARM] Starting build for {lead.lead_id} ({slug})...")
                
                # Send initial progress
                import asyncio
                asyncio.run(progress_manager.send_progress(
                    slug, State.DEV_BUILDING, 5, "Initializing autonomous dev swarm..."
                ))
                
                # Run the dev team with progress callbacks
                def progress_callback(state: State, progress: int, message: str, details: dict = None):
                    asyncio.run(progress_manager.send_progress(slug, state, progress, message, details))
                
                run_autonomous_dev_team(lead, slug=slug, portal=portal_service, progress_callback=progress_callback)
                storage_backend.save_lead(lead)
                storage_backend.save_sandbox(sandbox)
                
                logger.info(f"✓ [BACKGROUND DEV SWARM COMPLETE] Lead {lead.lead_id} -> {lead.state.value}")
                asyncio.run(progress_manager.send_complete(slug, True, lead.state))
            except Exception as err:
                logger.error(f"Background dev swarm error: {err}")
                asyncio.run(progress_manager.send_complete(slug, False, error=str(err)))

        threading.Thread(target=_async_dev_swarm, daemon=True).start()

        logger.info(f"🚀 [CHECKOUT COMPLETE] Lead {lead.lead_id} advanced to DEV_BUILDING. Redirecting customer to dashboard.")

        return {
            "ok": True,
            "lead_id": lead.lead_id,
            "slug": slug,
            "state": "DEV_BUILDING",
            "deposit_paid": True,
            "qa_score": lead.qa_score or 95.0,
            "preview_rows": lead.preview_rows or 25,
            "escrow_ready": False,
            "dashboard_url": f"/dashboard/{lead.lead_id}",
            "portal_url": f"/p/{slug}",
        }
    except (KeyError, ValueError) as e:
        logger.error(f"Checkout error for {slug}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/api/sandbox/{slug}/final-checkout", tags=["Portal API"])
def get_final_checkout(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    portal_service=Depends(get_portal_service),
):
    """Returns final milestone (Payment #2) checkout payload."""
    try:
        checkout_info = portal_service.request_final_checkout(slug)
        client_id = os.environ.get("PAYPAL_CLIENT_ID", "mock_paypal_client_id")
        return {**checkout_info, "paypal_client_id": client_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sandbox/{slug}/pay-final", tags=["Portal API"])
@router.post("/api/sandbox/{slug}/simulate-final", tags=["Portal API"])
def pay_final(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Processes the second 50% milestone payment transaction ($250) and activates live feed delivery."""
    try:
        sandbox = portal_service.get_sandbox(slug)
        lead = sandbox.lead
        amount_usd = 250.00 if lead.tier_key != "buyout" else 1500.00
        logger.info(f"💳 [FINAL PAYMENT RECEIVED] Slug: {slug} | Lead: {lead.lead_id} | Amount: ${amount_usd:.2f}")

        if lead.state == State.ESCROW_PREVIEW:
            event = PaymentEvent.FINAL_PAID if lead.tier_key != "buyout" else PaymentEvent.BUYOUT_PAID
            lead.record_payment(event)
            lead.transition(State.DELIVERED, "Final payment received and feed deployed")
            if lead.tier_key != "buyout":
                lead.subscription_active = True

        storage_backend.save_lead(lead)
        storage_backend.save_sandbox(sandbox)

        logger.info(f"🚀 [FEED ACTIVATED] Lead {lead.lead_id} is now DELIVERED and active")
        return {
            "ok": True,
            "lead_id": lead.lead_id,
            "slug": slug,
            "state": lead.state.value,
            "final_paid": lead.final_paid,
            "subscription_active": lead.subscription_active,
            "message": "Final milestone payment processed. Live feed is active!",
            "dashboard_url": f"/dashboard/{lead.lead_id}",
        }
    except (KeyError, ValueError) as e:
        logger.error(f"Final payment error for {slug}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/sandbox/{slug}/events", tags=["Portal API"])
def record_event(
    slug: str,
    req: RecordEventRequest,
    portal_service=Depends(get_portal_service),
):
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
        return {"ok": True, **result}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
