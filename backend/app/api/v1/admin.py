"""
SupportPilot AI — Platform Super Admin API (v1)
Restricted to platform-level administrators (SUPER_ADMIN).
Provides cross-tenant observability, organization lifecycle, and quota management.
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_role
from app.models.organization import Organization
from app.models.ticket import Ticket
from app.models.user import User, UserRole
from app.services.usage_service import UsageOverviewResponse, UsageService

router = APIRouter(prefix="/admin", tags=["Super Admin"])


class AdminOrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    is_active: bool
    users_count: int
    tickets_count: int
    ai_messages_used: int
    max_ai_messages: int
    created_at: str


class UpdatePlanRequest(BaseModel):
    plan: str = Field(..., description="Target plan name: free, starter, pro, enterprise")


@router.get(
    "/organizations",
    response_model=list[AdminOrganizationSummary],
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)
async def list_all_organizations(db: AsyncSession = Depends(get_db)):
    """List all tenant organizations across the entire platform."""
    orgs_query = select(Organization).order_by(Organization.created_at.desc())
    orgs = (await db.execute(orgs_query)).scalars().all()

    summaries = []
    for org in orgs:
        users_cnt = await db.scalar(
            select(func.count(User.id)).where(User.organization_id == org.id)
        ) or 0
        tickets_cnt = await db.scalar(
            select(func.count(Ticket.id)).where(Ticket.organization_id == org.id)
        ) or 0

        summaries.append(
            AdminOrganizationSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
                plan=org.plan,
                is_active=org.is_active,
                users_count=users_cnt,
                tickets_count=tickets_cnt,
                ai_messages_used=org.ai_messages_used_this_month,
                max_ai_messages=org.max_ai_messages_per_month,
                created_at=org.created_at.isoformat(),
            )
        )
    return summaries


@router.patch(
    "/organizations/{org_id}/plan",
    response_model=UsageOverviewResponse,
    dependencies=[Depends(require_role(UserRole.SUPER_ADMIN))],
)
async def update_organization_plan(
    org_id: str,
    data: UpdatePlanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Upgrade or downgrade an organization's subscription tier and sync quotas."""
    service = UsageService(db)
    await service.update_plan(org_id, data.plan)
    return await service.get_usage(org_id)
