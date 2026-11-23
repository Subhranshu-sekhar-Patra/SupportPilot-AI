"""
SupportPilot AI — Tickets API Endpoints (v1)
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser
from app.models.ticket import TicketStatus
from app.schemas.ticket import (
    AddMessageRequest,
    CreateTicketRequest,
    TicketListResponse,
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
    assigned_to_me: bool = Query(False),
) -> TicketListResponse:
    """List tickets for the current organization (paginated)."""
    return await TicketService(db, current_user).list_tickets(
        page=page,
        page_size=page_size,
        status=status,
        assigned_to_me=assigned_to_me,
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
