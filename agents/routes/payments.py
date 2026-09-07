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
                amount_val = float(resource.get("amount", {}).get("value", 250.00)) if isinstance(resource.get("amount"), dict) else 250.00
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
                    payment_type="50% Milestone Setup Deposit (Webhook Confirmed)",
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
                    payment_type="50% Milestone Setup Deposit",
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
