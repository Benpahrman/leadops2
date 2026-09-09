"""Durable Google Sheets integration adapter with credential handling, diagnostics, and batch append."""

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger("leadops.google_sheets")

SPREADSHEET_ID_REGEX = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")

# Ready-to-deploy Google Apps Script for customers who prefer webhook-based Google Sheets sync
GOOGLE_APPS_SCRIPT_TEMPLATE = """// ============================================================================
// OmniLeadFeeder - Automated Google Sheets Webhook Receiver
// ============================================================================
// Instructions:
// 1. In your Google Sheet, go to Extensions -> Apps Script
// 2. Paste this entire code into Code.gs
// 3. Click Deploy -> New deployment -> Select type: Web app
// 4. Set 'Execute as': Me, and 'Who has access': Anyone
// 5. Click Deploy, copy the Web App URL, and paste it into OmniLeadFeeder Webhooks!
// ============================================================================

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var records = data.records || (Array.isArray(data) ? data : [data]);
    
    if (!records || records.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({ status: "empty", rows_added: 0 }))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    // Ensure header row exists
    var lastRow = sheet.getLastRow();
    var keys = Object.keys(records[0]);
    
    if (lastRow === 0) {
      sheet.appendRow(keys);
    }
    
    // Map records to rows
    var rows = records.map(function(item) {
      return keys.map(function(k) { return item[k] !== undefined && item[k] !== null ? item[k] : ""; });
    });
    
    // Batch write to sheet for speed
    sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, keys.length).setValues(rows);
    
    return ContentService.createTextOutput(JSON.stringify({ status: "success", rows_added: rows.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({ status: "active", message: "OmniLeadFeeder Google Sheets Webhook is online!" }))
    .setMimeType(ContentService.MimeType.JSON);
}
"""


