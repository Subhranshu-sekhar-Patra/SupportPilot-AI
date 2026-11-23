"""
SupportPilot AI — Analytics Service
Calculates real PostgreSQL metrics scoped to the organization.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import CustomerFeedback
from app.models.ticket import (
    MessageAuthorType,
    Ticket,
    TicketMessage,
    TicketStatus,
)
from app.schemas.analytics import AnalyticsOverviewResponse


class AnalyticsService:
    def __init__(self, db: AsyncSession, organization_id: str):
        self.db = db
        self.org_id = organization_id

    async def get_overview(self) -> AnalyticsOverviewResponse:
        """
        Compute real organization-scoped analytics directly from PostgreSQL.
        """
        # 1. Total volume
        total_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(Ticket.organization_id == self.org_id)
        ) or 0

        # 2. Open tickets (active queue)
        open_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.organization_id == self.org_id,
                Ticket.status.in_([
                    TicketStatus.OPEN,
                    TicketStatus.ASSIGNED,
                    TicketStatus.IN_PROGRESS,
                    TicketStatus.PENDING_REVIEW,
                    TicketStatus.ESCALATED,
                ]),
            )
        ) or 0

        # 3. Resolved tickets
        resolved_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.organization_id == self.org_id,
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
            )
        ) or 0

        # 4. Currently escalated
        escalated_tickets = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.organization_id == self.org_id,
                Ticket.status == TicketStatus.ESCALATED,
            )
        ) or 0

        # 5. Escalation rate (tickets ever escalated or marked with escalation metadata)
        escalated_total_count = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.organization_id == self.org_id,
                (Ticket.status == TicketStatus.ESCALATED)
                | (Ticket.ai_metadata["escalation"].isnot(None)),
            )
        ) or 0
        escalation_rate = (
            round((escalated_total_count / total_tickets) * 100.0, 2)
            if total_tickets > 0
            else 0.0
        )

        # 6. AI vs Human resolved tickets
        human_resolved_count = await self.db.scalar(
            select(func.count(Ticket.id)).where(
                Ticket.organization_id == self.org_id,
                Ticket.status.in_([TicketStatus.RESOLVED, TicketStatus.CLOSED]),
                Ticket.assigned_to_id.isnot(None),
            )
        ) or 0
        ai_resolved_count = max(0, resolved_tickets - human_resolved_count)

        # 7. Average First Response Time (in seconds)
        first_msg_subq = (
            select(
                TicketMessage.ticket_id,
                func.min(TicketMessage.created_at).label("first_msg_at"),
            )
            .where(
                TicketMessage.author_type.in_([
                    MessageAuthorType.AGENT,
                    MessageAuthorType.AI,
                ]),
                TicketMessage.is_internal.is_(False),
            )
            .group_by(TicketMessage.ticket_id)
            .subquery()
        )
        avg_frt_query = (
            select(
                func.avg(
                    func.extract("epoch", first_msg_subq.c.first_msg_at - Ticket.created_at)
                )
            )
            .join(first_msg_subq, Ticket.id == first_msg_subq.c.ticket_id)
            .where(Ticket.organization_id == self.org_id)
        )
        avg_frt_val = await self.db.scalar(avg_frt_query)
        avg_first_response_time_seconds = (
            round(max(0.0, float(avg_frt_val)), 2) if avg_frt_val is not None else None
        )

        # 8. Average Resolution Time (in seconds)
        avg_res_val = await self.db.scalar(
            select(func.avg(Ticket.resolution_time_seconds)).where(
                Ticket.organization_id == self.org_id,
                Ticket.resolution_time_seconds.isnot(None),
            )
        )
        avg_resolution_time_seconds = (
            round(max(0.0, float(avg_res_val)), 2) if avg_res_val is not None else None
        )

        # 9. Customer Satisfaction (CSAT) metrics
        csat_total = await self.db.scalar(
            select(func.count(CustomerFeedback.id)).where(
                CustomerFeedback.organization_id == self.org_id
            )
        ) or 0

        csat_avg = await self.db.scalar(
            select(func.avg(CustomerFeedback.rating)).where(
                CustomerFeedback.organization_id == self.org_id
            )
        )
        csat_score = round(float(csat_avg), 2) if csat_avg is not None else None

        csat_pos = await self.db.scalar(
            select(func.count(CustomerFeedback.id)).where(
                CustomerFeedback.organization_id == self.org_id,
                CustomerFeedback.rating >= 4,
            )
        ) or 0
        csat_positive_rate = (
            round((csat_pos / csat_total) * 100.0, 2) if csat_total > 0 else None
        )

        # 10. Distributions
        cat_rows = await self.db.execute(
            select(Ticket.ai_category, func.count(Ticket.id))
            .where(Ticket.organization_id == self.org_id, Ticket.ai_category.isnot(None))
            .group_by(Ticket.ai_category)
        )
        category_distribution = {row[0]: row[1] for row in cat_rows.all()}

        pri_rows = await self.db.execute(
            select(Ticket.priority, func.count(Ticket.id))
            .where(Ticket.organization_id == self.org_id)
            .group_by(Ticket.priority)
        )
        priority_distribution = {row[0].value: row[1] for row in pri_rows.all()}

        st_rows = await self.db.execute(
            select(Ticket.status, func.count(Ticket.id))
            .where(Ticket.organization_id == self.org_id)
            .group_by(Ticket.status)
        )
        status_distribution = {row[0].value: row[1] for row in st_rows.all()}

        return AnalyticsOverviewResponse(
            total_tickets=total_tickets,
            open_tickets=open_tickets,
            resolved_tickets=resolved_tickets,
            escalated_tickets=escalated_tickets,
            ai_resolved_tickets=ai_resolved_count,
            human_resolved_tickets=human_resolved_count,
            escalation_rate=escalation_rate,
            avg_first_response_time_seconds=avg_first_response_time_seconds,
            avg_resolution_time_seconds=avg_resolution_time_seconds,
            csat_score=csat_score,
            csat_total_feedback=csat_total,
            csat_positive_rate=csat_positive_rate,
            category_distribution=category_distribution,
            priority_distribution=priority_distribution,
            status_distribution=status_distribution,
        )
