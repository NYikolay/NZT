"""Database session factory and Unit of Work pattern.

The UnitOfWork manages transaction lifecycle using SQLAlchemy 2.0's
implicit transaction model (autocommit=False). The session begins a
transaction on first use; commit/rollback are explicit.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
    create_async_engine,
)

from src.core.config import settings

logger = structlog.get_logger()


def create_session_factory(
    engine: AsyncEngine,
    **kwargs: Any,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session maker bound to the given engine.

    Args:
        engine: An AsyncEngine instance (typically from app.state.engine).
        **kwargs: Additional keyword arguments forwarded to async_sessionmaker.

    Returns:
        An async_sessionmaker bound to the provided engine.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,  # Keep objects accessible after commit — required for UoW pattern
        **kwargs,
    )


def create_engine_from_settings() -> AsyncEngine:
    """Create an AsyncEngine from application settings.

    All pool and connection parameters are configurable via environment
    variables through DataBaseSettings.
    """
    return create_async_engine(
        url=str(settings.db.SQLALCHEMY_DATABASE_URI),
        echo=settings.db.ECHO,
        pool_size=settings.db.POOL_SIZE,
        max_overflow=settings.db.MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=settings.db.POOL_RECYCLE,
    )
