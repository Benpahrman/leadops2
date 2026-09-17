"""Telegram Bot API notification sender for LeadOps."""

import logging
from typing import Any
import httpx

logger = logging.getLogger("leadops.notifications.telegram")


class TelegramNotifier:
    """Sends clean Markdown/HTML messages to Telegram private chats or group channels via Bot API."""

    def __init__(self, bot_token: str, chat_id: str, timeout: float = 3.5):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send_message(self, text: str, reply_markup: dict[str, Any] | None = None) -> bool:
        """Send a message to the configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text[:4096],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.warning(f"Telegram notification dispatch failed: {e}")
            return False
