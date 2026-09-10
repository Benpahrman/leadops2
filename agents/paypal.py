"""PayPal webhook adapter for verified LeadOps payment events."""

import base64
import json
from dataclasses import dataclass
from typing import Any, Protocol

from .domain import Lead, PaymentEvent
from .paypal_config import PayPalSettings
from .payments import PaymentEventProcessor


class PayPalResponse(Protocol):
    status_code: int

    def json(self) -> dict[str, Any]: ...


class PayPalHttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        content: str | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> PayPalResponse: ...


@dataclass
class PayPalWebhookAdapter:
    client: PayPalHttpClient
    client_id: str
    client_secret: str
    webhook_id: str
    base_url: str = "https://api-m.paypal.com"
    processor: PaymentEventProcessor | None = None

    @classmethod
    def from_environment(cls, client: PayPalHttpClient) -> "PayPalWebhookAdapter":
        settings = PayPalSettings.from_environment()
        return cls(
            client,
            settings.client_id,
            settings.client_secret,
            settings.webhook_id,
            settings.base_url,
        )

    def __post_init__(self) -> None:
        self.processor = self.processor or PaymentEventProcessor()

    def verify_and_apply(
        self,
        raw_body: str,
        headers: dict[str, str],
        lead: Lead,
    ) -> bool:
        event = json.loads(raw_body)
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("PayPal webhook id is required")
        if not self._verify_signature(raw_body, headers, event):
            raise ValueError("PayPal webhook signature verification failed")
        payment_event = self._map_event(event)
        return self.processor.apply(lead, event_id, payment_event)

    def _verify_signature(
        self,
        raw_body: str,
        headers: dict[str, str],
        event: dict[str, Any],
    ) -> bool:
        access_token = self._access_token()
        verification_payload = {
            "auth_algo": self._header(headers, "PAYPAL-AUTH-ALGO"),
            "cert_url": self._header(headers, "PAYPAL-CERT-URL"),
            "transmission_id": self._header(headers, "PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": self._header(headers, "PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": self._header(headers, "PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": self.webhook_id,
            "webhook_event": event,
        }
        if any(not value for value in verification_payload.values()):
            return False
        response = self.client.post(
            f"{self.base_url}/v1/notifications/verify-webhook-signature",
            headers={"Authorization": f"Bearer {access_token}"},
            json=verification_payload,
        )
        return response.status_code == 200 and response.json().get("verification_status") == "SUCCESS"

    def _access_token(self) -> str:
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        response = self.client.post(
            f"{self.base_url}/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        if response.status_code != 200:
            raise ValueError("PayPal access token request failed")
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise ValueError("PayPal access token was missing")
        return token

    @staticmethod
    def _map_event(event: dict[str, Any]) -> PaymentEvent:
        event_type = event.get("event_type")
        resource = event.get("resource") or {}
        if event_type == "BILLING.SUBSCRIPTION.ACTIVATED":
            return PaymentEvent.SUBSCRIPTION_ACTIVE
        if event_type != "PAYMENT.CAPTURE.COMPLETED":
            raise ValueError(f"Unsupported PayPal event: {event_type}")
        payment_kind = resource.get("custom_id")
        if payment_kind == "deposit":
            return PaymentEvent.DEPOSIT_PAID
        if payment_kind == "final":
            return PaymentEvent.FINAL_PAID
        if payment_kind == "buyout":
            return PaymentEvent.BUYOUT_PAID

        # Fallback to invoice_id prefix inspection if custom_id was used for lead identification
        invoice_id = str(resource.get("invoice_id", ""))
        if invoice_id.startswith("setup-"):
            return PaymentEvent.DEPOSIT_PAID
        if invoice_id.startswith("final-"):
            return PaymentEvent.FINAL_PAID

        raise ValueError("PayPal capture custom_id must be deposit, final, or buyout")

    @staticmethod
    def _header(headers: dict[str, str], name: str) -> str:
        return next((value for key, value in headers.items() if key.lower() == name.lower()), "")