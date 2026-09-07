"""Tests for Unified Outreach Quality Gatekeeper and Discord/Telegram Mobile Notifications."""

import pytest
from unittest.mock import MagicMock, patch

from agents.domain import Lead, State
from agents.pitcher import PitchMessage, PitcherService
from agents.notifications import (
    NotificationSettings,
    DiscordNotifier,
    TelegramNotifier,
    NotificationManager,
)
from agents.email.quality_gate import OutreachQualityGatekeeper, QualityGateResult
from agents.email.verifier import DeliverabilityVerifier, DeliverabilityStatus, VerificationResult
from agents.email.warmup import WarmupManager
from agents.email.client import EmailClient
from agents.storage import InMemoryStorageBackend


def test_notification_settings_from_env(monkeypatch):
    monkeypatch.setenv("NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/test/token")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_bot_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")

    settings = NotificationSettings.from_env()
    assert settings.enabled is True
    assert settings.discord_webhook_url == "https://discord.com/api/webhooks/test/token"
    assert settings.telegram_bot_token == "test_bot_token"
    assert settings.telegram_chat_id == "123456789"


def test_discord_notifier_payload_construction():
    sent_requests = []

    def mock_post(url, json=None, **kwargs):
        sent_requests.append({"url": url, "json": json})
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        return mock_resp

    notifier = DiscordNotifier("https://discord.com/api/webhooks/123/abc")
    with patch("httpx.Client.post", side_effect=mock_post):
        success = notifier.send_embed(
            title="🎯 Lead Qualified: Apex Real Estate",
            description="Passed all quality gates.",
            fields=[{"name": "Contact", "value": "Sarah <sarah@apex.com>", "inline": True}],
            color=0x24483B,
        )

    assert success is True
    assert len(sent_requests) == 1
    payload = sent_requests[0]["json"]
    assert "embeds" in payload
    assert payload["embeds"][0]["title"] == "🎯 Lead Qualified: Apex Real Estate"
    assert payload["embeds"][0]["color"] == 0x24483B
    assert payload["embeds"][0]["fields"][0]["name"] == "Contact"


def test_telegram_notifier_payload_construction():
    sent_requests = []

    def mock_post(url, json=None, **kwargs):
        sent_requests.append({"url": url, "json": json})
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        return mock_resp

    notifier = TelegramNotifier("bot123456:ABC-DEF", "987654321")
    with patch("httpx.Client.post", side_effect=mock_post):
        success = notifier.send_message("<b>Lead Qualified</b>: Apex Real Estate")

    assert success is True
    assert len(sent_requests) == 1
    assert "sendMessage" in sent_requests[0]["url"]
    assert sent_requests[0]["json"]["chat_id"] == "987654321"
    assert "Apex Real Estate" in sent_requests[0]["json"]["text"]


def test_notification_manager_lead_qualified_and_dispatching():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()

    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,  # synchronous for tests
        force_dispatch_in_test=True,
    )

    lead = Lead(
        "lead-101",
        "daily",
        company_name="Apex Real Estate",
        contact_name="Sarah",
        contact_email="sarah@apex.com",
    )
    lead.niche = "Probate Court"
    lead.jurisdiction = "Cook County"

    pitch = PitchMessage(
        subject="Cook County probate list",
        body_text="Hi Sarah,\nWe ran a pull on Cook County probate records for Apex.\nMind if I send it over?\nBest, Alex",
        body_html="<p>Hi Sarah,<br>We ran a pull on Cook County probate records for Apex.<br>Mind if I send it over?<br>Best, Alex</p>",
        sandbox_url="https://omnileadfeeder.tech/p/apex",
        word_count=24,
    )

    manager.notify_lead_qualified_and_dispatching(
        lead=lead,
        pitch=pitch,
        quota_info={"sent_today": 3, "daily_quota": 25, "warmup_week": 1},
    )

    assert mock_discord.send_embed.called
    assert mock_telegram.send_message.called

    # Verify Discord embed arguments
    embed_kwargs = mock_discord.send_embed.call_args.kwargs
    assert "Apex Real Estate" in embed_kwargs["title"]
    field_names = [f["name"] for f in embed_kwargs["fields"]]
    assert "👤 Contact" in field_names
    assert "🏢 Company & Niche" in field_names
    assert "📱 Mobile 1-Tap Operator Control" in field_names

    # Verify Telegram inline keyboard with mobile approval buttons
    tg_kwargs = mock_telegram.send_message.call_args.kwargs
    assert "reply_markup" in tg_kwargs
    inline_kb = tg_kwargs["reply_markup"]["inline_keyboard"][0]
    assert any("Approve" in btn["text"] for btn in inline_kb)
    assert any("quick-action?action=approve_pitch" in btn["url"] for btn in inline_kb)


