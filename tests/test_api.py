import pytest
import hmac
import hashlib
import os
from fastapi.testclient import TestClient

from agents.api import create_app
from agents.domain import Lead, State
from agents.portal import PortalService
from agents.storage import InMemoryStorageBackend


def generate_test_csrf_token(user_id: str) -> str:
    """Generate test CSRF token matching the HMAC implementation."""
    secret = os.environ.get("CLERK_SECRET_KEY", "dev-secret-change-in-production").encode()[:32]
    return hmac.new(secret, user_id.encode(), hashlib.sha256).hexdigest()[:32]


@pytest.fixture
def client():
    storage = InMemoryStorageBackend()
    portal = PortalService(storage=storage)
    lead = Lead("test-lead-1", "weekly")
    portal.publish_sandbox(
        lead=lead,
        company_name="Test Company",
        rows=[{"col_a": "val1", "col_b": "val2"}],
        source_url="https://portal.example.gov",
    )
    app = create_app(storage=storage, portal_svc=portal, api_token="valid-secret-token")
    return TestClient(app)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_get_portal_html(client):
    res = client.get("/p/test-company-test-lead-1")
    assert res.status_code == 200
    assert "root" in res.text
    assert "test-company-test-lead-1" in res.text


def test_sandbox_api_flow(client):
    slug = "test-company-test-lead-1"
    # Mock token "mock_user_founder_lead_admin" parses to user_id="user_founder"
    auth_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    csrf_token = generate_test_csrf_token("user_founder")
    csrf_headers = {**auth_headers, "X-CSRF-Token": csrf_token}
    
    # 1. Fetch sandbox
    res = client.get(f"/api/sandbox/{slug}")
    assert res.status_code == 200
    data = res.json()
    assert data["slug"] == slug
    assert data["state"] == "REVIEW"

    # 2. Select fields
    res = client.post(f"/api/sandbox/{slug}/fields", json={"fields": ["col_a", "col_b"]}, headers=csrf_headers)
    assert res.status_code == 200
    assert res.json()["state"] == "CONVERSATIONAL_INTAKE"

    # 3. Approve scope
    res = client.post(f"/api/sandbox/{slug}/scope", headers=csrf_headers)
    assert res.status_code == 200
    assert res.json()["state"] == "SOW_GENERATED"

    # 4. Request checkout
    res = client.post(f"/api/sandbox/{slug}/checkout", headers=csrf_headers)
    assert res.status_code == 200
    checkout_data = res.json()
    assert checkout_data["lead_id"] == "test-lead-1"
    assert checkout_data["payment_kind"] == "setup_deposit"
    assert checkout_data["amount_cents"] == 9900  # $99 setup deposit sprint


