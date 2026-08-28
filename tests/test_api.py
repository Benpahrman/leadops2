import pytest
from fastapi.testclient import TestClient

from agents.api import create_app
from agents.domain import Lead, State
from agents.portal import PortalService
from agents.storage import InMemoryStorageBackend


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
    assert "LeadOps Live Sandbox" in res.text
    assert "test-company-test-lead-1" in res.text


def test_sandbox_api_flow(client):
    slug = "test-company-test-lead-1"
    csrf_headers = {"X-CSRF-Token": "csrf-dev_admin"}
    
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
    assert checkout_data["amount_cents"] == 12500  # $250 / 2 = $125


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
    assert "LeadOps Customer Dashboard" in res.text

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