def test_notification_manager_inbound_reply_received():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()

    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
        force_dispatch_in_test=True,
    )

    manager.notify_inbound_reply_received(
        sender_email="sarah@apex.com",
        sender_name="Sarah",
        company_name="Apex Real Estate",
        subject="Re: Cook County probate list",
        reply_snippet="Yes! Please send over the sample spreadsheet to review.",
        ai_intent="INTERESTED",
        ai_sentiment="POSITIVE",
        ai_draft_reply="Hi Sarah, here is the live sandbox: https://omnileadfeeder.tech/p/apex\nBest, Alex",
    )

    assert mock_discord.send_embed.called
    assert mock_telegram.send_message.called
    tg_text = mock_telegram.send_message.call_args.args[0]
    assert "New Prospect Reply Received" in tg_text
    assert "INTERESTED" in tg_text


def test_outreach_quality_gatekeeper_all_pass():
    mock_website_agent = MagicMock()
    mock_website_agent.verify_website.return_value = {
        "is_legitimate_buyer": True,
        "confidence_score": 0.95,
        "commercial_activity_detected": "Active probate legal services",
    }

    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = VerificationResult(
        email="sarah@apex.com",
        status=DeliverabilityStatus.DELIVERABLE,
        reason="Syntax and MX valid",
        is_valid_format=True,
        is_disposable=False,
        is_role_account=False,
    )

    mock_voice_agent = MagicMock()
    mock_voice_agent.review_and_humanize.return_value = {
        "is_voice_compliant": True,
        "word_count": 38,
        "humanized_subject": "cook county probate list",
        "humanized_body_text": "Hi Sarah,\nWe extracted this week's Cook County filings for Apex.\nMind if I send the records over?\nBest, Alex",
    }

    storage = InMemoryStorageBackend()
    warmup = WarmupManager(storage_backend=storage)
    mock_notifier = MagicMock()

    gatekeeper = OutreachQualityGatekeeper(
        website_agent=mock_website_agent,
        deliverability_verifier=mock_verifier,
        voice_agent=mock_voice_agent,
        warmup_manager=warmup,
        notification_manager=mock_notifier,
    )

    lead = Lead(
        "lead-gate-1",
        "daily",
        company_name="Apex Legal",
        contact_name="Sarah",
        contact_email="sarah@apex.com",
    )
    pitch = PitchMessage(
        subject="Sample Probate Court feed",
        body_text="Hi Sarah, sample text",
        body_html="<p>Hi Sarah, sample text</p>",
        sandbox_url="https://leadops.app/p/apex",
        word_count=20,
    )

    res = gatekeeper.evaluate(lead, pitch, notify_on_pass=True)
    assert res.passed is True
    assert res.gate_failed is None
    assert mock_notifier.notify_lead_qualified_and_dispatching.called


def test_outreach_quality_gatekeeper_deliverability_failure():
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = VerificationResult(
        email="invalid@nosuchdomain12345.org",
        status=DeliverabilityStatus.UNDELIVERABLE,
        reason="DNS MX resolution failed",
        is_valid_format=True,
        is_disposable=False,
        is_role_account=False,
    )

    gatekeeper = OutreachQualityGatekeeper(deliverability_verifier=mock_verifier)

    lead = Lead(
        "lead-gate-fail-1",
        "daily",
        company_name="Bad Domain Corp",
        contact_email="invalid@nosuchdomain12345.org",
    )
    pitch = PitchMessage(
        subject="test",
        body_text="test body",
        body_html="<p>test body</p>",
        sandbox_url="url",
        word_count=5,
    )

    # Temporarily allow verifier in test mode
    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        res = gatekeeper.evaluate(lead, pitch)
        assert res.passed is False
        assert res.gate_failed == "DELIVERABILITY_BOUNCE_CHECK"
        assert "undeliverable" in res.reasons[0].lower()


