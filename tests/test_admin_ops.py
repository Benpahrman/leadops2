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


def test_admin_draft_email_and_lifecycle_dispatch(test_setup):
    storage, admin_service, client = test_setup
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    lead = storage.get_lead("lead-admin-1")
    lead.company_name = "Apex Logistics"
    lead.contact_name = "Marcus Vance"
    lead.contact_email = "marcus@apexlogistics.com"
    lead.target_portal_name = "Harris County Freight Docket"
    lead.niche = "Commercial Freight Records"
    storage.save_lead(lead)

    # Test draft-email endpoint
    draft_res = client.post(
        "/api/admin/leads/lead-admin-1/draft-email",
        headers=admin_headers,
        json={
            "template_name": "outreach_pitch",
            "tone": "human_peer",
            "custom_instruction": "Mention Harris County specifically",
        },
    )
    assert draft_res.status_code == 200
    data = draft_res.json()
    assert data["ok"] is True
    assert "subject" in data
    assert "body" in data
    assert len(data["body"]) > 0

    # Test send-lifecycle-email endpoint with custom body
    send_res = client.post(
        "/api/admin/leads/lead-admin-1/send-lifecycle-email",
        headers=admin_headers,
        json={
            "template_name": "outreach_pitch",
            "custom_subject": data["subject"],
            "custom_body": data["body"],
        },
    )
    assert send_res.status_code == 200
    send_data = send_res.json()
    assert send_data["ok"] is True
    assert send_data["lead_id"] == "lead-admin-1"


def test_is_office_hours():
    from datetime import datetime
    import zoneinfo
    from agents.scout_runner import is_office_hours

    cst = zoneinfo.ZoneInfo("US/Central")

    # Wednesday 10:30 AM CST -> Inside office hours
    dt_work_hours = datetime(2026, 9, 9, 10, 30, tzinfo=cst)
    is_open, sec, msg = is_office_hours(now=dt_work_hours)
    assert is_open is True

    # Wednesday 6:30 PM CST -> Outside office hours
    dt_evening = datetime(2026, 9, 9, 18, 30, tzinfo=cst)
    assert is_office_hours(now=dt_evening)[0] is False

    # Wednesday 7:30 AM CST -> Outside office hours
    dt_morning = datetime(2026, 9, 9, 7, 30, tzinfo=cst)
    assert is_office_hours(now=dt_morning)[0] is False

    # Saturday 11:00 AM CST -> Weekend (outside office hours)
    dt_saturday = datetime(2026, 9, 12, 11, 0, tzinfo=cst)
    assert is_office_hours(now=dt_saturday)[0] is False


