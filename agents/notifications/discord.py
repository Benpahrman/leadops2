"""Discord Webhook notification sender for LeadOps."""

import logging
from typing import Any
import httpx

logger = logging.getLogger("leadops.notifications.discord")


class DiscordNotifier:
    """Sends rich, formatted embeds to Discord channels via Webhooks."""

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 3.5,
        channel_webhooks: dict[str, str] | None = None,
    ):
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.channel_webhooks = channel_webhooks or {}

    def get_webhook(self, channel: str | None = None) -> str:
        """Resolve the target webhook URL for the specified channel or fallback to default."""
        if channel and self.channel_webhooks.get(channel):
            return self.channel_webhooks[channel]
        return self.webhook_url

    def send_embed(
        self,
        title: str,
        description: str,
        fields: list[dict[str, Any]] | None = None,
        color: int = 0x15251F,  # Forest Deep default
        footer: str = "LeadOps Autonomous Swarm",
        author: dict[str, str] | None = None,
        thumbnail_url: str | None = None,
        timestamp: str | None = None,
        footer_icon_url: str | None = None,
        username: str = "LeadOps Mission Control",
        avatar_url: str = "https://cdn-icons-png.flaticon.com/512/906/906334.png",
        channel: str | None = None,
        image_url: str | None = None,
    ) -> bool:
        """Build and send a Discord embed payload via HTTP POST."""
        target_url = self.get_webhook(channel)
        if not target_url:
            return False

        from datetime import datetime, timezone
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        embed: dict[str, Any] = {
            "title": title[:256],
            "description": description[:2048],
            "color": color,
            "fields": [
                {
                    "name": str(f.get("name", ""))[:256],
                    "value": str(f.get("value", ""))[:1024],
                    "inline": bool(f.get("inline", True)),
                }
                for f in (fields or [])[:25]
            ],
            "timestamp": ts,
        }

        footer_obj: dict[str, str] = {"text": footer[:2048]}
        if footer_icon_url:
            footer_obj["icon_url"] = footer_icon_url
        embed["footer"] = footer_obj

        if author:
            author_obj: dict[str, str] = {"name": str(author.get("name", ""))[:256]}
            if author.get("icon_url"):
                author_obj["icon_url"] = author["icon_url"]
            if author.get("url"):
                author_obj["url"] = author["url"]
            embed["author"] = author_obj

        if thumbnail_url:
            embed["thumbnail"] = {"url": thumbnail_url}

        if image_url:
            embed["image"] = {"url": image_url}

        payload = {
            "username": username,
            "avatar_url": avatar_url,
            "embeds": [embed],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(target_url, json=payload)
                return res.status_code in (200, 204)
        except Exception as e:
            logger.warning(f"Discord webhook dispatch failed ({channel or 'default'}): {e}")
            return False
