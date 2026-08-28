import pytest

from agents.domain import Lead, State
from agents.drift_monitor import DriftIncident, DriftSeverity, RetainerMonitorWorker
from agents.tools.waf_prober import AntiBotBlockException


def test_drift_monitor_detects_schema_drift():
    monitor = RetainerMonitorWorker()
    lead = Lead("lead-warranty-1", "daily", state=State.WARRANTY_ACTIVE)

    # Source missing 'county' field
    def mock_fetcher():
        return [{"case_number": "100", "filing_date": "2026-08-27"}]

    incident = monitor.inspect_feed(
        lead=lead,
        source_url="https://court.example.gov",
        expected_fields=["case_number", "filing_date", "county"],
        test_fetcher=mock_fetcher,
    )

    assert incident is not None
    assert incident.issue_type == "schema_drift"
    assert incident.severity == DriftSeverity.HIGH
    assert "county" in incident.details
    assert incident.repair_ticket_opened is True
    assert len(lead.audit_log) == 1


def test_drift_monitor_detects_zero_rows():
    monitor = RetainerMonitorWorker()
    lead = Lead("lead-warranty-2", "weekly", state=State.WARRANTY_ACTIVE)

    incident = monitor.inspect_feed(
        lead=lead,
        source_url="https://portal.example.gov",
        expected_fields=["id", "name"],
        test_fetcher=lambda: [],
    )

    assert incident is not None
    assert incident.issue_type == "zero_rows_returned"
    assert incident.severity == DriftSeverity.CRITICAL


def test_drift_monitor_detects_waf_blocking():
    monitor = RetainerMonitorWorker()
    lead = Lead("lead-warranty-3", "daily", state=State.WARRANTY_ACTIVE)

    def mock_blocking_fetcher():
        raise AntiBotBlockException(waf_type="Cloudflare", status_code=403, details="Cloudflare Turnstile challenge")

    incident = monitor.inspect_feed(
        lead=lead,
        source_url="https://protected.gov",
        expected_fields=["col1"],
        test_fetcher=mock_blocking_fetcher,
    )

    assert incident is not None
    assert incident.issue_type == "waf_blocked"
    assert incident.severity == DriftSeverity.CRITICAL
    assert "Cloudflare" in incident.details


def test_drift_monitor_healthy_feed():
    monitor = RetainerMonitorWorker()
    lead = Lead("lead-healthy", "ai", state=State.WARRANTY_ACTIVE)

    def healthy_fetcher():
        return [{"case_number": "A-1", "filing_date": "2026-08-27", "county": "Cook"}]

    incident = monitor.inspect_feed(
        lead=lead,
        source_url="https://court.example.gov",
        expected_fields=["case_number", "filing_date", "county"],
        test_fetcher=healthy_fetcher,
    )

    assert incident is None
    assert len(monitor.incidents) == 0
