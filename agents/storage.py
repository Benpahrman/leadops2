"""Durable persistence layer for LeadOps domain and portal state."""

import json
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Protocol

from .domain import Lead, State
from .progress import ProgressFeed, ProgressStatus


class StorageBackend(Protocol):
    """Protocol for persisting leads, sandboxes, and webhook idempotency records."""

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

    def get_email_sent_count_today(self, inbox_id: str) -> int: ...

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



class InMemoryStorageBackend:
    """In-memory storage backend for isolated unit testing."""

    def __init__(self) -> None:
        self.leads: dict[str, Lead] = {}
        self.sandboxes: dict[str, Any] = {}
        self.webhook_events: set[str] = set()
        self.tickets: dict[str, Any] = {}
        self.cancellation_requests: dict[str, Any] = {}
        self.email_templates: dict[str, Any] = {}

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

    def get_email_sent_count_today(self, inbox_id: str) -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if not hasattr(self, "_sent_email_logs"):
            return 0
        return sum(1 for e in self._sent_email_logs if e["inbox_id"] == inbox_id and e["sent_date"] == today_str)

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



class SqliteStorageBackend:
    """Durable, zero-cloud SQLite storage backend for leads, sandboxes, and idempotency."""

    def __init__(self, db_path: str = "leadops.db") -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._init_new_tables()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn'):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    tier_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    selected_fields TEXT NOT NULL,
                    qa_score REAL,
                    preview_rows INTEGER NOT NULL,
                    deposit_paid INTEGER NOT NULL,
                    final_paid INTEGER NOT NULL,
                    subscription_active INTEGER NOT NULL,
                    buyout_paid INTEGER NOT NULL,
                    audit_log TEXT NOT NULL,
                    company_name TEXT DEFAULT '',
                    contact_email TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    jurisdiction TEXT DEFAULT '',
                    slug TEXT DEFAULT '',
                    outreach_subject TEXT DEFAULT '',
                    outreach_body TEXT DEFAULT '',
                    repo_url TEXT DEFAULT '',
                    updated_at TEXT NOT NULL
                )
                """
            )
            # Migration check for existing DBs
            for col in ["company_name", "contact_name", "contact_role", "contact_email", "contact_phone", "target_portal_name", "source_url", "jurisdiction", "slug", "outreach_subject", "outreach_body", "repo_url"]:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass
            # Automation workflow columns
            automation_text_cols = ["niche", "last_login_at", "created_at", "referred_by", "claimed_by", "paused_until", "paypal_vault_id", "subscription_id", "decision_maker_linkedin"]
            automation_int_cols = ["delivery_count", "upsell_sent", "referral_sent", "winback_stage", "heartbeat_count", "is_paused"]
            for col in automation_text_cols:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass
            for col in automation_int_cols:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
            # AI Lead Scoring & Qualification columns
            for col in ["automation_opportunity_score", "purchase_probability", "pain_severity"]:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} INTEGER DEFAULT 0")
                except sqlite3.OperationalError:
                    pass
            for col in ["qualification_verdict", "research"]:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} TEXT DEFAULT ''")
                except sqlite3.OperationalError:
                    pass
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sandboxes (
                    slug TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    rows TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    events TEXT NOT NULL,
                    progress TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_idempotency (
                    event_id TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_lead(self, lead: Lead) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO leads (
                    lead_id, tier_key, state, selected_fields, qa_score,
                    preview_rows, deposit_paid, final_paid, subscription_active,
                    buyout_paid, audit_log, company_name, contact_name, contact_role,
                    contact_email, contact_phone, target_portal_name,
                    source_url, jurisdiction, slug, outreach_subject,
                    outreach_body, repo_url, niche, delivery_count,
                    last_login_at, created_at, upsell_sent, referral_sent,
                    winback_stage, heartbeat_count, referred_by, claimed_by, is_paused, paused_until, paypal_vault_id, subscription_id, decision_maker_linkedin,
                    automation_opportunity_score, purchase_probability, pain_severity, qualification_verdict, research, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(lead_id) DO UPDATE SET
                    tier_key=excluded.tier_key,
                    state=excluded.state,
                    selected_fields=excluded.selected_fields,
                    qa_score=excluded.qa_score,
                    preview_rows=excluded.preview_rows,
                    deposit_paid=excluded.deposit_paid,
                    final_paid=excluded.final_paid,
                    subscription_active=excluded.subscription_active,
                    buyout_paid=excluded.buyout_paid,
                    audit_log=excluded.audit_log,
                    company_name=excluded.company_name,
                    contact_name=excluded.contact_name,
                    contact_role=excluded.contact_role,
                    contact_email=excluded.contact_email,
                    contact_phone=excluded.contact_phone,
                    target_portal_name=excluded.target_portal_name,
                    source_url=excluded.source_url,
                    jurisdiction=excluded.jurisdiction,
                    slug=excluded.slug,
                    outreach_subject=excluded.outreach_subject,
                    outreach_body=excluded.outreach_body,
                    repo_url=excluded.repo_url,
                    niche=excluded.niche,
                    delivery_count=excluded.delivery_count,
                    last_login_at=excluded.last_login_at,
                    created_at=excluded.created_at,
                    upsell_sent=excluded.upsell_sent,
                    referral_sent=excluded.referral_sent,
                    winback_stage=excluded.winback_stage,
                    heartbeat_count=excluded.heartbeat_count,
                    referred_by=excluded.referred_by,
                    claimed_by=excluded.claimed_by,
                    is_paused=excluded.is_paused,
                    paused_until=excluded.paused_until,
                    paypal_vault_id=excluded.paypal_vault_id,
                    subscription_id=excluded.subscription_id,
                    decision_maker_linkedin=excluded.decision_maker_linkedin,
                    automation_opportunity_score=excluded.automation_opportunity_score,
                    purchase_probability=excluded.purchase_probability,
                    pain_severity=excluded.pain_severity,
                    qualification_verdict=excluded.qualification_verdict,
                    research=excluded.research,
                    updated_at=excluded.updated_at
                """,
                (
                    lead.lead_id,
                    lead.tier_key,
                    lead.state.value,
                    json.dumps(lead.selected_fields),
                    lead.qa_score,
                    lead.preview_rows,
                    1 if lead.deposit_paid else 0,
                    1 if lead.final_paid else 0,
                    1 if lead.subscription_active else 0,
                    1 if lead.buyout_paid else 0,
                    json.dumps(lead.audit_log),
                    getattr(lead, "company_name", "") or "",
                    getattr(lead, "contact_name", "") or "",
                    getattr(lead, "contact_role", "") or "",
                    getattr(lead, "contact_email", "") or "",
                    getattr(lead, "contact_phone", "") or "",
                    getattr(lead, "target_portal_name", "") or "",
                    getattr(lead, "source_url", "") or "",
                    getattr(lead, "jurisdiction", "") or "",
                    getattr(lead, "slug", "") or "",
                    getattr(lead, "outreach_subject", "") or "",
                    getattr(lead, "outreach_body", "") or "",
                    getattr(lead, "repo_url", "") or "",
                    getattr(lead, "niche", "") or "",
                    getattr(lead, "delivery_count", 0),
                    getattr(lead, "last_login_at", "") or "",
                    getattr(lead, "created_at", "") or "",
                    1 if getattr(lead, "upsell_sent", False) else 0,
                    1 if getattr(lead, "referral_sent", False) else 0,
                    getattr(lead, "winback_stage", 0),
                    getattr(lead, "heartbeat_count", 0),
                    getattr(lead, "referred_by", "") or "",
                    getattr(lead, "claimed_by", "") or "",
                    1 if getattr(lead, "is_paused", False) else 0,
                    getattr(lead, "paused_until", "") or "",
                    getattr(lead, "paypal_vault_id", "") or "",
                    getattr(lead, "subscription_id", "") or "",
                    getattr(lead, "decision_maker_linkedin", "") or "",
                    getattr(lead, "automation_opportunity_score", 75) or 75,
                    getattr(lead, "purchase_probability", 60) or 60,
                    getattr(lead, "pain_severity", 6) or 6,
                    getattr(lead, "qualification_verdict", "QUALIFIED_HOT") or "QUALIFIED_HOT",
                    json.dumps(getattr(lead, "research", {}) or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_lead(self, lead_id: str) -> Lead | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_lead(row)

    def list_leads(self) -> list[Lead]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_lead(row) for row in rows]

    def save_sandbox(self, sandbox: Any) -> None:
        self.save_lead(sandbox.lead)
        progress_data = [
            {
                "role": event.role,
                "status": event.status.value,
                "public_message": event.public_message,
            }
            for event in sandbox.progress.events
        ]
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sandboxes (
                    slug, lead_id, rows, source_url, events, progress, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(slug) DO UPDATE SET
                    lead_id=excluded.lead_id,
                    rows=excluded.rows,
                    source_url=excluded.source_url,
                    events=excluded.events,
                    progress=excluded.progress,
                    updated_at=excluded.updated_at
                """,
                (
                    sandbox.slug,
                    sandbox.lead.lead_id,
                    json.dumps(sandbox.rows),
                    sandbox.source_url,
                    json.dumps(sandbox.events),
                    json.dumps(progress_data),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_sandbox(self, slug: str) -> Any | None:
        from .portal import Sandbox

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sandboxes WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            if not row:
                return None
            lead = self.get_lead(row["lead_id"])
            if not lead:
                return None

            feed = ProgressFeed()
            raw_progress = json.loads(row["progress"])
            for p in raw_progress:
                feed.publish(
                    role=p["role"],
                    status=ProgressStatus(p["status"]),
                    public_message=p["public_message"],
                )

            return Sandbox(
                slug=row["slug"],
                lead=lead,
                rows=json.loads(row["rows"]),
                source_url=row["source_url"],
                events=json.loads(row["events"]),
                progress=feed,
            )

    def list_sandboxes(self) -> list[Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT slug FROM sandboxes ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            sandboxes = []
            for r in rows:
                sb = self.get_sandbox(r["slug"])
                if sb:
                    sandboxes.append(sb)
            return sandboxes

    def record_webhook_event(self, event_id: str) -> bool:
        if not event_id:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO webhook_idempotency (event_id, received_at) VALUES (?, ?)",
                    (event_id, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def has_webhook_event(self, event_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM webhook_idempotency WHERE event_id = ?", (event_id,))
            return cursor.fetchone() is not None

    def _init_new_tables(self) -> None:
        """Initialize new tables for tickets, cancellation requests, and email templates."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    ticket_type TEXT NOT NULL DEFAULT 'general',
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    assignee TEXT,
                    sla_deadline TEXT,
                    sla_breached INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    resolved_at TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_tickets_lead_id ON tickets (lead_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cancellation_requests (
                    request_id TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    user_email TEXT NOT NULL,
                    reason TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    refund_amount REAL,
                    processed_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    processed_at TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_cancellation_requests_lead_id ON cancellation_requests (lead_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS email_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    subject_a TEXT NOT NULL,
                    subject_b TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    body_html TEXT NOT NULL,
                    variant TEXT NOT NULL DEFAULT 'A',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_email_quota_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inbox_id TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    lead_id TEXT DEFAULT '',
                    dispatched_at TEXT NOT NULL,
                    sent_date TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_email_quota_inbox_date ON daily_email_quota_logs (inbox_id, sent_date)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inbound_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    sender_email TEXT NOT NULL,
                    sender_name TEXT DEFAULT '',
                    subject TEXT DEFAULT '',
                    body TEXT DEFAULT '',
                    intent TEXT DEFAULT '',
                    draft_reply TEXT DEFAULT '',
                    lead_id TEXT DEFAULT '',
                    received_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_inbound_emails_lead ON inbound_emails (lead_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS inbox_accounts (
                    inbox_id TEXT PRIMARY KEY,
                    email_address TEXT NOT NULL,
                    warmup_start_date TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_chat_messages_conv ON chat_messages (conversation_id, created_at)
                """
            )
            conn.commit()


    # Ticket operations
    def save_ticket(self, ticket: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO tickets (
                    ticket_id, lead_id, ticket_type, status, priority,
                    title, description, assignee, sla_deadline,
                    sla_breached, created_at, updated_at, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket_id) DO UPDATE SET
                    lead_id=excluded.lead_id,
                    ticket_type=excluded.ticket_type,
                    status=excluded.status,
                    priority=excluded.priority,
                    title=excluded.title,
                    description=excluded.description,
                    assignee=excluded.assignee,
                    sla_deadline=excluded.sla_deadline,
                    sla_breached=excluded.sla_breached,
                    updated_at=excluded.updated_at,
                    resolved_at=excluded.resolved_at
                """,
                (
                    ticket.ticket_id,
                    ticket.lead_id,
                    ticket.ticket_type.value if hasattr(ticket.ticket_type, 'value') else ticket.ticket_type,
                    ticket.status.value if hasattr(ticket.status, 'value') else ticket.status,
                    ticket.priority.value if hasattr(ticket.priority, 'value') else ticket.priority,
                    ticket.title,
                    ticket.description,
                    ticket.assignee,
                    ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
                    1 if ticket.sla_breached else 0,
                    ticket.created_at.isoformat() if hasattr(ticket.created_at, 'isoformat') else ticket.created_at,
                    datetime.now(timezone.utc).isoformat(),
                    ticket.resolved_at.isoformat() if ticket.resolved_at and hasattr(ticket.resolved_at, 'isoformat') else ticket.resolved_at,
                ),
            )
            conn.commit()

    def get_ticket(self, ticket_id: str) -> Any | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_ticket(row)

    def list_tickets(self, lead_id: str | None = None) -> list[Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if lead_id:
                cursor.execute("SELECT * FROM tickets WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,))
            else:
                cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_ticket(row) for row in rows]

    # Cancellation operations
    def save_cancellation_request(self, request: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO cancellation_requests (
                    request_id, lead_id, user_email, reason, status,
                    refund_amount, processed_by, created_at, updated_at, processed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(request_id) DO UPDATE SET
                    lead_id=excluded.lead_id,
                    user_email=excluded.user_email,
                    reason=excluded.reason,
                    status=excluded.status,
                    refund_amount=excluded.refund_amount,
                    processed_by=excluded.processed_by,
                    updated_at=excluded.updated_at,
                    processed_at=excluded.processed_at
                """,
                (
                    request.request_id,
                    request.lead_id,
                    request.user_email,
                    request.reason,
                    request.status.value if hasattr(request.status, 'value') else request.status,
                    request.refund_amount,
                    request.processed_by,
                    request.created_at.isoformat() if hasattr(request.created_at, 'isoformat') else request.created_at,
                    datetime.now(timezone.utc).isoformat(),
                    request.processed_at.isoformat() if request.processed_at and hasattr(request.processed_at, 'isoformat') else request.processed_at,
                ),
            )
            conn.commit()

    def get_cancellation_request(self, request_id: str) -> Any | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cancellation_requests WHERE request_id = ?", (request_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_cancellation_request(row)

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if lead_id:
                cursor.execute("SELECT * FROM cancellation_requests WHERE lead_id = ? ORDER BY created_at DESC", (lead_id,))
            else:
                cursor.execute("SELECT * FROM cancellation_requests ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_cancellation_request(row) for row in rows]

    # Email template operations
    def save_email_template(self, template: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO email_templates (
                    template_id, name, subject_a, subject_b,
                    body_text, body_html, variant, active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    name=excluded.name,
                    subject_a=excluded.subject_a,
                    subject_b=excluded.subject_b,
                    body_text=excluded.body_text,
                    body_html=excluded.body_html,
                    variant=excluded.variant,
                    active=excluded.active,
                    updated_at=excluded.updated_at
                """,
                (
                    template.template_id,
                    template.name,
                    template.subject_a,
                    template.subject_b,
                    template.body_text,
                    template.body_html,
                    template.variant.value if hasattr(template.variant, 'value') else template.variant,
                    1 if template.active else 0,
                    template.created_at.isoformat() if hasattr(template.created_at, 'isoformat') else template.created_at,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def get_email_template(self, template_id: str) -> Any | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_templates WHERE template_id = ?", (template_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_email_template(row)

    def list_email_templates(self) -> list[Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_templates ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_email_template(row) for row in rows]

    def record_email_sent(self, inbox_id: str, recipient: str, lead_id: str, dispatched_at: str) -> None:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO daily_email_quota_logs (inbox_id, recipient, lead_id, dispatched_at, sent_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (inbox_id, recipient, lead_id, dispatched_at, today_str),
            )
            conn.commit()

    def get_email_sent_count_today(self, inbox_id: str) -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM daily_email_quota_logs
                WHERE inbox_id = ? AND sent_date = ?
                """,
                (inbox_id, today_str),
            )
            row = cursor.fetchone()
            return row[0] if row else 0

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
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inbound_emails (
                    message_id, sender_email, sender_name, subject, body,
                    intent, draft_reply, lead_id, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    sender_email,
                    sender_name,
                    subject,
                    body,
                    intent,
                    draft_reply,
                    lead_id,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def list_inbound_emails(self, lead_id: str | None = None) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if lead_id:
                cursor.execute("SELECT * FROM inbound_emails WHERE lead_id = ? ORDER BY received_at DESC", (lead_id,))
            else:
                cursor.execute("SELECT * FROM inbound_emails ORDER BY received_at DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def record_chat_message(
        self,
        conversation_id: str,
        sender: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (
                    conversation_id, sender, message, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    sender,
                    message,
                    json.dumps(metadata or {}),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()

    def list_chat_messages(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if conversation_id:
                cursor.execute(
                    "SELECT * FROM chat_messages WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
                    (conversation_id, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM chat_messages ORDER BY created_at ASC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [dict(r) for r in rows]


    @staticmethod
    def _row_to_ticket(row: sqlite3.Row):
        from .models import Ticket, TicketType, TicketStatus, TicketPriority
        from datetime import datetime
        return Ticket(
            ticket_id=row["ticket_id"],
            lead_id=row["lead_id"],
            ticket_type=TicketType(row["ticket_type"]),
            status=TicketStatus(row["status"]),
            priority=TicketPriority(row["priority"]),
            title=row["title"],
            description=row["description"],
            assignee=row["assignee"],
            sla_deadline=datetime.fromisoformat(row["sla_deadline"]) if row["sla_deadline"] else None,
            sla_breached=bool(row["sla_breached"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
        )

    @staticmethod
    def _row_to_cancellation_request(row: sqlite3.Row):
        from .models import CancellationRequest, CancellationStatus
        from datetime import datetime
        return CancellationRequest(
            request_id=row["request_id"],
            lead_id=row["lead_id"],
            user_email=row["user_email"],
            reason=row["reason"],
            status=CancellationStatus(row["status"]),
            refund_amount=row["refund_amount"],
            processed_by=row["processed_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            processed_at=datetime.fromisoformat(row["processed_at"]) if row["processed_at"] else None,
        )

    @staticmethod
    def _row_to_email_template(row: sqlite3.Row):
        from .models import EmailTemplate, ABTestVariant
        from datetime import datetime
        return EmailTemplate(
            template_id=row["template_id"],
            name=row["name"],
            subject_a=row["subject_a"],
            subject_b=row["subject_b"],
            body_text=row["body_text"],
            body_html=row["body_html"],
            variant=ABTestVariant(row["variant"]),
            active=bool(row["active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_lead(row: sqlite3.Row) -> Lead:
        def get_col(col_name: str, default: Any = ""):
            try:
                val = row[col_name]
                return val if val is not None else default
            except (IndexError, KeyError):
                return default

        return Lead(
            lead_id=row["lead_id"],
            tier_key=row["tier_key"],
            state=State(row["state"]),
            selected_fields=json.loads(row["selected_fields"]),
            qa_score=row["qa_score"],
            preview_rows=row["preview_rows"],
            deposit_paid=bool(row["deposit_paid"]),
            final_paid=bool(row["final_paid"]),
            subscription_active=bool(row["subscription_active"]),
            buyout_paid=bool(row["buyout_paid"]),
            audit_log=json.loads(row["audit_log"]),
            company_name=get_col("company_name", ""),
            contact_name=get_col("contact_name", ""),
            contact_role=get_col("contact_role", ""),
            contact_email=get_col("contact_email", ""),
            contact_phone=get_col("contact_phone", ""),
            target_portal_name=get_col("target_portal_name", ""),
            source_url=get_col("source_url", ""),
            jurisdiction=get_col("jurisdiction", ""),
            slug=get_col("slug", ""),
            outreach_subject=get_col("outreach_subject", ""),
            outreach_body=get_col("outreach_body", ""),
            repo_url=get_col("repo_url", ""),
            niche=get_col("niche", ""),
            delivery_count=int(get_col("delivery_count", 0)),
            last_login_at=get_col("last_login_at", ""),
            created_at=get_col("created_at", ""),
            upsell_sent=bool(get_col("upsell_sent", 0)),
            referral_sent=bool(get_col("referral_sent", 0)),
            winback_stage=int(get_col("winback_stage", 0)),
            heartbeat_count=int(get_col("heartbeat_count", 0)),
            referred_by=get_col("referred_by", ""),
            claimed_by=get_col("claimed_by", ""),
            is_paused=bool(get_col("is_paused", 0)),
            paused_until=get_col("paused_until", ""),
            paypal_vault_id=get_col("paypal_vault_id", ""),
            subscription_id=get_col("subscription_id", ""),
            decision_maker_linkedin=get_col("decision_maker_linkedin", ""),
            automation_opportunity_score=int(get_col("automation_opportunity_score", 75) or 75),
            purchase_probability=int(get_col("purchase_probability", 60) or 60),
            pain_severity=int(get_col("pain_severity", 6) or 6),
            qualification_verdict=str(get_col("qualification_verdict", "QUALIFIED_HOT") or "QUALIFIED_HOT"),
            research=(
                json.loads(get_col("research", "{}"))
                if isinstance(get_col("research", "{}"), str) and get_col("research", "{}").strip().startswith("{")
                else (get_col("research", {}) if isinstance(get_col("research", {}), dict) else {})
            ),
        )

    def backup_db(self, target_path: str | None = None) -> str:
        """Create a consistent online SQLite backup snapshot using the native backup API."""
        import os
        from datetime import datetime, timezone
        if not target_path:
            backup_dir = os.path.join(os.path.dirname(self.db_path) or ".", "backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            target_path = os.path.join(backup_dir, f"leadops_backup_{timestamp}.db")

        src_conn = self._get_connection()
        dest_conn = sqlite3.connect(target_path)
        try:
            with dest_conn:
                src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
        return target_path

    def purge_all_data(self) -> dict[str, int]:
        """Purge all leads, sandboxes, tickets, and operational records for a clean fresh slate."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            counts = {}
            for table in [
                "sandboxes", "leads", "tickets", "cancellation_requests",
                "chat_messages", "emails_sent", "inbound_emails", "webhook_events"
            ]:
                try:
                    cursor.execute(f"SELECT count(*) FROM {table}")
                    counts[table] = cursor.fetchone()[0]
                    cursor.execute(f"DELETE FROM {table}")
                except sqlite3.OperationalError:
                    pass
            conn.commit()
            return counts

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a single lead and any corresponding sandboxes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sandboxes WHERE lead_id = ? OR slug LIKE ?", (lead_id, f"%{lead_id}%"))
            cursor.execute("DELETE FROM leads WHERE lead_id = ?", (lead_id,))
            conn.commit()
            return cursor.rowcount > 0


class PostgresStorageBackend:
    """Production-grade PostgreSQL storage backend for Azure Database for PostgreSQL (Flexible Server)."""

    def __init__(self, database_url: str) -> None:
        from sqlalchemy import create_engine
        normalized_url = database_url
        if normalized_url.startswith("postgres://"):
            normalized_url = normalized_url.replace("postgres://", "postgresql://", 1)
        self.database_url = normalized_url
        self.engine = create_engine(
            self.database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        self._init_db()

    def _init_db(self) -> None:
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id VARCHAR(255) PRIMARY KEY,
                    tier_key VARCHAR(50) NOT NULL,
                    state VARCHAR(50) NOT NULL,
                    selected_fields TEXT NOT NULL,
                    qa_score DOUBLE PRECISION,
                    preview_rows INTEGER NOT NULL DEFAULT 0,
                    deposit_paid INTEGER NOT NULL DEFAULT 0,
                    final_paid INTEGER NOT NULL DEFAULT 0,
                    subscription_active INTEGER NOT NULL DEFAULT 0,
                    buyout_paid INTEGER NOT NULL DEFAULT 0,
                    audit_log TEXT NOT NULL,
                    company_name VARCHAR(255) DEFAULT '',
                    contact_name VARCHAR(255) DEFAULT '',
                    contact_role VARCHAR(255) DEFAULT '',
                    contact_email VARCHAR(255) DEFAULT '',
                    contact_phone VARCHAR(100) DEFAULT '',
                    target_portal_name VARCHAR(255) DEFAULT '',
                    source_url TEXT DEFAULT '',
                    jurisdiction VARCHAR(255) DEFAULT '',
                    slug VARCHAR(255) DEFAULT '',
                    outreach_subject TEXT DEFAULT '',
                    outreach_body TEXT DEFAULT '',
                    repo_url VARCHAR(500) DEFAULT '',
                    niche VARCHAR(255) DEFAULT '',
                    delivery_count INTEGER DEFAULT 0,
                    last_login_at VARCHAR(100) DEFAULT '',
                    created_at VARCHAR(100) DEFAULT '',
                    upsell_sent INTEGER DEFAULT 0,
                    referral_sent INTEGER DEFAULT 0,
                    winback_stage INTEGER DEFAULT 0,
                    heartbeat_count INTEGER DEFAULT 0,
                    referred_by VARCHAR(255) DEFAULT '',
                    claimed_by VARCHAR(255) DEFAULT '',
                    is_paused INTEGER DEFAULT 0,
                    paused_until VARCHAR(100) DEFAULT '',
                    updated_at VARCHAR(100) NOT NULL
                )
            """))
            for column, definition in {
                "contact_name": "VARCHAR(255) DEFAULT ''",
                "contact_role": "VARCHAR(255) DEFAULT ''",
                "contact_phone": "VARCHAR(100) DEFAULT ''",
                "target_portal_name": "VARCHAR(255) DEFAULT ''",
                "decision_maker_linkedin": "VARCHAR(500) DEFAULT ''",
                "automation_opportunity_score": "INTEGER DEFAULT 75",
                "purchase_probability": "INTEGER DEFAULT 60",
                "pain_severity": "INTEGER DEFAULT 6",
                "qualification_verdict": "VARCHAR(50) DEFAULT 'QUALIFIED_HOT'",
                "research": "TEXT DEFAULT '{}'",
            }.items():
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN IF NOT EXISTS {column} {definition}"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS sandboxes (
                    slug VARCHAR(255) PRIMARY KEY,
                    lead_id VARCHAR(255) NOT NULL,
                    rows TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    events TEXT NOT NULL,
                    progress TEXT NOT NULL,
                    updated_at VARCHAR(100) NOT NULL,
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS webhook_idempotency (
                    event_id VARCHAR(255) PRIMARY KEY,
                    received_at VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id VARCHAR(255) PRIMARY KEY,
                    lead_id VARCHAR(255) NOT NULL,
                    ticket_type VARCHAR(50) NOT NULL DEFAULT 'general',
                    status VARCHAR(50) NOT NULL DEFAULT 'open',
                    priority VARCHAR(50) NOT NULL DEFAULT 'medium',
                    title VARCHAR(255) NOT NULL,
                    description TEXT DEFAULT '',
                    assignee VARCHAR(255),
                    sla_deadline VARCHAR(100),
                    sla_breached INTEGER NOT NULL DEFAULT 0,
                    created_at VARCHAR(100) NOT NULL,
                    updated_at VARCHAR(100) NOT NULL,
                    resolved_at VARCHAR(100),
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cancellation_requests (
                    request_id VARCHAR(255) PRIMARY KEY,
                    lead_id VARCHAR(255) NOT NULL,
                    user_email VARCHAR(255) NOT NULL,
                    reason TEXT NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    refund_amount DOUBLE PRECISION,
                    processed_by VARCHAR(255),
                    created_at VARCHAR(100) NOT NULL,
                    updated_at VARCHAR(100) NOT NULL,
                    processed_at VARCHAR(100),
                    FOREIGN KEY (lead_id) REFERENCES leads (lead_id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS email_templates (
                    template_id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    subject_a TEXT NOT NULL,
                    subject_b TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    body_html TEXT NOT NULL,
                    variant VARCHAR(10) NOT NULL DEFAULT 'A',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at VARCHAR(100) NOT NULL,
                    updated_at VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id SERIAL PRIMARY KEY,
                    conversation_id VARCHAR(255) NOT NULL,
                    sender VARCHAR(64) NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    created_at VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_chat_messages_conv ON chat_messages (conversation_id, created_at)
            """))

    def save_lead(self, lead: Lead) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO leads (
                lead_id, tier_key, state, selected_fields, qa_score,
                preview_rows, deposit_paid, final_paid, subscription_active,
                buyout_paid, audit_log, company_name, contact_name, contact_role,
                contact_email, contact_phone, target_portal_name,
                source_url, jurisdiction, slug, outreach_subject,
                outreach_body, repo_url, niche, delivery_count,
                last_login_at, created_at, upsell_sent, referral_sent,
                winback_stage, heartbeat_count, referred_by, claimed_by, is_paused, paused_until, decision_maker_linkedin,
                automation_opportunity_score, purchase_probability, pain_severity, qualification_verdict, research, updated_at
            ) VALUES (
                :lead_id, :tier_key, :state, :selected_fields, :qa_score,
                :preview_rows, :deposit_paid, :final_paid, :subscription_active,
                :buyout_paid, :audit_log, :company_name, :contact_name, :contact_role,
                :contact_email, :contact_phone, :target_portal_name,
                :source_url, :jurisdiction, :slug, :outreach_subject,
                :outreach_body, :repo_url, :niche, :delivery_count,
                :last_login_at, :created_at, :upsell_sent, :referral_sent,
                :winback_stage, :heartbeat_count, :referred_by, :claimed_by, :is_paused, :paused_until, :decision_maker_linkedin,
                :automation_opportunity_score, :purchase_probability, :pain_severity, :qualification_verdict, :research, :updated_at
            )
            ON CONFLICT (lead_id) DO UPDATE SET
                tier_key = EXCLUDED.tier_key,
                state = EXCLUDED.state,
                selected_fields = EXCLUDED.selected_fields,
                qa_score = EXCLUDED.qa_score,
                preview_rows = EXCLUDED.preview_rows,
                deposit_paid = EXCLUDED.deposit_paid,
                final_paid = EXCLUDED.final_paid,
                subscription_active = EXCLUDED.subscription_active,
                buyout_paid = EXCLUDED.buyout_paid,
                audit_log = EXCLUDED.audit_log,
                company_name = EXCLUDED.company_name,
                contact_name = EXCLUDED.contact_name,
                contact_role = EXCLUDED.contact_role,
                contact_email = EXCLUDED.contact_email,
                contact_phone = EXCLUDED.contact_phone,
                target_portal_name = EXCLUDED.target_portal_name,
                source_url = EXCLUDED.source_url,
                jurisdiction = EXCLUDED.jurisdiction,
                slug = EXCLUDED.slug,
                outreach_subject = EXCLUDED.outreach_subject,
                outreach_body = EXCLUDED.outreach_body,
                repo_url = EXCLUDED.repo_url,
                niche = EXCLUDED.niche,
                delivery_count = EXCLUDED.delivery_count,
                last_login_at = EXCLUDED.last_login_at,
                created_at = EXCLUDED.created_at,
                upsell_sent = EXCLUDED.upsell_sent,
                referral_sent = EXCLUDED.referral_sent,
                winback_stage = EXCLUDED.winback_stage,
                heartbeat_count = EXCLUDED.heartbeat_count,
                referred_by = EXCLUDED.referred_by,
                claimed_by = EXCLUDED.claimed_by,
                is_paused = EXCLUDED.is_paused,
                paused_until = EXCLUDED.paused_until,
                decision_maker_linkedin = EXCLUDED.decision_maker_linkedin,
                automation_opportunity_score = EXCLUDED.automation_opportunity_score,
                purchase_probability = EXCLUDED.purchase_probability,
                pain_severity = EXCLUDED.pain_severity,
                qualification_verdict = EXCLUDED.qualification_verdict,
                research = EXCLUDED.research,
                updated_at = EXCLUDED.updated_at
        """)
        params = {
            "lead_id": lead.lead_id,
            "tier_key": lead.tier_key,
            "state": lead.state.value,
            "selected_fields": json.dumps(lead.selected_fields),
            "qa_score": lead.qa_score,
            "preview_rows": lead.preview_rows,
            "deposit_paid": 1 if lead.deposit_paid else 0,
            "final_paid": 1 if lead.final_paid else 0,
            "subscription_active": 1 if lead.subscription_active else 0,
            "buyout_paid": 1 if lead.buyout_paid else 0,
            "audit_log": json.dumps(lead.audit_log),
            "company_name": getattr(lead, "company_name", "") or "",
            "contact_name": getattr(lead, "contact_name", "") or "",
            "contact_role": getattr(lead, "contact_role", "") or "",
            "contact_email": getattr(lead, "contact_email", "") or "",
            "contact_phone": getattr(lead, "contact_phone", "") or "",
            "target_portal_name": getattr(lead, "target_portal_name", "") or "",
            "source_url": getattr(lead, "source_url", "") or "",
            "jurisdiction": getattr(lead, "jurisdiction", "") or "",
            "slug": getattr(lead, "slug", "") or "",
            "outreach_subject": getattr(lead, "outreach_subject", "") or "",
            "outreach_body": getattr(lead, "outreach_body", "") or "",
            "repo_url": getattr(lead, "repo_url", "") or "",
            "niche": getattr(lead, "niche", "") or "",
            "delivery_count": getattr(lead, "delivery_count", 0),
            "last_login_at": getattr(lead, "last_login_at", "") or "",
            "created_at": getattr(lead, "created_at", "") or "",
            "upsell_sent": 1 if getattr(lead, "upsell_sent", False) else 0,
            "referral_sent": 1 if getattr(lead, "referral_sent", False) else 0,
            "winback_stage": getattr(lead, "winback_stage", 0),
            "heartbeat_count": getattr(lead, "heartbeat_count", 0),
            "referred_by": getattr(lead, "referred_by", "") or "",
            "claimed_by": getattr(lead, "claimed_by", "") or "",
            "is_paused": 1 if getattr(lead, "is_paused", False) else 0,
            "paused_until": getattr(lead, "paused_until", "") or "",
            "decision_maker_linkedin": getattr(lead, "decision_maker_linkedin", "") or "",
            "automation_opportunity_score": getattr(lead, "automation_opportunity_score", 75) or 75,
            "purchase_probability": getattr(lead, "purchase_probability", 60) or 60,
            "pain_severity": getattr(lead, "pain_severity", 6) or 6,
            "qualification_verdict": getattr(lead, "qualification_verdict", "QUALIFIED_HOT") or "QUALIFIED_HOT",
            "research": json.dumps(getattr(lead, "research", {}) or {}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_lead(self, lead_id: str) -> Lead | None:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM leads WHERE lead_id = :lead_id"), {"lead_id": lead_id})
            row = result.mappings().fetchone()
            if not row:
                return None
            return SqliteStorageBackend._row_to_lead(row)

    def list_leads(self) -> list[Lead]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM leads ORDER BY updated_at DESC"))
            rows = result.mappings().fetchall()
            return [SqliteStorageBackend._row_to_lead(r) for r in rows]

    def save_sandbox(self, sandbox: Any) -> None:
        from sqlalchemy import text
        self.save_lead(sandbox.lead)
        progress_data = [
            {
                "role": event.role,
                "status": event.status.value,
                "public_message": event.public_message,
            }
            for event in sandbox.progress.events
        ]
        stmt = text("""
            INSERT INTO sandboxes (
                slug, lead_id, rows, source_url, events, progress, updated_at
            ) VALUES (
                :slug, :lead_id, :rows, :source_url, :events, :progress, :updated_at
            )
            ON CONFLICT (slug) DO UPDATE SET
                lead_id = EXCLUDED.lead_id,
                rows = EXCLUDED.rows,
                source_url = EXCLUDED.source_url,
                events = EXCLUDED.events,
                progress = EXCLUDED.progress,
                updated_at = EXCLUDED.updated_at
        """)
        params = {
            "slug": sandbox.slug,
            "lead_id": sandbox.lead.lead_id,
            "rows": json.dumps(sandbox.rows),
            "source_url": sandbox.source_url,
            "events": json.dumps(sandbox.events),
            "progress": json.dumps(progress_data),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_sandbox(self, slug: str) -> Any | None:
        from sqlalchemy import text
        from .portal import Sandbox

        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM sandboxes WHERE slug = :slug"), {"slug": slug})
            row = result.mappings().fetchone()
            if not row:
                return None
            lead = self.get_lead(row["lead_id"])
            if not lead:
                return None

            feed = ProgressFeed()
            raw_progress = json.loads(row["progress"])
            for p in raw_progress:
                feed.publish(
                    role=p["role"],
                    status=ProgressStatus(p["status"]),
                    public_message=p["public_message"],
                )

            return Sandbox(
                slug=row["slug"],
                lead=lead,
                rows=json.loads(row["rows"]),
                source_url=row["source_url"],
                events=json.loads(row["events"]),
                progress=feed,
            )

    def list_sandboxes(self) -> list[Any]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT slug FROM sandboxes ORDER BY updated_at DESC"))
            rows = result.mappings().fetchall()
            sandboxes = []
            for r in rows:
                sb = self.get_sandbox(r["slug"])
                if sb:
                    sandboxes.append(sb)
            return sandboxes

    def record_webhook_event(self, event_id: str) -> bool:
        from sqlalchemy import text
        if not event_id:
            return False
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO webhook_idempotency (event_id, received_at) VALUES (:event_id, :received_at)"),
                    {"event_id": event_id, "received_at": datetime.now(timezone.utc).isoformat()},
                )
                return True
        except Exception:
            return False

    def has_webhook_event(self, event_id: str) -> bool:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM webhook_idempotency WHERE event_id = :event_id"),
                {"event_id": event_id},
            )
            return result.fetchone() is not None

    def save_ticket(self, ticket: Any) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO tickets (
                ticket_id, lead_id, ticket_type, status, priority,
                title, description, assignee, sla_deadline,
                sla_breached, created_at, updated_at, resolved_at
            ) VALUES (
                :ticket_id, :lead_id, :ticket_type, :status, :priority,
                :title, :description, :assignee, :sla_deadline,
                :sla_breached, :created_at, :updated_at, :resolved_at
            )
            ON CONFLICT (ticket_id) DO UPDATE SET
                lead_id = EXCLUDED.lead_id,
                ticket_type = EXCLUDED.ticket_type,
                status = EXCLUDED.status,
                priority = EXCLUDED.priority,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                assignee = EXCLUDED.assignee,
                sla_deadline = EXCLUDED.sla_deadline,
                sla_breached = EXCLUDED.sla_breached,
                updated_at = EXCLUDED.updated_at,
                resolved_at = EXCLUDED.resolved_at
        """)
        params = {
            "ticket_id": ticket.ticket_id,
            "lead_id": ticket.lead_id,
            "ticket_type": ticket.ticket_type.value if hasattr(ticket.ticket_type, "value") else str(ticket.ticket_type),
            "status": ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
            "priority": ticket.priority.value if hasattr(ticket.priority, "value") else str(ticket.priority),
            "title": ticket.title,
            "description": ticket.description,
            "assignee": ticket.assignee,
            "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
            "sla_breached": 1 if ticket.sla_breached else 0,
            "created_at": ticket.created_at.isoformat() if hasattr(ticket.created_at, "isoformat") else str(ticket.created_at),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at and hasattr(ticket.resolved_at, "isoformat") else None,
        }
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_ticket(self, ticket_id: str) -> Any | None:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM tickets WHERE ticket_id = :ticket_id"), {"ticket_id": ticket_id})
            row = result.mappings().fetchone()
            if not row:
                return None
            return SqliteStorageBackend._row_to_ticket(row)

    def list_tickets(self, lead_id: str | None = None) -> list[Any]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            if lead_id:
                result = conn.execute(
                    text("SELECT * FROM tickets WHERE lead_id = :lead_id ORDER BY created_at DESC"),
                    {"lead_id": lead_id},
                )
            else:
                result = conn.execute(text("SELECT * FROM tickets ORDER BY created_at DESC"))
            rows = result.mappings().fetchall()
            return [SqliteStorageBackend._row_to_ticket(r) for r in rows]

    def save_cancellation_request(self, request: Any) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO cancellation_requests (
                request_id, lead_id, user_email, reason, status,
                refund_amount, processed_by, created_at, updated_at, processed_at
            ) VALUES (
                :request_id, :lead_id, :user_email, :reason, :status,
                :refund_amount, :processed_by, :created_at, :updated_at, :processed_at
            )
            ON CONFLICT (request_id) DO UPDATE SET
                lead_id = EXCLUDED.lead_id,
                user_email = EXCLUDED.user_email,
                reason = EXCLUDED.reason,
                status = EXCLUDED.status,
                refund_amount = EXCLUDED.refund_amount,
                processed_by = EXCLUDED.processed_by,
                updated_at = EXCLUDED.updated_at,
                processed_at = EXCLUDED.processed_at
        """)
        params = {
            "request_id": request.request_id,
            "lead_id": request.lead_id,
            "user_email": request.user_email,
            "reason": request.reason,
            "status": request.status.value if hasattr(request.status, "value") else str(request.status),
            "refund_amount": request.refund_amount,
            "processed_by": request.processed_by,
            "created_at": request.created_at.isoformat() if hasattr(request.created_at, "isoformat") else str(request.created_at),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": request.processed_at.isoformat() if request.processed_at and hasattr(request.processed_at, "isoformat") else None,
        }
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_cancellation_request(self, request_id: str) -> Any | None:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM cancellation_requests WHERE request_id = :request_id"),
                {"request_id": request_id},
            )
            row = result.mappings().fetchone()
            if not row:
                return None
            return SqliteStorageBackend._row_to_cancellation_request(row)

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            if lead_id:
                result = conn.execute(
                    text("SELECT * FROM cancellation_requests WHERE lead_id = :lead_id ORDER BY created_at DESC"),
                    {"lead_id": lead_id},
                )
            else:
                result = conn.execute(text("SELECT * FROM cancellation_requests ORDER BY created_at DESC"))
            rows = result.mappings().fetchall()
            return [SqliteStorageBackend._row_to_cancellation_request(r) for r in rows]

    def save_email_template(self, template: Any) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO email_templates (
                template_id, name, subject_a, subject_b, body_text,
                body_html, variant, active, created_at, updated_at
            ) VALUES (
                :template_id, :name, :subject_a, :subject_b, :body_text,
                :body_html, :variant, :active, :created_at, :updated_at
            )
            ON CONFLICT (template_id) DO UPDATE SET
                name = EXCLUDED.name,
                subject_a = EXCLUDED.subject_a,
                subject_b = EXCLUDED.subject_b,
                body_text = EXCLUDED.body_text,
                body_html = EXCLUDED.body_html,
                variant = EXCLUDED.variant,
                active = EXCLUDED.active,
                updated_at = EXCLUDED.updated_at
        """)
        params = {
            "template_id": template.template_id,
            "name": template.name,
            "subject_a": template.subject_a,
            "subject_b": template.subject_b,
            "body_text": template.body_text,
            "body_html": template.body_html,
            "variant": template.variant.value if hasattr(template.variant, "value") else str(template.variant),
            "active": 1 if template.active else 0,
            "created_at": template.created_at.isoformat() if hasattr(template.created_at, "isoformat") else str(template.created_at),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.engine.begin() as conn:
            conn.execute(stmt, params)

    def get_email_template(self, template_id: str) -> Any | None:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT * FROM email_templates WHERE template_id = :template_id"),
                {"template_id": template_id},
            )
            row = result.mappings().fetchone()
            if not row:
                return None
            return SqliteStorageBackend._row_to_email_template(row)

    def list_email_templates(self) -> list[Any]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM email_templates ORDER BY created_at DESC"))
            rows = result.mappings().fetchall()
            return [SqliteStorageBackend._row_to_email_template(r) for r in rows]

    def record_email_sent(self, inbox_id: str, recipient: str, lead_id: str, dispatched_at: str) -> None:
        from sqlalchemy import text
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stmt = text("""
            INSERT INTO daily_email_quota_logs (inbox_id, recipient, lead_id, dispatched_at, sent_date)
            VALUES (:inbox_id, :recipient, :lead_id, :dispatched_at, :sent_date)
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {
                "inbox_id": inbox_id,
                "recipient": recipient,
                "lead_id": lead_id,
                "dispatched_at": dispatched_at,
                "sent_date": today_str,
            })

    def get_email_sent_count_today(self, inbox_id: str) -> int:
        from sqlalchemy import text
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM daily_email_quota_logs WHERE inbox_id = :inbox_id AND sent_date = :sent_date"),
                {"inbox_id": inbox_id, "sent_date": today_str},
            )
            return result.scalar() or 0

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
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO inbound_emails (
                message_id, sender_email, sender_name, subject, body,
                intent, draft_reply, lead_id, received_at
            ) VALUES (
                :message_id, :sender_email, :sender_name, :subject, :body,
                :intent, :draft_reply, :lead_id, :received_at
            )
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {
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
        from sqlalchemy import text
        with self.engine.connect() as conn:
            if lead_id:
                result = conn.execute(
                    text("SELECT * FROM inbound_emails WHERE lead_id = :lead_id ORDER BY received_at DESC"),
                    {"lead_id": lead_id},
                )
            else:
                result = conn.execute(text("SELECT * FROM inbound_emails ORDER BY received_at DESC"))
            return [dict(r) for r in result.mappings().fetchall()]

    def record_chat_message(
        self,
        conversation_id: str,
        sender: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO chat_messages (
                conversation_id, sender, message, metadata_json, created_at
            ) VALUES (
                :conversation_id, :sender, :message, :metadata_json, :created_at
            )
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {
                "conversation_id": conversation_id,
                "sender": sender,
                "message": message,
                "metadata_json": json.dumps(metadata or {}),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    def list_chat_messages(
        self, conversation_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            if conversation_id:
                result = conn.execute(
                    text("SELECT * FROM chat_messages WHERE conversation_id = :conversation_id ORDER BY created_at ASC LIMIT :limit"),
                    {"conversation_id": conversation_id, "limit": limit},
                )
            else:
                result = conn.execute(
                    text("SELECT * FROM chat_messages ORDER BY created_at ASC LIMIT :limit"),
                    {"limit": limit},
                )
            return [dict(r) for r in result.mappings().fetchall()]


    def backup_db(self, target_path: str | None = None) -> str:
        return target_path or f"azure_pg_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.sql"

    def purge_all_data(self) -> dict[str, int]:
        """Purge all leads, sandboxes, tickets, and operational records in PostgreSQL."""
        from sqlalchemy import text
        counts = {}
        with self.engine.begin() as conn:
            for table in [
                "sandboxes", "leads", "tickets", "cancellation_requests",
                "chat_messages", "emails_sent", "inbound_emails", "webhook_events"
            ]:
                try:
                    cnt = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()
                    counts[table] = int(cnt or 0)
                    conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                except Exception:
                    pass
        return counts

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a single lead and any associated sandboxes in PostgreSQL."""
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM sandboxes WHERE lead_id = :lid OR slug LIKE :pat"), {"lid": lead_id, "pat": f"%{lead_id}%"})
            res = conn.execute(text("DELETE FROM leads WHERE lead_id = :lid"), {"lid": lead_id})
            return res.rowcount > 0


def create_storage_backend(database_url: str | None = None) -> StorageBackend:
    """Factory creating PostgresStorageBackend when DATABASE_URL is set, else SqliteStorageBackend."""
    import os
    db_url = database_url or os.environ.get("DATABASE_URL")
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        return PostgresStorageBackend(database_url=db_url)
    return SqliteStorageBackend()

