"""Autonomous 14-Day High-Volume Work-Hours Prospecting Engine.

Executes high-throughput prospecting during business office hours (8:00 AM - 5:00 PM CST, Mon-Fri)
over a 14-day window to build a vetted, scored, and enriched B2B candidate backlog.
Enforces strict multi-key deduplication and immediately executes the full audit journey.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

from agents.domain import State, Lead
from agents.logging_config import get_logger
from agents.office_hours import is_office_hours, is_scout_24_7_enabled
from agents.portal import PortalService
from agents.storage import StorageBackend, normalize_company_name, normalize_domain

logger = get_logger("prospector")

STATE_FILE = Path("data/high_volume_prospector_state.json")


@dataclass
class ProspectorCampaignMetrics:
    total_evaluated: int = 0
    duplicates_blocked: int = 0
    duplicates_by_reason: dict[str, int] = field(default_factory=lambda: {
        "DUPLICATE_COMPANY": 0,
        "DUPLICATE_DOMAIN": 0,
        "DUPLICATE_EMAIL": 0,
        "GLOBAL_SUPPRESSION": 0,
        "RECENTLY_CONTACTED_45D": 0,
    })
    deliverability_passed: int = 0
    deliverability_failed: int = 0
    websites_verified: int = 0
    sandboxes_created: int = 0
    qualified_backlog_count: int = 0
    last_lead_discovered: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_evaluated": self.total_evaluated,
            "duplicates_blocked": self.duplicates_blocked,
            "duplicates_by_reason": dict(self.duplicates_by_reason),
            "deliverability_passed": self.deliverability_passed,
            "deliverability_failed": self.deliverability_failed,
            "websites_verified": self.websites_verified,
            "sandboxes_created": self.sandboxes_created,
            "qualified_backlog_count": self.qualified_backlog_count,
            "last_lead_discovered": self.last_lead_discovered,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProspectorCampaignMetrics:
        metrics = cls()
        metrics.total_evaluated = data.get("total_evaluated", 0)
        metrics.duplicates_blocked = data.get("duplicates_blocked", 0)
        metrics.duplicates_by_reason = data.get("duplicates_by_reason", {
            "DUPLICATE_COMPANY": 0,
            "DUPLICATE_DOMAIN": 0,
            "DUPLICATE_EMAIL": 0,
            "GLOBAL_SUPPRESSION": 0,
            "RECENTLY_CONTACTED_45D": 0,
        })
        metrics.deliverability_passed = data.get("deliverability_passed", 0)
        metrics.deliverability_failed = data.get("deliverability_failed", 0)
        metrics.websites_verified = data.get("websites_verified", 0)
        metrics.sandboxes_created = data.get("sandboxes_created", 0)
        metrics.qualified_backlog_count = data.get("qualified_backlog_count", 0)
        metrics.last_lead_discovered = data.get("last_lead_discovered")
        return metrics


class HighVolumeProspectorEngine:
    """Orchestrates 14-day high-volume autonomous prospecting during office hours."""

    CHANNELS = ["county_filing_party", "state_bar", "sos_entity", "local_business", "b2b_web_search"]

    def __init__(
        self,
        storage: StorageBackend,
        portal: PortalService,
        campaign_duration_days: int = 14,
        volume_per_cycle: int = 3,
        rest_seconds_min: int = 30,
        rest_seconds_max: int = 90,
    ):
        self.storage = storage
        self.portal = portal
        self.campaign_duration_days = campaign_duration_days
        self.volume_per_cycle = volume_per_cycle
        self.rest_seconds_min = rest_seconds_min
        self.rest_seconds_max = rest_seconds_max

        self.is_active = False
        self._task: asyncio.Task | None = None
        self._lock = threading.Lock()
        self.metrics = ProspectorCampaignMetrics()
        self.run_24_7: bool = is_scout_24_7_enabled()

        self.start_time: datetime = datetime.now(timezone.utc)
        self.end_time: datetime = self.start_time + timedelta(days=campaign_duration_days)
        self.current_phase = "IDLE"
        self.last_status_message = "14-Day High-Volume Prospector ready"
        self.active_channels = list(self.CHANNELS)
        self.channel_index = 0

        self._load_state()

    def _save_state(self) -> None:
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "campaign_duration_days": self.campaign_duration_days,
                "is_active": self.is_active,
                "volume_per_cycle": self.volume_per_cycle,
                "active_channels": self.active_channels,
                "run_24_7": self.run_24_7,
                "metrics": self.metrics.to_dict(),
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            STATE_FILE.write_text(json.dumps(payload, indent=2))
        except Exception as e:
            logger.warning(f"Could not persist high volume prospector state: {e}")

    def _load_state(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            data = json.loads(STATE_FILE.read_text())
            if "start_time" in data:
                self.start_time = datetime.fromisoformat(data["start_time"])
            if "end_time" in data:
                self.end_time = datetime.fromisoformat(data["end_time"])
            self.campaign_duration_days = data.get("campaign_duration_days", 14)
            self.volume_per_cycle = data.get("volume_per_cycle", 3)
            self.active_channels = data.get("active_channels", list(self.CHANNELS))
            if "run_24_7" in data:
                self.run_24_7 = bool(data["run_24_7"])
            if "metrics" in data:
                self.metrics = ProspectorCampaignMetrics.from_dict(data["metrics"])
            logger.info(f"Loaded high-volume prospector state (Campaign: Day {self.current_day} of {self.campaign_duration_days}, 24/7={self.run_24_7})")
        except Exception as e:
            logger.warning(f"Failed to load high volume prospector state: {e}")

    @property
    def current_day(self) -> int:
        now = datetime.now(timezone.utc)
        elapsed = (now - self.start_time).total_seconds()
        day = int(elapsed // 86400) + 1
        return max(1, min(self.campaign_duration_days, day))

    @property
    def days_remaining(self) -> int:
        now = datetime.now(timezone.utc)
        if now >= self.end_time:
            return 0
        rem_sec = (self.end_time - now).total_seconds()
        return max(0, int(rem_sec // 86400) + (1 if rem_sec % 86400 > 0 else 0))

    @property
    def is_campaign_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.end_time

    def get_status(self) -> dict[str, Any]:
        is_open, wait_sec, status_msg = is_office_hours()
        
        # Sync candidate evaluations count and backlog leads from storage
        if hasattr(self.storage, "get_candidate_evaluations_count"):
            try:
                eval_count = self.storage.get_candidate_evaluations_count()
                if eval_count > 0:
                    self.metrics.total_evaluated = max(self.metrics.total_evaluated, eval_count)
            except Exception:
                pass

        if hasattr(self.storage, "list_leads"):
            try:
                leads = self.storage.list_leads()
                if not hasattr(self.storage, "get_candidate_evaluations_count") or self.metrics.total_evaluated == 0:
                    self.metrics.total_evaluated = max(self.metrics.total_evaluated, len(leads))
                backlog_count = sum(
                    1 for l in leads
                    if l.state in (State.REVIEW, State.PITCH_PENDING_APPROVAL, State.PROSPECTING)
                    and getattr(l, "outreach_status", "") == "BACKLOG_VETTED"
                )
                self.metrics.qualified_backlog_count = backlog_count
            except Exception:
                pass

        return {
            "is_active": self.is_active,
            "campaign_duration_days": self.campaign_duration_days,
            "current_day": self.current_day,
            "days_remaining": self.days_remaining,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "is_campaign_expired": self.is_campaign_expired,
            "current_phase": self.current_phase,
            "status_message": self.last_status_message,
            "run_24_7": self.run_24_7,
            "is_office_hours": is_open,
            "office_hours_status": status_msg,
            "seconds_until_office_window": wait_sec,
            "volume_per_cycle": self.volume_per_cycle,
            "active_channels": self.active_channels,
            "metrics": self.metrics.to_dict(),
        }

    def set_24_7_mode(self, enabled: bool) -> dict[str, Any]:
        """Toggle continuous 24/7 all-day prospecting on or off."""
        with self._lock:
            self.run_24_7 = bool(enabled)
            self._save_state()
            logger.info(f"⚡ [HIGH-VOLUME PROSPECTOR] 24/7 All-Day Mode set to: {self.run_24_7}")
            return self.get_status()

    def start_campaign(
        self,
        duration_days: int = 14,
        volume_per_cycle: int = 3,
        channels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Start or restart the 14-day high volume prospecting campaign."""
        with self._lock:
            self.campaign_duration_days = duration_days
            self.volume_per_cycle = max(1, min(volume_per_cycle, 15))
            if channels:
                self.active_channels = [c for c in channels if c in self.CHANNELS] or list(self.CHANNELS)
            self.start_time = datetime.now(timezone.utc)
            self.end_time = self.start_time + timedelta(days=duration_days)
            self.is_active = True
            self.current_phase = "ACTIVE"
            self.last_status_message = f"14-Day High-Volume Campaign started (Day 1 of {duration_days})"
            self._save_state()

        try:
            loop = asyncio.get_running_loop()
            if self._task is None or self._task.done():
                self._task = loop.create_task(self._campaign_loop())
        except RuntimeError:
            pass

        logger.info(f"🚀 [HIGH-VOLUME PROSPECTOR] Started {duration_days}-day campaign with volume {self.volume_per_cycle}/cycle")
        return self.get_status()

    def pause_campaign(self) -> dict[str, Any]:
        """Pause the campaign loop."""
        with self._lock:
            self.is_active = False
            self.current_phase = "PAUSED"
            self.last_status_message = "14-Day High-Volume Campaign paused by operator"
            self._save_state()
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("⏸️ [HIGH-VOLUME PROSPECTOR] Campaign paused by operator")
        return self.get_status()

    def resume_campaign(self) -> dict[str, Any]:
        """Resume the campaign loop."""
        with self._lock:
            self.is_active = True
            self.current_phase = "ACTIVE"
            self.last_status_message = f"14-Day High-Volume Campaign resumed (Day {self.current_day} of {self.campaign_duration_days})"
            self._save_state()
        try:
            loop = asyncio.get_running_loop()
            if self._task is None or self._task.done():
                self._task = loop.create_task(self._campaign_loop())
        except RuntimeError:
            pass
        logger.info(f"▶️ [HIGH-VOLUME PROSPECTOR] Campaign resumed (Day {self.current_day})")
        return self.get_status()

    async def trigger_burst(self, count: int = 3, channel: str | None = None) -> dict[str, Any]:
        """Execute an immediate high-volume discovery pass."""
        clamped_count = max(1, min(count, 10))
        target_channel = channel if channel in self.CHANNELS else None
        logger.info(f"⚡ [HIGH-VOLUME BURST] Triggering immediate burst of {clamped_count} leads (Channel: {target_channel or 'All'})")

        discovered = []
        # Lazy import to avoid circular: agents.scout_runner.worker → agents.scout_runner → agents.scout_runner.worker
        from agents.scout_runner.worker import ScoutBackgroundWorker  # noqa: PLC0415
        worker = ScoutBackgroundWorker(storage=self.storage, portal=self.portal)

        for i in range(clamped_count):
            chan = target_channel or self.active_channels[self.channel_index % len(self.active_channels)]
            self.channel_index += 1
            self.metrics.total_evaluated += 1

            try:
                res = await asyncio.to_thread(worker.discover_next_candidate, channel=chan, run_until_found=False)
                if res and res.get("ok"):
                    discovered.append(res)
                    self.metrics.deliverability_passed += 1
                    self.metrics.sandboxes_created += 1
                    self.metrics.websites_verified += 1
                    self.metrics.qualified_backlog_count += 1
                    self.metrics.last_lead_discovered = {
                        "company_name": res.get("company_name"),
                        "contact_email": res.get("contact_email"),
                        "slug": res.get("slug"),
                        "discovered_at": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    reason = (res or {}).get("dedup_reason") or (res or {}).get("reason") or "REJECTED"
                    if "DUPLICATE" in str(reason) or "SUPPRESSION" in str(reason) or "CONTACTED" in str(reason):
                        self.metrics.duplicates_blocked += 1
                        key = "GLOBAL_SUPPRESSION" if "SUPPRESSION" in str(reason) else (
                            "DUPLICATE_EMAIL" if "EMAIL" in str(reason) else (
                                "DUPLICATE_DOMAIN" if "DOMAIN" in str(reason) else (
                                    "RECENTLY_CONTACTED_45D" if "CONTACTED" in str(reason) else "DUPLICATE_COMPANY"
                                )
                            )
                        )
                        self.metrics.duplicates_by_reason[key] = self.metrics.duplicates_by_reason.get(key, 0) + 1
                    elif "EMAIL" in str(reason) or "DELIVERABLE" in str(reason):
                        self.metrics.deliverability_failed += 1
            except Exception as e:
                logger.error(f"Burst pass {i+1} exception: {e}", exc_info=True)

        self._save_state()
        return {
            "ok": len(discovered) > 0,
            "requested": clamped_count,
            "qualified_count": len(discovered),
            "leads": discovered,
            "campaign_day": self.current_day,
            "days_remaining": self.days_remaining,
            "metrics": self.metrics.to_dict(),
        }

    async def _campaign_loop(self) -> None:
        """Continuous background execution loop running during office hours."""
        logger.info(f"🌟 [HIGH-VOLUME PROSPECTOR LOOP] Starting loop for Day {self.current_day} of {self.campaign_duration_days}")
        try:
            while self.is_active:
                if self.is_campaign_expired:
                    self.current_phase = "COMPLETED"
                    self.last_status_message = "14-Day High-Volume Campaign completed successfully!"
                    self.is_active = False
                    self._save_state()
                    logger.info("🏁 [HIGH-VOLUME PROSPECTOR] 14-day campaign duration completed.")
                    break

                # 1. Office Hours Gate (evaluated only when not in 24/7 all-day mode)
                is_open, wait_seconds, status_msg = is_office_hours()
                if not self.run_24_7 and not is_open:
                    self.current_phase = "STANDBY_OFFICE_HOURS"
                    self.last_status_message = status_msg
                    logger.info(f"🌙 [OFFICE HOURS STANDBY] {status_msg} Standing by for morning window.")
                    self._save_state()
                    sleep_time = min(wait_seconds, 300)
                    await asyncio.sleep(sleep_time)
                    continue

                if not is_open:
                    logger.info(f"⚡ [24/7 ALL-DAY SCOUTING] High-Volume Prospector active outside standard hours ({status_msg}). Continuing discovery burst.")

                # 2. Execute Discovery Burst (round-the-clock or during office hours)
                self.current_phase = "PROSPECTING_BURST"
                self.last_status_message = f"Day {self.current_day}/{self.campaign_duration_days}: Searching & qualifying {self.volume_per_cycle} candidates"

                burst_res = await self.trigger_burst(count=self.volume_per_cycle)
                qual_count = burst_res.get("qualified_count", 0)

                # 3. Rest interval between bursts
                rest_sec = random.randint(self.rest_seconds_min, self.rest_seconds_max)
                self.current_phase = "RESTING"
                self.last_status_message = f"Burst complete (+{qual_count} vetted). Next pass in {rest_sec}s."
                logger.info(f"⚡ [PROSPECTING PASS DONE] Qualified +{qual_count} leads. Resting {rest_sec}s before next pass.")
                self._save_state()

                await asyncio.sleep(rest_sec)

        except asyncio.CancelledError:
            self.current_phase = "PAUSED"
            logger.info("🛑 [HIGH-VOLUME PROSPECTOR] Campaign loop cancelled.")
        except Exception as e:
            self.current_phase = "ERROR"
            self.last_status_message = f"Prospector error: {str(e)}"
            logger.exception("High-volume prospector unexpected failure")
        finally:
            self._save_state()


# Global singleton instance
_prospector_engine: HighVolumeProspectorEngine | None = None


def get_high_volume_prospector(storage: StorageBackend, portal: PortalService) -> HighVolumeProspectorEngine:
    global _prospector_engine
    if _prospector_engine is None:
        _prospector_engine = HighVolumeProspectorEngine(storage=storage, portal=portal)
    return _prospector_engine
