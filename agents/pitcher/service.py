"""Outbound Pitcher service coordinating approvals, deliverability checks, warmup quotas, and dispatch."""

import os
import random
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from agents.domain import Lead, State
from agents.email.client import EmailClient
from agents.email.verifier import DeliverabilityVerifier
from agents.email.warmup import WarmupManager
from .models import PitchMessage
from .freshness import ensure_fresh_records_for_lead

logger = logging.getLogger("leadops.pitcher.service")


class PitcherService:
    """Coordinates outreach approvals, bounce verification, warmup quotas, voice QA, notifications, and Gmail dispatch."""

    def __init__(
        self,
        sendpulse_client: Any = None,
        email_client: EmailClient | None = None,
        opt_out_emails: set[str] | None = None,
        warmup_manager: WarmupManager | None = None,
        deliverability_verifier: DeliverabilityVerifier | None = None,
        storage_backend: Any = None,
        notification_manager: Any = None,
        quality_gatekeeper: Any = None,
    ) -> None:
        self.client = email_client or sendpulse_client or EmailClient()
        self.opt_outs = opt_out_emails or set()
        self.storage = storage_backend
        self.storage_backend = storage_backend
        self.warmup_manager = warmup_manager or WarmupManager(storage_backend=storage_backend)
        self.verifier = deliverability_verifier or DeliverabilityVerifier(probe_smtp=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
        self.sent_log: list[dict[str, Any]] = []

        from agents.notifications import NotificationManager
        from agents.email.quality_gate import OutreachQualityGatekeeper

        self.notifier = notification_manager or NotificationManager()
        self.quality_gate = quality_gatekeeper or OutreachQualityGatekeeper(
            deliverability_verifier=self.verifier,
            warmup_manager=self.warmup_manager,
            notification_manager=self.notifier,
        )

    def record_opt_out(self, email: str) -> None:
        self.opt_outs.add(email.lower().strip())

    def is_opted_out(self, email: str) -> bool:
        return email.lower().strip() in self.opt_outs

    def evaluate_quality_gate(
        self,
        lead: Lead,
        pitch: PitchMessage,
        page_content: str = "",
        notify_on_pass: bool = True,
    ) -> Any:
        """Run all quality gates: commercial due diligence, MX bounce check, voice QA, and warmup capacity."""
        return self.quality_gate.evaluate(
            lead=lead,
            pitch=pitch,
            page_content=page_content,
            notify_on_pass=notify_on_pass,
        )

    def approve_and_dispatch(
        self,
        lead: Lead,
        recipient_email: str,
        recipient_name: str,
        pitch: PitchMessage,
        human_approver: str = "Autonomous AI Engine",
        enforce_office_hours: bool = False,
        force_out_of_hours: bool = False,
        enforce_deliverability: bool | None = None,
    ) -> dict[str, Any]:
        """Verify opt-out, deliverability, warmup quota, voice alignment, and dispatch email."""
        if human_approver == "":
            require_human = os.environ.get("LEADOPS_REQUIRE_HUMAN_APPROVAL", "false").lower() == "true"
            if require_human:
                raise ValueError("Human approval is required for outbound pitch dispatch")

        approver = human_approver.strip() if (human_approver and human_approver.strip()) else "Autonomous AI Engine"
        if not getattr(lead, "contact_email", ""):
            lead.contact_email = recipient_email
        if not getattr(lead, "contact_name", ""):
            lead.contact_name = recipient_name

        # 0. Office hours check for outbound cold outreach (8:00 AM - 5:00 PM CST Mon-Fri)
        should_enforce_hours = (
            enforce_office_hours
            or os.environ.get("ENFORCE_OUTREACH_OFFICE_HOURS", "true").lower() in ("1", "true", "yes")
        )
        if should_enforce_hours and not force_out_of_hours:
            from agents.scout_runner import is_office_hours
            is_open, seconds_until_open, msg = is_office_hours()
            if not is_open:
                raise ValueError(
                    f"Outbound cold outreach sending is restricted to office hours (8:00 AM - 5:00 PM CST Mon-Fri). {msg}"
                )

        def _persist_archive():
            if self.storage_backend:
                try:
                    if hasattr(self.storage_backend, "save_lead"):
                        self.storage_backend.save_lead(lead)
                    elif hasattr(self.storage_backend, "update_lead"):
                        self.storage_backend.update_lead(lead)
                except Exception as save_err:
                    logger.warning(f"Failed to persist lead archival: {save_err}")

        # 1. Opt-out suppression check
        if self.is_opted_out(recipient_email):
            lead.transition(State.ARCHIVED, "Prospect opted out of communications")
            _persist_archive()
            raise ValueError(f"Recipient {recipient_email} is on the opt-out suppression list")

        # 1b. Anti-duplicate suppression check (45-day cooldown per domain/company/recipient)
        if self.storage_backend and hasattr(self.storage_backend, "is_recipient_or_domain_contacted"):
            if self.storage_backend.is_recipient_or_domain_contacted(
                email=recipient_email,
                domain=getattr(lead, "website", ""),
                company_name=getattr(lead, "company_name", ""),
                within_days=45,
                exclude_lead_id=lead.lead_id,
            ):
                lead.transition(State.ARCHIVED, f"Recipient {recipient_email} or company {lead.company_name} already contacted within 45 days")
                _persist_archive()
                raise ValueError(f"Recipient {recipient_email} / {lead.company_name} was already contacted within 45 days (anti-duplicate suppression)")

        # 1c. Smart Deliverability Pre-Flight Check & Caching
        try:
            from agents.email.knowlez_client import get_knowlez_client
            knowlez = get_knowlez_client()
            should_check = enforce_deliverability if enforce_deliverability is not None else not bool(os.environ.get("PYTEST_CURRENT_TEST"))
            if should_check and (getattr(lead, "deliverability_score", None) is None or not getattr(lead, "deliverability_checked_at", "")):
                deliv_res = knowlez.verify_email(recipient_email, force=False)
                lead.deliverability_score = deliv_res.get("score")
                lead.deliverability_status = deliv_res.get("status") or ("DELIVERABLE" if deliv_res.get("valid") else "UNDELIVERABLE")
                lead.deliverability_checked_at = deliv_res.get("checked_at") or datetime.now(timezone.utc).isoformat()
                lead.email_provider = deliv_res.get("provider") or "other"
                lead.email_mx_hosts = deliv_res.get("mx_hosts", [])
                _persist_archive()

            # Hard bounce shield: reject if score < 60 or explicitly undeliverable
            if getattr(lead, "deliverability_score", None) is not None:
                if lead.deliverability_score < 60 or getattr(lead, "deliverability_status", "") in ("UNDELIVERABLE", "RISKY"):
                    reason_msg = getattr(lead, "deliverability_status", "UNDELIVERABLE")
                    lead.transition(State.ARCHIVED, f"Deliverability check rejected email {recipient_email} (score {lead.deliverability_score}, status: {reason_msg})")
                    _persist_archive()
                    raise ValueError(f"Recipient {recipient_email} rejected by pre-flight deliverability shield: score {lead.deliverability_score} ({reason_msg})")
        except ValueError:
            raise
        except Exception as deliv_err:
            logger.warning(f"Pre-flight deliverability auto-check notice: {deliv_err}")

        # 1d. Pre-Outreach Same-Day Freshness Gate (<24h stale check & micro-scrape refresh)
        try:
            from agents.portal import PortalService
            portal_svc = PortalService(storage=self.storage_backend) if self.storage_backend else None
            freshness_res = ensure_fresh_records_for_lead(
                lead=lead,
                portal_service=portal_svc,
                storage_backend=self.storage_backend,
                max_age_hours=24,
            )
            if freshness_res.get("refreshed"):
                logger.info(
                    f"🔄 [PRE-DISPATCH FRESHNESS] Injected {freshness_res.get('record_count')} fresh same-day filings "
                    f"into sandbox {freshness_res.get('slug')} before dispatch."
                )
        except Exception as fresh_err:
            logger.debug(f"Pre-dispatch freshness check notice: {fresh_err}")

        # 2. Run Unified Outreach Quality Gatekeeper
        gate_res = self.quality_gate.evaluate(lead=lead, pitch=pitch, notify_on_pass=False)
        if not gate_res.passed:
            if gate_res.gate_failed == "DELIVERABILITY_BOUNCE_CHECK":
                reason = gate_res.metrics.get("deliverability_reason", "undeliverable")
                lead.transition(State.ARCHIVED, f"Email {recipient_email} failed deliverability check: {reason}")
                _persist_archive()
                raise ValueError(f"Recipient {recipient_email} failed pre-send deliverability check: {reason}")
            elif gate_res.gate_failed == "WARMUP_QUOTA_REACHED":
                quota = gate_res.quota_info.get("daily_quota", 25)
                sent_today = gate_res.quota_info.get("sent_today", 0)
                raise ValueError(
                    f"Daily warmup dispatch quota of {quota} emails reached for today ({sent_today}/{quota} dispatched). "
                    f"Email held for next dispatch window."
                )
            elif gate_res.gate_failed == "COMMERCIAL_DUE_DILIGENCE":
                lead.transition(State.ARCHIVED, "Website failed commercial due diligence")
                _persist_archive()
                raise ValueError(f"Prospect failed commercial due diligence gate")
            else:
                raise ValueError(f"Outreach Quality Gate failed: {'; '.join(gate_res.reasons)}")

        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "Scout candidate reviewed")
        if lead.state == State.REVIEW:
            lead.transition(State.PITCH_PENDING_APPROVAL, "Pitch queued for autonomous dispatch")

        if lead.state != State.PITCH_PENDING_APPROVAL:
            raise ValueError(f"Lead must be in PITCH_PENDING_APPROVAL state (current: {lead.state.value})")

        final_pitch = gate_res.sanitized_pitch or pitch
        final_subject = final_pitch.subject
        final_body = final_pitch.body_text

        # 3. Provider routing alignment & inbox selection
        provider = getattr(lead, "email_provider", "") or "other"
        if provider == "microsoft":
            logger.info(f"🎯 [PROVIDER ALIGNMENT] Recipient {recipient_email} is Microsoft 365 / Outlook. Using Microsoft / Azure Communication Services aligned identity.")
        elif provider == "google":
            logger.info(f"🎯 [PROVIDER ALIGNMENT] Recipient {recipient_email} is Google Workspace / Gmail. Standardizing SPF/DKIM headers for Google anti-spam filters.")
        else:
            logger.info(f"🎯 [PROVIDER ALIGNMENT] Recipient {recipient_email} uses {provider} mail server.")

        chosen_inbox = None
        if hasattr(self.warmup_manager, "get_available_inbox_account"):
            chosen_inbox = self.warmup_manager.get_available_inbox_account(check_jitter=True) or self.warmup_manager.get_available_inbox_account(check_jitter=False)
        inbox_id = chosen_inbox.id if chosen_inbox else (self.warmup_manager.get_available_inbox() or "primary")

        send_result = self.client.send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=final_subject,
            text_body=final_body,
            html_body=final_pitch.body_html,
            inbox=chosen_inbox,
        )

        # Only count towards warmup quota if an actual email was transmitted (not dry-run simulation)
        is_simulated = isinstance(send_result, dict) and send_result.get("status") in ("SIMULATED_DISPATCH_FROZEN", "SIMULATED_NO_CREDENTIALS")
        if not is_simulated:
            self.warmup_manager.record_send(inbox_id=inbox_id, recipient=recipient_email, lead_id=lead.lead_id)
        else:
            logger.info(f"ℹ️ [WARMUP QUOTA] Skipped recording send for simulated dispatch on inbox '{inbox_id}'.")
        
        # Enforce per-inbox 5-20 min jitter cooldown for this specific account
        try:
            min_j = int(str(os.environ.get("AUTO_OUTREACH_MIN_JITTER_SECONDS", "300")).split("#")[0].strip().strip("\"'"))
        except (ValueError, TypeError):
            min_j = 300
        try:
            max_j = int(str(os.environ.get("AUTO_OUTREACH_MAX_JITTER_SECONDS", "1200")).split("#")[0].strip().strip("\"'"))
        except (ValueError, TypeError):
            max_j = 1200
        jitter_dur = 0.01 if os.environ.get("PYTEST_CURRENT_TEST") else random.uniform(min_j, max_j)
        if hasattr(self.warmup_manager, "record_inbox_jitter"):
            self.warmup_manager.record_inbox_jitter(inbox_id, jitter_dur)

        provider_desc = f"{chosen_inbox.provider.title()} [{chosen_inbox.email_address}]" if chosen_inbox else f"SMTP [{inbox_id}]"
        lead.transition(State.OUTREACH_SENT, f"Pitch dispatched via {provider_desc} (approved by: {approver})")

        # Multi-touch sequencer initialization for Touch 1
        msg_id = ""
        if isinstance(send_result, dict):
            msg_id = str(send_result.get("id") or send_result.get("message_id") or "")
        elif hasattr(send_result, "message_id"):
            msg_id = str(getattr(send_result, "message_id"))
        if not msg_id:
            import uuid
            msg_id = f"<leadops-{lead.lead_id}-{uuid.uuid4().hex[:10]}@olfmailer.com>"

        lead.outreach_thread_id = msg_id
        lead.outreach_touch_count = 1
        now_dt = datetime.now(timezone.utc)
        lead.last_outreach_at = now_dt.isoformat()
        lead.next_outreach_at = (now_dt + timedelta(hours=72)).isoformat()
        lead.outreach_replied = False

        if self.storage_backend and hasattr(self.storage_backend, "save_lead"):
            self.storage_backend.save_lead(lead)

        # 4. Notify operator via Discord and Telegram
        self.notifier.notify_lead_qualified_and_dispatching(
            lead=lead,
            pitch=final_pitch,
            quota_info=gate_res.quota_info,
        )

        log_entry = {
            "lead_id": lead.lead_id,
            "recipient_email": recipient_email,
            "subject": final_subject,
            "approver": approver,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "sendpulse_result": send_result,
            "email_result": send_result,
        }
        self.sent_log.append(log_entry)
        return log_entry
