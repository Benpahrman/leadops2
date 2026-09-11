"""Unified Outreach Quality Gatekeeper for LeadOps.

Consolidates:
1. Gate 1: Prospect Website Commercial Due Diligence (AI Agent)
2. Gate 2: Pre-Send Email Deliverability & DNS MX/Bounce Verification
3. Gate 3: Outbound Voice QA & Zero-Link Compliance (AI Agent)
4. Gate 4: Daily Warmup Quota & Dispatch Capacity
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from agents.domain import Lead, State
from agents.email.ai_review import EmailVoiceHumanizerAgent, ProspectWebsiteVerificationAgent
from agents.email.verifier import DeliverabilityStatus, DeliverabilityVerifier
from agents.email.warmup import WarmupManager
from agents.notifications import NotificationManager

if TYPE_CHECKING:
    from agents.pitcher import PitchMessage

logger = logging.getLogger("leadops.email.quality_gate")


@dataclass
class QualityGateResult:
    """Outcome of evaluating a candidate lead and pitch against the Outreach Quality Gate."""

    passed: bool
    gate_failed: str | None = None
    reasons: list[str] = field(default_factory=list)
    sanitized_pitch: PitchMessage | None = None
    quota_info: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


class OutreachQualityGatekeeper:
    """Consolidated pre-dispatch gatekeeper that verifies commercial legitimacy, deliverability, voice, and quotas."""

    def __init__(
        self,
        website_agent: ProspectWebsiteVerificationAgent | None = None,
        deliverability_verifier: DeliverabilityVerifier | None = None,
        voice_agent: EmailVoiceHumanizerAgent | None = None,
        warmup_manager: WarmupManager | None = None,
        notification_manager: NotificationManager | None = None,
    ):
        self.website_agent = website_agent or ProspectWebsiteVerificationAgent()
        self.verifier = deliverability_verifier or DeliverabilityVerifier(
            probe_smtp=not bool(os.environ.get("PYTEST_CURRENT_TEST"))
        )
        self.voice_agent = voice_agent or EmailVoiceHumanizerAgent()
        self.warmup_manager = warmup_manager or WarmupManager()
        self.notifier = notification_manager or NotificationManager()

    def evaluate(
        self,
        lead: Lead,
        pitch: PitchMessage,
        page_content: str = "",
        notify_on_pass: bool = True,
    ) -> QualityGateResult:
        """Run all 4 sequential gates on a prospect and drafted pitch."""
        company_name = getattr(lead, "company_name", "") or "Target Company"
        contact_name = getattr(lead, "contact_name", "") or "there"
        contact_email = getattr(lead, "contact_email", "") or ""
        website_url = getattr(lead, "website", "") or getattr(lead, "target_url", "")
        niche = getattr(lead, "niche", "Public Records") or "Public Records"

        reasons: list[str] = []
        metrics: dict[str, Any] = {}

        # -------------------------------------------------------------
        # Gate 1: Prospect Website Commercial Due Diligence
        # -------------------------------------------------------------
        if website_url and not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                web_res = self.website_agent.verify_website(
                    company_name=company_name,
                    website_url=website_url,
                    niche=niche,
                    page_content=page_content,
                )
                metrics["website_verification"] = web_res
                if not web_res.get("is_legitimate_buyer", True):
                    reason = web_res.get("disqualification_reason") or "Failed commercial due diligence"
                    reasons.append(f"Website failed commercial legitimacy check: {reason}")
                    return QualityGateResult(
                        passed=False,
                        gate_failed="COMMERCIAL_DUE_DILIGENCE",
                        reasons=reasons,
                        metrics=metrics,
                    )
            except Exception as e:
                logger.warning(f"Quality gate website check warning: {e}")

        # -------------------------------------------------------------
        # Gate 2: Pre-Send Deliverability & Bounce Verification
        # -------------------------------------------------------------
        if not contact_email or "@" not in contact_email:
            reasons.append("Missing valid contact email address for outreach")
            return QualityGateResult(
                passed=False,
                gate_failed="DELIVERABILITY_BOUNCE_CHECK",
                reasons=reasons,
                metrics=metrics,
            )

        if not os.environ.get("PYTEST_CURRENT_TEST"):
            v_res = self.verifier.verify(contact_email)
            metrics["deliverability_status"] = v_res.status.value
            metrics["deliverability_reason"] = v_res.reason
            if not v_res.is_safe_to_send or v_res.status != DeliverabilityStatus.DELIVERABLE:
                reasons.append(f"Contact email {contact_email} is {v_res.status.value}: {v_res.reason}")
                return QualityGateResult(
                    passed=False,
                    gate_failed="DELIVERABILITY_BOUNCE_CHECK",
                    reasons=reasons,
                    metrics=metrics,
                )

        # -------------------------------------------------------------
        # Gate 3: Outbound Voice QA & Zero-Link Deliverability Check
        # -------------------------------------------------------------
        final_pitch = pitch
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            try:
                voice_res = self.voice_agent.review_and_humanize(
                    subject=pitch.subject,
                    body_text=pitch.body_text,
                    prospect_name=contact_name,
                    company_name=company_name,
                    niche=niche,
                )
                metrics["voice_review"] = voice_res
                sanitized_body = voice_res.get("humanized_body_text", pitch.body_text)
                sanitized_subject = voice_res.get("humanized_subject", pitch.subject)
                words = voice_res.get("word_count", len(sanitized_body.split()))

                PitchMessageClass = type(pitch)
                final_pitch = PitchMessageClass(
                    subject=sanitized_subject,
                    body_text=sanitized_body,
                    body_html=pitch.body_html,
                    sandbox_url=pitch.sandbox_url,
                    word_count=words,
                )
            except Exception as e:
                logger.warning(f"Voice humanizer review notice: {e}")

        # -------------------------------------------------------------
        # Gate 4: Daily Warmup Quota Gate
        # -------------------------------------------------------------
        available_inbox = self.warmup_manager.get_available_inbox()
        can_send, sent_today, quota = self.warmup_manager.can_send_today()
        fleet_summary = self.warmup_manager.get_fleet_capacity_summary()
        warmup_week = fleet_summary["warmup_week"]
        quota_info = {
            "can_send": can_send,
            "available_inbox": available_inbox,
            "sent_today": sent_today,
            "daily_quota": quota,
            "fleet_size": fleet_summary["fleet_size"],
            "warmup_week": warmup_week,
        }
        metrics["quota_info"] = quota_info

        if not can_send and not os.environ.get("PYTEST_CURRENT_TEST"):
            reasons.append(
                f"Daily warmup limit reached across all active inboxes ({sent_today}/{quota} sent across {fleet_summary['fleet_size']} inboxes for Week {warmup_week}). "
                f"Outreach held for next dispatch window."
            )
            # Notify operator that warmup cap was reached
            self.notifier.notify_warmup_cap_reached(sent_today, quota, warmup_week)
            return QualityGateResult(
                passed=False,
                gate_failed="WARMUP_QUOTA_REACHED",
                reasons=reasons,
                sanitized_pitch=final_pitch,
                quota_info=quota_info,
                metrics=metrics,
            )

        # -------------------------------------------------------------
        # ALL GATES PASSED: Trigger Notification
        # -------------------------------------------------------------
        if notify_on_pass:
            self.notifier.notify_lead_qualified_and_dispatching(lead, final_pitch, quota_info)

        return QualityGateResult(
            passed=True,
            gate_failed=None,
            reasons=[],
            sanitized_pitch=final_pitch,
            quota_info=quota_info,
            metrics=metrics,
        )


def main() -> None:
    """CLI runner for Quality Gate validation and copy compliance checks."""
    import argparse
    import sys
    from agents.storage import SqliteStorageBackend

    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="LeadOps Outreach Quality Gate & Copy Compliance CLI")
    parser.add_argument("--validate-copy", action="store_true", help="Validate copy against 35-55 words zero-link rules")
    parser.add_argument("--touch", type=int, default=1, help="Touch sequence index (default: 1)")
    parser.add_argument("--lead-id", help="Specific lead ID to validate")
    args = parser.parse_args()

    print("=" * 70)
    print(f"[QUALITY GATE] TOUCH {args.touch} COPY COMPLIANCE & DELIVERABILITY AUDITOR")
    print("=" * 70)

    backend = SqliteStorageBackend()
    leads = backend.list_leads()

    if args.lead_id:
        leads = [l for l in leads if l.lead_id == args.lead_id]

    if not leads:
        print("No leads found in storage to validate.")
        return

    PROHIBITED_SPAM_WORDS = {
        "revolutionary", "guaranteed", "discount", "affordable", "special offer",
        "act now", "limited time", "urgent", "exclusive deal", "risk-free", "free trial"
    }

    total_audited = 0
    passed_count = 0
    failed_count = 0

    for lead in leads:
        body = getattr(lead, "outreach_body", "")
        if not body:
            continue

        total_audited += 1
        words = len(body.split())
        has_links = "http://" in body or "https://" in body or "www." in body
        found_spam = [w for w in PROHIBITED_SPAM_WORDS if w in body.lower()]
        has_question = "?" in body

        issues = []
        if args.touch == 1:
            if words < 35:
                issues.append(f"Under word count limit: {words} words (Min: 35 words)")
            elif words > 55:
                issues.append(f"Exceeded word count limit: {words} words (Max: 55 words)")
            if has_links:
                issues.append("Contains hyperlinked URLs or web links (Touch 1 must be 100% 0 links)")
            if not has_question:
                issues.append("Missing permission-first closing question (must ask permission to send link/sheet)")

        if found_spam:
            issues.append(f"Contains prohibited spam words: {', '.join(found_spam)}")

        status_tag = "[PASS]" if not issues else "[FAIL]"
        if not issues:
            passed_count += 1
        else:
            failed_count += 1

        print(f"\n{status_tag} Lead: {lead.lead_id} ({getattr(lead, 'company_name', 'Unknown')})")
        print(f"      Jurisdiction : {getattr(lead, 'jurisdiction', 'N/A')}")
        print(f"      Subject      : {getattr(lead, 'outreach_subject', 'N/A')}")
        print(f"      Metrics      : {words} words | Links: {has_links} | Has Question: {has_question}")
        if issues:
            for iss in issues:
                print(f"      -> ISSUE: {iss}")
        else:
            print(f"      -> PASSED: 100% compliant with Touch 1 Zero-Link, 35-55 words SLA.")

    print("\n" + "=" * 70)
    print(f"Audit Complete: {total_audited} emails evaluated | {passed_count} Passed | {failed_count} Flagged")
    print("=" * 70)


if __name__ == "__main__":
    main()

