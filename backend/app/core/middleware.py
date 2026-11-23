"""
SupportPilot AI — Middleware Stack
  1. RequestLoggingMiddleware — request/response metadata logging
  2. RateLimitMiddleware       — per-IP sliding-window rate limiting with dedicated auth tier
"""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

_rate_counters: dict[str, list[float]] = {}
_auth_rate_counters: dict[str, list[float]] = {}
_WINDOW_SECONDS = 60


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        response.headers["X-Request-Id"] = request_id

        logger.info(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        # Dedicated strict rate limiting for authentication endpoints (e.g. login, register)
        is_auth_route = path.startswith("/api/v1/auth/login") or path.startswith("/api/v1/auth/register")

        if is_auth_route:
            counter_key = f"auth:{client_ip}"
            if counter_key not in _auth_rate_counters:
                _auth_rate_counters[counter_key] = []
            _auth_rate_counters[counter_key] = [
                ts for ts in _auth_rate_counters[counter_key] if ts > window_start
            ]

            if len(_auth_rate_counters[counter_key]) >= settings.rate_limit_auth_per_minute:
                logger.warning("auth_rate_limit_exceeded", client_ip=client_ip, path=path)
                return Response(
                    content='{"success":false,"error":{"code":"AUTH_RATE_LIMIT","message":"Too many authentication attempts. Please try again in 1 minute."}}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": str(_WINDOW_SECONDS)},
                )
            _auth_rate_counters[counter_key].append(now)

        # General rate limiting across all API endpoints
        if client_ip not in _rate_counters:
            _rate_counters[client_ip] = []
        _rate_counters[client_ip] = [
            ts for ts in _rate_counters[client_ip] if ts > window_start
        ]

        if len(_rate_counters[client_ip]) >= settings.rate_limit_per_minute:
            logger.warning("rate_limit_exceeded", client_ip=client_ip, path=path)
            return Response(
                content='{"success":false,"error":{"code":"RATE_LIMIT","message":"Rate limit exceeded. Please throttle your requests."}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )

        _rate_counters[client_ip].append(now)
        return await call_next(request)


def reset_rate_limiters() -> None:
    """Clear in-memory rate limit tracking counters (used by test suites)."""
    _rate_counters.clear()
    _auth_rate_counters.clear()
