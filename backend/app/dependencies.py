"""
SupportPilot AI — Shared FastAPI Dependencies
Provides dependency-injected current user, org scoping, and RBAC guards.
"""

from typing import Annotated
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

logger = get_logger(__name__)


async def get_current_user(
    authorization: Annotated[str, Header(alias="Authorization")],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the Bearer token from Authorization header."""
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Invalid authorization header format")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token)

    service = AuthService(db)
    user = await service.get_user_by_id(payload["sub"])
    logger.info("authenticated_user", user_id=user.id, org_id=user.organization_id)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole):
    """Enforce role-based access control."""
    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"This action requires one of: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return _check_role
