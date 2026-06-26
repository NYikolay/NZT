"""Database session factory and Unit of Work pattern."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
    create_async_engine,
)

from src.core.config import settings


def create_session_factory(
    engine: AsyncEngine | None = None,
    **kwargs: Any,
) -> async_sessionmaker[AsyncSession]:
    """Create an async session maker connected to the given engine.

    If no engine is provided, creates one from settings.
    """
    if engine is None:
        engine = create_async_engine(
            url=str(settings.db.SQLALCHEMY_DATABASE_URI),
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        **kwargs,
    )


class UnitOfWork:
    """Unit of Work pattern — wraps a session and manages transaction lifecycle.

    Usage:
        async with UnitOfWork(session_factory) as uow:
            user = await uow.session.get(User, user_id)
            user.name = "new name"
            await uow.commit()   # explicit commit
    """

    __slots__ = ("_session_factory", "session", "_session_context")

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ):
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self._session_context: AsyncIterator[AsyncSession] | None = None

    async def __aenter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self._session_context = self.session.begin()
        await self._session_context.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        if self._session_context is not None:
            # Rollback on error, otherwise the caller decides
            if exc_type is not None:
                await self._session_context.__aexit__(exc_type, exc_val, exc_tb)
            else:
                # Don't auto-commit — caller must call commit() explicitly
                await self._session_context.__aexit__(None, None, None)

        if self.session is not None:
            await self.session.close()
            self.session = None

    async def commit(self) -> None:
        """Explicitly commit the transaction."""
        if self.session is not None:
            await self.session.commit()

    async def rollback(self) -> None:
        """Explicitly rollback the transaction."""
        if self.session is not None:
            await self.session.rollback()
