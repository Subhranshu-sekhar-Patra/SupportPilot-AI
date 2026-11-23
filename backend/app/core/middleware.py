"""
SupportPilot AI — Middleware Stack
  1. RequestLoggingMiddleware — request/response metadata logging
  2. RateLimitMiddleware       — per-IP sliding-window rate limiting
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
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - _WINDOW_SECONDS

        if client_ip not in _rate_counters:
            _rate_counters[client_ip] = []
        _rate_counters[client_ip] = [
            ts for ts in _rate_counters[client_ip] if ts > window_start
        ]

        if len(_rate_counters[client_ip]) >= settings.rate_limit_per_minute:
            logger.warning("rate_limit_exceeded", client_ip=client_ip)
            return Response(
                content='{"success":false,"error":{"code":"RATE_LIMIT","message":"Rate limit exceeded"}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(_WINDOW_SECONDS)},
            )

        _rate_counters[client_ip].append(now)
        return await call_next(request)
