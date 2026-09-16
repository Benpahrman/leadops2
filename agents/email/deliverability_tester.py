"""Enterprise Deliverability & Placement Audit Adapter.

Provides backward-compatible interface delegating to the 4-vector DeliverabilitySuite.
Audits DNS matrix, 12 Global RBLs, AI Zero-Link compliance, and Multi-provider placement.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from .config import EmailSettings, InboxAccountConfig
from .deliverability_suite import DeliverabilitySuite, get_deliverability_suite

logger = logging.getLogger("leadops.email.deliverability_tester")


class DeliverabilityTester:
    """Automated 4-vector deliverability probe engine for multi-inbox fleet auditing."""

    def __init__(
        self,
        api_key: str | None = None,
        namespace: str | None = None,
        settings: EmailSettings | None = None,
        email_client: Any = None,
        storage_backend: Any = None,
        notifier: Any = None,
    ) -> None:
        self.settings = settings or EmailSettings.from_environment()
        self.storage = storage_backend
        self.notifier = notifier
        self.domain = "olfmailer.com"
        self.suite = get_deliverability_suite(self.domain)

    def generate_cold_email_probe(self, inbox: InboxAccountConfig) -> dict[str, str]:
        """Synthesize a realistic B2B cold email conforming to zero-link plain-text rules."""
        sender_name = inbox.from_name or self.settings.from_name or "Alex | OmniLeadFeeder"
        display_first = sender_name.split("|")[0].split()[0].strip() or "Alex"

        subject = "morning docket records for your jurisdiction"
        body = (
            f"Hi there,\n\n"
            f"Our automated scraper indexed today's morning public records and filings "
            f"for your target jurisdiction into a clean spreadsheet.\n\n"
            f"Would it be helpful if I passed over the sample dataset so your team can review it?\n\n"
            f"Best,\n"
            f"{display_first}\n"
            f"OmniLeadFeeder Automated Swarm"
        )

        return {
            "subject": subject,
            "body": body,
            "sender_name": sender_name,
            "sender_email": inbox.email_address,
        }

    def run_fleet_audit(
        self,
        inboxes: list[InboxAccountConfig] | None = None,
        force: bool = False,
        wait_seconds: int = 0,
    ) -> dict[str, Any]:
        """Execute 4-vector deliverability diagnostic audit across domain fleet."""
        now_iso = datetime.now(timezone.utc).isoformat()
        run_id = f"AUDIT-{int(time.time())}"

        target_inboxes = inboxes or self.settings.inbox_pool
        inbox_addrs = [ib.email_address for ib in target_inboxes] if target_inboxes else [self.settings.user or "ben@olfmailer.com"]

        report = self.suite.run_full_audit()

        per_inbox_reports = [
            {
                "inbox_id": addr.replace("@", "_").replace(".", "_"),
                "email_address": addr,
                "status": "HEALTHY" if report.composite_score >= 80 else "WARNING",
                "score": int(report.composite_score),
                "spf": report.dns_vector.spf_status,
                "dkim": report.dns_vector.dkim_status,
                "spam_score": report.content_vector.spam_score,
                "diagnostic": f"DNS: {report.dns_vector.spf_status}/{report.dns_vector.dkim_status} | 12 RBLs: {report.rbl_vector.listed_count} listed | Zero-Link: {report.content_vector.zero_link_passed}",
            }
            for addr in inbox_addrs
        ]

        fleet_status = "HEALTHY" if report.composite_score >= 90 else "WARNING" if report.composite_score >= 70 else "CRITICAL"

        full_report: dict[str, Any] = {
            "ok": True,
            "run_id": run_id,
            "audited_at": now_iso,
            "fleet_status": fleet_status,
            "average_score": report.composite_score,
            "inbox_count": len(per_inbox_reports),
            "healthy_count": len(per_inbox_reports) if fleet_status == "HEALTHY" else 0,
            "warning_count": len(per_inbox_reports) if fleet_status == "WARNING" else 0,
            "critical_count": len(per_inbox_reports) if fleet_status == "CRITICAL" else 0,
            "inboxes": per_inbox_reports,
            "comprehensive_report": asdict(report),
        }

        # Save to storage if available
        if self.storage and hasattr(self.storage, "save_deliverability_audit"):
            try:
                self.storage.save_deliverability_audit(full_report)
            except Exception as store_err:
                logger.warning(f"Could not persist deliverability audit: {store_err}")

        return full_report
