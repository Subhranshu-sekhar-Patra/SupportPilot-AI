"""
SupportPilot AI — Ticket Service (Business Logic)
Implements the ticket state machine and org-scoped CRUD.
"""

import math

from app.core.logger import get_logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models.ticket import (
    MessageAuthorType,
    Ticket,
    TicketMessage,
    TicketStatus,
)
from app.models.user import User, UserRole
from app.schemas.ticket import (
    AddMessageRequest,
    CreateTicketRequest,
    TicketListResponse,
    TicketResponse,
    UpdateTicketRequest,
)

logger = get_logger(__name__)

# Valid state transitions
_VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN:           {TicketStatus.ASSIGNED, TicketStatus.ESCALATED},
    TicketStatus.ASSIGNED:       {TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED, TicketStatus.OPEN},
    TicketStatus.IN_PROGRESS:    {TicketStatus.PENDING_REVIEW, TicketStatus.ESCALATED},
    TicketStatus.PENDING_REVIEW: {TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS},
    TicketStatus.ESCALATED:      {TicketStatus.IN_PROGRESS, TicketStatus.ASSIGNED},
    TicketStatus.RESOLVED:       {TicketStatus.CLOSED, TicketStatus.OPEN},
    TicketStatus.CLOSED:         set(),
}


class TicketService:
    """
    All ticket operations are scoped to org_id — a user can only
    see/modify tickets belonging to their organization.
    """

    def __init__(self, db: AsyncSession, current_user: User):
        self.db = db
        self.user = current_user
        self.org_id = current_user.organization_id

    async def create_ticket(self, data: CreateTicketRequest) -> TicketResponse:
        """Create a new ticket in the OPEN state."""
        ticket = Ticket(
            subject=data.subject,
            description=data.description,
            priority=data.priority,
            channel=data.channel,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            organization_id=self.org_id,
            created_by_id=self.user.id,
            status=TicketStatus.OPEN,
        )
        self.db.add(ticket)

        # Add initial customer message
        initial_msg = TicketMessage(
            ticket=ticket,
            author_type=MessageAuthorType.CUSTOMER,
            author_id=None,
            content=data.description,
        )
        self.db.add(initial_msg)
        await self.db.commit()
        await self.db.refresh(ticket)

        logger.info("ticket_created", ticket_id=ticket.id, org_id=self.org_id)
        return TicketResponse.model_validate(ticket)

    async def get_ticket(self, ticket_id: str) -> TicketResponse:
        """Get a single ticket by ID, enforcing org scope."""
        ticket = await self._get_ticket_or_404(ticket_id)
        return TicketResponse.model_validate(ticket)

    async def list_tickets(
        self,
        page: int = 1,
        page_size: int = 20,
        status: TicketStatus | None = None,
        assigned_to_me: bool = False,
    ) -> TicketListResponse:
        """Paginated, filterable ticket list scoped to org."""
        query = (
            select(Ticket)
            .where(Ticket.organization_id == self.org_id)
            .options(selectinload(Ticket.messages))
            .order_by(Ticket.created_at.desc())
        )
        if status:
            query = query.where(Ticket.status == status)
        if assigned_to_me:
            query = query.where(Ticket.assigned_to_id == self.user.id)

        # Count
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total = await self.db.scalar(count_query) or 0

        # Paginate
        offset = (page - 1) * page_size
        result = await self.db.execute(query.offset(offset).limit(page_size))
        tickets = result.scalars().all()

        return TicketListResponse(
            items=[TicketResponse.model_validate(t) for t in tickets],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total else 0,
        )

    async def update_ticket(
        self, ticket_id: str, data: UpdateTicketRequest
    ) -> TicketResponse:
        """Update ticket fields with state machine validation."""
        ticket = await self._get_ticket_or_404(ticket_id)

        if data.status and data.status != ticket.status:
            self._validate_transition(ticket.status, data.status)
            ticket.status = data.status

        if data.subject is not None:
            ticket.subject = data.subject
        if data.description is not None:
            ticket.description = data.description
        if data.priority is not None:
            ticket.priority = data.priority
        if data.resolution_notes is not None:
            ticket.resolution_notes = data.resolution_notes

        # Assignment — agents can only self-assign; admins/owners can assign freely
        if data.assigned_to_id is not None:
            if self.user.role in (UserRole.AGENT,) and data.assigned_to_id != self.user.id:
                raise AuthorizationError("Agents can only assign tickets to themselves")
            ticket.assigned_to_id = data.assigned_to_id
            if ticket.status == TicketStatus.OPEN:
                ticket.status = TicketStatus.ASSIGNED

        await self.db.commit()
        await self.db.refresh(ticket)
        logger.info("ticket_updated", ticket_id=ticket_id)
        return TicketResponse.model_validate(ticket)

    async def add_message(
        self, ticket_id: str, data: AddMessageRequest, is_ai: bool = False
    ) -> TicketResponse:
        """Add a message to a ticket conversation thread."""
        ticket = await self._get_ticket_or_404(ticket_id)

        msg = TicketMessage(
            ticket_id=ticket_id,
            author_type=MessageAuthorType.AI if is_ai else MessageAuthorType.AGENT,
            author_id=self.user.id,
            content=data.content,
            is_internal=data.is_internal,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(ticket)
        return TicketResponse.model_validate(ticket)

    # ── Helpers ────────────────────────────────────────────

    async def _get_ticket_or_404(self, ticket_id: str) -> Ticket:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.id == ticket_id, Ticket.organization_id == self.org_id)
            .options(selectinload(Ticket.messages))
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            raise NotFoundError("Ticket")
        return ticket

    @staticmethod
    def _validate_transition(current: TicketStatus, next_status: TicketStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if next_status not in allowed:
            raise ConflictError(
                f"Invalid status transition: {current.value} → {next_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
