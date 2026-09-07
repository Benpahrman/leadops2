"""Native SMTP & IMAP Client for Company Gmail via Google App Password."""

import email
import email.utils
import imaplib
import logging
import os
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable

from .config import EmailSettings

logger = logging.getLogger("leadops.email.client")


class EmailClient:
    """Production email client using Gmail SMTP/IMAP with Google App Password authentication."""

    def __init__(
        self,
        settings: EmailSettings | None = None,
        transport_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        http_requester: Callable[[str, dict[str, str], bytes | None, str], tuple[int, dict[str, Any]]] | None = None,
    ) -> None:
        self.settings = settings or EmailSettings.from_environment()
        self.transport_hook = transport_hook
        self.http_requester = http_requester

    def get_token(self) -> str:
        """Backward-compatible OAuth token mock for legacy test mocks."""
        if self.http_requester:
            status, data = self.http_requester("https://api.sendpulse.com/oauth/access_token", {}, b"{}", "POST")
            return data.get("access_token", "test_token")
        return "native_gmail_app_password"


    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> dict[str, Any]:
        """Dispatch email via Gmail SMTP using Google App Password."""
        # Check for development/test overrides
        override_email = "" if os.environ.get("PYTEST_CURRENT_TEST") else os.environ.get("LEADOPS_EMAIL_OVERRIDE", "").strip()
        actual_recipient = override_email if override_email else to_email
        actual_name = f"{to_name} ({to_email})" if (override_email and override_email.lower() != to_email.lower()) else to_name
        email_subject = f"[{to_name}] {subject}" if (override_email and override_email.lower() != to_email.lower()) else subject

        sender_email = self.settings.from_email or self.settings.user
        sender_name = self.settings.from_name

        # If running in unit test mode with a mock transport hook, execute hook
        if self.transport_hook is not None:
            return self.transport_hook({
                "to_email": actual_recipient,
                "to_name": actual_name,
                "subject": email_subject,
                "text_body": text_body,
                "html_body": html_body,
                "from_email": sender_email,
                "from_name": sender_name,
                "in_reply_to": in_reply_to,
                "references": references,
            })

        if self.http_requester is not None:
            import json
            payload = {
                "email": {
                    "subject": email_subject,
                    "text": text_body,
                    "html": html_body or f"<p>{text_body.replace(chr(10), '<br>')}</p>",
                    "from": {"name": sender_name, "email": sender_email},
                    "to": [{"name": actual_name, "email": actual_recipient}],
                }
            }
            status, data = self.http_requester(
                "https://api.sendpulse.com/smtp/emails",
                {"Content-Type": "application/json"},
                json.dumps(payload).encode(),
                "POST",
            )
            return data


        # Build RFC 5322 MIME Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email_subject
        msg["From"] = email.utils.formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["Reply-To"] = email.utils.formataddr((str(Header(sender_name, "utf-8")), sender_email))
        msg["To"] = email.utils.formataddr((str(Header(actual_name, "utf-8")), actual_recipient))
        msg["Date"] = email.utils.formatdate(localtime=True)
        message_id = email.utils.make_msgid(domain=sender_email.split("@")[-1] if "@" in sender_email else "leadops.tech")
        msg["Message-ID"] = message_id

        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        # Attach text and HTML bodies
        part_text = MIMEText(text_body, "plain", "utf-8")
        msg.attach(part_text)

        if html_body:
            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_html)
        else:
            # Generate clean HTML paragraph fallback
            fallback_html = f"<div style='font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif; line-height: 1.5; color: #1e293b;'><p>{text_body.replace(chr(10), '<br>')}</p></div>"
            msg.attach(MIMEText(fallback_html, "html", "utf-8"))

        # HARD SAFETY LOCK: Prevent any outbound outreach unless explicitly enabled
        if not self.settings.outreach_dispatch_enabled:
            logger.info(
                f"🛡️ [OUTREACH FROZEN / DRY-RUN] OUTREACH_DISPATCH_ENABLED is false. "
                f"Simulated dispatch for recipient '{actual_recipient}' with subject '{email_subject}'. "
                f"ZERO SMTP emails transmitted."
            )
            return {
                "ok": True,
                "message_id": message_id,
                "recipient": actual_recipient,
                "status": "SIMULATED_DISPATCH_FROZEN",
                "notice": "Outreach dispatch is frozen (OUTREACH_DISPATCH_ENABLED=false)",
            }

        if not self.settings.user or not self.settings.app_password:
            # In test environments without live credentials, log and return simulated response
            logger.warning("No GMAIL_USER or GMAIL_APP_PASSWORD configured. Simulating SMTP dispatch.")
            return {
                "ok": True,
                "message_id": message_id,
                "recipient": actual_recipient,
                "status": "SIMULATED_NO_CREDENTIALS",
            }

        # Live SMTP Dispatch
        try:
            if self.settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    context=context,
                    timeout=self.settings.smtp_timeout,
                ) as server:
                    server.login(self.settings.user, self.settings.app_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=self.settings.smtp_timeout,
                ) as server:
                    server.ehlo()
                    if self.settings.smtp_use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                    server.login(self.settings.user, self.settings.app_password)
                    server.send_message(msg)

            logger.info(f"📧 [SMTP SENT] Successfully sent email to {actual_recipient} via Gmail SMTP (MsgID: {message_id})")
            return {
                "ok": True,
                "message_id": message_id,
                "recipient": actual_recipient,
                "status": "SENT",
            }
        except Exception as exc:
            logger.error(f"❌ [SMTP FAILED] Could not dispatch email to {actual_recipient}: {exc}")
            raise RuntimeError(f"Gmail SMTP dispatch failed: {exc}") from exc

    def fetch_unseen_emails(self, folder: str = "INBOX", mark_as_read: bool = False) -> list[dict[str, Any]]:
        """Fetch unread emails from Gmail IMAP (e.g. replies routed via Cloudflare Email Routing)."""
        if not self.settings.user or not self.settings.app_password:
            logger.debug("No Gmail IMAP credentials configured for fetching unseen emails.")
            return []

        messages: list[dict[str, Any]] = []
        try:
            if self.settings.imap_use_ssl:
                mail = imaplib.IMAP4_SSL(self.settings.imap_host, self.settings.imap_port, timeout=self.settings.imap_timeout)
            else:
                mail = imaplib.IMAP4(self.settings.imap_host, self.settings.imap_port, timeout=self.settings.imap_timeout)

            mail.login(self.settings.user, self.settings.app_password)
            mail.select(folder)

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK" or not search_data or not search_data[0]:
                mail.logout()
                return []

            message_numbers = search_data[0].split()
            for num in message_numbers:
                res, data = mail.fetch(num, "(RFC822)")
                if res != "OK" or not data or not isinstance(data[0], tuple):
                    continue

                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Parse sender & headers
                from_header = msg.get("From", "")
                from_name, sender_email = email.utils.parseaddr(from_header)
                subject = msg.get("Subject", "")
                message_id = msg.get("Message-ID", "")
                in_reply_to = msg.get("In-Reply-To", "")
                references = msg.get("References", "")
                date_header = msg.get("Date", "")

                # Decode subject
                decoded_subject = ""
                for part, enc in email.header.decode_header(subject):
                    if isinstance(part, bytes):
                        decoded_subject += part.decode(enc or "utf-8", errors="ignore")
                    else:
                        decoded_subject += str(part)

                # Extract text body
                body_text = ""
                body_html = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        cdispo = str(part.get("Content-Disposition"))
                        if "attachment" in cdispo:
                            continue
                        charset = part.get_content_charset() or "utf-8"
                        payload = part.get_payload(decode=True)
                        if payload:
                            if ctype == "text/plain" and not body_text:
                                body_text = payload.decode(charset, errors="ignore")
                            elif ctype == "text/html" and not body_html:
                                body_html = payload.decode(charset, errors="ignore")
                else:
                    charset = msg.get_content_charset() or "utf-8"
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(charset, errors="ignore")

                messages.append({
                    "imap_id": num.decode(),
                    "sender_name": from_name,
                    "sender_email": sender_email.lower().strip(),
                    "subject": decoded_subject,
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references,
                    "date": date_header,
                    "body_text": body_text.strip(),
                    "body_html": body_html.strip(),
                })

                if mark_as_read:
                    mail.store(num, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception as exc:
            logger.error(f"Failed to fetch emails via IMAP: {exc}")

        return messages
