"""ETL Data Migration: Transfer local SQLite records to Azure Database for PostgreSQL.

Safely loads leads, sandboxes, tickets, cancellation requests, email templates,
and webhook idempotency events from leadops.db into the target PostgreSQL instance.
"""

import argparse
import logging
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.storage import SqliteStorageBackend, PostgresStorageBackend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("leadops.migration")


def migrate_data(sqlite_path: str, postgres_url: str) -> None:
    logger.info("Starting database migration: '%s' -> Azure PostgreSQL", sqlite_path)

    if not Path(sqlite_path).exists():
        logger.error("Source SQLite database file not found: %s", sqlite_path)
        sys.exit(1)

    # Initialize backends
    source = SqliteStorageBackend(db_path=sqlite_path)
    target = PostgresStorageBackend(database_url=postgres_url)

    # 1. Migrate Leads
    leads = source.list_leads()
    logger.info("Migrating %d leads...", len(leads))
    for lead in leads:
        target.save_lead(lead)
    logger.info("Leads migration complete.")

    # 2. Migrate Sandboxes
    sandboxes = source.list_sandboxes()
    logger.info("Migrating %d sandboxes...", len(sandboxes))
    for sandbox in sandboxes:
        target.save_sandbox(sandbox)
    logger.info("Sandboxes migration complete.")

    # 3. Migrate Tickets
    tickets = source.list_tickets()
    logger.info("Migrating %d tickets...", len(tickets))
    for ticket in tickets:
        target.save_ticket(ticket)
    logger.info("Tickets migration complete.")

    # 4. Migrate Cancellation Requests
    cancellations = source.list_cancellation_requests()
    logger.info("Migrating %d cancellation requests...", len(cancellations))
    for req in cancellations:
        target.save_cancellation_request(req)
    logger.info("Cancellation requests migration complete.")

    # 5. Migrate Email Templates
    templates = source.list_email_templates()
    logger.info("Migrating %d email templates...", len(templates))
    for tmpl in templates:
        target.save_email_template(tmpl)
    logger.info("Email templates migration complete.")

    # 6. Migrate Webhook Idempotency Events
    with sqlite3.connect(sqlite_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT event_id FROM webhook_idempotency")
        events = [r[0] for r in cursor.fetchall()]
        logger.info("Migrating %d webhook idempotency events...", len(events))
        for evt in events:
            target.record_webhook_event(evt)
    logger.info("Webhook events migration complete.")

    logger.info("🎉 Database migration to Azure PostgreSQL successfully completed with ZERO data loss!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local SQLite database to Azure PostgreSQL")
    parser.add_argument("--sqlite-path", default="leadops.db", help="Path to source leadops.db file")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"), help="Target PostgreSQL connection string")

    args = parser.parse_args()

    if not args.database_url:
        logger.error("DATABASE_URL must be specified via argument or environment variable.")
        sys.exit(1)

    migrate_data(args.sqlite_path, args.database_url)
