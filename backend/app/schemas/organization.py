"""
SupportPilot AI — Organization Pydantic Schemas
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=255)
    description: str | None = None
    logo_url: str | None = None


class OrganizationStatsResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    max_users: int
    max_tickets_per_month: int
    total_users: int
    total_tickets: int
    open_tickets: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgMemberResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class OrgMemberInviteRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = UserRole.AGENT
    password: str = Field(..., min_length=8, max_length=128)


class OrgMemberUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
