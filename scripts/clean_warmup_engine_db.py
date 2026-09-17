#!/usr/bin/env python3
"""Inspect and sanitize email_engine.db and leadops.db warmup targets."""

import sqlite3
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

BURNT_EMAILS = [
    "submittohim520n@hotmail.com",
    "submittohim520n@outlook.com",
    "christopher.ben.pahrman@gmail.com",
    "pahrmancb@gmail.com",
]

def sanitize_db(db_path: str):
    if not os.path.exists(db_path):
        return
    print(f"--- Sanitizing {db_path} ---")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in c.fetchall()]

    for t in ["warmup_targets", "leads_queue", "inbox_accounts", "warm_receivers", "peer_inboxes"]:
        if t in tables:
            c.execute(f"SELECT * FROM {t}")
            rows = [dict(r) for r in c.fetchall()]
            print(f"Table '{t}' has {len(rows)} row(s):")
            for r in rows:
                print("  ", r)

            for burnt in BURNT_EMAILS:
                # Find column name with email
                cols = [col[1] for col in c.execute(f"PRAGMA table_info({t})").fetchall()]
                for col in ["email", "email_address", "recipient", "sender_email"]:
                    if col in cols:
                        delete_sql = f'DELETE FROM "{t}" WHERE lower("{col}") = ?'
                        c.execute(delete_sql, (burnt.lower(),))
                        if c.rowcount > 0:
                            print(f"  🗑️ Deleted {c.rowcount} row(s) matching '{burnt}' from {t}.{col}")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    sanitize_db(str(ROOT_DIR / "email_engine.db"))
    sanitize_db(str(ROOT_DIR / "leadops.db"))