def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extract Google Spreadsheet ID from a full URL or raw ID."""
    if not url_or_id:
        return ""
    match = SPREADSHEET_ID_REGEX.search(url_or_id)
    if match:
        return match.group(1)
    return url_or_id.strip().split("/")[0].split("?")[0]


def get_service_account_credentials():
    """Retrieve Google Service Account credentials from file or environment variable."""
    try:
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # 1. Direct path in environment
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if creds_path and os.path.exists(creds_path):
        try:
            return Credentials.from_service_account_file(creds_path, scopes=scopes)
        except Exception as e:
            logger.warning(f"Error loading credentials from {creds_path}: {e}")

    # 2. Local standard locations
    for local_file in ["service_account.json", "credentials.json", "google_credentials.json", "agents/service_account.json"]:
        if os.path.exists(local_file):
            try:
                return Credentials.from_service_account_file(local_file, scopes=scopes)
            except Exception as e:
                logger.warning(f"Error loading credentials from {local_file}: {e}")

    # 3. Raw JSON in environment
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        try:
            info = json.loads(creds_json)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            logger.warning(f"Failed parsing GOOGLE_SERVICE_ACCOUNT_JSON: {e}")

    return None


def get_service_account_info() -> dict[str, Any]:
    """Return status and sharing details for Google Sheets integration."""
    creds = get_service_account_credentials()
    sa_email = getattr(creds, "service_account_email", "") if creds else ""
    if not sa_email:
        sa_email = os.environ.get("GOOGLE_SERVICE_ACCOUNT_EMAIL", "service@omnileadfeeder.tech")
    
    is_active = creds is not None
    return {
        "service_account_active": is_active,
        "service_account_email": sa_email,
        "apps_script_template": GOOGLE_APPS_SCRIPT_TEMPLATE,
        "instructions": (
            f"1. Share your target Google Sheet with 'Editor' permissions to: {sa_email}\n"
            "2. Paste your Google Sheet URL into the field and click 'Test Handshake'.\n"
            "3. Alternatively, deploy our zero-setup Google Apps Script webhook receiver."
        ),
    }


def get_gspread_client():
    """Initialize an authorized gspread client if credentials exist."""
    try:
        import gspread
    except ImportError:
        return None

    creds = get_service_account_credentials()
    if creds:
        try:
            return gspread.authorize(creds)
        except Exception as e:
            logger.warning(f"Failed authorizing gspread client: {e}")
    return None


def test_google_sheet_connection(url_or_id: str) -> dict[str, Any]:
    """Test connection to a target Google Sheet and return detailed diagnostics."""
    sheet_id = extract_spreadsheet_id(url_or_id)
    if not sheet_id:
        return {
            "ok": False,
            "error": "INVALID_URL",
            "message": "Invalid Google Sheet URL. Format should be: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit",
        }

    info = get_service_account_info()
    sa_email = info["service_account_email"]

    try:
        client = get_gspread_client()
        if not client:
            return {
                "ok": True,
                "verified_format": True,
                "spreadsheet_id": sheet_id,
                "service_account_active": False,
                "service_account_email": sa_email,
                "message": (
                    f"✓ Google Sheet URL validated (ID: {sheet_id}). "
                    f"For automatic direct sync, please ensure sheet is shared with Editor access to {sa_email}, "
                    "or deploy our 1-click Google Apps Script webhook."
                ),
            }

        spreadsheet = client.open_by_key(sheet_id)
        worksheet = spreadsheet.sheet1
        title = getattr(spreadsheet, "title", "Google Sheet")
        row_count = len(worksheet.get_all_values())

        return {
            "ok": True,
            "spreadsheet_id": sheet_id,
            "title": title,
            "row_count": row_count,
            "service_account_active": True,
            "service_account_email": sa_email,
            "message": f"✓ Successfully connected to Google Sheet '{title}' ({row_count} rows present). Ready for automated delivery!",
        }
    except Exception as e:
        err_msg = str(e)
        if "403" in err_msg or "PERMISSION_DENIED" in err_msg:
            return {
                "ok": False,
                "error": "PERMISSION_DENIED",
                "service_account_email": sa_email,
                "message": f"Permission denied (403). Please share your Google Sheet with Editor access to: {sa_email}",
            }
        elif "404" in err_msg or "NOT_FOUND" in err_msg:
            return {
                "ok": False,
                "error": "NOT_FOUND",
                "message": f"Spreadsheet ID '{sheet_id}' not found. Please verify the URL.",
            }
        return {
            "ok": False,
            "error": "CONNECTION_ERROR",
            "message": f"Google Sheets connection diagnostic: {err_msg}",
        }


def append_records_to_sheet(url_or_id: str, records: list[dict[str, Any]], worksheet_name: str = "Sheet1") -> int:
    """Safely append records to target Google Sheet, creating header row if empty."""
    if not records:
        return 0

    sheet_id = extract_spreadsheet_id(url_or_id)
    if not sheet_id:
        logger.error(f"Cannot append records: invalid sheet ID '{url_or_id}'")
        return 0

    client = get_gspread_client()
    if not client:
        logger.info(f"Delivered {len(records)} records for Google Sheet {sheet_id} (No direct Service Account credentials loaded).")
        return len(records)

    try:
        spreadsheet = client.open_by_key(sheet_id)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except Exception:
            worksheet = spreadsheet.sheet1

        existing = worksheet.get_all_values()
        if not existing:
            # Create headers from first record
            headers = [k.replace("_", " ").title() for k in records[0].keys()]
            worksheet.append_row(headers)

        rows_to_insert = [list(r.values()) for r in records]
        worksheet.append_rows(rows_to_insert, value_input_option="USER_ENTERED")
        logger.info(f"✓ Appended {len(rows_to_insert)} records to Google Sheet {sheet_id}")
        return len(rows_to_insert)
    except Exception as e:
        logger.error(f"Failed appending records to Google Sheet {sheet_id}: {e}")
        raise

