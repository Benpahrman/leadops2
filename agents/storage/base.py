"""Base interfaces, protocols, and string normalizers for storage."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Protocol

from ..domain import Lead, State
from ..progress import ProgressFeed, ProgressStatus
from ..logging_config import get_logger

logger = get_logger("storage.base")

def normalize_company_name(name: str) -> str:
    """Normalize company name by stripping punctuation, whitespace, trailing digits, and corporate entity suffixes."""
    if not name:
        return ""
    import re
    s = str(name).lower().strip()
    s = re.sub(r"\s+\d{3,}.*$", "", s).strip()
    s = s.replace(".", "").replace(",", " ")
    pattern = r"\b(llc|inc|incorporated|corp|corporation|co|company|ltd|limited|pllc|pc|llp|lp|group|holdings|associates|partners|services|enterprise|enterprises)\b"
    s = re.sub(pattern, "", s)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def normalize_domain(domain_or_url: str) -> str:
    """Normalize domain by stripping protocol, www., paths, ports, query strings."""
    if not domain_or_url:
        return ""
    import re
    d = str(domain_or_url).lower().strip()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.split("/")[0].split("?")[0].split(":")[0].strip()
    return d


class StorageBackend(Protocol):
    """Protocol for persisting leads, sandboxes, and webhook idempotency records."""

    def check_prospect_deduplication(
        self,
        company_name: str = "",
        domain: str = "",
        email: str = "",
        exclude_lead_id: str = "",
    ) -> tuple[bool, str]: ...

    def save_lead(self, lead: Lead) -> None: ...

    def get_lead(self, lead_id: str) -> Lead | None: ...

    def list_leads(self) -> list[Lead]: ...

    def save_sandbox(self, sandbox: Any) -> None: ...

    def get_sandbox(self, slug: str) -> Any | None: ...

    def list_sandboxes(self) -> list[Any]: ...

    def record_webhook_event(self, event_id: str) -> bool: ...

    def has_webhook_event(self, event_id: str) -> bool: ...

    # Ticket operations
    def save_ticket(self, ticket: Any) -> None: ...

    def get_ticket(self, ticket_id: str) -> Any | None: ...

    def list_tickets(self, lead_id: str | None = None) -> list[Any]: ...

    # Cancellation operations
    def save_cancellation_request(self, request: Any) -> None: ...

    def get_cancellation_request(self, request_id: str) -> Any | None: ...

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]: ...

    # Email template operations
    def save_email_template(self, template: Any) -> None: ...

    def get_email_template(self, template_id: str) -> Any | None: ...

    def list_email_templates(self) -> list[Any]: ...

    # Native email module operations
    def record_email_sent(self, inbox_id: str, recipient: str, lead_id: str, dispatched_at: str) -> None: ...

    def get_email_sent_count_today(self, inbox_id: str = "") -> int: ...

    def is_recipient_or_domain_contacted(
        self, email: str = "", domain: str = "", company_name: str = "", within_days: int = 45, exclude_lead_id: str = ""
    ) -> bool: ...

    def record_inbound_email(
        self,
        message_id: str,
        sender_email: str,
        sender_name: str,
        subject: str,
        body: str,
        intent: str,
        draft_reply: str,
        lead_id: str = "",
    ) -> None: ...

    def list_inbound_emails(self, lead_id: str | None = None) -> list[dict[str, Any]]: ...

    # Multi-Inbox management operations
    def list_inbox_accounts(self) -> list[dict[str, Any]]: ...

    def get_inbox_account(self, inbox_id: str) -> dict[str, Any] | None: ...

    def upsert_inbox_account(self, account: dict[str, Any]) -> None: ...

    def delete_inbox_account(self, inbox_id: str) -> None: ...

    def record_chat_message(
        self,
        conversation_id: str,
        sender: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def list_chat_messages(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]: ...

    def backup_db(self, target_path: str | None = None) -> str: ...

    def purge_all_data(self) -> dict[str, int]: ...

    def delete_lead(self, lead_id: str) -> bool: ...

    # Deliverability & Spam Assessment operations
    def save_deliverability_audit(self, report: dict[str, Any]) -> None: ...

    def get_latest_deliverability_audit(self) -> dict[str, Any] | None: ...

    def list_deliverability_audits(self, limit: int = 10) -> list[dict[str, Any]]: ...



