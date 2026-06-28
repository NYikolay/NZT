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


class UnitOfWork:
    """Unit of Work pattern — wraps a session and manages transaction lifecycle.

    Uses SQLAlchemy 2.0 implicit transaction model: the session starts a
    transaction on first SQL operation. No explicit ``session.begin()`` is
    needed — this avoids nested SAVEPOINT transactions.

    Usage:
        async with UnitOfWork(session_factory) as uow:
            user = await uow.session.get(User, user_id)
            user.name = "new name"
            await uow.commit()   # explicit commit

    On exception within the context, the transaction is rolled back
    automatically. The session is always closed on exit.
    """

    __slots__ = ("_session_factory", "session")

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Rollback on exception, close session always.

        Does NOT auto-commit — the caller must call ``commit()`` explicitly.
        Returning None (not truthy) ensures exceptions propagate.
        """
        if self.session is not None:
            if exc_type is not None:
                await self.session.rollback()
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        """Explicitly commit the transaction."""
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        """Explicitly rollback the transaction.

        Note: This does NOT close the session. The context manager will
        close it on exit. If you need to abort immediately, prefer
        raising an exception to trigger automatic rollback + close.
        """
        if self.session is not None:
            await self.session.rollback()
