"""
SupportPilot AI — AI Agents API Endpoints (v1)
Trigger the AI pipeline for ticket processing.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import AgentOrchestrator
from app.db.session import get_db
from app.dependencies import CurrentUser
from app.models.ticket import Ticket, TicketStatus
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/agents", tags=["AI Agents"])


class ProcessTicketRequest(BaseModel):
    ticket_id: str
    force_reprocess: bool = False


class ProcessTicketResponse(BaseModel):
    ticket_id: str
    category: str
    priority: str
    confidence: float
    suggested_response: str
    quality_score: float
    is_safe_to_send: bool
    source_documents: list[str]


@router.post("/process-ticket", response_model=ProcessTicketResponse)
async def process_ticket_with_ai(
    data: ProcessTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProcessTicketResponse:
    """
    Run the full AI pipeline (classify → retrieve → generate → evaluate)
    for a given ticket. Updates ticket with AI-generated fields.
    """
    # Fetch the ticket (org-scoped)
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == data.ticket_id,
            Ticket.organization_id == current_user.organization_id,
        )
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise NotFoundError("Ticket")

    # Run the AI pipeline
    orchestrator = AgentOrchestrator(org_id=current_user.organization_id)
    ai_result = await orchestrator.process_ticket(
        ticket_id=ticket.id,
        subject=ticket.subject,
        description=ticket.description,
        customer_name=ticket.customer_name,
    )

    # Persist AI results to ticket
    ticket.ai_category = ai_result.classification.category
    ticket.ai_suggested_response = ai_result.response.response_text
    ticket.ai_confidence_score = ai_result.classification.confidence
    ticket.ai_quality_score = ai_result.evaluation.overall_score
    ticket.ai_metadata = ai_result.ai_metadata

    # Auto-update priority from AI classification
    if ai_result.classification.confidence > 0.8:
        ticket.priority = ai_result.classification.priority  # type: ignore

    await db.commit()

    return ProcessTicketResponse(
        ticket_id=ticket.id,
        category=ai_result.classification.category,
        priority=ai_result.classification.priority,
        confidence=ai_result.classification.confidence,
        suggested_response=ai_result.response.response_text,
        quality_score=ai_result.evaluation.overall_score,
        is_safe_to_send=ai_result.evaluation.is_safe_to_send,
        source_documents=ai_result.context.source_documents,
    )