def test_batch_approve_pending_pitches(test_setup, monkeypatch):
    import agents.scout_runner
    monkeypatch.setattr(agents.scout_runner, "is_office_hours", lambda: (True, 3600, "Office hours active"))
    storage, admin_service, client = test_setup
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    # Lead 1: Valid contact email in PITCH_PENDING_APPROVAL
    lead_valid = Lead("lead-valid-p1", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead_valid.company_name = "Valid Corp"
    lead_valid.contact_email = "director@validcorp.com"
    lead_valid.contact_name = "Marcus"
    storage.save_lead(lead_valid)

    # Lead 2: Junk aggregator email in PITCH_PENDING_APPROVAL
    lead_junk = Lead("lead-junk-p2", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead_junk.company_name = "Junk Aggregator Co"
    lead_junk.contact_email = "contact@duckduckgo.com"
    lead_junk.contact_name = "Bot"
    storage.save_lead(lead_junk)

    # Lead 3: Another junk aggregator (sentry)
    lead_sentry = Lead("lead-sentry-p3", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead_sentry.company_name = "Sentry Co"
    lead_sentry.contact_email = "bca456@sentry.globalreach.com"
    storage.save_lead(lead_sentry)

    # Call batch approve API
    res = client.post("/api/admin/leads/batch-approve", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    # The valid lead was approved, junk aggregators skipped
    assert data["approved_count"] == 1
    assert data["skipped_count"] == 2
    assert "lead-valid-p1" in data["approved_lead_ids"]
    assert "lead-junk-p2" in data["skipped_lead_ids"]
    assert "lead-sentry-p3" in data["skipped_lead_ids"]

    # Verify state updates in storage
    assert storage.get_lead("lead-valid-p1").state == State.OUTREACH_SENT
    assert storage.get_lead("lead-junk-p2").state == State.PITCH_PENDING_APPROVAL


def test_batch_approve_outside_office_hours_queues_lead(test_setup, monkeypatch):
    import agents.scout_runner
    monkeypatch.setattr(agents.scout_runner, "is_office_hours", lambda: (False, 7200, "Closed for the evening"))
    storage, admin_service, client = test_setup
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    lead = Lead("lead-night-p1", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead.company_name = "Night Corp"
    lead.contact_email = "ops@nightcorp.com"
    storage.save_lead(lead)

    res = client.post("/api/admin/leads/batch-approve", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["status"] == "QUEUED_OFFICE_HOURS"
    assert data["approved_count"] == 1
    assert data["dispatched_count"] == 0
    # Remains in PITCH_PENDING_APPROVAL queued for morning dispatch
    assert storage.get_lead("lead-night-p1").state == State.PITCH_PENDING_APPROVAL


def test_auto_outreach_scheduler():
    from agents.auto_outreach import AutoOutreachScheduler
    from agents.pitcher import PitchMessage
    storage = InMemoryStorageBackend()

    scheduler = AutoOutreachScheduler(grace_period_seconds=180, min_jitter_seconds=1, max_jitter_seconds=2)
    scheduler.set_enabled(True)
    assert scheduler.is_enabled is True

    lead = Lead("lead-auto-test-1", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead.company_name = "Beta Systems"
    lead.contact_email = "alex@betasystems.com"
    pitch = PitchMessage("beta records", "Hello beta", "<p>Hello</p>", "https://test.com/p/beta", 5)

    res = scheduler.schedule_lead_for_dispatch(lead, pitch, storage)
    assert res["ok"] is True
    assert scheduler.is_pending("lead-auto-test-1") is True

    # Operator cancels via mobile
    cancelled = scheduler.cancel_dispatch("lead-auto-test-1", reason="Operator tapped Cancel")
    assert cancelled is True
    assert scheduler.is_pending("lead-auto-test-1") is False


def test_quick_action_cancel_and_send_now(test_setup):
    from agents.auth import generate_mobile_action_token
    storage, admin_service, client = test_setup

    lead = Lead("lead-quick-test", "daily", state=State.PITCH_PENDING_APPROVAL)
    lead.company_name = "Quick Test Corp"
    lead.contact_email = "director@quicktest.com"
    lead.outreach_subject = "quick records"
    lead.outreach_body = "Hi, here is your feed."
    storage.save_lead(lead)

    # 1. Test cancel_auto_outreach
    cancel_tok = generate_mobile_action_token("cancel_auto_outreach", "lead-quick-test")
    res = client.get(f"/api/admin/quick-action?action=cancel_auto_outreach&lead_id=lead-quick-test&token={cancel_tok}")
    assert res.status_code == 200
    assert "Outreach Cancelled" in res.text
    assert storage.get_lead("lead-quick-test").state == State.ARCHIVED

    # Reset for send_immediately
    lead.state = State.PITCH_PENDING_APPROVAL
    storage.save_lead(lead)
    send_tok = generate_mobile_action_token("send_immediately", "lead-quick-test")
    res2 = client.get(f"/api/admin/quick-action?action=send_immediately&lead_id=lead-quick-test&token={send_tok}")
    assert res2.status_code == 200
    assert "Outreach Pitch Approved & Dispatched" in res2.text
    assert storage.get_lead("lead-quick-test").state == State.OUTREACH_SENT


def test_archival_isolation_and_jitter_cadence(test_setup):
    """Verify that archived leads are strictly segregated from active pipeline and jitter settings are 5-20m."""
    storage, admin_service, client = test_setup
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    # Create 1 active lead and 1 archived lead
    lead_active = Lead("lead-active-1", "daily", state=State.PROSPECTING)
    lead_active.company_name = "Active Logistics"
    lead_active.contact_email = "dispatch@activelogistics.com"
    storage.save_lead(lead_active)

    lead_archived = Lead("lead-archived-1", "daily", state=State.ARCHIVED)
    lead_archived.company_name = "Archived Bounced Inc"
    lead_archived.contact_email = "bounced@invalid-domain-xyz.com"
    lead_archived.audit_log.append({
        "from": State.PROSPECTING.value,
        "to": State.ARCHIVED.value,
        "reason": "Email bounced: 550 User unknown",
        "timestamp": "2026-09-09T12:00:00Z",
    })
    storage.save_lead(lead_archived)

    # 1. Pipeline API must isolate archived leads from active columns
    res = client.get("/api/admin/pipeline", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    # Active leads list must NOT contain archived lead
    active_ids = [l["lead_id"] for l in data["leads"]]
    assert "lead-active-1" in active_ids
    assert "lead-archived-1" not in active_ids

    # Kanban columns must NOT contain archived lead
    for col_name, col_leads in data["kanban"]["columns"].items():
        col_lead_ids = [l["lead_id"] for l in col_leads]
        assert "lead-archived-1" not in col_lead_ids, f"Archived lead leaked into kanban column: {col_name}"

    # Archived vault list must contain the archived lead
    archived_ids = [l["lead_id"] for l in data["archived"]]
    assert "lead-archived-1" in archived_ids

    # 2. Inboxes API must return live jitter cadence configuration (300s - 1200s)
    res_inboxes = client.get("/api/admin/inboxes", headers=admin_headers)
    assert res_inboxes.status_code == 200
    inboxes_data = res_inboxes.json()
    assert inboxes_data["ok"] is True
    assert inboxes_data["fleet_summary"]["min_jitter_seconds"] == 300
    assert inboxes_data["fleet_summary"]["max_jitter_seconds"] == 1200
    assert "jitter_wait_seconds" in inboxes_data["inboxes"][0]
