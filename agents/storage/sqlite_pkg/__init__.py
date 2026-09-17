"""Durable SQLite storage backend implementation."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from ...domain import Lead, State
from ...progress import ProgressFeed, ProgressStatus
from ...logging_config import get_logger
from ..base import normalize_company_name, normalize_domain

logger = get_logger("storage.sqlite")

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

    def close(self) -> None:
        """Close any thread-local connection for this storage instance."""
        if hasattr(self._local, "conn"):
            try:
                self._local.conn.close()
            except Exception:
                pass
            delattr(self._local, "conn")

    def __enter__(self) -> SqliteStorageBackend:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

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
            for col in ["company_name", "contact_name", "contact_role", "contact_email", "contact_phone", "target_portal_name", "source_url", "website", "jurisdiction", "slug", "outreach_subject", "outreach_body", "repo_url"]:
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
            # Funnel & Low-Friction Pricing columns
            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN deposit_amount_usd REAL DEFAULT 99.0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE leads ADD COLUMN unlocked_30d_backlog INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            # Deliverability Suite & Email Provider columns
            for col, col_def in [
                ("deliverability_score", "INTEGER DEFAULT NULL"),
                ("deliverability_status", "TEXT DEFAULT ''"),
                ("deliverability_checked_at", "TEXT DEFAULT ''"),
                ("email_provider", "TEXT DEFAULT ''"),
                ("email_mx_hosts", "TEXT DEFAULT '[]'"),
                ("city", "TEXT DEFAULT ''"),
                ("state_code", "TEXT DEFAULT ''"),
                ("county", "TEXT DEFAULT ''"),
                ("county_fips", "TEXT DEFAULT ''"),
                ("outreach_touch_count", "INTEGER DEFAULT 0"),
                ("last_outreach_at", "TEXT DEFAULT ''"),
                ("next_outreach_at", "TEXT DEFAULT ''"),
                ("outreach_replied", "INTEGER DEFAULT 0"),
                ("outreach_thread_id", "TEXT DEFAULT ''"),
                ("sequence_state", "TEXT DEFAULT 'NOT_ENROLLED'"),
                ("recipient_timezone", "TEXT DEFAULT 'America/Chicago'"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} {col_def}")
                except sqlite3.OperationalError:
                    pass
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sequence_dispatch_log (
                    idempotency_key TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    touch_number INTEGER NOT NULL,
                    dispatched_at TEXT NOT NULL,
                    recipient_email TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_seq_dispatch_lead_id ON sequence_dispatch_log (lead_id)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS universal_suppression (
                    identifier TEXT PRIMARY KEY,
                    suppressed_at TEXT NOT NULL,
                    reason TEXT DEFAULT ''
                )
                """
            )
            try:
                cursor.execute("ALTER TABLE universal_suppression ADD COLUMN reason TEXT DEFAULT ''")
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS candidate_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    contact_email TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    reason TEXT DEFAULT '',
                    jurisdiction TEXT DEFAULT '',
                    lead_id TEXT DEFAULT '',
                    evaluated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_cand_eval_chan ON candidate_evaluations (channel)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_cand_eval_status ON candidate_evaluations (status)
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
                    automation_opportunity_score, purchase_probability, pain_severity, qualification_verdict, research,
                    deposit_amount_usd, unlocked_30d_backlog, updated_at,
                    deliverability_score, deliverability_status, deliverability_checked_at, email_provider, email_mx_hosts,
                    city, state_code, county, county_fips,
                    outreach_touch_count, last_outreach_at, next_outreach_at, outreach_replied, outreach_thread_id,
                    sequence_state, recipient_timezone
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?
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
                    deposit_amount_usd=excluded.deposit_amount_usd,
                    unlocked_30d_backlog=excluded.unlocked_30d_backlog,
                    deliverability_score=excluded.deliverability_score,
                    deliverability_status=excluded.deliverability_status,
                    deliverability_checked_at=excluded.deliverability_checked_at,
                    email_provider=excluded.email_provider,
                    email_mx_hosts=excluded.email_mx_hosts,
                    city=excluded.city,
                    state_code=excluded.state_code,
                    county=excluded.county,
                    county_fips=excluded.county_fips,
                    outreach_touch_count=excluded.outreach_touch_count,
                    last_outreach_at=excluded.last_outreach_at,
                    next_outreach_at=excluded.next_outreach_at,
                    outreach_replied=excluded.outreach_replied,
                    outreach_thread_id=excluded.outreach_thread_id,
                    sequence_state=excluded.sequence_state,
                    recipient_timezone=excluded.recipient_timezone,
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
                    getattr(lead, "winback_stage", 0) or 0,
                    getattr(lead, "heartbeat_count", 0) or 0,
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
                    json.dumps({
                        **(getattr(lead, "research", {}) or {}),
                        **({"discovery_channel": lead.discovery_channel} if getattr(lead, "discovery_channel", None) else {}),
                        **({"filing_case_number": lead.filing_case_number} if getattr(lead, "filing_case_number", None) else {}),
                        **({"website": lead.website} if getattr(lead, "website", None) else {}),
                    }),
                    float(getattr(lead, "deposit_amount_usd", 99.00) or 99.00),
                    1 if getattr(lead, "unlocked_30d_backlog", False) else 0,
                    datetime.now(timezone.utc).isoformat(),
                    getattr(lead, "deliverability_score", None),
                    getattr(lead, "deliverability_status", "") or "",
                    getattr(lead, "deliverability_checked_at", "") or "",
                    getattr(lead, "email_provider", "") or "",
                    json.dumps(getattr(lead, "email_mx_hosts", []) or []),
                    getattr(lead, "city", "") or "",
                    getattr(lead, "state_code", "") or "",
                    getattr(lead, "county", "") or "",
                    getattr(lead, "county_fips", "") or "",
                    int(getattr(lead, "outreach_touch_count", 0) or 0),
                    getattr(lead, "last_outreach_at", "") or "",
                    getattr(lead, "next_outreach_at", "") or "",
                    1 if getattr(lead, "outreach_replied", False) else 0,
                    getattr(lead, "outreach_thread_id", "") or "",
                    getattr(lead, "sequence_state", "NOT_ENROLLED") or "NOT_ENROLLED",
                    getattr(lead, "recipient_timezone", "America/Chicago") or "America/Chicago",
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
        from ...portal import Sandbox

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
            for col, col_def in [
                ("provider", "TEXT DEFAULT 'zoho'"),
                ("smtp_host", "TEXT DEFAULT ''"),
                ("smtp_port", "INTEGER DEFAULT 465"),
                ("smtp_use_ssl", "INTEGER DEFAULT 1"),
                ("imap_host", "TEXT DEFAULT ''"),
                ("imap_port", "INTEGER DEFAULT 993"),
                ("imap_use_ssl", "INTEGER DEFAULT 1"),
                ("password", "TEXT DEFAULT ''"),
                ("from_name", "TEXT DEFAULT ''"),
                ("daily_limit", "INTEGER DEFAULT 25"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE inbox_accounts ADD COLUMN {col} {col_def}")
                except Exception as ex:
                    logger.debug("Column %s might already exist in inbox_accounts: %s", col, ex)
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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS deliverability_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    audited_at TEXT NOT NULL,
                    fleet_status TEXT NOT NULL,
                    average_score REAL NOT NULL,
                    inbox_count INTEGER NOT NULL,
                    healthy_count INTEGER NOT NULL,
                    warning_count INTEGER NOT NULL,
                    critical_count INTEGER NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS candidate_evaluations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_name TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    contact_email TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'QUALIFIED',
                    reason TEXT DEFAULT '',
                    jurisdiction TEXT DEFAULT '',
                    lead_id TEXT DEFAULT '',
                    evaluated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_candidate_evaluations_channel ON candidate_evaluations (channel)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_candidate_evaluations_status ON candidate_evaluations (status)
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS ix_candidate_evaluations_lead ON candidate_evaluations (lead_id)
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

    def get_email_sent_count_today(self, inbox_id: str = "") -> int:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if inbox_id:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM daily_email_quota_logs
                    WHERE inbox_id = ? AND sent_date = ?
                    """,
                    (inbox_id, today_str),
                )
            else:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM daily_email_quota_logs
                    WHERE sent_date = ?
                    """,
                    (today_str,),
                )
            row = cursor.fetchone()
            return row[0] if row else 0

    def is_recipient_or_domain_contacted(
        self, email: str = "", domain: str = "", company_name: str = "", within_days: int = 45, exclude_lead_id: str = ""
    ) -> bool:
        import re
        email_clean = (email or "").lower().strip()
        domain_clean = (domain or (email_clean.split("@")[-1] if "@" in email_clean else "")).lower().strip()
        comp_norm = re.sub(r"[^a-z0-9]", "", company_name.lower()) if company_name else ""

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Check daily_email_quota_logs
            if email_clean:
                if exclude_lead_id:
                    cursor.execute(
                        "SELECT inbox_id, dispatched_at FROM daily_email_quota_logs WHERE LOWER(recipient) = ? AND (lead_id IS NULL OR lead_id != ?) ORDER BY dispatched_at DESC LIMIT 1",
                        (email_clean, exclude_lead_id),
                    )
                else:
                    cursor.execute(
                        "SELECT inbox_id, dispatched_at FROM daily_email_quota_logs WHERE LOWER(recipient) = ? ORDER BY dispatched_at DESC LIMIT 1",
                        (email_clean,),
                    )
                row = cursor.fetchone()
                if row:
                    return True

            # 2. Check leads table
            cursor.execute("SELECT lead_id, company_name, contact_email, state FROM leads")
            rows = cursor.fetchall()
            for r in rows:
                if exclude_lead_id and r["lead_id"] == exclude_lead_id:
                    continue
                l_email = (r["contact_email"] or "").lower().strip()
                l_comp = r["company_name"] or ""
                l_comp_norm = re.sub(r"[^a-z0-9]", "", l_comp.lower())
                l_state = r["state"] or ""

                if email_clean and l_email == email_clean:
                    if l_state in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                        return True

                if domain_clean and domain_clean not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"):
                    if l_email.endswith(f"@{domain_clean}") and l_state in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                        return True

                if comp_norm and len(comp_norm) >= 4 and l_comp_norm:
                    if (comp_norm == l_comp_norm or comp_norm in l_comp_norm or l_comp_norm in comp_norm) and l_state in ("OUTREACH_SENT", "PITCH_PENDING_APPROVAL", "REVIEW", "REPLIED", "CUSTOMER", "CONVERSATIONAL_INTAKE"):
                        return True

        return False

    def check_prospect_deduplication(
        self,
        company_name: str = "",
        domain: str = "",
        email: str = "",
        exclude_lead_id: str = "",
    ) -> tuple[bool, str]:
        """Strict multi-key deduplication against universal suppression, 45-day contact logs, and existing database leads."""
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

        # 3. Check All Existing Leads in Database
        PUBLIC_MAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads")
            rows = cursor.fetchall()
            for r in rows:
                if exclude_lead_id and r["lead_id"] == exclude_lead_id:
                    continue

                r_dict = dict(r)
                l_email = (r_dict.get("contact_email") or "").lower().strip()
                l_comp = r_dict.get("company_name") or ""
                l_comp_norm = normalize_company_name(l_comp)
                raw_web = r_dict.get("website") or r_dict.get("source_url") or ""
                l_website = normalize_domain(raw_web)

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

    def list_inbox_accounts(self) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inbox_accounts ORDER BY created_at ASC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_inbox_account(self, inbox_id: str) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inbox_accounts WHERE inbox_id = ?", (inbox_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_inbox_account(self, account: dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO inbox_accounts (
                    inbox_id, email_address, provider, smtp_host, smtp_port,
                    smtp_use_ssl, imap_host, imap_port, imap_use_ssl, password,
                    from_name, daily_limit, warmup_start_date, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(inbox_id) DO UPDATE SET
                    email_address = excluded.email_address,
                    provider = excluded.provider,
                    smtp_host = excluded.smtp_host,
                    smtp_port = excluded.smtp_port,
                    smtp_use_ssl = excluded.smtp_use_ssl,
                    imap_host = excluded.imap_host,
                    imap_port = excluded.imap_port,
                    imap_use_ssl = excluded.imap_use_ssl,
                    password = CASE WHEN excluded.password != '' THEN excluded.password ELSE inbox_accounts.password END,
                    from_name = excluded.from_name,
                    daily_limit = excluded.daily_limit,
                    warmup_start_date = excluded.warmup_start_date,
                    is_active = excluded.is_active
                """,
                (
                    account.get("inbox_id", ""),
                    account.get("email_address", ""),
                    account.get("provider", "zoho"),
                    account.get("smtp_host", ""),
                    int(account.get("smtp_port", 465)),
                    1 if account.get("smtp_use_ssl", True) else 0,
                    account.get("imap_host", ""),
                    int(account.get("imap_port", 993)),
                    1 if account.get("imap_use_ssl", True) else 0,
                    account.get("password", ""),
                    account.get("from_name", ""),
                    int(account.get("daily_limit", 25)),
                    account.get("warmup_start_date", ""),
                    1 if account.get("is_active", True) else 0,
                    account.get("created_at", datetime.now(timezone.utc).isoformat()),
                ),
            )
            conn.commit()

    def delete_inbox_account(self, inbox_id: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM inbox_accounts WHERE inbox_id = ?", (inbox_id,))
            conn.commit()

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

    def save_deliverability_audit(self, report: dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO deliverability_audits (
                    run_id, audited_at, fleet_status, average_score,
                    inbox_count, healthy_count, warning_count, critical_count, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.get("run_id", ""),
                    report.get("audited_at", datetime.now(timezone.utc).isoformat()),
                    report.get("fleet_status", "UNKNOWN"),
                    float(report.get("average_score", 0.0)),
                    int(report.get("inbox_count", 0)),
                    int(report.get("healthy_count", 0)),
                    int(report.get("warning_count", 0)),
                    int(report.get("critical_count", 0)),
                    json.dumps(report),
                ),
            )
            conn.commit()

    def get_latest_deliverability_audit(self) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT report_json FROM deliverability_audits ORDER BY audited_at DESC, id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row and row["report_json"]:
                try:
                    return json.loads(row["report_json"])
                except Exception:
                    return None
            return None

    def list_deliverability_audits(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT report_json FROM deliverability_audits ORDER BY audited_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                try:
                    results.append(json.loads(r["report_json"]))
                except Exception:
                    pass
            return results

    # Sequence dispatch idempotency & fail-closed universal suppression
    def record_sequence_dispatch(
        self,
        idempotency_key: str,
        lead_id: str,
        touch_number: int,
        recipient_email: str,
        status: str = "DISPATCHED",
        metadata: dict | None = None,
    ) -> bool:
        """Record an outbound sequence dispatch event with durable idempotency key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO sequence_dispatch_log (
                        idempotency_key, lead_id, touch_number, dispatched_at, recipient_email, status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        idempotency_key,
                        lead_id,
                        touch_number,
                        datetime.now(timezone.utc).isoformat(),
                        recipient_email,
                        status,
                        json.dumps(metadata or {}),
                    ),
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def has_sequence_dispatch(self, idempotency_key: str) -> bool:
        """Check if a specific sequence touch was already dispatched."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM sequence_dispatch_log WHERE idempotency_key = ?",
                (idempotency_key,),
            )
            return cursor.fetchone() is not None

    def add_to_global_suppression(self, identifier: str, reason: str = "") -> None:
        """Add an email or domain to the universal suppression database."""
        ident = (identifier or "").strip().lower()
        if not ident:
            return
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS universal_suppression (
                    identifier TEXT PRIMARY KEY,
                    suppressed_at TEXT NOT NULL,
                    reason TEXT DEFAULT ''
                )
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO universal_suppression (identifier, suppressed_at, reason)
                VALUES (?, ?, ?)
                """,
                (ident, datetime.now(timezone.utc).isoformat(), reason or ""),
            )
            conn.commit()

    def is_globally_suppressed(self, email: str = "", domain: str = "") -> bool:
        """Millisecond fail-closed suppression check against global suppression list and opted-out leads."""
        email_clean = (email or "").strip().lower()
        domain_clean = (domain or (email_clean.split("@")[-1] if "@" in email_clean else "")).strip().lower()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS universal_suppression (
                    identifier TEXT PRIMARY KEY,
                    suppressed_at TEXT NOT NULL,
                    reason TEXT DEFAULT ''
                )
                """
            )
            if email_clean:
                cursor.execute("SELECT 1 FROM universal_suppression WHERE identifier = ?", (email_clean,))
                if cursor.fetchone() is not None:
                    return True
            if domain_clean:
                cursor.execute("SELECT 1 FROM universal_suppression WHERE identifier = ?", (domain_clean,))
                if cursor.fetchone() is not None:
                    return True

            # Also check leads table
            if email_clean:
                cursor.execute("SELECT 1 FROM leads WHERE LOWER(contact_email) = ? AND state = 'ARCHIVED'", (email_clean,))
                if cursor.fetchone() is not None:
                    return True

        return False


    @staticmethod
    def _row_to_ticket(row: sqlite3.Row):
        from ...models import Ticket, TicketType, TicketStatus, TicketPriority
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
        from ...models import CancellationRequest, CancellationStatus
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
        from ...models import EmailTemplate, ABTestVariant
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
            website=(
                get_col("website", "")
                or (json.loads(get_col("research", "{}")).get("website", "") if isinstance(get_col("research", "{}"), str) and get_col("research", "{}").strip().startswith("{") else (get_col("research", {}).get("website", "") if isinstance(get_col("research", {}), dict) else ""))
                or (json.loads(get_col("research", "{}")).get("domain", "") if isinstance(get_col("research", "{}"), str) and get_col("research", "{}").strip().startswith("{") else (get_col("research", {}).get("domain", "") if isinstance(get_col("research", {}), dict) else ""))
            ),
            discovery_channel=(
                get_col("discovery_channel", "")
                or (json.loads(get_col("research", "{}")).get("discovery_channel", "") if isinstance(get_col("research", "{}"), str) and get_col("research", "{}").strip().startswith("{") else (get_col("research", {}).get("discovery_channel", "") if isinstance(get_col("research", {}), dict) else ""))
                or "CATALOG_SEARCH"
            ),
            filing_case_number=(
                get_col("filing_case_number", "")
                or (json.loads(get_col("research", "{}")).get("filing_case_number", "") if isinstance(get_col("research", "{}"), str) and get_col("research", "{}").strip().startswith("{") else (get_col("research", {}).get("filing_case_number", "") if isinstance(get_col("research", {}), dict) else ""))
            ),
            deposit_amount_usd=float(get_col("deposit_amount_usd", 99.00) or 99.00),
            unlocked_30d_backlog=bool(get_col("unlocked_30d_backlog", 0)),
            deliverability_score=(
                int(get_col("deliverability_score"))
                if get_col("deliverability_score") is not None and str(get_col("deliverability_score")).strip() != ""
                else None
            ),
            deliverability_status=str(get_col("deliverability_status", "") or ""),
            deliverability_checked_at=str(get_col("deliverability_checked_at", "") or ""),
            email_provider=str(get_col("email_provider", "") or ""),
            email_mx_hosts=(
                json.loads(get_col("email_mx_hosts", "[]"))
                if isinstance(get_col("email_mx_hosts", "[]"), str) and get_col("email_mx_hosts", "[]").strip().startswith("[")
                else (get_col("email_mx_hosts", []) if isinstance(get_col("email_mx_hosts", []), list) else [])
            ),
            city=str(get_col("city", "") or ""),
            state_code=str(get_col("state_code", "") or ""),
            county=str(get_col("county", "") or ""),
            county_fips=str(get_col("county_fips", "") or ""),
            outreach_touch_count=int(get_col("outreach_touch_count", 0) or 0),
            last_outreach_at=str(get_col("last_outreach_at", "") or ""),
            next_outreach_at=str(get_col("next_outreach_at", "") or ""),
            outreach_replied=bool(get_col("outreach_replied", 0)),
            outreach_thread_id=str(get_col("outreach_thread_id", "") or ""),
            sequence_state=str(get_col("sequence_state", "NOT_ENROLLED") or "NOT_ENROLLED"),
            recipient_timezone=str(get_col("recipient_timezone", "America/Chicago") or "America/Chicago"),
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
        """Record an evaluated candidate across any of the 5 public-record channels."""
        now_str = datetime.now(timezone.utc).isoformat()
        meta_str = json.dumps(metadata or {})
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO candidate_evaluations (
                    company_name, channel, contact_email, status, reason, jurisdiction, lead_id, evaluated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (company_name or "").strip(),
                    (channel or "").strip(),
                    (contact_email or "").strip(),
                    (status or "QUALIFIED").strip(),
                    (reason or "").strip(),
                    (jurisdiction or "").strip(),
                    (lead_id or "").strip(),
                    now_str,
                    meta_str,
                ),
            )
            row_id = cursor.lastrowid
            conn.commit()
            return {
                "id": row_id,
                "company_name": company_name,
                "channel": channel,
                "contact_email": contact_email,
                "status": status,
                "reason": reason,
                "jurisdiction": jurisdiction,
                "lead_id": lead_id,
                "evaluated_at": now_str,
            }

    def list_candidate_evaluations(
        self, limit: int = 100, channel: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        """List evaluated candidate records with optional channel and status filters."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT id, company_name, channel, contact_email, status, reason, jurisdiction, lead_id, evaluated_at, metadata FROM candidate_evaluations"
            params: list[Any] = []
            conditions = []
            if channel and channel.upper() != "ALL":
                conditions.append("UPPER(channel) = ?")
                params.append(channel.upper().strip())
            if status:
                conditions.append("status = ?")
                params.append(status.strip())
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(max(1, min(limit, 500)))

            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                meta = {}
                try:
                    meta = json.loads(r[9]) if r[9] else {}
                except Exception:
                    pass
                results.append({
                    "id": r[0],
                    "company_name": r[1],
                    "channel": r[2],
                    "contact_email": r[3],
                    "status": r[4],
                    "reason": r[5],
                    "jurisdiction": r[6],
                    "lead_id": r[7],
                    "evaluated_at": r[8],
                    "metadata": meta,
                })
            return results

    def get_candidate_evaluations_count(self) -> int:
        """Return total count of candidates evaluated across all channels."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM candidate_evaluations")
            row = cursor.fetchone()
            return row[0] if row else 0



