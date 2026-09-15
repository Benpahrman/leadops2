"""Azure Communication Services (ACS) Email Client for LeadOps Swarm.

Provides high-deliverability dispatch through Azure's Port 443 REST API:
- DKIM & SPF signing handled natively by Azure Communication Services.
- Rate-limiting guardrail enforcing <100 emails/hour custom domain throttle.
- Pure plain-text delivery eliminating open-tracking pixel deliverability penalties.
- Strict single-message asynchronous polling avoiding 429 concurrency blocks.
"""

import collections
import logging
import os
import time
from typing import Any, Callable

logger = logging.getLogger("leadops.email.acs")

DEFAULT_ACS_SENDER = "ben@olfmailer.com"
MAX_HOURLY_DISPATCH_LIMIT = 95  # Azure custom domains enforce a hard cap of 100 emails/hour


class AzureCommunicationEmailClient:
    """Production client for dispatching transactional and warm-up emails via Azure Communication Services."""

    def __init__(
        self,
        connection_string: str | None = None,
        default_sender: str | None = None,
        transport_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self.connection_string = (
            connection_string
            if connection_string is not None
            else (os.environ.get("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING") or "")
        ).strip().strip("\"'")

        self.default_sender = (
            default_sender
            or os.environ.get("AZURE_COMMUNICATION_SENDER_EMAIL")
            or DEFAULT_ACS_SENDER
        ).strip()

        self.transport_hook = transport_hook
        self._dispatch_timestamps: collections.deque = collections.deque()
        self._sdk_client: Any = None

    @property
    def is_configured(self) -> bool:
        """Return True if connection string is configured and valid."""
        return bool(self.connection_string and "endpoint=" in self.connection_string.lower())

    def _get_sdk_client(self) -> Any:
        """Lazily initialize the Azure SDK EmailClient."""
        if self._sdk_client is not None:
            return self._sdk_client

        if not self.is_configured:
            return None

        try:
            from azure.communication.email import EmailClient
            self._sdk_client = EmailClient.from_connection_string(self.connection_string)
            return self._sdk_client
        except Exception as exc:
            logger.error(f"Failed to instantiate Azure EmailClient: {exc}")
            return None

    def _enforce_rate_limit(self) -> None:
        """Guardrail: Ensure hourly dispatch volume does not exceed Azure's 100 emails/hour cap."""
        now = time.time()
        one_hour_ago = now - 3600.0

        # Purge timestamps older than 1 hour
        while self._dispatch_timestamps and self._dispatch_timestamps[0] < one_hour_ago:
            self._dispatch_timestamps.popleft()

        # If reaching hourly threshold, delay dispatch to stay under Azure limit
        if len(self._dispatch_timestamps) >= MAX_HOURLY_DISPATCH_LIMIT:
            oldest = self._dispatch_timestamps[0]
            sleep_duration = max(1.0, (oldest + 3601.0) - now)
            logger.warning(
                f"⚠️ [ACS RATE LIMIT GUARD] {len(self._dispatch_timestamps)} emails sent in past hour. "
                f"Pausing dispatch for {sleep_duration:.1f}s to respect Azure 100/hr limit."
            )
            time.sleep(sleep_duration)

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
        sender_address: str | None = None,
        is_transactional: bool = False,
    ) -> dict[str, Any]:
        """Dispatch a single email message via Azure Communication Services.
        
        Args:
            to_email: Target recipient email address.
            to_name: Recipient display name.
            subject: Email subject line.
            text_body: Plain text email body (optimal deliverability).
            html_body: Optional HTML body (omitted for Touch 1 deliverability).
            sender_address: Explicit sender address (e.g., ben@olfmailer.com).
            is_transactional: Whether this is a critical transactional export.
        """
        sender = (sender_address or self.default_sender).strip()

        # Unit test or mock hook interceptor
        if self.transport_hook is not None:
            return self.transport_hook({
                "to_email": to_email,
                "to_name": to_name,
                "subject": subject,
                "text_body": text_body,
                "html_body": html_body,
                "sender": sender,
                "from_email": sender,
                "is_transactional": is_transactional,
            })

        # Development / dry-run fallback if no live connection string
        if not self.is_configured:
            logger.warning(
                f"🛡️ [ACS DRY-RUN] AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING not set. "
                f"Simulating dispatch to '{to_email}' with subject '{subject}'. Zero live network calls."
            )
            return {
                "ok": True,
                "status": "SIMULATED_NO_CONNECTION_STRING",
                "message_id": f"simulated-acs-{int(time.time()*1000)}",
                "recipient": to_email,
                "sender": sender,
            }

        # Enforce rate limit before calling Azure
        self._enforce_rate_limit()

        sdk_client = self._get_sdk_client()
        if not sdk_client:
            return {
                "ok": False,
                "error": "Failed to initialize Azure EmailClient SDK",
                "status": "INITIALIZATION_FAILED",
                "recipient": to_email,
            }

        # Build message payload per Azure Communication Services specification
        content_payload: dict[str, Any] = {
            "subject": subject,
            "plainText": text_body,
        }
        if html_body:
            content_payload["html"] = html_body

        message = {
            "senderAddress": sender,
            "recipients": {
                "to": [
                    {"address": to_email, "displayName": to_name}
                ]
            },
            "content": content_payload,
        }

        try:
            logger.info(f"📤 [ACS DISPATCH] Dispatching via Azure API: {sender} -> {to_email} | Subject: '{subject}'")
            poller = sdk_client.begin_send(message)
            result = poller.result()

            status = result.get("status", "Unknown") if isinstance(result, dict) else getattr(result, "status", "Succeeded")
            message_id = result.get("id", "") if isinstance(result, dict) else getattr(result, "id", "")

            # Record timestamp for sliding window rate limiter
            self._dispatch_timestamps.append(time.time())

            logger.info(f"✅ [ACS DISPATCH SUCCESS] Status: {status} | Message ID: {message_id}")
            return {
                "ok": status in ("Succeeded", "Running", "Unknown"),
                "status": status,
                "message_id": message_id,
                "recipient": to_email,
                "sender": sender,
            }
        except Exception as exc:
            logger.error(f"❌ [ACS DISPATCH ERROR] Failed to send to '{to_email}': {exc}")
            return {
                "ok": False,
                "error": str(exc),
                "status": "DISPATCH_FAILED",
                "recipient": to_email,
                "sender": sender,
            }
