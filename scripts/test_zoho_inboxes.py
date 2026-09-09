#!/usr/bin/env python3
"""Diagnostic verification script for LeadOps Zoho Mail and multi-inbox connections.

Tests live SMTP SSL (port 465) and IMAP SSL (port 993) authentication
against Zoho Workplace and Gmail without dispatching any emails.

Usage:
    python scripts/test_zoho_inboxes.py
    python scripts/test_zoho_inboxes.py --email user@company.com --password "zoho-app-pwd" --provider zoho
"""

import argparse
import sys
import os

# Add repo root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from agents.email.config import EmailSettings, InboxAccountConfig
from agents.email.client import EmailClient
from agents.email.warmup import WarmupManager
from agents.storage import create_storage_backend


def test_inbox_table():
    parser = argparse.ArgumentParser(description="Test Zoho Mail & Multi-Inbox Connections")
    parser.add_argument("--email", help="Specific email address to test")
    parser.add_argument("--password", help="Specific app password to test")
    parser.add_argument("--provider", default="zoho", choices=["zoho", "gmail", "smtp_generic"], help="Email provider preset")
    parser.add_argument("--smtp-host", default="", help="Custom SMTP host")
    parser.add_argument("--imap-host", default="", help="Custom IMAP host")
    args = parser.parse_args()

    settings = EmailSettings.from_environment()
    client = EmailClient(settings=settings)

    inboxes_to_test: list[InboxAccountConfig] = []

    if args.email and args.password:
        # User provided manual target
        custom_inbox = InboxAccountConfig(
            id="manual_test",
            email_address=args.email.strip(),
            password=args.password.strip(),
            provider=args.provider,
            smtp_host=args.smtp_host,
            imap_host=args.imap_host,
        )
        inboxes_to_test.append(custom_inbox)
    else:
        # Load from environment and persistent storage
        storage = create_storage_backend()
        warmup = WarmupManager(settings=settings, storage_backend=storage)
        inboxes_to_test = warmup.get_all_configured_accounts()

    print("\n" + "=" * 80)
    print(" 📬 LEADOPS MULTI-INBOX CONNECTIVITY TESTER (ZOHO / GMAIL / SMTP)")
    print("=" * 80)

    if not inboxes_to_test:
        print("\n⚠️  No inboxes configured!")
        print("   Set up inboxes via:")
        print("   1. Environment variables in .env (e.g. ZOHO_INBOX_1_EMAIL and ZOHO_INBOX_1_APP_PASSWORD)")
        print("   2. Admin Mission Control UI (/admin -> Email Inboxes)")
        print("   3. Or pass directly: python scripts/test_zoho_inboxes.py --email <email> --password <pwd>\n")
        return

    print(f"\nFound {len(inboxes_to_test)} configured inbox(es) to test.\n")

    success_count = 0
    fail_count = 0

    for idx, inbox in enumerate(inboxes_to_test, 1):
        print(f"[{idx}/{len(inboxes_to_test)}] Testing '{inbox.id}' ({inbox.email_address}) [Provider: {inbox.provider}]...")
        if not inbox.password:
            print("   ⚠️  SKIPPED: No password configured for this inbox.")
            continue

        res = client.test_inbox_connection(inbox)
        smtp_ok = res.get("smtp_ok", False)
        imap_ok = res.get("imap_ok", False)
        latency = res.get("latency_ms", 0)

        smtp_icon = "✅" if smtp_ok else "❌"
        imap_icon = "✅" if imap_ok else "❌"

        print(f"   SMTP SSL (465): {smtp_icon} {res.get('smtp_message')}")
        print(f"   IMAP SSL (993): {imap_icon} {res.get('imap_message')}")
        print(f"   Latency:        ⚡ {latency}ms")

        if smtp_ok and imap_ok:
            print("   🏆 Status: READY FOR OUTREACH & INBOUND LISTENING")
            success_count += 1
        elif smtp_ok:
            print("   🏆 Status: READY FOR OUTREACH (SMTP OK | Outbound dispatch enabled)")
            success_count += 1
        else:
            fail_count += 1
            if "authentication failed" in str(res).lower() or "credentials" in str(res).lower():
                print("   💡 Tip: Zoho Workplace accounts require an App-Specific Password.")
                print("           Generate one at: https://accounts.zoho.com -> Security -> App Passwords")

        print("-" * 80)

    print(f"\nSummary: {success_count} Passed | {fail_count} Failed | Total: {len(inboxes_to_test)}\n")


if __name__ == "__main__":
    test_inbox_table()
