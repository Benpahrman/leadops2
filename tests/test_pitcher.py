import json
import pytest

from agents.domain import Lead, State
from agents.pitcher import (
    PitcherService,
    SendPulseClient,
    SendPulseSettings,
    render_sub_60_word_pitch,
)


def test_render_sub_60_word_pitch():
    pitch = render_sub_60_word_pitch(
        company_name="Apex Real Estate",
        niche="Probate Court",
        portal_name="Cook County Clerk",
        sample_count=20,
        slug="apex-real-estate-lead-1",
        base_url="https://leadops.app",
        contact_name="Sarah",
    )
    assert pitch.word_count < 60
    assert "https://leadops.app/p/apex-real-estate-lead-1" in pitch.sandbox_url
    assert "Cook County Clerk" in pitch.body_text
    assert pitch.subject
    assert len(pitch.subject.split()) <= 6
    assert "sample" not in pitch.subject.lower()
    assert "data feed for" not in pitch.subject.lower()


def test_natural_subject_generation():
    from agents.pitcher import generate_natural_subject
    subj = generate_natural_subject(
        company_name="Austin Architects LLC",
        niche="Commercial Construction & Permits",
        portal_name="City of Austin Building Permits Portal",
        contact_name="Marcus Vance",
    )
    assert subj
    # Non-AI subjects: 2-4 words, casual lowercase peer subject
    assert len(subj.split()) <= 5
    assert "sample" not in subj.lower()
    assert "data feed" not in subj.lower()
    assert "automating" not in subj.lower()
    assert not subj.endswith(" 4")



def test_pitcher_dispatch_lifecycle_and_mock_client():
    sent_payloads = []

    def mock_requester(url: str, headers: dict[str, str], body_bytes: bytes | None, method: str):
        if url.endswith("/oauth/access_token"):
            return 200, {"access_token": "mock_token_abc", "expires_in": 3600}
        if url.endswith("/smtp/emails"):
            payload = json.loads(body_bytes.decode()) if body_bytes else {}
            sent_payloads.append(payload)
            return 200, {"result": True, "id": "msg_9876"}
        return 404, {"error": "not found"}

    settings = SendPulseSettings(
        client_id="test_id",
        client_secret="test_secret",
        from_email="alex@leadops.app",
        from_name="Alex | LeadOps",
    )
    client = SendPulseClient(settings=settings, http_requester=mock_requester)
    from agents.email.verifier import DeliverabilityVerifier
    verifier = DeliverabilityVerifier(probe_smtp=False)
    verifier.resolve_mx_records = lambda d: ["mail.acme.com"]
    pitcher = PitcherService(sendpulse_client=client, deliverability_verifier=verifier)

    lead = Lead("lead-outreach-1", "weekly")
    pitch = render_sub_60_word_pitch(
        company_name="Acme Legal",
        niche="Eviction Filings",
        portal_name="Municipal Court",
        sample_count=15,
        slug="acme-legal-lead-outreach-1",
    )

    # Dispatch requires human approver in strict approval mode
    import os
    os.environ["LEADOPS_REQUIRE_HUMAN_APPROVAL"] = "true"
    try:
        with pytest.raises(ValueError, match="Human approval is required"):
            pitcher.approve_and_dispatch(lead, "sarah@acme.com", "Sarah", pitch, human_approver="")
    finally:
        os.environ.pop("LEADOPS_REQUIRE_HUMAN_APPROVAL", None)

    # Successful dispatch moves lead state: PROSPECTING -> REVIEW -> PITCH_PENDING_APPROVAL -> OUTREACH_SENT
    log = pitcher.approve_and_dispatch(lead, "sarah@acme.com", "Sarah", pitch, human_approver="Operator Dan")
    assert lead.state == State.OUTREACH_SENT
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["email"]["to"][0]["email"] == "sarah@acme.com"
    assert log["approver"] == "Operator Dan"


def test_pitcher_opt_out_suppression():
    pitcher = PitcherService(opt_out_emails={"optout@example.com"})
    lead = Lead("lead-outreach-2", "daily")
    pitch = render_sub_60_word_pitch("Beta Corp", "Permits", "City Portal", 10, "beta-corp-2")

    with pytest.raises(ValueError, match="opt-out suppression list"):
        pitcher.approve_and_dispatch(lead, "optout@example.com", "Manager", pitch, human_approver="Dan")

    assert lead.state == State.ARCHIVED


