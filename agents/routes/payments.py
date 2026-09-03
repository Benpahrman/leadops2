import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from ..paypal_config import PayPalSettings
from ..paypal_http import PayPalHttpClient
from ..paypal_webhook import PayPalWebhookRouter
from .dependencies import get_storage

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
        return {"received": True, "applied": applied}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing error: {e}")
