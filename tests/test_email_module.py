"""Comprehensive tests for LeadOps Native Email Module, Warmup Throttler, Deliverability Verifier, and AI Agents."""

from datetime import datetime, timezone, timedelta
import pytest

from agents.domain import Lead, State
from agents.email.config import EmailSettings
from agents.email.client import EmailClient
from agents.email.verifier import (
    DeliverabilityVerifier,
    DeliverabilityStatus,
    VerificationResult,
)
from agents.email.warmup import WarmupManager, WarmupTier
from agents.email.inbound_watcher import InboundEmailWatcher
from agents.email.ai_review import (
    ProspectWebsiteVerificationAgent,
    EmailVoiceHumanizerAgent,
    InboundReplyAgent,
)
from agents.pitcher import (
    PitcherService,
    render_sub_60_word_pitch,
    PitchMessage,
)
from agents.storage import InMemoryStorageBackend


def test_email_settings_from_env(monkeypatch):
    monkeypatch.setenv("GMAIL_USER", "testops@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd-efgh-ijkl-mnop")
    monkeypatch.setenv("COLD_EMAIL_LINK_MODE", "permission_first")
    monkeypatch.setenv("WARMUP_WEEK1_LIMIT", "20")

    settings = EmailSettings.from_environment()
    assert settings.user == "testops@gmail.com"
    assert settings.app_password == "abcd-efgh-ijkl-mnop"
    assert settings.cold_email_link_mode == "permission_first"
    assert settings.warmup_week1_limit == 20
    assert settings.smtp_host == "smtp.gmail.com"
    assert settings.imap_host == "imap.gmail.com"


def test_deliverability_verifier_syntax_and_disposable():
    verifier = DeliverabilityVerifier(probe_smtp=False)

    # 1. Invalid syntax
    res1 = verifier.verify("not-an-email")
    assert res1.status == DeliverabilityStatus.UNDELIVERABLE
    assert not res1.is_valid_format

    # 2. Disposable domain rejection
    res2 = verifier.verify("prospect@mailinator.com")
    assert res2.status == DeliverabilityStatus.UNDELIVERABLE
    assert res2.is_disposable

    # 3. Role account warning
    res3 = verifier.verify("noreply@google.com")
    assert res3.status == DeliverabilityStatus.RISKY
    assert res3.is_role_account

    # 4. Valid commercial domain with MX records
    res4 = verifier.verify("engineering@github.com")
    assert res4.status == DeliverabilityStatus.DELIVERABLE
    assert res4.is_safe_to_send
    assert len(res4.mx_records) > 0


def test_warmup_tier_progression():
    settings = EmailSettings(
        warmup_week1_limit=25,
        warmup_week2_limit=50,
        warmup_week3_limit=75,
        warmup_week4_limit=100,
    )
    warmup = WarmupManager(settings=settings)

    now = datetime.now(timezone.utc)

    # Day 0 (Week 1): 25 limit
    t1 = warmup.get_warmup_tier(warmup_start=now)
    assert t1.week_number == 1
    assert t1.daily_quota == 25

    # Day 8 (Week 2): 50 limit (+25)
    t2 = warmup.get_warmup_tier(warmup_start=now - timedelta(days=8))
    assert t2.week_number == 2
    assert t2.daily_quota == 50

    # Day 16 (Week 3): 75 limit (+25)
    t3 = warmup.get_warmup_tier(warmup_start=now - timedelta(days=16))
    assert t3.week_number == 3
    assert t3.daily_quota == 75

    # Day 24 (Week 4): 100 limit (Max)
    t4 = warmup.get_warmup_tier(warmup_start=now - timedelta(days=24))
    assert t4.week_number == 4
    assert t4.daily_quota == 100


def test_warmup_quota_enforcement_with_storage():
    storage = InMemoryStorageBackend()
    settings = EmailSettings(warmup_week1_limit=3)
    warmup = WarmupManager(settings=settings, storage_backend=storage)

    # Can send initial
    can_send, sent, quota = warmup.can_send_today()
    assert can_send
    assert sent == 0
    assert quota == 3

    # Dispatch 3 emails
    warmup.record_send(inbox_id="primary", recipient="p1@corp.com", lead_id="lead-1")
    warmup.record_send(inbox_id="primary", recipient="p2@corp.com", lead_id="lead-2")
    warmup.record_send(inbox_id="primary", recipient="p3@corp.com", lead_id="lead-3")

    # Limit reached
    can_send, sent, quota = warmup.can_send_today()
    assert not can_send
    assert sent == 3
    assert storage.get_email_sent_count_today("primary") == 3


def test_multi_inbox_selection():
    settings = EmailSettings(
        warmup_week1_limit=2,
        extra_inboxes=[{"id": "secondary_gmail"}],
    )
    storage = InMemoryStorageBackend()
    warmup = WarmupManager(settings=settings, storage_backend=storage)

    # Primary has capacity
    assert warmup.get_available_inbox() == "primary"

    # Max out primary
    warmup.record_send(inbox_id="primary", recipient="a@corp.com")
    warmup.record_send(inbox_id="primary", recipient="b@corp.com")

    # Load balancer falls over to secondary
    assert warmup.get_available_inbox() == "secondary_gmail"


