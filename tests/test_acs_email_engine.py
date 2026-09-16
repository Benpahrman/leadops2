"""Comprehensive Unit Tests for Azure Communication Services (ACS) Email Engine & Warmup."""

import os
import tempfile
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from agents.email.acs_client import AzureCommunicationEmailClient
from agents.email.config import EmailSettings
from agents.email.client import EmailClient
from agents.email.engine import (
    EmailEngine,
    EmailEngineQueue,
    RAMP_SCHEDULE,
    RampStage,
    SpintaxGenerator,
)


class TestAcsClient:
    """Tests for AzureCommunicationEmailClient."""

    def test_client_configuration_detection(self) -> None:
        client_empty = AzureCommunicationEmailClient(connection_string="")
        assert not client_empty.is_configured

        client_valid = AzureCommunicationEmailClient(
            connection_string="endpoint=https://leadops-acs.communication.azure.com/;accesskey=fakekey123"
        )
        assert client_valid.is_configured
        assert client_valid.default_sender == "ben@olfmailer.com"

    def test_dry_run_simulation_without_connection_string(self) -> None:
        client = AzureCommunicationEmailClient(connection_string="")
        res = client.send_email(
            to_email="test@example.com",
            to_name="Jane Doe",
            subject="Test Subject",
            text_body="Plain text body without links.",
        )
        assert res["ok"] is True
        assert res["status"] == "SIMULATED_NO_CONNECTION_STRING"
        assert res["recipient"] == "test@example.com"
        assert res["sender"] == "ben@olfmailer.com"

    def test_transport_hook_interception(self) -> None:
        intercepted = {}

        def mock_hook(payload: dict) -> dict:
            nonlocal intercepted
            intercepted = payload
            return {"ok": True, "status": "HOOKED", "message_id": "hook-123"}

        client = AzureCommunicationEmailClient(
            connection_string="endpoint=https://leadops-acs.communication.azure.com/;accesskey=fakekey123",
            transport_hook=mock_hook,
        )
        res = client.send_email(
            to_email="prospect@county.gov",
            to_name="Official",
            subject="Filings Inquiry",
            text_body="Plain body",
            sender_address="alex@olfmailer.com",
        )
        assert res["ok"] is True
        assert res["status"] == "HOOKED"
        assert intercepted["to_email"] == "prospect@county.gov"
        assert intercepted["sender"] == "alex@olfmailer.com"


class TestSpintaxGenerator:
    """Tests for plain-text conversational spintax generation."""

    def test_outreach_spintax_zero_links_and_length(self) -> None:
        lead = {
            "first_name": "Marcus",
            "company": "Lone Star Title",
            "jurisdiction": "Bexar County, TX",
        }
        subject, body = SpintaxGenerator.generate_outreach_spintax(lead, sender_name="Ben")
        assert len(subject) > 0
        assert "Marcus" in body
        assert "Bexar County, TX" in body
        assert "olfmailer.com" in body
        # Zero-link Touch 1 rule: no hyperlinks, no http:// or https:// in body
        assert "http://" not in body
        assert "https://" not in body
        # Word count check: between 30 and 70 words
        word_count = len(body.split())
        assert 30 <= word_count <= 70

    def test_peer_warmup_spintax(self) -> None:
        subject, body = SpintaxGenerator.generate_peer_warmup_spintax(sender_name="Ben")
        assert len(subject) > 0
        assert len(body) > 0
        assert "Ben" in body


