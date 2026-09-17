"""In-memory storage backend implementation for isolated unit testing."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from ..domain import Lead, State
from ..progress import ProgressFeed, ProgressStatus
from ..logging_config import get_logger
from .base import normalize_company_name, normalize_domain

logger = get_logger("storage.memory")

class InMemoryStorageBackend:
    """In-memory storage backend for isolated unit testing."""

    def __init__(self) -> None:
        self.leads: dict[str, Lead] = {}
        self.sandboxes: dict[str, Any] = {}
        self.webhook_events: set[str] = set()
        self.tickets: dict[str, Any] = {}
        self.cancellation_requests: dict[str, Any] = {}
        self.email_templates: dict[str, Any] = {}
        self.sequence_dispatch_log: dict[str, dict[str, Any]] = {}
        self.global_suppression_list: set[str] = set()

    def record_sequence_dispatch(
        self,
        idempotency_key: str,
        lead_id: str,
        touch_number: int,
        recipient_email: str,
        status: str = "DISPATCHED",
        metadata: dict | None = None,
    ) -> bool:
        if idempotency_key in self.sequence_dispatch_log:
            return False
        self.sequence_dispatch_log[idempotency_key] = {
            "idempotency_key": idempotency_key,
            "lead_id": lead_id,
            "touch_number": touch_number,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "recipient_email": recipient_email,
            "status": status,
            "metadata": metadata or {},
        }
        return True

    def has_sequence_dispatch(self, idempotency_key: str) -> bool:
        return idempotency_key in self.sequence_dispatch_log

    def add_to_global_suppression(self, identifier: str, reason: str = "") -> None:
        if identifier:
            self.global_suppression_list.add(identifier.strip().lower())

    def is_globally_suppressed(self, email: str = "", domain: str = "") -> bool:
        email_clean = (email or "").strip().lower()
        domain_clean = (domain or (email_clean.split("@")[-1] if "@" in email_clean else "")).strip().lower()
        if email_clean and email_clean in self.global_suppression_list:
            return True
        if domain_clean and domain_clean in self.global_suppression_list:
            return True
        for l in self.leads.values():
            if getattr(l, "opt_out", False):
                if (l.contact_email or "").strip().lower() == email_clean:
                    return True
        return False

    def save_lead(self, lead: Lead) -> None:
        self.leads[lead.lead_id] = lead

    def get_lead(self, lead_id: str) -> Lead | None:
        return self.leads.get(lead_id)

    def list_leads(self) -> list[Lead]:
        return list(self.leads.values())

    def save_sandbox(self, sandbox: Any) -> None:
        self.sandboxes[sandbox.slug] = sandbox
        self.save_lead(sandbox.lead)

    def get_sandbox(self, slug: str) -> Any | None:
        return self.sandboxes.get(slug)

    def list_sandboxes(self) -> list[Any]:
        return list(self.sandboxes.values())

    def record_webhook_event(self, event_id: str) -> bool:
        if not event_id or event_id in self.webhook_events:
            return False
        self.webhook_events.add(event_id)
        return True

    def has_webhook_event(self, event_id: str) -> bool:
        return event_id in self.webhook_events

    def save_ticket(self, ticket: Any) -> None:
        self.tickets[ticket.ticket_id] = ticket

    def get_ticket(self, ticket_id: str) -> Any | None:
        return self.tickets.get(ticket_id)

    def list_tickets(self, lead_id: str | None = None) -> list[Any]:
        if lead_id:
            return [t for t in self.tickets.values() if t.lead_id == lead_id]
        return list(self.tickets.values())

    def save_cancellation_request(self, request: Any) -> None:
        self.cancellation_requests[request.request_id] = request

    def get_cancellation_request(self, request_id: str) -> Any | None:
        return self.cancellation_requests.get(request_id)

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]:
        if lead_id:
            return [r for r in self.cancellation_requests.values() if r.lead_id == lead_id]
        return list(self.cancellation_requests.values())

    def save_email_template(self, template: Any) -> None:
        self.email_templates[template.template_id] = template

    def get_email_template(self, template_id: str) -> Any | None:
        return self.email_templates.get(template_id)

    def list_email_templates(self) -> list[Any]:
        return list(self.email_templates.values())

    def record_email_sent(self, inbox_id: str, recipient: str, lead_id: str, dispatched_at: str) -> None:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not hasattr(self, "_sent_email_logs"):
            self._sent_email_logs = []
        self._sent_email_logs.append({
            "inbox_id": inbox_id,
            "recipient": recipient,
            "lead_id": lead_id,
            "dispatched_at": dispatched_at,
            "sent_date": today_str,
        })

    def get_email_sent_count_today(self, inbox_id: str = "") -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not hasattr(self, "_sent_email_logs"):
            return 0
        if inbox_id:
            return sum(1 for e in self._sent_email_logs if e["inbox_id"] == inbox_id and e["sent_date"] == today_str)
        return sum(1 for e in self._sent_email_logs if e["sent_date"] == today_str)

    def is_recipient_or_domain_contacted(
        self, email: str = "", domain: str = "", company_name: str = "", within_days: int = 45, exclude_lead_id: str = ""
    ) -> bool:
        import re
        email_clean = (email or "").lower().strip()
        domain_clean = (domain or (email_clean.split("@")[-1] if "@" in email_clean else "")).lower().strip()
        comp_norm = re.sub(r"[^a-z0-9]", "", company_name.lower()) if company_name else ""

        # 1. Check sent email logs
        if hasattr(self, "_sent_email_logs"):
            for log in self._sent_email_logs:
                if exclude_lead_id and log.get("lead_id") == exclude_lead_id:
                    continue
                rec = (log.get("recipient") or "").lower().strip()
                if email_clean and rec == email_clean:
                    return True
                if domain_clean and domain_clean not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"):
                    if rec.endswith(f"@{domain_clean}"):
                        return True

        # 2. Check active and historical leads
        for lead in self.leads.values():
            if exclude_lead_id and lead.lead_id == exclude_lead_id:
                continue
            l_email = (getattr(lead, "contact_email", "") or "").lower().strip()
            l_comp = getattr(lead, "company_name", "") or ""
            l_comp_norm = re.sub(r"[^a-z0-9]", "", l_comp.lower())
            l_state = getattr(lead, "state", None)
            l_state_val = l_state.value if hasattr(l_state, "value") else str(l_state)

            if email_clean and l_email == email_clean:
                if l_state_val in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                    return True

            if domain_clean and domain_clean not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"):
                if l_email.endswith(f"@{domain_clean}") and l_state_val in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                    return True

            if comp_norm and len(comp_norm) >= 4 and l_comp_norm:
                if (comp_norm == l_comp_norm or comp_norm in l_comp_norm or l_comp_norm in comp_norm) and l_state_val in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                    return True

        return False

    def check_prospect_deduplication(
        self,
        company_name: str = "",
        domain: str = "",
        email: str = "",
        exclude_lead_id: str = "",
    ) -> tuple[bool, str]:
        """Strict multi-key deduplication against universal suppression, 45-day contact logs, and existing leads."""
        email_clean = (email or "").lower().strip()
        domain_clean = normalize_domain(domain or (email_clean.split("@")[-1] if "@" in email_clean else ""))
        comp_norm = normalize_company_name(company_name)

        # 1. Universal Global Suppression Check
        if email_clean and self.is_globally_suppressed(email=email_clean, domain=domain_clean):
            return True, "GLOBAL_SUPPRESSION"

        # 2. Sent Logs & Recent Contact History Check (45-Day window)
        if self.is_recipient_or_domain_contacted(
            email=email_clean,
            domain=domain_clean,
            company_name=company_name,
            within_days=45,
            exclude_lead_id=exclude_lead_id,
        ):
            return True, "RECENTLY_CONTACTED_45D"

        # 3. Check All Existing Leads in Storage
        PUBLIC_MAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"}
        for lead in self.leads.values():
            if exclude_lead_id and getattr(lead, "lead_id", "") == exclude_lead_id:
                continue

            l_email = (getattr(lead, "contact_email", "") or "").lower().strip()
            l_comp = getattr(lead, "company_name", "") or ""
            l_comp_norm = normalize_company_name(l_comp)
            l_website = normalize_domain(getattr(lead, "website", "") or "")

            # A. Exact Email Match
            if email_clean and l_email and email_clean == l_email:
                return True, "DUPLICATE_EMAIL"

            # B. Company Name Match
            if comp_norm and len(comp_norm) >= 4 and l_comp_norm and len(l_comp_norm) >= 4:
                if comp_norm == l_comp_norm or (len(comp_norm) >= 6 and (comp_norm in l_comp_norm or l_comp_norm in comp_norm)):
                    return True, "DUPLICATE_COMPANY"

            # C. Domain Match
            if domain_clean and domain_clean not in PUBLIC_MAIL_DOMAINS:
                if l_website and domain_clean == l_website:
                    return True, "DUPLICATE_DOMAIN"
                if l_email and l_email.endswith(f"@{domain_clean}"):
                    return True, "DUPLICATE_DOMAIN"

        return False, "UNIQUE"

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
    ) -> None:
        if not hasattr(self, "_inbound_emails"):
            self._inbound_emails = []
        self._inbound_emails.append({
            "message_id": message_id,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "subject": subject,
            "body": body,
            "intent": intent,
            "draft_reply": draft_reply,
            "lead_id": lead_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

    def list_inbound_emails(self, lead_id: str | None = None) -> list[dict[str, Any]]:
        if not hasattr(self, "_inbound_emails"):
            return []
        if lead_id:
            return [e for e in self._inbound_emails if e["lead_id"] == lead_id]
        return list(self._inbound_emails)

    def list_inbox_accounts(self) -> list[dict[str, Any]]:
        if not hasattr(self, "_inbox_accounts"):
            self._inbox_accounts = {}
        return list(self._inbox_accounts.values())

    def get_inbox_account(self, inbox_id: str) -> dict[str, Any] | None:
        if not hasattr(self, "_inbox_accounts"):
            self._inbox_accounts = {}
        return self._inbox_accounts.get(inbox_id)

    def upsert_inbox_account(self, account: dict[str, Any]) -> None:
        if not hasattr(self, "_inbox_accounts"):
            self._inbox_accounts = {}
        inbox_id = account.get("inbox_id")
        if inbox_id:
            self._inbox_accounts[inbox_id] = dict(account)

    def delete_inbox_account(self, inbox_id: str) -> None:
        if not hasattr(self, "_inbox_accounts"):
            self._inbox_accounts = {}
        self._inbox_accounts.pop(inbox_id, None)

    def record_chat_message(
        self,
        conversation_id: str,
        sender: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not hasattr(self, "_chat_messages"):
            self._chat_messages = []
        self._chat_messages.append({
            "conversation_id": conversation_id,
            "sender": sender,
            "message": message,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    def list_chat_messages(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        if not hasattr(self, "_chat_messages"):
            return []
        msgs = self._chat_messages
        if conversation_id:
            msgs = [m for m in msgs if m["conversation_id"] == conversation_id]
        return msgs[-limit:]

    def backup_db(self, target_path: str | None = None) -> str:
        return target_path or "in_memory_backup.db"

    def purge_all_data(self) -> dict[str, int]:
        counts = {
            "leads": len(self.leads),
            "sandboxes": len(self.sandboxes),
            "tickets": len(self.tickets),
            "cancellation_requests": len(self.cancellation_requests),
            "webhook_events": len(self.webhook_events),
        }
        self.leads.clear()
        self.sandboxes.clear()
        self.tickets.clear()
        self.cancellation_requests.clear()
        self.webhook_events.clear()
        if hasattr(self, "_chat_messages"):
            self._chat_messages.clear()
        if hasattr(self, "_inbound_emails"):
            self._inbound_emails.clear()
        if hasattr(self, "_emails_sent"):
            self._emails_sent.clear()
        return counts

    def delete_lead(self, lead_id: str) -> bool:
        deleted = False
        if lead_id in self.leads:
            del self.leads[lead_id]
            deleted = True
        to_del = [slug for slug, sb in self.sandboxes.items() if getattr(sb, "lead_id", "") == lead_id or getattr(getattr(sb, "lead", None), "lead_id", "") == lead_id]
        for slug in to_del:
            del self.sandboxes[slug]
        return deleted

    def save_deliverability_audit(self, report: dict[str, Any]) -> None:
        if not hasattr(self, "_deliverability_audits"):
            self._deliverability_audits = []
        self._deliverability_audits.append(dict(report))

    def get_latest_deliverability_audit(self) -> dict[str, Any] | None:
        if not hasattr(self, "_deliverability_audits") or not self._deliverability_audits:
            return None
        return dict(self._deliverability_audits[-1])

    def record_candidate_evaluation(
        self,
        company_name: str,
        channel: str,
        contact_email: str = "",
        status: str = "QUALIFIED",
        reason: str = "",
        jurisdiction: str = "",
        lead_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not hasattr(self, "_candidate_evaluations"):
            self._candidate_evaluations = []
        now_str = datetime.now(timezone.utc).isoformat()
        rec_id = len(self._candidate_evaluations) + 1
        record = {
            "id": rec_id,
            "company_name": company_name,
            "channel": channel,
            "contact_email": contact_email,
            "status": status,
            "reason": reason,
            "jurisdiction": jurisdiction,
            "lead_id": lead_id,
            "evaluated_at": now_str,
            "metadata": dict(metadata or {}),
        }
        self._candidate_evaluations.append(record)
        return record

    def list_candidate_evaluations(
        self, limit: int = 100, channel: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        if not hasattr(self, "_candidate_evaluations"):
            return []
        res = list(self._candidate_evaluations)
        if channel and channel.upper() != "ALL":
            res = [r for r in res if r.get("channel", "").upper() == channel.upper().strip()]
        if status:
            res = [r for r in res if r.get("status", "") == status.strip()]
        return list(reversed(res))[:limit]

    def get_candidate_evaluations_count(self) -> int:
        if not hasattr(self, "_candidate_evaluations"):
            return 0
        return len(self._candidate_evaluations)