def test_pitcher_service_with_quality_gate_and_notifications():
    dispatched = []

    def mock_hook(payload: dict) -> dict:
        dispatched.append(payload)
        return {"ok": True, "status": "SENT"}

    client = EmailClient(transport_hook=mock_hook)
    storage = InMemoryStorageBackend()
    warmup = WarmupManager(storage_backend=storage)
    mock_notifier = MagicMock()

    pitcher = PitcherService(
        email_client=client,
        warmup_manager=warmup,
        storage_backend=storage,
        notification_manager=mock_notifier,
    )

    lead = Lead(
        "lead-pitch-gate",
        "daily",
        company_name="Lone Star Construction",
        contact_name="David",
        contact_email="david@lonestar.com",
    )
    pitch = PitchMessage(
        subject="quick question / City of Austin permits",
        body_text="Hi David,\nExtracted Austin building permits for Lone Star.\nMind if I send over the records?\nCheers,\nAlex | LeadOps",
        body_html="<p>Hi David,<br>Extracted Austin building permits for Lone Star.<br>Mind if I send over the records?<br>Cheers,<br>Alex | LeadOps</p>",
        sandbox_url="https://omnileadfeeder.tech/p/lone-star",
        word_count=25,
    )

    # Dispatch through quality gate
    result = pitcher.approve_and_dispatch(lead, "david@lonestar.com", "David", pitch, human_approver="Auto Swarm")

    assert lead.state == State.OUTREACH_SENT
    assert len(dispatched) == 1
    assert warmup.get_sent_count_today("primary") == 1
    assert mock_notifier.notify_lead_qualified_and_dispatching.called


def test_notify_payment_received_dispatch():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    lead = Lead("lead-pay-1", "daily", company_name="Apex Roofing", contact_email="owner@apex.com")

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        manager.notify_payment_received(
            lead=lead,
            amount_usd=250.00,
            payment_type="50% Milestone Setup Deposit",
            provider="PayPal Vault",
            transaction_id="TXN-998877",
        )

    assert mock_discord.send_embed.called
    embed_call = mock_discord.send_embed.call_args[1]
    assert "Payment Captured" in embed_call["title"]
    assert embed_call["color"] == 0x10B981

    assert mock_telegram.send_message.called
    tg_msg = mock_telegram.send_message.call_args[0][0]
    assert "$250.00 USD" in tg_msg
    assert "Apex Roofing" in tg_msg


def test_notify_cancellation_requested_dispatch():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    lead = Lead("lead-cancel-1", "daily", company_name="Lone Star Recovery", contact_email="ops@lonestar.com")

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        manager.notify_cancellation_requested(
            lead=lead,
            reason="Switching internal tools",
            user_email="ops@lonestar.com",
        )

    assert mock_discord.send_embed.called
    embed_call = mock_discord.send_embed.call_args[1]
    assert "Cancellation" in embed_call["title"]
    assert embed_call["color"] == 0xEF4444

    assert mock_telegram.send_message.called
    assert "Switching internal tools" in mock_telegram.send_message.call_args[0][0]


def test_notify_complaint_or_ticket_dispatch():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    ticket = MagicMock()
    ticket.ticket_id = "TKT-1002"
    ticket.title = "Filing date column format changed in Travis County"
    ticket.description = "The clerk website updated table headers yesterday morning."
    ticket.priority = "HIGH"
    ticket.ticket_type = "selector_repair"
    ticket.lead_id = "lead-tkt-1"

    lead = Lead("lead-tkt-1", "weekly", company_name="Austin Probate Leads")

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        manager.notify_complaint_or_ticket(ticket=ticket, lead=lead)

    assert mock_discord.send_embed.called
    assert "TKT-1002" in mock_discord.send_embed.call_args[1]["fields"][0]["value"]

    assert mock_telegram.send_message.called
    assert "Travis County" in mock_telegram.send_message.call_args[0][0]


