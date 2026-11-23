"""
SupportPilot AI — Tickets API Endpoints (v1)
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser, require_role
from app.models.ticket import TicketPriority, TicketStatus
from app.models.user import UserRole
from app.schemas.ticket import (
    AddMessageRequest,
    AssignTicketRequest,
    AuditLogResponse,
    CreateTicketRequest,
    ReopenTicketRequest,
    ResolveTicketRequest,
    TicketListResponse,
    TicketMessageResponse,
    TicketResponse,
    UpdateTicketRequest,
)
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    data: CreateTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Create a new support ticket."""
    return await TicketService(db, current_user).create_ticket(data)


@router.get("", response_model=TicketListResponse)
async def list_tickets(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TicketStatus | None = Query(None),
    priority: TicketPriority | None = Query(None),
    category: str | None = Query(None),
    assigned_to_me: bool = Query(False),
) -> TicketListResponse:
    """List tickets for the current organization (paginated and filterable)."""
    return await TicketService(db, current_user).list_tickets(
        page=page,
        page_size=page_size,
        status=status,
        priority=priority,
        category=category,
        assigned_to_me=assigned_to_me,
    )


@router.get("/escalated/queue", response_model=TicketListResponse)
async def list_escalated_queue(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> TicketListResponse:
    """List all escalated tickets in the organization requiring human attention."""
    return await TicketService(db, current_user).list_tickets(
        page=page,
        page_size=page_size,
        status=TicketStatus.ESCALATED,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Get a single ticket by ID."""
    return await TicketService(db, current_user).get_ticket(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    data: UpdateTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Update ticket status, priority, assignment, or resolution notes."""
    return await TicketService(db, current_user).update_ticket(ticket_id, data)


@router.post("/{ticket_id}/messages", response_model=TicketResponse)
async def add_message(
    ticket_id: str,
    data: AddMessageRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Add a message to a ticket's conversation thread."""
    return await TicketService(db, current_user).add_message(ticket_id, data)


@router.get("/{ticket_id}/messages", response_model=list[TicketMessageResponse])
async def list_messages(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[TicketMessageResponse]:
    """Retrieve full conversation message history for a ticket."""
    messages = await TicketService(db, current_user).get_messages(ticket_id)
    return [TicketMessageResponse.model_validate(m) for m in messages]


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> None:
    """Delete a support ticket (Owner and Admin only)."""
    await TicketService(db, current_user).delete_ticket(ticket_id)


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket(
    ticket_id: str,
    data: AssignTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Assign ticket to a support agent and write audit log."""
    return await TicketService(db, current_user).assign_ticket(ticket_id, data.agent_id)


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: str,
    data: ResolveTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Mark ticket as resolved with resolution notes and compute duration."""
    return await TicketService(db, current_user).resolve_ticket(
        ticket_id, resolution_notes=data.resolution_notes
    )


@router.post("/{ticket_id}/reopen", response_model=TicketResponse)
async def reopen_ticket(
    ticket_id: str,
    data: ReopenTicketRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Reopen a resolved ticket and write audit log."""
    return await TicketService(db, current_user).reopen_ticket(
        ticket_id, reason=data.reason
    )


@router.get("/{ticket_id}/audit-logs", response_model=list[AuditLogResponse])
async def get_ticket_audit_logs(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    """Retrieve complete audit history for a specific ticket."""
    logs = await TicketService(db, current_user).get_audit_logs(ticket_id)
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.post("/{ticket_id}/process-ai")
async def process_ticket_ai(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    auto_reply: bool = Query(True),
):
    """
    Trigger the 5-agent AI workflow on a ticket:
    Classification → RAG Retrieval → Generation → Evaluation → AI Response / Escalation.
    """
    return await TicketService(db, current_user).process_ai(ticket_id, auto_reply=auto_reply)


@router.post("/{ticket_id}/classify")
async def classify_ticket(
    ticket_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Run standalone classification agent on a ticket."""
    return await TicketService(db, current_user).classify_ticket(ticket_id)