def test_scout_candidate_auth(client):
    candidate_payload = {
        "company_name": "New Corp",
        "lead_id": "lead-new-99",
        "evidence": [{"url": "https://newcorp.example.gov"}],
        "source_url": "https://newcorp.example.gov",
        "sample_rows": [{"item": "1"}],
        "research": {"niche": "Permits"},
        "tier_key": "daily",
    }

    # Unauthorized without header
    res = client.post("/api/scout/candidate", json=candidate_payload)
    assert res.status_code == 401

    # Unauthorized with wrong token
    res = client.post(
        "/api/scout/candidate",
        json=candidate_payload,
        headers={"Authorization": "Bearer bad-token"},
    )
    assert res.status_code == 403

    # Authorized
    res = client.post(
        "/api/scout/candidate",
        json=candidate_payload,
        headers={"Authorization": "Bearer valid-secret-token"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["lead_id"] == "lead-new-99"
    assert "new-corp-lead-new-99" in data["slug"]


def test_dashboard_api_routes(client):
    headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    # 1. View dashboard HTML
    res = client.get("/dashboard/test-lead-1")
    assert res.status_code == 200
    assert "root" in res.text
    assert "test-lead-1" in res.text

    # 2. Get dashboard state
    res = client.get("/api/dashboard/test-lead-1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["lead_id"] == "test-lead-1"
    assert "sync_metrics" in data
    assert "fields" in data

    # 3. Request field changes
    res = client.post(
        "/api/dashboard/test-lead-1/fields/request",
        json={"add_fields": ["col_x", "col_y"], "remove_fields": []},
        headers=headers,
    )
    assert res.status_code == 200
    assert "col_x" in res.json()["resulting_fields"]

    # 4. Update destination
    res = client.post(
        "/api/dashboard/test-lead-1/destination",
        json={"destination_type": "webhook", "webhook_url": "https://client.com/hook"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["destination"]["destination_type"] == "webhook"

    # 5. Trigger sync
    res = client.post("/api/dashboard/test-lead-1/sync", headers=headers)
    assert res.status_code == 200
    assert res.json()["records_extracted"] >= 1

    # 6. Export CSV
    res = client.get("/api/dashboard/test-lead-1/export", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")

    # 7. Claim account
    res = client.post(
        "/api/auth/claim",
        json={"user_id": "user_clerk_999", "lead_id": "test-lead-1", "email": "ops@client.com"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["account"]["public_metadata"]["lead_id"] == "test-lead-1"


def test_dashboard_security_checks(client):
    import os
    os.environ["DISABLE_TEST_FALLBACK"] = "true"
    try:
        # 1. Access to dashboard with no token should fail (401)
        res = client.get("/api/dashboard/test-lead-1")
        assert res.status_code == 401
    finally:
        os.environ.pop("DISABLE_TEST_FALLBACK", None)

    # 2. Access to dashboard with invalid user token should fail (403)
    user_headers = {"Authorization": "Bearer mock_user_client1_lead_test-lead-2"}
    res = client.get("/api/dashboard/test-lead-1", headers=user_headers)
    assert res.status_code == 403

    # 3. Access to dashboard with valid user token who owns the lead should succeed (200)
    owner_headers = {"Authorization": "Bearer mock_user_client1_lead_test-lead-1"}
    res = client.get("/api/dashboard/test-lead-1", headers=owner_headers)
    assert res.status_code == 200

    # 4. Non-admin trying to claim sandbox account of another user should fail (403)
    other_user_headers = {"Authorization": "Bearer mock_user_client2_lead_test-lead-2"}
    res = client.post(
        "/api/auth/claim",
        json={"user_id": "user_clerk_999", "lead_id": "test-lead-1", "email": "ops@client.com"},
        headers=other_user_headers,
    )
    assert res.status_code == 403

    # 5. Normal user claiming their own sandbox account should succeed (200)
    self_headers = {"Authorization": "Bearer mock_user_client1_lead_test-lead-1"}
    res = client.post(
        "/api/auth/claim",
        json={"user_id": "user_client1", "lead_id": "test-lead-1", "email": "client_client1@example.com"},
        headers=self_headers,
    )
    assert res.status_code == 200


def test_portal_email_restriction(client):
    # 1. Admin querying another user's email lead feed should bypass the email-ownership check (returning 200 or 404 depending on existence)
    admin_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    res = client.get("/api/portal/my-lead?email=client_client1@example.com", headers=admin_headers)
    assert res.status_code in {200, 404}

    # 2. Non-admin user querying another email should fail with 403 Forbidden
    user_headers = {"Authorization": "Bearer mock_user_client1_lead_test-lead-1"}
    res = client.get("/api/portal/my-lead?email=other_email@example.com", headers=user_headers)
    assert res.status_code == 403

    # 3. Non-admin user querying their own email should bypass 403 check (returning 200 or 404 depending on existence)
    res = client.get("/api/portal/my-lead?email=client_client1@example.com", headers=user_headers)
    assert res.status_code in {200, 404}


def test_get_landing_page(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "root" in res.text
    assert "OmniLeadFeeder" in res.text


def test_search_sandboxes(client):
    res = client.get("/api/sandboxes/search?q=test")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert data["results"][0]["slug"] == "test-company-test-lead-1"


def test_static_assets_serving(client):
    css_res = client.get("/static/main.css")
    assert css_res.status_code == 200
    assert "--bg:" in css_res.text
    assert ".skip-link" in css_res.text

    favicon_res = client.get("/static/favicon.svg")
    assert favicon_res.status_code == 200
    assert "<svg" in favicon_res.text


def test_pay_final_with_subscription(client):
    slug = "test-company-test-lead-1"
    # Transition sandbox lead to ESCROW_PREVIEW
    portal = client.app.state.portal_service
    sandbox = portal.get_sandbox(slug)
    sandbox.lead.deposit_paid = True
    sandbox.lead.qa_score = 100.0
    sandbox.lead.preview_rows = 25
    sandbox.lead.state = State.ESCROW_PREVIEW

    res = client.post(f"/api/sandbox/{slug}/pay-final")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["state"] == "DELIVERED"
    assert data["subscription_active"] is True
    assert data["subscription_info"] is not None
    assert data["subscription_info"]["tier"] == "Weekly Sync"


def test_sandbox_select_fields(client):
    slug = "test-company-test-lead-1"
    csrf_token = generate_test_csrf_token("user_founder")
    headers = {"Authorization": "Bearer mock_user_founder_lead_admin", "X-CSRF-Token": csrf_token}
    res = client.post(
        f"/api/sandbox/{slug}/fields",
        headers=headers,
        json={"fields": ["case_number", "decedent_name", "est_value", "filing_date"]}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["selected_fields"]) == 4
    assert "est_value" in data["selected_fields"]


def test_admin_lifecycle_email_and_triage(client):
    headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    lead_id = "test-lead-1"

    # Send lifecycle email
    res = client.post(
        f"/api/admin/leads/{lead_id}/send-lifecycle-email",
        headers=headers,
        json={
            "template_name": "deposit_confirmation",
            "custom_subject": "Test Milestone Subject",
            "custom_body": "Custom Body Text"
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["template"] == "deposit_confirmation"
    assert data["sent"] is not None

    # Swarm progress endpoint
    prog_res = client.get(f"/api/admin/leads/{lead_id}/swarm-progress", headers=headers)
    assert prog_res.status_code == 200
    prog_data = prog_res.json()
    assert prog_data["lead_id"] == lead_id

    # Daily trigger endpoint
    sync_res = client.post(f"/api/admin/leads/{lead_id}/daily-trigger", headers=headers)
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["ok"] is True
    assert sync_data["rows_delivered"] >= 1


def test_client_artifacts_and_audit_trail(client, tmp_path):
    headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    lead_id = "test-lead-audit-1"

    from agents.client_artifacts import ClientArtifactStore
    store = ClientArtifactStore(base_dir=tmp_path / "build_artifacts")
    store.save_artifact(
        lead_id=lead_id,
        stage="01_SCOUT_DISCOVERY",
        agent_name="Market Prospector",
        filename="01_scout_intelligence.json",
        content={"company": "Audit Legal Co"},
        description="Scout test artifact"
    )

    artifacts = store.list_client_artifacts(lead_id)
    assert len(artifacts) >= 1
    assert "01_scout_intelligence.json" in artifacts[0]["filename"]
    assert artifacts[0]["stage"] == "01_SCOUT_DISCOVERY"

    trail = store.get_audit_trail(lead_id)
    assert len(trail) >= 1
    assert trail[0]["agent"] == "Market Prospector"

    # Test modular codebase scaffolding
    client_dir = store.scaffold_modular_codebase(
        lead_id=lead_id,
        company_name="Audit Legal Co",
        source_url="https://example.gov/filings",
        niche="Probate & Estate Filings",
        selected_fields=["case_number", "filing_date", "estate_name", "executor"],
    )
    assert (client_dir / "ai-log-trace").exists()
    assert (client_dir / "src" / "models" / "schema.py").exists()
    assert (client_dir / "src" / "stealth" / "proxy" / "rotator.py").exists()
    assert (client_dir / "src" / "stealth" / "captchas" / "solver.py").exists()
    assert (client_dir / "src" / "stealth" / "evasion.py").exists()
    assert (client_dir / "src" / "utils" / "date_helpers.py").exists()
    assert (client_dir / "src" / "utils" / "http_client.py").exists()
    assert (client_dir / "src" / "export" / "json_exporter.py").exists()
    assert (client_dir / "src" / "export" / "csv_exporter.py").exists()
    assert (client_dir / "src" / "export" / "webhook_poster.py").exists()
    assert (client_dir / "src" / "scraper" / "portal_scraper.py").exists()
    assert (client_dir / "src" / "tests" / "test_extractor.py").exists()
    assert (client_dir / "entry.py").exists()
    assert (client_dir / "requirements.txt").exists()
    assert (client_dir / "README.md").exists()
    assert (client_dir / "post_mortem.json").exists()
    assert (client_dir / "memory.json").exists()
    assert (client_dir / "research_notes.md").exists()

    # Test admin endpoints
    res = client.get(f"/api/admin/leads/{lead_id}/artifacts", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True

    trail_res = client.get(f"/api/admin/leads/{lead_id}/audit-trail", headers=headers)
    assert trail_res.status_code == 200
    trail_data = trail_res.json()
    assert trail_data["ok"] is True


def test_invoice_endpoint(client):
    res = client.get("/api/dashboard/test-lead-1/invoice")
    assert res.status_code == 200
    assert "OMNILEADFEEDER TECHNOLOGIES" in res.text
    assert "OFFICIAL RECEIPT / INVOICE" in res.text


def test_pause_resume_endpoints(client):
    auth_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    
    # Pause feed
    pause_res = client.post("/api/dashboard/test-lead-1/pause", json={"days": 30}, headers=auth_headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["is_paused"] is True

    # Resume feed
    resume_res = client.post("/api/dashboard/test-lead-1/resume", headers=auth_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["is_paused"] is False


def test_suggest_columns_endpoint(client):
    slug = "test-company-test-lead-1"
    res = client.post(f"/api/sandbox/{slug}/suggest-columns")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert len(data["suggestions"]) > 0


def test_sandbox_live_source_verification_links(client):
    """Verify that sandboxes pull genuine public records with canonical 1-click verification URLs on every row."""
    res = client.get("/api/sandbox/austin-commercial-permits")
    assert res.status_code == 200
    data = res.json()
    assert "sample" in data
    assert len(data["sample"]) > 0
    assert "source_url" in data
    assert data["source_url"].startswith("http")

    # Verify every single row carries its verifiable source_url
    for row in data["sample"]:
        assert "source_url" in row
        assert row["source_url"].startswith("http")
        assert len(row["source_url"]) > 10


def test_chat_endpoints_flow(client):
    """Verify live consultative chat with Alex on both slug sandbox and universal /api/chat."""
    # 1. Sandbox slug chat
    slug = "test-company-test-lead-1"
    res1 = client.post(f"/api/sandbox/{slug}/chat", json={"message": "Can you add custom parcel number and owner address columns?"})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["ok"] is True
    assert "reply" in data1
    assert len(data1["reply"]) > 10

    # 2. Universal /api/chat
    res2 = client.post("/api/chat", json={"message": "How does webhook delivery to our CRM work?"})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["ok"] is True
    assert "reply" in data2
    assert len(data2["reply"]) > 10


def test_inbound_email_webhook_flow(client):
    """Verify incoming email webhook processing, intent classification, and lead state transition."""
    res = client.post("/api/email/inbound", json={
        "sender": "prospect@example.com",
        "subject": "Can we see a demo of Travis County filings?",
        "body": "Hi Alex, saw your note. Do you have live data for Travis County commercial filings?",
        "sender_name": "Dave Miller",
    })
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "result" in data
    assert data["result"]["sender"] == "prospect@example.com"
    assert data["result"]["intent"] in {"INTERESTED", "QUESTION"}


def test_chat_persistent_conversation_log_and_history(client):
    """Verify multi-turn conversational memory and persistent logs across chat interactions."""
    slug = "test-company-test-lead-1"

    # Turn 1: Client specifies tool stack
    res1 = client.post(f"/api/sandbox/{slug}/chat", json={
        "message": "We manage all our leads in HubSpot."
    })
    assert res1.status_code == 200
    assert res1.json()["ok"] is True

    # Turn 2: Client asks about delivery time
    res2 = client.post(f"/api/sandbox/{slug}/chat", json={
        "message": "Can we get records synced by 6:00 AM UTC?"
    })
    assert res2.status_code == 200
    assert res2.json()["ok"] is True

    # Turn 3: Fetch persistent conversation log
    history_res = client.get(f"/api/sandbox/{slug}/chat")
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["ok"] is True
    assert len(history_data["messages"]) >= 4  # 2 user messages + 2 Alex replies

    # Verify messages have sender and message fields
    senders = [m["sender"] for m in history_data["messages"]]
    assert "user" in senders
    assert "alex" in senders
    assert any("HubSpot" in m["message"] for m in history_data["messages"])


def test_target_url_confirmation_flow(client):
    """Verify that confirming or customizing the target docket URL updates lead and sandbox source_url."""
    slug = "test-company-test-lead-1"
    custom_target_url = "https://records.dallascounty.org/dockets/search"

    # 1. Validate custom target URL pre-flight
    val_res = client.post(
        f"/api/sandbox/{slug}/validate-source",
        json={"target_url": custom_target_url}
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["ok"] is True
    assert val_data["source_url"] == custom_target_url
    assert val_data["url_valid"] is True

    # 2. Pay deposit confirming the custom target URL
    pay_res = client.post(
        f"/api/sandbox/{slug}/pay-deposit",
        json={
            "email": "lead-counsel@dallastexas.com",
            "cardholder": "Dallas Litigation Group",
            "target_url": custom_target_url,
            "paypal_order_id": "PAYID-CONFIRM-TARGET-001",
        }
    )
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    assert pay_data["ok"] is True

    # 3. Verify that lead and sandbox now reflect the confirmed target URL
    portal = client.app.state.portal_service
    sandbox = portal.get_sandbox(slug)
    assert sandbox.source_url == custom_target_url
    assert sandbox.lead.source_url == custom_target_url


def test_chat_target_url_detection(client):
    """Verify that providing a target URL in customer chat automatically updates lead and sandbox source_url."""
    slug = "test-company-test-lead-1"
    chat_url = "https://permits.austintexas.gov/citizenaccess"

    res = client.post(
        f"/api/sandbox/{slug}/chat",
        json={"message": f"Here is the exact permit portal we need scraped: {chat_url}"}
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    portal = client.app.state.portal_service
    sandbox = portal.get_sandbox(slug)
    assert sandbox.source_url == chat_url
    assert sandbox.lead.source_url == chat_url


def test_unlock_30d_backlog_flow(client):
    """Verify $49 tripwire backlog unlock endpoint and transaction recording."""
    slug = "test-company-test-lead-1"
    res = client.post(
        f"/api/sandbox/{slug}/unlock-backlog",
        json={"email": "buyer@acme-corp.com", "paypal_order_id": "PAYID-TEST-BACKLOG-49"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["unlocked"] is True
    assert data["amount_paid"] == 49.00
    assert len(data["rows"]) >= 1

    portal = client.app.state.portal_service
    sandbox = portal.get_sandbox(slug)
    assert sandbox.lead.unlocked_30d_backlog is True


def test_setup_sprint_deposit_and_final_credit_flow(client):
    """Verify $99 setup sprint deposit and 100% credit towards month 1 ($151 balance)."""
    slug = "test-company-test-lead-1"
    
    # 1. Pay $99 setup sprint deposit
    pay_res = client.post(
        f"/api/sandbox/{slug}/pay-deposit",
        json={
            "email": "alex@acme-corp.com",
            "cardholder": "Acme Corp",
            "deposit_amount": 99.00,
            "paypal_order_id": "PAYID-SPRINT-99",
        }
    )
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    assert pay_data["ok"] is True
    assert pay_data["deposit_paid"] is True

    portal = client.app.state.portal_service
    sandbox = portal.get_sandbox(slug)
    assert sandbox.lead.deposit_paid is True
    assert sandbox.lead.deposit_amount_usd == 99.00

    # 2. Simulate dev swarm completion to ESCROW_PREVIEW
    sandbox.lead.qa_score = 98.0
    sandbox.lead.preview_rows = 25
    sandbox.lead.transition(State.ESCROW_PREVIEW, "Build certified by QA")
    client.app.state.storage_backend.save_lead(sandbox.lead)

    # 3. Check final milestone breakdown (100% deposit credit)
    final_checkout = portal.request_final_checkout(slug)
    assert final_checkout["deposit_credit_usd"] == 99.00
    # $250 plan - $99 deposit = $151 net balance due
    assert final_checkout["amount_cents"] == 15100

    # 4. Pay final balance ($151)
    auth_headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}
    csrf_token = generate_test_csrf_token("user_founder")
    final_res = client.post(
        f"/api/sandbox/{slug}/pay-final",
        headers={**auth_headers, "X-CSRF-Token": csrf_token}
    )
    assert final_res.status_code == 200
    assert sandbox.lead.state == State.DELIVERED
    assert sandbox.lead.final_paid is True
    assert sandbox.lead.subscription_active is True


def test_pipeline_initialize(client):
    payload = {
        "company_name": "Acme Legal Research",
        "contact_email": "ops@acmelegal.com",
        "target_url": "https://data.austintexas.gov",
        "jurisdiction": "Travis County, TX",
        "data_goal": "Extract all commercial building permits filed in last 30 days",
        "tier_key": "daily",
        "preferred_destination": "Google Sheets",
    }
    res = client.post("/api/pipeline/initialize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["company_name"] == "Acme Legal Research"
    assert "slug" in data
    assert "lead_id" in data
    assert data["sandbox_url"].startswith("/p/")

    # Fetch the newly provisioned sandbox
    slug = data["slug"]
    sandbox_res = client.get(f"/api/sandbox/{slug}")
    assert sandbox_res.status_code == 200
    sandbox_data = sandbox_res.json()
    assert sandbox_data["company_name"] == "Acme Legal Research"











