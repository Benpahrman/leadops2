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
    monkeypatch.delenv("INBOX_WATCHER_EMAIL", raising=False)
    monkeypatch.delenv("OUTLOOK_USER", raising=False)
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


def test_email_settings_outlook_watched_inbox(monkeypatch):
    monkeypatch.setenv("INBOX_WATCHER_EMAIL", "omnileadfeeder@outlook.com")
    monkeypatch.setenv("OUTLOOK_APP_PASSWORD", "test-outlook-password")
    monkeypatch.delenv("IMAP_HOST", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)

    settings = EmailSettings.from_environment()
    assert settings.user == "omnileadfeeder@outlook.com"
    assert settings.app_password == "test-outlook-password"
    assert settings.imap_host == "outlook.office365.com"
    assert settings.imap_port == 993
    assert settings.smtp_host == "smtp-mail.outlook.com"
    assert settings.smtp_port == 587
    assert settings.smtp_use_ssl is False
    assert settings.smtp_use_tls is True

    # Verify primary inbox account config
    inboxes = settings.get_all_inboxes()
    primary = inboxes[0]
    assert primary.id == "primary"
    assert primary.email_address == "omnileadfeeder@outlook.com"
    assert primary.provider == "outlook"
    assert primary.imap_host == "outlook.office365.com"
    assert primary.imap_port == 993
    assert primary.smtp_host == "smtp-mail.outlook.com"
    assert primary.smtp_port == 587


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
        outbound_use_gmail=True,
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


def test_cloudflare_sending_domains_resolution():
    """Verify that sender emails strictly resolve to Cloudflare registered subdomains."""
    # Default without explicit domain rotates/resolves to email.omnileadfeeder.tech or contact.omnileadfeeder.tech
    settings = EmailSettings(from_name="Alex | OmniLeadFeeder")
    resolved_1 = settings.resolve_sender_email(hint="lead_123")
    assert any(resolved_1.endswith(d) for d in ("@email.omnileadfeeder.tech", "@contact.omnileadfeeder.tech"))

    # Explicit strategy contact_only
    settings_contact = EmailSettings(sending_strategy="contact_only")
    assert settings_contact.resolve_sender_email() == "alex@contact.omnileadfeeder.tech"

    # Explicit strategy email_only
    settings_email = EmailSettings(sending_strategy="email_only")
    assert settings_email.resolve_sender_email() == "alex@email.omnileadfeeder.tech"

    # Preserves custom username prefix
    settings_custom_user = EmailSettings(from_email="outreach.ops@unknown-domain.com")
    resolved_custom = settings_custom_user.resolve_sender_email(preferred_domain="contact.omnileadfeeder.tech")
    assert resolved_custom == "outreach.ops@contact.omnileadfeeder.tech"


def test_cloudflare_sending_domains_rotation():
    """Verify rotation between email.omnileadfeeder.tech and contact.omnileadfeeder.tech across leads."""
    settings = EmailSettings(sending_strategy="rotate")
    hits = set()
    for test_id in ["prospect_a", "prospect_b", "prospect_c", "prospect_d", "prospect_e"]:
        email_addr = settings.resolve_sender_email(hint=test_id)
        hits.add(email_addr.split("@")[-1])

    # Confirms both Cloudflare registered subdomains are exercised
    assert "email.omnileadfeeder.tech" in hits
    assert "contact.omnileadfeeder.tech" in hits


def test_email_client_dispatches_with_cloudflare_subdomain():
    """Verify EmailClient generates MIME From and Reply-To using Cloudflare subdomains."""
    captured = {}
    def fake_hook(data):
        captured.update(data)
        return {"ok": True, "message_id": "test_msg_id"}

    settings = EmailSettings(from_email="alex@email.omnileadfeeder.tech", outreach_dispatch_enabled=True)
    client = EmailClient(settings=settings, transport_hook=fake_hook)

    res = client.send_email(
        to_email="prospect@commercialbuilders.com",
        to_name="Jane Doe",
        subject="Quick question re: Dallas permits",
        text_body="Saw you do commercial work in Dallas.",
    )

    assert res["ok"] is True
    assert captured["from_email"] in ("alex@email.omnileadfeeder.tech", "alex@contact.omnileadfeeder.tech")


