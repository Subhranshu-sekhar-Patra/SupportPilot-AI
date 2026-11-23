"""
SupportPilot AI — Webhook Endpoints & n8n Integration (v1)
Handles incoming webhook events from n8n workflows and records customer feedback in PostgreSQL.
"""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logger import get_logger
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.feedback import CustomerFeedback
from app.models.ticket import MessageAuthorType, Ticket, TicketMessage, TicketPriority, TicketStatus
from app.models.user import User
from app.webhooks.security import is_duplicate_event, verify_webhook_auth

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ── Schemas ───────────────────────────────────────────────────

class N8nTicketEvent(BaseModel):
    """Payload sent by n8n workflows to our backend."""
    event_id: str | None = None
    event_type: str  # ticket.escalated | ticket.created | ticket.updated | ticket.resolved
    ticket_id: str
    assigned_to_id: str | None = None
    priority: TicketPriority | None = None
    notification_status: str | None = None
    extra_data: dict[str, Any] | None = None


class CustomerFeedbackRequest(BaseModel):
    """Payload sent by customer feedback surveys or n8n follow-up workflow."""
    ticket_id: str
    rating: int = Field(..., ge=1, le=5, description="CSAT Rating 1 to 5 stars")
    comment: str | None = Field(None, max_length=2000)
    customer_email: str | None = None
    event_id: str | None = None


class CustomerFeedbackResponse(BaseModel):
    id: str
    ticket_id: str
    organization_id: str
    rating: int
    comment: str | None
    customer_email: str | None
    status: str

    model_config = {"from_attributes": True}


# ── Incoming n8n Event Endpoint ───────────────────────────────

@router.post("/n8n/event", summary="Receive lifecycle event from n8n workflow")
async def receive_n8n_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_n8n_signature: str | None = Header(None, alias="X-N8N-Signature"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_event_id: str | None = Header(None, alias="X-Event-ID"),
) -> dict[str, Any]:
    """
    Receives events from n8n workflows:
      - Enforces HMAC-SHA256 signature / API key authentication.
      - Enforces duplicate-event suppression (idempotency).
      - Handles ticket escalation, assignment, status update, and notification audit logs.
    """
    body = await request.body()

    # 1. Authentication check
    if not verify_webhook_auth(body, signature=x_n8n_signature, api_key=x_api_key):
        logger.warning("unauthorized_n8n_webhook_rejected")
        raise HTTPException(status_code=401, detail="Unauthorized webhook: invalid signature or API key")

    try:
        payload = N8nTicketEvent.model_validate_json(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Malformed webhook payload: {e}")

    # 2. Duplicate event protection
    event_id = payload.event_id or x_event_id
    if is_duplicate_event(event_id):
        logger.info("duplicate_n8n_event_suppressed", event_id=event_id)
        return {
            "status": "duplicate_ignored",
            "event_id": event_id,
            "message": "Event has already been processed.",
        }

    logger.info(
        "n8n_event_processing",
        event_type=payload.event_type,
        ticket_id=payload.ticket_id,
        event_id=event_id,
    )

    # 3. Fetch ticket from database
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == payload.ticket_id)
        .options(selectinload(Ticket.messages))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {payload.ticket_id} not found")

    # 4. Route and handle event
    if payload.event_type == "ticket.escalated":
        ticket.status = TicketStatus.ESCALATED
        if payload.priority:
            ticket.priority = payload.priority
        if payload.assigned_to_id:
            user_exists = await db.scalar(select(User.id).where(User.id == payload.assigned_to_id))
            if user_exists:
                ticket.assigned_to_id = payload.assigned_to_id
            else:
                ticket.ai_metadata = ticket.ai_metadata or {}
                ticket.ai_metadata["assigned_agent"] = payload.assigned_to_id

        # Insert audit note
        note_text = (
            f"⚡ **n8n Automation**: Ticket escalated."
            + (f" Assigned to agent: `{payload.assigned_to_id}`." if payload.assigned_to_id else "")
            + (f" Priority set to `{payload.priority.value}`." if payload.priority else "")
        )
        msg = TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.SYSTEM,
            author_id=None,
            content=note_text,
            is_internal=True,
            message_metadata={"source": "n8n_escalation_workflow", "event_id": event_id},
        )
        db.add(msg)

        audit = AuditLog(
            organization_id=ticket.organization_id,
            action="ticket_escalated_via_n8n",
            resource_type="ticket",
            resource_id=ticket.id,
            description="n8n Escalation workflow assigned agent and marked ticket as escalated.",
            extra_data=payload.extra_data,
        )
        db.add(audit)

    elif payload.event_type in ("ticket.created", "ticket.notification_sent"):
        audit = AuditLog(
            organization_id=ticket.organization_id,
            action="customer_notification_dispatched",
            resource_type="ticket",
            resource_id=ticket.id,
            description=f"n8n Customer notification workflow acknowledged for {ticket.customer_email or 'customer'}.",
            extra_data=payload.extra_data,
        )
        db.add(audit)

    elif payload.event_type == "ticket.resolved":
        audit = AuditLog(
            organization_id=ticket.organization_id,
            action="ticket_resolution_followup_initiated",
            resource_type="ticket",
            resource_id=ticket.id,
            description="n8n Follow-up workflow initiated CSAT survey timer.",
            extra_data=payload.extra_data,
        )
        db.add(audit)

    await db.commit()
    await db.refresh(ticket)

    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": payload.event_type,
        "ticket_id": ticket.id,
        "ticket_status": ticket.status.value,
        "assigned_to_id": ticket.assigned_to_id or (ticket.ai_metadata or {}).get("assigned_agent"),
    }


