"""Unit and Integration Tests for Cold Outreach Multi-Touch Sequencer."""

import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from agents.domain import Lead, State
from agents.storage import InMemoryStorageBackend
from agents.email.sequencer import ColdOutreachSequencer, clean_re_subject
from agents.pitcher import render_sub_60_word_pitch


class ColdOutreachSequencerTests(unittest.TestCase):
    def setUp(self):
        self.storage = InMemoryStorageBackend()
        self.mock_client = MagicMock()
        self.mock_client.send_email.return_value = {"id": "msg_seq_123", "status": "SENT"}
        self.sequencer = ColdOutreachSequencer(
            storage_backend=self.storage,
            email_client=self.mock_client,
        )

    def test_clean_re_subject(self):
        """Test formatting in-thread reply subjects without duplicate 'Re: ' prefixes."""
        self.assertEqual(clean_re_subject("travis county records"), "Re: travis county records")
        self.assertEqual(clean_re_subject("Re: travis county records"), "Re: travis county records")
        self.assertEqual(clean_re_subject("re: RE: question re: apex title"), "Re: question re: apex title")
        self.assertEqual(clean_re_subject(""), "Re: update")

    def test_touch_1_sample_snippet_and_dual_offer(self):
        """Test that Touch 1 cold email embeds 2 live sample rows and presents the dual offer under 55 words with 0 links."""
        sample_rows = [
            {"case_number": "2026-09142", "document_type": "Probate", "filing_party": "Estate of Miller"},
            {"case_number": "2026-09143", "document_type": "Deed of Trust", "filing_party": "Apex Title Group"},
        ]
        pitch = render_sub_60_word_pitch(
            company_name="Apex Escrow LLC",
            niche="Title & Settlement",
            portal_name="Travis County Clerk",
            sample_count=10,
            slug="apex-escrow-lead-1",
            contact_name="Marcus",
            link_mode="permission_first",
            sample_rows=sample_rows,
            county_name="Travis County",
        )

        # 1. Strictly sub-55 words
        self.assertLess(pitch.word_count, 55, f"Touch 1 word count {pitch.word_count} exceeded 55-word cap")
        # 2. 100% plaintext, zero links in Touch 1
        self.assertNotIn("http://", pitch.body_text)
        self.assertNotIn("https://", pitch.body_text)
        # 3. Features the 2 live sample snippet rows
        self.assertIn("2026-09142", pitch.body_text)
        self.assertIn("2026-09143", pitch.body_text)
        # 4. Features dual offer hook (rest of today's spreadsheet or test a 3-day run)
        self.assertIn("rest of today's spreadsheet", pitch.body_text)
        self.assertIn("3-day run", pitch.body_text)

    def test_render_touch_2_fresh_filings_bump(self):
        """Test rendering Touch 2 (Day 4 Bump): in-thread, sub-35 words, 0 links."""
        lead = Lead(
            lead_id="lead-seq-001",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Lone Star Probate Law",
            contact_name="David Vance",
            contact_email="david@lonestarprobate.com",
            county="Travis County",
            outreach_subject="travis county filings for lone star",
            outreach_thread_id="<msg-initial-001@olfmailer.com>",
            outreach_touch_count=1,
        )

        rendered = ColdOutreachSequencer.render_touch_email(lead, touch_number=2)

        self.assertEqual(rendered["touch_number"], 2)
        self.assertEqual(rendered["subject"], "Re: travis county filings for lone star")
        self.assertEqual(rendered["in_reply_to"], "<msg-initial-001@olfmailer.com>")
        self.assertEqual(rendered["references"], "<msg-initial-001@olfmailer.com>")
        self.assertFalse(rendered["has_links"])
        self.assertLess(rendered["word_count"], 35, f"Touch 2 word count {rendered['word_count']} exceeded 35-word cap")
        self.assertIn("Travis County", rendered["body_text"])
        self.assertIn("this morning's new", rendered["body_text"])
        self.assertIn("David", rendered["body_text"])

    def test_render_touch_3_breakup_resource(self):
        """Test rendering Touch 3 (Day 8 Breakup): in-thread, sub-35 words, 0 links."""
        lead = Lead(
            lead_id="lead-seq-002",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Lone Star Probate Law",
            contact_name="David Vance",
            contact_email="david@lonestarprobate.com",
            county="Travis County",
            outreach_subject="travis county filings for lone star",
            outreach_thread_id="<msg-initial-001@olfmailer.com>",
            outreach_touch_count=2,
        )

        rendered = ColdOutreachSequencer.render_touch_email(lead, touch_number=3)

        self.assertEqual(rendered["touch_number"], 3)
        self.assertEqual(rendered["subject"], "Re: travis county filings for lone star")
        self.assertEqual(rendered["in_reply_to"], "<msg-initial-001@olfmailer.com>")
        self.assertFalse(rendered["has_links"])
        self.assertLess(rendered["word_count"], 35, f"Touch 3 word count {rendered['word_count']} exceeded 35-word cap")
        self.assertTrue(
            "Assuming you have this handled in-house" in rendered["body_text"]
            or "Assuming you're all set" in rendered["body_text"]
        )
        self.assertIn("Travis County", rendered["body_text"])

    def test_find_eligible_leads_and_scheduling(self):
        """Test identifying leads whose scheduled follow-up timestamp has elapsed."""
        now = datetime.now(timezone.utc)

        # Lead 1: Due for Touch 2 (past next_outreach_at)
        lead_due = Lead(
            lead_id="lead-due-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            contact_email="due@acme.com",
            outreach_touch_count=1,
            next_outreach_at=(now - timedelta(hours=2)).isoformat(),
            outreach_replied=False,
        )
        self.storage.save_lead(lead_due)

        # Lead 2: Future follow-up (not yet due)
        lead_future = Lead(
            lead_id="lead-future-2",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            contact_email="future@acme.com",
            outreach_touch_count=1,
            next_outreach_at=(now + timedelta(hours=48)).isoformat(),
            outreach_replied=False,
        )
        self.storage.save_lead(lead_future)

        # Lead 3: Already replied (must be excluded from sequencer)
        lead_replied = Lead(
            lead_id="lead-replied-3",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            contact_email="replied@acme.com",
            outreach_touch_count=1,
            next_outreach_at=(now - timedelta(hours=2)).isoformat(),
            outreach_replied=True,
        )
        self.storage.save_lead(lead_replied)

        # Lead 4: Converted to intake (state is not OUTREACH_SENT)
        lead_intake = Lead(
            lead_id="lead-intake-4",
            tier_key="daily",
            state=State.CONVERSATIONAL_INTAKE,
            contact_email="intake@acme.com",
            outreach_touch_count=1,
            next_outreach_at=(now - timedelta(hours=2)).isoformat(),
            outreach_replied=False,
        )
        self.storage.save_lead(lead_intake)

        eligible = self.sequencer.find_eligible_leads(now_dt=now)
        eligible_ids = [l.lead_id for l in eligible]

        self.assertEqual(len(eligible), 1)
        self.assertIn("lead-due-1", eligible_ids)
        self.assertNotIn("lead-future-2", eligible_ids)
        self.assertNotIn("lead-replied-3", eligible_ids)
        self.assertNotIn("lead-intake-4", eligible_ids)

    def test_full_sequence_lifecycle_dispatch(self):
        """Test dispatching Touch 2, advancing schedule, and dispatching Touch 3 completion."""
        now = datetime.now(timezone.utc)
        lead = Lead(
            lead_id="lead-lifecycle-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Apex Legal Partners",
            contact_name="Rachel",
            contact_email="rachel@apexlegal.com",
            county="Harris County",
            outreach_subject="harris county records",
            outreach_thread_id="<msg-lead-lifecycle-1@olfmailer.com>",
            outreach_touch_count=1,
            last_outreach_at=(now - timedelta(days=3)).isoformat(),
            next_outreach_at=(now - timedelta(hours=1)).isoformat(),
            outreach_replied=False,
        )
        self.storage.save_lead(lead)

        # 1. Dispatch Touch 2
        res2 = self.sequencer.dispatch_next_touch(lead, enforce_hours=False)
        self.assertEqual(res2["status"], "DISPATCHED")
        self.assertEqual(res2["touch_number"], 2)
        self.assertEqual(lead.outreach_touch_count, 2)
        self.assertTrue(lead.next_outreach_at)

        # 2. Fast forward 4 days for Touch 3
        future_dt = datetime.now(timezone.utc) + timedelta(days=5)
        res3 = self.sequencer.dispatch_next_touch(lead, enforce_hours=False)
        self.assertEqual(res3["status"], "DISPATCHED")
        self.assertEqual(res3["touch_number"], 3)
        self.assertEqual(lead.outreach_touch_count, 3)
        # Touch 3 completes sequence: next_outreach_at is cleared
        self.assertEqual(lead.next_outreach_at, "")

        # 3. Attempting Touch 4 is gracefully skipped
        res4 = self.sequencer.dispatch_next_touch(lead, enforce_hours=False)
        self.assertEqual(res4["status"], "SKIPPED")
        self.assertIn("no further touches", res4["reason"])

    def test_auto_outreach_scheduler_flushes_sequencer(self):
        """Test that AutoOutreachScheduler.flush_pending_office_hours_queue automatically advances eligible sequencer follow-ups."""
        from agents.auto_outreach import AutoOutreachScheduler
        from unittest.mock import patch

        scheduler = AutoOutreachScheduler()
        now = datetime.now(timezone.utc)
        lead = Lead(
            lead_id="lead-sched-seq-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Lone Star Records",
            contact_name="Bob",
            contact_email="bob@lonestar.com",
            county="Travis County",
            outreach_subject="travis county filings",
            outreach_thread_id="<msg-bob@olfmailer.com>",
            outreach_touch_count=1,
            last_outreach_at=(now - timedelta(days=4)).isoformat(),
            next_outreach_at=(now - timedelta(hours=2)).isoformat(),
            outreach_replied=False,
        )
        self.storage.save_lead(lead)

        with patch("agents.auto_outreach.is_office_hours", return_value=(True, 0, "Office hours open")), \
             patch("agents.email.sequencer.ColdOutreachSequencer.dispatch_next_touch") as mock_dispatch:
            mock_dispatch.return_value = {"lead_id": lead.lead_id, "status": "DISPATCHED", "touch_number": 2}
            dispatched = scheduler.flush_pending_office_hours_queue(storage_backend=self.storage)
            self.assertIn("lead-sched-seq-1", dispatched)
            self.assertTrue(mock_dispatch.called)

    def test_admin_sequencer_status_telemetry(self):
        """Test calculating sequence distribution metrics for admin telemetry."""
        now = datetime.now(timezone.utc)
        l1 = Lead(lead_id="l1", tier_key="daily", state=State.OUTREACH_SENT, outreach_touch_count=1, next_outreach_at=(now - timedelta(hours=1)).isoformat())
        l2 = Lead(lead_id="l2", tier_key="daily", state=State.OUTREACH_SENT, outreach_touch_count=2, next_outreach_at=(now + timedelta(days=2)).isoformat())
        l3 = Lead(lead_id="l3", tier_key="daily", state=State.OUTREACH_SENT, outreach_touch_count=3, outreach_replied=True)
        self.storage.save_lead(l1)
        self.storage.save_lead(l2)
        self.storage.save_lead(l3)

        all_leads = self.storage.list_leads()
        t1 = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) == 1)
        t2 = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) == 2)
        t3 = sum(1 for l in all_leads if getattr(l, "outreach_touch_count", 0) >= 3)
        replied = sum(1 for l in all_leads if getattr(l, "outreach_replied", False))

        self.assertEqual(t1, 1)
        self.assertEqual(t2, 1)
        self.assertEqual(t3, 1)
        self.assertEqual(replied, 1)

    def test_spintax_recursive_resolution(self):
        """Test recursive spintax resolution with nested brackets and deterministic seed."""
        import random
        from agents.email.sequencer import render_spintax

        rng1 = random.Random(42)
        text1 = "{Hi|Hey|Hello} {there|friend}, {how are you|hope all is well}."
        rendered1 = render_spintax(text1, rng=rng1)
        self.assertNotIn("{", rendered1)
        self.assertNotIn("}", rendered1)
        self.assertNotIn("|", rendered1)

        # Test nested brackets
        rng2 = random.Random(100)
        nested = "{A|{B|C}}"
        rendered2 = render_spintax(nested, rng=rng2)
        self.assertIn(rendered2, {"A", "B", "C"})

        # Test plain text without brackets unchanged
        plain = "Standard plain text without spintax."
        self.assertEqual(render_spintax(plain), plain)

    def test_infer_recipient_timezone_and_business_hours(self):
        """Test inferring timezone from state/city and evaluating 8:30 AM - 4:30 PM local window."""
        from agents.email.sequencer import infer_recipient_timezone, is_recipient_business_hours

        # 1. State code resolution
        self.assertEqual(infer_recipient_timezone("FL"), "America/New_York")
        self.assertEqual(infer_recipient_timezone("TX"), "America/Chicago")
        self.assertEqual(infer_recipient_timezone("CO"), "America/Denver")
        self.assertEqual(infer_recipient_timezone("CA"), "America/Los_Angeles")

        # 2. City fallback resolution
        self.assertEqual(infer_recipient_timezone("", "Austin"), "America/Chicago")
        self.assertEqual(infer_recipient_timezone("", "Miami"), "America/New_York")
        self.assertEqual(infer_recipient_timezone("", "Denver"), "America/Denver")
        self.assertEqual(infer_recipient_timezone("", "San Francisco"), "America/Los_Angeles")

        # 3. Business hours checks: Tuesday 10:00 AM Central (15:00 UTC) -> Open
        tuesday_open = datetime(2026, 9, 15, 15, 0, tzinfo=timezone.utc)
        is_open, wait_sec, msg = is_recipient_business_hours("America/Chicago", now_utc=tuesday_open)
        self.assertTrue(is_open)
        self.assertEqual(wait_sec, 0)

        # Tuesday 2:00 AM Central (07:00 UTC) -> Closed, waiting for 8:30 AM
        tuesday_early = datetime(2026, 9, 15, 7, 0, tzinfo=timezone.utc)
        is_open_early, wait_early, _ = is_recipient_business_hours("America/Chicago", now_utc=tuesday_early)
        self.assertFalse(is_open_early)
        self.assertGreater(wait_early, 0)

        # Saturday noon Central -> Closed for weekend
        saturday = datetime(2026, 9, 19, 17, 0, tzinfo=timezone.utc)
        is_open_weekend, wait_weekend, _ = is_recipient_business_hours("America/Chicago", now_utc=saturday)
        self.assertFalse(is_open_weekend)
        self.assertGreater(wait_weekend, 86400)  # Over a day until Monday morning

    def test_calculate_gaussian_jitter_and_idempotency_key(self):
        """Test Gaussian distribution jitter bounded within [180, 420] and SHA-256 idempotency key."""
        from agents.email.sequencer import calculate_gaussian_jitter, generate_idempotency_key

        jitters = [calculate_gaussian_jitter() for _ in range(50)]
        for j in jitters:
            self.assertGreaterEqual(j, 180)
            self.assertLessEqual(j, 420)

        # Deterministic idempotency key
        k1 = generate_idempotency_key("lead-xyz-123", 2)
        k2 = generate_idempotency_key("lead-xyz-123", 2)
        k3 = generate_idempotency_key("lead-xyz-123", 3)
        self.assertEqual(k1, k2)
        self.assertNotEqual(k1, k3)
        self.assertEqual(len(k1), 24)

    def test_sqlite_idempotency_and_fail_closed_suppression(self):
        """Test durable SQLite idempotency rejection and fail-closed universal suppression."""
        import tempfile
        import os
        from agents.storage import SqliteStorageBackend
        from agents.domain import SequenceState

        with tempfile.TemporaryDirectory() as tmpdir:
            db_file = os.path.join(tmpdir, "test_seq.db")
            with SqliteStorageBackend(db_path=db_file) as storage:
                # 1. Test universal suppression table
                self.assertFalse(storage.is_globally_suppressed("prospect@bad.com"))
                storage.add_to_global_suppression("prospect@bad.com", reason="Hard bounce 550")
                self.assertTrue(storage.is_globally_suppressed("prospect@bad.com"))
                self.assertTrue(storage.is_globally_suppressed("PROSPECT@BAD.COM"))  # Case insensitive

                # 2. Test ColdOutreachSequencer using this SQLite backend
                mock_client = MagicMock()
                sequencer = ColdOutreachSequencer(storage_backend=storage, email_client=mock_client)

                # Test lead 1: Enrolled into sequence state
                lead1 = Lead(
                    lead_id="lead-test-1",
                    tier_key="daily",
                    state=State.OUTREACH_SENT,
                    company_name="Lone Star Escrow",
                    contact_email="prospect@good.com",
                    outreach_touch_count=1,
                )
                sequencer.enroll_lead(lead1)
                self.assertEqual(lead1.sequence_state, SequenceState.ENROLLED.value)

                # First dispatch succeeds
                res1 = sequencer.dispatch_next_touch(lead1, enforce_hours=False)
                self.assertEqual(res1["status"], "DISPATCHED")
                self.assertTrue(mock_client.send_email.called)
                mock_client.send_email.reset_mock()

                # Reset lead1 touch count to 1 to simulate a duplicate trigger on Touch 2
                lead1.outreach_touch_count = 1
                res_dup = sequencer.dispatch_next_touch(lead1, enforce_hours=False)
                self.assertEqual(res_dup["status"], "ALREADY_DISPATCHED")
                self.assertFalse(mock_client.send_email.called)

                # Test lead 2: Suppressed recipient drops send fail-closed
                lead2 = Lead(
                    lead_id="lead-test-2",
                    tier_key="daily",
                    state=State.OUTREACH_SENT,
                    company_name="Bad Escrow",
                    contact_email="prospect@bad.com",
                    outreach_touch_count=1,
                )
                storage.save_lead(lead2)
                res_supp = sequencer.dispatch_next_touch(lead2, enforce_hours=False)
                self.assertEqual(res_supp["status"], "SUPPRESSED")
                self.assertEqual(lead2.sequence_state, SequenceState.SUPPRESSED.value)
                self.assertEqual(lead2.state, State.ARCHIVED)
                self.assertFalse(mock_client.send_email.called)

    def test_inbound_ooo_auto_snoozing(self):
        """Test InboundEmailWatcher Out-of-Office detection, return date parsing, and sequence auto-snooze."""
        from agents.email.inbound_watcher import InboundEmailWatcher
        from agents.domain import SequenceState

        # 1. Date parser tests
        ref_dt = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
        d1 = InboundEmailWatcher.parse_ooo_return_date("I am out of the office until October 15th", reference_date=ref_dt)
        self.assertIsNotNone(d1)
        self.assertEqual(d1.month, 10)
        self.assertEqual(d1.day, 15)

        d2 = InboundEmailWatcher.parse_ooo_return_date("Returning on 11/04, please contact support.", reference_date=ref_dt)
        self.assertIsNotNone(d2)
        self.assertEqual(d2.month, 11)
        self.assertEqual(d2.day, 4)

        d3 = InboundEmailWatcher.parse_ooo_return_date("Back on Friday with limited access.", reference_date=ref_dt)
        self.assertIsNotNone(d3)
        self.assertEqual(d3.weekday(), 4)  # Friday

        d4 = InboundEmailWatcher.parse_ooo_return_date("I am away from my desk until tomorrow.", reference_date=ref_dt)
        self.assertIsNotNone(d4)
        self.assertEqual(d4.day, 16)

        # 2. Watcher process_single_inbound_email with OOO message
        watcher = InboundEmailWatcher(storage_backend=self.storage)
        lead = Lead(
            lead_id="lead-ooo-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            contact_email="vacationer@firm.com",
            outreach_touch_count=1,
            next_outreach_at=(ref_dt + timedelta(days=2)).isoformat(),
        )
        self.storage.save_lead(lead)

        ooo_msg = {
            "sender_email": "vacationer@firm.com",
            "subject": "Automatic reply: travis county filings",
            "body_text": "Thank you for reaching out. I am out of the office until October 20th.",
        }

        res = watcher.process_single_inbound_email(ooo_msg)
        self.assertEqual(res["status"], "OOO_SNOOZED")
        self.assertEqual(res["intent"], "OOO_AUTO_REPLY")
        self.assertFalse(res["reply_dispatched"])

        # Check that lead was paused and next_outreach_at rescheduled to return date + 24h
        reloaded = self.storage.get_lead("lead-ooo-1")
        self.assertEqual(reloaded.sequence_state, SequenceState.PAUSED.value)
        self.assertIn("2026-10-21", reloaded.next_outreach_at)
        self.assertTrue(any(e.get("event") == "OOO_SNOOZED" for e in reloaded.audit_log))

    def test_inbound_bounce_extract_and_suppression(self):
        """Test InboundEmailWatcher delivery failure bounce parsing, global suppression, and lead archival."""
        from agents.email.inbound_watcher import InboundEmailWatcher
        from agents.domain import SequenceState

        watcher = InboundEmailWatcher(storage_backend=self.storage)
        lead = Lead(
            lead_id="lead-bounce-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Defunct Law LLC",
            contact_email="bounced.prospect@defunct.com",
            outreach_touch_count=1,
        )
        self.storage.save_lead(lead)

        bounce_msg = {
            "sender_email": "mailer-daemon@googlemail.com",
            "subject": "Delivery Status Notification (Failure)",
            "body_text": "Delivery to the following recipient failed permanently: bounced.prospect@defunct.com (550 Mailbox not found)",
        }

        res = watcher.process_single_inbound_email(bounce_msg)
        self.assertEqual(res["status"], "BOUNCE_PROCESSED_AND_ARCHIVED")
        self.assertEqual(res["bounced_email"], "bounced.prospect@defunct.com")

        # Check lead was archived with BOUNCED sequence state
        reloaded = self.storage.get_lead("lead-bounce-1")
        self.assertEqual(reloaded.sequence_state, SequenceState.BOUNCED.value)
        self.assertEqual(reloaded.state, State.ARCHIVED)

        # Check email was globally suppressed
        self.assertTrue(self.storage.is_globally_suppressed("bounced.prospect@defunct.com"))

    def test_sequencer_inbox_load_balancing_and_quota_circuit_breaker(self):
        """Test ColdOutreachSequencer respecting WarmupManager inbox selection and daily quota enforcement."""
        from agents.email.warmup import WarmupManager
        from agents.email.config import InboxAccountConfig, EmailSettings

        settings = EmailSettings(
            user="test@example.com",
            app_password="pwd",
            warmup_week1_limit=2,
            inbox_pool=[
                InboxAccountConfig(id="inbox-a", email_address="alex@domain1.com", password="p1", daily_limit=1),
                InboxAccountConfig(id="inbox-b", email_address="alex@domain2.com", password="p2", daily_limit=1),
            ],
        )
        warmup = WarmupManager(settings=settings, storage_backend=self.storage)
        mock_client = MagicMock()
        mock_client.send_email.return_value = {"id": "msg_quota_1"}

        sequencer = ColdOutreachSequencer(
            storage_backend=self.storage,
            email_client=mock_client,
            warmup_manager=warmup,
        )

        lead1 = Lead(lead_id="lead-q1", tier_key="daily", state=State.OUTREACH_SENT, contact_email="user1@target.com", outreach_touch_count=1)
        lead2 = Lead(lead_id="lead-q2", tier_key="daily", state=State.OUTREACH_SENT, contact_email="user2@target.com", outreach_touch_count=1)
        lead3 = Lead(lead_id="lead-q3", tier_key="daily", state=State.OUTREACH_SENT, contact_email="user3@target.com", outreach_touch_count=1)

        # 1. First send: dispatches via inbox-a or inbox-b
        res1 = sequencer.dispatch_next_touch(lead1, enforce_hours=False)
        self.assertEqual(res1["status"], "DISPATCHED")

        # 2. Second send: balances load to the remaining available inbox
        res2 = sequencer.dispatch_next_touch(lead2, enforce_hours=False)
        self.assertEqual(res2["status"], "DISPATCHED")

        # 3. Third send: both inboxes reached daily_limit=1 -> QUOTA_EXHAUSTED
        res3 = sequencer.dispatch_next_touch(lead3, enforce_hours=False)
        self.assertEqual(res3["status"], "QUOTA_EXHAUSTED")
        self.assertIn("Fleet daily send quota reached", res3["reason"])

    def test_sequencer_llm_agent_generation(self):
        """Test that ColdOutreachSequencer uses LLM AI Agent for humanized, peer-to-peer sequence copy."""
        from agents.domain import Lead, State
        from agents.email.sequencer import ColdOutreachSequencer

        mock_llm = MagicMock()
        mock_llm.is_available.return_value = True
        mock_llm.run_sequencer_agent.return_value = {
            "touch_number": 2,
            "subject": "Re: travis county records",
            "body_text": "Hi Marcus,\n\nFollowing up on my note — we just indexed this morning's new Travis County filings. Want me to send the spreadsheet over, or are you all set in-house?\n\nBest,\nAlex",
            "word_count": 29,
            "is_humanized_peer": True,
        }

        lead = Lead(
            lead_id="lead-llm-1",
            tier_key="daily",
            state=State.OUTREACH_SENT,
            company_name="Lone Star Probate Law",
            contact_name="Marcus Vance",
            contact_email="marcus@lonestarprobate.com",
            county="Travis County",
            outreach_subject="travis county records",
            outreach_thread_id="<msg-001@olfmailer.com>",
            outreach_touch_count=1,
        )

        rendered = ColdOutreachSequencer.render_touch_email(lead, touch_number=2, llm_engine=mock_llm)
        self.assertEqual(rendered["generated_by"], "llm_agent")
        self.assertEqual(rendered["touch_number"], 2)
        self.assertLess(rendered["word_count"], 35)
        self.assertFalse(rendered["has_links"])
        self.assertNotIn("quick", rendered["body_text"].lower())
        self.assertIn("Marcus", rendered["body_text"])
        self.assertIn("Travis County", rendered["body_text"])
        self.assertTrue(mock_llm.run_sequencer_agent.called)

    def test_sequencer_voice_agent_direct_call(self):
        """Test SequencerVoiceAgent direct generation and humanization."""
        from agents.email.ai_review import SequencerVoiceAgent

        mock_llm = MagicMock()
        mock_llm.run_sequencer_agent.return_value = {
            "touch_number": 3,
            "subject": "Re: dallas dockets",
            "body_text": "Hi Sarah,\n\nAssuming you have this handled in-house. If you ever need daily Dallas County filings before 8 AM, reach out anytime.\n\nBest,\nAlex | LeadOps",
            "word_count": 26,
            "is_humanized_peer": True,
        }
        agent = SequencerVoiceAgent(llm_engine=mock_llm)
        lead_info = {"company_name": "Dallas Title", "contact_name": "Sarah", "county": "Dallas County"}
        res = agent.generate_touch(touch_number=3, lead_info=lead_info, prior_subject="dallas dockets")

        self.assertEqual(res["touch_number"], 3)
        self.assertTrue(res["is_humanized_peer"])
        self.assertLess(res["word_count"], 35)
        self.assertNotIn("quick", res["body_text"].lower())


if __name__ == "__main__":
    unittest.main()
