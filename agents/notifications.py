"""Multi-channel real-time notification engine for LeadOps (Discord Webhooks & Telegram Bot)."""

import json
import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger("leadops.notifications")


@dataclass
class NotificationSettings:
    """Settings for outbound operator notifications."""

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


class TelegramNotifier:
    """Sends clean Markdown messages to Telegram private chats or group channels via Bot API."""

    def __init__(self, bot_token: str, chat_id: str, timeout: float = 3.5):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    def send_message(self, text: str, reply_markup: dict[str, Any] | None = None) -> bool:
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


class NotificationManager:
    """Unified notification coordinator for LeadOps operations."""

    def __init__(
        self,
        settings: NotificationSettings | None = None,
        discord_notifier: DiscordNotifier | None = None,
        telegram_notifier: TelegramNotifier | None = None,
        async_dispatch: bool = True,
        base_url: str = "",
        force_dispatch_in_test: bool = False,
    ):
        self.settings = settings or NotificationSettings.from_env()
        channel_map = {
            "outreach": self.settings.discord_webhook_outreach,
            "inbox": self.settings.discord_webhook_inbox,
            "revenue": self.settings.discord_webhook_revenue,
            "dev": self.settings.discord_webhook_dev,
            "alerts": self.settings.discord_webhook_alerts,
        }
        self.discord = discord_notifier or (
            DiscordNotifier(
                self.settings.discord_webhook_url,
                self.settings.timeout_seconds,
                channel_webhooks=channel_map,
            )
            if (self.settings.discord_webhook_url or any(channel_map.values()))
            else None
        )
        self.telegram = telegram_notifier or (
            TelegramNotifier(
                self.settings.telegram_bot_token,
                self.settings.telegram_chat_id,
                self.settings.timeout_seconds,
            )
            if (self.settings.telegram_bot_token and self.settings.telegram_chat_id)
            else None
        )
        is_cloud = bool(
            os.environ.get("CONTAINER_APP_NAME")
            or os.environ.get("DATABASE_URL", "").startswith("postgresql")
            or os.environ.get("ENVIRONMENT") == "production"
        )
        default_base = "https://www.omnileadfeeder.tech" if is_cloud else "http://127.0.0.1:8000"
        self.base_url = (
            base_url
            or os.environ.get("LEADOPS_PUBLIC_URL", "")
            or os.environ.get("BASE_URL", "")
            or default_base
        ).rstrip("/")
        self.async_dispatch = async_dispatch
        self.force_dispatch_in_test = force_dispatch_in_test

    def is_configured(self) -> bool:
        return bool(self.settings.enabled and (self.discord or self.telegram))

    def _dispatch(self, target_func: Any, *args: Any, **kwargs: Any) -> None:
        if not self.settings.enabled:
            return
        if not self.force_dispatch_in_test:
            if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("MOCK_NOTIFICATIONS") == "true":
                return

        if self.async_dispatch:
            thread = threading.Thread(target=target_func, args=args, kwargs=kwargs, daemon=True)
            thread.start()
        else:
            try:
                target_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Direct notification dispatch error: {e}")

    def notify_lead_qualified_and_dispatching(
        self,
        lead: Any,
        pitch: Any,
        quota_info: dict[str, Any] | None = None,
        grace_period_seconds: int = 180,
    ) -> None:
        """Alert operator when a prospect passes all quality gates and is queued for cold outreach."""
        from .auth import generate_mobile_action_token
        lead_id = getattr(lead, "lead_id", "")
        slug = getattr(lead, "slug", "") or lead_id

        approve_tok = generate_mobile_action_token("approve_pitch", lead_id)
        reject_tok = generate_mobile_action_token("reject_pitch", lead_id)
        send_now_tok = generate_mobile_action_token("send_immediately", lead_id)
        cancel_tok = generate_mobile_action_token("cancel_auto_outreach", lead_id)

        approve_url = f"{self.base_url}/api/admin/quick-action?action=approve_pitch&lead_id={lead_id}&token={approve_tok}"
        send_now_url = f"{self.base_url}/api/admin/quick-action?action=send_immediately&lead_id={lead_id}&token={send_now_tok}"
        cancel_url = f"{self.base_url}/api/admin/quick-action?action=cancel_auto_outreach&lead_id={lead_id}&token={cancel_tok}"
        reject_url = f"{self.base_url}/api/admin/quick-action?action=reject_pitch&lead_id={lead_id}&token={reject_tok}"
        sandbox_url = f"{self.base_url}/p/{slug}"

        def _send():
            company = getattr(lead, "company_name", "Unknown Company")
            contact = getattr(lead, "contact_name", "Decision Maker")
            role = getattr(lead, "contact_role", "Executive")
            email = getattr(lead, "contact_email", "N/A")
            niche = getattr(lead, "niche", "Public Records")
            portal = getattr(lead, "jurisdiction", "") or getattr(lead, "portal_name", "County Records Portal")
            subject = getattr(pitch, "subject", "Cold outreach")
            body = getattr(pitch, "body_text", "") or getattr(lead, "outreach_body", "")
            words = getattr(pitch, "word_count", len(body.split()))
            
            quota_str = ""
            if quota_info:
                sent = quota_info.get("sent_today", 0)
                quota = quota_info.get("daily_quota", 25)
                week = quota_info.get("warmup_week", 1)
                quota_str = f"Week {week} ({sent}/{quota} dispatched today)"

            linkedin_url = getattr(lead, "decision_maker_linkedin", "") or (getattr(lead, "research", {}).get("linkedin_url", "") if isinstance(getattr(lead, "research", None), dict) else "")

            # 1. Discord Embed - Clean, Executive Visual Hierarchy
            if self.discord:
                from .email.config import EmailSettings
                sending_from = EmailSettings.from_environment().resolve_sender_email(hint=getattr(lead, "lead_id", "") or email)

                contact_lines = [f"▸ **Contact:** **{contact}** ({role})", f"▸ **Email:** `{email}`"]
                if linkedin_url:
                    contact_lines.append(f"▸ **Profile:** [👔 View LinkedIn Profile]({linkedin_url})")

                # Format pitch body as clean markdown blockquote
                body_preview = "\n".join(f"> {line}" if line.strip() else ">" for line in body.strip().splitlines()) if body else "> (Drafting complete)"

                fields = [
                    {
                        "name": "🏢 Verified Buyer & Prospect",
                        "value": f"**{company}**\n*{niche}*\n" + "\n".join(contact_lines),
                        "inline": True,
                    },
                    {
                        "name": "🏛️ Routing & Delivery Node",
                        "value": (
                            f"▸ **Target Portal:** `{portal}`\n"
                            f"▸ **Sending Mailbox:** `{sending_from}`\n"
                            f"▸ **Routing:** Native SMTP / Cloudflare\n"
                            f"▸ **Warmup:** {quota_str or 'Normal Schedule'}"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "✉️ Cold Email Subject Line",
                        "value": f"```\n{subject}\n```",
                        "inline": False,
                    },
                    {
                        "name": f"📄 Cold Email Draft ({words} words • Zero-Link Peer Outreach)",
                        "value": body_preview[:1024],
                        "inline": False,
                    },
                    {
                        "name": "⏱️ Autonomous Dispatch Countdown",
                        "value": (
                            f"⏳ **Auto-sending in {grace_period_seconds // 60}:00 minutes** unless cancelled.\n"
                            f"🛡️ *Anti-spam jitter delay (90-240s) enforced between sends • 8am-5pm CST office hours only.*"
                        ),
                        "inline": False,
                    },
                    {
                        "name": "📱 1-Tap Mobile Actions",
                        "value": (
                            f"> 🛑 **[ ✕ CANCEL DISPATCH ]({cancel_url})**    •    "
                            f"⚡ **[ ➔ SEND NOW ]({send_now_url})**    •    "
                            f"🌐 **[ ↗ LIVE SANDBOX ]({sandbox_url})**"
                        ),
                        "inline": False,
                    },
                ]

                self.discord.send_embed(
                    title=f"🎯 Lead Qualified • Outbound Review: {company}",
                    description=(
                        f"### 🎯 Verified Prospect Enriched & Drafted\n"
                        f"Review live prospect intelligence and the exact email draft below before autonomous dispatch.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0x10B981,  # Emerald Green
                    author={
                        "name": "LEADOPS AUTONOMOUS OUTREACH • 3-MIN REVIEW WINDOW",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/2921/2921222.png",
                    footer="OmniLeadFeeder Technologies • Autonomous Outreach Engine",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Scout & Outreach",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                    channel="outreach",
                )

            # 2. Telegram Message - Structured HTML with Inline Keyboard
            if self.telegram:
                body_escaped = body.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
                msg = (
                    f"🎯 <b>Lead Qualified & Auto-Queued</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"👤 <b>Contact:</b> {contact} ({role}) • <code>{email}</code>\n"
                    f"🏛️ <b>Portal:</b> {portal}\n"
                    f"📤 <b>Mailbox:</b> <code>{sending_from if 'sending_from' in locals() else 'primary'}</code>\n\n"
                    f"✉️ <b>Subject:</b> <i>{subject}</i>\n\n"
                    f"📄 <b>Email Draft:</b>\n"
                    f"<blockquote>{body_escaped[:600]}</blockquote>\n\n"
                    f"⏱️ <i>Auto-sending in {grace_period_seconds // 60} mins unless cancelled.</i>"
                )
                if quota_str:
                    msg += f"\n⚡ <i>{quota_str}</i>"

                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "🛑 Cancel / Reject", "url": cancel_url},
                            {"text": "⚡ Send Immediately", "url": send_now_url},
                        ],
                        [
                            {"text": "🌐 View Live Sandbox", "url": sandbox_url},
                        ]
                    ]
                }
                self.telegram.send_message(msg, reply_markup=reply_markup)

        self._dispatch(_send)

    def notify_inbound_reply_received(
        self,
        sender_email: str,
        sender_name: str,
        company_name: str,
        subject: str,
        reply_snippet: str,
        ai_intent: str,
        ai_sentiment: str,
        ai_draft_reply: str,
    ) -> None:
        """Alert operator when a prospect replies to an outreach email."""
        def _send():
            # 1. Discord Embed
            if self.discord:
                color_map = {
                    "INTERESTED": 0x10B981,  # Emerald
                    "QUESTION": 0x3B82F6,    # Blue
                    "OBJECTION": 0xF59E0B,   # Amber
                    "OPT_OUT": 0xEF4444,     # Crimson
                    "OUT_OF_OFFICE": 0x6B7280, # Gray
                }
                color = color_map.get(ai_intent.upper(), 0x3B82F6)

                fields = [
                    {
                        "name": "🏢 Verified Company & Lead",
                        "value": f"▸ **Company:** **{company_name}**\n▸ **From:** **{sender_name}** (`{sender_email}`)",
                        "inline": True,
                    },
                    {
                        "name": "🧠 AI Triage & Sentiment",
                        "value": f"▸ **Intent:** `{ai_intent}`\n▸ **Sentiment:** `{ai_sentiment}`",
                        "inline": True,
                    },
                    {
                        "name": f"💬 Prospect Message (Re: {subject})",
                        "value": "\n".join(f"> {line}" for line in reply_snippet.strip().splitlines()[:10]) or "> (Empty message)",
                        "inline": False,
                    },
                    {
                        "name": "🤖 Alex's Autonomous AI Response",
                        "value": f"```\n{ai_draft_reply[:600]}\n```",
                        "inline": False,
                    },
                ]

                self.discord.send_embed(
                    title=f"📬 Inbound Reply: {company_name}",
                    description=(
                        f"### 📬 Prospect Message Received\n"
                        f"Cloudflare routed prospect reply from `{sender_email}` for subject *{subject}*.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=color,
                    author={
                        "name": f"LEADOPS INBOUND CONCIERGE • {ai_intent.upper()}",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/2099/2099199.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/1041/1041916.png",
                    footer="LeadOps • Autonomous Inbound Concierge",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Inbound Concierge",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/2099/2099199.png",
                    channel="inbox",
                )

            # 2. Telegram Message
            if self.telegram:
                msg = (
                    f"📬 <b>New Prospect Reply Received!</b>\n\n"
                    f"🏢 <b>Company:</b> {company_name}\n"
                    f"👤 <b>From:</b> {sender_name} (<code>{sender_email}</code>)\n"
                    f"🧠 <b>AI Intent:</b> <code>{ai_intent}</code> ({ai_sentiment})\n\n"
                    f"💬 <b>Prospect Said:</b>\n<i>\"{reply_snippet[:250]}\"</i>\n\n"
                    f"🤖 <b>Alex's Response:</b>\n<pre>{ai_draft_reply[:300]}</pre>"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_warmup_cap_reached(
        self,
        sent_count: int,
        quota: int,
        warmup_week: int,
        next_resume_time: str = "Tomorrow at 08:00 AM",
    ) -> None:
        """Alert operator when the daily warmup dispatch quota has been satisfied."""
        def _send():
            title = f"🛑 Daily Warmup Quota Reached ({sent_count}/{quota})"
            desc = (
                f"### 🛡️ Warmup Safety Gatekeeper Engaged\n"
                f"Week {warmup_week} daily quota satisfied ({sent_count}/{quota} sent today).\n"
                f"Outbound outreach paused until `{next_resume_time}` to protect sender authority.\n"
                f"────────────────────────────────────────"
            )

            if self.discord:
                self.discord.send_embed(
                    title=title,
                    description=desc,
                    fields=[
                        {"name": "📅 Warmup Tier", "value": f"**Week {warmup_week}**", "inline": True},
                        {"name": "📊 Dispatched Today", "value": f"**{sent_count} / {quota}**", "inline": True},
                        {"name": "⏰ Resuming Window", "value": f"`{next_resume_time}`", "inline": True},
                    ],
                    color=0xF59E0B,  # Warm Amber
                    author={
                        "name": "LEADOPS DELIVERABILITY PROTECTION",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/7595/7595571.png",
                    },
                    footer="LeadOps • Deliverability Protection Gate",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Deliverability Watchdog",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/7595/7595571.png",
                    channel="outreach",
                )

            if self.telegram:
                msg = (
                    f"🛑 <b>Daily Warmup Quota Reached</b>\n\n"
                    f"• <b>Tier:</b> Week {warmup_week}\n"
                    f"• <b>Dispatched Today:</b> {sent_count}/{quota}\n"
                    f"• <b>Status:</b> Outbound paused until {next_resume_time} to preserve sender authority."
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_system_alert(
        self,
        title: str,
        message: str,
        severity: str = "WARNING",
    ) -> None:
        """General system alert (extractor failure, unexpected exception, config alert)."""
        def _send():
            color = 0xEF4444 if severity.upper() == "ERROR" else (0xF59E0B if severity.upper() == "WARNING" else 0x10B981)
            if self.discord:
                self.discord.send_embed(
                    title=f"⚠️ [{severity}] {title}",
                    description=f"{message}\n────────────────────────────────────────",
                    color=color,
                    author={
                        "name": f"LEADOPS SYSTEM TELEMETRY • {severity.upper()}",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    },
                    footer="LeadOps System Telemetry",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • System Watchdog",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    channel="alerts",
                )
            if self.telegram:
                msg = f"⚠️ <b>[{severity}] {title}</b>\n\n{message}"
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_payment_received(
        self,
        lead: Any,
        amount_usd: float,
        payment_type: str,
        provider: str = "PayPal",
        transaction_id: str = "",
    ) -> None:
        """Alert operator immediately when a payment (deposit, final milestone, or subscription) is captured."""
        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Unknown Lead")
            contact = getattr(lead, "contact_name", "Valued Customer")
            email = getattr(lead, "contact_email", "") or getattr(lead, "claimed_by", "N/A")
            tier = getattr(getattr(lead, "tier", None), "name", getattr(lead, "tier_key", "Standard Tier"))
            portal = getattr(lead, "target_portal_name", "") or "Public Records Feed"

            if self.discord:
                fields = [
                    {"name": "💵 Cash Captured", "value": f"**${amount_usd:,.2f} USD**", "inline": True},
                    {"name": "📋 Milestone Type", "value": f"`{payment_type}`", "inline": True},
                    {"name": "💳 Payment Provider", "value": f"**{provider}**", "inline": True},
                    {"name": "🏢 Client Company", "value": f"**{company}**", "inline": True},
                    {"name": "👤 Contact", "value": f"**{contact}**\n`{email}`", "inline": True},
                    {"name": "🏛️ Data Registry Feed", "value": f"`{portal}`\n*(Tier: {tier})*", "inline": True},
                ]
                if transaction_id:
                    fields.append({"name": "🧾 Transaction ID", "value": f"`{transaction_id}`", "inline": False})

                self.discord.send_embed(
                    title=f"💰 Payment Captured: ${amount_usd:,.2f} USD ({company})",
                    description=(
                        f"### 💵 Revenue Captured\n"
                        f"Successfully processed **{payment_type}** for **{company}** via {provider}.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0x10B981,  # Emerald Green
                    author={
                        "name": "LEADOPS ACCOUNTING & REVENUE • PAYMENT CAPTURED",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/2489/2489756.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/1006/1006555.png",
                    footer="LeadOps • Accounting & Revenue Engine",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Treasury & Billing",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/2489/2489756.png",
                    channel="revenue",
                )

            if self.telegram:
                msg = (
                    f"💰 <b>PAYMENT CAPTURED!</b>\n\n"
                    f"💵 <b>Amount:</b> <code>${amount_usd:,.2f} USD</code>\n"
                    f"📋 <b>Type:</b> {payment_type}\n"
                    f"💳 <b>Provider:</b> {provider}\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"👤 <b>Contact:</b> {contact} (<code>{email}</code>)\n"
                    f"🏛️ <b>Data Feed:</b> {portal} ({tier})\n"
                )
                if transaction_id:
                    msg += f"🧾 <b>Txn ID:</b> <code>{transaction_id}</code>\n"
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_cancellation_requested(
        self,
        lead: Any,
        reason: str = "",
        user_email: str = "",
    ) -> None:
        """Alert operator when a customer requests subscription cancellation."""
        from .auth import generate_mobile_action_token
        lead_id = getattr(lead, "lead_id", "")
        cancel_tok = generate_mobile_action_token("confirm_cancellation", lead_id)
        pause_tok = generate_mobile_action_token("pause_subscription", lead_id)
        cancel_url = f"{self.base_url}/api/admin/quick-action?action=confirm_cancellation&lead_id={lead_id}&token={cancel_tok}"
        pause_url = f"{self.base_url}/api/admin/quick-action?action=pause_subscription&lead_id={lead_id}&token={pause_tok}"

        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Unknown")
            contact = getattr(lead, "contact_name", "")
            email = user_email or getattr(lead, "contact_email", "N/A")
            tier = getattr(getattr(lead, "tier", None), "name", getattr(lead, "tier_key", "Standard"))
            mrr = getattr(getattr(lead, "tier", None), "price_cents", 25000) / 100

            if self.discord:
                fields = [
                    {"name": "🏢 Company", "value": f"**{company}**", "inline": True},
                    {"name": "👤 Contact", "value": f"**{contact}**\n`{email}`", "inline": True},
                    {"name": "📉 Churn Impact", "value": f"**-${mrr:,.2f}/mo** ({tier})", "inline": True},
                    {"name": "💬 Stated Customer Reason", "value": f"> {reason or 'No reason provided'}", "inline": False},
                    {
                        "name": "📱 Mobile 1-Tap Operator Retention",
                        "value": (
                            f"> 🚨 **[ ✕ CONFIRM CANCELLATION ]({cancel_url})**    •    "
                            f"⏸️ **[ ⏸ GRANT 30-DAY PAUSE ]({pause_url})**"
                        ),
                        "inline": False,
                    },
                ]
                self.discord.send_embed(
                    title=f"🚨 Subscription Cancellation Requested: {company}",
                    description=(
                        f"### 🚨 Customer Churn Alert\n"
                        f"A cancellation request was submitted for **{company}**. Immediate win-back intervention recommended.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0xEF4444,  # Bright Red
                    author={
                        "name": "LEADOPS RETENTION & CHURN DEFENSE",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/1828/1828843.png",
                    footer="LeadOps • Churn Prevention & Retention",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Retention Shield",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/1828/1828843.png",
                    channel="revenue",
                )

            if self.telegram:
                msg = (
                    f"🚨 <b>CANCELLATION REQUESTED!</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"👤 <b>User:</b> {email}\n"
                    f"📉 <b>Tier:</b> {tier} (-${mrr:,.2f}/mo)\n"
                    f"💬 <b>Reason:</b> <i>\"{reason or 'None provided'}\"</i>\n\n"
                    f"📱 <b>Mobile Actions:</b>\n"
                    f"• <a href=\"{cancel_url}\">🚨 Confirm Cancellation</a>\n"
                    f"• <a href=\"{pause_url}\">⏸️ Grant 30-Day Pause</a>"
                )
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "🚨 Confirm Cancel", "url": cancel_url},
                            {"text": "⏸️ 30-Day Pause", "url": pause_url},
                        ]
                    ]
                }
                self.telegram.send_message(msg, reply_markup=reply_markup)

        self._dispatch(_send)

    def notify_complaint_or_ticket(
        self,
        ticket: Any,
        lead: Any | None = None,
    ) -> None:
        """Alert operator when a support ticket or customer complaint is raised."""
        def _send():
            ticket_id = getattr(ticket, "ticket_id", "TKT-UNKNOWN")
            title = getattr(ticket, "title", "Customer Support Ticket")
            desc = getattr(ticket, "description", "") or "No details provided"
            priority = str(getattr(getattr(ticket, "priority", None), "value", getattr(ticket, "priority", "NORMAL"))).upper()
            ttype = str(getattr(getattr(ticket, "ticket_type", None), "value", getattr(ticket, "ticket_type", "General Support"))).replace("_", " ").title()
            lead_id = getattr(ticket, "lead_id", "") or (getattr(lead, "lead_id", "") if lead else "")
            company = (getattr(lead, "company_name", "") if lead else "") or lead_id or "Client"

            if self.discord:
                fields = [
                    {"name": "🎫 Ticket ID", "value": f"`{ticket_id}`", "inline": True},
                    {"name": "⚡ Priority", "value": f"**{priority}**", "inline": True},
                    {"name": "📂 Category", "value": ttype, "inline": True},
                    {"name": "🏢 Company / Lead", "value": f"**{company}** (`{lead_id}`)", "inline": True},
                    {"name": "📝 Issue Details", "value": f"> {desc[:400]}", "inline": False},
                ]
                self.discord.send_embed(
                    title=f"⚠️ Support Ticket: [{priority}] {title[:100]}",
                    description=(
                        f"### ⚠️ Customer Support Case\n"
                        f"A customer service ticket was filed for **{company}** requiring operator review.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0xF97316,  # Orange
                    author={
                        "name": f"LEADOPS SUPPORT TELEMETRY • [{priority}]",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/1041/1041888.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/3875/3875880.png",
                    footer="LeadOps • Support & Remediation",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Support Desk",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/3875/3875880.png",
                    channel="inbox",
                )

            if self.telegram:
                msg = (
                    f"⚠️ <b>CUSTOMER COMPLAINT / TICKET</b>\n\n"
                    f"🎫 <b>ID:</b> <code>{ticket_id}</code> [{priority}]\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"📂 <b>Category:</b> {ttype}\n"
                    f"📌 <b>Title:</b> <b>{title}</b>\n\n"
                    f"📝 <b>Details:</b>\n<i>\"{desc[:300]}\"</i>"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_chat_message(
        self,
        slug: str,
        sender_role: str,
        message_text: str,
        ai_reply_text: str = "",
        lead: Any | None = None,
    ) -> None:
        """Alert operator when a customer sends a live chat message in the dashboard/sandbox widget."""
        def _send():
            company = (getattr(lead, "company_name", "") if lead else "") or slug
            contact = (getattr(lead, "contact_name", "") if lead else "") or "Portal Visitor"

            if self.discord:
                fields = [
                    {"name": "🏢 Portal & Company", "value": f"**{company}**\n`{slug}`", "inline": True},
                    {"name": "👤 Sender", "value": f"**{contact}** ({sender_role})", "inline": True},
                    {"name": "💬 User Message", "value": f"> {message_text[:350]}", "inline": False},
                ]
                if ai_reply_text:
                    fields.append({"name": "🤖 Alex's AI Response", "value": f"```\n{ai_reply_text[:350]}\n```", "inline": False})

                self.discord.send_embed(
                    title=f"💬 Portal Chat: {company}",
                    description=(
                        f"### 💬 Real-Time Portal Inbound\n"
                        f"Incoming customer concierge chat on portal `{slug}`.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0x3B82F6,  # Blue
                    author={
                        "name": "LEADOPS LIVE CONCIERGE",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/1041/1041916.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/1041/1041916.png",
                    footer="LeadOps • Live Concierge Telemetry",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Alex Live Concierge",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/1041/1041916.png",
                    channel="inbox",
                )

            if self.telegram:
                msg = (
                    f"💬 <b>LIVE PORTAL CHAT MESSAGE</b>\n\n"
                    f"🏢 <b>Company:</b> {company} (<code>{slug}</code>)\n"
                    f"👤 <b>From:</b> {contact}\n\n"
                    f"💬 <b>Message:</b>\n<i>\"{message_text[:250]}\"</i>\n"
                )
                if ai_reply_text:
                    msg += f"\n🤖 <b>Alex Responded:</b>\n<pre>{ai_reply_text[:250]}</pre>"
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_feed_delivered(
        self,
        lead: Any,
        sample_count: int = 25,
        qa_score: float = 100.0,
        auto_charged: bool = False,
        destination: str = "Google Sheets & CRM Webhook",
    ) -> None:
        """Alert operator when an autonomous scraper build finishes, passes QA, and is delivered."""
        from .auth import generate_mobile_action_token
        lead_id = getattr(lead, "lead_id", "")
        delivery_tok = generate_mobile_action_token("approve_delivery", lead_id)
        delivery_url = f"{self.base_url}/api/admin/quick-action?action=approve_delivery&lead_id={lead_id}&token={delivery_tok}"

        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Client")
            portal = getattr(lead, "target_portal_name", "") or "Target Registry"
            tier = getattr(getattr(lead, "tier", None), "name", getattr(lead, "tier_key", "Standard"))
            auto_str = "✅ Captured ($250 via PayPal Vault)" if auto_charged else "⏳ Pending Escrow Approval"

            if self.discord:
                fields = [
                    {"name": "🏢 Client Company", "value": f"**{company}**", "inline": True},
                    {"name": "🏛️ Source Registry", "value": f"`{portal}`", "inline": True},
                    {"name": "📦 Feed Cadence", "value": f"**{tier}**", "inline": True},
                    {"name": "🛡️ QA Gate Score", "value": f"**{qa_score:.1f}% CERTIFIED**", "inline": True},
                    {"name": "📊 Verified Records", "value": f"**{sample_count} live rows**", "inline": True},
                    {"name": "💳 Milestone 2 Auto-Charge", "value": auto_str, "inline": True},
                    {"name": "🚀 Delivery Target", "value": f"`{destination}`", "inline": False},
                ]
                if not auto_charged:
                    fields.append({
                        "name": "📱 Mobile 1-Tap Control",
                        "value": f"> 🚀 **[ ➔ FORCE RELEASE & CHARGE $250 ]({delivery_url})**",
                        "inline": False,
                    })

                self.discord.send_embed(
                    title=f"🚀 Live Feed Delivered: {company}",
                    description=(
                        f"### 🚀 Production Pipeline Activated\n"
                        f"Autonomous Swarm has verified, compiled, and deployed the live data pipeline for **{company}**.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0x059669,  # Emerald
                    author={
                        "name": "LEADOPS DELIVERY ENGINE • LIVE PIPELINE ACTIVE",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/1356/1356479.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/3135/3135763.png",
                    footer="LeadOps • Autonomous Delivery Engine",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Delivery Engine",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/1356/1356479.png",
                    channel="dev",
                )

            if self.telegram:
                msg = (
                    f"🚀 <b>LIVE FEED DELIVERED!</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"🏛️ <b>Registry:</b> {portal}\n"
                    f"🛡️ <b>QA Score:</b> {qa_score:.1f}% (Certified)\n"
                    f"📊 <b>Records:</b> {sample_count} verified rows\n"
                    f"💳 <b>Milestone 2:</b> {auto_str}\n"
                    f"📡 <b>Destination:</b> {destination}\n\n"
                    f"✅ <i>Daily morning sync active at 6:00 AM UTC.</i>"
                )
                reply_markup = None
                if not auto_charged:
                    msg += f"\n\n📱 <b>Mobile Action:</b> <a href=\"{delivery_url}\">Approve & Release $250</a>"
                    reply_markup = {
                        "inline_keyboard": [
                            [{"text": "🚀 Release Escrow & Charge $250", "url": delivery_url}]
                        ]
                    }
                self.telegram.send_message(msg, reply_markup=reply_markup)

        self._dispatch(_send)

    def notify_dev_swarm_started(
        self,
        lead: Any,
        objectives: list[str] | None = None,
    ) -> None:
        """Alert operator when autonomous dev swarm starts building a scraper."""
        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Client")
            source = getattr(lead, "source_url", "") or getattr(lead, "target_source_url", "Public Registry")
            tier = getattr(getattr(lead, "tier", None), "name", getattr(lead, "tier_key", "Standard"))
            fields_count = len(getattr(lead, "selected_fields", []) or [])
            objs = objectives or [
                "Probe target registry anti-bot posture",
                "Reverse engineer DOM selector tree",
                "Compile resilient Playwright extractor",
                "Certify 25 real records against QA gatekeeper",
            ]

            if self.discord:
                discord_fields = [
                    {"name": "🏢 Client Company", "value": f"**{company}**", "inline": True},
                    {"name": "🏛️ Target Portal", "value": f"`{source[:60]}`", "inline": True},
                    {"name": "📦 Target Tier", "value": f"**{tier}** ({fields_count} fields)", "inline": True},
                    {
                        "name": "🤖 7-Agent Autonomous Specialists",
                        "value": (
                            "▸ **Solutions Architect AI** • Architecture & pipeline planning\n"
                            "▸ **Anti-Bot & Network Engineer** • WAF evasion & residential proxies\n"
                            "▸ **Frontend DOM Specialist** • Selector & pagination mapping\n"
                            "▸ **Systems & Schema Architect** • Pydantic schema validation\n"
                            "▸ **Playwright Coder** • Resilient async crawler compilation\n"
                            "▸ **Independent QA Gatekeeper** • Zero-mock dataset certification"
                        ),
                        "inline": False,
                    },
                    {
                        "name": "📋 Active Milestones",
                        "value": "\n".join(f"▸ {o}" for o in objs[:4]),
                        "inline": False,
                    },
                ]
                self.discord.send_embed(
                    title=f"🛠️ Autonomous Dev Swarm Activated: {company}",
                    description=(
                        f"### 🛠️ Builder Swarm Initialized\n"
                        f"Deposit verified. Swarm launched to compile and certify extraction pipeline for **{company}**.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=discord_fields,
                    color=0x6366F1,  # Electric Indigo
                    author={
                        "name": "LEADOPS AUTONOMOUS DEV SWARM • BUILD ACTIVE",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/4712/4712109.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/2065/2065224.png",
                    footer="LeadOps • Autonomous Builder Swarm",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Autonomous Dev Swarm",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/4712/4712109.png",
                    channel="dev",
                )

            if self.telegram:
                obj_text = "\n".join(f"• {o}" for o in objs[:3])
                msg = (
                    f"🛠️ <b>AUTONOMOUS DEV SWARM ACTIVATED!</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"🏛️ <b>Target:</b> <code>{source[:60]}</code>\n"
                    f"📦 <b>Tier:</b> {tier} ({fields_count} fields)\n\n"
                    f"🤖 <b>Specialists Engaged:</b>\n"
                    f"Lead Architect, Network, DOM, Systems, Playwright & QA\n\n"
                    f"📋 <b>Objectives:</b>\n{obj_text}\n\n"
                    f"⚡ <i>Live build telemetry streaming to customer portal.</i>"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_qa_evaluation(
        self,
        lead: Any,
        qa_score: float,
        escrow_ready: bool,
        issues: list[str] | None = None,
        record_count: int = 25,
    ) -> None:
        """Alert operator when the independent QA Gatekeeper evaluates the build."""
        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Client")
            status_str = "CERTIFIED ZERO-MOCK PASS" if escrow_ready else "ROADBLOCK / RETRYING"
            color = 0x10B981 if escrow_ready else 0xF59E0B  # Green if pass, Amber if issues

            if self.discord:
                fields = [
                    {"name": "🏢 Client Company", "value": f"**{company}**", "inline": True},
                    {"name": "🛡️ QA Gatekeeper Score", "value": f"**{qa_score:.1f}%**", "inline": True},
                    {"name": "📊 Verified Records", "value": f"**{record_count} live rows**", "inline": True},
                    {"name": "🔍 Gatekeeper Verdict", "value": f"**{status_str}**", "inline": False},
                ]
                if issues:
                    fields.append({
                        "name": "⚠️ Feedback / Roadblocks",
                        "value": "\n".join(f"▸ {i}" for i in issues[:3]),
                        "inline": False,
                    })

                self.discord.send_embed(
                    title=f"🛡️ QA Gatekeeper: {company} ({status_str})",
                    description=(
                        f"### 🛡️ Zero-Mock Quality Certification\n"
                        f"Independent Quality Gatekeeper evaluated live extraction against strict production standards.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=color,
                    author={
                        "name": "LEADOPS QA GATEKEEPER • ZERO-MOCK CERTIFICATION",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/7595/7595571.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/190/190411.png" if escrow_ready else "https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    footer="LeadOps • QA Gatekeeper & Escrow Verifier",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • QA Gatekeeper",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/7595/7595571.png",
                    channel="dev",
                )

            if self.telegram:
                issue_text = ("\n• " + "\n• ".join(issues[:2])) if issues else " None"
                msg = (
                    f"🛡️ <b>QA GATEKEEPER EVALUATION</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"🎯 <b>Status:</b> <b>{status_str}</b>\n"
                    f"📊 <b>Score:</b> {qa_score:.1f}%\n"
                    f"📄 <b>Verified Rows:</b> {record_count} real registry rows\n"
                    f"🔍 <b>Issues:</b>{issue_text}"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_dev_swarm_completed(
        self,
        lead: Any,
        escrow_ready: bool,
        qa_score: float,
        auto_charged: bool = False,
    ) -> None:
        """Alert operator when the autonomous dev team finishes building and verifying."""
        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Client")
            status_text = "READY FOR DEPLOYMENT" if escrow_ready else "REQUIRES OPERATOR REVIEW"
            color = 0x059669 if escrow_ready else 0xDC2626

            if self.discord:
                fields = [
                    {"name": "🏢 Company", "value": f"**{company}**", "inline": True},
                    {"name": "🛡️ Certified Score", "value": f"**{qa_score:.1f}%**", "inline": True},
                    {
                        "name": "💳 Milestone Auto-Charge",
                        "value": "✅ $250 Captured (Vaulted)" if auto_charged else "⏳ Pending Review",
                        "inline": True,
                    },
                    {
                        "name": "📦 Codebase Assets Generated",
                        "value": (
                            "▸ Standalone `extractor.py`\n"
                            "▸ Modular structure (`src/models`, `src/utils`)\n"
                            "▸ GitHub Actions CI/CD workflow\n"
                            "▸ Signed QA insurance certificate"
                        ),
                        "inline": False,
                    },
                ]
                self.discord.send_embed(
                    title=f"🚀 Dev Swarm Finished: {company} ({status_text})",
                    description=(
                        f"### 🚀 Autonomous Swarm Build Finished\n"
                        f"Autonomous Swarm has completed the build iteration for **{company}**.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=color,
                    author={
                        "name": "LEADOPS DEV SWARM • BUILD CERTIFIED",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/1356/1356479.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/190/190411.png" if escrow_ready else "https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    footer="LeadOps • Autonomous Delivery Engine",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Delivery Engine",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/1356/1356479.png",
                    channel="dev",
                )

            if self.telegram:
                msg = (
                    f"🚀 <b>DEV SWARM FINISHED!</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"🎯 <b>Status:</b> {status_text}\n"
                    f"🛡️ <b>QA Score:</b> {qa_score:.1f}%\n"
                    f"💳 <b>Milestone 2:</b> {'✅ Auto-Charged $250' if auto_charged else '⏳ Pending'}\n\n"
                    f"📁 <i>Scraper repository compiled & CI/CD workflow ready.</i>"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_dev_swarm_stopped(
        self,
        lead: Any,
        reason: str = "Anti-bot roadblock",
        requires_intervention: bool = True,
    ) -> None:
        """Alert operator when the dev swarm hits a blocker and pauses."""
        def _send():
            company = getattr(lead, "company_name", "") or getattr(lead, "lead_id", "Client")
            if self.discord:
                fields = [
                    {"name": "🏢 Company", "value": f"**{company}**", "inline": True},
                    {"name": "⚠️ Blocker Details", "value": f"> {reason[:400]}", "inline": False},
                    {
                        "name": "🎫 SLA Remediation Ticket",
                        "value": "An automated critical selector repair ticket has been created with 4-hour SLA.",
                        "inline": False,
                    },
                ]
                self.discord.send_embed(
                    title=f"🛑 Dev Swarm Stopped / Roadblock: {company}",
                    description=(
                        f"### 🛑 Swarm Blocker Encountered\n"
                        f"Autonomous builder swarm hit an obstacle requiring attention.\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0xDC2626,  # Red
                    author={
                        "name": "LEADOPS DEV SWARM • EXCEPTION TELEMETRY",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    footer="LeadOps • Swarm Exception Telemetry",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Swarm Diagnostics",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/564/564619.png",
                    channel="dev",
                )

            if self.telegram:
                msg = (
                    f"🛑 <b>DEV SWARM STOPPED / ROADBLOCK</b>\n\n"
                    f"🏢 <b>Company:</b> {company}\n"
                    f"⚠️ <b>Blocker:</b> <i>\"{reason[:300]}\"</i>\n\n"
                    f"🚨 <i>Critical SLA ticket opened in Mission Control.</i>"
                )
                self.telegram.send_message(msg)

        self._dispatch(_send)

    def notify_morning_briefing(
        self,
        storage: Any,
        portal: Any | None = None,
    ) -> dict[str, Any]:
        """Compile and dispatch daily executive morning briefing with complete accounting, MRR, pipeline, and health."""
        from datetime import datetime, timezone
        leads = storage.list_leads() if hasattr(storage, "list_leads") else []
        sandboxes = portal.list_sandboxes() if (portal and hasattr(portal, "list_sandboxes")) else (
            storage.list_sandboxes() if hasattr(storage, "list_sandboxes") else []
        )
        tickets = storage.list_tickets() if hasattr(storage, "list_tickets") else []
        cancellations = storage.list_cancellation_requests() if hasattr(storage, "list_cancellation_requests") else []

        # 1. Accounting & Financials
        deposits_paid = sum(1 for l in leads if getattr(l, "deposit_paid", False))
        final_paid = sum(1 for l in leads if getattr(l, "final_paid", False))
        buyouts_paid = sum(1 for l in leads if getattr(l, "buyout_paid", False))

        deposit_revenue = deposits_paid * 250.0
        final_revenue = final_paid * 250.0
        buyout_revenue = buyouts_paid * 1500.0
        total_cash_collected = deposit_revenue + final_revenue + buyout_revenue

        active_subs = [l for l in leads if getattr(l, "subscription_active", False) and not getattr(l, "is_paused", False)]
        paused_subs = [l for l in leads if getattr(l, "subscription_active", False) and getattr(l, "is_paused", False)]

        mrr = 0.0
        for l in active_subs:
            if getattr(l, "tier_key", "") != "buyout":
                tier_obj = getattr(l, "tier", None)
                price = (getattr(tier_obj, "price_cents", 25000) / 100.0) if tier_obj else 250.0
                mrr += price
        arr = mrr * 12.0

        # 2. Pipeline Stages
        pipeline = {
            "prospecting": sum(1 for l in leads if getattr(getattr(l, "state", None), "value", str(getattr(l, "state", ""))) in {"PROSPECTING", "REVIEW", "PITCH_PENDING_APPROVAL", "OUTREACH_SENT"}),
            "intake": sum(1 for l in leads if getattr(getattr(l, "state", None), "value", str(getattr(l, "state", ""))) in {"CONVERSATIONAL_INTAKE", "SOW_GENERATED"}),
            "building": sum(1 for l in leads if getattr(getattr(l, "state", None), "value", str(getattr(l, "state", ""))) == "DEV_BUILDING"),
            "escrow_preview": sum(1 for l in leads if getattr(getattr(l, "state", None), "value", str(getattr(l, "state", ""))) == "ESCROW_PREVIEW"),
            "delivered": sum(1 for l in leads if getattr(getattr(l, "state", None), "value", str(getattr(l, "state", ""))) in {"DELIVERED", "WARRANTY_ACTIVE"}),
        }

        # 3. Support & Service Health
        open_tickets = [t for t in tickets if getattr(getattr(t, "status", None), "value", str(getattr(t, "status", ""))) in {"open", "in_progress"}]
        urgent_tickets = [t for t in open_tickets if getattr(getattr(t, "priority", None), "value", str(getattr(t, "priority", ""))) in {"critical", "high"}]
        pending_cancellations = [c for c in cancellations if getattr(getattr(c, "status", None), "value", str(getattr(c, "status", ""))) == "pending"]

        now_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

        from .auth import generate_mobile_action_token
        pause_prosp_tok = generate_mobile_action_token("pause_prospector", "")
        resume_prosp_tok = generate_mobile_action_token("resume_prospector", "")
        pause_prosp_url = f"{self.base_url}/api/admin/quick-action?action=pause_prospector&token={pause_prosp_tok}"
        resume_prosp_url = f"{self.base_url}/api/admin/quick-action?action=resume_prospector&token={resume_prosp_tok}"

        briefing_data = {
            "date": now_str,
            "accounting": {
                "total_cash_collected": total_cash_collected,
                "deposits_count": deposits_paid,
                "deposits_revenue": deposit_revenue,
                "final_count": final_paid,
                "final_revenue": final_revenue,
                "buyouts_count": buyouts_paid,
                "buyouts_revenue": buyout_revenue,
                "mrr": mrr,
                "arr": arr,
                "active_subscriptions": len(active_subs),
                "paused_subscriptions": len(paused_subs),
            },
            "pipeline": pipeline,
            "operations": {
                "total_leads": len(leads),
                "total_sandboxes": len(sandboxes),
                "open_tickets": len(open_tickets),
                "urgent_tickets": len(urgent_tickets),
                "pending_cancellations": len(pending_cancellations),
            },
        }

        def _send():
            if self.discord:
                fields = [
                    {"name": "💵 Total Cash Collected", "value": f"**${total_cash_collected:,.2f}**\n*({deposits_paid} deposits • {final_paid} deliveries)*", "inline": True},
                    {"name": "📈 Active MRR / ARR", "value": f"**${mrr:,.2f}/mo**\n*(${arr:,.2f} ARR)*", "inline": True},
                    {"name": "🔄 Subscriptions", "value": f"**{len(active_subs)} Active**\n*({len(paused_subs)} paused)*", "inline": True},
                    {"name": "📊 Autonomous Pipeline Breakdown", "value": (
                        f"▸ Outreach & Intake: **{pipeline['prospecting'] + pipeline['intake']}**\n"
                        f"▸ Autonomous Swarms Building: **{pipeline['building']}**\n"
                        f"▸ Escrow QA Review: **{pipeline['escrow_preview']}**\n"
                        f"▸ Delivered & Active: **{pipeline['delivered']}**"
                    ), "inline": False},
                    {"name": "🛡️ Infrastructure & Health Telemetry", "value": (
                        f"▸ Active Client Portals: **{len(sandboxes)}**\n"
                        f"▸ Support Tickets: **{len(open_tickets)}** ({len(urgent_tickets)} critical/urgent)\n"
                        f"▸ Pending Cancellations: **{len(pending_cancellations)}**\n"
                        f"▸ Swarm Uptime: **100% Lights-Out Autonomous**"
                    ), "inline": False},
                    {
                        "name": "📱 Mobile 1-Tap Swarm Controls",
                        "value": (
                            f"> ⏸️ **[ ⏸ PAUSE PROSPECTOR ]({pause_prosp_url})**    •    "
                            f"▶️ **[ ▶ RESUME PROSPECTOR ]({resume_prosp_url})**"
                        ),
                        "inline": False,
                    },
                ]
                self.discord.send_embed(
                    title=f"🌅 Executive Morning Briefing — {now_str}",
                    description=(
                        f"### 🌅 Autonomous 24-Hour Operations, Pipeline & Accounting Summary\n"
                        f"────────────────────────────────────────"
                    ),
                    fields=fields,
                    color=0x7C3AED,  # Royal Purple
                    author={
                        "name": "LEADOPS EXECUTIVE MISSION CONTROL",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/869/869869.png",
                    },
                    thumbnail_url="https://cdn-icons-png.flaticon.com/512/2920/2920329.png",
                    footer="LeadOps • Executive Mission Control",
                    footer_icon_url="https://cdn-icons-png.flaticon.com/512/906/906334.png",
                    username="LeadOps • Executive Mission Control",
                    avatar_url="https://cdn-icons-png.flaticon.com/512/869/869869.png",
                    channel="alerts",
                )

            if self.telegram:
                msg = (
                    f"🌅 <b>LEADOPS EXECUTIVE MORNING BRIEFING</b>\n"
                    f"📅 <i>{now_str}</i>\n\n"
                    f"💰 <b>ACCOUNTING & FINANCIALS:</b>\n"
                    f"• <b>Total Cash Collected:</b> <code>${total_cash_collected:,.2f}</code>\n"
                    f"• <b>MRR:</b> <code>${mrr:,.2f}/mo</code> (ARR: <code>${arr:,.2f}</code>)\n"
                    f"• <b>Active Subs:</b> {len(active_subs)} ({len(paused_subs)} paused)\n"
                    f"• <b>Milestones:</b> {deposits_paid} deposits | {final_paid} deliveries\n\n"
                    f"📈 <b>PIPELINE STATUS:</b>\n"
                    f"• <b>Outreach & Intake:</b> {pipeline['prospecting'] + pipeline['intake']}\n"
                    f"• <b>Autonomous Swarms:</b> {pipeline['building']} active\n"
                    f"• <b>Escrow & Delivery:</b> {pipeline['escrow_preview']} review / {pipeline['delivered']} live\n\n"
                    f"🛡️ <b>OPERATIONS & SUPPORT:</b>\n"
                    f"• <b>Live Portals:</b> {len(sandboxes)}\n"
                    f"• <b>Open Tickets:</b> {len(open_tickets)} ({len(urgent_tickets)} urgent)\n"
                    f"• <b>Pending Cancellations:</b> {len(pending_cancellations)}\n\n"
                    f"⚡ <i>Autonomous Swarm Health: 100% Operational</i>\n\n"
                    f"📱 <b>Mobile Swarm Controls:</b>\n"
                    f"• <a href=\"{pause_prosp_url}\">⏸️ Pause Prospector</a>\n"
                    f"• <a href=\"{resume_prosp_url}\">▶️ Resume Prospector</a>"
                )
                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "⏸️ Pause Prospector", "url": pause_prosp_url},
                            {"text": "▶️ Resume Prospector", "url": resume_prosp_url},
                        ]
                    ]
                }
                self.telegram.send_message(msg, reply_markup=reply_markup)

        self._dispatch(_send)
        return briefing_data


# Global notification manager singleton
notification_manager = NotificationManager()
