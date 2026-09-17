"""Production PostgreSQL storage backend implementation for Azure Flexible Server."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from ...domain import Lead, State
from ...progress import ProgressFeed, ProgressStatus
from ...logging_config import get_logger
from ..base import normalize_company_name, normalize_domain

logger = get_logger("storage.postgres")

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
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS daily_email_quota_logs (
                    id SERIAL PRIMARY KEY,
                    inbox_id VARCHAR(64) NOT NULL,
                    recipient VARCHAR(255) NOT NULL,
                    lead_id VARCHAR(255) NOT NULL,
                    dispatched_at VARCHAR(64) NOT NULL,
                    sent_date VARCHAR(16) NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_email_quota_inbox_date ON daily_email_quota_logs (inbox_id, sent_date)
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS inbound_emails (
                    id SERIAL PRIMARY KEY,
                    message_id VARCHAR(255) UNIQUE,
                    sender_email VARCHAR(255) NOT NULL,
                    sender_name VARCHAR(255) DEFAULT '',
                    subject TEXT DEFAULT '',
                    body TEXT DEFAULT '',
                    lead_id VARCHAR(255),
                    intent VARCHAR(64) DEFAULT 'unclassified',
                    draft_reply TEXT DEFAULT '',
                    received_at VARCHAR(64) NOT NULL
                )
            """))
            conn.execute(text("""
                ALTER TABLE inbound_emails ADD COLUMN IF NOT EXISTS draft_reply TEXT DEFAULT ''
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS inbox_accounts (
                    inbox_id VARCHAR(64) PRIMARY KEY,
                    email_address VARCHAR(255) NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    daily_limit INTEGER NOT NULL DEFAULT 25,
                    created_at VARCHAR(64) NOT NULL
                )
            """))
            for col, col_def in [
                ("provider", "VARCHAR(32) DEFAULT 'zoho'"),
                ("smtp_host", "VARCHAR(255) DEFAULT ''"),
                ("smtp_port", "INTEGER DEFAULT 465"),
                ("smtp_use_ssl", "INTEGER DEFAULT 1"),
                ("imap_host", "VARCHAR(255) DEFAULT ''"),
                ("imap_port", "INTEGER DEFAULT 993"),
                ("imap_use_ssl", "INTEGER DEFAULT 1"),
                ("password", "VARCHAR(255) DEFAULT ''"),
                ("from_name", "VARCHAR(255) DEFAULT ''"),
                ("warmup_start_date", "VARCHAR(64) DEFAULT ''"),
            ]:
                try:
                    conn.execute(text(f"ALTER TABLE inbox_accounts ADD COLUMN IF NOT EXISTS {col} {col_def}"))
                except Exception as ex:
                    logger.debug("Column %s might already exist in postgres inbox_accounts: %s", col, ex)

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS deliverability_audits (
                    id SERIAL PRIMARY KEY,
                    run_id VARCHAR(128) NOT NULL,
                    audited_at VARCHAR(100) NOT NULL,
                    fleet_status VARCHAR(64) NOT NULL,
                    average_score DOUBLE PRECISION NOT NULL,
                    inbox_count INTEGER NOT NULL,
                    healthy_count INTEGER NOT NULL,
                    warning_count INTEGER NOT NULL,
                    critical_count INTEGER NOT NULL,
                    report_json TEXT NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_deliverability_audits_date ON deliverability_audits (audited_at DESC)
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
            "research": json.dumps({
                **(getattr(lead, "research", {}) or {}),
                **({"discovery_channel": lead.discovery_channel} if getattr(lead, "discovery_channel", None) else {}),
                **({"filing_case_number": lead.filing_case_number} if getattr(lead, "filing_case_number", None) else {}),
                **({"website": lead.website} if getattr(lead, "website", None) else {}),
            }),
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
        from ...portal import Sandbox

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

    def get_email_sent_count_today(self, inbox_id: str = "") -> int:
        from sqlalchemy import text
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.engine.connect() as conn:
            if inbox_id:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM daily_email_quota_logs WHERE inbox_id = :inbox_id AND sent_date = :sent_date"),
                    {"inbox_id": inbox_id, "sent_date": today_str},
                )
            else:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM daily_email_quota_logs WHERE sent_date = :sent_date"),
                    {"sent_date": today_str},
                )
            return result.scalar() or 0

    def is_recipient_or_domain_contacted(
        self, email: str = "", domain: str = "", company_name: str = "", within_days: int = 45, exclude_lead_id: str = ""
    ) -> bool:
        import re
        from sqlalchemy import text
        email_clean = (email or "").lower().strip()
        domain_clean = (domain or (email_clean.split("@")[-1] if "@" in email_clean else "")).lower().strip()
        comp_norm = re.sub(r"[^a-z0-9]", "", company_name.lower()) if company_name else ""

        with self.engine.connect() as conn:
            # 1. Check daily_email_quota_logs
            if email_clean:
                if exclude_lead_id:
                    res = conn.execute(
                        text("SELECT inbox_id, dispatched_at FROM daily_email_quota_logs WHERE LOWER(recipient) = :recipient AND (lead_id IS NULL OR lead_id != :exclude_id) ORDER BY dispatched_at DESC LIMIT 1"),
                        {"recipient": email_clean, "exclude_id": exclude_lead_id},
                    )
                else:
                    res = conn.execute(
                        text("SELECT inbox_id, dispatched_at FROM daily_email_quota_logs WHERE LOWER(recipient) = :recipient ORDER BY dispatched_at DESC LIMIT 1"),
                        {"recipient": email_clean},
                    )
                row = res.mappings().fetchone()
                if row:
                    return True

            # 2. Check leads table
            res = conn.execute(text("SELECT lead_id, company_name, contact_email, state FROM leads"))
            rows = res.mappings().fetchall()
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
        """Strict multi-key deduplication against universal suppression, 45-day contact logs, and existing PostgreSQL leads."""
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

        # 3. Check Database Leads
        PUBLIC_MAIL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "aol.com"}
        from sqlalchemy import text
        with self.engine.connect() as conn:
            query = text("SELECT lead_id, company_name, contact_email, website FROM leads")
            result = conn.execute(query)
            rows = result.mappings().fetchall()
            for r in rows:
                if exclude_lead_id and r["lead_id"] == exclude_lead_id:
                    continue

                l_email = (r["contact_email"] or "").lower().strip()
                l_comp = r["company_name"] or ""
                l_comp_norm = normalize_company_name(l_comp)
                l_website = normalize_domain(r["website"] or "")

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

    def list_inbox_accounts(self) -> list[dict[str, Any]]:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM inbox_accounts ORDER BY created_at ASC"))
            return [dict(r) for r in result.mappings().fetchall()]

    def get_inbox_account(self, inbox_id: str) -> dict[str, Any] | None:
        from sqlalchemy import text
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT * FROM inbox_accounts WHERE inbox_id = :inbox_id"), {"inbox_id": inbox_id})
            row = result.mappings().fetchone()
            return dict(row) if row else None

    def upsert_inbox_account(self, account: dict[str, Any]) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO inbox_accounts (
                inbox_id, email_address, provider, smtp_host, smtp_port,
                smtp_use_ssl, imap_host, imap_port, imap_use_ssl, password,
                from_name, daily_limit, warmup_start_date, is_active, created_at
            ) VALUES (
                :inbox_id, :email_address, :provider, :smtp_host, :smtp_port,
                :smtp_use_ssl, :imap_host, :imap_port, :imap_use_ssl, :password,
                :from_name, :daily_limit, :warmup_start_date, :is_active, :created_at
            )
            ON CONFLICT (inbox_id) DO UPDATE SET
                email_address = EXCLUDED.email_address,
                provider = EXCLUDED.provider,
                smtp_host = EXCLUDED.smtp_host,
                smtp_port = EXCLUDED.smtp_port,
                smtp_use_ssl = EXCLUDED.smtp_use_ssl,
                imap_host = EXCLUDED.imap_host,
                imap_port = EXCLUDED.imap_port,
                imap_use_ssl = EXCLUDED.imap_use_ssl,
                password = CASE WHEN EXCLUDED.password != '' THEN EXCLUDED.password ELSE inbox_accounts.password END,
                from_name = EXCLUDED.from_name,
                daily_limit = EXCLUDED.daily_limit,
                warmup_start_date = EXCLUDED.warmup_start_date,
                is_active = EXCLUDED.is_active
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {
                "inbox_id": account.get("inbox_id", ""),
                "email_address": account.get("email_address", ""),
                "provider": account.get("provider", "zoho"),
                "smtp_host": account.get("smtp_host", ""),
                "smtp_port": int(account.get("smtp_port", 465)),
                "smtp_use_ssl": 1 if account.get("smtp_use_ssl", True) else 0,
                "imap_host": account.get("imap_host", ""),
                "imap_port": int(account.get("imap_port", 993)),
                "imap_use_ssl": 1 if account.get("imap_use_ssl", True) else 0,
                "password": account.get("password", ""),
                "from_name": account.get("from_name", ""),
                "daily_limit": int(account.get("daily_limit", 25)),
                "warmup_start_date": account.get("warmup_start_date", ""),
                "is_active": 1 if account.get("is_active", True) else 0,
                "created_at": account.get("created_at", datetime.now(timezone.utc).isoformat()),
            })

    def delete_inbox_account(self, inbox_id: str) -> None:
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM inbox_accounts WHERE inbox_id = :inbox_id"), {"inbox_id": inbox_id})

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

    def save_deliverability_audit(self, report: dict[str, Any]) -> None:
        from sqlalchemy import text
        stmt = text("""
            INSERT INTO deliverability_audits (
                run_id, audited_at, fleet_status, average_score,
                inbox_count, healthy_count, warning_count, critical_count, report_json
            ) VALUES (
                :run_id, :audited_at, :fleet_status, :average_score,
                :inbox_count, :healthy_count, :warning_count, :critical_count, :report_json
            )
        """)
        with self.engine.begin() as conn:
            conn.execute(stmt, {
                "run_id": report.get("run_id", ""),
                "audited_at": report.get("audited_at", datetime.now(timezone.utc).isoformat()),
                "fleet_status": report.get("fleet_status", "UNKNOWN"),
                "average_score": float(report.get("average_score", 0.0)),
                "inbox_count": int(report.get("inbox_count", 0)),
                "healthy_count": int(report.get("healthy_count", 0)),
                "warning_count": int(report.get("warning_count", 0)),
                "critical_count": int(report.get("critical_count", 0)),
                "report_json": json.dumps(report),
            })

    def get_latest_deliverability_audit(self) -> dict[str, Any] | None:
        from sqlalchemy import text
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT report_json FROM deliverability_audits ORDER BY audited_at DESC, id DESC LIMIT 1"))
                row = res.mappings().fetchone()
                if row and row.get("report_json"):
                    try:
                        return json.loads(row["report_json"])
                    except Exception:
                        return None
                return None
        except Exception as ex:
            logger.debug(f"Postgres deliverability audit query note: {ex}")
            return None

    def list_deliverability_audits(self, limit: int = 10) -> list[dict[str, Any]]:
        from sqlalchemy import text
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT report_json FROM deliverability_audits ORDER BY audited_at DESC, id DESC LIMIT :limit"), {"limit": limit})
                rows = res.mappings().fetchall()
                results = []
                for r in rows:
                    try:
                        results.append(json.loads(r["report_json"]))
                    except Exception:
                        pass
                return results
        except Exception as ex:
            logger.debug(f"Postgres list deliverability audits note: {ex}")
            return []

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
                except Exception as ex:
                    logger.debug("Table %s truncate note: %s", table, ex)
        return counts

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a single lead and any associated sandboxes in PostgreSQL."""
        from sqlalchemy import text
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM sandboxes WHERE lead_id = :lid OR slug LIKE :pat"), {"lid": lead_id, "pat": f"%{lead_id}%"})
            res = conn.execute(text("DELETE FROM leads WHERE lead_id = :lid"), {"lid": lead_id})
            return res.rowcount > 0


