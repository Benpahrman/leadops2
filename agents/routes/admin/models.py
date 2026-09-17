"""Pydantic request and response models for Admin API routes."""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class OverrideStateRequest(BaseModel):
    target_state: str
    founder_reason: str = "Manual founder intervention"


class OverrideQARequest(BaseModel):
    qa_score: float
    justification: str = "Founder verified edge-case QA pass"


class EmergencyStopRequest(BaseModel):
    active: bool
    reason: str = "Global operational emergency pause"


class CreateTicketRequest(BaseModel):
    lead_id: str
    ticket_type: str = "selector_repair"
    priority: str = "high"
    title: str
    description: str = ""
    assignee: Optional[str] = None
    sla_hours: int = 4


class UpdateTicketRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    sla_hours: Optional[int] = None


class CancellationActionRequest(BaseModel):
    action: str  # "approve" or "reject"
    refund_amount: Optional[float] = None
    processed_by: str


class VerifyDeliverabilityRequest(BaseModel):
    force: bool = False


class BatchVerifyDeliverabilityRequest(BaseModel):
    lead_ids: Optional[List[str]] = None
    force: bool = False
    limit: int = 50


class ValidateDomainRequest(BaseModel):
    domain: str
    force: bool = False


class ToggleAutoOutreachRequest(BaseModel):
    enabled: bool


class TriggerWebScoutRequest(BaseModel):
    niche: Optional[str] = None
    channel: Optional[str] = None
    run_until_found: Optional[bool] = True
    max_attempts: Optional[int] = 12


class BatchScoutRequest(BaseModel):
    count: Optional[int] = 3
    channel: Optional[str] = None
    niche: Optional[str] = None


class SetStateFocusRequest(BaseModel):
    state_code: Optional[str] = None


class StartProspectorRequest(BaseModel):
    duration_days: Optional[int] = 14
    volume_per_cycle: Optional[int] = 3
    channels: Optional[list[str]] = None


class TriggerProspectorBurstRequest(BaseModel):
    count: Optional[int] = 3
    channel: Optional[str] = None


class SendLifecycleEmailRequest(BaseModel):
    template_name: str
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None


class DraftEmailRequest(BaseModel):
    template_name: str = "outreach_pitch"
    tone: str = "human_peer"
    custom_instruction: str = ""


class InboxUpsertRequest(BaseModel):
    inbox_id: Optional[str] = None
    email_address: str
    password: Optional[str] = ""
    provider: Optional[str] = "zoho"
    from_name: Optional[str] = "Alex | OmniLeadFeeder"
    smtp_host: Optional[str] = ""
    smtp_port: Optional[int] = 465
    smtp_use_ssl: Optional[bool] = True
    smtp_use_tls: Optional[bool] = False
    imap_host: Optional[str] = ""
    imap_port: Optional[int] = 993
    imap_use_ssl: Optional[bool] = True
    daily_limit: Optional[int] = 25
    warmup_start_date: Optional[str] = ""
    is_active: Optional[bool] = True


class WarmupStartRequest(BaseModel):
    start_date: Optional[str] = None


class AddWarmupTargetRequest(BaseModel):
    email: str
    name: Optional[str] = ""
    password: Optional[str] = ""
    provider: Optional[str] = "gmail"
    is_monitored: Optional[bool] = True


class RunComprehensiveAuditRequest(BaseModel):
    domain: Optional[str] = "olfmailer.com"
    subject: Optional[str] = "morning docket records for your jurisdiction"
    body: Optional[str] = None


class RblCheckRequest(BaseModel):
    target: Optional[str] = "olfmailer.com"


class ContentAuditRequest(BaseModel):
    subject: Optional[str] = "morning docket records for your jurisdiction"
    body: str


class RunDeliverabilityAuditRequest(BaseModel):
    inbox_id: Optional[str] = None
    force: bool = True
    wait: bool = False


class VerifyEmailRequest(BaseModel):
    email: str


class ValidateDomainRequest(BaseModel):
    domain: str


class Toggle247Request(BaseModel):
    enabled: bool = True


__all__ = ['OverrideStateRequest', 'OverrideQARequest', 'EmergencyStopRequest', 'CreateTicketRequest', 'UpdateTicketRequest', 'CancellationActionRequest', 'VerifyDeliverabilityRequest', 'BatchVerifyDeliverabilityRequest', 'ValidateDomainRequest', 'ToggleAutoOutreachRequest', 'TriggerWebScoutRequest', 'BatchScoutRequest', 'SetStateFocusRequest', 'StartProspectorRequest', 'TriggerProspectorBurstRequest', 'SendLifecycleEmailRequest', 'DraftEmailRequest', 'InboxUpsertRequest', 'WarmupStartRequest', 'AddWarmupTargetRequest', 'RunComprehensiveAuditRequest', 'RblCheckRequest', 'ContentAuditRequest', 'RunDeliverabilityAuditRequest', 'VerifyEmailRequest', 'ValidateDomainRequest', 'Toggle247Request']
