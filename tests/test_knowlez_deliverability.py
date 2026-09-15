"""Tests for Knowlez Deliverability Suite integration, bounce reduction, and pre-flight verification."""

from unittest.mock import MagicMock, patch
import pytest

from agents.email.knowlez_client import KnowlezDeliverabilityClient
from agents.email.verifier import DeliverabilityVerifier, DeliverabilityStatus
from agents.email.engine import EmailEngine, EmailEngineQueue


def test_knowlez_client_configured():
    client = KnowlezDeliverabilityClient(api_key="ik_test_key123")
    assert client.is_configured
    assert client._get_headers()["x-api-key"] == "ik_test_key123"


def test_knowlez_client_unconfigured_graceful_fallback():
    client = KnowlezDeliverabilityClient(api_key="")
    assert not client.is_configured
    res = client.verify_email("test@example.com")
    assert res.get("unverified_fallback") is True
    assert res.get("valid") is True


def test_knowlez_verify_email_mocked_success():
    client = KnowlezDeliverabilityClient(api_key="ik_live_test")
    mock_resp = {
        "email": "lead@targetfirm.com",
        "valid": True,
        "syntax_ok": True,
        "mx_ok": True,
        "mx_hosts": ["mail.targetfirm.com"],
        "disposable": False,
        "role_based": False,
        "score": 100,
        "reason": None,
    }
    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_resp
        mock_post.return_value = mock_res

        result = client.verify_email("lead@targetfirm.com")
        assert result["valid"] is True
        assert result["mx_ok"] is True
        assert result["score"] == 100


def test_knowlez_verify_disposable_domain():
    client = KnowlezDeliverabilityClient(api_key="ik_live_test")
    mock_resp = {
        "email": "badlead@mailinator.com",
        "valid": False,
        "syntax_ok": True,
        "mx_ok": True,
        "mx_hosts": ["mail.mailinator.com"],
        "disposable": True,
        "role_based": False,
        "score": 70,
        "reason": "disposable_domain",
    }
    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_resp
        mock_post.return_value = mock_res

        result = client.verify_email("badlead@mailinator.com")
        assert result["valid"] is False
        assert result["disposable"] is True
        assert result["reason"] == "disposable_domain"


def test_deliverability_verifier_integrates_knowlez():
    mock_knowlez = MagicMock()
    mock_knowlez.is_configured = True
    mock_knowlez.verify_email.return_value = {
        "email": "lead@validcorp.com",
        "valid": True,
        "syntax_ok": True,
        "mx_ok": True,
        "mx_hosts": ["mx.validcorp.com"],
        "disposable": False,
        "role_based": False,
        "score": 100,
        "reason": None,
    }

    verifier = DeliverabilityVerifier(
        probe_smtp=False,
        probe_web=False,
        knowlez_client=mock_knowlez,
    )
    res = verifier.verify("lead@validcorp.com")
    assert res.status == DeliverabilityStatus.DELIVERABLE
    assert res.is_safe_to_send
    assert "mx.validcorp.com" in res.mx_records


def test_deliverability_verifier_blocks_knowlez_flagged_lead():
    mock_knowlez = MagicMock()
    mock_knowlez.is_configured = True
    mock_knowlez.verify_email.return_value = {
        "email": "bounced@deadserver.com",
        "valid": False,
        "syntax_ok": True,
        "mx_ok": False,
        "mx_hosts": [],
        "disposable": False,
        "role_based": False,
        "score": 50,
        "reason": "no_mx_records",
    }

    verifier = DeliverabilityVerifier(
        probe_smtp=False,
        probe_web=False,
        knowlez_client=mock_knowlez,
    )
    res = verifier.verify("bounced@deadserver.com")
    assert res.status == DeliverabilityStatus.UNDELIVERABLE
    assert not res.is_safe_to_send
    assert "no_mx_records" in res.reason


def test_email_engine_bounce_shield_suppression(tmp_path):
    db_file = tmp_path / "test_engine.db"
    queue = EmailEngineQueue(db_path=db_file)
    queue.enqueue_lead("badbounce@invalidserver.com", "John", "Acme", "Harris County")

    mock_acs = MagicMock()
    mock_knowlez = MagicMock()
    mock_knowlez.is_configured = True
    mock_knowlez.verify_email.return_value = {
        "email": "badbounce@invalidserver.com",
        "valid": False,
        "syntax_ok": True,
        "mx_ok": False,
        "disposable": False,
        "reason": "no_mx_records",
    }

    engine = EmailEngine(
        queue=queue,
        acs_client=mock_acs,
        knowlez_client=mock_knowlez,
    )
    # Set stage with cold leads available and enabled outreach
    with patch.dict("os.environ", {"AUTO_OUTREACH_ENABLED": "true"}), \
         patch.object(engine.queue, "get_today_sent_counts", return_value=(0, 10)), \
         patch.object(engine, "get_active_stage") as mock_stage:
        stage_mock = MagicMock()
        stage_mock.cold_leads = 5
        stage_mock.warmup_emails = 10
        stage_mock.description = "Test Ramp Tier"
        mock_stage.return_value = stage_mock

        # Run worker cycle
        engine.execute_worker_cycle(single_step=True)

        # ACS send_email MUST NOT be called because bounce shield intercepted it!
        mock_acs.send_email.assert_not_called()

        # Queue must record lead as suppressed
        logs = queue.get_dispatch_history()
        assert len(logs) == 1
        assert logs[0]["status"] == "suppressed_no_mx_records"


