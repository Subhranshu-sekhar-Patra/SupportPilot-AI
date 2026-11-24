"""
SupportPilot AI — Organizations API Endpoints (v1)
Multi-tenant organization profile, team members, and RBAC management.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.core.security import hash_password
from app.db.session import get_db
from app.dependencies import CurrentUser, require_role
from app.models.organization import Organization
from pydantic import BaseModel, Field
from app.models.knowledge import KnowledgeDocument
from app.models.ticket import Ticket, TicketStatus
from app.services.usage_service import UsageOverviewResponse, UsageService
from app.models.user import User, UserRole
from app.schemas.organization import (
    OrganizationStatsResponse,
    OrganizationUpdate,
    OrgMemberInviteRequest,
    OrgMemberResponse,
    OrgMemberUpdateRequest,
)

router = APIRouter(prefix="/organizations", tags=["Organizations & Team"])


@router.get(
    "/me",
    response_model=OrganizationStatsResponse,
    summary="Get current organization details and usage metrics",
)
async def get_current_organization(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OrganizationStatsResponse:
    org_id = current_user.organization_id

    # Fetch organization
    org = await db.get(Organization, org_id)
    if not org:
        raise NotFoundError("Organization")

    # Aggregate counts
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.organization_id == org_id)
    ) or 0
    total_tickets = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.organization_id == org_id)
    ) or 0
    open_tickets = await db.scalar(
        select(func.count(Ticket.id)).where(
            Ticket.organization_id == org_id,
            Ticket.status.in_([TicketStatus.OPEN, TicketStatus.ASSIGNED, TicketStatus.IN_PROGRESS]),
        )
    ) or 0

    return OrganizationStatsResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        max_users=org.max_users,
        max_tickets_per_month=org.max_tickets_per_month,
        total_users=total_users,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        created_at=org.created_at,
    )


@router.patch(
    "/me",
    response_model=OrganizationStatsResponse,
    summary="Update organization details (Owner and Admin only)",
)
async def update_organization(
    data: OrganizationUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> OrganizationStatsResponse:
    org = await db.get(Organization, current_user.organization_id)
    if not org:
        raise NotFoundError("Organization")

    if data.name is not None:
        org.name = data.name
    if data.description is not None:
        org.description = data.description
    if data.logo_url is not None:
        org.logo_url = data.logo_url

    await db.commit()
    await db.refresh(org)
    return await get_current_organization(current_user=current_user, db=db)


@router.get(
    "/members",
    response_model=list[OrgMemberResponse],
    summary="List members in current organization",
)
async def list_organization_members(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[OrgMemberResponse]:
    result = await db.execute(
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.asc())
    )
    users = result.scalars().all()
    return [
        OrgMemberResponse(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role.value,
            is_active=u.is_active,
            is_verified=u.is_verified,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.post(
    "/members",
    response_model=OrgMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite or add a team member (Owner and Admin only)",
)
async def add_organization_member(
    data: OrgMemberInviteRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> OrgMemberResponse:
    # Check if email is already taken
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise ConflictError("A user with this email address already exists")

    # Restrict assigning OWNER role unless caller is OWNER
    if data.role == UserRole.OWNER and current_user.role != UserRole.OWNER:
        raise AuthorizationError("Only the workspace Owner can transfer or grant Owner role")

    new_user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
        organization_id=current_user.organization_id,
        is_verified=True,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return OrgMemberResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        role=new_user.role.value,
        is_active=new_user.is_active,
        is_verified=new_user.is_verified,
        created_at=new_user.created_at,
    )


@router.patch(
    "/members/{user_id}",
    response_model=OrgMemberResponse,
    summary="Update a team member's role or active status (Owner and Admin only)",
)
async def update_organization_member(
    user_id: str,
    data: OrgMemberUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> OrgMemberResponse:
    target_user = await db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    if not target_user:
        raise NotFoundError("User")

    if target_user.role == UserRole.OWNER and current_user.role != UserRole.OWNER:
        raise AuthorizationError("Cannot modify the workspace Owner")

    if data.role is not None:
        if data.role == UserRole.OWNER and current_user.role != UserRole.OWNER:
            raise AuthorizationError("Only an Owner can designate another Owner")
        target_user.role = data.role

    if data.is_active is not None:
        if target_user.id == current_user.id:
            raise ConflictError("Cannot deactivate your own account")
        target_user.is_active = data.is_active

    await db.commit()
    await db.refresh(target_user)

    return OrgMemberResponse(
        id=target_user.id,
        email=target_user.email,
        full_name=target_user.full_name,
        role=target_user.role.value,
        is_active=target_user.is_active,
        is_verified=target_user.is_verified,
        created_at=target_user.created_at,
    )


@router.delete(
    "/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a team member from the organization (Owner and Admin only)",
)
async def remove_organization_member(
    user_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> None:
    target_user = await db.scalar(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    if not target_user:
        raise NotFoundError("User")

    if target_user.id == current_user.id:
        raise ConflictError("Cannot remove yourself from the organization")

    if target_user.role == UserRole.OWNER:
        raise AuthorizationError("Cannot remove the workspace Owner")

    await db.delete(target_user)
    await db.commit()


# ── Onboarding, Usage & Widget Configuration ──────────────

class OnboardingStep(BaseModel):
    id: str
    title: str
    description: str
    completed: bool


class OnboardingStatusResponse(BaseModel):
    is_fully_onboarded: bool
    completed_steps_count: int
    total_steps_count: int
    steps: list[OnboardingStep]


class WidgetSettingsRequest(BaseModel):
    widget_enabled: bool | None = None
    widget_primary_color: str | None = None
    widget_greeting: str | None = None
    widget_allowed_domains: str | None = None


class WidgetSettingsResponse(BaseModel):
    widget_enabled: bool
    widget_primary_color: str
    widget_greeting: str | None
    widget_allowed_domains: str | None
    embed_snippet: str


@router.get(
    "/me/usage",
    response_model=UsageOverviewResponse,
    summary="Get organization AI message and ticket usage against plan quotas",
)
async def get_organization_usage(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UsageOverviewResponse:
    """Fetch current organization resource usage, AI message limits, and plan details."""
    service = UsageService(db)
    return await service.get_usage(current_user.organization_id)


@router.get(
    "/me/onboarding",
    response_model=OnboardingStatusResponse,
    summary="Get organization onboarding checklist progress",
)
async def get_organization_onboarding_status(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """Evaluate organization setup milestones (team, knowledge docs, widget, first ticket)."""
    org_id = current_user.organization_id
    org = await db.get(Organization, org_id)
    if not org:
        raise NotFoundError("Organization")

    # Milestone 1: Knowledge base docs uploaded
    docs_count = await db.scalar(
        select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.organization_id == org_id)
    ) or 0

    # Milestone 2: Team members invited
    members_count = await db.scalar(
        select(func.count(User.id)).where(User.organization_id == org_id)
    ) or 0

    # Milestone 3: Tickets handled
    tickets_count = await db.scalar(
        select(func.count(Ticket.id)).where(Ticket.organization_id == org_id)
    ) or 0

    steps = [
        OnboardingStep(
            id="account_created",
            title="Create Workspace Account",
            description="Organization workspace and owner credentials registered.",
            completed=True,
        ),
        OnboardingStep(
            id="knowledge_uploaded",
            title="Upload Knowledge Documents",
            description="Ingest company policies, FAQs, or manuals into RAG vector store.",
            completed=docs_count > 0,
        ),
        OnboardingStep(
            id="team_invited",
            title="Invite Support Agents",
            description="Add tier-1 and tier-2 human support specialists to your organization.",
            completed=members_count > 1,
        ),
        OnboardingStep(
            id="widget_customized",
            title="Configure Customer Chatbot Widget",
            description="Customize branding, theme color, and allowed domains.",
            completed=bool(org.widget_enabled),
        ),
        OnboardingStep(
            id="first_ticket_handled",
            title="Process First Customer Ticket",
            description="Resolve an inbound customer inquiry using automated AI or human workflow.",
            completed=tickets_count > 0,
        ),
    ]

    completed_count = sum(1 for s in steps if s.completed)
    return OnboardingStatusResponse(
        is_fully_onboarded=completed_count == len(steps),
        completed_steps_count=completed_count,
        total_steps_count=len(steps),
        steps=steps,
    )


@router.patch(
    "/me/widget",
    response_model=WidgetSettingsResponse,
    summary="Configure the embeddable customer chatbot widget",
)
async def update_widget_settings(
    data: WidgetSettingsRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    _guard=Depends(require_role(UserRole.OWNER, UserRole.ADMIN)),
) -> WidgetSettingsResponse:
    """Update embeddable chatbot widget theme, greeting message, and enabled status."""
    org = await db.get(Organization, current_user.organization_id)
    if not org:
        raise NotFoundError("Organization")

    if data.widget_enabled is not None:
        org.widget_enabled = data.widget_enabled
    if data.widget_primary_color is not None:
        org.widget_primary_color = data.widget_primary_color
    if data.widget_greeting is not None:
        org.widget_greeting = data.widget_greeting
    if data.widget_allowed_domains is not None:
        org.widget_allowed_domains = data.widget_allowed_domains

    await db.commit()
    await db.refresh(org)

    snippet = (
        f'<script src="https://api.supportpilot.dev/api/v1/widget/loader.js" '
        f'data-org="{org.slug}" async></script>'
    )

    return WidgetSettingsResponse(
        widget_enabled=org.widget_enabled,
        widget_primary_color=org.widget_primary_color,
        widget_greeting=org.widget_greeting,
        widget_allowed_domains=org.widget_allowed_domains,
        embed_snippet=snippet,
    )
