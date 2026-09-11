"""Unit and integration tests for Morning Deliverability & TestMail Spam Assessment Subsystem."""

import os
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from agents.email.config import EmailSettings, InboxAccountConfig
from agents.email.client import EmailClient
from agents.email.deliverability_tester import DeliverabilityTester
from agents.storage import InMemoryStorageBackend, SqliteStorageBackend
from agents.api import create_app


@pytest.fixture
def mock_inbox():
    return InboxAccountConfig(
        id="zoho_test",
        email_address="alex.clientops@getyomnileadfeeder.cyou",
        password="test-password",
        provider="zoho",
        from_name="Alex | OmniLeadFeeder",
    )


def test_generate_cold_email_probe(mock_inbox):
    tester = DeliverabilityTester()
    probe = tester.generate_cold_email_probe(mock_inbox)

    assert "subject" in probe
    assert "body" in probe
    assert probe["sender_email"] == "alex.clientops@getyomnileadfeeder.cyou"

    body = probe["body"]
    words = body.split()
    # LeadOps swarm rule: 35-55 words
    assert 30 <= len(words) <= 65, f"Probe word count {len(words)} outside target range"

    # Zero-link rule
    assert "http://" not in body
    assert "https://" not in body
    assert ".com" not in body
    assert "www." not in body

    # Permission-first hook
    assert "?" in body
    assert "Alex" in body


def test_evaluate_inbox_health_healthy(mock_inbox):
    tester = DeliverabilityTester()
    send_result = {"ok": True, "latency_ms": 250}
    testmail_data = {
        "SPF": "pass",
        "dkim": "pass",
        "spam": "-0.5",
        "spam_report": "Content analysis details: -0.5 points",
        "date": 1726040000000,
    }

    eval_res = tester.evaluate_inbox_health(mock_inbox, testmail_data, send_result)
    assert eval_res["status"] == "HEALTHY"
    assert eval_res["score"] >= 95
    assert "pass" in eval_res["spf"]
    assert "pass" in eval_res["dkim"]
    assert eval_res["spam_score"] == -0.5
    assert eval_res["received_in_testmail"] is True


def test_evaluate_inbox_health_dkim_warning(mock_inbox):
    tester = DeliverabilityTester()
    send_result = {"ok": True, "latency_ms": 300}
    testmail_data = {
        "SPF": "pass",
        "dkim": "none",
        "spam": "0.1",
        "spam_report": "DKIM missing",
        "date": 1726040000000,
    }

    eval_res = tester.evaluate_inbox_health(mock_inbox, testmail_data, send_result)
    assert eval_res["status"] == "WARNING"
    assert eval_res["score"] < 95
    assert "DKIM missing" in eval_res["diagnostic"] or "DKIM" in eval_res["diagnostic"]


def test_evaluate_inbox_health_send_failure(mock_inbox):
    tester = DeliverabilityTester()
    send_result = {"ok": False, "error": "SMTPAuthenticationError: 535 Authentication Failed", "latency_ms": 120}

    eval_res = tester.evaluate_inbox_health(mock_inbox, None, send_result)
    assert eval_res["status"] == "CRITICAL"
    assert eval_res["score"] == 0
    assert eval_res["received_in_testmail"] is False
    assert "Authentication Failed" in eval_res["spam_report"]


def test_storage_persistence_in_memory():
    storage = InMemoryStorageBackend()
    report = {
        "run_id": "AUDIT-12345",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "fleet_status": "HEALTHY",
        "average_score": 98.5,
        "inbox_count": 5,
        "healthy_count": 5,
        "warning_count": 0,
        "critical_count": 0,
        "inboxes": [
            {"email_address": "alex@getyomnileadfeeder.cyou", "status": "HEALTHY", "score": 100}
        ],
    }

    storage.save_deliverability_audit(report)
    latest = storage.get_latest_deliverability_audit()

    assert latest is not None
    assert latest["run_id"] == "AUDIT-12345"
    assert latest["fleet_status"] == "HEALTHY"
    assert latest["average_score"] == 98.5
    assert len(latest["inboxes"]) == 1

    audits = storage.list_deliverability_audits(limit=5)
    assert len(audits) == 1


