"""
SupportPilot AI — Ticket Service (Business Logic)
Implements the ticket state machine and org-scoped CRUD.
"""

from datetime import datetime, timezone
import math

from app.core.logger import get_logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.models.audit_log import AuditLog
from app.models.ticket import (
    MessageAuthorType,
    Ticket,
    TicketMessage,
    TicketPriority,
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
    TicketStatus.OPEN:           {TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED, TicketStatus.RESOLVED},
    TicketStatus.ASSIGNED:       {TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED, TicketStatus.OPEN, TicketStatus.RESOLVED},
    TicketStatus.IN_PROGRESS:    {TicketStatus.PENDING_REVIEW, TicketStatus.ESCALATED, TicketStatus.RESOLVED, TicketStatus.ASSIGNED},
    TicketStatus.PENDING_REVIEW: {TicketStatus.RESOLVED, TicketStatus.IN_PROGRESS},
    TicketStatus.ESCALATED:      {TicketStatus.IN_PROGRESS, TicketStatus.ASSIGNED, TicketStatus.RESOLVED},
    TicketStatus.RESOLVED:       {TicketStatus.CLOSED, TicketStatus.OPEN, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED:         {TicketStatus.OPEN, TicketStatus.IN_PROGRESS},
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
        logger.info("ticket_created", ticket_id=ticket.id, org_id=self.org_id)
        return await self.get_ticket(ticket.id)

    async def get_ticket(self, ticket_id: str) -> TicketResponse:
        """Get a single ticket by ID, enforcing org scope."""
        ticket = await self._get_ticket_or_404(ticket_id)
        return TicketResponse.model_validate(ticket)

    async def list_tickets(
        self,
        page: int = 1,
        page_size: int = 20,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: str | None = None,
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
        if priority:
            query = query.where(Ticket.priority == priority)
        if category:
            query = query.where(Ticket.ai_category == category)
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
        logger.info("ticket_updated", ticket_id=ticket_id)
        return await self.get_ticket(ticket.id)

    async def add_message(
        self, ticket_id: str, data: AddMessageRequest, is_ai: bool = False
    ) -> TicketResponse:
        """Add a message to a ticket conversation thread."""
        ticket = await self._get_ticket_or_404(ticket_id)

        author_type = MessageAuthorType.AI if is_ai else MessageAuthorType.AGENT
        msg = TicketMessage(
            ticket_id=ticket_id,
            author_type=author_type,
            author_id=self.user.id if not is_ai else None,
            content=data.content,
            is_internal=data.is_internal,
        )
        self.db.add(msg)

        # Audit log for manual or internal responses
        audit = AuditLog(
            user_id=self.user.id,
            organization_id=self.org_id,
            action="message_added",
            resource_type="ticket",
            resource_id=ticket.id,
            description="Internal note added" if data.is_internal else "Reply added to ticket",
            extra_data={
                "is_internal": data.is_internal,
                "author_type": author_type.value,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        return await self.get_ticket(ticket.id)

    async def assign_ticket(self, ticket_id: str, agent_id: str) -> TicketResponse:
        """Assign ticket to a human agent, validate membership, and record audit."""
        ticket = await self._get_ticket_or_404(ticket_id)

        # Verify agent belongs to the organization
        agent = await self.db.scalar(
            select(User).where(User.id == agent_id, User.organization_id == self.org_id)
        )
        if not agent:
            raise NotFoundError("Agent user not found in this organization")

        # Agents can only self-assign
        if self.user.role in (UserRole.AGENT,) and agent_id != self.user.id:
            raise AuthorizationError("Agents can only assign tickets to themselves")

        old_assigned = ticket.assigned_to_id
        old_status = ticket.status
        ticket.assigned_to_id = agent.id

        # Update status if open or escalated
        if ticket.status in (TicketStatus.OPEN, TicketStatus.ESCALATED):
            ticket.status = TicketStatus.IN_PROGRESS

        # Add system message in conversation thread
        agent_name = agent.full_name or agent.email
        sys_msg = TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.SYSTEM,
            author_id=self.user.id,
            content=f"Ticket assigned to support agent {agent_name}.",
            is_internal=True,
        )
        self.db.add(sys_msg)

        # Record audit log
        audit = AuditLog(
            user_id=self.user.id,
            organization_id=self.org_id,
            action="ticket_assigned",
            resource_type="ticket",
            resource_id=ticket.id,
            description=f"Ticket assigned to {agent_name}",
            extra_data={
                "previous_assigned_to": old_assigned,
                "assigned_to_id": agent.id,
                "previous_status": old_status.value,
                "new_status": ticket.status.value,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info("ticket_assigned", ticket_id=ticket.id, agent_id=agent.id, by_user=self.user.id)
        return await self.get_ticket(ticket.id)

    async def resolve_ticket(
        self, ticket_id: str, resolution_notes: str | None = None
    ) -> TicketResponse:
        """Resolve a support ticket, compute duration, and record audit history."""
        ticket = await self._get_ticket_or_404(ticket_id)
        self._validate_transition(ticket.status, TicketStatus.RESOLVED)

        old_status = ticket.status
        ticket.status = TicketStatus.RESOLVED
        ticket.resolution_notes = resolution_notes

        # Calculate resolution duration in seconds
        now = datetime.now(timezone.utc)
        created_at = (
            ticket.created_at
            if ticket.created_at.tzinfo
            else ticket.created_at.replace(tzinfo=timezone.utc)
        )
        duration_seconds = max(0, int((now - created_at).total_seconds()))
        ticket.resolution_time_seconds = duration_seconds

        # Add system message to conversation
        msg_text = (
            f"Ticket marked as resolved. Resolution notes: {resolution_notes}"
            if resolution_notes
            else "Ticket marked as resolved by agent."
        )
        sys_msg = TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.SYSTEM,
            author_id=self.user.id,
            content=msg_text,
            is_internal=False,
        )
        self.db.add(sys_msg)

        # Record audit log
        audit = AuditLog(
            user_id=self.user.id,
            organization_id=self.org_id,
            action="ticket_resolved",
            resource_type="ticket",
            resource_id=ticket.id,
            description="Ticket resolved",
            extra_data={
                "previous_status": old_status.value,
                "resolution_notes": resolution_notes,
                "resolution_time_seconds": duration_seconds,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info(
            "ticket_resolved",
            ticket_id=ticket.id,
            duration_seconds=duration_seconds,
            by_user=self.user.id,
        )
        return await self.get_ticket(ticket.id)

    async def reopen_ticket(
        self, ticket_id: str, reason: str | None = None
    ) -> TicketResponse:
        """Reopen a resolved or closed ticket and record audit log."""
        ticket = await self._get_ticket_or_404(ticket_id)
        self._validate_transition(ticket.status, TicketStatus.IN_PROGRESS)

        old_status = ticket.status
        ticket.status = TicketStatus.IN_PROGRESS

        # Add system message
        msg_text = (
            f"Ticket reopened. Reason: {reason}"
            if reason
            else "Ticket reopened by support agent."
        )
        sys_msg = TicketMessage(
            ticket_id=ticket.id,
            author_type=MessageAuthorType.SYSTEM,
            author_id=self.user.id,
            content=msg_text,
            is_internal=False,
        )
        self.db.add(sys_msg)

        # Record audit log
        audit = AuditLog(
            user_id=self.user.id,
            organization_id=self.org_id,
            action="ticket_reopened",
            resource_type="ticket",
            resource_id=ticket.id,
            description="Ticket reopened",
            extra_data={
                "previous_status": old_status.value,
                "reason": reason,
            },
        )
        self.db.add(audit)

        await self.db.commit()
        logger.info("ticket_reopened", ticket_id=ticket.id, reason=reason, by_user=self.user.id)
        return await self.get_ticket(ticket.id)

    async def get_audit_logs(self, ticket_id: str) -> list[AuditLog]:
        """Fetch audit trail history for a specific ticket in this organization."""
        await self._get_ticket_or_404(ticket_id)
        result = await self.db.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == "ticket",
                AuditLog.resource_id == ticket_id,
                AuditLog.organization_id == self.org_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_messages(self, ticket_id: str) -> list[TicketMessage]:
        """Get all messages in a ticket conversation thread, verifying org access."""
        ticket = await self._get_ticket_or_404(ticket_id)
        result = await self.db.execute(
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket.id)
            .order_by(TicketMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_ticket(self, ticket_id: str) -> None:
        """Delete/archive a ticket from the organization."""
        ticket = await self._get_ticket_or_404(ticket_id)
        await self.db.delete(ticket)
        await self.db.commit()
        logger.info("ticket_deleted", ticket_id=ticket_id, org_id=self.org_id)

    async def process_ai(
        self,
        ticket_id: str,
        auto_reply: bool = True,
        llm_override=None,
    ):
        """
        Run the complete SupportPilot AI workflow:
        Classification → RAG Retrieval → Generation → Evaluation → AI Response / Escalation.
        """
        ticket = await self._get_ticket_or_404(ticket_id)
        from app.ai.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator(org_id=self.org_id, llm=llm_override)
        result = await orchestrator.process_and_persist_ticket(
            db=self.db, ticket=ticket, auto_reply=auto_reply
        )
        return result

    async def classify_ticket(
        self,
        ticket_id: str,
        llm_override=None,
    ):
        """Run standalone query classification."""
        ticket = await self._get_ticket_or_404(ticket_id)
        from app.ai.agents.classifier import ClassifierAgent
        from app.ai.providers.gemini import get_llm_provider
        llm = llm_override or get_llm_provider()
        classifier = ClassifierAgent(llm)
        output = await classifier.classify(ticket.subject, ticket.description)
        ticket.ai_category = output.category.value
        ticket.ai_confidence_score = output.confidence
        await self.db.commit()
        await self.db.refresh(ticket)
        return output

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
