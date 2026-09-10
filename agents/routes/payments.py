import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from ..paypal_config import PayPalSettings
from ..paypal_http import PayPalHttpClient
from ..paypal_webhook import PayPalWebhookRouter
from .dependencies import get_portal_service, get_storage

logger = logging.getLogger("api.payments")

router = APIRouter()

# Required PayPal webhook headers for verification
REQUIRED_PAYPAL_HEADERS = [
    "PAYPAL-AUTH-ALGO",
    "PAYPAL-CERT-URL",
    "PAYPAL-TRANSMISSION-ID",
    "PAYPAL-TRANSMISSION-SIG",
    "PAYPAL-TRANSMISSION-TIME",
]


@router.post("/api/paypal/webhook", tags=["Payments"])
async def paypal_webhook(
    request: Request,
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    # Verify required PayPal transmission headers before processing
    headers = dict(request.headers)
    missing_headers = [h for h in REQUIRED_PAYPAL_HEADERS if h not in headers]
    if missing_headers:
        logger.warning(f"PayPal webhook missing required headers: {missing_headers}")
        raise HTTPException(
            status_code=400,
            detail=f"Missing required PayPal headers: {', '.join(missing_headers)}"
        )
    
    raw_body = (await request.body()).decode("utf-8")
    leads_map = {l.lead_id: l for l in storage_backend.list_leads()}
    try:
        router = PayPalWebhookRouter.from_environment(PayPalHttpClient())
        applied = router.route(raw_body, headers, leads_map)
        event = json.loads(raw_body)
        resource = event.get("resource") or {}
        lead_id = resource.get("invoice_id", "")
        if isinstance(lead_id, str) and lead_id.startswith(("setup-", "final-")):
            lead_id = lead_id.split("-", 1)[1]
        custom_id = resource.get("custom_id", "")
        if isinstance(custom_id, str) and custom_id.startswith("lead:"):
            lead_id = custom_id[5:]
        elif isinstance(custom_id, str) and custom_id in leads_map:
            lead_id = custom_id

        lead = leads_map.get(lead_id)
        if applied and lead and lead.deposit_paid and lead.state.value == "DEPOSIT_PAID":
            import threading
            from ..domain import State
            from ..workflow import run_autonomous_dev_team
            from ..audit_vault import audit_vault

            # Extract PayPal Vault token for off-session final milestone capture
            payment_source = resource.get("payment_source") or {}
            paypal_src = payment_source.get("paypal") or {}
            vault_id = (
                paypal_src.get("attributes", {}).get("vault", {}).get("id")
                or paypal_src.get("vault_id")
                or resource.get("vault_id", "")
            )
            if vault_id:
                lead.paypal_vault_id = vault_id
                logger.info(f"🔐 [PAYPAL VAULT TOKEN STORED] Lead: {lead.lead_id} | Vault Token: {vault_id}")

            # Record verified PayPal webhook event in Audit Vault
            try:
                amount_val = float(resource.get("amount", {}).get("value", 99.00)) if isinstance(resource.get("amount"), dict) else 99.00
                currency_val = resource.get("amount", {}).get("currency_code", "USD") if isinstance(resource.get("amount"), dict) else "USD"
                audit_vault.record_payment_event(
                    lead_id=lead.lead_id,
                    provider="PAYPAL",
                    transaction_id=resource.get("id", f"TXN-{int(time.time()*1000)}"),
                    order_id=resource.get("parent_payment", resource.get("id", "ORDER-WEBHOOK")),
                    amount_usd=amount_val,
                    currency=currency_val,
                    status="COMPLETED",
                    payer_email=resource.get("payer", {}).get("email_address", lead.contact_email),
                    payer_name=lead.company_name,
                    payment_type=f"Setup Sprint Deposit (${amount_val:.2f} credited to Month 1)",
                    raw_metadata=event,
                )
            except Exception as audit_err:
                logger.warning(f"Audit vault payment recording notice: {audit_err}")

            # Notify operator of setup deposit captured
            try:
                from ..notifications import notification_manager
                notification_manager.notify_payment_received(
                    lead=lead,
                    amount_usd=amount_val,
                    payment_type="Setup Sprint Deposit",
                    provider="PayPal",
                    transaction_id=str(resource.get("id", "")),
                )
            except Exception as notif_err:
                logger.warning(f"Payment notification notice: {notif_err}")

            lead.transition(State.DEV_BUILDING, "Verified PayPal deposit received; autonomous dev swarm started")
            storage_backend.save_lead(lead)

            def _start_dev_swarm() -> None:
                try:
                    run_autonomous_dev_team(lead, slug=lead.slug or lead.lead_id, portal=portal_service)
                    storage_backend.save_lead(lead)
                except Exception:
                    logger.exception("Verified deposit build kickoff failed for lead %s", lead.lead_id)

            threading.Thread(target=_start_dev_swarm, daemon=True).start()
        return {"received": True, "applied": applied}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing error: {e}")


@router.post("/api/paypal/create-order/{slug}", tags=["Payments"])
async def create_paypal_order(
    slug: str,
    request: Request,
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Creates a real PayPal order against live PayPal API and returns order ID and approve URL."""
    from .portal import ensure_demo_sandbox
    from ..domain import State
    from ..paypal_checkout import PayPalCheckout

    sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
    lead = sandbox.lead

    body = {}
    try:
        body = await request.json()
    except Exception as e:
        logger.debug(f"Optional request json parsing in create-order: {e}")

    deposit_amount = float(body.get("deposit_amount") or getattr(lead, "deposit_amount_usd", 99.00) or 99.00)
    lead.deposit_amount_usd = deposit_amount

    target_url = (body.get("target_url") or "").strip()
    if target_url:
        lead.source_url = target_url
        sandbox.source_url = target_url

    email = body.get("email")
    if email:
        lead.contact_email = email

    cardholder = body.get("cardholder")
    if cardholder:
        lead.company_name = cardholder

    if lead.state in (State.PROSPECTING, State.OUTREACH_SENT, State.REVIEW):
        lead.transition(State.CONVERSATIONAL_INTAKE, "Client visited portal and initiated intake")
    if lead.state == State.CONVERSATIONAL_INTAKE:
        lead.transition(State.SOW_GENERATED, "Client opened checkout modal; SOW generated")

    storage_backend.save_lead(lead)
    storage_backend.save_sandbox(sandbox)

    checkout = PayPalCheckout.from_environment(PayPalHttpClient())
    try:
        order_info = checkout.create_setup_order(lead)
        lead.paypal_order_id = order_info["order_id"]
        storage_backend.save_lead(lead)
        logger.info(f"✅ [PAYPAL ORDER CREATED] Slug: {slug} | Order ID: {order_info['order_id']} | Amount: ${order_info['amount']}")
        return {
            "success": True,
            "order_id": order_info["order_id"],
            "approve_url": order_info.get("approve_url", f"https://www.paypal.com/checkoutnow?token={order_info['order_id']}"),
            "amount": order_info["amount"],
            "purpose": order_info.get("purpose", "deposit"),
        }
    except Exception as e:
        logger.error(f"❌ [PAYPAL ORDER CREATION ERROR] Slug: {slug} | Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create PayPal order: {str(e)}")


@router.post("/api/paypal/capture-order/{slug}", tags=["Payments"])
async def capture_paypal_order(
    slug: str,
    request: Request,
    storage_backend=Depends(get_storage),
    portal_service=Depends(get_portal_service),
):
    """Captures an approved PayPal order directly via server-to-server Live API."""
    import base64
    import httpx
    import threading
    import time
    from datetime import datetime
    from .portal import ensure_demo_sandbox
    from ..domain import State
    from ..audit_vault import audit_vault
    from ..workflow import run_autonomous_dev_team

    sandbox = ensure_demo_sandbox(slug, portal_service, storage_backend)
    lead = sandbox.lead

    body = {}
    try:
        body = await request.json()
    except Exception as e:
        logger.debug(f"Optional request json parsing in capture-order: {e}")

    order_id = body.get("order_id") or getattr(lead, "paypal_order_id", "")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id for PayPal capture")

    settings = PayPalSettings.from_environment()
    auth = base64.b64encode(f"{settings.client_id}:{settings.client_secret}".encode()).decode()

    async with httpx.AsyncClient(timeout=30.0) as client:
        tok_resp = await client.post(
            f"{settings.base_url}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"},
        )
        if tok_resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to authenticate with PayPal")
        access_token = tok_resp.json().get("access_token")

        capture_resp = await client.post(
            f"{settings.base_url}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        capture_data = capture_resp.json()

    status = capture_data.get("status")
    # In PayPal v2 orders, already captured orders or completed orders return COMPLETED
    if status not in ("COMPLETED", "APPROVED") and "ORDER_ALREADY_CAPTURED" not in capture_resp.text:
        logger.error(f"PayPal capture failed: {capture_resp.status_code} - {capture_resp.text}")
        raise HTTPException(status_code=400, detail=f"PayPal capture status: {status or 'FAILED'}")

    captures = (
        capture_data.get("purchase_units", [{}])[0]
        .get("payments", {})
        .get("captures", [{}])
    )
    capture_id = captures[0].get("id") if captures else order_id
    deposit_amount = float(getattr(lead, "deposit_amount_usd", 99.00) or 99.00)
    lead.deposit_amount_usd = deposit_amount
    lead.deposit_paid = True
    lead.paypal_order_id = order_id

    # Record client details
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else "127.0.0.1")
    )
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    user_agent = request.headers.get("user-agent", "Standard Browser")

    contact_email = body.get("email") or lead.contact_email or "customer@client.com"
    company_name = body.get("cardholder") or lead.company_name or slug

    # Record clickwrap agreement in AuditVault
    target_url = lead.source_url or sandbox.source_url or "Target Web Portal"
    active_fields = lead.selected_fields or (list(sandbox.rows[0].keys()) if sandbox.rows else ["case_number", "filing_date", "status"])
    audit_vault.record_terms_acceptance(
        lead_id=lead.lead_id,
        company_name=company_name,
        contact_email=contact_email,
        ip_address=client_ip,
        user_agent=user_agent,
        target_url=target_url,
        selected_fields=active_fields,
        tier_key=lead.tier_key or "daily",
        deposit_amount_usd=deposit_amount,
    )

    # Record financial transaction in AuditVault
    audit_vault.record_payment_event(
        lead_id=lead.lead_id,
        provider="PAYPAL",
        transaction_id=f"TXN-{capture_id}",
        order_id=order_id,
        amount_usd=deposit_amount,
        currency="USD",
        status="COMPLETED",
        payer_email=contact_email,
        payer_name=company_name,
        payment_type=f"Setup Sprint Deposit (${deposit_amount:.2f} credited to Month 1)",
        raw_metadata={"client_ip": client_ip, "user_agent": user_agent, "capture_id": capture_id},
    )

    # Transition state and start dev swarm
    lead.transition(State.DEV_BUILDING, "Verified PayPal deposit received; autonomous dev swarm started")
    storage_backend.save_lead(lead)
    storage_backend.save_sandbox(sandbox)

    try:
        from ..notifications import notification_manager
        notification_manager.notify_payment_received(
            lead=lead,
            amount_usd=deposit_amount,
            payment_type=f"Setup Sprint Deposit (${deposit_amount:.2f} credited)",
            provider="PayPal Live",
            transaction_id=str(capture_id),
        )
    except Exception as notif_err:
        logger.warning(f"Payment notification notice: {notif_err}")

    def _start_dev_swarm() -> None:
        try:
            run_autonomous_dev_team(lead, slug=lead.slug or lead.lead_id, portal=portal_service)
            storage_backend.save_lead(lead)
        except Exception:
            logger.exception("Verified deposit build kickoff failed for lead %s", lead.lead_id)

    threading.Thread(target=_start_dev_swarm, daemon=True).start()

    return {
        "success": True,
        "lead_id": lead.lead_id,
        "status": "COMPLETED",
        "capture_id": capture_id,
        "amount": deposit_amount,
    }
