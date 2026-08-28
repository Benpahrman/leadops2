import logging
from fastapi import APIRouter, Depends, HTTPException, Request

from ..paypal_config import PayPalSettings
from ..paypal_http import PayPalHttpClient
from ..paypal_webhook import PayPalWebhookRouter
from .dependencies import get_storage

logger = logging.getLogger("api.payments")

router = APIRouter()

@router.post("/api/paypal/webhook", tags=["Payments"])
async def paypal_webhook(
    request: Request,
    storage_backend=Depends(get_storage),
):
    raw_body = (await request.body()).decode("utf-8")
    headers = dict(request.headers)
    leads_map = {l.lead_id: l for l in storage_backend.list_leads()}
    try:
        router = PayPalWebhookRouter.from_environment(PayPalHttpClient())
        applied = router.route(raw_body, headers, leads_map)
        return {"received": True, "applied": applied}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook processing error: {e}")
