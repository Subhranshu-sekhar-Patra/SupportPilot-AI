"""
SupportPilot AI — Custom Exception Classes and Handlers
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.core.logger import get_logger

logger = get_logger(__name__)


class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, status_code: int = 500, error_code: str = "INTERNAL_ERROR"):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "AUTHENTICATION_ERROR")


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN, "AUTHORIZATION_ERROR")


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status.HTTP_404_NOT_FOUND, "NOT_FOUND")


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR")


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_409_CONFLICT, "CONFLICT_ERROR")


class RateLimitError(AppException):
    def __init__(self):
        super().__init__("Rate limit exceeded", status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT")


class AIProviderError(AppException):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_502_BAD_GATEWAY, "AI_PROVIDER_ERROR")


def error_response(error_code: str, message: str) -> dict:
    return {"success": False, "error": {"code": error_code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "app_exception",
            error_code=exc.error_code,
            message=exc.message,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.error_code, exc.message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", path=str(request.url.path), error=str(exc))
        return JSONResponse(
            status_code=500,
            content=error_response("INTERNAL_ERROR", "An unexpected error occurred"),
        )