def test_cold_email_link_mode_permission_first_vs_direct():
    # 1. Permission-first mode: zero links in body text, ends with binary question
    pitch_pf = render_sub_60_word_pitch(
        company_name="Lone Star Construction",
        niche="Building Permits",
        portal_name="City of Austin",
        sample_count=25,
        slug="lone-star-pf",
        link_mode="permission_first",
    )
    assert pitch_pf.word_count < 60
    assert "Would it be helpful to see the live feed sandbox" in pitch_pf.body_text
    assert "http" not in pitch_pf.body_text
    # Still provides sandbox URL on PitchMessage for reply agent
    assert "/p/lone-star-pf" in pitch_pf.sandbox_url

    # 2. Direct link mode: contains direct link in body text
    pitch_dl = render_sub_60_word_pitch(
        company_name="Lone Star Construction",
        niche="Building Permits",
        portal_name="City of Austin",
        sample_count=25,
        slug="lone-star-dl",
        link_mode="direct_link",
    )
    assert "/p/lone-star-dl" in pitch_dl.body_text
    assert pitch_dl.word_count < 60


def test_native_email_client_mock_dispatch():
    dispatched = []

    def mock_hook(payload: dict) -> dict:
        dispatched.append(payload)
        return {"ok": True, "status": "MOCK_SENT", "id": "msg_abc"}

    client = EmailClient(transport_hook=mock_hook)
    res = client.send_email(
        to_email="prospect@acme.com",
        to_name="Sarah",
        subject="Quick note re: Austin permits",
        text_body="Hi Sarah, verified 25 rows for Acme.",
    )
    assert res["status"] == "MOCK_SENT"
    assert len(dispatched) == 1
    assert dispatched[0]["to_email"] == "prospect@acme.com"
    assert dispatched[0]["subject"] == "Quick note re: Austin permits"


def test_pitcher_service_with_deliverability_and_warmup():
    dispatched = []

    def mock_hook(payload: dict) -> dict:
        dispatched.append(payload)
        return {"ok": True, "status": "SENT"}

    client = EmailClient(transport_hook=mock_hook)
    storage = InMemoryStorageBackend()
    warmup = WarmupManager(settings=EmailSettings(warmup_week1_limit=5), storage_backend=storage)
    pitcher = PitcherService(email_client=client, warmup_manager=warmup, storage_backend=storage)

    lead = Lead("lead-warmup-test", "daily", company_name="Acme Corp", contact_email="sarah@acme.com")
    pitch = render_sub_60_word_pitch("Acme Corp", "Permits", "City Portal", 20, "acme-warmup", link_mode="permission_first")

    # Dispatch
    res = pitcher.approve_and_dispatch(lead, "sarah@acme.com", "Sarah", pitch, human_approver="Operator")
    assert lead.state == State.OUTREACH_SENT
    assert len(dispatched) == 1
    assert warmup.get_sent_count_today("primary") == 1


def test_inbound_watcher_poll_and_ai_reply():
    storage = InMemoryStorageBackend()
    lead = Lead(
        "lead-inbound-test",
        "daily",
        company_name="Apex Builders",
        contact_name="Bob",
        contact_email="bob@apexbuilders.com",
    )
    lead.state = State.OUTREACH_SENT
    lead.slug = "apex-builders-slug"
    storage.save_lead(lead)

    # Simulated email client returning an unread prospect reply
    class MockInboundClient(EmailClient):
        def fetch_unseen_emails(self, folder="INBOX", mark_as_read=False):
            return [{
                "imap_id": "101",
                "sender_name": "Bob Vance",
                "sender_email": "bob@apexbuilders.com",
                "subject": "Re: Sample Building Permits data feed for Apex Builders",
                "message_id": "<reply-101@apexbuilders.com>",
                "in_reply_to": "<pitch-99@leadops.tech>",
                "references": "<pitch-99@leadops.tech>",
                "date": "Mon, 06 Sep 2026 12:00:00 -0500",
                "body_text": "Hey Alex, this looks interesting! Could you send over the sandbox link to review the permits?",
                "body_html": "",
            }]

    watcher = InboundEmailWatcher(
        email_client=MockInboundClient(),
        storage_backend=storage,
    )

    results = watcher.poll_and_process_once()
    assert len(results) == 1
    assert results[0]["sender"] == "bob@apexbuilders.com"
    assert results[0]["intent"] in {"INTERESTED", "QUESTION"}

    # Verified lead transitioned to CONVERSATIONAL_INTAKE
    updated_lead = storage.get_lead("lead-inbound-test")
    assert updated_lead.state == State.CONVERSATIONAL_INTAKE

    # Inbound email stored in database
    records = storage.list_inbound_emails("lead-inbound-test")
    assert len(records) == 1
    assert records[0]["sender_email"] == "bob@apexbuilders.com"
    assert "sandbox link" in records[0]["body"]



