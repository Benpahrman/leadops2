from dataclasses import dataclass, field
from typing import Any

from .domain import Lead, PaymentEvent


@dataclass
class PaymentEventProcessor:
    """Apply already-verified events exactly once per lead with durable idempotency."""

    processed_event_ids: set[str] = field(default_factory=set)
    storage: Any | None = None

    def apply(self, lead: Lead, event_id: str, event: PaymentEvent) -> bool:
        if not event_id:
            raise ValueError("A provider event id is required")
        if self.storage:
            if not self.storage.record_webhook_event(event_id):
                return False
        else:
            if event_id in self.processed_event_ids:
                return False
            self.processed_event_ids.add(event_id)

        lead.record_payment(event)
        if self.storage:
            self.storage.save_lead(lead)
        return True