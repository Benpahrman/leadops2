"""Unit and integration tests for the Enterprise Deliverability & Inbox Placement Suite."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from agents.email.deliverability_suite import (
    DnsMatrixAuditor,
    RblBlacklistScanner,
    ContentSpamAuditor,
    MultiProviderPlacementProbe,
    DeliverabilitySuite,
    get_deliverability_suite,
    DnsAuthVector,
    RblBlacklistVector,
    ContentSpamVector,
    ProviderPlacementVector,
    ComprehensiveDeliverabilityReport,
)
from agents.email.config import EmailSettings


def test_content_spam_auditor_zero_link_pass():
    """Verify clean outreach copy passes with 0 links and high score."""
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
    assert res.word_count >= 25
    assert len(res.spam_triggers_found) == 0


def test_content_spam_auditor_flags_links_and_spam_keywords():
    """Verify copy with forbidden links and aggressive spam triggers is penalized."""
    auditor = ContentSpamAuditor()
    subject = "FREE MONEY! Act now to earn extra cash guaranteed"
    body = (
        "Click here now https://spamlink.com to double your income! "
        "You have been selected for free money and 100% free cash bonus. "
        "No risk! Wire transfer immediately!"
    )
    res = auditor.analyze_copy(subject, body)
    assert res.zero_link_passed is False
    assert res.link_count >= 1
    assert res.status == "FLAGGED"
    assert res.score < 60.0
    assert len(res.spam_triggers_found) > 0
    # Check that recommendations were generated
    assert any("Remove" in r for r in res.recommendations)


def test_rbl_scanner_clean_target():
    """Verify RBL scanner against a mock or live target."""
    scanner = RblBlacklistScanner(timeout=1.5)
    # Using mock to test logic deterministically
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


def test_rbl_scanner_listed_target():
    """Verify RBL scanner flags listed IPs/domains."""
    scanner = RblBlacklistScanner(timeout=1.5)
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
        assert res.score < 100.0


def test_dns_matrix_auditor_mock():
    """Verify DNS matrix evaluation with mock TXT and CNAME resolution."""
    auditor = DnsMatrixAuditor()
    with patch.object(auditor, "resolve_txt_records") as mock_txt, \
         patch.object(auditor, "resolve_cname") as mock_cname, \
         patch.object(auditor, "resolve_mx") as mock_mx:

        mock_txt.side_effect = lambda domain: (
            ["v=spf1 include:spf.protection.outlook.com ~all"] if not domain.startswith("_dmarc")
            else ["v=DMARC1; p=quarantine; pct=100;"]
        )
        mock_cname.return_value = "selector1-azurecomm-prod-net.azurecomm.net"
        mock_mx.return_value = ["mx1.cloudflare.net"]

        res = auditor.audit_domain("olfmailer.com")
        assert res.spf_status == "PASS"
        assert res.dmarc_status == "PASS"
        assert res.dkim_status == "PASS"
        assert res.mx_status == "PASS"
        assert res.score >= 90.0


def test_provider_placement_probe():
    """Verify provider placement vector generation."""
    settings = MagicMock(spec=EmailSettings)
    settings.is_azure_communication_ready.return_value = True
    prober = MultiProviderPlacementProbe(settings=settings)
    res = prober.evaluate_providers()
    assert res.google_status == "DELIVERABLE"
    assert res.microsoft_status == "DELIVERABLE"
    assert res.acs_port443_status == "OPERATIONAL"
    assert res.score >= 90.0


def test_deliverability_suite_end_to_end(tmp_path):
    """Verify full 4-vector suite execution, scoring, and sqlite persistence."""
    test_db = tmp_path / "test_email.db"
    suite = DeliverabilitySuite(domain="olfmailer.com", db_path=test_db)

    # Mock vectors for fast deterministic unit testing
    suite.dns_auditor.audit_domain = MagicMock(return_value=DnsAuthVector(
        domain="olfmailer.com",
        spf_status="PASS",
        spf_record="v=spf1 include:spf.protection.outlook.com ~all",
        spf_lookup_count=2,
        spf_details="Valid",
        dkim_status="PASS",
        dkim_selectors=[{"selector": "sel1", "valid": True}],
        dkim_details="Valid 2048-bit",
        dmarc_status="PASS",
        dmarc_record="v=DMARC1; p=quarantine;",
        dmarc_policy="quarantine",
        dmarc_details="Valid",
        mx_status="PASS",
        mx_records=["mx1.cloudflare.net"],
        mx_details="Valid",
        ptr_status="PASS",
        ptr_record="Verified",
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
        word_count=45,
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
        average_latency_ms=45,
        probes_summary=[],
        score=100.0,
        status="PRISTINE",
    ))

    report = suite.run_full_audit()
    assert report.composite_score == 100.0
    assert report.tier == "PRISTINE"

    # Verify SQLite caching
    saved = suite.get_latest_saved_report()
    assert saved is not None
    assert saved["domain"] == "olfmailer.com"
    assert saved["composite_score"] == 100.0
    assert saved["tier"] == "PRISTINE"
