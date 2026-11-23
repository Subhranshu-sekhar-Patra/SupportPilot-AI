"""
SupportPilot AI — JWT & Password Security
Uses bcrypt directly for password hashing and python-jose for JWT tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import bcrypt
from jose import JWTError, jwt

from app.config import settings
from app.core.exceptions import AuthenticationError


# ── Password Hashing ───────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt with salt."""
    pwd_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain-text password against bcrypt hash."""
    pwd_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


# ── JWT Tokens ─────────────────────────────────────────────

def _build_token(
    subject: str,
    token_type: str,
    extra_claims: dict[str, Any],
    expires_delta: timedelta,
) -> str:
    """Internal helper to build a signed JWT."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        **extra_claims,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(
    user_id: str,
    org_id: str,
    role: str,
) -> str:
    """
    Create a short-lived access token.
    Claims include user_id, org_id, and role for RBAC.
    """
    return _build_token(
        subject=user_id,
        token_type="access",
        extra_claims={"org_id": org_id, "role": role},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token (user_id only)."""
    return _build_token(
        subject=user_id,
        token_type="refresh",
        extra_claims={},
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access token.
    Raises AuthenticationError on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        return payload
    except JWTError as e:
        raise AuthenticationError(f"Invalid or expired token: {e}") from e


def decode_refresh_token(token: str) -> str:
    """
    Decode refresh token and return user_id (sub).
    Raises AuthenticationError on invalid/expired tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        return payload["sub"]
    except JWTError as e:
        raise AuthenticationError(f"Invalid or expired refresh token: {e}") from e
