import sqlalchemy
from sqlalchemy import text

db_url = "postgresql://omnileadadmin:OmniLead410779!Safe@psql-leadops-production-zycafu6rh2iqq.postgres.database.azure.com:5432/leadops?sslmode=require"
engine = sqlalchemy.create_engine(db_url)

with engine.begin() as conn:
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
            received_at VARCHAR(64) NOT NULL
        )
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
    tables = [r[0] for r in conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()]
    print("SUCCESS! Live Tables in Azure PostgreSQL:")
    for t in sorted(tables):
        print("  -", t)
