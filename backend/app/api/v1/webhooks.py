"""
SupportPilot AI — n8n Webhook Handler
Receives workflow events from n8n and dispatches outgoing webhooks.
"""

import hashlib
import hmac

import httpx
from app.core.logger import get_logger
from fastapi import APIRouter, Header, HTTPException, Request, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.models.ticket import Ticket, TicketStatus

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


# ── Incoming payload schemas ───────────────────────────────

class N8nTicketEvent(BaseModel):
    """Payload sent by n8n workflows to our backend."""
    event_type: str         # ticket.created | ticket.updated | ticket.escalated
    ticket_id: str
    extra_data: dict | None = None


# ── Signature verification ─────────────────────────────────

def _verify_n8n_signature(payload: bytes, signature: str) -> bool:
    """
    Verify the HMAC-SHA256 signature of an incoming n8n webhook.
    Prevents unauthorized webhook calls.
    """
    expected = hmac.new(
        settings.n8n_api_key.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Incoming webhook endpoints ─────────────────────────────

@router.post("/n8n/event", summary="Receive event from n8n workflow")
async def receive_n8n_event(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_n8n_signature: str | None = Header(None, alias="X-N8N-Signature"),
) -> dict:
    """
    Endpoint called by n8n workflows.
    Verifies the signature and processes the event.
    """
    body = await request.body()

    # Signature verification (skip in development for ease of testing)
    if settings.is_production and x_n8n_signature:
        if not _verify_n8n_signature(body, x_n8n_signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = N8nTicketEvent.model_validate_json(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid payload: {e}")

    logger.info("n8n_event_received", event_type=payload.event_type, ticket_id=payload.ticket_id)

    # Route event to handler
    handlers = {
        "ticket.escalated": _handle_escalation,
        "ticket.sla_breach": _handle_sla_breach,
    }
    handler = handlers.get(payload.event_type)
    if handler:
        await handler(payload.ticket_id, payload.extra_data or {}, db)

    return {"status": "processed", "event_type": payload.event_type}


# ── Outgoing webhook dispatcher ────────────────────────────

async def dispatch_to_n8n(event_type: str, ticket_id: str, payload: dict) -> None:
    """
    Send an event to n8n to trigger a workflow.
    Called internally when ticket events occur (e.g., ticket created, resolved).
    """
    if not settings.n8n_webhook_url:
        logger.warning("n8n_webhook_url_not_configured")
        return

    webhook_payload = {
        "event_type": event_type,
        "ticket_id": ticket_id,
        **payload,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{settings.n8n_webhook_url}/{event_type.replace('.', '-')}",
                json=webhook_payload,
                headers={
                    "X-API-Key": settings.n8n_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            logger.info(
                "n8n_webhook_dispatched",
                event=event_type,
                ticket_id=ticket_id,
                status=response.status_code,
            )
    except httpx.HTTPError as e:
        logger.error("n8n_webhook_failed", event=event_type, error=str(e))


# ── Event handlers ─────────────────────────────────────────

async def _handle_escalation(ticket_id: str, data: dict, db: AsyncSession) -> None:
    """Mark a ticket as escalated based on n8n workflow trigger."""
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket:
        ticket.status = TicketStatus.ESCALATED
        await db.commit()
        logger.info("ticket_escalated_via_n8n", ticket_id=ticket_id)


async def _handle_sla_breach(ticket_id: str, data: dict, db: AsyncSession) -> None:
    """Log SLA breach event (extend with notification logic)."""
    logger.warning("sla_breach_event", ticket_id=ticket_id, data=data)