class TestEmailEngineQueue:
    """Tests for persistent SQLite queue management."""

    @pytest.fixture
    def temp_queue(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        queue = EmailEngineQueue(db_path=tmp_path)
        yield queue
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    def test_lead_enqueuing_and_deduplication(self, temp_queue: EmailEngineQueue) -> None:
        assert temp_queue.enqueue_lead("target@firm.com", "John", "Firm LLC", "Dallas, TX") is True
        # Duplicate enqueue returns False
        assert temp_queue.enqueue_lead("target@firm.com", "John", "Firm LLC", "Dallas, TX") is False

        lead = temp_queue.pop_pending_lead()
        assert lead is not None
        assert lead["email"] == "target@firm.com"
        assert lead["first_name"] == "John"

        temp_queue.mark_lead_sent(lead["id"], status="Succeeded")
        # Now pending should be empty
        assert temp_queue.pop_pending_lead() is None

    def test_warmup_targets_rotation(self, temp_queue: EmailEngineQueue) -> None:
        assert temp_queue.enqueue_warmup_target("inbox1@gmail.com", "Inbox One") is True
        assert temp_queue.enqueue_warmup_target("inbox2@outlook.com", "Inbox Two") is True

        t1 = temp_queue.get_next_warmup_target()
        assert t1 is not None
        assert t1["email"] == "inbox1@gmail.com"
        temp_queue.record_warmup_sent(t1["id"])

        # Second target should rotate next
        t2 = temp_queue.get_next_warmup_target()
        assert t2 is not None
        assert t2["email"] == "inbox2@outlook.com"


class TestEmailEngine:
    """Tests for warm-up ramp progression and worker cycle."""

    @pytest.fixture
    def test_engine(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        queue = EmailEngineQueue(db_path=tmp_path)
        acs_client = AzureCommunicationEmailClient(connection_string="")
        engine = EmailEngine(queue=queue, acs_client=acs_client)
        yield engine
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    def test_ramp_stage_progression(self, test_engine: EmailEngine) -> None:
        # Day 1 -> 100% Peer Warm-up (Days 1-4)
        s1 = test_engine.get_active_stage(1)
        assert s1.cold_leads == 0
        assert s1.warmup_emails == 4

        # Day 6 -> Days 5-8
        s6 = test_engine.get_active_stage(6)
        assert s6.cold_leads == 0
        assert s6.warmup_emails == 10

        # Day 16 -> Days 15-21 (5 Cold + 20 Warm-up)
        s16 = test_engine.get_active_stage(16)
        assert s16.cold_leads == 5
        assert s16.warmup_emails == 20

        # Day 35 -> Day 31+ Steady State (30 Cold + 15 Warm-up)
        s35 = test_engine.get_active_stage(35)
        assert s35.cold_leads == 30
        assert s35.warmup_emails == 15

    def test_domain_2_milestone_trigger_at_day_15(self, test_engine: EmailEngine) -> None:
        # Simulate warmup start date 16 days ago
        past_date = (datetime.now(timezone.utc) - timedelta(days=15)).date().isoformat()
        test_engine.queue.set_state("warmup_start_date", past_date)

        day = test_engine.get_current_day()
        assert day == 16

        # Enqueue warm-up target
        test_engine.queue.enqueue_warmup_target("peer@outlook.com", "Peer")

        test_engine.execute_worker_cycle(single_step=True)
        # Domain 2 readiness should be set
        assert test_engine.queue.get_state("domain_2_warmup_ready") == "ready"

    def test_single_step_worker_cycle(self, test_engine: EmailEngine) -> None:
        test_engine.queue.enqueue_warmup_target("peer1@gmail.com", "Peer 1")
        test_engine.execute_worker_cycle(single_step=True)

        cold_count, warmup_count = test_engine.queue.get_today_sent_counts()
        assert warmup_count == 1
        assert cold_count == 0


class TestClientAcsIntegration:
    """Tests for integration between EmailClient and Azure Communication Services."""

    def test_email_client_routes_olfmailer_domain_to_acs(self) -> None:
        intercepted = {}

        def mock_transport(payload: dict) -> dict:
            nonlocal intercepted
            intercepted = payload
            return {"ok": True, "status": "ACS_INTERCEPTED", "message_id": "test-msg-1"}

        settings = EmailSettings(
            allowed_sending_domains=["olfmailer.com", "olfmailer.net"],
            from_email="ben@olfmailer.com",
            azure_communication_sender_email="ben@olfmailer.com",
        )
        client = EmailClient(settings=settings, transport_hook=mock_transport)

        res = client.send_email(
            to_email="recipient@example.com",
            to_name="Target",
            subject="Outreach via ACS",
            text_body="Plain text inquiry.",
        )
        assert res["ok"] is True
        assert intercepted["sender"] == "ben@olfmailer.com"
        assert intercepted["to_email"] == "recipient@example.com"


class TestWarmupAgentAndWatcher:
    """Tests for LLM WarmupAgent and PeerInboxWarmupWatcher unspam loop."""

    def test_warmup_agent_generation_and_fallback(self) -> None:
        from agents.email.engine import WarmupAgent

        class MockLLM:
            def generate_completion(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
                return '{"subject": "Observability Spike", "body": "Checked the Redis telemetry and latency is down to 4ms. Looks solid.\\n\\nBest,\\nBen"}'

        agent = WarmupAgent(llm_engine=MockLLM())
        subj, body = agent.generate_warmup_email(sender_name="Ben")
        assert subj == "Observability Spike"
        assert "Redis telemetry" in body
        assert "Ben" in body

        # Test contextual reply generation
        class MockReplyLLM:
            def generate_completion(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
                return "Great catch on the Redis latency. We saw the same on our US-East node.\n\nBest,\nAlex"

        agent_reply = WarmupAgent(llm_engine=MockReplyLLM())
        reply = agent_reply.generate_reply_email("Observability Spike", body, responder_name="Alex")
        assert "Redis latency" in reply
        assert "Alex" in reply

    def test_monitored_peer_inbox_registration(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        queue = EmailEngineQueue(db_path=tmp_path)

        ok = queue.enqueue_warmup_target(
            email="peer-inbox@gmail.com",
            name="Peer Test Inbox",
            password="app-password-xyz",
            provider="gmail",
            is_monitored=True,
        )
        assert ok is True

        monitored = queue.get_monitored_warmup_targets()
        assert len(monitored) == 1
        assert monitored[0]["email"] == "peer-inbox@gmail.com"
        assert monitored[0]["password"] == "app-password-xyz"
        assert monitored[0]["is_monitored"] == 1
        assert monitored[0]["imap_host"] == "imap.gmail.com"

        queue.record_unspam_event(monitored[0]["id"], count=2)
        queue.record_reply_event(monitored[0]["id"], count=1)

        updated = queue.get_monitored_warmup_targets()[0]
        assert updated["unspammed_count"] == 2
        assert updated["replied_count"] == 1

        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass

    def test_multi_mailbox_rotation_across_olfmailer(self) -> None:
        """Verify EmailEngine rotates dispatches across all 3 olfmailer mailboxes (ben@, alex@, contact@)."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        queue = EmailEngineQueue(db_path=tmp_path)
        engine = EmailEngine(queue=queue)

        senders = [engine.get_next_sender()["email"] for _ in range(6)]
        assert senders == [
            "ben@olfmailer.com",
            "alex@olfmailer.com",
            "contact@olfmailer.com",
            "ben@olfmailer.com",
            "alex@olfmailer.com",
            "contact@olfmailer.com",
        ]

        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass

    def test_target_exclusion_prevents_self_sends(self) -> None:
        """Verify get_next_warmup_target never returns the sender mailbox."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        queue = EmailEngineQueue(db_path=tmp_path)
        queue.enqueue_warmup_target("ben@olfmailer.com", "Ben OLF")
        queue.enqueue_warmup_target("alex@olfmailer.com", "Alex OLF")
        queue.enqueue_warmup_target("contact@olfmailer.com", "Contact OLF")

        target_for_ben = queue.get_next_warmup_target(exclude_email="ben@olfmailer.com")
        assert target_for_ben is not None
        assert target_for_ben["email"] != "ben@olfmailer.com"
        assert target_for_ben["email"] in ("alex@olfmailer.com", "contact@olfmailer.com")

        target_for_alex = queue.get_next_warmup_target(exclude_email="alex@olfmailer.com")
        assert target_for_alex is not None
        assert target_for_alex["email"] != "alex@olfmailer.com"

        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