def test_inbound_watcher_should_ignore_google_and_system_senders():
    """Verify should_ignore_inbound accurately flags Google service domains, mailer-daemons, and bounce alerts."""
    # 1. Googlemail.com and Google.com domains
    assert InboundEmailWatcher.should_ignore_inbound("mailer-daemon@googlemail.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("user@googlemail.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("no-reply@accounts.google.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("Google Community Team <googlecommunityteam-noreply@google.com>") is True
    assert InboundEmailWatcher.should_ignore_inbound("alerts@google.com") is True

    # 2. Self-addressed loop protection
    assert InboundEmailWatcher.should_ignore_inbound("alex@email.omnileadfeeder.tech") is True
    assert InboundEmailWatcher.should_ignore_inbound("alex@contact.omnileadfeeder.tech") is True

    # 3. System daemon and noreply prefixes on any domain
    assert InboundEmailWatcher.should_ignore_inbound("mailer-daemon@yahoo.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("postmaster@company.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("no-reply@service.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("noreply@randomsaas.com") is True
    assert InboundEmailWatcher.should_ignore_inbound("bounce+12345@sendgrid.net") is True

    # 4. Delivery failure / bounce subjects
    assert InboundEmailWatcher.should_ignore_inbound("someone@anydomain.com", subject="Delivery Status Notification (Failure)") is True
    assert InboundEmailWatcher.should_ignore_inbound("someone@anydomain.com", subject="Undelivered Mail Returned to Sender") is True
    assert InboundEmailWatcher.should_ignore_inbound("someone@anydomain.com", subject="Automatic reply: Out of office") is True

    # 5. Legitimate prospective leads are NOT ignored
    assert InboundEmailWatcher.should_ignore_inbound("prospect.owner@gmail.com", subject="Re: Austin Permits") is False
    assert InboundEmailWatcher.should_ignore_inbound("bob@apexbuilders.com", subject="Interested in the data feed") is False
    assert InboundEmailWatcher.should_ignore_inbound("sarah@commercialroofing.com", subject="Pricing question") is False


def test_inbound_watcher_does_not_reply_or_create_lead_for_ignored_senders():
    """Verify that InboundEmailWatcher does not provision leads or send replies when receiving mailer-daemon@googlemail.com or google.com."""
    storage = InMemoryStorageBackend()
    sent_emails = []

    class MockClient(EmailClient):
        def fetch_unseen_emails(self, folder="INBOX", mark_as_read=False):
            return [
                {
                    "imap_id": "1",
                    "sender_name": "Mail Delivery Subsystem",
                    "sender_email": "mailer-daemon@googlemail.com",
                    "subject": "Delivery Status Notification (Failure)",
                    "message_id": "<msg-bounce-1@googlemail.com>",
                    "body_text": "The message could not be delivered to recipient@nonexistentdomain.org",
                },
                {
                    "imap_id": "2",
                    "sender_name": "Google",
                    "sender_email": "no-reply@accounts.google.com",
                    "subject": "Security alert for your linked Google Account",
                    "message_id": "<msg-google-2@google.com>",
                    "body_text": "A new sign-in was detected on your account.",
                },
            ]

        def send_email(self, **kwargs):
            sent_emails.append(kwargs)
            return {"ok": True, "message_id": "fake_sent"}

    watcher = InboundEmailWatcher(
        email_client=MockClient(),
        storage_backend=storage,
    )

    results = watcher.poll_and_process_once()

    # Both messages processed as ignored
    assert len(results) == 2
    for res in results:
        assert res["ok"] is True
        assert res["status"] in {"IGNORED_SYSTEM_SENDER", "BOUNCE_PROCESSED_AND_ARCHIVED"}
        assert res["reply_dispatched"] is False
        assert res["intent"] == "IGNORED"
        assert res["lead_id"] is None

    # CRITICAL: Zero emails dispatched
    assert len(sent_emails) == 0

    # CRITICAL: Zero dummy leads created in storage
    leads = storage.list_leads()
    assert len(leads) == 0

    # CRITICAL: Zero inbound email records persisted
    records = storage.list_inbound_emails()
    assert len(records) == 0


def test_word_quick_banned_from_vocabulary():
    """Verify that the word 'quick' is strictly banned and purged from subjects, body copy, and AI humanizers."""
    from agents.pitcher import generate_natural_subject, render_sub_60_word_pitch
    import re

    # 1. Subject line generator must never emit 'quick'
    for _ in range(50):
        subj = generate_natural_subject(
            company_name="Apex Roofing Corp",
            niche="roofing permits",
            portal_name="Travis County Permits",
            contact_name="Bob",
        )
        assert not re.search(r"\bquick\b", subj, re.I), f"Found 'quick' in subject: {subj}"

    # 2. Pitch generator must never emit 'quick' in subject or body
    pitch = render_sub_60_word_pitch(
        company_name="Apex Roofing",
        niche="roofing permits",
        portal_name="Travis County Permits",
        sample_count=5,
        slug="apex-roofing",
        contact_name="Bob",
    )
    assert not re.search(r"\bquick\b", pitch.subject, re.I), f"Found 'quick' in pitch subject: {pitch.subject}"
    assert not re.search(r"\bquick\b", pitch.body_text, re.I), f"Found 'quick' in pitch body: {pitch.body_text}"

    # 3. Voice Humanizer purges 'quick' from input text and fallback subject
    humanizer = EmailVoiceHumanizerAgent()
    res = humanizer.review_and_humanize(
        subject="quick question re: permits",
        body_text="Got a quick question about your permits. Let me know if you want to take a quick look.",
        prospect_name="Bob Vance",
        company_name="Vance Refrigeration",
        niche="HVAC & Refrigeration",
    )
    assert not re.search(r"\bquick\b", res["humanized_subject"], re.I), f"Found 'quick' in humanized subject: {res['humanized_subject']}"
    assert not re.search(r"\bquick\b", res["humanized_body_text"], re.I), f"Found 'quick' in humanized body: {res['humanized_body_text']}"


def test_deliverability_verifier_rejects_dummy_domains_and_test_accounts():
    """Verify DeliverabilityVerifier flags dummy placeholder domains and unmonitored test accounts as UNDELIVERABLE."""
    verifier = DeliverabilityVerifier(probe_smtp=False)

    # 1. Dummy placeholder domains must be UNDELIVERABLE
    res_dummy1 = verifier.verify("contact@company.com")
    assert res_dummy1.status == DeliverabilityStatus.UNDELIVERABLE
    assert not res_dummy1.is_safe_to_send

    res_dummy2 = verifier.verify("ops@testcompany.com")
    assert res_dummy2.status == DeliverabilityStatus.UNDELIVERABLE

    # 2. Test accounts on any domain must not be safe to send
    res_test = verifier.verify("test@lonestar.com")
    assert res_test.is_role_account
    assert not res_test.is_safe_to_send


def test_inbound_watcher_extracts_bounced_email_and_archives_lead():
    """Verify that when a delivery failure notice is received, InboundEmailWatcher auto-archives the matching lead."""
    storage = InMemoryStorageBackend()
    bounced_lead = Lead(
        lead_id="lead-bounced-partner",
        tier_key="daily",
        company_name="Commercial Finance Partners",
        contact_email="contact@commercialfinancepartners.com",
    )
    bounced_lead.state = State.OUTREACH_SENT
    storage.save_lead(bounced_lead)

    bounce_msg = {
        "imap_id": "99",
        "sender_name": "Mail Delivery Subsystem",
        "sender_email": "mailer-daemon@googlemail.com",
        "subject": "Delivery Status Notification (Failure)",
        "message_id": "<bounce-msg-99@googlemail.com>",
        "body_text": "Address not found\n\nYour message wasn't delivered to contact@commercialfinancepartners.com because the address couldn't be found, or is unable to receive mail.",
    }

    watcher = InboundEmailWatcher(storage_backend=storage)
    res = watcher.process_single_inbound_email(bounce_msg)

    assert res["status"] == "BOUNCE_PROCESSED_AND_ARCHIVED"
    assert res["bounced_email"] == "contact@commercialfinancepartners.com"
    assert res["lead_id"] == "lead-bounced-partner"
    assert res["reply_dispatched"] is False

    # Verify lead was transitioned to ARCHIVED
    updated_lead = storage.get_lead("lead-bounced-partner")
    assert updated_lead.state == State.ARCHIVED
    assert "Delivery bounce received" in updated_lead.audit_log[-1]["reason"]


# =============================================================
# ZOHO MAIL & MULTI-INBOX TEST SUITE
# =============================================================

def test_zoho_inbox_config_defaults():
    """Verify Zoho workplace and personal domain host/port presets."""
    from agents.email.config import InboxAccountConfig

    # 1. Custom domain Zoho Workplace -> smtp.zoho.com & imap.zoho.com
    workplace_inbox = InboxAccountConfig(
        id="zoho_workplace",
        email_address="alex@omnileadfeeder.tech",
        password="app-secret-pwd",
        provider="zoho",
    )
    assert workplace_inbox.smtp_host == "smtp.zoho.com"
    assert workplace_inbox.smtp_port == 465
    assert workplace_inbox.smtp_use_ssl is True
    assert workplace_inbox.imap_host == "imap.zoho.com"
    assert workplace_inbox.imap_port == 993
    assert workplace_inbox.imap_use_ssl is True

    # 2. Personal @zoho.com -> smtp.zoho.com & imap.zoho.com
    personal_inbox = InboxAccountConfig(
        id="zoho_personal",
        email_address="founder@zoho.com",
        password="personal-app-pwd",
        provider="zoho",
    )
    assert personal_inbox.smtp_host == "smtp.zoho.com"
    assert personal_inbox.imap_host == "imap.zoho.com"


def test_zoho_inbox_env_loader(monkeypatch):
    """Verify loading numbered Zoho inboxes and JSON pool from environment variables."""
    from agents.email.config import EmailSettings

    # Clear any surrounding env inboxes for test isolation
    for i in range(1, 11):
        monkeypatch.delenv(f"ZOHO_INBOX_{i}_EMAIL", raising=False)
        monkeypatch.delenv(f"ZOHO_INBOX_{i}_APP_PASSWORD", raising=False)
        monkeypatch.delenv(f"ZOHO_INBOX_{i}_FROM_NAME", raising=False)
    monkeypatch.delenv("ZOHO_INBOXES_JSON", raising=False)

    monkeypatch.setenv("ZOHO_INBOX_1_EMAIL", "outreach1@company.com")
    monkeypatch.setenv("ZOHO_INBOX_1_APP_PASSWORD", "pwd-one-1234")
    monkeypatch.setenv("ZOHO_INBOX_1_FROM_NAME", "Alex | Outreach 1")
    monkeypatch.setenv("ZOHO_INBOX_2_EMAIL", "outreach2@company.com")
    monkeypatch.setenv("ZOHO_INBOX_2_APP_PASSWORD", "pwd-two-5678")

    settings = EmailSettings.from_environment()
    accounts = settings.inbox_pool
    assert len(accounts) == 2

    acc1 = next(a for a in accounts if a.id == "zoho_1")
    assert acc1.email_address == "outreach1@company.com"
    assert acc1.password == "pwd-one-1234"
    assert acc1.from_name == "Alex | Outreach 1"
    assert acc1.smtp_host == "smtp.zoho.com"
    assert acc1.imap_host == "imap.zoho.com"

    acc2 = next(a for a in accounts if a.id == "zoho_2")
    assert acc2.email_address == "outreach2@company.com"
    assert acc2.password == "pwd-two-5678"


def test_multi_inbox_warmup_load_balancing_4_zoho():
    """Verify round-robin load balancing across 4 Zoho inboxes without using Gmail for outbound."""
    from agents.email.config import EmailSettings, InboxAccountConfig
    from agents.email.warmup import WarmupManager

    inbox1 = InboxAccountConfig(id="zoho_1", email_address="z1@corp.com", password="p1", daily_limit=2)
    inbox2 = InboxAccountConfig(id="zoho_2", email_address="z2@corp.com", password="p2", daily_limit=2)
    inbox3 = InboxAccountConfig(id="zoho_3", email_address="z3@corp.com", password="p3", daily_limit=2)
    inbox4 = InboxAccountConfig(id="zoho_4", email_address="z4@corp.com", password="p4", daily_limit=2)

    settings = EmailSettings(
        warmup_week1_limit=2,
        outbound_use_gmail=False,
        inbox_pool=[inbox1, inbox2, inbox3, inbox4],
    )
    storage = InMemoryStorageBackend()
    warmup = WarmupManager(settings=settings, storage_backend=storage)

    # 1. First Zoho inbox has quota (Gmail excluded from outbound)
    assert warmup.get_available_inbox() == "zoho_1"
    warmup.record_send(inbox_id="zoho_1", recipient="z1_a@a.com")
    warmup.record_send(inbox_id="zoho_1", recipient="z1_b@a.com")

    # 2. Zoho 1 exhausted -> falls over to Zoho 2
    assert warmup.get_available_inbox() == "zoho_2"
    warmup.record_send(inbox_id="zoho_2", recipient="z2_a@a.com")
    warmup.record_send(inbox_id="zoho_2", recipient="z2_b@a.com")

    # 3. Zoho 2 exhausted -> falls over to Zoho 3
    assert warmup.get_available_inbox() == "zoho_3"
    warmup.record_send(inbox_id="zoho_3", recipient="z3_a@a.com")
    warmup.record_send(inbox_id="zoho_3", recipient="z3_b@a.com")

    # 4. Zoho 3 exhausted -> falls over to Zoho 4
    assert warmup.get_available_inbox() == "zoho_4"
    warmup.record_send(inbox_id="zoho_4", recipient="z4_a@a.com")
    warmup.record_send(inbox_id="zoho_4", recipient="z4_b@a.com")

    # 5. All 4 Zoho inboxes exhausted for today -> returns None
    assert warmup.get_available_inbox() is None


def test_email_client_zoho_from_header_binding():
    """Verify EmailClient strictly binds From: header to authentic Zoho mailbox address."""
    from agents.email.config import InboxAccountConfig

    dispatched_data = {}

    def mock_transport(payload):
        dispatched_data.update(payload)
        return {"ok": True, "message_id": "<test-msg-1@zoho>"}

    client = EmailClient(transport_hook=mock_transport)

    zoho_inbox = InboxAccountConfig(
        id="zoho_acct_3",
        email_address="alex.outreach@customdomain.com",
        password="app-secret-pwd",
        from_name="Alex | OmniLeadFeeder",
        provider="zoho",
    )

    res = client.send_email(
        to_email="prospect@targetcorp.com",
        to_name="Target Prospect",
        subject="Quick question about building permits",
        text_body="Hi Target, would you like to review sample data?",
        inbox=zoho_inbox,
    )

    assert res["ok"] is True
    # Crucial: From email MUST match the Zoho authenticated user to avoid relay rejection
    assert dispatched_data["from_email"] == "alex.outreach@customdomain.com"
    assert dispatched_data["from_name"] == "Alex | OmniLeadFeeder"
    assert dispatched_data["inbox_id"] == "zoho_acct_3"


def test_storage_inbox_accounts_crud():
    """Verify list, get, upsert, and delete operations on inbox accounts."""
    storage = InMemoryStorageBackend()

    account = {
        "inbox_id": "zoho_test_inbox",
        "email_address": "inbox1@zoho-corp.com",
        "provider": "zoho",
        "smtp_host": "smtppro.zoho.com",
        "smtp_port": 465,
        "smtp_use_ssl": True,
        "imap_host": "imappro.zoho.com",
        "imap_port": 993,
        "imap_use_ssl": True,
        "daily_limit": 50,
        "warmup_start_date": "2026-09-08T00:00:00Z",
        "is_active": 1,
    }

    storage.upsert_inbox_account(account)

    fetched = storage.get_inbox_account("zoho_test_inbox")
    assert fetched is not None
    assert fetched["email_address"] == "inbox1@zoho-corp.com"
    assert fetched["provider"] == "zoho"
    assert fetched["daily_limit"] == 50

    all_inboxes = storage.list_inbox_accounts()
    assert len(all_inboxes) == 1
    assert all_inboxes[0]["inbox_id"] == "zoho_test_inbox"

    storage.delete_inbox_account("zoho_test_inbox")
    assert storage.get_inbox_account("zoho_test_inbox") is None
    assert len(storage.list_inbox_accounts()) == 0


def test_deliverability_verifier_active_domain_and_bounce_prevention():
    """Verify DeliverabilityVerifier flags inactive/non-existent domains and verifies real email deliverability."""
    verifier = DeliverabilityVerifier(probe_smtp=False, probe_web=False)

    # 1. Non-existent / inactive domain
    fake_domain = "nonexistent-domain-xyz-98741-def.org"
    is_live, msg = verifier.check_domain_active(fake_domain)
    assert not is_live
    assert "no active DNS" in msg or "NXDOMAIN" in msg

    # 2. Email on non-existent domain should be UNDELIVERABLE
    res_fake = verifier.verify(f"alex@{fake_domain}")
    assert res_fake.status == DeliverabilityStatus.UNDELIVERABLE
    assert not res_fake.is_domain_active
    assert not res_fake.is_safe_to_send

    # 3. Active legitimate domain
    live_domain = "google.com"
    is_live_google, _ = verifier.check_domain_active(live_domain)
    assert is_live_google

    # 4. Valid email on active domain with MX
    res_real = verifier.verify("engineering@github.com")
    assert res_real.status == DeliverabilityStatus.DELIVERABLE
    assert res_real.is_domain_active
    assert res_real.is_safe_to_send


def test_auto_outreach_rejection_window_and_autonomous_dispatch():
    """Verify AutoOutreachScheduler registers lead with 3-minute grace period and supports mobile cancellation."""
    from agents.auto_outreach import AutoOutreachScheduler
    from agents.domain import Lead, State

    scheduler = AutoOutreachScheduler(grace_period_seconds=180)
    assert scheduler.grace_period_seconds == 180

    storage = InMemoryStorageBackend()
    lead = Lead(
        lead_id="lead-test-autonomous-1",
        state=State.PITCH_PENDING_APPROVAL,
        company_name="Lone Star Construction",
        contact_email="chris@getyomnileadfeeder.cyou",
        tier_key="daily",
    )
    storage.save_lead(lead)

    # Schedule lead for dispatch
    schedule_res = scheduler.schedule_lead_for_dispatch(
        lead=lead,
        pitch=None,
        storage_backend=storage,
    )
    assert schedule_res["ok"]
    assert schedule_res["grace_period_seconds"] == 180
    assert scheduler.is_pending("lead-test-autonomous-1")

    # Operator cancels via rejection window
    cancelled = scheduler.cancel_dispatch("lead-test-autonomous-1", reason="Operator test rejection")
    assert cancelled
    assert not scheduler.is_pending("lead-test-autonomous-1")







