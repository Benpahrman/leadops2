"""Tests for LeadOps Observability & Real-Time Telemetry subsystem."""

import pytest
from fastapi.testclient import TestClient

from agents.api import create_app
from agents.domain import Lead, State
from agents.observability import SystemTelemetryCollector, telemetry_collector
from agents.portal import PortalService
from agents.storage import SqliteStorageBackend
from agents.dashboard import CustomerDashboardService
from agents.admin_ops import AdminMissionControlService


@pytest.fixture
def test_env(tmp_path):
    db_path = str(tmp_path / "test_observability.db")
    storage = SqliteStorageBackend(db_path=db_path)
    portal = PortalService(storage=storage)
    dash_svc = CustomerDashboardService(storage=storage)
    admin_ops = AdminMissionControlService(storage=storage)

    # Seed test lead
    lead = Lead(
        lead_id="lead-test-obs",
        tier_key="daily",
        company_name="Test Observability Enterprise",
        contact_email="founder@testenterprise.com",
        deposit_paid=True,
        final_paid=True,
        state=State.DELIVERED,
    )
    lead.delivery_count = 3
    lead.delivery_destination = "Google Sheets (Live Connected)"
    storage.save_lead(lead)

    app = create_app(
        storage=storage,
        portal_svc=portal,
        api_token="test_token",
        dashboard_svc=dash_svc,
        admin_ops=admin_ops,
    )
    client = TestClient(app)
    return storage, client, lead


def test_telemetry_collector_events():
    collector = SystemTelemetryCollector()
    evt = collector.log_event(
        category="DELIVERY",
        title="Test Batch Delivery",
        details="Dispatched 25 records to test Google Sheet",
        status="SUCCESS",
        lead_id="lead-test-obs",
    )
    assert evt.event_id.startswith("evt-")
    assert evt.category == "DELIVERY"
    assert evt.status == "SUCCESS"

    recent = collector.get_recent_events(limit=10)
    assert any(e["title"] == "Test Batch Delivery" for e in recent)


from unittest.mock import patch, MagicMock


def test_telemetry_collector_destination_probe():
    collector = SystemTelemetryCollector()
    
    # Test Google Sheets probe
    res_sheet = collector.test_destination("google_sheets", "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
    assert res_sheet["ok"] is True
    assert res_sheet["status_code"] == 200
    assert "Google Sheets" in res_sheet["destination_type"]

    # Test Webhook probe with mocked httpx probe
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        res_webhook = collector.test_destination("webhook", "https://api.example.com/webhooks/filings")
        assert res_webhook["ok"] is True
        assert res_webhook["status_code"] == 200

    # Test Empty URL
    res_empty = collector.test_destination("google_sheets", "")
    assert res_empty["ok"] is False


def test_dashboard_feed_health_api(test_env):
    _, client, _ = test_env
    headers = {"Authorization": "Bearer mock_user_client_lead_test-obs"}

    telemetry_collector.record_delivery(
        lead_id="lead-test-obs",
        rows_delivered=25,
        destination="Google Sheets",
        status="DELIVERED",
        latency_ms=120,
    )
    
    res = client.get("/api/dashboard/lead-test-obs/health", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["feed_status"] == "HEALTHY"
    assert len(data["delivery_history"]) >= 1
    assert "DELIVERED" in data["delivery_history"][0]["status"]


def test_dashboard_destination_ping_api(test_env):
    from unittest.mock import patch
    _, client, _ = test_env
    headers = {"Authorization": "Bearer mock_user_client_lead_test-obs"}
    
    with patch("agents.google_sheets.test_google_sheet_connection", return_value={"ok": True, "spreadsheet_id": "12345", "service_account_active": True}):
        res = client.post(
            "/api/dashboard/lead-test-obs/destination/test",
            headers=headers,
            json={"destination_type": "google_sheets", "url": "https://docs.google.com/spreadsheets/d/12345"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["status_code"] == 200


def test_admin_live_telemetry_api(test_env):
    _, client, _ = test_env
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    
    res = client.get("/api/admin/telemetry/live", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["uptime_pct"] >= 0.0
    assert "proxy_pool" in data
    assert "waf_blocks_last_24h" in data["proxy_pool"]
    assert "recent_events" in data
