"""
SupportPilot AI — Auth API Endpoints (v1)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import CurrentUser
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    OrganizationResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="Register a new organization and owner account",
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await AuthService(db).register(data)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and receive token pair",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    return await AuthService(db).login(data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using refresh token",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    return await AuthService(db).refresh_tokens(data.refresh_token)


@router.post(
    "/change-password",
    status_code=204,
    summary="Change password for current authenticated user",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    await AuthService(db).change_password(current_user.id, data)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.value,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        organization=OrganizationResponse(
            id=current_user.organization.id,
            name=current_user.organization.name,
            slug=current_user.organization.slug,
            plan=current_user.organization.plan,
        ),
    )
