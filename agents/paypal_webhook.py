"""Route verified PayPal webhook events to the correct Lead record."""

import json
from dataclasses import dataclass
from typing import Any

from .domain import Lead
from .paypal import PayPalHttpClient, PayPalWebhookAdapter


@dataclass
class PayPalWebhookRouter:
    adapter: PayPalWebhookAdapter

    @classmethod
    def from_environment(cls, client: PayPalHttpClient) -> "PayPalWebhookRouter":
        return cls(PayPalWebhookAdapter.from_environment(client))

    def route(
        self,
        raw_body: str,
        headers: dict[str, str],
        leads: dict[str, Lead],
    ) -> bool:
        event = json.loads(raw_body)
        lead_id = self._lead_id(event)
        if not lead_id or lead_id not in leads:
            raise ValueError("PayPal webhook does not identify a known lead")
        return self.adapter.verify_and_apply(raw_body, headers, leads[lead_id])

    @staticmethod
    def _lead_id(event: dict[str, Any]) -> str:
        resource = event.get("resource") or {}
        invoice_id = resource.get("invoice_id", "")
        if isinstance(invoice_id, str):
            for prefix in ("setup-", "final-"):
                if invoice_id.startswith(prefix):
                    return invoice_id[len(prefix):]
        custom_id = resource.get("custom_id", "")
        if isinstance(custom_id, str) and custom_id.startswith("lead:"):
            return custom_id[5:]
        return ""