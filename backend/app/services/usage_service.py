"""
SupportPilot AI — Usage Tracking & Subscription Limits Service
Monitors and enforces organization quotas (AI messages, tickets, user seats).
"""

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logger import get_logger
from app.models.organization import Organization
from app.models.ticket import Ticket
from app.models.user import User

logger = get_logger(__name__)

# Standard Plan Limits
PLAN_LIMITS = {
    "free": {
        "max_users": 5,
        "max_tickets_per_month": 500,
        "max_ai_messages_per_month": 1000,
    },
    "starter": {
        "max_users": 15,
        "max_tickets_per_month": 2500,
        "max_ai_messages_per_month": 5000,
    },
    "pro": {
        "max_users": 50,
        "max_tickets_per_month": 10000,
        "max_ai_messages_per_month": 25000,
    },
    "enterprise": {
        "max_users": 500,
        "max_tickets_per_month": 100000,
        "max_ai_messages_per_month": 250000,
    },
}


class UsageOverviewResponse(BaseModel):
    organization_id: str
    organization_name: str
    plan: str
    users_count: int
    max_users: int
    tickets_this_month: int
    max_tickets_per_month: int
    ai_messages_used_this_month: int
    max_ai_messages_per_month: int
    ai_messages_remaining: int
    is_ai_quota_exceeded: bool
    is_ticket_quota_exceeded: bool


class UsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_usage(self, organization_id: str) -> UsageOverviewResponse:
        """Fetch organization resource utilization against assigned plan quotas."""
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError("Organization")

        # Active users count
        users_count = await self.db.scalar(
            select(func.count(User.id)).where(
                User.organization_id == organization_id, User.is_active == True
            )
        ) or 0

        # Total tickets created in organization
        tickets_count = await self.db.scalar(
            select(func.count(Ticket.id)).where(Ticket.organization_id == organization_id)
        ) or 0

        ai_remaining = max(0, org.max_ai_messages_per_month - org.ai_messages_used_this_month)
        is_ai_exceeded = org.ai_messages_used_this_month >= org.max_ai_messages_per_month
        is_ticket_exceeded = tickets_count >= org.max_tickets_per_month

        return UsageOverviewResponse(
            organization_id=org.id,
            organization_name=org.name,
            plan=org.plan,
            users_count=users_count,
            max_users=org.max_users,
            tickets_this_month=tickets_count,
            max_tickets_per_month=org.max_tickets_per_month,
            ai_messages_used_this_month=org.ai_messages_used_this_month,
            max_ai_messages_per_month=org.max_ai_messages_per_month,
            ai_messages_remaining=ai_remaining,
            is_ai_quota_exceeded=is_ai_exceeded,
            is_ticket_quota_exceeded=is_ticket_exceeded,
        )

    async def check_and_increment_ai_message(self, organization_id: str) -> bool:
        """
        Atomically verify that the organization has available AI message quota,
        increment the counter if permitted, and commit.
        Returns True if message allowed, False if quota exceeded.
        """
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError("Organization")

        if org.ai_messages_used_this_month >= org.max_ai_messages_per_month:
            logger.warning(
                "ai_quota_exceeded",
                org_id=organization_id,
                used=org.ai_messages_used_this_month,
                max=org.max_ai_messages_per_month,
            )
            return False

        org.ai_messages_used_this_month += 1
        await self.db.commit()
        return True

    async def update_plan(self, organization_id: str, plan_name: str) -> Organization:
        """Update organization plan and synchronize quota ceilings."""
        plan_name = plan_name.lower()
        if plan_name not in PLAN_LIMITS:
            raise ConflictError(
                f"Invalid plan '{plan_name}'. Available: {list(PLAN_LIMITS.keys())}"
            )

        org = await self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError("Organization")

        limits = PLAN_LIMITS[plan_name]
        org.plan = plan_name
        org.max_users = limits["max_users"]
        org.max_tickets_per_month = limits["max_tickets_per_month"]
        org.max_ai_messages_per_month = limits["max_ai_messages_per_month"]

        await self.db.commit()
        logger.info("plan_updated", org_id=organization_id, plan=plan_name)
        return org
