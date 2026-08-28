"""Environment-backed PayPal configuration with sandbox-safe defaults."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PayPalSettings:
    client_id: str
    client_secret: str
    webhook_id: str
    mode: str = "sandbox"
    return_url: str = "http://localhost:8765/payment/success"
    cancel_url: str = "http://localhost:8765/payment/cancel"

    @property
    def base_url(self) -> str:
        return (
            "https://api-m.sandbox.paypal.com"
            if self.mode == "sandbox"
            else "https://api-m.paypal.com"
        )

    @classmethod
    def from_environment(cls) -> "PayPalSettings":
        mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
        if mode not in {"sandbox", "live"}:
            raise ValueError("PAYPAL_MODE must be sandbox or live")
        values = {
            "client_id": os.getenv("PAYPAL_CLIENT_ID", ""),
            "client_secret": os.getenv("PAYPAL_CLIENT_SECRET", ""),
            "webhook_id": os.getenv("PAYPAL_WEBHOOK_ID", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise ValueError(f"Missing PayPal settings: {', '.join(missing)}")
        return cls(
            **values,
            mode=mode,
            return_url=os.getenv("PAYPAL_RETURN_URL", cls.return_url),
            cancel_url=os.getenv("PAYPAL_CANCEL_URL", cls.cancel_url),
        )