# ── Customer Feedback Submission Endpoint ─────────────────────

@router.post(
    "/feedback",
    response_model=CustomerFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save customer follow-up CSAT survey feedback into PostgreSQL",
)
async def submit_customer_feedback(
    data: CustomerFeedbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_n8n_signature: str | None = Header(None, alias="X-N8N-Signature"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_event_id: str | None = Header(None, alias="X-Event-ID"),
) -> CustomerFeedbackResponse:
    """
    Saves post-resolution survey feedback directly into PostgreSQL:
      - Validates ticket exists.
      - Checks duplicate-event suppression.
      - Records CustomerFeedback entry.
      - Attaches customer feedback message to ticket thread.
      - Emits AuditLog record.
    """
    body = await request.body()
    # Check auth if headers are present
    if x_n8n_signature or x_api_key:
        if not verify_webhook_auth(body, signature=x_n8n_signature, api_key=x_api_key):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Duplicate check
    event_id = data.event_id or x_event_id
    if is_duplicate_event(event_id):
        logger.info("duplicate_feedback_suppressed", event_id=event_id)
        # Fetch existing feedback
        existing = await db.scalar(
            select(CustomerFeedback).where(CustomerFeedback.ticket_id == data.ticket_id)
        )
        if existing:
            return CustomerFeedbackResponse(
                id=existing.id,
                ticket_id=existing.ticket_id,
                organization_id=existing.organization_id,
                rating=existing.rating,
                comment=existing.comment,
                customer_email=existing.customer_email,
                status="duplicate_acknowledged",
            )

    # 1. Fetch ticket
    res = await db.execute(
        select(Ticket)
        .where(Ticket.id == data.ticket_id)
        .options(selectinload(Ticket.messages))
    )
    ticket = res.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {data.ticket_id} not found")

    # 2. Persist CustomerFeedback record
    feedback = CustomerFeedback(
        ticket_id=ticket.id,
        organization_id=ticket.organization_id,
        rating=data.rating,
        comment=data.comment,
        customer_email=data.customer_email or ticket.customer_email,
        feedback_metadata={"event_id": event_id, "source": "n8n_followup_workflow"},
    )
    db.add(feedback)

    # 3. Update ticket metadata & add message to thread
    ticket.ai_metadata = ticket.ai_metadata or {}
    ticket.ai_metadata["customer_feedback"] = {
        "rating": data.rating,
        "comment": data.comment,
        "submitted_at": str(feedback.created_at),
    }

    stars = "⭐" * data.rating
    feedback_message = (
        f"{stars} **Customer Satisfaction Survey (CSAT): {data.rating}/5**\n"
        + (f"Comment: *\"{data.comment}\"*" if data.comment else "No additional comments provided.")
    )
    msg = TicketMessage(
        ticket_id=ticket.id,
        author_type=MessageAuthorType.CUSTOMER,
        author_id=None,
        content=feedback_message,
        is_internal=False,
        message_metadata={"csat_rating": data.rating, "event_id": event_id},
    )
    db.add(msg)

    # 4. Audit Log
    audit = AuditLog(
        organization_id=ticket.organization_id,
        action="customer_feedback_received",
        resource_type="ticket",
        resource_id=ticket.id,
        description=f"Received CSAT {data.rating}/5 from customer.",
        extra_data={"rating": data.rating, "comment": data.comment},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(feedback)

    logger.info(
        "customer_feedback_persisted",
        ticket_id=ticket.id,
        rating=feedback.rating,
        feedback_id=feedback.id,
    )

    return CustomerFeedbackResponse(
        id=feedback.id,
        ticket_id=feedback.ticket_id,
        organization_id=feedback.organization_id,
        rating=feedback.rating,
        comment=feedback.comment,
        customer_email=feedback.customer_email,
        status="saved",
    )
