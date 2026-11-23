"""
SupportPilot AI — Shared FastAPI Dependencies
Provides dependency-injected current user, org scoping, and RBAC guards.
Integrates HTTPBearer for interactive Swagger UI documentation.
"""

from typing import Annotated
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logger import get_logger
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.auth_service import AuthService

logger = get_logger(__name__)

# HTTPBearer enables the Swagger UI "Authorize" button
http_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer_scheme)],
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the Bearer token from the Authorization header."""
    token: str | None = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        # Fallback to direct Authorization header check
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        raise AuthenticationError("Authentication token is missing. Please sign in.")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    service = AuthService(db)
    user = await service.get_user_by_id(user_id)
    if not user.is_active:
        raise AuthenticationError("Account has been deactivated")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed_roles: UserRole):
    """Enforce role-based access control with clear hierarchy error reporting."""
    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Action restricted. Required role(s): {[r.value for r in allowed_roles]}, "
                f"current role: '{current_user.role.value}'"
            )
        return current_user

    return _check_role
