"""Tests for Lead Archival on Bad Email / 45-Day Warnings and Contact Enricher Researcher Agent."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from agents.domain import Lead, State, ALLOWED_TRANSITIONS
from agents.admin_ops import AdminMissionControlService
from agents.storage import SqliteStorageBackend
from agents.contact_enricher_agent import ContactEnricherResearcherAgent
from agents.email.verifier import DeliverabilityVerifier, DeliverabilityStatus, VerificationResult


@pytest.fixture
def temp_storage(tmp_path):
    db_file = tmp_path / "test_leadops.db"
    storage = SqliteStorageBackend(db_path=str(db_file))
    return storage


def test_archived_leads_excluded_from_active_kanban(temp_storage):
    """Archived leads must be isolated from active Kanban columns and stored in archived list."""
    # 1. Create an active lead
    lead_active = Lead(
        lead_id="lead-active-firm",
        tier_key="weekly",
        state=State.REVIEW,
        company_name="Active Commercial Title",
        contact_name="Sarah Connor",
        contact_email="sarah@activetitle.com",
    )
    temp_storage.save_lead(lead_active)

    # 2. Create an archived lead (bad email or 45-day suppression)
    lead_archived = Lead(
        lead_id="lead-bad-email-firm",
        tier_key="daily",
        state=State.ARCHIVED,
        company_name="Bounced Title Corp",
        contact_name="John Doe",
        contact_email="invalid-bounce@badcorp.com",
    )
    lead_archived.log_event("QUALITY_GATE_REJECTED", "Email invalid-bounce@badcorp.com failed deliverability check: mailbox does not exist")
    temp_storage.save_lead(lead_archived)

    admin_svc = AdminMissionControlService(storage=temp_storage)
    kanban_data = admin_svc.get_pipeline_kanban()

    columns = kanban_data["columns"]
    archived_list = kanban_data.get("archived", [])

    # The active lead must be in REVIEW
    review_ids = [l["lead_id"] for l in columns.get("REVIEW", [])]
    assert "lead-active-firm" in review_ids

    # The archived lead must NOT be in PROSPECTING, REVIEW, or any active column
    for col_name, col_leads in columns.items():
        col_ids = [l["lead_id"] for l in col_leads]
        assert "lead-bad-email-firm" not in col_ids, f"Archived lead found in active column {col_name}!"

    # The archived lead must be in the isolated archived list
    archived_ids = [l["lead_id"] for l in archived_list]
    assert "lead-bad-email-firm" in archived_ids
    assert kanban_data["archived_count"] == 1


def test_allowed_transitions_permits_archived_rehabilitation():
    """State.ARCHIVED must allow transition to State.REVIEW or State.PITCH_PENDING_APPROVAL."""
    assert State.REVIEW in ALLOWED_TRANSITIONS[State.ARCHIVED]
    assert State.PITCH_PENDING_APPROVAL in ALLOWED_TRANSITIONS[State.ARCHIVED]

    lead = Lead(lead_id="test-lead", tier_key="daily", state=State.ARCHIVED)
    lead.transition(State.REVIEW, "Rehabilitated by Contact Enricher Agent")
    assert lead.state == State.REVIEW


def test_contact_enricher_agent_recovers_lead(temp_storage):
    """ContactEnricherResearcherAgent finds deliverable email, updates lead, and rehabilitates to REVIEW."""
    lead = Lead(
        lead_id="lead-rehab-test",
        tier_key="daily",
        state=State.ARCHIVED,
        company_name="Apex Real Estate Title Group",
        contact_name="Old Bounced Name",
        contact_email="bounced@apexrealestatetitle.com",
        website="https://apexrealestatetitle.com",
        niche="Title & Settlement",
    )
    lead.log_event("QUALITY_GATE_REJECTED", "Email bounced@apexrealestatetitle.com failed deliverability check: 550 User Unknown")
    temp_storage.save_lead(lead)

    mock_verifier = MagicMock(spec=DeliverabilityVerifier)
    # The old email is rejected, but new email passes
    def mock_verify(email):
        if "david" in email:
            return VerificationResult(
                email=email,
                status=DeliverabilityStatus.DELIVERABLE,
                reason="Mailbox verified via SMTP probe",
                is_valid_format=True,
                is_disposable=False,
                is_role_account=False,
                mx_records=["mail.apexrealestatetitle.com"],
                smtp_check_passed=True,
                is_domain_active=True,
            )
        return VerificationResult(
            email=email,
            status=DeliverabilityStatus.UNDELIVERABLE,
            reason="Mailbox does not exist",
            is_valid_format=True,
            is_disposable=False,
            is_role_account=False,
        )

    mock_verifier.verify.side_effect = mock_verify

    agent = ContactEnricherResearcherAgent(verifier=mock_verifier)

    # Patch research_alternative_contacts to return realistic discovered candidates
    with patch.object(
        agent,
        "research_alternative_contacts",
        return_value=[
            {"name": "David Miller", "role": "Managing Partner", "email": "david.miller@apexrealestatetitle.com", "source": "website_leadership_page"},
            {"name": "General Info", "role": "Staff", "email": "info@apexrealestatetitle.com", "source": "domain_role_fallback"},
        ],
    ):
        result = agent.enrich_and_recover_lead(lead, storage_backend=temp_storage)

    assert result["ok"] is True
    assert result["recovered"] is True
    assert result["new_email"] == "david.miller@apexrealestatetitle.com"
    assert result["new_name"] == "David Miller"
    assert result["new_state"] == "REVIEW"

    # Verify persisted in database
    reloaded = temp_storage.get_lead("lead-rehab-test")
    assert reloaded.contact_email == "david.miller@apexrealestatetitle.com"
    assert reloaded.contact_name == "David Miller"
    assert reloaded.state == State.REVIEW
    assert "contact_enricher_recovery" in reloaded.research


def test_contact_enricher_agent_unrecoverable_stays_archived(temp_storage):
    """If no candidate passes deliverability, lead stays ARCHIVED and logs attempt."""
    lead = Lead(
        lead_id="lead-hopeless-firm",
        tier_key="daily",
        state=State.ARCHIVED,
        company_name="Defunct Title Co",
        contact_name="Unknown",
        contact_email="nobody@defunct-title-fake.com",
        website="https://defunct-title-fake.com",
    )
    temp_storage.save_lead(lead)

    mock_verifier = MagicMock(spec=DeliverabilityVerifier)
    mock_verifier.verify.return_value = VerificationResult(
        email="nobody@defunct-title-fake.com",
        status=DeliverabilityStatus.UNDELIVERABLE,
        reason="NXDOMAIN: domain does not exist",
        is_valid_format=True,
        is_disposable=False,
        is_role_account=False,
    )

    agent = ContactEnricherResearcherAgent(verifier=mock_verifier)
    with patch.object(agent, "research_alternative_contacts", return_value=[]):
        result = agent.enrich_and_recover_lead(lead, storage_backend=temp_storage)

    assert result["ok"] is True
    assert result["recovered"] is False

    reloaded = temp_storage.get_lead("lead-hopeless-firm")
    assert reloaded.state == State.ARCHIVED
    assert reloaded.research.get("contact_enricher_recovery", {}).get("status") == "FAILED_NO_DELIVERABLE_FOUND"


def test_admin_api_archived_and_enrich_endpoints(temp_storage):
    """Test GET /api/admin/leads/archived and POST /api/admin/leads/{id}/enrich-contact via FastAPI TestClient."""
    from fastapi.testclient import TestClient
    from agents.api import create_app

    # Create archived lead
    lead = Lead(
        lead_id="lead-api-archived-1",
        tier_key="daily",
        state=State.ARCHIVED,
        company_name="Lone Star Escrow Partners",
        contact_name="Bob Vance",
        contact_email="bob@lonestartitle.com",
    )
    lead.log_event("QUALITY_GATE_REJECTED", "Email bob@lonestartitle.com failed deliverability check: 550 User Unknown")
    temp_storage.save_lead(lead)

    app = create_app(storage=temp_storage, api_token="test_token_123")
    client = TestClient(app)

    headers = {"Authorization": "Bearer mock_user_founder_lead_admin"}

    # 1. Test GET /api/admin/leads/archived
    resp = client.get("/api/admin/leads/archived", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["count"] >= 1
    found = [l for l in data["leads"] if l["lead_id"] == "lead-api-archived-1"]
    assert len(found) == 1
    assert "Lone Star Escrow" in found[0]["company_name"]

    # 2. Test POST /api/admin/leads/{id}/enrich-contact
    with patch(
        "agents.contact_enricher_agent.ContactEnricherResearcherAgent.enrich_and_recover_lead",
        return_value={
            "ok": True,
            "recovered": True,
            "lead_id": "lead-api-archived-1",
            "company_name": "Lone Star Escrow Partners",
            "new_email": "rachel.greene@lonestartitle.com",
            "new_name": "Rachel Greene",
            "new_role": "Managing Partner",
            "new_state": "REVIEW",
        },
    ):
        resp_enrich = client.post("/api/admin/leads/lead-api-archived-1/enrich-contact", headers=headers)
        assert resp_enrich.status_code == 200
        enrich_data = resp_enrich.json()
        assert enrich_data["ok"] is True
        assert enrich_data["recovered"] is True
        assert enrich_data["new_email"] == "rachel.greene@lonestartitle.com"

