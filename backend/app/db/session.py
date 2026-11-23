"""
SupportPilot AI — Async SQLAlchemy Database Session
Configured for PostgreSQL (asyncpg) with automatic fallback for local development.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

db_url = settings.database_url
engine_kwargs = {"echo": settings.app_env == "development"}

# Check if PostgreSQL async driver is present; if not on bare host, fallback to SQLite
if "postgresql" in db_url:
    try:
        import asyncpg  # noqa: F401
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20
    except ImportError:
        logger.warning(
            "asyncpg_not_found_falling_back_to_sqlite",
            original_url=db_url,
            fallback="sqlite+aiosqlite:///./supportpilot_dev.db",
        )
        db_url = "sqlite+aiosqlite:///./supportpilot_dev.db"
        engine_kwargs["connect_args"] = {"check_same_thread": False}
elif "sqlite" in db_url:
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Shared base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency yielding an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
