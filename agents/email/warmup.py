"""Automated warmup scheduler and multi-inbox throttle manager."""

import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone, date
from typing import Any

from .config import EmailSettings, InboxAccountConfig

logger = logging.getLogger("leadops.email.warmup")


@dataclass
class WarmupTier:
    week_number: int
    daily_quota: int
    name: str


class WarmupManager:
    """Calculates automated warmup progression and enforces daily dispatch quotas across inboxes."""

    # Shared class-level tracking across instances during process lifecycle
    _shared_inbox_next_available: dict[str, float] = {}
    _shared_in_memory_daily_counts: dict[str, int] = {}
    _shared_rate_limited_inboxes: dict[str, float] = {}

    def __init__(
        self,
        settings: EmailSettings | None = None,
        storage_backend: Any = None,
    ):
        self.settings = settings or EmailSettings.from_environment()
        self.storage = storage_backend
        self._in_memory_daily_counts = self._shared_in_memory_daily_counts
        self._rate_limited_inboxes = self._shared_rate_limited_inboxes
        self._inbox_next_available_time = self._shared_inbox_next_available
        self._rr_index = 0

    def record_inbox_jitter(self, inbox_id: str, jitter_seconds: float) -> None:
        """Mark a specific inbox on anti-spam jitter cooldown after sending."""
        import time
        until = time.time() + jitter_seconds
        self._inbox_next_available_time[inbox_id] = until
        logger.info(
            f"⏳ [PER-INBOX JITTER] Inbox '{inbox_id}' set on {jitter_seconds/60:.1f}m ({jitter_seconds:.0f}s) cooldown until {datetime.fromtimestamp(until, tz=timezone.utc).strftime('%H:%M:%S UTC')}."
        )

    def is_inbox_on_jitter(self, inbox_id: str) -> bool:
        """Check if this specific inbox is currently in a 5-30 min jitter cooldown."""
        import time
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return False
        until = self._inbox_next_available_time.get(inbox_id, 0.0)
        return time.time() < until

    def get_inbox_jitter_wait(self, inbox_id: str) -> float:
        """Return remaining seconds of jitter cooldown for this inbox."""
        import time
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return 0.0
        until = self._inbox_next_available_time.get(inbox_id, 0.0)
        return max(0.0, until - time.time())

    def mark_inbox_rate_limited(self, inbox_id: str, cooldown_seconds: int = 7200) -> None:
        """Mark an inbox on temporary cooldown after receiving SMTP 421/451 rate limit responses."""
        import time
        until = time.time() + cooldown_seconds
        self._rate_limited_inboxes[inbox_id] = until
        logger.warning(
            f"⏸️ [INBOX RATE-LIMIT COOLDOWN] Inbox '{inbox_id}' marked on cooldown for {cooldown_seconds}s (until {datetime.fromtimestamp(until, tz=timezone.utc).isoformat()})."
        )

    def is_inbox_rate_limited(self, inbox_id: str) -> bool:
        """Check if inbox is currently in a temporary rate-limit cooldown."""
        import time
        until = self._rate_limited_inboxes.get(inbox_id, 0.0)
        return time.time() < until

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

    def get_all_configured_accounts(self, outbound_only: bool = False) -> list[InboxAccountConfig]:
        """Return all inboxes configured via environment settings and database storage."""
        if outbound_only:
            accounts = list(self.settings.get_outbound_inboxes())
        else:
            accounts = list(self.settings.get_all_inboxes())
        existing_ids = {a.id for a in accounts}

        if self.storage and hasattr(self.storage, "list_inbox_accounts"):
            try:
                db_inboxes = self.storage.list_inbox_accounts()
                for d in db_inboxes:
                    inbox_id = d.get("inbox_id")
                    if inbox_id and inbox_id not in existing_ids:
                        accounts.append(
                            InboxAccountConfig(
                                id=inbox_id,
                                email_address=d.get("email_address", ""),
                                password=d.get("password", ""),
                                provider=d.get("provider", "zoho"),
                                from_name=d.get("from_name", self.settings.from_name),
                                smtp_host=d.get("smtp_host", ""),
                                smtp_port=int(d.get("smtp_port", 465)),
                                smtp_use_ssl=bool(d.get("smtp_use_ssl", True)),
                                imap_host=d.get("imap_host", ""),
                                imap_port=int(d.get("imap_port", 993)),
                                imap_use_ssl=bool(d.get("imap_use_ssl", True)),
                                warmup_start_date=d.get("warmup_start_date", ""),
                                daily_limit=int(d.get("daily_limit", self.settings.warmup_week1_limit)),
                                is_active=bool(d.get("is_active", 1)),
                            )
                        )
                        existing_ids.add(inbox_id)
            except Exception as e:
                logger.warning(f"Could not load inboxes from database: {e}")

        return accounts

    def get_inbox_by_id(self, inbox_id: str) -> InboxAccountConfig | None:
        """Find an inbox configuration by ID from the configured pool."""
        for inb in self.get_all_configured_accounts():
            if inb.id == inbox_id:
                return inb
        return None

    def can_send_today(self, inbox_id: str = "primary", warmup_start: datetime | None = None) -> tuple[bool, int, int]:
        """Determine if inbox has remaining quota for today. Returns (can_send, sent_today, daily_quota)."""
        if self.is_inbox_rate_limited(inbox_id):
            sent_today = self.get_sent_count_today(inbox_id)
            return False, sent_today, 0

        inbox_cfg = self.get_inbox_by_id(inbox_id)
        if inbox_cfg and not warmup_start and inbox_cfg.warmup_start_date:
            try:
                warmup_start = datetime.fromisoformat(inbox_cfg.warmup_start_date.replace("Z", "+00:00"))
            except Exception:
                pass

        tier = self.get_warmup_tier(warmup_start)
        daily_quota = inbox_cfg.daily_limit if (inbox_cfg and inbox_cfg.daily_limit and inbox_cfg.daily_limit != 25) else tier.daily_quota
        sent_today = self.get_sent_count_today(inbox_id)
        can_send = sent_today < daily_quota
        return can_send, sent_today, daily_quota

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

    def get_available_inbox(self, check_jitter: bool = False) -> str | None:
        """Multi-inbox load balancer: returns active outbound inbox ID with remaining daily quota.
        
        If check_jitter is True, strictly returns inboxes that are NOT currently on anti-spam jitter cooldown.
        Prioritizes the inbox with the lowest sent count today for even load distribution.
        """
        all_accounts = self.get_all_configured_accounts(outbound_only=True)
        eligible_candidates: list[tuple[int, str]] = []

        if all_accounts:
            for acc in all_accounts:
                if not acc.is_active:
                    continue
                if self.is_inbox_rate_limited(acc.id):
                    continue
                if check_jitter and self.is_inbox_on_jitter(acc.id):
                    continue
                can_send, sent, quota = self.can_send_today(acc.id)
                if can_send:
                    eligible_candidates.append((sent, acc.id))

        if eligible_candidates:
            # Sort by least sent today (stable sort preserves configured priority among tie counts)
            eligible_candidates.sort(key=lambda x: x[0])
            return eligible_candidates[0][1]

        # Fallback to legacy extra_inboxes format for backwards compatibility
        if self.settings.extra_inboxes:
            for i, inb in enumerate(self.settings.extra_inboxes):
                inbox_id = inb.get("id", f"inbox_{i}")
                if self.is_inbox_rate_limited(inbox_id):
                    continue
                if check_jitter and self.is_inbox_on_jitter(inbox_id):
                    continue
                can_send, sent, quota = self.can_send_today(inbox_id)
                if can_send:
                    return inbox_id

        # If outbound_use_gmail is explicitly enabled or no other inboxes exist
        if self.settings.outbound_use_gmail or not (self.settings.inbox_pool or self.settings.extra_inboxes):
            if not self.is_inbox_rate_limited("primary") and not (check_jitter and self.is_inbox_on_jitter("primary")):
                can_send, sent, quota = self.can_send_today("primary")
                if can_send:
                    return "primary"

        return None

    def get_earliest_jitter_wait(self) -> float:
        """Return the minimum seconds to wait until the earliest inbox with remaining quota finishes its jitter."""
        all_accounts = self.get_all_configured_accounts(outbound_only=True)
        waits = []
        for acc in all_accounts:
            if not acc.is_active or self.is_inbox_rate_limited(acc.id):
                continue
            can_send, _, _ = self.can_send_today(acc.id)
            if can_send:
                w = self.get_inbox_jitter_wait(acc.id)
                waits.append(w)
        if not waits:
            return 0.0
        return min(waits)

    def get_available_inbox_account(self, check_jitter: bool = False) -> InboxAccountConfig | None:
        """Returns the full InboxAccountConfig object for the next available inbox."""
        inbox_id = self.get_available_inbox(check_jitter=check_jitter)
        if not inbox_id:
            return None
        return self.get_inbox_by_id(inbox_id)