def test_email_engine_cold_outreach_disabled_safety(tmp_path):
    db_file = tmp_path / "test_engine_disabled.db"
    queue = EmailEngineQueue(db_path=db_file)
    queue.enqueue_lead("prospect@validcorp.com", "Jane", "Acme", "Travis County")

    mock_acs = MagicMock()
    mock_knowlez = MagicMock()
    mock_knowlez.is_configured = True
    mock_knowlez.verify_email.return_value = {"valid": True, "mx_ok": True}

    engine = EmailEngine(
        queue=queue,
        acs_client=mock_acs,
        knowlez_client=mock_knowlez,
    )
    with patch.dict("os.environ", {"AUTO_OUTREACH_ENABLED": "false"}), \
         patch.object(engine.queue, "get_today_sent_counts", return_value=(0, 10)), \
         patch.object(engine, "get_active_stage") as mock_stage:
        stage_mock = MagicMock()
        stage_mock.cold_leads = 5
        stage_mock.warmup_emails = 10
        mock_stage.return_value = stage_mock

        # Run worker cycle
        engine.execute_worker_cycle(single_step=True)

        # Neither ACS nor Knowlez should be called because cold outreach is administratively disabled!
        mock_acs.send_email.assert_not_called()
        mock_knowlez.verify_email.assert_not_called()
        assert len(queue.get_dispatch_history()) == 0


def test_detect_email_provider():
    from agents.email.knowlez_client import detect_email_provider

    # Google checks
    assert detect_email_provider([], "partner@gmail.com") == "google"
    assert detect_email_provider(["aspmx.l.google.com"], "ceo@startup.io") == "google"
    assert detect_email_provider(["alt1.aspmx.l.google.com"], "lead@firm.com") == "google"

    # Microsoft checks
    assert detect_email_provider([], "user@outlook.com") == "microsoft"
    assert detect_email_provider([], "exec@hotmail.com") == "microsoft"
    assert detect_email_provider(["enterprise-com.mail.protection.outlook.com"], "cfo@enterprise.com") == "microsoft"
    assert detect_email_provider(["mx1.office365.com"], "partner@lawfirm.com") == "microsoft"

    # Other checks
    assert detect_email_provider(["mail.private-server.net"], "contact@private-server.net") == "other"
    assert detect_email_provider([], "info@unknown-domain.org") == "other"


def test_knowlez_smart_caching_zero_waste(tmp_path):
    from agents.email.knowlez_client import KnowlezDeliverabilityClient

    db_path = tmp_path / "cache_test.db"
    client = KnowlezDeliverabilityClient(api_key="ik_test_live", db_path=db_path)

    mock_resp = {
        "email": "lawyer@houstontxprobate.com",
        "valid": True,
        "syntax_ok": True,
        "mx_ok": True,
        "mx_hosts": ["houstontxprobate-com.mail.protection.outlook.com"],
        "disposable": False,
        "role_based": False,
        "score": 95,
        "reason": None,
    }

    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_resp
        mock_post.return_value = mock_res

        # First call -> hits API and stores in cache
        first_res = client.verify_email("lawyer@houstontxprobate.com")
        assert first_res["valid"] is True
        assert first_res["score"] == 95
        assert first_res["cached"] is False
        assert first_res["provider"] == "microsoft"
        assert mock_post.call_count == 1

        # Second call -> serves from 14-day SQLite cache with 0 API calls!
        second_res = client.verify_email("lawyer@houstontxprobate.com")
        assert second_res["valid"] is True
        assert second_res["score"] == 95
        assert second_res["cached"] is True
        assert second_res["provider"] == "microsoft"
        # call_count MUST still be 1 (zero credits burned!)
        assert mock_post.call_count == 1

        # Force call -> bypasses cache
        third_res = client.verify_email("lawyer@houstontxprobate.com", force=True)
        assert third_res["cached"] is False
        assert mock_post.call_count == 2


