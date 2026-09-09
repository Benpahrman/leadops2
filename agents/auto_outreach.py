"""Auto-Outreach Grace Period Scheduler & Anti-Spam Jitter Engine.

Provides autonomous cold outreach with human oversight:
1. When a lead is scouted and passes all quality gates, it initiates a 3-minute (180s) grace period.
2. The operator receives an organized Discord/Telegram notification with the complete email draft.
3. The operator can 1-tap [🛑 Cancel / Reject] or [⚡ Send Immediately].
4. If no cancellation is received after 3 minutes, the scheduler verifies office hours (8:00 AM - 5:00 PM CST)
   and applies randomized anti-spam human jitter (90-240s) between successive emails before dispatching.
"""

from __future__ import annotations

import logging
import os
import random
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import logging
import os
import queue
import random
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from .domain import Lead, State
from .scout_runner import is_office_hours

logger = logging.getLogger("leadops.auto_outreach")


class AutoOutreachScheduler:
    """Coordinates grace-period timers, mobile cancellation, FIFO sequential queue, and 5-20 min anti-spam jitter."""

    def __init__(
        self,
        grace_period_seconds: int = 180,
        min_jitter_seconds: int = 300,
        max_jitter_seconds: int = 1200,
    ) -> None:
        def _clean_int(val: Any, default: int) -> int:
            try:
                return int(str(val).split("#")[0].strip().strip("\"'"))
            except (ValueError, TypeError):
                return default

        self.grace_period_seconds = _clean_int(
            os.environ.get("AUTO_OUTREACH_GRACE_PERIOD_SECONDS", grace_period_seconds),
            grace_period_seconds,
        )
        self.min_jitter_seconds = _clean_int(
            os.environ.get("AUTO_OUTREACH_MIN_JITTER_SECONDS", min_jitter_seconds),
            min_jitter_seconds,
        )
        self.max_jitter_seconds = _clean_int(
            os.environ.get("AUTO_OUTREACH_MAX_JITTER_SECONDS", max_jitter_seconds),
            max_jitter_seconds,
        )
        self._lock = threading.Lock()
        self._scheduled: dict[str, dict[str, Any]] = {}
        self._dispatch_queue: queue.Queue = queue.Queue()
        self._worker_thread: threading.Thread | None = None
        self._worker_running: bool = False
        self._last_dispatch_time: float = 0.0

    def _ensure_worker_running(self) -> None:
        """Start single background worker thread if not already running."""
        with self._lock:
            if not self._worker_running or self._worker_thread is None or not self._worker_thread.is_alive():
                self._worker_running = True
                self._worker_thread = threading.Thread(target=self._dispatch_worker_loop, daemon=True)
                self._worker_thread.start()
                logger.debug("⚡ [AUTO-OUTREACH QUEUE] Dispatch worker thread initialized.")

    @property
    def is_enabled(self) -> bool:
        """Check if automatic outreach grace-period mode is active."""
        val = os.environ.get("AUTO_OUTREACH_ENABLED", "true").lower().strip()
        return val in ("1", "true", "yes", "on", "active")

    def set_enabled(self, enabled: bool) -> None:
        os.environ["AUTO_OUTREACH_ENABLED"] = "true" if enabled else "false"

    def schedule_lead_for_dispatch(
        self,
        lead: Lead,
        pitch: Any,
        storage_backend: Any,
        notifier: Any = None,
    ) -> dict[str, Any]:
        """Register lead in the 3-minute grace period queue."""
        lead_id = lead.lead_id
        now_dt = datetime.now(timezone.utc)
        dispatch_at = now_dt + timedelta(seconds=self.grace_period_seconds)

        lead.auto_dispatch_at = dispatch_at.isoformat()
        if hasattr(storage_backend, "save_lead"):
            storage_backend.save_lead(lead)

        with self._lock:
            # Cancel any pre-existing timer for this lead
            if lead_id in self._scheduled and self._scheduled[lead_id].get("timer"):
                try:
                    self._scheduled[lead_id]["timer"].cancel()
                except Exception:
                    pass

            timer = threading.Timer(
                self.grace_period_seconds,
                self._on_grace_period_expired,
                args=[lead_id, storage_backend, notifier],
            )
            timer.daemon = True

            self._scheduled[lead_id] = {
                "lead_id": lead_id,
                "company_name": getattr(lead, "company_name", ""),
                "contact_email": getattr(lead, "contact_email", ""),
                "scheduled_at": now_dt.isoformat(),
                "dispatch_at": dispatch_at.isoformat(),
                "cancelled": False,
                "dispatched": False,
                "queued": False,
                "timer": timer,
            }

            if self.is_enabled:
                timer.start()
                logger.info(
                    f"⏱️ [AUTO-OUTREACH QUEUED] Lead {lead_id} ({lead.company_name}) scheduled for auto-dispatch in {self.grace_period_seconds}s at {dispatch_at.isoformat()}."
                )

        return {
            "ok": True,
            "lead_id": lead_id,
            "grace_period_seconds": self.grace_period_seconds,
            "dispatch_at": dispatch_at.isoformat(),
            "auto_outreach_active": self.is_enabled,
        }

    def cancel_dispatch(self, lead_id: str, reason: str = "Operator cancelled via mobile") -> bool:
        """Cancel a pending scheduled outreach within the 3-minute grace period."""
        with self._lock:
            entry = self._scheduled.get(lead_id)
            if not entry:
                logger.debug(f"Auto-outreach cancel requested for unscheduled lead: {lead_id}")
                return False

            entry["cancelled"] = True
            if entry.get("timer"):
                try:
                    entry["timer"].cancel()
                except Exception:
                    pass

            logger.info(f"🛑 [AUTO-OUTREACH CANCELLED] Lead {lead_id} cancelled. Reason: {reason}")
            return True

    def is_pending(self, lead_id: str) -> bool:
        with self._lock:
            entry = self._scheduled.get(lead_id)
            if not entry:
                return False
            return not entry.get("cancelled") and not entry.get("dispatched")

    def _on_grace_period_expired(self, lead_id: str, storage_backend: Any, notifier: Any) -> None:
        """Callback executed when the 3-minute timer fires: pushes lead to sequential FIFO dispatch queue."""
        with self._lock:
            entry = self._scheduled.get(lead_id)
            if not entry or entry.get("cancelled") or entry.get("dispatched") or entry.get("queued"):
                return
            entry["queued"] = True

        self._dispatch_queue.put((lead_id, storage_backend, notifier))
        self._ensure_worker_running()
        logger.info(f"📥 [DISPATCH QUEUE] Lead {lead_id} enqueued in FIFO dispatch queue (Queue depth: {self._dispatch_queue.qsize()}).")

    def _dispatch_worker_loop(self) -> None:
        """Single dedicated FIFO worker thread: processes one email at a time with 5-30 min jitter."""
        while self._worker_running:
            try:
                item = self._dispatch_queue.get(timeout=3.0)
            except queue.Empty:
                continue

            lead_id, storage_backend, notifier = item
            try:
                self._process_single_queued_dispatch(lead_id, storage_backend, notifier)
            except Exception as e:
                logger.error(f"❌ [DISPATCH QUEUE ERROR] Failed dispatch for {lead_id}: {e}")
            finally:
                self._dispatch_queue.task_done()

    def _process_single_queued_dispatch(self, lead_id: str, storage_backend: Any, notifier: Any) -> None:
        """Execute dispatch sequentially for a single lead."""
        with self._lock:
            entry = self._scheduled.get(lead_id)
            if entry and (entry.get("cancelled") or entry.get("dispatched")):
                logger.info(f"⏭️ [DISPATCH QUEUE] Lead {lead_id} cancelled or already dispatched. Skipping.")
                return

        lead = storage_backend.get_lead(lead_id) if hasattr(storage_backend, "get_lead") else None
        if not lead:
            logger.warning(f"Auto-outreach worker encountered missing lead: {lead_id}")
            return

        if lead.state != State.PITCH_PENDING_APPROVAL:
            logger.info(f"Auto-outreach skipped for lead {lead_id}: State is {lead.state.value}.")
            return

        # Check 45-day anti-duplicate suppression
        if storage_backend and hasattr(storage_backend, "is_recipient_or_domain_contacted"):
            if storage_backend.is_recipient_or_domain_contacted(
                email=lead.contact_email,
                domain=getattr(lead, "website", ""),
                company_name=getattr(lead, "company_name", ""),
                within_days=45,
                exclude_lead_id=lead.lead_id,
            ):
                logger.info(f"🛑 [AUTO-OUTREACH SUPPRESSION] {lead.company_name} / {lead.contact_email} was contacted within 45 days. Skipping duplicate.")
                lead.transition(State.ARCHIVED, "Duplicate outreach suppressed (contacted within 45 days)")
                if hasattr(storage_backend, "save_lead"):
                    storage_backend.save_lead(lead)
                return

        # Verify Office Hours (8:00 AM - 5:00 PM CST)
        while True:
            is_open, seconds_until_open, msg = is_office_hours()
            if is_open:
                break
            logger.info(f"🌙 [AUTO-OUTREACH PAUSED] Outside office hours. Waiting until 8:00 AM CST ({seconds_until_open}s) before dispatching {lead.company_name}...")
            sleep_chunk = min(seconds_until_open, 300)
            time.sleep(sleep_chunk)

        # Verify daily sending capacity across inboxes
        from .email.warmup import WarmupManager
        from .email.config import EmailSettings
        warmup_mgr = WarmupManager(settings=EmailSettings.from_environment(), storage_backend=storage_backend)
        if not warmup_mgr.get_available_inbox(check_jitter=False):
            logger.info(f"🛑 [AUTO-OUTREACH HELD] Daily send limit reached on all inboxes. Holding {lead.company_name} for tomorrow.")
            return

        # Wait until an inbox finishes its per-inbox 5-30m jitter cooldown
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        while not is_test:
            ready_inbox = warmup_mgr.get_available_inbox(check_jitter=True)
            if ready_inbox:
                break
            earliest_wait = warmup_mgr.get_earliest_jitter_wait()
            if earliest_wait <= 0:
                break
            logger.info(
                f"⏳ [PER-INBOX JITTER QUEUE] All active inboxes are in 5-30m jitter cooldown. "
                f"Holding {lead.company_name} for {earliest_wait/60:.1f}m ({earliest_wait:.0f}s) until next inbox is ready..."
            )
            time.sleep(min(earliest_wait, 15.0))

        # Enforce Anti-Burst Human Stagger (15-30s between consecutive dispatches to prevent 501 / socket spikes)
        self._enforce_anti_burst_stagger()

        # Re-check cancellation before final dispatch
        with self._lock:
            if entry and entry.get("cancelled"):
                logger.info(f"Auto-outreach for {lead_id} cancelled during jitter wait window.")
                return

        # Perform actual dispatch
        self._execute_dispatch(lead, storage_backend, notifier)

    def _enforce_anti_burst_stagger(self) -> None:
        """Enforce brief human spacing (15 to 30s) between successive emails across the pool to prevent simultaneous bursts."""
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        if is_test:
            return

        now_sec = time.time()
        elapsed_since_last = now_sec - self._last_dispatch_time
        target_stagger = random.uniform(15.0, 30.0)

        if self._last_dispatch_time > 0 and elapsed_since_last < target_stagger:
            wait_sec = target_stagger - elapsed_since_last
            logger.info(f"⚡ [ANTI-BURST STAGGER] Enforcing {wait_sec:.1f}s stagger before dispatching next inbox...")
            time.sleep(wait_sec)

        self._last_dispatch_time = time.time()

    def _enforce_sequential_jitter(self) -> None:
        """Alias for backward-compatibility with tests."""
        self._enforce_anti_burst_stagger()

    def _execute_dispatch(self, lead: Lead, storage_backend: Any, notifier: Any = None) -> None:
        """Dispatch cold outreach pitch via PitcherService."""
        if notifier is None:
            try:
                from .notifications import notification_manager
                notifier = notification_manager
            except Exception:
                notifier = None

        from .pitcher import PitcherService, PitchMessage, render_sub_60_word_pitch

        company = lead.company_name or "Partner"
        recipient_email = (lead.contact_email or "").strip()

        if not recipient_email or "@" not in recipient_email:
            logger.warning(
                f"🛑 [AUTO-OUTREACH ABORTED] Lead {lead.lead_id} has invalid email: '{recipient_email}'."
            )
            return

        slug = getattr(lead, "slug", "") or lead.lead_id
        pitch = None
        if getattr(lead, "outreach_subject", "") and getattr(lead, "outreach_body", ""):
            pitch = PitchMessage(
                subject=lead.outreach_subject,
                body_text=lead.outreach_body,
                body_html=getattr(lead, "outreach_html", "") or f"<p>{lead.outreach_body}</p>",
                sandbox_url=f"https://www.omnileadfeeder.tech/p/{slug}",
                word_count=len(lead.outreach_body.split()),
            )
        else:
            pitch = render_sub_60_word_pitch(
                company_name=company,
                niche=getattr(lead, "niche", "Public Records") or "Public Records",
                portal_name=getattr(lead, "target_portal_name", "Official Records Portal") or "Official Records Portal",
                sample_count=4,
                slug=slug,
                contact_name=(getattr(lead, "contact_name", "") or "there").split()[0],
                contact_role=getattr(lead, "contact_role", ""),
            )
            lead.outreach_subject = pitch.subject
            lead.outreach_body = pitch.body_text
            lead.outreach_html = pitch.body_html

        pitcher = PitcherService(storage_backend=storage_backend)

        try:
            logger.info(
                f"🚀 [AUTO-OUTREACH EXECUTING] 3-minute window elapsed. Dispatching pitch to {recipient_email} ({company}) with subject: '{pitch.subject}'"
            )
            pitcher.approve_and_dispatch(
                lead=lead,
                recipient_email=recipient_email,
                recipient_name=getattr(lead, "contact_name", "") or company,
                pitch=pitch,
                human_approver="Auto-Pilot Grace Period",
                enforce_office_hours=True,
            )
            storage_backend.save_lead(lead)

            with self._lock:
                if lead.lead_id in self._scheduled:
                    self._scheduled[lead.lead_id]["dispatched"] = True

            # Notify Discord of completed automated dispatch
            if notifier:
                try:
                    notifier.notify_system_alert(
                        title=f"🚀 Auto-Outreach Dispatched: {company}",
                        message=f"Cold pitch was automatically dispatched after the 3-minute grace period without rejection.\n\n"
                                f"**To:** `{recipient_email}`\n"
                                f"**Subject:** _{pitch.subject}_\n"
                                f"**State:** `OUTREACH_SENT`",
                        severity="INFO",
                    )
                except Exception as ne:
                    logger.debug(f"Auto-dispatch alert notification note: {ne}")

        except Exception as err:
            logger.warning(
                f"⚠️ [AUTO-OUTREACH GATE REJECTED] Pitch for {lead.lead_id} could not be dispatched: {err}"
            )
            if notifier:
                try:
                    notifier.notify_system_alert(
                        title=f"⚠️ Auto-Outreach Blocked: {company}",
                        message=f"Outreach could not be dispatched for {company} ({recipient_email}):\n\n`{str(err)}`",
                        severity="WARNING",
                    )
                except Exception:
                    pass

    def flush_pending_office_hours_queue(self, storage_backend: Any, notifier: Any = None) -> list[str]:
        """Flush any pending approved pitches when office hours open (8:00 AM - 5:00 PM CST)."""
        if notifier is None:
            try:
                from .notifications import notification_manager
                notifier = notification_manager
            except Exception:
                notifier = None

        is_open, seconds_until_open, msg = is_office_hours()
        if not is_open:
            logger.debug(f"flush_pending_office_hours_queue: Outside office hours ({msg}). Standing by.")
            return []

        if not hasattr(storage_backend, "list_leads"):
            return []

        try:
            leads = storage_backend.list_leads()
        except Exception as e:
            logger.warning(f"Failed to list leads for office hours flush: {e}")
            return []

        pending = [
            l for l in leads
            if l.state == State.PITCH_PENDING_APPROVAL
            and (l.contact_email or "").strip()
            and not getattr(l, "opt_out", False)
        ]

        if not pending:
            return []

        logger.info(
            f"☀️ [OFFICE HOURS FLUSH] Found {len(pending)} pending pitch(es) queued for dispatch. "
            f"Dispatching with human anti-spam jitter ({self.min_jitter_seconds}-{self.max_jitter_seconds}s)..."
        )
        dispatched_ids = []
        for lead in pending:
            with self._lock:
                entry = self._scheduled.get(lead.lead_id)
                if entry and entry.get("cancelled"):
                    logger.info(f"Skipping cancelled lead {lead.lead_id} during queue flush.")
                    continue

            # Verify office hours remain open before sending each successive email
            is_still_open, _, _ = is_office_hours()
            if not is_still_open:
                logger.info("Office hours closed during queue flush. Pausing remainder until next window.")
                break

            # Verify remaining daily quota across inboxes
            from .email.warmup import WarmupManager
            from .email.config import EmailSettings
            warmup_mgr = WarmupManager(settings=EmailSettings.from_environment(), storage_backend=storage_backend)
            if not warmup_mgr.get_available_inbox():
                logger.info("Daily send quota reached across all inboxes during queue flush. Pausing remainder until tomorrow.")
                break

            self._enforce_sequential_jitter()
            try:
                self._execute_dispatch(lead, storage_backend, notifier)
                dispatched_ids.append(lead.lead_id)
            except Exception as exc:
                logger.warning(f"Error during office hours queue flush for {lead.lead_id}: {exc}")

        return dispatched_ids

    def get_status(self) -> dict[str, Any]:
        """Return current status of auto-outreach engine."""
        with self._lock:
            pending_count = sum(
                1 for s in self._scheduled.values() if not s["cancelled"] and not s["dispatched"]
            )
            return {
                "enabled": self.is_enabled,
                "grace_period_seconds": self.grace_period_seconds,
                "min_jitter_seconds": self.min_jitter_seconds,
                "max_jitter_seconds": self.max_jitter_seconds,
                "pending_queue_count": pending_count,
                "queue_depth": self._dispatch_queue.qsize(),
                "total_tracked": len(self._scheduled),
                "scheduled": [
                    {
                        "lead_id": s["lead_id"],
                        "company_name": s["company_name"],
                        "contact_email": s["contact_email"],
                        "dispatch_at": s["dispatch_at"],
                        "cancelled": s["cancelled"],
                        "dispatched": s["dispatched"],
                    }
                    for s in self._scheduled.values()
                ][-10:],
            }


# Global singleton instance
auto_outreach_scheduler = AutoOutreachScheduler()