def test_notify_chat_message_dispatch():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    lead = Lead("lead-chat-1", "daily", company_name="Dallas Capital")

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        manager.notify_chat_message(
            slug="dallas-county-probate-records",
            sender_role="user",
            message_text="Can we add an extra column for estimated estate value?",
            ai_reply_text="Yes absolutely, our autonomous extractor maps that column.",
            lead=lead,
        )

    assert mock_discord.send_embed.called
    assert mock_telegram.send_message.called
    assert "estimated estate value" in mock_telegram.send_message.call_args[0][0]


def test_notify_feed_delivered_dispatch():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    lead = Lead("lead-deliv-1", "daily", company_name="Austin Permitting Partners")
    lead.target_portal_name = "Travis County Commercial Filings"

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        manager.notify_feed_delivered(
            lead=lead,
            sample_count=25,
            qa_score=100.0,
            auto_charged=True,
            destination="Google Sheets Daily Sync",
        )

    assert mock_discord.send_embed.called
    assert "Delivered" in mock_discord.send_embed.call_args[1]["title"]
    assert mock_telegram.send_message.called
    assert "100.0%" in mock_telegram.send_message.call_args[0][0]


def test_notify_morning_briefing_compilation():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
    )

    storage = InMemoryStorageBackend()
    l1 = Lead("lead-1", "daily", deposit_paid=True, final_paid=True, subscription_active=True)
    l2 = Lead("lead-2", "weekly", deposit_paid=True, final_paid=False, subscription_active=False)
    l3 = Lead("lead-3", "buyout", buyout_paid=True)
    storage.save_lead(l1)
    storage.save_lead(l2)
    storage.save_lead(l3)

    with patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
        briefing = manager.notify_morning_briefing(storage)

    assert briefing["accounting"]["deposits_count"] == 2
    assert briefing["accounting"]["final_count"] == 1
    assert briefing["accounting"]["buyouts_count"] == 1
    # l1: $250 dep + $250 fin = $500; l2: $250 dep = $250; l3: $1500 buyout = $1500 => Total = $2250
    assert briefing["accounting"]["total_cash_collected"] == 2250.0
    # MRR from l1 (daily tier = $500/mo)
    assert briefing["accounting"]["mrr"] == 500.0
    assert briefing["accounting"]["active_subscriptions"] == 1

    assert mock_discord.send_embed.called
    assert "Morning Briefing" in mock_discord.send_embed.call_args[1]["title"]
    assert mock_telegram.send_message.called
    assert "$2,250.00" in mock_telegram.send_message.call_args[0][0]


def test_notify_dev_swarm_started():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
        force_dispatch_in_test=True,
    )

    lead = Lead("lead-dev-1", "daily", company_name="Apex Construction", source_url="https://austin.gov/permits")
    manager.notify_dev_swarm_started(lead, objectives=["Map 4 fields", "Probe WAF"])

    assert mock_discord.send_embed.called
    discord_title = mock_discord.send_embed.call_args.kwargs["title"]
    assert "Dev Swarm Activated" in discord_title
    assert "Apex Construction" in discord_title

    assert mock_telegram.send_message.called
    tg_msg = mock_telegram.send_message.call_args.args[0]
    assert "AUTONOMOUS DEV SWARM ACTIVATED" in tg_msg
    assert "Apex Construction" in tg_msg


def test_notify_qa_evaluation_pass_and_fail():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
        force_dispatch_in_test=True,
    )

    lead = Lead("lead-qa-1", "daily", company_name="Apex Construction")

    # Pass case
    manager.notify_qa_evaluation(lead, qa_score=100.0, escrow_ready=True, record_count=25)
    assert mock_discord.send_embed.called
    assert "PASS" in mock_discord.send_embed.call_args.kwargs["title"]
    assert "100.0%" in mock_telegram.send_message.call_args.args[0]

    # Roadblock/fail case
    manager.notify_qa_evaluation(lead, qa_score=60.0, escrow_ready=False, issues=["DOM selector changed"])
    assert "ROADBLOCK" in mock_discord.send_embed.call_args.kwargs["title"]
    assert "DOM selector changed" in mock_telegram.send_message.call_args.args[0]


