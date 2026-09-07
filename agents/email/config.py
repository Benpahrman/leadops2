"""Configuration dataclass and environment loader for LeadOps native email module."""

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class EmailSettings:
    """Settings for company Gmail SMTP dispatch, IMAP listening, warmup, and outreach."""

    # Authentication & Mailbox
    user: str = ""
    app_password: str = ""
    from_name: str = "Alex | LeadOps"
    from_email: str = ""

    # Legacy SendPulse compatibility fields
    client_id: str = ""
    client_secret: str = ""


    # SMTP Configuration
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    smtp_timeout: int = 20

    # IMAP Configuration (Cloudflare Email Routing to Gmail)
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    imap_timeout: int = 20
    imap_poll_interval_seconds: int = 60

    # Warmup Schedule Limits (emails/day)
    warmup_week1_limit: int = 25
    warmup_week2_limit: int = 50
    warmup_week3_limit: int = 75
    warmup_week4_limit: int = 100
    warmup_start_date: str = ""

    # Cold Email Link Delivery Strategy
    # 'permission_first': Zero links in initial cold email; AI delivers sandbox link on prospect reply (highest deliverability)
    # 'direct_link': Direct branded sandbox link in initial email (for warmed domains)
    # 'plain_domain': Clean text URL without HTML anchor tags
    cold_email_link_mode: Literal["permission_first", "direct_link", "plain_domain"] = "permission_first"

    # Outreach Safety Lock / Kill-Switch
    # When False, system runs in Safe / Dry-Run mode: NO real emails sent via SMTP
    outreach_dispatch_enabled: bool = False

    # Multi-Inbox Accounts (list of {id, user, password, from_name, from_email, start_date})
    extra_inboxes: list[dict[str, str]] = field(default_factory=list)

    # Cloudflare Registered Sending Subdomains (email.omnileadfeeder.tech & contact.omnileadfeeder.tech)
    allowed_sending_domains: list[str] = field(
        default_factory=lambda: ["email.omnileadfeeder.tech", "contact.omnileadfeeder.tech"]
    )
    outreach_sending_domains: list[str] = field(
        default_factory=lambda: ["email.omnileadfeeder.tech", "contact.omnileadfeeder.tech"]
    )
    sending_strategy: Literal["rotate", "email_only", "contact_only"] = "rotate"

    def resolve_sender_email(self, hint: str = "", preferred_domain: str | None = None) -> str:
        """Resolve the authentic From: address enforcing registered Cloudflare sending domains.
        
        Guarantees sender domain is either email.omnileadfeeder.tech or contact.omnileadfeeder.tech.
        """
        raw_email = (self.from_email or "").strip()
        user_part = "alex"
        explicit_domain = ""

        if "@" in raw_email:
            parts = raw_email.split("@", 1)
            user_part = parts[0] or "alex"
            explicit_domain = parts[1].lower().strip()

        # If user explicitly preferred a domain that is valid
        if preferred_domain and preferred_domain.lower().strip() in self.allowed_sending_domains:
            return f"{user_part}@{preferred_domain.lower().strip()}"

        # If configured from_email already uses one of the allowed Cloudflare subdomains, use it
        if explicit_domain in self.allowed_sending_domains:
            return f"{user_part}@{explicit_domain}"

        # Strategy-based selection from pool
        active_pool = self.outreach_sending_domains or self.allowed_sending_domains
        if self.sending_strategy == "contact_only" and "contact.omnileadfeeder.tech" in active_pool:
            return f"{user_part}@contact.omnileadfeeder.tech"
        elif self.sending_strategy == "email_only" and "email.omnileadfeeder.tech" in active_pool:
            return f"{user_part}@email.omnileadfeeder.tech"

        # Rotate based on hint (e.g. recipient email or lead_id)
        if hint:
            idx = sum(ord(c) for c in hint) % len(active_pool)
            chosen = active_pool[idx]
        else:
            chosen = active_pool[0]

        return f"{user_part}@{chosen}"

    @classmethod
    def from_environment(cls) -> "EmailSettings":
        """Load email configuration dynamically from environment variables."""
        user = (
            os.environ.get("GMAIL_USER")
            or os.environ.get("LEADOPS_EMAIL_USER")
            or os.environ.get("SMTP_USER")
            or ""
        ).strip()

        app_password = (
            os.environ.get("GMAIL_APP_PASSWORD")
            or os.environ.get("LEADOPS_EMAIL_PASSWORD")
            or os.environ.get("SMTP_PASSWORD")
            or ""
        ).strip()

        from_name = os.environ.get("EMAIL_FROM_NAME", "Alex | OmniLeadFeeder").strip()
        from_email = (
            os.environ.get("EMAIL_FROM_EMAIL")
            or "alex@email.omnileadfeeder.tech"
        ).strip()

        # Cloudflare Sending Subdomains
        outreach_domains_raw = os.environ.get("OUTREACH_SENDING_DOMAINS", "").strip()
        if outreach_domains_raw:
            outreach_sending_domains = [d.strip().lower() for d in outreach_domains_raw.split(",") if d.strip()]
        else:
            outreach_sending_domains = ["email.omnileadfeeder.tech", "contact.omnileadfeeder.tech"]

        sending_strategy_raw = os.environ.get("OUTREACH_SENDING_STRATEGY", "rotate").strip().lower()
        sending_strategy: Literal["rotate", "email_only", "contact_only"] = (
            "contact_only"
            if sending_strategy_raw == "contact_only"
            else "email_only"
            if sending_strategy_raw == "email_only"
            else "rotate"
        )

        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com").strip()
        smtp_port = int(os.environ.get("SMTP_PORT", "465"))
        smtp_use_ssl = smtp_port == 465 or os.environ.get("SMTP_USE_SSL", "true").lower() == "true"
        smtp_use_tls = smtp_port == 587 or os.environ.get("SMTP_USE_TLS", "false").lower() == "true"

        imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com").strip()
        imap_port = int(os.environ.get("IMAP_PORT", "993"))
        imap_use_ssl = os.environ.get("IMAP_USE_SSL", "true").lower() == "true"
        imap_poll_interval_seconds = int(os.environ.get("IMAP_POLL_INTERVAL_SECONDS", "60"))

        warmup_week1_limit = int(os.environ.get("WARMUP_WEEK1_LIMIT", "25"))
        warmup_week2_limit = int(os.environ.get("WARMUP_WEEK2_LIMIT", "50"))
        warmup_week3_limit = int(os.environ.get("WARMUP_WEEK3_LIMIT", "75"))
        warmup_week4_limit = int(os.environ.get("WARMUP_WEEK4_LIMIT", "100"))
        warmup_start_date = os.environ.get("WARMUP_START_DATE", "").strip()

        link_mode_raw = os.environ.get("COLD_EMAIL_LINK_MODE", "permission_first").strip().lower()
        link_mode: Literal["permission_first", "direct_link", "plain_domain"] = (
            "direct_link"
            if link_mode_raw == "direct_link"
            else "plain_domain"
            if link_mode_raw == "plain_domain"
            else "permission_first"
        )

        outreach_dispatch_enabled = os.environ.get(
            "OUTREACH_DISPATCH_ENABLED",
            "true" if os.environ.get("PYTEST_CURRENT_TEST") else "false",
        ).strip().lower() in ("true", "1", "yes")

        return cls(
            user=user,
            app_password=app_password,
            from_name=from_name,
            from_email=from_email,
            allowed_sending_domains=["email.omnileadfeeder.tech", "contact.omnileadfeeder.tech"],
            outreach_sending_domains=outreach_sending_domains,
            sending_strategy=sending_strategy,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_use_ssl=smtp_use_ssl,
            smtp_use_tls=smtp_use_tls,
            imap_host=imap_host,
            imap_port=imap_port,
            imap_use_ssl=imap_use_ssl,
            imap_poll_interval_seconds=imap_poll_interval_seconds,
            warmup_week1_limit=warmup_week1_limit,
            warmup_week2_limit=warmup_week2_limit,
            warmup_week3_limit=warmup_week3_limit,
            warmup_week4_limit=warmup_week4_limit,
            warmup_start_date=warmup_start_date,
            cold_email_link_mode=link_mode,
            outreach_dispatch_enabled=outreach_dispatch_enabled,
        )
