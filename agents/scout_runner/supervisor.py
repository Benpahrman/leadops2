"""Scout automation supervisor managing continuous discovery cycles, office hours, and rate limits."""

import asyncio
import os
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from agents.domain import State
from agents.portal import PortalService
from agents.storage import StorageBackend
from agents.llm_client import LLMAgentEngine
from agents.office_hours import is_office_hours

logger = logging.getLogger("leadops.scout.supervisor")


@dataclass
class ScoutAutomationSupervisor:
    """Runs bounded scout batches and exposes operator-visible activity state."""

    storage: StorageBackend
    portal: PortalService
    llm_engine: LLMAgentEngine = field(default_factory=LLMAgentEngine)
    target_per_cycle: int = 1
    min_rest_seconds: int = 3600
    max_rest_seconds: int = 7200
    enabled: bool = True
    is_running: bool = False
    run_24_7: bool = True
    _task: asyncio.Task | None = None
    _status: dict[str, Any] = field(default_factory=lambda: {
        "phase": "STOPPED",
        "message": "Scout automation has not started",
        "cycle": 0,
        "qualified_this_cycle": 0,
        "target_per_cycle": 1,
        "attempts_this_cycle": 0,
        "last_result": None,
        "last_error": None,
        "last_activity_at": None,
        "next_run_at": None,
        "run_24_7": True,
    })

    def __post_init__(self) -> None:
        def _clean_int(val: Any, default: int) -> int:
            try:
                return int(str(val).split("#")[0].strip().strip("\"'"))
            except (ValueError, TypeError):
                return default

        if "SCOUT_MIN_REST_SECONDS" in os.environ:
            self.min_rest_seconds = _clean_int(os.environ["SCOUT_MIN_REST_SECONDS"], self.min_rest_seconds)
        if "SCOUT_MAX_REST_SECONDS" in os.environ:
            self.max_rest_seconds = _clean_int(os.environ["SCOUT_MAX_REST_SECONDS"], self.max_rest_seconds)
        if "SCOUT_TARGET_PER_CYCLE" in os.environ:
            self.target_per_cycle = _clean_int(os.environ["SCOUT_TARGET_PER_CYCLE"], self.target_per_cycle)
        if "SCOUT_24_7_MODE" in os.environ or "SCOUT_RUN_24_7" in os.environ:
            val = os.environ.get("SCOUT_24_7_MODE", os.environ.get("SCOUT_RUN_24_7", "true")).lower()
            self.run_24_7 = val in ("true", "1", "yes")

    def status(self) -> dict[str, Any]:
        stat = dict(self._status)
        is_open, wait_sec, status_msg = is_office_hours()
        stat["is_office_hours"] = is_open
        stat["office_hours_status"] = status_msg
        stat["seconds_until_office_window"] = wait_sec
        stat["run_24_7"] = self.run_24_7
        return stat

    def set_24_7_mode(self, enabled: bool) -> dict[str, Any]:
        """Dynamically toggle 24/7 all-day scouting mode."""
        self.run_24_7 = bool(enabled)
        self._status["run_24_7"] = self.run_24_7
        logger.info(f"⚡ [SCOUT SUPERVISOR] 24/7 All-Day Mode set to: {self.run_24_7}")
        return self.status()

    def start(self) -> None:
        if self.enabled and not self.is_running:
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        self.is_running = True
        self._status.update({
            "phase": "IDLE",
            "message": "Scout automation is online",
            "target_per_cycle": self.target_per_cycle,
            "run_24_7": self.run_24_7,
        })
        try:
            while self.is_running:
                is_open, wait_seconds, status_msg = is_office_hours()
                self._status["is_office_hours"] = is_open
                self._status["run_24_7"] = self.run_24_7

                if not self.run_24_7 and not is_open:
                    next_run_dt = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)
                    self._status.update({
                        "phase": "STANDBY_OFFICE_HOURS",
                        "message": status_msg,
                        "next_run_at": next_run_dt.isoformat(),
                        "last_activity_at": datetime.now(timezone.utc).isoformat(),
                    })
                    logger.info(f"🌙 [SCOUT OFFICE HOURS] {status_msg} Standing by until 8:00 AM window.")
                    sleep_chunk = min(wait_seconds, 300)
                    await asyncio.sleep(sleep_chunk)
                    continue

                if not is_open:
                    logger.info(f"⚡ [SCOUT 24/7 ALL-DAY ACTIVE] Prospecting outside standard office hours ({status_msg}).")

                # Check if daily email sending capacity is exhausted across all inboxes.
                from agents.email.warmup import WarmupManager
                from agents.email.config import EmailSettings
                warmup_mgr = WarmupManager(settings=EmailSettings.from_environment(), storage_backend=self.storage)
                available_inbox = warmup_mgr.get_available_inbox()

                if not available_inbox:
                    logger.info("📭 [SCOUT] Daily email quota saturated — continuing discovery (outreach will queue for tomorrow)")
                    self._status.update({
                        "phase": "DISCOVERING_NO_DISPATCH",
                        "message": "Daily email quota full. Still discovering leads — outreach queued for tomorrow morning.",
                        "last_activity_at": datetime.now(timezone.utc).isoformat(),
                    })

                # Autonomous copywriter sweep: ensure leads in State.REVIEW have pitch copy generated & scheduled
                try:
                    import threading
                    from agents.auto_outreach import auto_outreach_scheduler
                    from agents.notifications import notification_manager
                    threading.Thread(
                        target=auto_outreach_scheduler.auto_prepare_review_pitches,
                        args=(self.storage, notification_manager, self.llm_engine),
                        daemon=True,
                        name="auto-prepare-review-pitches",
                    ).start()
                except Exception as prep_err:
                    logger.debug(f"Auto-prepare review pitches trigger note: {prep_err}")

                # Check pending review/dispatch queue backlog
                try:
                    max_pending = int(str(os.environ.get("SCOUT_MAX_PENDING_QUEUE", "200")).split("#")[0].strip().strip("\"'"))
                except (ValueError, TypeError):
                    max_pending = 200
                if self.storage and hasattr(self.storage, "list_leads"):
                    leads = self.storage.list_leads()
                    pending_count = sum(1 for l in leads if l.state in (State.PITCH_PENDING_APPROVAL, State.REVIEW))
                    if pending_count >= max_pending:
                        self._status.update({
                            "phase": "STANDBY_QUEUE_FULL",
                            "message": f"Pending outreach queue has {pending_count} leads waiting for dispatch (max: {max_pending}). Pausing discovery.",
                            "next_run_at": (datetime.now(timezone.utc) + timedelta(seconds=300)).isoformat(),
                            "last_activity_at": datetime.now(timezone.utc).isoformat(),
                        })
                        logger.info(f"⏸️ [SCOUT QUEUE BACKLOG] {pending_count} leads pending in approval queue. Standing by.")
                        await asyncio.sleep(300)
                        continue

                # When office hours open, dispatch any cold outreach pitches held overnight in background thread
                try:
                    import threading
                    from agents.auto_outreach import auto_outreach_scheduler
                    from agents.notifications import notification_manager
                    threading.Thread(
                        target=auto_outreach_scheduler.flush_pending_office_hours_queue,
                        args=(self.storage, notification_manager),
                        daemon=True,
                        name="office-hours-flush",
                    ).start()
                except Exception as flush_err:
                    logger.debug(f"Office hours outreach queue flush note: {flush_err}")

                await self._run_cycle()
                rest_seconds = random.randint(self.min_rest_seconds, self.max_rest_seconds)
                next_run = datetime.now(timezone.utc).timestamp() + rest_seconds
                self._status.update({
                    "phase": "RESTING",
                    "message": f"Cycle complete; resting for {rest_seconds // 60} minutes",
                    "next_run_at": datetime.fromtimestamp(next_run, timezone.utc).isoformat(),
                    "last_activity_at": datetime.now(timezone.utc).isoformat(),
                })
                await asyncio.sleep(rest_seconds)
        except asyncio.CancelledError:
            self._status.update({"phase": "STOPPED", "message": "Scout automation stopped"})
            raise
        except Exception as exc:
            self._status.update({
                "phase": "ERROR",
                "message": "Scout automation stopped after an unexpected error",
                "last_error": str(exc),
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
            })
            logger.exception("Scout automation supervisor failed")
        finally:
            self.is_running = False

    async def _run_cycle(self) -> None:
        from .worker import ScoutBackgroundWorker

        self._status.update({
            "phase": "SEARCHING",
            "cycle": self._status.get("cycle", 0) + 1,
            "qualified_this_cycle": 0,
            "attempts_this_cycle": 0,
            "last_error": None,
            "next_run_at": None,
        })
        qualified = 0
        attempts = 0
        max_attempts = self.target_per_cycle * 4
        while self.is_running and qualified < self.target_per_cycle and attempts < max_attempts:
            attempts += 1
            self._status.update({
                "phase": "SEARCHING",
                "message": f"Searching and qualifying lead {qualified + 1} of {self.target_per_cycle}",
                "attempts_this_cycle": attempts,
                "last_activity_at": datetime.now(timezone.utc).isoformat(),
            })
            try:
                result = await asyncio.to_thread(
                    ScoutBackgroundWorker(
                        storage=self.storage,
                        portal=self.portal,
                        llm_engine=self.llm_engine,
                    ).discover_next_candidate
                )
                if result.get("ok"):
                    qualified += 1
                    self._status.update({
                        "phase": "ENRICHING",
                        "qualified_this_cycle": qualified,
                        "last_result": result,
                        "message": f"Lead qualified and queued for review ({qualified}/{self.target_per_cycle})",
                    })
                else:
                    self._status.update({
                        "phase": "SEARCHING",
                        "last_result": result,
                        "message": result.get("reason", "Candidate rejected; continuing search"),
                    })
            except Exception as exc:
                self._status.update({
                    "phase": "SEARCHING",
                    "last_error": str(exc),
                    "message": "Candidate failed validation; continuing search",
                })
                logger.exception("Scout candidate attempt failed")

        self._status.update({
            "phase": "CYCLE_COMPLETE" if qualified >= self.target_per_cycle else "NEEDS_ATTENTION",
            "qualified_this_cycle": qualified,
            "attempts_this_cycle": attempts,
            "message": (
                f"Queued {qualified} qualified leads for founder review"
                if qualified >= self.target_per_cycle
                else f"Only {qualified} qualified leads found after {attempts} attempts"
            ),
            "last_activity_at": datetime.now(timezone.utc).isoformat(),
        })