def test_notify_dev_swarm_completed_and_stopped():
    mock_discord = MagicMock()
    mock_telegram = MagicMock()
    manager = NotificationManager(
        settings=NotificationSettings(enabled=True),
        discord_notifier=mock_discord,
        telegram_notifier=mock_telegram,
        async_dispatch=False,
        force_dispatch_in_test=True,
    )

    lead = Lead("lead-fin-1", "daily", company_name="Apex Construction")

    # Completed
    manager.notify_dev_swarm_completed(lead, escrow_ready=True, qa_score=100.0, auto_charged=True)
    assert mock_discord.send_embed.called
    assert "Finished" in mock_discord.send_embed.call_args.kwargs["title"]
    assert "Auto-Charged $250" in mock_telegram.send_message.call_args.args[0]

    # Stopped
    manager.notify_dev_swarm_stopped(lead, reason="Cloudflare Turnstile captcha triggered")
    assert "Roadblock" in mock_discord.send_embed.call_args.kwargs["title"]
    assert "Cloudflare Turnstile" in mock_telegram.send_message.call_args.args[0]


def test_mobile_action_token_generation_and_verification():
    from agents.auth import generate_mobile_action_token, verify_mobile_action_token

    tok = generate_mobile_action_token("approve_pitch", "lead-100")
    assert isinstance(tok, str)
    assert len(tok) == 24

    # Valid check
    assert verify_mobile_action_token(tok, "approve_pitch", "lead-100") is True

    # Tampered action or lead
    assert verify_mobile_action_token(tok, "reject_pitch", "lead-100") is False
    assert verify_mobile_action_token(tok, "approve_pitch", "lead-999") is False
    assert verify_mobile_action_token("invalid_token", "approve_pitch", "lead-100") is False


def test_mobile_quick_action_endpoint():
    from fastapi.testclient import TestClient
    from agents.api import create_app
    from agents.auth import generate_mobile_action_token
    from agents.domain import State

    storage = InMemoryStorageBackend()
    lead = Lead("lead-mobile-test", "daily", company_name="Lone Star Escrow", contact_email="test@lonestar.com")
    lead.state = State.PITCH_PENDING_APPROVAL
    storage.save_lead(lead)

    app = create_app(storage=storage)
    client = TestClient(app)

    # 1. Invalid token should 403
    resp = client.get("/api/admin/quick-action?action=approve_pitch&lead_id=lead-mobile-test&token=badtoken")
    assert resp.status_code == 403

    # 2. Valid token approves pitch
    tok = generate_mobile_action_token("approve_pitch", "lead-mobile-test")
    resp = client.get(
        f"/api/admin/quick-action?action=approve_pitch&lead_id=lead-mobile-test&token={tok}",
        headers={"Accept": "application/json"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["action"] == "approve_pitch"

    updated_lead = storage.get_lead("lead-mobile-test")
    assert updated_lead.state == State.OUTREACH_SENT

    # 3. Pause prospector via mobile quick-action
    prosp_tok = generate_mobile_action_token("pause_prospector", "")
    resp = client.get(
        f"/api/admin/quick-action?action=pause_prospector&token={prosp_tok}",
        headers={"Accept": "application/json"}
    )
    assert resp.status_code == 200
    import os
    assert os.environ.get("PROSPECTOR_PAUSED") == "true"

    # 4. Resume prospector via mobile quick-action
    resume_tok = generate_mobile_action_token("resume_prospector", "")
    resp = client.get(
        f"/api/admin/quick-action?action=resume_prospector&token={resume_tok}",
        headers={"Accept": "application/json"}
    )
    assert resp.status_code == 200
    assert os.environ.get("PROSPECTOR_PAUSED") == "false"