def test_storage_persistence_sqlite(tmp_path):
    db_path = str(tmp_path / "test_deliv.db")
    storage = SqliteStorageBackend(db_path=db_path)

    report = {
        "run_id": "AUDIT-SQLITE-999",
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "fleet_status": "WARNING",
        "average_score": 82.0,
        "inbox_count": 2,
        "healthy_count": 1,
        "warning_count": 1,
        "critical_count": 0,
        "inboxes": [
            {"email_address": "chris.founder@getyomnileadfeeder.cyou", "status": "HEALTHY", "score": 95},
            {"email_address": "alex.sales@getyomnileadfeeder.cyou", "status": "WARNING", "score": 75},
        ],
    }

    storage.save_deliverability_audit(report)
    latest = storage.get_latest_deliverability_audit()

    assert latest is not None
    assert latest["run_id"] == "AUDIT-SQLITE-999"
    assert latest["fleet_status"] == "WARNING"
    assert latest["average_score"] == 82.0
    assert len(latest["inboxes"]) == 2


def test_run_fleet_audit_mocked_transports(monkeypatch, mock_inbox):
    storage = InMemoryStorageBackend()
    settings = EmailSettings(inbox_pool=[mock_inbox])

    # Mock EmailClient transport hook to avoid live network
    client = EmailClient(settings=settings)
    client.transport_hook = lambda payload: {"ok": True, "message_id": "test-msg-123"}

    tester = DeliverabilityTester(
        settings=settings,
        email_client=client,
        storage_backend=storage,
    )

    # Mock fetch_testmail_report to return valid SPF/DKIM payload
    monkeypatch.setattr(
        tester,
        "fetch_testmail_report",
        lambda tag, **kwargs: {
            "SPF": "pass",
            "dkim": "pass",
            "spam": "0.0",
            "spam_report": "Clean test payload",
            "date": 1726040000000,
        },
    )

    report = tester.run_fleet_audit(force=True, wait_seconds=0)

    assert report["ok"] is True
    assert report["fleet_status"] == "HEALTHY"
    assert report["healthy_count"] == 1
    assert report["warning_count"] == 0
    assert len(report["inboxes"]) == 1
    assert report["inboxes"][0]["email_address"] == mock_inbox.email_address

    # Verify persisted in storage
    stored = storage.get_latest_deliverability_audit()
    assert stored is not None
    assert stored["run_id"] == report["run_id"]


def test_admin_deliverability_api_endpoints(monkeypatch):
    storage = InMemoryStorageBackend()
    app = create_app(storage=storage)
    client = TestClient(app)

    # Bypass Clerk admin authentication in test
    from agents.auth import ClerkUser
    app.dependency_overrides = {}
    from agents.routes.admin import require_admin
    app.dependency_overrides[require_admin] = lambda: ClerkUser(
        user_id="user_admin",
        email="admin@leadops.io",
        is_admin=True,
    )

    # 1. Initial status with no audits yet
    res = client.get("/api/admin/deliverability/status")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["report"]["fleet_status"] in ("PENDING_AUDIT", "HEALTHY", "WARNING")

    # 2. Trigger on-demand audit in synchronous wait mode with mocked tester
    def mock_run_fleet_audit(self, inboxes=None, force=False):
        return {
            "ok": True,
            "run_id": "AUDIT-MOCK-API",
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "fleet_status": "HEALTHY",
            "average_score": 100.0,
            "inbox_count": 1,
            "healthy_count": 1,
            "warning_count": 0,
            "critical_count": 0,
            "inboxes": [{"email_address": "test@domain.com", "status": "HEALTHY", "score": 100}],
        }

    monkeypatch.setattr(DeliverabilityTester, "run_fleet_audit", mock_run_fleet_audit)

    trigger_res = client.post(
        "/api/admin/deliverability/run-audit",
        json={"force": True, "wait": True},
    )
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.json()
    assert trigger_data["ok"] is True
    assert trigger_data["report"]["run_id"] == "AUDIT-MOCK-API"
    assert trigger_data["report"]["fleet_status"] == "HEALTHY"
