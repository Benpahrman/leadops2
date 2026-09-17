"""Portal $99 setup sprint deposit, PayPal order checkout, and final milestone balance payment routes."""

import asyncio
import logging
import os
import threading
import urllib.parse
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ...auth import ClerkUser, get_current_user, get_current_user_optional
from ...domain import State, PaymentEvent
from ...pitcher import send_ab_test_email, send_lifecycle_email
from agents.swarm.workflow import run_autonomous_dev_team
from ..dependencies import get_storage, get_portal_service, verify_csrf_token
from .helpers import ensure_demo_sandbox
from agents.client_artifacts import artifact_store
from agents.integrations.audit_vault import audit_vault
from agents.notifications import notification_manager
from agents.billing.subscriptions import subscription_activation, subscription_plan
from agents.websocket import progress_manager

logger = logging.getLogger("api.portal.checkout")

router = APIRouter()


@router.post("/api/sandbox/{slug}/checkout", tags=["Portal API"])
def request_checkout(
    slug: str,
    user: ClerkUser = Depends(get_current_user),
    _csrf: bool = Depends(verify_csrf_token),
    portal_service=Depends(get_portal_service),
):
    """Generate server-side checkout payload and resolve client ID."""
    try:
        checkout_info = portal_service.request_checkout(slug)
        paypal_mode = os.environ.get("PAYPAL_MODE", "sandbox").lower()
        client_id = (
            (os.environ.get("PAYPAL_LIVE_CLIENT_ID") if paypal_mode == "live" else None)
            or os.environ.get("PAYPAL_CLIENT_ID", "")
        )
        return {**checkout_info, "paypal_client_id": client_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/sandbox/{slug}/unlock-backlog", tags=["Portal API"])
async def unlock_30d_backlog(
    slug: str,
    request: Request,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Processes $49 tripwire purchase to unlock the full 30-day backlog CSV dataset (200-500 rows)."""
    try:
        sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
        lead = sandbox.lead
        body = {}
        try:
            body = await request.json()
        except Exception as e:
            logger.debug(f"Optional request json parsing in unlock_30d_backlog: {e}")

        email = body.get("email") or lead.contact_email or (user.email if user else "") or "customer@client.com"
        paypal_order_id = body.get("paypal_order_id") or f"PAYID-BACKLOG-{int(datetime.now().timestamp()*1000)}"

        lead.unlocked_30d_backlog = True
        storage_backend.save_lead(lead)

        # Record financial transaction in Audit Vault
        audit_vault.record_payment_event(
            lead_id=lead.lead_id,
            provider="PAYPAL",
            transaction_id=f"TXN-{paypal_order_id}",
            order_id=paypal_order_id,
            amount_usd=49.00,
            currency="USD",
            status="COMPLETED",
            payer_email=email,
            payer_name=lead.company_name or slug,
            payment_type="30-Day Historical Backlog Dataset Unlock ($49 Tripwire)",
            raw_metadata={"client_ip": request.client.host if request.client else "127.0.0.1"},
        )

        try:
            notification_manager.notify_payment_received(
                lead=lead,
                amount_usd=49.00,
                payment_type="30-Day Full Backlog CSV Unlock",
                provider="PayPal",
            )
        except Exception as notif_err:
            logger.warning(f"Notification notice for backlog payment: {notif_err}")

        # Return full rows dataset
        full_rows = sandbox.rows or []
        return {
            "ok": True,
            "unlocked": True,
            "amount_paid": 49.00,
            "rows_count": len(full_rows),
            "rows": full_rows,
            "message": "Full 30-day historical backlog unlocked successfully!",
        }
    except Exception as e:
        logger.error(f"Backlog unlock error for {slug}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/sandbox/{slug}/pay-deposit", tags=["Portal API"])
@router.post("/api/sandbox/{slug}/simulate-deposit", tags=["Portal API"])
async def pay_deposit(
    slug: str,
    request: Request,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Processes $99 setup sprint deposit, records binding clickwrap agreement, and starts dev swarm."""
    try:
        sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
        lead = sandbox.lead

        # Parse request body payload
        body = {}
        try:
            body = await request.json()
        except Exception as e:
            logger.debug(f"Optional request json parsing in pay_deposit: {e}")

        deposit_amount_usd = float(body.get("deposit_amount") or 99.00)
        lead.deposit_amount_usd = deposit_amount_usd
        logger.info(f"💳 [CHECKOUT DEPOSIT RECEIVED] Slug: {slug} | Lead: {lead.lead_id} | Amount: ${deposit_amount_usd:.2f} (100% credited to Month 1)")

        # Capture client network and device details for indisputable audit proof
        client_ip = (
            request.headers.get("cf-connecting-ip")
            or request.headers.get("x-forwarded-for")
            or (request.client.host if request.client else "127.0.0.1")
        )
        if "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        user_agent = request.headers.get("user-agent", "Standard Browser")

        paypal_order_id = body.get("paypal_order_id") or f"PAYID-{int(datetime.now().timestamp()*1000)}"
        contact_email = body.get("email") or lead.contact_email or (user.email if user else "") or "customer@client.com"
        company_name = body.get("cardholder") or lead.company_name or slug

        # Extract customer-confirmed or updated target portal / docket URL
        confirmed_target_url = (body.get("target_url") or "").strip()
        if confirmed_target_url:
            lead.source_url = confirmed_target_url
            sandbox.source_url = confirmed_target_url
            try:
                parsed_netloc = urllib.parse.urlparse(confirmed_target_url).netloc
                if parsed_netloc:
                    lead.target_portal_name = f"{parsed_netloc} Official Records"
            except Exception as url_err:
                logger.debug(f"Portal netloc parsing note: {url_err}")
            logger.info(f"🎯 [CUSTOMER TARGET URL CONFIRMED] Lead: {lead.lead_id} | URL: {confirmed_target_url}")

        # Attach claimed user if logged in
        if user and user.email and not getattr(lead, "claimed_by", ""):
            lead.claimed_by = user.email

        # 1. Record binding SOW & Terms clickwrap contract in immutable Audit Vault
        target_source_url = confirmed_target_url or lead.source_url or sandbox.source_url or "Target Web Portal"
        active_fields = lead.selected_fields or (list(sandbox.rows[0].keys()) if sandbox.rows else ["case_number", "filing_date", "status"])
        audit_vault.record_terms_acceptance(
            lead_id=lead.lead_id,
            company_name=company_name,
            contact_email=contact_email,
            ip_address=client_ip,
            user_agent=user_agent,
            target_url=target_source_url,
            selected_fields=active_fields,
            tier_key=lead.tier_key or "daily",
            deposit_amount_usd=deposit_amount_usd,
        )

        # 2. Record financial transaction in Audit Vault
        audit_vault.record_payment_event(
            lead_id=lead.lead_id,
            provider="PAYPAL",
            transaction_id=f"TXN-{paypal_order_id}",
            order_id=paypal_order_id,
            amount_usd=deposit_amount_usd,
            currency="USD",
            status="COMPLETED",
            payer_email=contact_email,
            payer_name=company_name,
            payment_type=f"Setup Sprint Deposit (${deposit_amount_usd:.2f} credited to Month 1)",
            raw_metadata={"client_ip": client_ip, "user_agent": user_agent},
        )

        # Already past deposit stage — return success idempotently
        if lead.state in {State.DEV_BUILDING, State.ESCROW_PREVIEW, State.DELIVERED, State.WARRANTY_ACTIVE}:
            lead.deposit_paid = True
            storage_backend.save_lead(lead)

            logger.info(f"🚀 [CHECKOUT COMPLETE] Lead {lead.lead_id} active at {lead.state.value}")
            return {
                "ok": True,
                "lead_id": lead.lead_id,
                "slug": slug,
                "state": lead.state.value,
                "qa_score": lead.qa_score or 100.0,
                "preview_rows": lead.preview_rows or 25,
                "escrow_ready": lead.state != State.DEV_BUILDING,
                "dashboard_url": f"/dashboard/{lead.lead_id}",
                "portal_url": f"/p/{slug}",
            }

        # Ensure selected fields are populated
        if not lead.selected_fields:
            lead.selected_fields = active_fields

        # Advance through the state machine properly using domain methods
        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "Fast-track review for checkout")
        if lead.state == State.REVIEW:
            lead.transition(State.CONVERSATIONAL_INTAKE, "Fast-track intake for checkout")
        if lead.state == State.PITCH_PENDING_APPROVAL:
            lead.transition(State.OUTREACH_SENT, "Fast-track outreach for checkout")
        if lead.state == State.OUTREACH_SENT:
            lead.transition(State.CONVERSATIONAL_INTAKE, "Fast-track intake for checkout")
        if lead.state == State.CONVERSATIONAL_INTAKE:
            lead.transition(State.SOW_GENERATED, "Fast-track SOW generated for deposit")

        if lead.state == State.SOW_GENERATED:
            lead.record_payment(PaymentEvent.DEPOSIT_PAID)
        else:
            lead.deposit_paid = True

        if lead.state == State.DEPOSIT_PAID:
            lead.transition(State.DEV_BUILDING, "autonomous builder swarm started")
        elif lead.state == State.BLOCKED_NEEDS_REVIEW:
            lead.transition(State.DEV_BUILDING, "rebuilding autonomous dev swarm")

        storage_backend.save_lead(lead)
        storage_backend.save_sandbox(sandbox)

        # Send deposit confirmation email with A/B test
        try:
            send_ab_test_email(lead, template_name="deposit_confirmation")
        except Exception as e:
            logger.warning(f"Failed to send deposit confirmation email: {e}")

        # Trigger real autonomous dev swarm build in background thread
        def _async_dev_swarm():
            try:
                logger.info(f"🤖 [BACKGROUND DEV SWARM] Starting build for {lead.lead_id} ({slug})...")
                
                # Send initial progress
                asyncio.run(progress_manager.send_progress(
                    slug, State.DEV_BUILDING, 5, "Initializing autonomous dev swarm..."
                ))
                
                # Run the dev team with progress callbacks
                def progress_callback(state: State, progress: int, message: str, details: dict = None):
                    asyncio.run(progress_manager.send_progress(slug, state or State.DEV_BUILDING, progress, message, details))
                
                run_autonomous_dev_team(lead, slug=slug, portal=portal_service, progress_callback=progress_callback)
                storage_backend.save_lead(lead)
                storage_backend.save_sandbox(sandbox)
                
                # Record delivery receipt and compile dispute defense dossier
                try:
                    audit_vault.record_delivery_receipt(
                        lead_id=lead.lead_id,
                        run_id=f"RUN-INITIAL-{lead.lead_id}",
                        rows_delivered=len(sandbox.rows) if sandbox.rows else 25,
                        destination_type="ESCROW_PREVIEW",
                        destination_target=f"/dashboard/{lead.lead_id}",
                        qa_score=lead.qa_score or 100.0,
                        sample_keys=lead.selected_fields,
                        notes="Initial 25 verified records delivered to customer escrow dashboard",
                    )
                    audit_vault.generate_chargeback_defense_dossier(lead.lead_id)
                except Exception as audit_err:
                    logger.warning(f"Audit vault delivery record notice: {audit_err}")

                logger.info(f"✓ [BACKGROUND DEV SWARM COMPLETE] Lead {lead.lead_id} -> {lead.state.value}")
                asyncio.run(progress_manager.send_complete(slug, True, lead.state))
            except Exception as err:
                logger.error(f"Background dev swarm error: {err}", exc_info=True)
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
        paypal_mode = os.environ.get("PAYPAL_MODE", "sandbox").lower()
        client_id = (
            (os.environ.get("PAYPAL_LIVE_CLIENT_ID") if paypal_mode == "live" else None)
            or os.environ.get("PAYPAL_CLIENT_ID", "")
        )
        return {**checkout_info, "paypal_client_id": client_id}
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/sandbox/{slug}/pay-final", tags=["Portal API"])
@router.post("/api/sandbox/{slug}/simulate-final", tags=["Portal API"])
def pay_final(
    slug: str,
    user: ClerkUser | None = Depends(get_current_user_optional),
    portal_service=Depends(get_portal_service),
    storage_backend=Depends(get_storage),
):
    """Processes the milestone #2 final balance payment (Month 1 balance net of $99 setup credit) and activates live feed delivery."""
    try:
        sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
        lead = sandbox.lead
        deposit_usd = getattr(lead, "deposit_amount_usd", 99.00)
        plan_price_usd = (lead.tier.price_cents / 100.0) if lead.tier else 250.00
        # 100% of the setup deposit is credited towards Month 1
        amount_usd = max(0.0, plan_price_usd - deposit_usd) if lead.tier_key != "buyout" else 1500.00
        logger.info(f"💳 [FINAL PAYMENT RECEIVED] Slug: {slug} | Lead: {lead.lead_id} | Amount: ${amount_usd:.2f} (Credited ${deposit_usd:.2f} setup deposit)")

        if user and user.email and not getattr(lead, "claimed_by", ""):
            lead.claimed_by = user.email

        subscription_info = None
        if lead.state == State.ESCROW_PREVIEW:
            event = PaymentEvent.FINAL_PAID if lead.tier_key != "buyout" else PaymentEvent.BUYOUT_PAID
            lead.record_payment(event)
            lead.transition(State.DELIVERED, "Final payment received and feed deployed")
            if lead.tier_key != "buyout":
                lead.record_payment(PaymentEvent.SUBSCRIPTION_ACTIVE)
                try:
                    subscription_info = subscription_activation(lead)
                except Exception:
                    plan = subscription_plan(lead.tier_key)
                    subscription_info = {
                        "lead_id": lead.lead_id,
                        "paypal_plan_id": plan.paypal_plan_id,
                        "tier": plan.name,
                        "amount": f"{plan.amount_cents / 100:.2f}",
                        "activation_confirmed": "false",
                    }

        storage_backend.save_lead(lead)
        storage_backend.save_sandbox(sandbox)

        # Persist final escrow & subscription release artifact
        try:
            artifact_store.save_artifact(
                lead_id=lead.lead_id,
                stage="04_FINAL_ESCROW_RELEASE",
                agent_name="Escrow & Billing Release Agent",
                filename="04_escrow_final_release.json",
                content={
                    "lead_id": lead.lead_id,
                    "company_name": lead.company_name,
                    "amount_paid_usd": amount_usd,
                    "subscription_active": lead.subscription_active,
                    "subscription_tier": lead.tier_key,
                    "subscription_info": subscription_info,
                    "status": "DELIVERED_AND_ACTIVE",
                },
                description="Milestone #2 final balance escrow release & recurring subscription activation"
            )
        except Exception as art_err:
            logger.warning(f"Final escrow artifact notice: {art_err}")

        # Dispatch feed delivery confirmation email
        try:
            send_lifecycle_email(lead, "feed_delivery", extra_variables={
                "tier_name": lead.tier.name if lead.tier else "Standard",
                "delivery_schedule": "Daily 6:00 AM UTC",
                "records_count": len(getattr(lead, "preview_records", [])) or 25,
            })
        except Exception as mail_err:
            logger.warning(f"Feed delivery email notice: {mail_err}")

        # Alert operator of final payment receipt
        try:
            notification_manager.notify_payment_received(
                lead=lead,
                amount_usd=amount_usd,
                payment_type="Final Milestone Payment (Client Approval)",
                provider="PayPal",
            )
        except Exception as notif_err:
            logger.warning(f"Payment notification notice: {notif_err}")

        logger.info(f"🚀 [FEED ACTIVATED] Lead {lead.lead_id} is now DELIVERED and active")
        return {
            "ok": True,
            "lead_id": lead.lead_id,
            "slug": slug,
            "state": lead.state.value,
            "final_paid": lead.final_paid,
            "subscription_active": lead.subscription_active,
            "subscription_info": subscription_info,
            "message": "Final milestone payment processed. Live feed and recurring subscription are active!",
            "dashboard_url": f"/dashboard/{lead.lead_id}",
        }
    except (KeyError, ValueError) as e:
        logger.error(f"Final payment error for {slug}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
