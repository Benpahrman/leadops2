"""Pydantic request models for portal and sandbox interactions."""

from typing import Any
from pydantic import BaseModel, Field


class SelectFieldsRequest(BaseModel):
    fields: list[str] = Field(min_length=1, max_length=50)


class RecordEventRequest(BaseModel):
    event: str = Field(min_length=1, max_length=100)


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, Any]] | None = None


class InboundEmailWebhookRequest(BaseModel):
    sender: str
    subject: str = ""
    body: str = ""
    message_id: str | None = None
    sender_name: str | None = None


class CancellationRequestModel(BaseModel):
    reason: str = Field(default="", max_length=2000)


class PipelineInitializeRequest(BaseModel):
    company_name: str
    contact_email: str
    target_url: str = ""
    jurisdiction: str = ""
    data_goal: str = ""
    tier_key: str = "daily"
    preferred_destination: str = "Google Sheets"