def test_escrow_ready_email_rendering_and_dispatch():
    from agents.pitcher import render_escrow_ready_email, send_escrow_ready_notification

    pitch = render_escrow_ready_email(
        company_name="Lone Star Asset Recovery",
        lead_id="lead-test-escrow",
        slug="lone-star-lead-test-escrow",
        qa_score=98.5,
        sample_count=25,
        tier_name="Daily Sync",
        final_balance_usd=250.0,
    )
    assert "98.5%" in pitch.subject
    assert "Lone Star Asset Recovery" in pitch.subject
    assert "25 live records" in pitch.body_text
    assert "$250.00" in pitch.body_text
    assert "/p/lone-star-lead-test-escrow" in pitch.sandbox_url

    sent_payloads = []

    def mock_requester(url: str, headers: dict[str, str], body_bytes: bytes | None, method: str):
        if url.endswith("/oauth/access_token"):
            return 200, {"access_token": "mock_token_abc", "expires_in": 3600}
        if url.endswith("/smtp/emails"):
            payload = json.loads(body_bytes.decode()) if body_bytes else {}
            sent_payloads.append(payload)
            return 200, {"result": True, "id": "msg_escrow_123"}
        return 404, {"error": "not found"}

    settings = SendPulseSettings(client_id="id", client_secret="secret", from_email="a@b.com")
    mock_client = SendPulseClient(settings=settings, http_requester=mock_requester)

    lead = Lead("lead-test-escrow", "daily", company_name="Lone Star Asset Recovery", contact_email="ops@lonestar.com")
    lead.qa_score = 98.5
    lead.preview_rows = 25
    result = send_escrow_ready_notification(lead, client=mock_client)
    assert result["status"] == "sent"
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["email"]["to"][0]["email"] == "ops@lonestar.com"
    assert "98.5%" in sent_payloads[0]["email"]["subject"]


def test_outreach_office_hours_enforcement_and_emergency_override(monkeypatch):
    import agents.scout_runner
    settings = SendPulseSettings(client_id="id", client_secret="secret", from_email="a@b.com")
    def mock_requester(url, headers, body_bytes, method):
        return 200, {"result": True, "id": "msg_test"}
    mock_client = SendPulseClient(settings=settings, http_requester=mock_requester)
    pitcher = PitcherService(sendpulse_client=mock_client)
    
    lead = Lead("lead-office-hours-test", "daily", company_name="Apex Testing", contact_email="apex@example.com")
    pitch = render_sub_60_word_pitch("Apex Testing", "Permits", "City Portal", 10, "apex-slug")

    # 1. Simulate outside office hours
    monkeypatch.setattr(agents.scout_runner, "is_office_hours", lambda: (False, 3600, "Outside office hours (closed)"))
    
    # Normal dispatch fails when enforce_office_hours is active
    with pytest.raises(ValueError, match="Outbound cold outreach sending is restricted to office hours"):
        pitcher.approve_and_dispatch(lead, "apex@example.com", "Apex", pitch, enforce_office_hours=True)

    # 2. Emergency force bypass allows dispatch even outside office hours
    res = pitcher.approve_and_dispatch(lead, "apex@example.com", "Apex", pitch, enforce_office_hours=True, force_out_of_hours=True)
    assert res["approver"] == "Autonomous AI Engine"
    assert lead.state == State.OUTREACH_SENT

    # 3. During office hours, dispatch succeeds normally without force
    lead2 = Lead("lead-in-hours-test", "daily", company_name="Beta Testing", contact_email="beta@example.com")
    monkeypatch.setattr(agents.scout_runner, "is_office_hours", lambda: (True, 7200, "Office hours active"))
    res2 = pitcher.approve_and_dispatch(lead2, "beta@example.com", "Beta", pitch, enforce_office_hours=True)
    assert res2["approver"] == "Autonomous AI Engine"
    assert lead2.state == State.OUTREACH_SENT