def test_knowlez_batch_smart_partitioning(tmp_path):
    from agents.email.knowlez_client import KnowlezDeliverabilityClient

    db_path = tmp_path / "batch_cache_test.db"
    client = KnowlezDeliverabilityClient(api_key="ik_test_live", db_path=db_path)

    # Pre-seed one cached email
    client.save_cached_verification("preseeded@gmail.com", {
        "email": "preseeded@gmail.com",
        "valid": True,
        "score": 100,
        "mx_ok": True,
        "mx_hosts": ["aspmx.l.google.com"],
        "disposable": False,
        "provider": "google",
    })

    emails = ["preseeded@gmail.com", "fresh@outlook.com"]

    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {
            "results": [
                {
                    "email": "fresh@outlook.com",
                    "valid": True,
                    "score": 90,
                    "mx_ok": True,
                    "mx_hosts": ["outlook.com"],
                    "disposable": False,
                }
            ]
        }
        mock_post.return_value = mock_res

        results = client.verify_batch(emails)
        assert len(results) == 2

        preseeded = next(r for r in results if r["email"] == "preseeded@gmail.com")
        fresh = next(r for r in results if r["email"] == "fresh@outlook.com")

        assert preseeded["cached"] is True
        assert preseeded["provider"] == "google"
        assert fresh["cached"] is False
        assert fresh["provider"] == "microsoft"

        # The API request sent to Knowlez should ONLY contain the uncached email ['fresh@outlook.com']!
        called_payload = mock_post.call_args[1]["json"]
        assert called_payload["emails"] == ["fresh@outlook.com"]


def test_pitcher_preflight_auto_check_blocks_bad_lead():
    from agents.domain import Lead, State
    from agents.pitcher import PitcherService, PitchMessage

    lead = Lead(
        lead_id="test_lead_preflight_fail",
        tier_key="weekly",
        state=State.PITCH_PENDING_APPROVAL,
        company_name="Bad Domain Co",
        contact_email="spammer@disposabledump.com",
    )

    mock_client = MagicMock()
    service = PitcherService(email_client=mock_client)

    pitch = PitchMessage(
        subject="quick question",
        body_text="Hi there,\n\nSaw your work. Best,\nAlex",
        body_html="<p>Hi</p>",
        sandbox_url="https://leadops.io/p/test",
        word_count=15,
    )

    # Mock knowlez returning invalid/disposable
    with patch("agents.email.knowlez_client.KnowlezDeliverabilityClient.verify_email") as mock_verify:
        mock_verify.return_value = {
            "email": "spammer@disposabledump.com",
            "valid": False,
            "score": 30,
            "status": "UNDELIVERABLE",
            "mx_ok": False,
            "disposable": True,
            "provider": "other",
            "cached": False,
        }

        with pytest.raises(ValueError, match="rejected by pre-flight deliverability shield"):
            service.approve_and_dispatch(
                lead=lead,
                recipient_email="spammer@disposabledump.com",
                recipient_name="Spammer",
                pitch=pitch,
                enforce_office_hours=False,
                enforce_deliverability=True,
            )

        assert lead.state == State.ARCHIVED
        assert lead.deliverability_score == 30
        assert lead.deliverability_status == "UNDELIVERABLE"
        mock_client.send_email.assert_not_called()


def test_knowlez_validate_domain_with_caching(tmp_path):
    db_file = tmp_path / "test_domain_cache.db"
    client = KnowlezDeliverabilityClient(api_key="ik_live_domain_test", db_path=db_file)

    mock_resp = {
        "domain": "olfmailer.com",
        "valid": True,
        "tld": "com",
        "normalized": "olfmailer.com",
    }

    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = mock_resp
        mock_post.return_value = mock_res

        # Call 1: calls remote API
        res1 = client.validate_domain("olfmailer.com")
        assert res1["valid"] is True
        assert res1["cached"] is False
        assert mock_post.call_count == 1

        # Call 2: hits SQLite cache, 0 API calls burned
        res2 = client.validate_domain("olfmailer.com")
        assert res2["valid"] is True
        assert res2["cached"] is True
        assert mock_post.call_count == 1  # Unchanged!


def test_deliverability_verifier_blocks_invalid_domain():
    mock_knowlez = MagicMock()
    mock_knowlez.is_configured = True
    mock_knowlez.validate_domain.return_value = {
        "domain": "broken-fake-tld.invalid999",
        "valid": False,
        "reason": "invalid_tld",
    }

    verifier = DeliverabilityVerifier(
        probe_smtp=False,
        probe_web=False,
        knowlez_client=mock_knowlez,
    )
    is_live, reason = verifier.check_domain_active("broken-fake-tld.invalid999")
    assert is_live is False
    assert "Domain deliverability validation failed" in reason


