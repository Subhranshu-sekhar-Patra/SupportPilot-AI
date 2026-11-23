"""
SupportPilot AI — Analytics API (v1)
Basic org-scoped ticket metrics.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser
from app.models.ticket import Ticket, TicketStatus

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    escalated_tickets: int
    avg_quality_score: float | None
    tickets_by_category: dict[str, int]
    tickets_by_priority: dict[str, int]


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Return aggregate ticket statistics for the organization dashboard."""
    org_id = current_user.organization_id

    # Total tickets
    total = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.organization_id == org_id)
    ) or 0

    # By status
    open_count = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.organization_id == org_id,
            Ticket.status == TicketStatus.OPEN,
        )
    ) or 0

    resolved_count = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.organization_id == org_id,
            Ticket.status == TicketStatus.RESOLVED,
        )
    ) or 0

    escalated_count = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.organization_id == org_id,
            Ticket.status == TicketStatus.ESCALATED,
        )
    ) or 0

    # Average AI quality score
    avg_quality = await db.scalar(
        select(func.avg(Ticket.ai_quality_score)).where(
            Ticket.organization_id == org_id,
            Ticket.ai_quality_score.isnot(None),
        )
    )

    # Category distribution
    category_rows = await db.execute(
        select(Ticket.ai_category, func.count(Ticket.id))
        .where(Ticket.organization_id == org_id, Ticket.ai_category.isnot(None))
        .group_by(Ticket.ai_category)
    )
    tickets_by_category = {row[0]: row[1] for row in category_rows.all()}

    # Priority distribution
    priority_rows = await db.execute(
        select(Ticket.priority, func.count(Ticket.id))
        .where(Ticket.organization_id == org_id)
        .group_by(Ticket.priority)
    )
    tickets_by_priority = {row[0].value: row[1] for row in priority_rows.all()}

    return DashboardStats(
        total_tickets=total,
        open_tickets=open_count,
        resolved_tickets=resolved_count,
        escalated_tickets=escalated_count,
        avg_quality_score=round(float(avg_quality), 3) if avg_quality else None,
        tickets_by_category=tickets_by_category,
        tickets_by_priority=tickets_by_priority,
    )
