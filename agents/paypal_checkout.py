"""PayPal Checkout order creation; payment confirmation remains webhook-only."""

import base64
from dataclasses import dataclass
from typing import Any, Protocol

from .domain import Lead, State
from .paypal_config import PayPalSettings


class CheckoutResponse(Protocol):
    status_code: int

    def json(self) -> dict[str, Any]: ...


class CheckoutHttpClient(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        data: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> CheckoutResponse: ...


@dataclass
class PayPalCheckout:
    client: CheckoutHttpClient
    client_id: str
    client_secret: str
    base_url: str = "https://api-m.paypal.com"

    @classmethod
    def from_environment(cls, client: CheckoutHttpClient) -> "PayPalCheckout":
        settings = PayPalSettings.from_environment()
        return cls(client, settings.client_id, settings.client_secret, settings.base_url)

    def create_setup_order(self, lead: Lead) -> dict[str, Any]:
        """Create a 50% setup order after SOW generation, never mark it paid."""
        if lead.state != State.SOW_GENERATED:
            raise ValueError("Checkout requires an approved scope and generated SOW")
        purpose = "buyout" if lead.tier_key == "buyout" else "deposit"
        amount = f"{lead.tier.price_cents / 200:.2f}"
        response = self.client.post(
            f"{self.base_url}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "custom_id": purpose,
                    "invoice_id": f"setup-{lead.lead_id}",
                    "amount": {"currency_code": "USD", "value": amount},
                }],
                "application_context": {"user_action": "PAY_NOW"},
            },
        )
        if response.status_code not in {200, 201}:
            raise ValueError("PayPal order creation failed")
        order = response.json()
        if not isinstance(order.get("id"), str) or not order["id"]:
            raise ValueError("PayPal order id was missing")
        return {"order_id": order["id"], "purpose": purpose, "amount": amount}

    def create_final_order(self, lead: Lead) -> dict[str, Any]:
        """Create the remaining setup-payment order after escrow preview."""
        if lead.state != State.ESCROW_PREVIEW:
            raise ValueError("Final checkout requires an approved escrow preview")
        amount = f"{lead.tier.price_cents / 200:.2f}"
        response = self.client.post(
            f"{self.base_url}/v2/checkout/orders",
            headers={
                "Authorization": f"Bearer {self._access_token()}",
                "Content-Type": "application/json",
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "custom_id": "final",
                    "invoice_id": f"final-{lead.lead_id}",
                    "amount": {"currency_code": "USD", "value": amount},
                }],
                "application_context": {"user_action": "PAY_NOW"},
            },
        )
        if response.status_code not in {200, 201}:
            raise ValueError("PayPal final order creation failed")
        order = response.json()
        if not isinstance(order.get("id"), str) or not order["id"]:
            raise ValueError("PayPal final order id was missing")
        return {"order_id": order["id"], "purpose": "final", "amount": amount}

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