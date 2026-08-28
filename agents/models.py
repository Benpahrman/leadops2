"""SQLAlchemy models for LeadOps database schema (for Alembic migrations)."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index, Enum
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class Lead(Base):
    __tablename__ = "leads"

    lead_id = Column(String(255), primary_key=True)
    tier_key = Column(String(50), nullable=False)
    state = Column(String(50), nullable=False)
    selected_fields = Column(Text, nullable=False, default="[]")
    qa_score = Column(Float, nullable=True)
    preview_rows = Column(Integer, nullable=False, default=0)
    deposit_paid = Column(Integer, nullable=False, default=0)
    final_paid = Column(Integer, nullable=False, default=0)
    subscription_active = Column(Integer, nullable=False, default=0)
    buyout_paid = Column(Integer, nullable=False, default=0)
    audit_log = Column(Text, nullable=False, default="[]")
    company_name = Column(String(255), nullable=False, default="")
    contact_email = Column(String(255), nullable=False, default="")
    source_url = Column(Text, nullable=False, default="")
    jurisdiction = Column(String(255), nullable=False, default="")
    slug = Column(String(255), nullable=False, default="")
    outreach_subject = Column(Text, nullable=False, default="")
    outreach_body = Column(Text, nullable=False, default="")
    repo_url = Column(String(500), nullable=False, default="")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    sandboxes = relationship("Sandbox", back_populates="lead", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="lead", cascade="all, delete-orphan")
    cancellation_requests = relationship("CancellationRequest", back_populates="lead", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Lead(lead_id={self.lead_id}, state={self.state})>"


class Sandbox(Base):
    __tablename__ = "sandboxes"

    slug = Column(String(255), primary_key=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), nullable=False)
    rows = Column(Text, nullable=False, default="[]")
    source_url = Column(Text, nullable=False, default="")
    events = Column(Text, nullable=False, default="[]")
    progress = Column(Text, nullable=False, default="{}")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="sandboxes")

    def __repr__(self):
        return f"<Sandbox(slug={self.slug}, lead_id={self.lead_id})>"


class WebhookIdempotency(Base):
    __tablename__ = "webhook_idempotency"

    event_id = Column(String(255), primary_key=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<WebhookIdempotency(event_id={self.event_id})>"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketType(str, enum.Enum):
    SELECTOR_REPAIR = "selector_repair"
    DELIVERY_ISSUE = "delivery_issue"
    BILLING = "billing"
    GENERAL = "general"


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String(255), primary_key=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), nullable=False, index=True)
    ticket_type = Column(Enum(TicketType), nullable=False, default=TicketType.GENERAL)
    status = Column(Enum(TicketStatus), nullable=False, default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False, default="")
    assignee = Column(String(255), nullable=True)
    sla_deadline = Column(DateTime, nullable=True)
    sla_breached = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="tickets")

    def __repr__(self):
        return f"<Ticket(ticket_id={self.ticket_id}, type={self.ticket_type}, status={self.status})>"


class CancellationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class CancellationRequest(Base):
    __tablename__ = "cancellation_requests"

    request_id = Column(String(255), primary_key=True)
    lead_id = Column(String(255), ForeignKey("leads.lead_id"), nullable=False, index=True)
    user_email = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False, default="")
    status = Column(Enum(CancellationStatus), nullable=False, default=CancellationStatus.PENDING)
    refund_amount = Column(Float, nullable=True)
    processed_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    lead = relationship("Lead", back_populates="cancellation_requests")

    def __repr__(self):
        return f"<CancellationRequest(request_id={self.request_id}, status={self.status})>"


class ABTestVariant(str, enum.Enum):
    A = "A"
    B = "B"


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    template_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    subject_a = Column(String(500), nullable=False)
    subject_b = Column(String(500), nullable=False)
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, nullable=False)
    variant = Column(Enum(ABTestVariant), nullable=False, default=ABTestVariant.A)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EmailTemplate(name={self.name}, variant={self.variant})>"