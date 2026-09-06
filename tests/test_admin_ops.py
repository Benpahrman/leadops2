import pytest
from fastapi.testclient import TestClient

from agents.admin_ops import AdminMissionControlService
from agents.api import create_app
from agents.auth import ClerkUser
from agents.domain import Lead, State
from agents.storage import InMemoryStorageBackend


@pytest.fixture
def test_setup():
    storage = InMemoryStorageBackend()
    lead1 = Lead("lead-admin-1", "daily", state=State.DEV_BUILDING)
    lead1.selected_fields = ["f1", "f2"]
    lead2 = Lead("lead-admin-2", "ai", state=State.DELIVERED)
    lead2.subscription_active = True
    storage.save_lead(lead1)
    storage.save_lead(lead2)

    admin_service = AdminMissionControlService(storage=storage)
    app = create_app(storage=storage, admin_ops=admin_service)
    client = TestClient(app)
    return storage, admin_service, client


def test_pipeline_kanban_and_telemetry(test_setup):
    storage, admin_service, client = test_setup
    kanban = admin_service.get_pipeline_kanban()

    assert kanban["total_leads"] >= 2
    assert len(kanban["columns"]["DEV_BUILDING"]) >= 1
    assert len(kanban["columns"]["DELIVERED"]) >= 1
    assert any(c["lead_id"] == "lead-admin-1" for c in kanban["columns"]["DEV_BUILDING"])


def test_pipeline_kanban_with_empty_contact_name(test_setup):
    storage, admin_service, client = test_setup
    # Create lead with empty string contact_name to ensure zero IndexError
    lead_empty = Lead("lead-empty-contact", "daily", state=State.PROSPECTING)
    lead_empty.contact_name = ""
    lead_empty.slug = "empty-slug"
    storage.save_lead(lead_empty)

    kanban = admin_service.get_pipeline_kanban()
    assert kanban["total_leads"] >= 3
    lead_entry = next((c for col in kanban["columns"].values() for c in col if c["lead_id"] == "lead-empty-contact"), None)
    assert lead_entry is not None
    assert "Hi there,\n\n" in lead_entry["outreach_body"]


def test_override_lead_state(test_setup):
    storage, admin_service, client = test_setup
    res = admin_service.override_lead_state("lead-admin-1", "ESCROW_PREVIEW", "Founder fast-track approval")

    assert res["ok"] is True
    assert res["new_state"] == "ESCROW_PREVIEW"
    lead = storage.get_lead("lead-admin-1")
    assert lead.state == State.ESCROW_PREVIEW
    assert "FOUNDER OVERRIDE" in lead.audit_log[-1]["reason"]


def test_dev_swarm_active_builds_and_qa_override(test_setup):
    storage, admin_service, client = test_setup
    builds = admin_service.get_active_builds()
    assert len(builds) >= 1
    assert builds[0]["lead_id"] == "lead-admin-1"
    assert "specialist_trace" in builds[0]

    qa_res = admin_service.override_qa_score("lead-admin-1", 99.0, "Manual inspection passed")
    assert qa_res["ok"] is True
    assert qa_res["qa_score"] == 99.0


def test_daily_execution_grid(test_setup):
    storage, admin_service, client = test_setup
    grid = admin_service.get_daily_execution_grid()

    assert grid["total_clients"] >= 1
    assert len(grid["drift_alerts"]) >= 1
    assert grid["jobs"][0]["status"] == "COMPLETED"


def test_governance_metrics_and_emergency_stop(test_setup):
    storage, admin_service, client = test_setup
    gov = admin_service.get_governance_overview()

    assert gov["mrr_usd"] == 850  # lead2 is AI tier ($850/mo)
    assert gov["emergency_stop"]["active"] is False

    # Activate emergency stop
    stop_res = admin_service.toggle_emergency_stop(True, "US-East proxy outage detected")
    assert stop_res["emergency_stop_active"] is True

    gov_after = admin_service.get_governance_overview()
    assert gov_after["emergency_stop"]["active"] is True
    assert gov_after["emergency_stop"]["reason"] == "US-East proxy outage detected"


def test_admin_api_endpoints_rbac(test_setup):
    _, _, client = test_setup

    # 1. Admin page requires admin role (in test env, auto-admin fallback grants access)
    res = client.get("/admin")
    assert res.status_code == 200

    # 1b. Admin page accessible with explicit admin token
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    res = client.get("/admin", headers=admin_headers)
    assert res.status_code == 200

    # 2. Pipeline API also accessible via admin auth
    res = client.get("/api/admin/pipeline", headers=admin_headers)
    assert res.status_code == 200
    assert "kanban" in res.json()

    # Unauthorized requests fail
    import os
    os.environ["DISABLE_TEST_FALLBACK"] = "true"
    try:
        res = client.get("/api/admin/pipeline")
        assert res.status_code == 401
    finally:
        os.environ.pop("DISABLE_TEST_FALLBACK", None)

    # Non-admin requests fail
    user_headers = {"Authorization": "Bearer mock_user_client1_lead_test-lead-1"}
    res = client.get("/api/admin/pipeline", headers=user_headers)
    assert res.status_code == 403

    # 3. Authorized with admin token
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    res = client.get("/api/admin/pipeline", headers=admin_headers)
    assert res.status_code == 200
    assert "kanban" in res.json()

    # 4. State override API
    res = client.post(
        "/api/admin/leads/lead-admin-1/override-transition",
        headers=admin_headers,
        json={"target_state": "SOW_GENERATED", "founder_reason": "Re-scoping requested"},
    )
    assert res.status_code == 200
    assert res.json()["new_state"] == "SOW_GENERATED"

    # 5. Governance API
    res = client.get("/api/admin/governance/metrics", headers=admin_headers)
    assert res.status_code == 200
    assert "mrr_usd" in res.json()

    # 6. Emergency Stop API
    res = client.post(
        "/api/admin/governance/emergency-stop",
        headers=admin_headers,
        json={"active": True, "reason": "Testing circuit breaker"},
    )
    assert res.status_code == 200
    assert res.json()["emergency_stop_active"] is True
