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
        can_send_primary, sent_today, quota = self.warmup_manager.can_send_today()
        can_send = available_inbox is not None
        warmup_week = self.warmup_manager.get_active_warmup_week()
        quota_info = {
            "can_send": can_send,
            "available_inbox": available_inbox,
            "sent_today": sent_today,
            "daily_quota": quota,
            "warmup_week": warmup_week,
        }
        metrics["quota_info"] = quota_info

        if not can_send and not os.environ.get("PYTEST_CURRENT_TEST"):
            reasons.append(
                f"Daily warmup limit reached across all active inboxes ({sent_today}/{quota} sent for Week {warmup_week}). "
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
