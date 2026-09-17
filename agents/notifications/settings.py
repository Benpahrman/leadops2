"""Settings and environment configuration for the LeadOps notification engine."""

import os
from dataclasses import dataclass


@dataclass
class NotificationSettings:
    """Settings for outbound operator notifications across Discord and Telegram."""

    enabled: bool = True
    discord_webhook_url: str = ""
    discord_webhook_outreach: str = ""
    discord_webhook_inbox: str = ""
    discord_webhook_revenue: str = ""
    discord_webhook_dev: str = ""
    discord_webhook_alerts: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    timeout_seconds: float = 3.5

    @classmethod
    def from_env(cls) -> "NotificationSettings":
        enabled_str = os.environ.get("NOTIFICATIONS_ENABLED", "true").lower().strip()
        default_discord = (
            os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
            or os.environ.get("DISCORD_WEBHOOK_ALERTS", "").strip()
            or os.environ.get("DISCORD_WEBHOOK_OUTREACH", "").strip()
        )
        return cls(
            enabled=enabled_str in ("true", "1", "yes"),
            discord_webhook_url=default_discord,
            discord_webhook_outreach=os.environ.get("DISCORD_WEBHOOK_OUTREACH", "").strip() or default_discord,
            discord_webhook_inbox=os.environ.get("DISCORD_WEBHOOK_INBOX", "").strip() or default_discord,
            discord_webhook_revenue=os.environ.get("DISCORD_WEBHOOK_REVENUE", "").strip() or default_discord,
            discord_webhook_dev=os.environ.get("DISCORD_WEBHOOK_DEV", "").strip() or default_discord,
            discord_webhook_alerts=os.environ.get("DISCORD_WEBHOOK_ALERTS", "").strip() or default_discord,
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", "").strip(),
            timeout_seconds=float(os.environ.get("NOTIFICATION_TIMEOUT_SECONDS", "3.5")),
        )
