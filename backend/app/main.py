"""
SupportPilot AI — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logger import get_logger
from app.core.middleware import RateLimitMiddleware, RequestLoggingMiddleware
from app.core.exceptions import register_exception_handlers
from app.db.session import engine, Base
from app.api.v1.router import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # ── Load GCP Secret Manager secrets (no-op in dev/local) ──
    try:
        from app.services.secret_manager_service import load_secrets_from_manager  # noqa: PLC0415
        load_secrets_from_manager()
        # Reload settings so the freshly injected env vars are picked up
        from app.config import get_settings  # noqa: PLC0415
        get_settings.cache_clear()
    except Exception as _sm_exc:
        logger.warning("secret_manager_startup_error", error=str(_sm_exc))

    logger.info(
        "starting_application",
        name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )
    # Sync DB tables in development if reachable
    if settings.app_env == "development":
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_synced")
        except Exception as e:
            logger.warning("database_sync_deferred", reason=str(e))

    yield

    try:
        await engine.dispose()
    except Exception:
        pass
    logger.info("application_shutdown")


def create_application() -> FastAPI:
    """Factory that creates and configures the FastAPI app."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="SupportPilot AI — Intelligent Customer Support Automation Platform",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS Middleware ────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Custom Middleware ───────────────────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # ── Exception Handlers ─────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────
    app.include_router(api_router, prefix="/api")

    # ── Root & Health Check Endpoints ──────────────────────
    @app.get("/", tags=["Health"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs" if not settings.is_production else None,
        }

    @app.get("/health", tags=["Health"], summary="Application health check")
    async def health() -> dict:
        return {
            "status": "healthy",
            "version": settings.app_version,
            "env": settings.app_env,
            "service": "supportpilot-backend",
        }

    return app


app = create_application()
