"""
SupportPilot AI — Auth Service (Business Logic)
"""

import re
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.logger import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, TokenResponse, UserResponse, OrganizationResponse

logger = get_logger(__name__)


def _slugify(name: str) -> str:
    """Convert org name to URL-safe slug."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
    return f"{slug}-{str(uuid.uuid4())[:8]}"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: RegisterRequest) -> AuthResponse:
        existing = await self.db.scalar(select(User).where(User.email == data.email))
        if existing:
            raise ConflictError("An account with this email already exists")

        org = Organization(
            name=data.organization_name,
            slug=_slugify(data.organization_name),
        )
        self.db.add(org)
        await self.db.flush()

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.OWNER,
            organization_id=org.id,
            is_verified=False,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        await self.db.refresh(org)

        logger.info("user_registered", user_id=user.id, org_id=org.id)
        return self._build_auth_response(user, org)

    async def login(self, data: LoginRequest) -> AuthResponse:
        result = await self.db.execute(
            select(User)
            .where(User.email == data.email)
            .options(selectinload(User.organization))
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        logger.info("user_login", user_id=user.id, org_id=user.organization_id)
        return self._build_auth_response(user, user.organization)

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        user_id = decode_refresh_token(refresh_token)

        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.organization))
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        return TokenResponse(
            access_token=create_access_token(user.id, user.organization_id, user.role.value),
            refresh_token=create_refresh_token(user.id),
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def get_user_by_id(self, user_id: str) -> User:
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.organization))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError("User")
        return user

    @staticmethod
    def _build_auth_response(user: User, org: Organization) -> AuthResponse:
        return AuthResponse(
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.value,
                is_active=user.is_active,
                is_verified=user.is_verified,
                organization=OrganizationResponse(
                    id=org.id,
                    name=org.name,
                    slug=org.slug,
                    plan=org.plan,
                ),
            ),
            tokens=TokenResponse(
                access_token=create_access_token(user.id, org.id, user.role.value),
                refresh_token=create_refresh_token(user.id),
                expires_in=settings.access_token_expire_minutes * 60,
            ),
        )
