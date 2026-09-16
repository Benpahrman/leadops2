"""Configuration dataclass and environment loader for LeadOps native email module."""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger("leadops.email.config")


@dataclass
class InboxAccountConfig:
    """Configuration for an individual inbox account (Zoho, Gmail, or Generic SMTP)."""

    id: str
    email_address: str
    password: str
    provider: Literal["zoho", "gmail", "smtp_generic"] = "zoho"
    from_name: str = "Alex | OmniLeadFeeder"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    imap_host: str = ""
    imap_port: int = 993
    imap_use_ssl: bool = True
    imap_enabled: bool = True
    warmup_start_date: str = ""
    daily_limit: int = 25
    is_active: bool = True

    def __post_init__(self) -> None:
        """Auto-configure host and port presets based on provider if not explicitly provided."""
        clean_email = (self.email_address or "").strip().lower()
        if self.provider == "zoho":
            if not self.smtp_host:
                self.smtp_host = "smtp.zoho.com"
            if not self.imap_host:
                self.imap_host = "imap.zoho.com"
        elif self.provider == "gmail":
            if not self.smtp_host:
                self.smtp_host = "smtp.gmail.com"
            if not self.imap_host:
                self.imap_host = "imap.gmail.com"
        elif self.provider in ("outlook", "office365", "microsoft") or any(clean_email.endswith(d) for d in ("@outlook.com", "@hotmail.com", "@live.com", "@office365.com")):
            if not self.provider or self.provider in ("smtp_generic", "primary"):
                self.provider = "outlook"
            if not self.smtp_host:
                self.smtp_host = "smtp-mail.outlook.com"
            if not self.smtp_port or self.smtp_port == 465:
                self.smtp_port = 587
                self.smtp_use_ssl = False
                self.smtp_use_tls = True
            if not self.imap_host:
                self.imap_host = "outlook.office365.com"
            if not self.imap_port:
                self.imap_port = 993
                self.imap_use_ssl = True


