"""
SupportPilot AI — Ticket Pydantic Schemas
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.ticket import TicketChannel, TicketPriority, TicketStatus


# ── Request schemas ────────────────────────────────────────

class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=3, max_length=500)
    description: str = Field(..., min_length=10)
    priority: TicketPriority = TicketPriority.MEDIUM
    channel: TicketChannel = TicketChannel.PORTAL
    customer_name: str | None = None
    customer_email: str | None = None
    tags: list[str] | None = None


class UpdateTicketRequest(BaseModel):
    subject: str | None = Field(None, min_length=3, max_length=500)
    description: str | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to_id: str | None = None
    resolution_notes: str | None = None


class AddMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)
    is_internal: bool = False


class AssignTicketRequest(BaseModel):
    agent_id: str = Field(..., description="ID of the agent assigned to this ticket")


class ResolveTicketRequest(BaseModel):
    resolution_notes: str | None = Field(None, description="Notes detailing how the issue was resolved")


class ReopenTicketRequest(BaseModel):
    reason: str | None = Field(None, description="Reason for reopening the ticket")


# ── Response schemas ───────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: str | None
    description: str | None
    extra_data: dict[str, Any] | None = None
    user_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketMessageResponse(BaseModel):
    id: str
    author_type: str
    author_id: str | None
    content: str
    is_internal: bool
    created_at: datetime
    message_metadata: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class TicketResponse(BaseModel):
    id: str
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    channel: TicketChannel
    customer_name: str | None
    customer_email: str | None
    ai_category: str | None
    ai_suggested_response: str | None
    ai_confidence_score: float | None
    ai_quality_score: float | None
    organization_id: str
    assigned_to_id: str | None
    resolution_notes: str | None = None
    resolution_time_seconds: int | None = None
    ai_metadata: dict[str, Any] | None = None
    ai_escalation_reason: str | None = None
    customer_sentiment: str | None = None
    created_at: datetime
    updated_at: datetime
    messages: list[TicketMessageResponse] = []

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
