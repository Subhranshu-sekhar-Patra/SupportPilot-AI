"""
SupportPilot AI — Public Embeddable Chatbot Widget API (v1)
Allows third-party websites to embed the customer AI chatbot.
Enforces organization quotas, domain restrictions, and RAG knowledge grounding.
"""

from typing import Any
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.logger import get_logger
from app.db.session import get_db
from app.models.organization import Organization
from app.models.ticket import MessageAuthorType, Ticket, TicketChannel, TicketMessage, TicketPriority, TicketStatus
from app.services.usage_service import UsageService

logger = get_logger(__name__)

router = APIRouter(prefix="/widget", tags=["Customer Chat Widget"])


class WidgetConfigResponse(BaseModel):
    organization_name: str
    organization_slug: str
    primary_color: str
    greeting: str
    enabled: bool


class WidgetChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    customer_name: str | None = None
    customer_email: str | None = None
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class WidgetChatResponse(BaseModel):
    reply: str
    ticket_id: str
    session_id: str
    citations: list[dict[str, Any]] = []
    is_quota_exceeded: bool = False


@router.get("/{org_slug}/config", response_model=WidgetConfigResponse)
async def get_widget_config(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint to fetch widget branding and configuration for an organization."""
    org = await db.scalar(select(Organization).where(Organization.slug == org_slug))
    if not org or not org.is_active:
        raise NotFoundError("Organization widget not found")

    return WidgetConfigResponse(
        organization_name=org.name,
        organization_slug=org.slug,
        primary_color=org.widget_primary_color or "#4F46E5",
        greeting=org.widget_greeting or "Hi there! How can we help you today?",
        enabled=org.widget_enabled,
    )


@router.post("/{org_slug}/chat", response_model=WidgetChatResponse)
async def widget_chat(
    org_slug: str,
    data: WidgetChatRequest,
    db: AsyncSession = Depends(get_db),
    origin: str | None = Header(None),
):
    """
    Public conversational endpoint for the customer-facing chatbot widget.
    Executes grounded RAG retrieval, tracks AI quota, and logs ticket threads.
    """
    org = await db.scalar(select(Organization).where(Organization.slug == org_slug))
    if not org or not org.is_active:
        raise NotFoundError("Organization")

    if not org.widget_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot widget is currently disabled for this organization.",
        )

    # Check and enforce AI message quota
    usage_svc = UsageService(db)
    has_quota = await usage_svc.check_and_increment_ai_message(org.id)

    # Find or create chat ticket for this session
    ticket = await db.scalar(
        select(Ticket).where(
            Ticket.organization_id == org.id,
            Ticket.channel == TicketChannel.CHAT,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ASSIGNED]),
            Ticket.ai_metadata["session_id"].as_string() == data.session_id,
        )
    )

    if not ticket:
        ticket = Ticket(
            subject=f"Live Chat ({data.customer_name or 'Visitor'} - {data.session_id[:8]})",
            description=data.message,
            priority=TicketPriority.MEDIUM,
            channel=TicketChannel.CHAT,
            customer_name=data.customer_name or "Web Visitor",
            customer_email=data.customer_email,
            organization_id=org.id,
            status=TicketStatus.OPEN,
            ai_metadata={"session_id": data.session_id, "is_widget": True},
        )
        db.add(ticket)
        await db.flush()

    # Log incoming customer message
    user_msg = TicketMessage(
        ticket_id=ticket.id,
        author_type=MessageAuthorType.CUSTOMER,
        content=data.message,
    )
    db.add(user_msg)

    # If organization has exceeded quota, gracefully notify and leave ticket for human support
    if not has_quota:
        fallback_reply = (
            "Thank you for contacting us! Our automated assistant is currently at monthly capacity. "
            "A human support specialist has received your message and will follow up shortly."
        )
        sys_msg = TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.SYSTEM,
            content="AI quota reached. Ticket queued for human support agent.",
            is_internal=True,
        )
        db.add(sys_msg)
        await db.commit()

        return WidgetChatResponse(
            reply=fallback_reply,
            ticket_id=ticket.id,
            session_id=data.session_id,
            citations=[],
            is_quota_exceeded=True,
        )

    # Execute RAG Knowledge Retrieval & Grounded Generation via Agent Orchestrator
    from app.ai.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(org_id=org.id)

    pipeline_result = await orchestrator.run_pipeline(
        ticket_id=ticket.id,
        subject=ticket.subject,
        description=data.message,
        customer_name=data.customer_name,
    )

    reply_content = (
        pipeline_result.generation.response_text
        if pipeline_result.generation and pipeline_result.generation.response_text
        else "Thank you for contacting us. A support specialist will follow up shortly."
    )
    citations = [
        {"document_id": c.document_id, "title": c.document_title, "chunk_index": c.chunk_index}
        for c in (pipeline_result.retrieval.citations or [])
    ]

    confidence = (
        pipeline_result.generation.confidence_score
        if pipeline_result.generation
        else 0.8
    )

    # Save AI response
    ai_msg = TicketMessage(
        ticket_id=ticket.id,
        author_type=MessageAuthorType.AI,
        content=reply_content,
        message_metadata={
            "citations": citations,
            "confidence": confidence,
        },
    )
    db.add(ai_msg)

    # Update ticket enrichment
    ticket.ai_suggested_response = reply_content
    ticket.ai_confidence_score = confidence

    await db.commit()
    logger.info("widget_chat_processed", org_id=org.id, ticket_id=ticket.id)

    return WidgetChatResponse(
        reply=reply_content,
        ticket_id=ticket.id,
        session_id=data.session_id,
        citations=citations,
        is_quota_exceeded=False,
    )


@router.get("/loader.js")
async def get_widget_loader_js():
    """Returns the lightweight JavaScript snippet for embedding SupportPilot on customer websites."""
    js_content = """(function() {
  'use strict';
  const scriptTag = document.currentScript || document.querySelector('script[data-org]');
  if (!scriptTag) return;
  const orgSlug = scriptTag.getAttribute('data-org');
  const hostUrl = scriptTag.src.substring(0, scriptTag.src.indexOf('/api/v1/widget/loader.js'));

  fetch(`${hostUrl}/api/v1/widget/${orgSlug}/config`)
    .then(r => r.json())
    .then(cfg => {
      if (!cfg.enabled) return;

      const btn = document.createElement('div');
      btn.id = 'supportpilot-widget-btn';
      btn.style.cssText = `position:fixed;bottom:24px;right:24px;width:56px;height:56px;border-radius:28px;background:${cfg.primary_color};box-shadow:0 4px 14px rgba(0,0,0,0.2);cursor:pointer;display:flex;align-items:center;justify-content:center;z-index:999999;transition:transform 0.2s;`;
      btn.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
      
      const frame = document.createElement('iframe');
      frame.id = 'supportpilot-widget-frame';
      frame.src = `${hostUrl.replace('8000', '3000')}/widget?org=${orgSlug}`;
      frame.style.cssText = `position:fixed;bottom:92px;right:24px;width:380px;height:560px;border:none;border-radius:16px;box-shadow:0 8px 30px rgba(0,0,0,0.18);display:none;z-index:999999;max-width:calc(100vw - 48px);max-height:calc(100vh - 120px);`;

      btn.onclick = () => {
        frame.style.display = frame.style.display === 'none' ? 'block' : 'none';
      };

      document.body.appendChild(btn);
      document.body.appendChild(frame);
    })
    .catch(console.error);
})();"""
    return Response(content=js_content, media_type="application/javascript")
