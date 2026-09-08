"""Customer portal application boundary, independent of a web framework."""

import csv
import io
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from .domain import Lead, State
from .progress import ProgressFeed, ProgressStatus
from .logging_config import get_logger

logger = get_logger("portal")


@dataclass
class Sandbox:
    slug: str
    lead: Lead
    rows: list[dict[str, str]]
    source_url: str
    events: list[dict[str, str]] = field(default_factory=list)
    progress: ProgressFeed = field(default_factory=ProgressFeed)


@dataclass(frozen=True)
class IntakeAssumption:
    key: str
    label: str
    value: str | list[str] | None
    source: str
    confidence: str
    requires_confirmation: bool = True


@dataclass(frozen=True)
class IntakeForm:
    """A reviewable intake form assembled from Scout research."""

    slug: str
    assumptions: tuple[IntakeAssumption, ...]
    completed_sections: tuple[str, ...] = ()


class PortalService:
    """Own sandbox data and portal events; HTTP handlers can delegate here."""

    def __init__(self, storage: Any | None = None) -> None:
        self._sandboxes: dict[str, Sandbox] = {}
        self.storage = storage

    def publish_sandbox(
        self,
        lead: Lead,
        company_name: str,
        rows: list[dict[str, str]],
        source_url: str,
    ) -> str:
        slug = self._slug(company_name, lead.lead_id)
        if slug in self._sandboxes or (self.storage and self.storage.get_sandbox(slug) is not None):
            existing = self._sandboxes.get(slug) or (self.storage.get_sandbox(slug) if self.storage else None)
            if existing:
                if rows:
                    existing.rows = rows
                if source_url:
                    existing.source_url = source_url
                if self.storage:
                    self.storage.save_sandbox(existing)
                return slug
        if not rows or not source_url:
            raise ValueError("A sandbox requires sample rows and a source URL")
        lead.company_name = lead.company_name or company_name
        lead.source_url = lead.source_url or source_url
        lead.slug = slug
        lead.repo_url = lead.repo_url or f"/api/dashboard/{lead.lead_id}/buyout-bundle"
        if not lead.contact_email:
            name_slug = re.sub(r"[^a-zA-Z0-9]+", "", company_name).lower()
            lead.contact_email = f"team@{name_slug}.com"
        if not lead.outreach_subject:
            lead.outreach_subject = f"Automated Record Feed for {company_name} [Interactive Sandbox Ready]"
        if not lead.outreach_body:
            lead.outreach_body = (
                f"Hi {company_name} Team,\n\n"
                f"We analyzed your public filings workflow from {source_url}.\n"
                f"Our autonomous crawler has already built a live sample feed for your pipeline.\n\n"
                f"Review your interactive data sandbox and test custom schema fields here:\n"
                f"http://127.0.0.1:8000/p/{slug}\n\n"
                f"Once you approve the schema, lock in your 50% milestone deposit ($250) to deploy your production feed.\n\n"
                f"Best,\n"
                f"Alex | LeadOps Automation Engineering"
            )

        if lead.state == State.PROSPECTING:
            lead.transition(State.REVIEW, "sandbox published")
        sandbox = Sandbox(slug, lead, rows, source_url)
        self._sandboxes[slug] = sandbox
        self._record(slug, "sandbox.viewed")
        if self.storage:
            self.storage.save_sandbox(sandbox)
        return slug

    def get_sandbox(self, slug: str) -> Sandbox:
        logger.info(f"GET_SANDBOX: slug={slug}, type={type(slug)}, sandboxes={list(self._sandboxes.keys())}")
        if slug in self._sandboxes:
            logger.info(f"GET_SANDBOX: Found in memory")
            return self._sandboxes[slug]
        for sb in self._sandboxes.values():
            if sb.lead.lead_id == slug or getattr(sb.lead, "slug", "") == slug:
                logger.info(f"GET_SANDBOX: Found by lead_id/slug")
                return sb
        if self.storage:
            sb = self.storage.get_sandbox(slug)
            if sb is not None:
                self._sandboxes[slug] = sb
                logger.info(f"GET_SANDBOX: Found in storage")
                return sb
            # Fallback search across all persisted sandboxes
            all_sbs = self.storage.list_sandboxes()
            for s in all_sbs:
                if s.slug == slug or s.lead.lead_id == slug or getattr(s.lead, "slug", "") == slug:
                    self._sandboxes[slug] = s
                    logger.info(f"GET_SANDBOX: Found in storage list")
                    return s
        logger.error(f"GET_SANDBOX: Not found, raising KeyError for slug={slug}")
        raise KeyError(f"Unknown sandbox: {slug}")

    def build_intake_form(self, slug: str, research: dict[str, object]) -> IntakeForm:
        """Turn Scout's evidence into low-friction, editable customer assumptions."""
        self.get_sandbox(slug)
        required = {
            "niche": "Business type",
            "jurisdiction": "Primary jurisdiction",
            "portal_name": "Likely data portal",
            "portal_url": "Portal URL",
            "suggested_fields": "Suggested fields",
            "recommended_tier": "Recommended plan",
            "delivery_destination": "Delivery destination",
        }
        assumptions = tuple(
            IntakeAssumption(
                key=key,
                label=label,
                value=research.get(key),
                source=str(research.get(f"{key}_source", "Scout research")),
                confidence=str(research.get(f"{key}_confidence", "medium")),
            )
            for key, label in required.items()
        )
        self._record(slug, "intake.prefilled")
        return IntakeForm(slug, assumptions)

    def record_interaction(self, slug: str, event: str) -> None:
        if not re.fullmatch(r"[a-z0-9_.-]+", event):
            raise ValueError("Portal event names may contain lowercase letters, numbers, dots, dashes, and underscores")
        self.get_sandbox(slug)
        self._record(slug, event)

    def publish_build_progress(
        self,
        slug: str,
        role: str,
        status: ProgressStatus,
        public_message: str,
    ) -> None:
        """Publish a safe build update for the customer portal."""
        sandbox = self.get_sandbox(slug)
        sandbox.progress.publish(role, status, public_message)
        if self.storage:
            self.storage.save_sandbox(sandbox)

    def build_progress(self, slug: str) -> list[dict[str, object]]:
        """Return only customer-safe build progress fields."""
        return self.get_sandbox(slug).progress.public_snapshot()

    def select_fields(self, slug: str, fields: list[str]) -> None:
        sandbox = self.get_sandbox(slug)
        sandbox.lead.select_fields(fields)
        if sandbox.lead.state == State.REVIEW:
            sandbox.lead.transition(State.CONVERSATIONAL_INTAKE, "fields selected")
        self._record(slug, "fields.selected")
        if self.storage:
            self.storage.save_sandbox(sandbox)
        try:
            from .client_artifacts import artifact_store
            artifact_store.save_artifact(
                lead_id=sandbox.lead.lead_id,
                stage="02_INTAKE_SCOPE",
                agent_name="Schema Architect",
                filename="02_selected_fields.json",
                content={"selected_fields": fields, "total_fields": len(fields), "slug": slug},
                description="Custom client schema fields configured in sandbox"
            )
        except Exception as exc:
            logger.warning(f"Failed to record selected fields artifact: {exc}")

    def approve_scope(self, slug: str) -> None:
        """Record the customer's core scope approval before checkout."""
        sandbox = self.get_sandbox(slug)
        if sandbox.lead.state != State.CONVERSATIONAL_INTAKE:
            raise ValueError("Scope approval requires completed intake")
        sandbox.lead.transition(State.SOW_GENERATED, "customer approved scope")
        self._record(slug, "scope.approved")
        if self.storage:
            self.storage.save_sandbox(sandbox)
        try:
            from .client_artifacts import artifact_store
            artifact_store.save_artifact(
                lead_id=sandbox.lead.lead_id,
                stage="02_INTAKE_SCOPE",
                agent_name="SOW Contract Generator",
                filename="02_intake_sow.json",
                content={
                    "company_name": sandbox.lead.company_name,
                    "lead_id": sandbox.lead.lead_id,
                    "tier": sandbox.lead.tier.name,
                    "tier_price_cents": sandbox.lead.tier.price_cents,
                    "setup_deposit_cents": sandbox.lead.tier.price_cents // 2,
                    "final_balance_cents": sandbox.lead.tier.price_cents // 2,
                    "selected_fields": sandbox.lead.selected_fields,
                    "approved_at": getattr(sandbox.lead, "updated_at", "") or getattr(sandbox.lead, "created_at", "") or datetime.now(timezone.utc).isoformat(),
                },
                description="Approved Statement of Work & Milestone Escrow Terms"
            )
        except Exception as exc:
            logger.warning(f"Failed to record SOW approval artifact: {exc}")

    def export_csv(self, slug: str) -> str:
        sandbox = self.get_sandbox(slug)
        self._record(slug, "sample.exported")
        output = io.StringIO()
        columns = list(sandbox.rows[0].keys())
        writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sandbox.rows)
        return output.getvalue()

    def request_checkout(self, slug: str) -> dict[str, object]:
        sandbox = self.get_sandbox(slug)
        if sandbox.lead.state != State.SOW_GENERATED:
            raise ValueError("Checkout requires an approved scope and generated SOW")
        self._record(slug, "checkout.requested")
        deposit_usd = getattr(sandbox.lead, "deposit_amount_usd", 99.00)
        return {
            "lead_id": sandbox.lead.lead_id,
            "tier": sandbox.lead.tier.name,
            "amount_cents": int(deposit_usd * 100) if sandbox.lead.tier_key != "buyout" else sandbox.lead.tier.price_cents // 2,
            "deposit_amount_usd": deposit_usd,
            "payment_provider": "paypal",
            "payment_kind": "buyout" if sandbox.lead.tier_key == "buyout" else "setup_deposit",
        }

    def request_final_checkout(self, slug: str) -> dict[str, object]:
        """Generate checkout payload for the second (final) milestone payment and recurring subscription initialization."""
        sandbox = self.get_sandbox(slug)
        if sandbox.lead.state != State.ESCROW_PREVIEW:
            raise ValueError("Final payment requires a completed build in ESCROW_PREVIEW state")
        self._record(slug, "final_checkout.requested")
        starts_subscription = sandbox.lead.tier_key != "buyout"
        plan_id = os.getenv(f"PAYPAL_PLAN_ID_{sandbox.lead.tier_key.upper()}", f"P-LEADOPS-{sandbox.lead.tier_key.upper()}-PLAN") if starts_subscription else ""
        deposit_usd = getattr(sandbox.lead, "deposit_amount_usd", 99.00)
        # 100% of the $99 setup deposit is credited towards Month 1 subscription balance ($250 - $99 = $151)
        net_amount_cents = max(0, sandbox.lead.tier.price_cents - int(deposit_usd * 100)) if starts_subscription else 150000
        return {
            "lead_id": sandbox.lead.lead_id,
            "tier": sandbox.lead.tier.name,
            "tier_key": sandbox.lead.tier_key,
            "amount_cents": net_amount_cents,
            "deposit_credit_usd": deposit_usd,
            "plan_price_usd": sandbox.lead.tier.price_cents / 100.0,
            "payment_provider": "paypal",
            "payment_kind": "final_payment_and_subscription",
            "starts_subscription": starts_subscription,
            "paypal_plan_id": plan_id,
            "recurring_monthly_usd": sandbox.lead.tier.price_cents // 100 if starts_subscription else 0,
        }

    def create_ticket(
        self,
        slug: str,
        ticket_type: str,
        title: str,
        description: str = "",
        priority: str = "high",
        assignee: str | None = None,
        sla_hours: int = 4,
    ) -> dict[str, object]:
        """Create a support ticket with SLA tracking."""
        import uuid
        from ..models import Ticket, TicketType, TicketStatus, TicketPriority
        
        sandbox = self.get_sandbox(slug)
        lead_id = sandbox.lead.lead_id
        
        ticket = Ticket(
            ticket_id=f"TKT-{uuid.uuid4().hex[:8].upper()}",
            lead_id=lead_id,
            ticket_type=TicketType(ticket_type),
            status=TicketStatus.OPEN,
            priority=TicketPriority(priority),
            title=title,
            description=description,
            assignee=assignee,
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=sla_hours),
            sla_breached=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        if self.storage:
            self.storage.save_ticket(ticket)
        
        self._record(slug, f"ticket.created:{ticket_type}")
        
        return {
            "ticket_id": ticket.ticket_id,
            "lead_id": lead_id,
            "ticket_type": ticket.ticket_type.value,
            "status": ticket.status.value,
            "priority": ticket.priority.value,
            "title": ticket.title,
            "sla_deadline": ticket.sla_deadline.isoformat(),
            "created_at": ticket.created_at.isoformat(),
        }

    def request_cancellation(
        self,
        slug: str,
        user_email: str,
        reason: str = "",
    ) -> dict[str, object]:
        """Create a cancellation request for self-serve cancellation."""
        import uuid
        from ..models import CancellationRequest, CancellationStatus
        
        sandbox = self.get_sandbox(slug)
        lead_id = sandbox.lead.lead_id
        
        # Check if there's already a pending cancellation
        if self.storage:
            existing = self.storage.list_cancellation_requests(lead_id)
            pending = [r for r in existing if r.status == CancellationStatus.PENDING]
            if pending:
                raise ValueError("A cancellation request is already pending for this lead")
        
        request = CancellationRequest(
            request_id=f"CANX-{uuid.uuid4().hex[:8].upper()}",
            lead_id=lead_id,
            user_email=user_email,
            reason=reason,
            status=CancellationStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        if self.storage:
            self.storage.save_cancellation_request(request)
        
        self._record(slug, "cancellation.requested")
        
        return {
            "request_id": request.request_id,
            "lead_id": lead_id,
            "user_email": user_email,
            "reason": reason,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
        }

    def _record(self, slug: str, event: str) -> None:
        self._sandboxes[slug].events.append({"event": event})
        if self.storage:
            self.storage.save_sandbox(self._sandboxes[slug])

    @staticmethod
    def _slug(company_name: str, lead_id: str) -> str:
        clean_company = re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")
        clean_id = re.sub(r"[^a-z0-9]+", "-", lead_id.lower()).strip("-")
        return f"{clean_company or 'prospect'}-{clean_id}"