def test_prospect_website_verification_agent():
    agent = ProspectWebsiteVerificationAgent()

    # Commercial General Contractor
    res_commercial = agent.verify_website(
        company_name="Austin Prime Contractors",
        website_url="https://austinprimecontractors.com",
        niche="Commercial Construction",
        page_content="Austin Prime Contractors is a full-service commercial general contracting firm specializing in ground-up structural construction and corporate tenant finish-outs in Central Texas.",
    )
    assert res_commercial["is_legitimate_buyer"] is True
    assert res_commercial["niche_alignment"] in {"high", "medium"}

    # Government Court (Not a buyer)
    res_gov = agent.verify_website(
        company_name="Travis County District Court",
        website_url="https://traviscountytx.gov/courts",
        niche="Court Dockets",
        page_content="Official website of the Travis County District Clerk and judicial district courts.",
    )
    assert res_gov["is_legitimate_buyer"] is False


def test_email_voice_humanizer_agent():
    agent = EmailVoiceHumanizerAgent()
    res = agent.review_and_humanize(
        subject="Sample Permits data feed for Acme Builders",
        body_text="Hi John,\n\nSaw Acme's commercial work in Austin. We automated daily permit tracking so your team doesn't have to pull dockets manually.\n\nIndexed 25 live records. Would it be helpful to stream these daily?\n\nBest,\nAlex | LeadOps",
        prospect_name="John",
        company_name="Acme Builders",
        niche="Commercial Construction",
    )
    assert res["is_voice_compliant"] is True
    assert res["word_count"] < 60
    assert "John" in res["humanized_body_text"] or "Alex" in res["humanized_body_text"]


def test_inbound_reply_pricing_and_destination_objections():
    agent = InboundReplyAgent()

    # 1. Pricing Inquiry
    res_price = agent.process_inbound_reply(
        inbound_text="Sounds interesting, how much does this cost?",
        inbound_subject="Re: Austin Permits",
        lead_context={
            "company_name": "Acme Builders",
            "contact_name": "Bob",
            "target_portal_name": "City of Austin",
        },
        sandbox_url="https://omnileadfeeder.tech/p/acme-builders",
    )
    assert res_price["intent"] in {"QUESTION", "INTERESTED"}
    assert "250" in res_price["draft_reply_text"]
    assert "escrow" in res_price["draft_reply_text"].lower() or "deposit" in res_price["draft_reply_text"].lower()

    # 2. General Interest
    res_interest = agent.process_inbound_reply(
        inbound_text="Yes please send me the preview link to see the data.",
        inbound_subject="Re: Austin Permits",
        lead_context={
            "company_name": "Acme Builders",
            "contact_name": "Bob",
            "target_portal_name": "City of Austin",
        },
        sandbox_url="https://omnileadfeeder.tech/p/acme-builders",
    )
    assert res_interest["intent"] == "INTERESTED"
    assert "https://omnileadfeeder.tech/p/acme-builders" in res_interest["draft_reply_text"]


def test_inbound_reply_with_running_conversation_log():
    """Verify that InboundReplyAgent incorporates running history and tailors responses dynamically."""
    agent = InboundReplyAgent()
    
    # Prior touchpoint: Alex sent cold email, Bob asked about price, Alex explained $250 escrow deposit.
    # Now Bob follows up specifically asking about webhook format.
    conversation_history = [
        {
            "sender_name": "Bob",
            "body": "How much is setup?",
            "draft_reply": "Hi Bob, setup is a 50% milestone deposit of $250 held in escrow. Ongoing sync is $250-$500/mo.",
        }
    ]
    initial_outreach = {
        "subject": "Austin Commercial Permits for Acme Builders",
        "body": "Hi Bob, noticed you pull commercial permits in Travis County. We automate daily extraction.",
    }

    res = agent.process_inbound_reply(
        inbound_text="Got it. Can you push this via JSON webhook to our Zapier endpoint instead of Sheets?",
        inbound_subject="Re: Austin Commercial Permits for Acme Builders",
        lead_context={
            "company_name": "Acme Builders",
            "contact_name": "Bob",
            "target_portal_name": "Travis County Permitting",
        },
        sandbox_url="https://omnileadfeeder.tech/p/acme-builders",
        conversation_history=conversation_history,
        initial_outreach=initial_outreach,
    )

    assert res["intent"] in {"QUESTION", "INTERESTED"}
    assert "draft_reply_text" in res
    reply_lower = res["draft_reply_text"].lower()
    # Confirms it answers the new webhook question rather than robotically repeating pricing setup
    assert "webhook" in reply_lower or "zapier" in reply_lower or "endpoint" in reply_lower or "json" in reply_lower

