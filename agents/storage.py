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


class InMemoryStorageBackend:
    """In-memory storage backend for isolated unit testing."""

    def __init__(self) -> None:
        self.leads: dict[str, Lead] = {}
        self.sandboxes: dict[str, Any] = {}
        self.webhook_events: set[str] = set()

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

    # Ticket operations
    def save_ticket(self, ticket: Any) -> None:
        if not hasattr(self, 'tickets'):
            self.tickets = {}
        self.tickets[ticket.ticket_id] = ticket

    def get_ticket(self, ticket_id: str) -> Any | None:
        if not hasattr(self, 'tickets'):
            return None
        return self.tickets.get(ticket_id)

    def list_tickets(self, lead_id: str | None = None) -> list[Any]:
        if not hasattr(self, 'tickets'):
            return []
        if lead_id:
            return [t for t in self.tickets.values() if t.lead_id == lead_id]
        return list(self.tickets.values())

    # Cancellation operations
    def save_cancellation_request(self, request: Any) -> None:
        if not hasattr(self, 'cancellation_requests'):
            self.cancellation_requests = {}
        self.cancellation_requests[request.request_id] = request

    def get_cancellation_request(self, request_id: str) -> Any | None:
        if not hasattr(self, 'cancellation_requests'):
            return None
        return self.cancellation_requests.get(request_id)

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]:
        if not hasattr(self, 'cancellation_requests'):
            return []
        if lead_id:
            return [r for r in self.cancellation_requests.values() if r.lead_id == lead_id]
        return list(self.cancellation_requests.values())

    # Email template operations
    def save_email_template(self, template: Any) -> None:
        if not hasattr(self, 'email_templates'):
            self.email_templates = {}
        self.email_templates[template.template_id] = template

    def get_email_template(self, template_id: str) -> Any | None:
        if not hasattr(self, 'email_templates'):
            return None
        return self.email_templates.get(template_id)

    def list_email_templates(self) -> list[Any]:
        if not hasattr(self, 'email_templates'):
            return []
        return list(self.email_templates.values())


class SqliteStorageBackend:
    """Durable, zero-cloud SQLite storage backend for leads, sandboxes, and idempotency."""

    def __init__(self, db_path: str = "leadops.db") -> None:
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

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
            for col in ["company_name", "contact_email", "source_url", "jurisdiction", "slug", "outreach_subject", "outreach_body", "repo_url"]:
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
                    buyout_paid, audit_log, company_name, contact_email,
                    source_url, jurisdiction, slug, outreach_subject,
                    outreach_body, repo_url, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    contact_email=excluded.contact_email,
                    source_url=excluded.source_url,
                    jurisdiction=excluded.jurisdiction,
                    slug=excluded.slug,
                    outreach_subject=excluded.outreach_subject,
                    outreach_body=excluded.outreach_body,
                    repo_url=excluded.repo_url,
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
                    getattr(lead, "contact_email", "") or "",
                    getattr(lead, "source_url", "") or "",
                    getattr(lead, "jurisdiction", "") or "",
                    getattr(lead, "slug", "") or "",
                    getattr(lead, "outreach_subject", "") or "",
                    getattr(lead, "outreach_body", "") or "",
                    getattr(lead, "repo_url", "") or "",
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
            conn.commit()

    # Ticket operations
    def save_ticket(self, ticket: Any) -> None:
        self._init_new_tables()
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
        self._init_new_tables()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_ticket(row)

    def list_tickets(self, lead_id: str | None = None) -> list[Any]:
        self._init_new_tables()
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
        self._init_new_tables()
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
        self._init_new_tables()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cancellation_requests WHERE request_id = ?", (request_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_cancellation_request(row)

    def list_cancellation_requests(self, lead_id: str | None = None) -> list[Any]:
        self._init_new_tables()
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
        self._init_new_tables()
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
        self._init_new_tables()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_templates WHERE template_id = ?", (template_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_email_template(row)

    def list_email_templates(self) -> list[Any]:
        self._init_new_tables()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_templates ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [self._row_to_email_template(row) for row in rows]

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
            contact_email=get_col("contact_email", ""),
            source_url=get_col("source_url", ""),
            jurisdiction=get_col("jurisdiction", ""),
            slug=get_col("slug", ""),
            outreach_subject=get_col("outreach_subject", ""),
            outreach_body=get_col("outreach_body", ""),
            repo_url=get_col("repo_url", ""),
        )
