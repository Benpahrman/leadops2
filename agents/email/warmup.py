"""Automated warmup scheduler and multi-inbox throttle manager."""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Any

from .config import EmailSettings

logger = logging.getLogger("leadops.email.warmup")


@dataclass
class WarmupTier:
    week_number: int
    daily_quota: int
    name: str


class WarmupManager:
    """Calculates automated warmup progression and enforces daily dispatch quotas."""

    def __init__(
        self,
        settings: EmailSettings | None = None,
        storage_backend: Any = None,
    ):
        self.settings = settings or EmailSettings.from_environment()
        self.storage = storage_backend
        self._in_memory_daily_counts: dict[str, int] = {}

    def get_warmup_tier(self, warmup_start: datetime | None = None) -> WarmupTier:
        """Calculate the active warmup week and corresponding daily dispatch limit.
        
        Week 1 (Days 0-6):   20-25 emails/day (Limit: 25)
        Week 2 (Days 7-13):  50 emails/day (+25)
        Week 3 (Days 14-20): 75 emails/day (+25)
        Week 4+ (Days 21+):  100 emails/day (Max)
        """
        now = datetime.now(timezone.utc)
        if not warmup_start:
            if self.settings.warmup_start_date:
                try:
                    warmup_start = datetime.fromisoformat(self.settings.warmup_start_date.replace("Z", "+00:00"))
                except Exception:
                    warmup_start = now
            else:
                warmup_start = now

        days_active = max(0, (now - warmup_start).days)
        week_number = (days_active // 7) + 1

        if week_number == 1:
            return WarmupTier(week_number=1, daily_quota=self.settings.warmup_week1_limit, name="Week 1 (Warmup: 20-25/day)")
        elif week_number == 2:
            return WarmupTier(week_number=2, daily_quota=self.settings.warmup_week2_limit, name="Week 2 (Expansion: 50/day)")
        elif week_number == 3:
            return WarmupTier(week_number=3, daily_quota=self.settings.warmup_week3_limit, name="Week 3 (Acceleration: 75/day)")
        else:
            return WarmupTier(week_number=week_number, daily_quota=self.settings.warmup_week4_limit, name=f"Week {week_number} (Full Throttle: 100/day max)")

    def get_active_warmup_week(self, warmup_start: datetime | None = None) -> int:
        """Convenience method returning the active week number (1, 2, 3, 4+)."""
        return self.get_warmup_tier(warmup_start).week_number

    def get_today_key(self, inbox_id: str = "primary") -> str:
        today_str = date.today().isoformat()
        return f"{inbox_id}:{today_str}"

    def get_sent_count_today(self, inbox_id: str = "primary") -> int:
        """Fetch count of emails dispatched today for the specified inbox."""
        today_key = self.get_today_key(inbox_id)
        if self.storage and hasattr(self.storage, "get_email_sent_count_today"):
            try:
                return self.storage.get_email_sent_count_today(inbox_id)
            except Exception as e:
                logger.warning(f"Storage query for email quota failed: {e}. Using in-memory counter.")
        return self._in_memory_daily_counts.get(today_key, 0)

    def can_send_today(self, inbox_id: str = "primary", warmup_start: datetime | None = None) -> tuple[bool, int, int]:
        """Determine if inbox has remaining quota for today. Returns (can_send, sent_today, daily_quota)."""
        tier = self.get_warmup_tier(warmup_start)
        sent_today = self.get_sent_count_today(inbox_id)
        can_send = sent_today < tier.daily_quota
        return can_send, sent_today, tier.daily_quota

    def record_send(self, inbox_id: str = "primary", recipient: str = "", lead_id: str = "") -> int:
        """Increment daily dispatch count and record event to persistent storage."""
        today_key = self.get_today_key(inbox_id)
        self._in_memory_daily_counts[today_key] = self._in_memory_daily_counts.get(today_key, 0) + 1
        new_count = self._in_memory_daily_counts[today_key]

        if self.storage and hasattr(self.storage, "record_email_sent"):
            try:
                self.storage.record_email_sent(
                    inbox_id=inbox_id,
                    recipient=recipient,
                    lead_id=lead_id,
                    dispatched_at=datetime.now(timezone.utc).isoformat(),
                )
            except Exception as e:
                logger.error(f"Failed to record email dispatch to storage: {e}")

        logger.info(f"📈 [WARMUP QUOTA] Dispatched {new_count} emails today on inbox '{inbox_id}'.")
        return new_count

    def get_available_inbox(self) -> str | None:
        """Multi-inbox load balancer: returns the active inbox ID that has remaining daily quota."""
        all_inboxes = ["primary"]
        if self.settings.extra_inboxes:
            all_inboxes.extend([inb.get("id", f"inbox_{i}") for i, inb in enumerate(self.settings.extra_inboxes)])

        for inbox_id in all_inboxes:
            can_send, sent, quota = self.can_send_today(inbox_id)
            if can_send:
                return inbox_id
        return None
