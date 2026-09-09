"""Inbound email listener and autonomous reply dispatcher for Cloudflare-routed Gmail messages."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

from .ai_review import InboundReplyAgent
from .client import EmailClient
from .config import EmailSettings, InboxAccountConfig
from agents.domain import State, Lead
from agents.notifications import NotificationManager

logger = logging.getLogger("leadops.email.inbound")


class InboundEmailWatcher:
    """Monitors company Gmail via IMAP for prospect replies, invokes Inbound AI Reply Agent, and advances lead lifecycle."""

    def __init__(
        self,
        email_client: EmailClient | None = None,
        storage_backend: Any = None,
        settings: EmailSettings | None = None,
        inbound_reply_agent: InboundReplyAgent | None = None,
        notification_manager: NotificationManager | None = None,
    ) -> None:
        self.settings = settings or EmailSettings.from_environment()
        self.client = email_client or EmailClient(self.settings)
        self.storage = storage_backend
        self.reply_agent = inbound_reply_agent or InboundReplyAgent()
        self.notifier = notification_manager or NotificationManager()
        self.is_running = False
        self._task: asyncio.Task[None] | None = None

    @staticmethod
    def should_ignore_inbound(sender: str, subject: str = "") -> bool:
        """Determines if an inbound email should be ignored without responding or provisioning leads.

        Specifically ignores:
        - googlemail.com and google.com domains / subdomains (system alerts, mailer-daemon, etc.)
        - system role accounts (mailer-daemon, postmaster, no-reply, autoreply)
        - automated bounce notifications / delivery failure notices
        - self-addressed loops from our own sending domains (omnileadfeeder.tech)
        """
        if not sender:
            return True

        # Extract clean email address if in "Display Name <user@domain.com>" format
        match = re.search(r"<([^>]+)>", sender)
        clean_sender = match.group(1).strip().lower() if match else sender.strip().lower()
        subject_lower = (subject or "").lower().strip()

        if "@" in clean_sender:
            local_part, domain = clean_sender.split("@", 1)
        else:
            local_part, domain = clean_sender, ""

        # 1. Block Googlemail, Google system domains, and our own domain loops
        # User requirement: "IN OUR INBOUND MESSAGES WE GET MAIL FROM GOOGLEMAIL.COM AND GOOGLE.COM WE NEED TO NOT RESPOND TO THOSE"
        blocked_domains = {
            "google.com",
            "googlemail.com",
            "omnileadfeeder.tech",
        }
        if domain in blocked_domains or any(domain.endswith(f".{bd}") for bd in blocked_domains):
            return True

        # 2. Block system, daemon, bounce, and no-reply local parts
        system_prefixes = (
            "mailer-daemon",
            "mailerdaemon",
            "postmaster",
            "no-reply",
            "noreply",
            "donotreply",
            "do-not-reply",
            "bounce",
            "bounces",
            "notifications",
            "daemon",
            "auto-reply",
            "autoreply",
        )
        if any(
            local_part == prefix or local_part.startswith(f"{prefix}+") or local_part.startswith(f"{prefix}-")
            for prefix in system_prefixes
        ):
            return True

        # 3. Block bounce / automated delivery status subjects
        bounce_phrases = (
            "delivery status notification",
            "undelivered mail returned to sender",
            "mail delivery failed",
            "failure notice",
            "returned mail",
            "address not found",
            "security alert",
            "undeliverable",
            "automatic reply",
            "out of office",
            "auto-reply",
            "vacation response",
        )
        if any(phrase in subject_lower for phrase in bounce_phrases):
            return True

        return False

    @staticmethod
    def extract_bounced_email(text: str) -> str | None:
        """Extract the failed recipient address from a delivery status failure / bounce notification."""
        patterns = [
            r"wasn'?t delivered to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
            r"could not be delivered to:?\s*<*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>*",
            r"delivery to the following recipient failed.*?:?\s*<*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>*",
            r"failed to deliver to:?\s*<*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>*",
            r"mailbox\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\s+does not exist",
            r"550\s+.*?<*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)>*",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                extracted = m.group(1).lower().strip().rstrip(".")
                if not any(extracted.endswith(f"@{d}") for d in ("googlemail.com", "google.com", "gmail.com")):
                    return extracted
        return None

    def get_active_inboxes(self) -> list[InboxAccountConfig]:
        """Return all active inboxes from settings and persistent storage."""
        accounts = list(self.settings.get_all_inboxes()) if hasattr(self.settings, "get_all_inboxes") else []
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
                logger.warning(f"Could not load inboxes from database in watcher: {e}")

        return [a for a in accounts if a.is_active]

    def poll_and_process_once(self) -> list[dict[str, Any]]:
        """Poll IMAP across all configured inboxes, process all unseen incoming replies, and return processed event logs."""
        unseen: list[dict[str, Any]] = []
        all_inboxes = [i for i in self.get_active_inboxes() if getattr(i, "imap_enabled", True)]

        if all_inboxes:
            for inbox in all_inboxes:
                try:
                    try:
                        msgs = self.client.fetch_unseen_emails(mark_as_read=True, inbox=inbox)
                        unseen.extend(msgs)
                    except TypeError:
                        unseen = self.client.fetch_unseen_emails(mark_as_read=True)
                        break
                except Exception as exc:
                    logger.warning(f"Failed to fetch unseen emails for inbox '{inbox.id}': {exc}")
        else:
            try:
                unseen = self.client.fetch_unseen_emails(mark_as_read=True)
            except Exception as exc:
                logger.warning(f"Failed to fetch unseen emails: {exc}")
                return []

        # Deduplicate unseen messages if the same message was fetched across aliases
        seen_message_ids: set[str] = set()
        deduped_unseen: list[dict[str, Any]] = []
        for msg in unseen:
            mid = msg.get("message_id")
            if mid:
                if mid in seen_message_ids:
                    continue
                seen_message_ids.add(mid)
            deduped_unseen.append(msg)

        results: list[dict[str, Any]] = []
        for msg in deduped_unseen:
            processed = self.process_single_inbound_email(msg)
            results.append(processed)
        return results

    def process_single_inbound_email(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Process an individual inbound message (from IMAP poll or HTTP webhook)."""
        import time
        raw_sender = msg.get("sender_email", "").strip()
        match = re.search(r"<([^>]+)>", raw_sender)
        sender = match.group(1).strip().lower() if match else raw_sender.strip().lower()
        sender_name = (msg.get("sender_name") or "").strip()
        subject = msg.get("subject", "")
        body = msg.get("body_text") or msg.get("body_html") or ""

        logger.info(f"📥 [INBOUND EMAIL RECEIVED] From: {sender} | Subject: '{subject}'")

        # 0. Early filter: Do not respond to Google system emails (googlemail.com, google.com), daemons, bounces, or noreply
        if self.should_ignore_inbound(sender, subject):
            # Check if this ignored system message is a bounce / delivery failure notification
            bounced_recipient = self.extract_bounced_email(f"{subject} {body}")
            archived_lead_id = None
            if bounced_recipient and self.storage and hasattr(self.storage, "list_leads"):
                for l in self.storage.list_leads():
                    if l.contact_email and l.contact_email.lower().strip() == bounced_recipient.lower().strip():
                        archived_lead_id = l.lead_id
                        l.transition(State.ARCHIVED, f"Delivery bounce received: {subject}")
                        if hasattr(self.storage, "save_lead"):
                            self.storage.save_lead(l)
                        logger.warning(
                            f"⚠️ [BOUNCE REGISTERED] Lead {l.lead_id} ({bounced_recipient}) marked ARCHIVED due to delivery failure notice."
                        )
                        break

            logger.info(
                f"🚫 [INBOUND IGNORED] Skipping automated response for system/ignored sender '{sender}' "
                f"| Subject: '{subject}' | Bounced Recipient: {bounced_recipient or 'None'}"
            )
            return {
                "ok": True,
                "sender": sender,
                "subject": subject,
                "intent": "IGNORED",
                "lead_id": archived_lead_id,
                "bounced_email": bounced_recipient,
                "reply_dispatched": False,
                "status": "BOUNCE_PROCESSED_AND_ARCHIVED" if bounced_recipient else "IGNORED_SYSTEM_SENDER",
                "received_at": datetime.now(timezone.utc).isoformat(),
            }

        # 1. Match sender to an existing Lead in storage
        lead = None
        if self.storage and hasattr(self.storage, "list_leads"):
            leads = self.storage.list_leads()
            for l in leads:
                if l.contact_email and l.contact_email.lower().strip() == sender:
                    lead = l
                    break

        # 2. Extract and infer jurisdiction, portal name, and matching sandbox
        text_lower = f"{subject} {body}".lower()
        if "travis" in text_lower or "austin" in text_lower:
            detected_slug = "austin-commercial-permits"
            detected_portal = "Travis County Commercial Filings"
        elif "harris" in text_lower or "houston" in text_lower:
            detected_slug = "harris-civil-court-filings"
            detected_portal = "Harris County Civil Court Records"
        elif "dallas" in text_lower:
            detected_slug = "dallas-county-probate-records"
            detected_portal = "Dallas County Probate Court"
        elif "bexar" in text_lower or "san antonio" in text_lower:
            detected_slug = "bexar-property-tax-liens"
            detected_portal = "Bexar County Property Tax Liens"
        else:
            detected_slug = getattr(lead, "slug", "") or "lead-apex-roofing"
            detected_portal = getattr(lead, "target_portal_name", "") or "County Public Records"

        # Resolve contact name
        full_name = getattr(lead, "contact_name", "") or sender_name or ""
        first_name = full_name.split()[0].title() if full_name else "there"

        # Resolve company name
        company_name = getattr(lead, "company_name", "")
        if not company_name:
            domain = sender.split("@")[-1] if "@" in sender else ""
            if domain and domain not in ("gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "example.com", "icloud.com"):
                company_name = domain.split(".")[0].title()
            else:
                company_name = full_name or "your team"

        lead_context = {
            "company_name": company_name,
            "contact_name": first_name,
            "target_portal_name": getattr(lead, "target_portal_name", "") or detected_portal,
        }

        base_url = "https://omnileadfeeder.tech"
        if lead and getattr(lead, "slug", ""):
            sandbox_url = f"{base_url}/p/{lead.slug}"
        elif lead and getattr(lead, "lead_id", ""):
            sandbox_url = f"{base_url}/dashboard/{lead.lead_id}"
        else:
            sandbox_url = f"{base_url}/p/{detected_slug}"

        prior_emails = []
        initial_outreach = None
        if lead:
            if self.storage and hasattr(self.storage, "list_inbound_emails"):
                prior_emails = self.storage.list_inbound_emails(lead.lead_id)
            if getattr(lead, "outreach_subject", ""):
                initial_outreach = {
                    "subject": lead.outreach_subject,
                    "body": getattr(lead, "outreach_body", ""),
                }
        elif self.storage and hasattr(self.storage, "save_lead"):
            # Auto-provision new lead record in storage for unregistered prospect
            lead_id = f"lead-{sender.split('@')[0]}-{int(time.time())}"
            lead = Lead(
                lead_id=lead_id,
                tier_key="weekly",
                state=State.CONVERSATIONAL_INTAKE,
                company_name=company_name,
                contact_name=full_name or first_name,
                contact_email=sender,
                target_portal_name=detected_portal,
                slug=detected_slug,
            )
            self.storage.save_lead(lead)

        # 2. Invoke Inbound Reply Agent with conversation memory
        ai_eval = self.reply_agent.process_inbound_reply(
            inbound_text=body,
            inbound_subject=subject,
            lead_context=lead_context,
            sandbox_url=sandbox_url,
            conversation_history=prior_emails,
            initial_outreach=initial_outreach,
        )

        intent = ai_eval.get("intent", "INTERESTED")
        draft_reply = ai_eval.get("draft_reply_text", "")
        draft_subj = ai_eval.get("draft_subject", f"Re: {subject}")

        # 3. Handle Lead State Machine Transitions
        if lead:
            if intent == "OPT_OUT":
                lead.transition(State.ARCHIVED, f"Opt-out received via email from {sender}")
            elif lead.state == State.OUTREACH_SENT and intent in {"INTERESTED", "QUESTION"}:
                lead.transition(State.CONVERSATIONAL_INTAKE, f"Prospect replied to outreach: {ai_eval.get('summary')}")
            
            if hasattr(self.storage, "save_lead"):
                self.storage.save_lead(lead)

        # 4. Save Inbound Record into Storage
        if self.storage and hasattr(self.storage, "record_inbound_email"):
            try:
                self.storage.record_inbound_email(
                    message_id=msg.get("message_id", ""),
                    sender_email=sender,
                    sender_name=msg.get("sender_name", ""),
                    subject=subject,
                    body=body,
                    intent=intent,
                    draft_reply=draft_reply,
                    lead_id=lead.lead_id if lead else "",
                )
            except Exception as e:
                logger.warning(f"Could not persist inbound email record: {e}")

        # 5. Dispatch automated response if autonomous mode is permitted
        dispatched = False
        if ai_eval.get("should_auto_send", False) and draft_reply:
            try:
                reply_inbox = None
                inbox_id = msg.get("inbox_id")
                recipient_email = (msg.get("recipient_email") or "").lower().strip()
                if hasattr(self.settings, "get_all_inboxes"):
                    all_inbs = self.settings.get_all_inboxes()
                    # 1. Match by explicit recipient email (e.g. catch-all forwarded to Gmail)
                    if recipient_email:
                        for inb in all_inbs:
                            if inb.email_address.lower().strip() == recipient_email:
                                reply_inbox = inb
                                break
                    # 2. Fall back to matching by inbox_id
                    if not reply_inbox and inbox_id:
                        for inb in all_inbs:
                            if inb.id == inbox_id:
                                reply_inbox = inb
                                break

                self.client.send_email(
                    to_email=sender,
                    to_name=msg.get("sender_name") or "there",
                    subject=draft_subj,
                    text_body=draft_reply,
                    in_reply_to=msg.get("message_id"),
                    references=msg.get("message_id"),
                    inbox=reply_inbox,
                )
                dispatched = True
                logger.info(f"🤖 [AI AUTO-REPLY SENT] Dispatched reply to {sender} for intent '{intent}' via inbox '{inbox_id or 'primary'}'")
            except Exception as send_err:
                logger.error(f"Failed to auto-send reply to {sender}: {send_err}")

        # 6. Notify Operator via Discord / Telegram
        try:
            self.notifier.notify_inbound_reply_received(
                sender_email=sender,
                sender_name=msg.get("sender_name") or "there",
                company_name=getattr(lead, "company_name", "") or msg.get("sender_name") or sender,
                subject=subject,
                reply_snippet=body[:300],
                ai_intent=intent,
                ai_sentiment=ai_eval.get("sentiment", "NEUTRAL"),
                ai_draft_reply=draft_reply,
            )
        except Exception as notify_err:
            logger.warning(f"Failed to send inbound reply notification: {notify_err}")

        return {
            "sender": sender,
            "subject": subject,
            "intent": intent,
            "lead_id": lead.lead_id if lead else None,
            "reply_dispatched": dispatched,
            "ai_eval": ai_eval,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _poll_loop(self) -> None:
        """Asynchronous continuous polling loop."""
        self.is_running = True
        logger.info(f"🔄 [INBOUND WATCHER STARTED] Polling every {self.settings.imap_poll_interval_seconds}s for Cloudflare-routed replies.")
        while self.is_running:
            try:
                self.poll_and_process_once()
            except Exception as exc:
                logger.error(f"Inbound watcher poll error: {exc}")
            await asyncio.sleep(self.settings.imap_poll_interval_seconds)

    def start(self) -> None:
        """Start watcher in background asyncio event loop."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Gracefully terminate background polling."""
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("🛑 [INBOUND WATCHER STOPPED]")
