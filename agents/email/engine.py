"""High-Deliverability Email Engine & Autonomous Warmup Controller for LeadOps Swarm.

Coordinates:
1. Azure Communication Services (ACS) REST API dispatch on Port 443.
2. 31-Day Warm-Up & Ramp Schedule with Gaussian Jitter (180-420s).
3. Persistent SQLite queue for cold leads, peer warm-up targets, and dispatch logs.
4. LLM AI Agent for generating 100% authentic, organic warm-up emails and replies.
5. Inbound IMAP & Peer Inbox Watcher for auto-unspam (Spam -> INBOX) and positive engagement reply loops.
6. Multi-domain rollover triggering Domain 2 (olfmailer.net) at Day 15.
"""

import argparse
import contextlib
import email
import email.utils
import imaplib
import json
import logging
import os
import random
import smtplib
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.header import Header
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv

from .acs_client import AzureCommunicationEmailClient
from .knowlez_client import KnowlezDeliverabilityClient, get_knowlez_client
from agents.llm_client import LLMAgentEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("leadops.email.engine")

DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "leadops_email_engine.db"
DEFAULT_PRIMARY_DOMAIN = "olfmailer.com"
DEFAULT_SECONDARY_DOMAIN = "olfmailer.net"
DEFAULT_SENDER_IDENTITY = "ben@olfmailer.com"

DEFAULT_SENDER_MAILBOXES: list[dict[str, str]] = [
    {"email": "ben@olfmailer.com", "name": "Ben | OmniLeadFeeder", "short_name": "Ben"},
    {"email": "alex@olfmailer.com", "name": "Alex | OmniLeadFeeder", "short_name": "Alex"},
    {"email": "contact@olfmailer.com", "name": "OmniLeadFeeder Operations", "short_name": "Operations"},
]


@dataclass
class RampStage:
    """Defines a warm-up ramp schedule tier."""

    min_day: int
    max_day: int
    daily_total: int
    cold_leads: int
    warmup_emails: int
    min_jitter_seconds: int
    max_jitter_seconds: int
    description: str


RAMP_SCHEDULE = [
    RampStage(1, 4, 4, 0, 4, 300, 600, "100% Peer Warm-up (Days 1-4)"),
    RampStage(5, 8, 10, 0, 10, 240, 480, "100% Peer Warm-up (Days 5-8)"),
    RampStage(9, 14, 18, 0, 18, 180, 360, "100% Peer Warm-up (Days 9-14)"),
    RampStage(15, 21, 25, 5, 20, 180, 420, "5 Cold Outreach + 20 Warm-up (Days 15-21)"),
    RampStage(22, 30, 35, 15, 20, 180, 420, "15 Cold Outreach + 20 Warm-up (Days 22-30)"),
    RampStage(31, 9999, 45, 30, 15, 180, 420, "Steady State: 30 Cold + 15 Warm-up (Day 31+)"),
]


class WarmupAgent:
    """LLM AI Agent that crafts authentic peer warm-up emails and contextual two-way replies."""

    def __init__(self, llm_engine: LLMAgentEngine | None = None) -> None:
        self.llm = llm_engine or LLMAgentEngine()

    def generate_warmup_email(self, sender_name: str = "Ben") -> tuple[str, str]:
        """Generate an organic, authentic peer conversation email using the LLM agent."""
        system_prompt = (
            "You are the Peer Deliverability & Warmup Communications Agent for LeadOps. "
            "Your job is to generate a realistic, organic, engaging work email between senior engineers, "
            "cloud architects, founders, or operations leads.\n\n"
            "CRITICAL RULES:\n"
            "1. Output valid JSON ONLY with exactly two keys: 'subject' and 'body'.\n"
            "2. Subject must be concise, natural, and relevant (3-7 words).\n"
            "3. Body must be 35-70 words: casual, professional, discussing technical or operational topics "
            "(e.g., PostgreSQL query planner, Azure Communication Services egress, AST pruning, scraper resilience, "
            "KEDA autoscaling, redis caching, API response latency, cloud architecture).\n"
            "4. NEVER sound like marketing, promotional copy, or sales outreach. No hyperlinks or URLs.\n"
            f"5. End with a natural sign-off: 'Best,\\n{sender_name}'."
        )

        user_prompt = "Generate a new, unique peer email discussing a recent engineering or system observation."

        try:
            raw = self.llm.generate_completion(system_prompt, user_prompt, temperature=0.7, max_tokens=250)
            cleaned = raw.strip()
            # Extract JSON substring if wrapped in markdown code blocks
            if "```" in cleaned:
                parts = cleaned.split("```")
                cleaned = parts[1] if len(parts) > 1 else cleaned
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
            data = json.loads(cleaned)
            subject = str(data.get("subject", "")).strip()
            body = str(data.get("body", "")).strip()
            if subject and body:
                logger.info(f"🤖 [LLM WARMUP GENERATED] Subject: '{subject}' ({len(body.split())} words)")
                return subject, body
        except Exception as exc:
            logger.warning(f"⚠️ LLM warm-up generation fallback triggered: {exc}")

        # Procedural fallback if LLM is unavailable or offline
        return SpintaxGenerator.generate_peer_warmup_spintax(sender_name=sender_name)

    def generate_reply_email(self, original_subject: str, original_body: str, responder_name: str = "Alex") -> str:
        """Generate a natural, context-aware reply to an incoming warm-up email using the LLM agent."""
        system_prompt = (
            "You are a colleague replying to a peer email in an ongoing technical discussion.\n"
            "CRITICAL RULES:\n"
            "1. Output the plain-text email reply body ONLY. No JSON, no quotes, no extra formatting.\n"
            "2. Keep it concise, natural, and conversational (25-50 words).\n"
            "3. Reference something specific mentioned in the original email.\n"
            f"4. Sign-off with: 'Best,\\n{responder_name}'."
        )

        user_prompt = f"Original Subject: {original_subject}\nOriginal Message:\n{original_body}\n\nWrite a thoughtful, authentic reply."

        try:
            reply = self.llm.generate_completion(system_prompt, user_prompt, temperature=0.7, max_tokens=200)
            cleaned = reply.strip().strip("\"'")
            if cleaned:
                logger.info(f"🤖 [LLM REPLY GENERATED] Length: {len(cleaned.split())} words")
                return cleaned
        except Exception as exc:
            logger.warning(f"⚠️ LLM warm-up reply fallback triggered: {exc}")

        return (
            f"Hey,\n\n"
            f"Thanks for the update. The metrics look solid on our end too. "
            f"Let me know if anything shifts during the next run.\n\n"
            f"Best,\n{responder_name}"
        )


