#!/usr/bin/env python3
"""Sanitize leadops_email_engine.db and seed pristine peer targets."""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "leadops_email_engine.db"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # 1. Purge all burnt email addresses from warmup_targets and dispatch_logs
    c.execute("DELETE FROM warmup_targets WHERE email LIKE '%submittohim%' OR email LIKE '%pahrman%'")
    print("Purged from warmup_targets:", c.rowcount)

    c.execute("DELETE FROM dispatch_logs WHERE recipient LIKE '%submittohim%' OR recipient LIKE '%pahrman%'")
    print("Purged from dispatch_logs:", c.rowcount)

    # 2. Insert pristine peer targets
    clean_targets = [
        ("ben@olfmailer.com", "Ben OLF", "custom", 0),
        ("alex@olfmailer.com", "Alex OLF", "custom", 0),
        ("contact@olfmailer.com", "Contact OLF", "custom", 0),
        ("omnileadfeeder.tech@gmail.com", "OmniLeadFeeder Gmail", "gmail", 0),
        ("omnileadfeeder@outlook.com", "OmniLeadFeeder Outlook", "outlook", 0),
    ]

    for email, name, provider, is_monitored in clean_targets:
        c.execute("""
            INSERT INTO warmup_targets (email, name, added_at, provider, is_monitored, status)
            VALUES (?, ?, datetime('now'), ?, ?, 'active')
            ON CONFLICT(email) DO UPDATE SET name=excluded.name, provider=excluded.provider
        """, (email, name, provider, is_monitored))

    conn.commit()

    c.execute("SELECT id, email, name, provider, status FROM warmup_targets")
    rows = c.fetchall()
    print("\n--- Current Active Warmup Targets ---")
    for r in rows:
        print(f"  ID {r[0]}: {r[1]} ({r[2]}) [{r[3]}] - {r[4]}")

    conn.close()

if __name__ == "__main__":
    main()
