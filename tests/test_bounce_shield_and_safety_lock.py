"""Tests for the hard bounce shield, role-address rejection, vendor domain filtering, and cold outreach freeze."""

import os
import pytest
from unittest.mock import MagicMock

from agents.domain import Lead, State
from agents.pitcher import PitcherService, render_sub_60_word_pitch
from agents.tools.email_finder import is_directory_or_portal, discover_verified_email
from agents.email.client import EmailClient
from agents.email.config import EmailSettings
from agents.auto_outreach import AutoOutreachScheduler


def test_pitcher_rejects_role_based_unmonitored_email():
    """Verify pitcher strictly rejects salestax@ and other high-bounce role addresses."""
    pitcher = PitcherService()
    lead = Lead(lead_id="test-lead-role", tier_key="daily", company_name="Test Corp", contact_email="salestax@example.com")
    pitch = render_sub_60_word_pitch("Test Corp", "Filings", "County Portal", 5, "test-slug")

    with pytest.raises(ValueError, match="unmonitored/high-risk role address"):
        pitcher.approve_and_dispatch(
            lead=lead,
            recipient_email="salestax@example.com",
            recipient_name="Sales Tax Dept",
            pitch=pitch,
            human_approver="Operator Ben",
        )
    assert lead.state == State.ARCHIVED


def test_pitcher_rejects_automated_approval_when_human_approval_required(monkeypatch):
    """Verify pitcher strictly blocks automated/grace-period approvals when LEADOPS_REQUIRE_HUMAN_APPROVAL is true."""
    monkeypatch.setenv("LEADOPS_REQUIRE_HUMAN_APPROVAL", "true")
    monkeypatch.setenv("AUTO_OUTREACH_ENABLED", "false")

    pitcher = PitcherService()
    lead = Lead(lead_id="test-lead-auto", tier_key="daily", company_name="Test Corp", contact_email="john@example.com")
    pitch = render_sub_60_word_pitch("Test Corp", "Filings", "County Portal", 5, "test-slug")

    for auto_approver in ("Auto-Pilot Grace Period", "Autonomous AI Engine", "auto", ""):
        with pytest.raises(ValueError, match="Human approval is required"):
            pitcher.approve_and_dispatch(
                lead=lead,
                recipient_email="john@example.com",
                recipient_name="John",
                pitch=pitch,
                human_approver=auto_approver,
            )


def test_email_finder_blacklists_vendor_and_directory_domains():
    """Verify email_finder treats hunter.io, apollo.io, newark.com, etc. as non-prospect domains."""
    assert is_directory_or_portal("hunter.io") is True
    assert is_directory_or_portal("https://hunter.io/about") is True
    assert is_directory_or_portal("newark.com") is True
    assert is_directory_or_portal("apollo.io") is True
    assert is_directory_or_portal("zoominfo.com") is True
    assert is_directory_or_portal("authenticlawfirm.com") is False


def test_email_finder_domain_alignment_and_role_rejection():
    """Verify email_finder rejects non-matching vendor domain emails when target domain is specified."""
    # When lead website domain is 'lawfirmoftexas.com', an email from 'hunter.io' or 'newark.com' must never be selected
    result = discover_verified_email(
        company_name="Law Firm of Texas",
        website_url="https://lawfirmoftexas.com",
        contact_name="John Smith",
    )
    # If any email is returned, it MUST belong to lawfirmoftexas.com and NOT a disallowed role
    if result.get("email"):
        em = result["email"]
        assert em.endswith("@lawfirmoftexas.com")
        assert not em.startswith("salestax@")
        assert not em.startswith("billing@")


def test_email_client_freezes_cold_outreach_when_disabled(monkeypatch):
    """Verify EmailClient halts cold outreach when AUTO_OUTREACH_ENABLED is false, but allows warmup."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("AUTO_OUTREACH_ENABLED", "false")
    monkeypatch.setenv("OUTREACH_DISPATCH_ENABLED", "false")

    settings = EmailSettings(
        allowed_sending_domains=["olfmailer.com"],
        from_email="ben@olfmailer.com",
        outreach_dispatch_enabled=False,
    )
    client = EmailClient(settings=settings)

    # 1. Cold outreach dispatch -> Frozen, 0 emails sent
    cold_res = client.send_email(
        to_email="prospect@externaldomain.com",
        to_name="External Prospect",
        subject="Cold Inquiry",
        text_body="Pitch text.",
        is_transactional=False,
        is_warmup=False,
    )
    assert cold_res["status"] == "SIMULATED_DISPATCH_FROZEN"

    # 2. Warmup dispatch -> Allowed to proceed
    warmup_res = client.send_email(
        to_email="alex@olfmailer.com",
        to_name="Alex",
        subject="Peer Warmup Exchange",
        text_body="Warmup text.",
        is_transactional=False,
        is_warmup=True,
    )
    # Warmup is not frozen by the cold outreach lock
    assert warmup_res["status"] != "SIMULATED_DISPATCH_FROZEN"


def test_auto_outreach_queue_flush_skips_when_disabled(monkeypatch):
    """Verify flush_pending_office_hours_queue strictly skips and returns [] when disabled."""
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("AUTO_OUTREACH_ENABLED", "false")
    monkeypatch.setenv("LEADOPS_REQUIRE_HUMAN_APPROVAL", "true")

    scheduler = AutoOutreachScheduler()
    storage = MagicMock()
    lead = Lead(lead_id="test-flush-lead", tier_key="daily", state=State.PITCH_PENDING_APPROVAL, contact_email="valid@company.com")
    storage.list_leads.return_value = [lead]

    dispatched = scheduler.flush_pending_office_hours_queue(storage_backend=storage)
    assert dispatched == []
