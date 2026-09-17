"""Multi-channel real-time notification engine for LeadOps (Discord Webhooks & Telegram Bot).

Decomposed and organized under ADR-0002 into domain modules:
- settings: NotificationSettings configuration dataclass
- discord: DiscordNotifier webhook dispatcher
- telegram: TelegramNotifier Bot API dispatcher
- manager: NotificationManager orchestrator & singleton
"""

import logging
from .settings import NotificationSettings
from .discord import DiscordNotifier
from .telegram import TelegramNotifier
from .manager import NotificationManager

logger = logging.getLogger("leadops.notifications")

# Global notification manager singleton
notification_manager = NotificationManager()

__all__ = [
    "NotificationSettings",
    "DiscordNotifier",
    "TelegramNotifier",
    "NotificationManager",
    "notification_manager",
    "logger",
]