@dataclass
class EmailSettings:
    """Settings for company Gmail/Zoho SMTP dispatch, IMAP listening, warmup, and outreach."""

    # Authentication & Mailbox (Primary / Default)
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

    # IMAP Configuration (Cloudflare Email Routing to Gmail / Zoho)
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

    # Fully typed multi-inbox pool (including Zoho inboxes)
    inbox_pool: list[InboxAccountConfig] = field(default_factory=list)

    # Allowed Outbound Sending Domains
    allowed_sending_domains: list[str] = field(
        default_factory=lambda: [
            "olfmailer.com",
            "olfmailer.net",
            "email.omnileadfeeder.tech",
            "contact.omnileadfeeder.tech",
        ]
    )
    outreach_sending_domains: list[str] = field(
        default_factory=lambda: [
            "olfmailer.com",
            "olfmailer.net",
            "email.omnileadfeeder.tech",
            "contact.omnileadfeeder.tech",
        ]
    )
    sending_strategy: Literal["rotate", "email_only", "contact_only"] = "rotate"

    # Azure Communication Services (ACS) Configuration
    azure_communication_connection_string: str = ""
    azure_communication_sender_domain: str = "olfmailer.com"
    azure_communication_sender_email: str = "ben@olfmailer.com"

    # Outbound Dispatch Policy: When False, strictly use dedicated custom domain/Zoho inboxes for outbound pitches, reserving Gmail for inbound replies and monitoring
    outbound_use_gmail: bool = False

    # Microsoft OAuth2 & Graph API Integration (Option 3 for watched Outlook inbox)
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_refresh_token: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/api/admin/oauth/microsoft/callback"

    # External Email Discovery & Verification APIs (Free-tier Fallbacks)
    hunter_api_key: str = ""
    apollo_api_key: str = ""

    def is_azure_communication_ready(self) -> bool:
        """Return True if Azure Communication Services is configured."""
        return bool(self.azure_communication_connection_string and "endpoint=" in self.azure_communication_connection_string.lower())

    def is_microsoft_oauth_ready(self) -> bool:
        """Return True if Microsoft OAuth is configured and authorized with a refresh token."""
        return bool(self.microsoft_client_id and self.microsoft_client_secret and self.microsoft_refresh_token)

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

    def get_outbound_inboxes(self) -> list[InboxAccountConfig]:
        """Return only inboxes authorized for outbound cold outreach (excluding monitored personal/reply inboxes unless explicitly enabled)."""
        all_inboxes = self.get_all_inboxes()
        olf_or_custom = [inb for inb in all_inboxes if inb.provider not in ("gmail", "outlook") and inb.id != "primary"]
        if olf_or_custom and not self.outbound_use_gmail:
            return olf_or_custom
        return all_inboxes

    def get_all_inboxes(self) -> list[InboxAccountConfig]:
        """Return all active and configured inbox accounts (monitored primary inbox + olfmailer sending pool)."""
        accounts: list[InboxAccountConfig] = []
        existing_ids: set[str] = set()

        # 1. Monitored primary inbox (for incoming prospect replies & IMAP watcher)
        user_lower = (self.user or "").lower()
        if (
            "outlook" in self.smtp_host.lower()
            or "office365" in self.smtp_host.lower()
            or "outlook" in self.imap_host.lower()
            or "office365" in self.imap_host.lower()
            or any(user_lower.endswith(d) for d in ("@outlook.com", "@hotmail.com", "@live.com", "@office365.com"))
        ):
            primary_provider = "outlook"
        elif "gmail" in self.smtp_host.lower() or not self.smtp_host:
            primary_provider = "gmail"
        else:
            primary_provider = "custom"

        primary_addr = self.user or "alex@olfmailer.com"
        accounts.append(
            InboxAccountConfig(
                id="primary",
                email_address=primary_addr,
                password=self.app_password,
                provider=primary_provider,
                from_name=self.from_name,
                smtp_host=self.smtp_host,
                smtp_port=self.smtp_port,
                smtp_use_ssl=self.smtp_use_ssl,
                smtp_use_tls=self.smtp_use_tls,
                imap_host=self.imap_host,
                imap_port=self.imap_port,
                imap_use_ssl=self.imap_use_ssl,
                warmup_start_date=self.warmup_start_date,
                daily_limit=self.warmup_week1_limit,
                is_active=True,
            )
        )
        existing_ids.add("primary")

        # 2. Structured inbox pool (olfmailer sending accounts)
        for inbox in self.inbox_pool:
            if inbox.id not in existing_ids:
                accounts.append(inbox)
                existing_ids.add(inbox.id)

        # 3. Custom extra_inboxes dictionary format
        for i, extra in enumerate(self.extra_inboxes):
            inbox_id = extra.get("id") or f"inbox_{i+1}"
            if inbox_id in existing_ids:
                continue
            email_addr = extra.get("email_address") or extra.get("user") or extra.get("email") or ""
            pwd = extra.get("password") or extra.get("app_password") or ""
            provider = extra.get("provider", "olfmailer" if "olfmailer" in email_addr else "custom")
            accounts.append(
                InboxAccountConfig(
                    id=inbox_id,
                    email_address=email_addr,
                    password=pwd,
                    provider=provider,
                    from_name=extra.get("from_name", self.from_name),
                    smtp_host=extra.get("smtp_host", ""),
                    smtp_port=int(extra.get("smtp_port", 465)),
                    smtp_use_ssl=str(extra.get("smtp_use_ssl", "true")).lower() == "true",
                    imap_host=extra.get("imap_host", ""),
                    imap_port=int(extra.get("imap_port", 993)),
                    imap_use_ssl=str(extra.get("imap_use_ssl", "true")).lower() == "true",
                    warmup_start_date=extra.get("warmup_start_date", self.warmup_start_date),
                    daily_limit=int(extra.get("daily_limit", self.warmup_week1_limit)),
                    is_active=str(extra.get("is_active", "true")).lower() in ("true", "1", "yes"),
                )
            )
            existing_ids.add(inbox_id)

        return accounts

    @classmethod
    def from_environment(cls) -> "EmailSettings":
        """Load email configuration dynamically from environment variables."""
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            from dotenv import load_dotenv
            load_dotenv(override=True)
        user = (
            os.environ.get("INBOX_WATCHER_EMAIL")
            or os.environ.get("OUTLOOK_USER")
            or os.environ.get("OUTLOOK_EMAIL")
            or os.environ.get("GMAIL_USER")
            or os.environ.get("LEADOPS_EMAIL_USER")
            or os.environ.get("SMTP_USER")
            or ""
        ).strip()

        user_lower = user.lower()
        is_outlook = any(user_lower.endswith(d) for d in ("@outlook.com", "@hotmail.com", "@live.com", "@office365.com")) or "outlook" in user_lower
        is_gmail = any(user_lower.endswith(d) for d in ("@gmail.com", "@googlemail.com")) or "gmail" in user_lower

        if is_gmail:
            app_password = (
                os.environ.get("GMAIL_APP_PASSWORD")
                or os.environ.get("INBOX_WATCHER_PASSWORD")
                or os.environ.get("LEADOPS_EMAIL_PASSWORD")
                or os.environ.get("SMTP_PASSWORD")
                or ""
            ).strip()
        elif is_outlook:
            app_password = (
                os.environ.get("OUTLOOK_APP_PASSWORD")
                or os.environ.get("OUTLOOK_PASSWORD")
                or os.environ.get("INBOX_WATCHER_PASSWORD")
                or os.environ.get("LEADOPS_EMAIL_PASSWORD")
                or os.environ.get("SMTP_PASSWORD")
                or ""
            ).strip()
        else:
            app_password = (
                os.environ.get("INBOX_WATCHER_PASSWORD")
                or os.environ.get("OUTLOOK_APP_PASSWORD")
                or os.environ.get("GMAIL_APP_PASSWORD")
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

        def _clean_int(val: Any, default: int) -> int:
            try:
                return int(str(val).split("#")[0].strip().strip("\"'"))
            except (ValueError, TypeError):
                return default

        user_lower = user.lower()
        is_outlook = any(user_lower.endswith(d) for d in ("@outlook.com", "@hotmail.com", "@live.com", "@office365.com")) or "outlook" in user_lower
        is_gmail = any(user_lower.endswith(d) for d in ("@gmail.com", "@googlemail.com")) or "gmail" in user_lower

        default_smtp_host = "smtp-mail.outlook.com" if is_outlook else "smtp.gmail.com"
        default_imap_host = "outlook.office365.com" if is_outlook else "imap.gmail.com"
        default_smtp_port = 587 if is_outlook else 465

        smtp_host = os.environ.get("SMTP_HOST", default_smtp_host).strip()
        smtp_port = _clean_int(os.environ.get("SMTP_PORT", str(default_smtp_port)), default_smtp_port)
        smtp_use_ssl = (
            (str(os.environ.get("SMTP_USE_SSL", "").lower()) == "true")
            if os.environ.get("SMTP_USE_SSL")
            else (smtp_port == 465 and not is_outlook)
        )
        smtp_use_tls = (
            (str(os.environ.get("SMTP_USE_TLS", "").lower()) == "true")
            if os.environ.get("SMTP_USE_TLS")
            else (smtp_port == 587 or is_outlook)
        )

        if is_gmail:
            imap_host = os.environ.get("IMAP_HOST", "imap.gmail.com").strip()
            if imap_host == "outlook.office365.com":
                imap_host = "imap.gmail.com"
        elif is_outlook:
            imap_host = os.environ.get("IMAP_HOST", "outlook.office365.com").strip()
            if imap_host == "imap.gmail.com":
                imap_host = "outlook.office365.com"
        else:
            imap_host = os.environ.get("IMAP_HOST", default_imap_host).strip()

        imap_port = _clean_int(os.environ.get("IMAP_PORT", "993"), 993)
        imap_use_ssl = os.environ.get("IMAP_USE_SSL", "true").lower() == "true"
        imap_poll_interval_seconds = _clean_int(os.environ.get("IMAP_POLL_INTERVAL_SECONDS", "60"), 60)

        warmup_week1_limit = _clean_int(os.environ.get("WARMUP_WEEK1_LIMIT", "25"), 25)
        warmup_week2_limit = _clean_int(os.environ.get("WARMUP_WEEK2_LIMIT", "50"), 50)
        warmup_week3_limit = _clean_int(os.environ.get("WARMUP_WEEK3_LIMIT", "75"), 75)
        warmup_week4_limit = _clean_int(os.environ.get("WARMUP_WEEK4_LIMIT", "100"), 100)
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

        inbox_pool: list[InboxAccountConfig] = []

        # 1. Parse olfmailer.com inboxes: OLFMAILER_INBOXES_JSON, INBOXES_CONFIG_JSON, or default 3 inboxes
        olf_inboxes_raw = os.environ.get("OLFMAILER_INBOXES_JSON") or os.environ.get("INBOXES_CONFIG_JSON") or ""
        if olf_inboxes_raw.strip():
            try:
                parsed_list = json.loads(olf_inboxes_raw)
                if isinstance(parsed_list, list):
                    for idx, item in enumerate(parsed_list):
                        if isinstance(item, dict):
                            addr = item.get("email_address") or item.get("email") or ""
                            if addr:
                                inbox_pool.append(
                                    InboxAccountConfig(
                                        id=item.get("id") or f"olf_{idx+1}",
                                        email_address=addr,
                                        password=item.get("password") or item.get("app_password") or "",
                                        provider="olfmailer",
                                        from_name=item.get("from_name", from_name),
                                        smtp_host=item.get("smtp_host", ""),
                                        smtp_port=int(item.get("smtp_port", 465)),
                                        daily_limit=int(item.get("daily_limit", warmup_week1_limit)),
                                        warmup_start_date=item.get("warmup_start_date", warmup_start_date),
                                        is_active=str(item.get("is_active", "true")).lower() in ("true", "1", "yes"),
                                    )
                                )
            except Exception as err:
                logger.error(f"Failed to parse OLFMAILER_INBOXES_JSON: {err}")

        # 2. Default to the 3 official olfmailer.com sending identities
        if not inbox_pool:
            default_olf = [
                ("olf_ben", "ben@olfmailer.com", "Ben | OmniLeadFeeder"),
                ("olf_alex", "alex@olfmailer.com", "Alex | OmniLeadFeeder"),
                ("olf_contact", "contact@olfmailer.com", "OmniLeadFeeder Operations"),
            ]
            for id_slug, addr, disp_name in default_olf:
                inbox_pool.append(
                    InboxAccountConfig(
                        id=id_slug,
                        email_address=addr,
                        password="",
                        provider="olfmailer",
                        from_name=disp_name,
                        daily_limit=warmup_week1_limit,
                        warmup_start_date=warmup_start_date,
                        is_active=True,
                    )
                )

        outbound_use_gmail = os.environ.get("OUTBOUND_USE_GMAIL", "false").strip().lower() in ("true", "1", "yes")

        microsoft_client_id = (os.environ.get("MICROSOFT_CLIENT_ID") or os.environ.get("AZURE_CLIENT_ID") or "").strip().strip("\"'")
        microsoft_client_secret = (os.environ.get("MICROSOFT_CLIENT_SECRET") or os.environ.get("AZURE_CLIENT_SECRET") or "").strip().strip("\"'")
        microsoft_tenant_id = (os.environ.get("MICROSOFT_TENANT_ID") or "common").strip().strip("\"'")
        microsoft_refresh_token = (os.environ.get("MICROSOFT_REFRESH_TOKEN") or "").strip().strip("\"'")
        microsoft_redirect_uri = (os.environ.get("MICROSOFT_REDIRECT_URI") or "http://localhost:8000/api/admin/oauth/microsoft/callback").strip().strip("\"'")

        # Azure Communication Services
        azure_comm_conn = (
            os.environ.get("AZURE_COMMUNICATION_SERVICES_CONNECTION_STRING")
            or os.environ.get("AZURE_COMMUNICATION_CONNECTION_STRING")
            or ""
        ).strip().strip("\"'")
        azure_comm_domain = os.environ.get("AZURE_COMMUNICATION_SENDER_DOMAIN", "olfmailer.com").strip().strip("\"'")
        azure_comm_sender = os.environ.get("AZURE_COMMUNICATION_SENDER_EMAIL", f"ben@{azure_comm_domain}").strip().strip("\"'")

        return cls(
            user=user,
            app_password=app_password,
            from_name=from_name,
            from_email=from_email,
            allowed_sending_domains=[
                "olfmailer.com",
                "olfmailer.net",
                "email.omnileadfeeder.tech",
                "contact.omnileadfeeder.tech",
            ],
            outreach_sending_domains=outreach_sending_domains,
            sending_strategy=sending_strategy,
            azure_communication_connection_string=azure_comm_conn,
            azure_communication_sender_domain=azure_comm_domain,
            azure_communication_sender_email=azure_comm_sender,
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
            outbound_use_gmail=outbound_use_gmail,
            inbox_pool=inbox_pool,
            microsoft_client_id=microsoft_client_id,
            microsoft_client_secret=microsoft_client_secret,
            microsoft_tenant_id=microsoft_tenant_id,
            microsoft_refresh_token=microsoft_refresh_token,
            microsoft_redirect_uri=microsoft_redirect_uri,
            hunter_api_key=os.environ.get("HUNTER_API_KEY", "").strip(),
            apollo_api_key=os.environ.get("APOLLO_API_KEY", "").strip(),
        )
