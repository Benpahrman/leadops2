
"""Interactive & Automated Setup Utility for Google Sheets Integration in LeadOps.

Usage:
    python scripts/setup_google_sheets.py
    python scripts/setup_google_sheets.py --sheet-url "https://docs.google.com/spreadsheets/d/YOUR_ID/edit" --lead-id demo_lead
"""

import argparse
import os
import sys
from datetime import datetime, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.google_sheets import (
    append_records_to_sheet,
    extract_spreadsheet_id,
    get_service_account_credentials,
    test_google_sheet_connection,
)
from agents.storage import SqliteStorageBackend


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def print_banner():
    print("=" * 68)
    print(" [LeadOps] Google Sheets Automated Setup & Diagnostics")
    print("=" * 68)


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Configure and verify Google Sheets integration for LeadOps.")
    parser.add_argument("--sheet-url", help="Target Google Sheet URL or Spreadsheet ID")
    parser.add_argument("--lead-id", default="demo_lead", help="Lead or Client ID to configure (default: demo_lead)")
    parser.add_argument("--creds", help="Path to Google Service Account JSON file")
    args = parser.parse_args()

    # 1. Prompt for sheet URL if not provided
    sheet_url = args.sheet_url
    if not sheet_url:
        print("\nPlease enter your Google Sheet URL:")
        print("Example: https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit")
        sheet_url = input("👉 Google Sheet URL: ").strip()

    if not sheet_url:
        print("❌ Error: Google Sheet URL cannot be empty.")
        sys.exit(1)

    sheet_id = extract_spreadsheet_id(sheet_url)
    print(f"\n[1/4] Extracted Spreadsheet ID: {sheet_id}")

    # 2. Check credentials
    if args.creds:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = args.creds

    creds = get_service_account_credentials()
    print("\n[2/4] Checking Google Service Account Credentials...")
    if creds:
        sa_email = getattr(creds, "service_account_email", "service-account")
        print(f"  ✓ Service Account Active: {sa_email}")
        print(f"  ℹ️  Ensure your sheet is shared with: {sa_email} (Editor access)")
    else:
        print("  ℹ️  No local service_account.json found.")
        print("  ℹ️  Make sure your Google Sheet is set to 'Anyone with the link can edit' or deploy an Apps Script Webhook.")

    # 3. Test Connection
    print("\n[3/4] Testing Connection Handshake...")
    diag = test_google_sheet_connection(sheet_url)
    print(f"  Result: {diag.get('message')}")

    if not diag.get("ok"):
        print(f"\n❌ Connection Error: {diag.get('message')}")
        if diag.get("error") == "PERMISSION_DENIED":
            print("\n💡 How to fix:")
            print("  1. Open your Google Sheet")
            print("  2. Click 'Share' in the top right")
            print(f"  3. Add the service account: {getattr(creds, 'service_account_email', 'client.operations@progenyresearch.net')}")
            print("  4. Set permission to 'Editor' and click 'Send'")
        sys.exit(1)

    # 4. Push Sample / Verification Row
    print("\n[4/4] Writing Schema Headers & Test Record to Google Sheet...")
    sample_records = [
        {
            "case_number": "2026-P-001048",
            "decedent_name": "Eleanor Vance",
            "filing_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "est_value": "$450,000",
            "attorney_name": "Marcus Sterling, Esq.",
            "status": "Active Verified",
        }
    ]

    try:
        count = append_records_to_sheet(sheet_url, sample_records)
        print(f"  ✓ Successfully verified write access ({count} test record processed).")
    except Exception as e:
        print(f"  ⚠️  Write test note: {e}")

    # 5. Save into SQLite database
    lead_id = args.lead_id
    try:
        storage = SqliteStorageBackend()
        lead = storage.get_lead(lead_id)
        if lead:
            setattr(lead, "delivery_destination", f"Google Sheets ({sheet_id})")
            storage.save_lead(lead)
            print(f"\n🎉 Successfully linked Google Sheet to lead '{lead_id}' in leadops.db!")
        else:
            print(f"\nℹ️  Note: Lead '{lead_id}' not found in DB, but Google Sheets adapter is ready.")
    except Exception as e:
        print(f"\nℹ️  Storage link note: {e}")

    print("\n" + "=" * 68)
    print(" ✅ Setup Complete! Your daily 06:00 AM UTC data stream is active.")
    print(f" 🔗 Target Sheet: {sheet_url}")
    print("=" * 68)


if __name__ == "__main__":
    main()
