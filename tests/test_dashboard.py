import pytest

from agents.auth import ClerkAuthService
from agents.dashboard import CustomerDashboardService
from agents.domain import Lead, State
from agents.storage import InMemoryStorageBackend


def test_clerk_auth_service_mock_token():
    auth = ClerkAuthService()
    user = auth.verify_token("mock_user_client123_lead_lead-456")
    assert user.user_id == "user_client123"
    assert user.lead_id == "lead-456"
    assert user.email == "client_client123@example.com"


def test_dashboard_state_retrieval():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-dash-1", "daily", state=State.DELIVERED)
    lead.subscription_active = True
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    state = service.get_dashboard_state("lead-dash-1")

    assert state["lead_id"] == "lead-dash-1"
    assert state["tier_name"] == "Daily Sync"
    assert state["billing"]["subscription_active"] is True
    assert state["sync_metrics"]["maintenance_shield_active"] is True
    assert len(state["fields"]["active_fields"]) <= 15


def test_dashboard_field_modification_enforces_tier_limit():
    storage = InMemoryStorageBackend()
    # Daily sync tier allows max 15 fields
    lead = Lead("lead-dash-2", "daily", state=State.DELIVERED)
    lead.select_fields(["f1", "f2", "f3"])
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    
    # Valid modification within 15 fields limit
    res = service.request_field_modification("lead-dash-2", add_fields=["f4", "f5"], remove_fields=["f1"])
    assert "f4" in res["resulting_fields"]
    assert "f1" not in res["resulting_fields"]
    assert len(res["resulting_fields"]) == 4

    # Exceeding 15 fields raises error
    too_many = [f"extra_{i}" for i in range(20)]
    with pytest.raises(ValueError, match="limit of 15"):
        service.request_field_modification("lead-dash-2", add_fields=too_many, remove_fields=[])


def test_dashboard_destination_update_and_manual_sync():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-dash-3", "weekly", state=State.WARRANTY_ACTIVE)
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    config = service.update_destination(
        lead_id="lead-dash-3",
        dest_type="webhook",
        webhook_url="https://api.client.com/webhooks/filings",
        delivery_schedule="Daily at 8:00 AM CST",
    )
    assert config.destination_type == "webhook"
    assert config.webhook_url == "https://api.client.com/webhooks/filings"

    sync_res = service.trigger_manual_sync("lead-dash-3")
    assert sync_res["ok"] is True
    assert sync_res["records_extracted"] >= 1
    assert sync_res["delivered_to"] == "webhook"


def test_dashboard_export_csv():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-dash-4", "daily", state=State.DELIVERED)
    lead.select_fields(["case_number", "decedent_name", "est_value"])
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    csv_data = service.export_latest_csv("lead-dash-4")
    assert "case_number,decedent_name,est_value" in csv_data
    assert "Eleanor Vance" in csv_data
