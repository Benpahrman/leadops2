"""Unit and integration tests for the Enterprise Deliverability & Inbox Placement Suite and Admin API Endpoints."""

import os
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from agents.email.config import EmailSettings, InboxAccountConfig
from agents.email.deliverability_suite import (
    DeliverabilitySuite,
    DnsMatrixAuditor,
    RblBlacklistScanner,
    ContentSpamAuditor,
    MultiProviderPlacementProbe,
    DnsAuthVector,
    RblBlacklistVector,
    ContentSpamVector,
    ProviderPlacementVector,
    get_deliverability_suite,
)
from agents.storage import InMemoryStorageBackend, SqliteStorageBackend
from agents.api import create_app


@pytest.fixture
def mock_inbox():
    return InboxAccountConfig(
        id="olf_ben",
        email_address="ben@olfmailer.com",
        password="test-password",
        provider="olfmailer",
        from_name="Ben | LeadOps",
    )


def test_content_spam_auditor_zero_link_policy():
    """Verify zero-link policy is enforced strictly."""
    auditor = ContentSpamAuditor()
    subject = "morning docket records for your jurisdiction"
    body = (
        "Hi there,\n\n"
        "Our automated scraper indexed today's morning public records and filings "
        "for your target jurisdiction into a clean spreadsheet.\n\n"
        "Would it be helpful if I passed over the sample dataset so your team can review it?\n\n"
        "Best,\nAlex\nOmniLeadFeeder"
    )
    res = auditor.analyze_copy(subject, body)
    assert res.zero_link_passed is True
    assert res.link_count == 0
    assert res.score >= 90.0
    assert res.status == "PASS"


def test_content_spam_auditor_flags_links():
    """Verify links in body are caught and penalize score."""
    auditor = ContentSpamAuditor()
    subject = "Special Offer"
    body = "Click here https://example.com to view records now!"
    res = auditor.analyze_copy(subject, body)
    assert res.zero_link_passed is False
    assert res.link_count == 1
    assert any("Remove all 1 hyperlink" in r for r in res.recommendations)


def test_rbl_blacklist_scanner_pristine():
    """Verify RBL scanner marks clean domains as PRISTINE."""
    scanner = RblBlacklistScanner(timeout=1.0)
    with patch.object(scanner, "_query_rbl") as mock_q:
        mock_q.return_value = {
            "rbl_name": "Spamhaus ZEN",
            "rbl_host": "zen.spamhaus.org",
            "impact": "critical",
            "is_listed": False,
            "return_code": "",
            "status": "CLEAN",
        }
        res = scanner.scan_target("olfmailer.com")
        assert res.listed_count == 0
        assert res.status == "PRISTINE"
        assert res.score == 100.0


def test_rbl_blacklist_scanner_listed():
    """Verify RBL scanner marks listed domains as LISTED."""
    scanner = RblBlacklistScanner(timeout=1.0)
    with patch.object(scanner, "_query_rbl") as mock_q:
        mock_q.return_value = {
            "rbl_name": "Spamhaus ZEN",
            "rbl_host": "zen.spamhaus.org",
            "impact": "critical",
            "is_listed": True,
            "return_code": "127.0.0.2",
            "status": "LISTED",
        }
        res = scanner.scan_target("127.0.0.2")
        assert res.listed_count > 0
        assert res.status == "LISTED"


def test_sqlite_deliverability_persistence(tmp_path):
    """Verify deliverability report persistence and retrieval in SQLite."""
    db_path = tmp_path / "test_deliv.db"
    suite = DeliverabilitySuite(domain="olfmailer.com", db_path=db_path)

    suite.dns_auditor.audit_domain = MagicMock(return_value=DnsAuthVector(
        domain="olfmailer.com",
        spf_status="PASS",
        spf_record="v=spf1 ~all",
        spf_lookup_count=1,
        spf_details="Valid",
        dkim_status="PASS",
        dkim_selectors=[],
        dkim_details="Valid",
        dmarc_status="PASS",
        dmarc_record="v=DMARC1; p=quarantine;",
        dmarc_policy="quarantine",
        dmarc_details="Valid",
        mx_status="PASS",
        mx_records=["mx.example.com"],
        mx_details="Valid",
        ptr_status="PASS",
        ptr_record="Valid",
        score=100.0,
        recommendations=[],
    ))
    suite.rbl_scanner.scan_target = MagicMock(return_value=RblBlacklistVector(
        target_ip_or_domain="olfmailer.com",
        total_scanned=12,
        listed_count=0,
        clean_count=12,
        status="PRISTINE",
        rbl_results=[],
        score=100.0,
        details="Clean",
    ))
    suite.content_auditor.analyze_copy = MagicMock(return_value=ContentSpamVector(
        subject="test",
        word_count=40,
        link_count=0,
        links_found=[],
        zero_link_passed=True,
        spam_score=0.0,
        spam_triggers_found=[],
        reading_grade="Grade 7",
        has_tracking_pixels=False,
        header_compliance={},
        score=100.0,
        status="PASS",
        recommendations=[],
    ))
    suite.placement_prober.evaluate_providers = MagicMock(return_value=ProviderPlacementVector(
        google_status="DELIVERABLE",
        microsoft_status="DELIVERABLE",
        corporate_status="DELIVERABLE",
        acs_port443_status="OPERATIONAL",
        average_latency_ms=35,
        probes_summary=[],
        score=100.0,
        status="PRISTINE",
    ))

    report = suite.run_full_audit()
    assert report.composite_score == 100.0
    assert report.tier == "PRISTINE"

    saved = suite.get_latest_saved_report()
    assert saved is not None
    assert saved["domain"] == "olfmailer.com"
    assert saved["composite_score"] == 100.0


def test_admin_deliverability_api_endpoints(monkeypatch):
    """Test comprehensive deliverability endpoints in FastAPI admin routes."""
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

    # 1. GET /api/admin/deliverability/status
    res = client.get("/api/admin/deliverability/status")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "report" in data

    # 2. POST /api/admin/deliverability/content-audit
    content_res = client.post(
        "/api/admin/deliverability/content-audit",
        json={
            "subject": "morning docket filings",
            "body": "Hi there,\n\nWe pulled today's public docket filings. Would you like a copy?\n\nBest,\nAlex",
        },
    )
    assert content_res.status_code == 200
    content_data = content_res.json()
    assert content_data["ok"] is True
    assert content_data["result"]["zero_link_passed"] is True
    assert content_data["result"]["status"] == "PASS"

    # 3. POST /api/admin/deliverability/rbl-check
    rbl_res = client.post(
        "/api/admin/deliverability/rbl-check",
        json={"target": "olfmailer.com"},
    )
    assert rbl_res.status_code == 200
    rbl_data = rbl_res.json()
    assert rbl_data["ok"] is True
    assert "status" in rbl_data["result"]