class SpintaxGenerator:
    """Generates natural, varied, plain-text email bodies for outreach and procedural fallback."""

    @staticmethod
    def generate_outreach_spintax(lead: dict[str, Any], sender_name: str = "Ben") -> tuple[str, str]:
        """Generate conversational Zero-Link Touch 1 email per Pitcher agent directives (35-55 words)."""
        first_name = lead.get("first_name", "there").strip().capitalize() or "there"
        company = lead.get("company", "your team").strip() or "your team"
        jurisdiction = lead.get("jurisdiction", "your area").strip()

        greetings = ["Hi", "Hey", "Hello"]
        intros = [
            f"saw you handle filings in {jurisdiction}.",
            f"noticed your team at {company} works public record filings in {jurisdiction}.",
            f"came across your work at {company}.",
        ]
        hooks = [
            f"We pulled today's raw docket filings for {jurisdiction} directly into a clean sheet as a gift.",
            f"We ran a micro-scrape this morning on {jurisdiction} filings and put the verified records in a sheet.",
            f"We automated the daily filings feed for {jurisdiction} so you get fresh leads every morning.",
        ]
        closers = [
            "Mind if I send over the link?",
            "Would it be helpful if I shared the spreadsheet?",
            "Open to taking a quick look?",
        ]

        subject_patterns = [
            f"Question regarding {company}",
            f"{jurisdiction} filings for {company}",
            f"{first_name} / {company}",
        ]

        subject = random.choice(subject_patterns)
        body = (
            f"{random.choice(greetings)} {first_name},\n\n"
            f"{random.choice(intros)}\n\n"
            f"{random.choice(hooks)}\n\n"
            f"{random.choice(closers)}\n\n"
            f"{sender_name}\n"
            f"{DEFAULT_PRIMARY_DOMAIN}"
        )
        return subject, body

    @staticmethod
    def generate_peer_warmup_spintax(sender_name: str = "Ben") -> tuple[str, str]:
        """Procedural fallback for peer warm-up messages if LLM is offline."""
        topics = [
            ("Q3 Infrastructure Review", "Reviewing our pipeline latency across our regional nodes. Latency looks solid, under 200ms across all worker jobs."),
            ("Pipeline Telemetry Check", "The automated scraper self-healing loop caught three updated county selectors this morning without errors."),
            ("Data Contract Validation", "All verified records passed the 95% QA schema threshold on today's live ingestion cycle."),
            ("Deployment Synchronization", "Confirming the Azure Communication Services dispatch queue completed its morning window ahead of schedule."),
            ("System Optimization Notes", "Pruned the DOM AST parser tree down to 3,200 tokens. LLM extraction throughput increased significantly."),
        ]
        subject, note = random.choice(topics)
        body = f"Hey team,\n\n{note}\n\nLet me know if you spot any anomalies.\n\nBest,\n{sender_name}"
        return subject, body


