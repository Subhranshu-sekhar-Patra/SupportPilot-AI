"""
Pytest configuration for SupportPilot AI Backend
Configures NullPool to prevent asyncpg cross-event-loop issues on Windows.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def override_db():
    """
    Use NullPool so each test creates clean asyncpg connections
    bound to the current test event loop, preventing Windows proactor errors.
    """
    test_engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
        echo=False,
    )
    test_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _test_get_db():
        async with test_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _test_get_db

    from app.core.middleware import reset_rate_limiters
    reset_rate_limiters()

    yield

    reset_rate_limiters()
    app.dependency_overrides.clear()
    await test_engine.dispose()
