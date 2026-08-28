"""Retainer Monitor worker for automated schema drift and selector health monitoring."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from .domain import Lead, State
from .tools.waf_prober import AntiBotBlockException


class DriftSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class DriftIncident:
    incident_id: str
    lead_id: str
    target_url: str
    issue_type: str
    severity: DriftSeverity
    details: str
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "OPEN"
    repair_ticket_opened: bool = True


class RetainerMonitorWorker:
    """Monitors live client feeds in warranty/retainer to detect drift before daily delivery."""

    def __init__(self) -> None:
        self.incidents: list[DriftIncident] = []

    def inspect_feed(
        self,
        lead: Lead,
        source_url: str,
        expected_fields: list[str],
        test_fetcher: Callable[[], list[dict[str, Any]]],
    ) -> DriftIncident | None:
        """Run non-destructive test probe on a feed to verify selector and schema integrity."""
        # Feeds eligible for drift monitoring: WARRANTY_ACTIVE, DELIVERED, or active subscriptions
        if lead.state not in {State.WARRANTY_ACTIVE, State.DELIVERED} and not lead.subscription_active:
            return None

        incident = None
        try:
            sample_rows = test_fetcher()
            if not sample_rows:
                incident = DriftIncident(
                    incident_id=f"inc-{uuid.uuid4().hex[:8]}",
                    lead_id=lead.lead_id,
                    target_url=source_url,
                    issue_type="zero_rows_returned",
                    severity=DriftSeverity.CRITICAL,
                    details="Source returned 0 records during pre-delivery health check.",
                )
            else:
                observed_fields = set(sample_rows[0].keys())
                missing_expected = set(expected_fields) - observed_fields
                if missing_expected:
                    incident = DriftIncident(
                        incident_id=f"inc-{uuid.uuid4().hex[:8]}",
                        lead_id=lead.lead_id,
                        target_url=source_url,
                        issue_type="schema_drift",
                        severity=DriftSeverity.HIGH,
                        details=f"Missing expected schema fields: {sorted(missing_expected)}",
                    )
        except AntiBotBlockException as e:
            incident = DriftIncident(
                incident_id=f"inc-{uuid.uuid4().hex[:8]}",
                lead_id=lead.lead_id,
                target_url=source_url,
                issue_type="waf_blocked",
                severity=DriftSeverity.CRITICAL,
                details=str(e),
            )
        except Exception as e:
            incident = DriftIncident(
                incident_id=f"inc-{uuid.uuid4().hex[:8]}",
                lead_id=lead.lead_id,
                target_url=source_url,
                issue_type="broken_selector_or_network_error",
                severity=DriftSeverity.HIGH,
                details=f"Fetch failed with error: {e}",
            )

        if incident:
            self.incidents.append(incident)
            lead.audit_log.append({
                "from": lead.state.value,
                "to": lead.state.value,
                "reason": f"Drift incident detected: {incident.issue_type} ({incident.severity.value})",
                "at": datetime.now(timezone.utc).isoformat(),
            })

        return incident

    def run_pre_delivery_health_checks(
        self,
        leads: list[Lead],
        feed_sources: dict[str, tuple[str, list[str], Callable[[], list[dict[str, Any]]]]],
    ) -> list[DriftIncident]:
        """Runs health checks for all eligible retainer clients before 6:00 AM UTC deadline."""
        opened_incidents = []
        for lead in leads:
            if lead.lead_id in feed_sources:
                source_url, expected_fields, fetcher = feed_sources[lead.lead_id]
                inc = self.inspect_feed(lead, source_url, expected_fields, fetcher)
                if inc:
                    opened_incidents.append(inc)
        return opened_incidents