class EmailEngineQueue:
    """Persistent SQLite database manager for engine queue, warm-up targets, and logs."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    @contextlib.contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create required tables and run migrations if columns are missing."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS engine_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS leads_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    first_name TEXT,
                    company TEXT,
                    jurisdiction TEXT,
                    status TEXT DEFAULT 'pending', -- pending, sent, failed, skipped
                    attempts INTEGER DEFAULT 0,
                    added_at TEXT NOT NULL,
                    sent_at TEXT
                );

                CREATE TABLE IF NOT EXISTS warmup_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    name TEXT,
                    status TEXT DEFAULT 'active',
                    total_sent INTEGER DEFAULT 0,
                    added_at TEXT NOT NULL,
                    last_sent_at TEXT,
                    password TEXT DEFAULT '',
                    provider TEXT DEFAULT 'gmail',
                    imap_host TEXT DEFAULT '',
                    imap_port INTEGER DEFAULT 993,
                    smtp_host TEXT DEFAULT '',
                    smtp_port INTEGER DEFAULT 465,
                    is_monitored INTEGER DEFAULT 0,
                    unspammed_count INTEGER DEFAULT 0,
                    replied_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS dispatch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    dispatch_type TEXT NOT NULL, -- cold_outreach, peer_warmup, test
                    status TEXT NOT NULL,
                    jitter_seconds REAL,
                    message_id TEXT,
                    created_at TEXT NOT NULL
                );
            """)

            # Ensure schema migration for existing databases missing monitoring columns
            cursor = conn.execute("PRAGMA table_info(warmup_targets)")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            migrations = [
                ("password", "TEXT DEFAULT ''"),
                ("provider", "TEXT DEFAULT 'gmail'"),
                ("imap_host", "TEXT DEFAULT ''"),
                ("imap_port", "INTEGER DEFAULT 993"),
                ("smtp_host", "TEXT DEFAULT ''"),
                ("smtp_port", "INTEGER DEFAULT 465"),
                ("is_monitored", "INTEGER DEFAULT 0"),
                ("unspammed_count", "INTEGER DEFAULT 0"),
                ("replied_count", "INTEGER DEFAULT 0"),
            ]
            for col_name, col_type in migrations:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE warmup_targets ADD COLUMN {col_name} {col_type}")

    def get_state(self, key: str, default: str = "") -> str:
        with self._get_conn() as conn:
            row = conn.execute("SELECT value FROM engine_state WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_state(self, key: str, value: str) -> None:
        with self._get_conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO engine_state (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value, now),
            )

    def enqueue_lead(self, email: str, first_name: str = "", company: str = "", jurisdiction: str = "") -> bool:
        try:
            with self._get_conn() as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO leads_queue (email, first_name, company, jurisdiction, added_at) VALUES (?, ?, ?, ?, ?)",
                    (email.strip().lower(), first_name.strip(), company.strip(), jurisdiction.strip(), now),
                )
                return True
        except sqlite3.IntegrityError:
            return False

    def enqueue_warmup_target(
        self,
        email: str,
        name: str = "",
        password: str = "",
        provider: str = "gmail",
        is_monitored: bool = False,
    ) -> bool:
        """Register a warm-up target inbox with optional credentials for 2-way unspam and reply loops."""
        clean_email = email.strip().lower()
        clean_provider = provider.lower().strip()

        imap_host = "imap.gmail.com" if clean_provider == "gmail" else "outlook.office365.com" if clean_provider in ("outlook", "office365") else ""
        smtp_host = "smtp.gmail.com" if clean_provider == "gmail" else "smtp-mail.outlook.com" if clean_provider in ("outlook", "office365") else ""
        smtp_port = 465 if clean_provider == "gmail" else 587

        try:
            with self._get_conn() as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    """
                    INSERT INTO warmup_targets (
                        email, name, added_at, password, provider, imap_host, imap_port, smtp_host, smtp_port, is_monitored
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        name = excluded.name,
                        password = CASE WHEN excluded.password != '' THEN excluded.password ELSE warmup_targets.password END,
                        provider = excluded.provider,
                        is_monitored = excluded.is_monitored
                    """,
                    (
                        clean_email, name.strip(), now, password.strip(), clean_provider,
                        imap_host, 993, smtp_host, smtp_port, 1 if is_monitored else 0
                    ),
                )
                return True
        except Exception as err:
            logger.error(f"Failed to register warm-up target '{clean_email}': {err}")
            return False

    def get_monitored_warmup_targets(self) -> list[dict[str, Any]]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM warmup_targets WHERE is_monitored = 1 AND password != ''"
            ).fetchall()
            return [dict(r) for r in rows]

    def record_unspam_event(self, target_id: int, count: int = 1) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE warmup_targets SET unspammed_count = unspammed_count + ? WHERE id = ?",
                (count, target_id),
            )

    def record_reply_event(self, target_id: int, count: int = 1) -> None:
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE warmup_targets SET replied_count = replied_count + ? WHERE id = ?",
                (count, target_id),
            )

    def pop_pending_lead(self) -> dict[str, Any] | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM leads_queue WHERE status = 'pending' ORDER BY id ASC LIMIT 1").fetchone()
            return dict(row) if row else None

    def mark_lead_sent(self, lead_id: int, status: str = "sent") -> None:
        with self._get_conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE leads_queue SET status = ?, sent_at = ?, attempts = attempts + 1 WHERE id = ?",
                (status, now, lead_id),
            )

    def get_next_warmup_target(self, exclude_email: str = "") -> dict[str, Any] | None:
        """Select next active warm receiver, excluding the current sender to prevent self-sends."""
        with self._get_conn() as conn:
            if exclude_email:
                row = conn.execute(
                    "SELECT * FROM warmup_targets WHERE status = 'active' AND lower(email) != lower(?) ORDER BY last_sent_at ASC, id ASC LIMIT 1",
                    (exclude_email.strip(),),
                ).fetchone()
                if row:
                    return dict(row)
            row = conn.execute(
                "SELECT * FROM warmup_targets WHERE status = 'active' ORDER BY last_sent_at ASC, id ASC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def record_warmup_sent(self, target_id: int) -> None:
        with self._get_conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE warmup_targets SET total_sent = total_sent + 1, last_sent_at = ? WHERE id = ?",
                (now, target_id),
            )

    def log_dispatch(
        self,
        recipient: str,
        sender: str,
        subject: str,
        dispatch_type: str,
        status: str,
        jitter_seconds: float,
        message_id: str = "",
    ) -> None:
        with self._get_conn() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO dispatch_logs (recipient, sender, subject, dispatch_type, status, jitter_seconds, message_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (recipient, sender, subject, dispatch_type, status, jitter_seconds, message_id, now),
            )

    def get_today_sent_counts(self) -> tuple[int, int]:
        """Return (cold_sent_today, warmup_sent_today)."""
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._get_conn() as conn:
            valid_statuses = "('Succeeded', 'sent', 'Running', 'SIMULATED_NO_CONNECTION_STRING', 'simulated')"
            cold_count = conn.execute(
                f"SELECT COUNT(*) AS c FROM dispatch_logs WHERE dispatch_type = 'cold_outreach' AND status IN {valid_statuses} AND created_at LIKE ?",
                (f"{today_prefix}%",),
            ).fetchone()["c"]
            warmup_count = conn.execute(
                f"SELECT COUNT(*) AS c FROM dispatch_logs WHERE dispatch_type = 'peer_warmup' AND status IN {valid_statuses} AND created_at LIKE ?",
                (f"{today_prefix}%",),
            ).fetchone()["c"]
            return cold_count, warmup_count

    def get_dispatch_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent dispatch logs."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM dispatch_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_warmup_targets(self) -> list[dict[str, Any]]:
        """Return all registered warm receiver accounts in the peer warmup pool."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, email, name, status, total_sent, added_at, last_sent_at, provider, imap_host, imap_port, smtp_host, smtp_port, is_monitored, unspammed_count, replied_count "
                "FROM warmup_targets ORDER BY id ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_warmup_target(self, target_id: int) -> bool:
        """Remove a warm receiver account from the peer warmup pool."""
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM warmup_targets WHERE id = ?", (target_id,))
            return cur.rowcount > 0



class PeerInboxWarmupWatcher:
    """Monitors registered test/warm-up inboxes via IMAP:
    1. Scans Spam/Junk folder: Moves emails from olfmailer.com to INBOX (crucial reputation signal).
    2. Scans INBOX: Reads unread warm-up emails, stars them, and drafts an LLM reply back to sender.
    """

    def __init__(self, queue: EmailEngineQueue, warmup_agent: WarmupAgent) -> None:
        self.queue = queue
        self.warmup_agent = warmup_agent

    def process_inbox(self, target: dict[str, Any]) -> dict[str, int]:
        """Perform unspam and reply cycle for a single monitored peer inbox."""
        email_addr = target["email"]
        password = target.get("password")
        imap_host = target.get("imap_host") or ("imap.gmail.com" if "gmail" in email_addr else "outlook.office365.com")
        imap_port = int(target.get("imap_port") or 993)

        if not password:
            return {"unspammed": 0, "replied": 0}

        unspammed = 0
        replied = 0

        try:
            # 1. Connect via IMAP SSL
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=20)
            mail.login(email_addr, password)

            # 2. Check Spam / Junk folders for olfmailer messages
            spam_folders = ['"[Gmail]/Spam"', '"Spam"', '"Junk"', '"Junk Email"']
            for folder in spam_folders:
                try:
                    status, _ = mail.select(folder)
                    if status != "OK":
                        continue

                    # Search for emails from olfmailer.com or olfmailer.net
                    status, msg_ids = mail.search(None, '(OR (FROM "olfmailer.com") (FROM "olfmailer.net"))')
                    if status == "OK" and msg_ids and msg_ids[0]:
                        ids = msg_ids[0].split()
                        for mid in ids:
                            logger.info(f"🛡️ [AUTO-UNSPAM] Found message from olfmailer in {folder} for {email_addr}. Moving to INBOX...")
                            # Move to INBOX
                            mail.copy(mid, "INBOX")
                            mail.store(mid, "+FLAGS", "\\Deleted")
                            unspammed += 1

                        mail.expunge()
                except Exception as folder_err:
                    logger.debug(f"Spam folder check {folder} skipped on {email_addr}: {folder_err}")

            if unspammed > 0:
                self.queue.record_unspam_event(target["id"], unspammed)
                logger.info(f"✅ [AUTO-UNSPAM SUCCESS] Moved {unspammed} emails from Spam to INBOX for {email_addr}!")

            # 3. Check INBOX for unread messages from olfmailer to reply to
            try:
                status, _ = mail.select("INBOX")
                if status == "OK":
                    status, msg_ids = mail.search(None, '(UNSEEN (OR (FROM "olfmailer.com") (FROM "olfmailer.net")))')
                    if status == "OK" and msg_ids and msg_ids[0]:
                        ids = msg_ids[0].split()
                        for mid in ids:
                            status, data = mail.fetch(mid, "(RFC822)")
                            if status != "OK" or not data:
                                continue

                            raw_msg = data[0][1]
                            parsed = email.message_from_bytes(raw_msg)
                            from_sender = parsed.get("From", "")
                            subject = parsed.get("Subject", "Re: Update")
                            msg_id_hdr = parsed.get("Message-ID", "")

                            # Extract body text
                            body_text = ""
                            if parsed.is_multipart():
                                for part in parsed.walk():
                                    if part.get_content_type() == "text/plain":
                                        body_text = part.get_payload(decode=True).decode(errors="ignore")
                                        break
                            else:
                                body_text = parsed.get_payload(decode=True).decode(errors="ignore")

                            # Mark read and star/flag
                            mail.store(mid, "+FLAGS", "(\\Seen \\Flagged)")

                            # Generate natural LLM reply
                            reply_text = self.warmup_agent.generate_reply_email(
                                original_subject=subject,
                                original_body=body_text,
                                responder_name=target.get("name") or "Alex",
                            )

                            # Calculate humanized response jitter (45 to 180 seconds delay in live operations)
                            resp_jitter = random.uniform(45.0, 180.0) if not os.environ.get("PYTEST_CURRENT_TEST") else 0.0
                            if resp_jitter > 0:
                                logger.info(
                                    f"⏳ [RESPONSE JITTER] Holding {resp_jitter:.1f}s ({resp_jitter/60:.1f} min) before dispatching peer reply to {from_sender}..."
                                )
                                time.sleep(resp_jitter)

                            # Dispatch reply via SMTP
                            smtp_host = target.get("smtp_host") or ("smtp.gmail.com" if "gmail" in email_addr else "smtp-mail.outlook.com")
                            smtp_port = int(target.get("smtp_port") or (465 if "gmail" in email_addr else 587))
                            self._send_smtp_reply(
                                from_email=email_addr,
                                password=password,
                                to_email=from_sender,
                                subject=f"Re: {subject.replace('Re: ', '')}",
                                body=reply_text,
                                in_reply_to=msg_id_hdr,
                                smtp_host=smtp_host,
                                smtp_port=smtp_port,
                            )
                            replied += 1
                            logger.info(f"💬 [PEER REPLY SENT] Sent 2-way conversation reply from {email_addr} -> {from_sender}")
            except Exception as inbox_err:
                logger.warning(f"INBOX check on {email_addr} error: {inbox_err}")

            if replied > 0:
                self.queue.record_reply_event(target["id"], replied)

            mail.logout()
        except Exception as exc:
            logger.warning(f"Peer inbox check for {email_addr} exception: {exc}")

        return {"unspammed": unspammed, "replied": replied}

    def _send_smtp_reply(
        self,
        from_email: str,
        password: str,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str,
        smtp_host: str,
        smtp_port: int,
    ) -> None:
        """Send an authenticated SMTP reply from the peer test inbox."""
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
            msg["References"] = in_reply_to

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()

        server.login(from_email, password)
        server.send_message(msg)
        server.quit()

    def run_monitoring_cycle(self) -> dict[str, int]:
        """Scan all registered and monitored peer inboxes for spam recovery and auto-replies."""
        monitored = self.queue.get_monitored_warmup_targets()
        if not monitored:
            return {"monitored_inboxes": 0, "unspammed": 0, "replied": 0}

        total_unspammed = 0
        total_replied = 0

        for target in monitored:
            res = self.process_inbox(target)
            total_unspammed += res.get("unspammed", 0)
            total_replied += res.get("replied", 0)

        # 2. Check if Microsoft Graph is authorized for Outlook unspam & reply
        try:
            from agents.email.microsoft_graph import get_microsoft_graph_client
            mg = get_microsoft_graph_client()
            if mg.is_authorized:
                mg_unspam = mg.scan_and_unspam_junk("olfmailer")
                mg_replied = mg.scan_and_reply_inbox(self.warmup_agent, "olfmailer")
                total_unspammed += mg_unspam
                total_replied += mg_replied
                if mg_unspam or mg_replied:
                    logger.info(f"📊 [MICROSOFT GRAPH CYCLE] Unspammed: {mg_unspam} | Replied: {mg_replied}")
        except Exception as ms_err:
            logger.debug(f"Microsoft Graph monitoring cycle error: {ms_err}")

        return {
            "monitored_inboxes": len(monitored),
            "unspammed": total_unspammed,
            "replied": total_replied,
        }


class EmailEngine:
    """Master controller managing ramp progression, Gaussian jitter queue loop, and ACS API dispatch."""

    def __init__(
        self,
        queue: EmailEngineQueue | None = None,
        acs_client: AzureCommunicationEmailClient | None = None,
        warmup_agent: WarmupAgent | None = None,
        knowlez_client: KnowlezDeliverabilityClient | None = None,
        sender_identity: str = DEFAULT_SENDER_IDENTITY,
        sender_mailboxes: list[dict[str, str]] | None = None,
    ) -> None:
        self.queue = queue or EmailEngineQueue()
        self.acs_client = acs_client or AzureCommunicationEmailClient()
        self.warmup_agent = warmup_agent or WarmupAgent()
        self.knowlez_client = knowlez_client or get_knowlez_client()
        self.inbox_watcher = PeerInboxWarmupWatcher(self.queue, self.warmup_agent)
        self.sender_identity = sender_identity
        self.sender_mailboxes = sender_mailboxes or list(DEFAULT_SENDER_MAILBOXES)
        self._sender_index = 0

    def get_next_sender(self) -> dict[str, str]:
        """Rotate across all 3 configured sending mailboxes (ben@, alex@, contact@olfmailer.com)."""
        if not self.sender_mailboxes:
            return {"email": self.sender_identity, "name": "Ben | OmniLeadFeeder", "short_name": "Ben"}
        mailbox = self.sender_mailboxes[self._sender_index % len(self.sender_mailboxes)]
        self._sender_index += 1
        return mailbox

    def get_current_day(self) -> int:
        """Calculate the current day of the warm-up cycle."""
        start_str = self.queue.get_state("warmup_start_date")
        now = datetime.now(timezone.utc)
        if not start_str:
            start_date = now.date()
            self.queue.set_state("warmup_start_date", start_date.isoformat())
            return 1
        try:
            start_date = datetime.fromisoformat(start_str).date()
            days = (now.date() - start_date).days + 1
            return max(1, days)
        except Exception:
            return 1

    def get_active_stage(self, day: int) -> RampStage:
        """Resolve current warm-up stage based on active day."""
        for stage in RAMP_SCHEDULE:
            if stage.min_day <= day <= stage.max_day:
                return stage
        return RAMP_SCHEDULE[-1]

    def calculate_gaussian_jitter(self, stage: RampStage) -> float:
        """Calculate Gaussian randomized delay between dispatches (3 to 7 minutes)."""
        mean = (stage.min_jitter_seconds + stage.max_jitter_seconds) / 2.0
        std_dev = (stage.max_jitter_seconds - stage.min_jitter_seconds) / 4.0
        jitter = random.gauss(mean, std_dev)
        return max(float(stage.min_jitter_seconds), min(float(stage.max_jitter_seconds), jitter))

    def dispatch_test_email(self, recipient: str, sender_address: str = "") -> dict[str, Any]:
        """Dispatch a single diagnostic test email to verify SPF, DKIM, and deliverability alignment."""
        sender = sender_address or self.get_next_sender()["email"]
        subject = f"Deliverability Verification - {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
        body = (
            "Deliverability telemetry check.\n\n"
            "Verifying Azure Communication Services DKIM signing, Cloudflare SPF alignment, and DMARC compliance.\n\n"
            "Status: System Operational"
        )
        logger.info(f"🧪 Dispatching diagnostic test email from {sender} to: {recipient}")
        result = self.acs_client.send_email(
            to_email=recipient,
            to_name="Deliverability Tester",
            subject=subject,
            text_body=body,
            sender_address=sender,
            is_transactional=True,
        )
        self.queue.log_dispatch(
            recipient=recipient,
            sender=sender,
            subject=subject,
            dispatch_type="test",
            status=result.get("status", "unknown"),
            jitter_seconds=0.0,
            message_id=result.get("message_id", ""),
        )
        return result

    def execute_worker_cycle(self, single_step: bool = False) -> None:
        """Run the main engine worker loop enforcing daily limits and humanized Gaussian jitter."""
        day = self.get_current_day()
        stage = self.get_active_stage(day)
        logger.info(f"🚀 Engine Worker Active | Day {day} | Tier: {stage.description}")

        # Check Domain 2 rollover notification
        if day >= 15:
            d2_status = self.queue.get_state("domain_2_warmup_ready")
            if d2_status != "ready":
                logger.info(
                    f"🔥 [MULTI-DOMAIN MILESTONE] Domain 1 ({DEFAULT_PRIMARY_DOMAIN}) reached Day {day}! "
                    f"Domain 2 ({DEFAULT_SECONDARY_DOMAIN}) is now READY for Day 1 warmup."
                )
                self.queue.set_state("domain_2_warmup_ready", "ready")

        # 1. Run peer inbox unspam and reply cycle
        watcher_stats = self.inbox_watcher.run_monitoring_cycle()
        if watcher_stats.get("unspammed", 0) > 0 or watcher_stats.get("replied", 0) > 0:
            logger.info(
                f"🛡️ [PEER INBOX CYCLE] Unspammed: {watcher_stats['unspammed']} | Replied: {watcher_stats['replied']}"
            )

        cold_sent, warmup_sent = self.queue.get_today_sent_counts()
        logger.info(f"📊 Daily Progress: Cold {cold_sent}/{stage.cold_leads} | Warm-up {warmup_sent}/{stage.warmup_emails}")

        # Determine dispatch candidate
        can_send_cold = cold_sent < stage.cold_leads
        can_send_warmup = warmup_sent < stage.warmup_emails

        # Enforce administrative cold outreach disablement
        auto_cold_allowed = os.environ.get("AUTO_OUTREACH_ENABLED", "false").lower().strip() in ("1", "true", "yes", "on", "active")
        if not auto_cold_allowed:
            can_send_cold = False

        if not can_send_cold and not can_send_warmup:
            if not auto_cold_allowed and stage.cold_leads > 0:
                logger.info("⏸️ Cold outreach is administratively disabled (AUTO_OUTREACH_ENABLED=false). Standing by.")
            else:
                logger.info("🏁 Daily quotas fulfilled for both cold outreach and peer warm-up. Standing by for next window.")
            return

        # Choose dispatch task (alternate or prioritize warmup)
        dispatch_type: Literal["cold_outreach", "peer_warmup"]
        if can_send_warmup and (not can_send_cold or random.random() < 0.7):
            dispatch_type = "peer_warmup"
        else:
            dispatch_type = "cold_outreach"

        # Execute selected dispatch
        if dispatch_type == "peer_warmup":
            sender_box = self.get_next_sender()
            sender_addr = sender_box["email"]
            sender_short = sender_box["short_name"]

            # Exclude current sender to avoid self-sends
            target = self.queue.get_next_warmup_target(exclude_email=sender_addr)
            if not target:
                logger.warning("⚠️ No active peer warm-up inboxes registered in queue. Enqueue targets via CLI.")
                return

            # Generate via LLM Warmup Agent with authentic persona
            subject, text_body = self.warmup_agent.generate_warmup_email(sender_name=sender_short)
            logger.info(f"📤 [PEER WARM-UP] Sending from {sender_addr} -> {target['email']} via LLM Agent...")
            res = self.acs_client.send_email(
                to_email=target["email"],
                to_name=target.get("name") or "Team Member",
                subject=subject,
                text_body=text_body,
                sender_address=sender_addr,
            )
            jitter = self.calculate_gaussian_jitter(stage)
            self.queue.record_warmup_sent(target["id"])
            self.queue.log_dispatch(
                recipient=target["email"],
                sender=sender_addr,
                subject=subject,
                dispatch_type="peer_warmup",
                status=res.get("status", "sent"),
                jitter_seconds=jitter,
                message_id=res.get("message_id", ""),
            )
        else:
            lead = self.queue.pop_pending_lead()
            if not lead:
                logger.info("ℹ️ No pending cold leads in queue.")
                return

            sender_box = self.get_next_sender()
            sender_addr = sender_box["email"]
            sender_short = sender_box["short_name"]

            # Pre-flight bounce shield using Knowlez Deliverability Suite
            if self.knowlez_client and self.knowlez_client.is_configured:
                kz = self.knowlez_client.verify_email(lead["email"])
                if not kz.get("unverified_fallback"):
                    if kz.get("valid") is False or kz.get("disposable") or not kz.get("mx_ok", True):
                        rej_reason = kz.get("reason") or "invalid_deliverability"
                        logger.warning(
                            f"🚫 [BOUNCE SHIELD] Suppressed cold send to {lead['email']}: Deliverability Suite flagged '{rej_reason}'."
                        )
                        self.queue.mark_lead_sent(lead["id"], status=f"suppressed_{rej_reason}")
                        self.queue.log_dispatch(
                            recipient=lead["email"],
                            sender=sender_addr,
                            subject="Suppressed Pre-Flight",
                            dispatch_type="cold_outreach",
                            status=f"suppressed_{rej_reason}",
                            jitter_seconds=0,
                            message_id=f"suppressed:{rej_reason}",
                        )
                        return

            subject, text_body = SpintaxGenerator.generate_outreach_spintax(lead, sender_name=sender_short)
            logger.info(f"📤 [COLD OUTREACH] Sending from {sender_addr} -> {lead['email']} ({lead.get('company')})...")
            res = self.acs_client.send_email(
                to_email=lead["email"],
                to_name=lead.get("first_name") or "Contact",
                subject=subject,
                text_body=text_body,
                sender_address=sender_addr,
            )
            jitter = self.calculate_gaussian_jitter(stage)
            self.queue.mark_lead_sent(lead["id"], status=res.get("status", "sent"))
            self.queue.log_dispatch(
                recipient=lead["email"],
                sender=sender_addr,
                subject=subject,
                dispatch_type="cold_outreach",
                status=res.get("status", "sent"),
                jitter_seconds=jitter,
                message_id=res.get("message_id", ""),
            )

        logger.info(f"⏳ Jitter delay: sleeping for {jitter:.1f}s ({jitter/60:.1f} min)...")
        if not single_step:
            time.sleep(jitter)

    def run_continuous_worker(self) -> None:
        """Run perpetual background worker executing the warm-up and dispatch schedule."""
        logger.info("⚡ Starting LeadOps Continuous Email Engine Worker...")
        while True:
            try:
                self.execute_worker_cycle(single_step=False)
            except KeyboardInterrupt:
                logger.info("🛑 Worker loop stopped by operator.")
                break
            except Exception as exc:
                logger.error(f"Worker exception: {exc}", exc_info=True)
                time.sleep(60)


def main() -> None:
    """CLI execution entrypoint."""
    load_dotenv()
    engine = EmailEngine()

    parser = argparse.ArgumentParser(description="LeadOps Email Engine & Warmup Scheduler")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # enqueue-lead
    lead_parser = subparsers.add_parser("enqueue-lead", help="Enqueue a cold outreach lead")
    lead_parser.add_argument("--email", required=True, help="Recipient email address")
    lead_parser.add_argument("--name", default="", help="Contact first name")
    lead_parser.add_argument("--company", default="", help="Target company")
    lead_parser.add_argument("--jurisdiction", default="local area", help="Filing jurisdiction")

    # enqueue-warmup
    warmup_parser = subparsers.add_parser("enqueue-warmup", help="Enqueue a peer warm-up inbox target")
    warmup_parser.add_argument("--email", required=True, help="Warm-up target email address")
    warmup_parser.add_argument("--name", default="", help="Display name")
    warmup_parser.add_argument("--password", default="", help="App Password (for auto-unspam and 2-way reply monitoring)")
    warmup_parser.add_argument("--provider", default="gmail", choices=["gmail", "outlook"], help="Provider type")

    # check-unspam
    subparsers.add_parser("check-unspam", help="Scan monitored inboxes, unspam messages and send LLM replies")

    # start
    subparsers.add_parser("start", help="Start continuous worker process")

    # test-send
    test_parser = subparsers.add_parser("test-send", help="Send diagnostic test email (e.g. to Mail-Tester)")
    test_parser.add_argument("--recipient", required=True, help="Destination email address")

    # verify-email
    ver_parser = subparsers.add_parser("verify-email", help="Verify an email using Knowlez Deliverability Suite")
    ver_parser.add_argument("--email", required=True, help="Email address to verify")
    ver_parser.add_argument("--force", action="store_true", help="Force fresh verification ignoring cache")

    # verify-lead
    vl_parser = subparsers.add_parser("verify-lead", help="Verify single lead deliverability via Knowlez & store result")
    vl_parser.add_argument("--lead-id", help="Lead ID in storage to verify")
    vl_parser.add_argument("--email", help="Direct email address to verify")
    vl_parser.add_argument("--force", action="store_true", help="Force re-verification ignoring 14-day cache")

    # batch-verify-leads
    bvl_parser = subparsers.add_parser("batch-verify-leads", help="Batch verify pending leads in storage or queue")
    bvl_parser.add_argument("--limit", type=int, default=25, help="Max leads to verify (default 25)")
    bvl_parser.add_argument("--force", action="store_true", help="Force re-verification ignoring 14-day cache")

    # validate-domain
    dom_parser = subparsers.add_parser("validate-domain", help="Validate a domain using Knowlez Deliverability Suite")
    dom_parser.add_argument("--domain", required=True, help="Domain name to validate")

    # deliverability-usage
    subparsers.add_parser("deliverability-usage", help="Check Knowlez Deliverability Suite API usage & quota")

    # status
    subparsers.add_parser("status", help="Print current engine status and ramp metrics")

    args = parser.parse_args()

    if args.command == "enqueue-lead":
        ok = engine.queue.enqueue_lead(
            email=args.email,
            first_name=args.name,
            company=args.company,
            jurisdiction=args.jurisdiction,
        )
        print("Enqueued lead successfully." if ok else "Lead already exists in queue.")

    elif args.command == "enqueue-warmup":
        is_mon = bool(args.password.strip())
        ok = engine.queue.enqueue_warmup_target(
            email=args.email,
            name=args.name,
            password=args.password,
            provider=args.provider,
            is_monitored=is_mon,
        )
        mode = "Monitored (Auto-Unspam & Reply Active)" if is_mon else "Outbound Target Only"
        print(f"Enqueued warm-up target [{mode}]." if ok else "Failed to enqueue warm-up target.")

    elif args.command == "check-unspam":
        stats = engine.inbox_watcher.run_monitoring_cycle()
        print(f"\nUnspam & Reply Scan Results: {json.dumps(stats, indent=2)}")

    elif args.command == "test-send":
        res = engine.dispatch_test_email(args.recipient)
        print(f"\nTest Dispatch Result: {json.dumps(res, indent=2)}")

    elif args.command == "verify-email":
        force_flag = getattr(args, "force", False)
        res = engine.knowlez_client.verify_email(args.email, force=force_flag)
        print(f"\nDeliverability Suite Verification:\n{json.dumps(res, indent=2)}")

    elif args.command == "verify-lead":
        from agents.storage import SqliteStorageBackend
        storage = SqliteStorageBackend()
        target_email = args.email
        lead = None
        if args.lead_id:
            lead = storage.get_lead(args.lead_id)
            if not lead:
                print(f"Error: Lead '{args.lead_id}' not found in storage.")
                return
            target_email = getattr(lead, "contact_email", "")

        if not target_email or "@" not in target_email:
            print("Error: No valid email specified (use --email or --lead-id with an existing lead).")
            return

        res = engine.knowlez_client.verify_email(target_email, force=args.force)
        score = res.get("score")
        valid = res.get("valid", False)
        provider = res.get("provider", "other")
        mx_hosts = res.get("mx_hosts", [])
        status = res.get("status") or ("DELIVERABLE" if (valid and (score is None or score >= 60)) else "UNDELIVERABLE" if not valid else "RISKY")

        if lead:
            lead.deliverability_score = score
            lead.deliverability_status = status
            lead.deliverability_checked_at = res.get("checked_at") or datetime.now(timezone.utc).isoformat()
            lead.email_provider = provider
            lead.email_mx_hosts = mx_hosts
            storage.save_lead(lead)
            print(f"\nUpdated lead {lead.lead_id} ({lead.company_name}) in storage.")

        print(f"\nDeliverability Result for '{target_email}':")
        print(f"  Valid        : {valid}")
        print(f"  Score        : {score}/100")
        print(f"  Status       : {status}")
        print(f"  Provider     : {provider.upper()}")
        print(f"  MX Hosts     : {', '.join(mx_hosts) if mx_hosts else 'None'}")
        print(f"  Cached Hit   : {res.get('cached', False)} (Zero Credits Burned)")
        if res.get("reason"):
            print(f"  Reason       : {res.get('reason')}")

    elif args.command == "batch-verify-leads":
        from agents.storage import SqliteStorageBackend
        storage = SqliteStorageBackend()
        all_leads = storage.list_leads()
        pending = []
        for l in all_leads:
            em = getattr(l, "contact_email", "")
            if not em or "@" not in em:
                continue
            if args.force or getattr(l, "deliverability_score", None) is None:
                pending.append(l)
            if len(pending) >= args.limit:
                break

        if not pending:
            print("\nNo unverified leads found in storage (all have valid cached deliverability scores).")
            return

        emails = [getattr(l, "contact_email", "") for l in pending]
        print(f"\nBatch verifying {len(emails)} leads (14-day zero-waste cache active)...")
        results = engine.knowlez_client.verify_batch(emails, force=args.force)
        res_by_email = {r.get("email", "").lower().strip(): r for r in results}

        cached_hits = 0
        valid_count = 0
        for l in pending:
            em = (getattr(l, "contact_email", "") or "").lower().strip()
            v = res_by_email.get(em, {})
            score = v.get("score")
            valid = v.get("valid", False)
            provider = v.get("provider", "other")
            status = v.get("status") or ("DELIVERABLE" if (valid and (score is None or score >= 60)) else "UNDELIVERABLE" if not valid else "RISKY")
            if v.get("cached"):
                cached_hits += 1
            if valid:
                valid_count += 1
            l.deliverability_score = score
            l.deliverability_status = status
            l.deliverability_checked_at = v.get("checked_at") or datetime.now(timezone.utc).isoformat()
            l.email_provider = provider
            l.email_mx_hosts = v.get("mx_hosts", [])
            storage.save_lead(l)

        print(f"\nBatch Verification Complete:")
        print(f"  Total Checked : {len(pending)}")
        print(f"  Cached Hits   : {cached_hits} (Zero Credits Burned)")
        print(f"  API Calls     : {len(pending) - cached_hits}")
        print(f"  Deliverable   : {valid_count}/{len(pending)}")

    elif args.command == "validate-domain":
        res = engine.knowlez_client.validate_domain(args.domain)
        print(f"\nDeliverability Suite Domain Validation:\n{json.dumps(res, indent=2)}")

    elif args.command == "deliverability-usage":
        usage = engine.knowlez_client.get_usage()
        print(f"\nDeliverability Suite Quota & Usage:\n{json.dumps(usage, indent=2)}")

    elif args.command == "status" or not args.command:
        day = engine.get_current_day()
        stage = engine.get_active_stage(day)
        cold_count, warmup_count = engine.queue.get_today_sent_counts()
        monitored = engine.queue.get_monitored_warmup_targets()
        auto_cold_allowed = os.environ.get("AUTO_OUTREACH_ENABLED", "false").lower().strip() in ("1", "true", "yes", "on", "active")
        print("\n" + "="*60)
        print("LEADOPS ACS EMAIL ENGINE & WARMUP STATUS")
        print("="*60)
        print(f"Primary Sending Domain : {DEFAULT_PRIMARY_DOMAIN}")
        print(f"Auto-Outreach Enabled  : {'ACTIVE' if auto_cold_allowed else 'OFF (Cold Outreach Locked)'}")
        print(f"Human Approval Required: {os.environ.get('LEADOPS_REQUIRE_HUMAN_APPROVAL', 'true')}")
        print(f"ACS Connection String  : {'Configured' if engine.acs_client.is_configured else 'Not Configured (Dry-Run Mode)'}")
        print(f"Deliverability Suite   : {'Active (Knowlez API Connected + 14-Day SQLite Cache)' if engine.knowlez_client.is_configured else 'Not Configured'}")
        print(f"Active Warm-up Day     : Day {day}")
        print(f"Current Ramp Tier      : {stage.description}")
        print(f"Today's Cold Volume    : {cold_count} / {stage.cold_leads} {'(BLOCKED: Auto-outreach disabled)' if not auto_cold_allowed else ''}")
        print(f"Today's Warmup Volume  : {warmup_count} / {stage.warmup_emails}")
        print(f"Jitter Window          : {stage.min_jitter_seconds}s - {stage.max_jitter_seconds}s")
        print(f"Monitored Test Inboxes : {len(monitored)} active (Auto-Unspam & Reply loop)")
        d2_ready = engine.queue.get_state("domain_2_warmup_ready") == "ready"
        print(f"Domain 2 ({DEFAULT_SECONDARY_DOMAIN})   : {'READY FOR WARMUP' if d2_ready else 'Pending Day 15'}")
        print("="*60 + "\n")

    elif args.command == "start":
        engine.run_continuous_worker()


if __name__ == "__main__":
    main()
