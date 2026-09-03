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
    from agents.portal import Sandbox

    storage = InMemoryStorageBackend()
    lead = Lead("lead-dash-4", "daily", state=State.DELIVERED)
    lead.select_fields(["case_number", "decedent_name", "est_value"])
    sandbox = Sandbox(
        slug="lead-dash-4",
        lead=lead,
        rows=[{"case_number": "2026-P-00104", "decedent_name": "Eleanor Vance", "est_value": "$450,000"}],
        source_url="https://example.com/probate"
    )
    storage.save_sandbox(sandbox)

    service = CustomerDashboardService(storage=storage)
    csv_data = service.export_latest_csv("lead-dash-4")
    assert "case_number,decedent_name,est_value" in csv_data
    assert "Eleanor Vance" in csv_data


def test_dashboard_roi_metrics_calculation():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-roi-1", "daily", state=State.DELIVERED, company_name="Apex Realty")
    lead.subscription_active = True
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    state = service.get_dashboard_state("lead-roi-1")

    assert "roi_metrics" in state
    roi = state["roi_metrics"]
    assert roi["hours_saved_per_week"] == 20
    assert roi["hours_saved_monthly"] > 80
    assert roi["manual_cost_monthly_usd"] > 3000
    assert roi["leadops_cost_monthly_usd"] == 500
    assert roi["net_monthly_savings_usd"] > 2500
    assert roi["roi_multiplier"] >= 4.0


def test_dashboard_invoice_generation():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-inv-1", "daily", state=State.DELIVERED, company_name="Sterling Title LLC")
    lead.deposit_paid = True
    lead.final_paid = True
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    inv_data = service.get_invoice_data("lead-inv-1")
    assert inv_data["company_name"] == "Sterling Title LLC"
    assert inv_data["total_paid_usd"] == 500.00
    assert len(inv_data["items"]) == 2

    inv_html = service.generate_invoice_html("lead-inv-1")
    assert "LEADOPS TECHNOLOGIES" in inv_html
    assert "Sterling Title LLC" in inv_html
    assert "$500.00 USD" in inv_html
    assert "OFFICIAL RECEIPT / INVOICE" in inv_html


def test_dashboard_pause_resume():
    storage = InMemoryStorageBackend()
    lead = Lead("lead-pause-1", "daily", state=State.DELIVERED)
    lead.subscription_active = True
    storage.save_lead(lead)

    service = CustomerDashboardService(storage=storage)
    pause_res = service.pause_subscription("lead-pause-1", days=30)
    assert pause_res["ok"] is True
    assert pause_res["is_paused"] is True
    assert pause_res["paused_until"] != ""

    saved_lead = storage.get_lead("lead-pause-1")
    assert saved_lead.is_paused is True

    # Check dashboard state reflects pause
    state = service.get_dashboard_state("lead-pause-1")
    assert state["is_paused"] is True
    assert state["billing"]["subscription_active"] is False
    assert "PAUSED" in state["sync_metrics"]["health_status"]

    # Resume feed
    resume_res = service.resume_subscription("lead-pause-1")
    assert resume_res["ok"] is True
    assert resume_res["is_paused"] is False

    resumed_lead = storage.get_lead("lead-pause-1")
    assert resumed_lead.is_paused is False
    assert resumed_lead.paused_until == ""

