"""Unit tests for Google Sheets diagnostics, Webhook signatures & latency, and Email CSV dispatch."""

import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from agents.delivery import (
    compute_webhook_signature,
    test_webhook_connection as verify_webhook_connection,
    WebhookDestination,
    EmailCsvDestination,
)
from agents.google_sheets import (
    extract_spreadsheet_id,
    get_service_account_info,
    test_google_sheet_connection as verify_google_sheet_connection,
)
from agents.domain import Lead, State
from agents.storage import InMemoryStorageBackend
from agents.dashboard import CustomerDashboardService
from agents.api import create_app


def test_spreadsheet_id_extraction():
    url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit#gid=0"
    assert extract_spreadsheet_id(url) == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    assert extract_spreadsheet_id("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms") == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


def test_service_account_info():
    info = get_service_account_info()
    assert "service_account_email" in info
    assert "apps_script_template" in info
    assert "doPost" in info["apps_script_template"]


def test_google_sheets_connection_diagnostic():
    url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
    res = verify_google_sheet_connection(url)
    assert res["ok"] is True
    assert "spreadsheet_id" in res
    assert res["spreadsheet_id"] == "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"


def test_webhook_signature_calculation():
    payload = b'{"event":"test"}'
    secret = "my_secret_token_123"
    sig = compute_webhook_signature(payload, secret)
    assert isinstance(sig, str)
    assert len(sig) == 64  # SHA256 hex string


def test_webhook_destination_with_hmac():
    posted_headers = {}
    posted_body = b""

    def mock_poster(url, headers, body):
        nonlocal posted_headers, posted_body
        posted_headers = headers
        posted_body = body
        return 200

    dest = WebhookDestination(
        webhook_url="https://example.com/webhook",
        secret_token="secret_key_abc",
        http_poster=mock_poster,
    )
    rows = [{"case_number": "2026-101", "name": "Test Company"}]
    appended = dest.append(rows)
    assert appended == 1
    assert "X-LeadOps-Signature" in posted_headers
    assert "X-LeadOps-Timestamp" in posted_headers
    assert posted_headers["X-LeadOps-Secret"] == "secret_key_abc"


def test_email_csv_destination_with_mock_client():
    mock_client = MagicMock()
    dest = EmailCsvDestination(
        recipient_email="client@example.com",
        recipient_name="Client Org",
        email_sender=mock_client,
    )
    rows = [{"docket_id": "D-101", "amount": "$5,000"}]
    appended = dest.append(rows)
    assert appended == 1
    assert mock_client.send_email.called
    call_kwargs = mock_client.send_email.call_args[1]
    assert call_kwargs["to_email"] == "client@example.com"
    assert call_kwargs["is_transactional"] is True
    assert len(call_kwargs["attachments"]) == 1
    assert "leadops_feed_" in call_kwargs["attachments"][0]["filename"]


def test_api_export_and_test_destination_endpoints():
    storage = InMemoryStorageBackend()
    lead = Lead(
        lead_id="test-export-lead-99",
        tier_key="weekly",
        company_name="Test Apex Roofing",
        state=State.DELIVERED,
        contact_email="test@apexroofing.com",
    )
    storage.save_lead(lead)
    app = create_app(storage=storage)
    client = TestClient(app)

    # 1. Test Google Sheets Info endpoint
    info_resp = client.get("/api/dashboard/integrations/google-sheets-info")
    assert info_resp.status_code == 200
    assert "service_account_email" in info_resp.json()

    # 2. Test CSV Export endpoint
    csv_resp = client.get("/api/dashboard/test-export-lead-99/export")
    assert csv_resp.status_code == 200
    assert csv_resp.headers["content-type"].startswith("text/csv")

    # 3. Test JSON Export endpoint
    json_resp = client.get("/api/dashboard/test-export-lead-99/export/json")
    assert json_resp.status_code == 200
    data = json_resp.json()
    assert data["ok"] is True
    assert "records" in data

    # 4. Test Destination Ping: Google Sheets
    test_gs = client.post(
        "/api/dashboard/test-export-lead-99/test-destination",
        json={"type": "google_sheets", "url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"},
    )
    assert test_gs.status_code == 200
    assert test_gs.json()["ok"] is True

    # 5. Test Destination Ping: Email CSV
    test_em = client.post(
        "/api/dashboard/test-export-lead-99/test-destination",
        json={"type": "email_csv", "email": "test@apexroofing.com"},
    )
    assert test_em.status_code == 200
    assert test_em.json()["ok"] is True
