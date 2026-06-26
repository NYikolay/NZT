"""Tests for the database module (session factory + UnitOfWork)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.database import create_session_factory, UnitOfWork


class TestCreateSessionFactory:
    def test_create_session_factory_without_engine(self):
        """Should create a session factory with a new engine when no engine provided."""
        with patch("src.core.database.create_async_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            factory = create_session_factory()

            mock_create_engine.assert_called_once()
            assert factory is not None
            # The factory should be callable
            assert callable(factory)

    def test_create_session_factory_with_engine(self):
        """Should use the provided engine."""
        mock_engine = MagicMock()
        with patch("src.core.database.create_async_engine") as mock_create_engine:
            factory = create_session_factory(engine=mock_engine)
            mock_create_engine.assert_not_called()
            assert callable(factory)


@pytest.fixture
def mock_async_context_manager():
    """Create a mock that acts as an async context manager."""
    mgr = MagicMock()
    mgr.__aenter__ = AsyncMock(return_value=None)
    mgr.__aexit__ = AsyncMock(return_value=None)
    return mgr


class TestUnitOfWork:
    """Tests for the UnitOfWork context manager."""

    @pytest.fixture
    def mock_uow_session(self, mock_async_context_manager):
        """Create a mock session that behaves like an async SQLAlchemy session."""
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.name = "mock_session"

        # begin() is a regular method that returns an async context manager
        mock_session.begin = MagicMock(return_value=mock_async_context_manager)

        mock_factory.return_value = mock_session
        return mock_factory, mock_session, mock_async_context_manager

    @pytest.mark.asyncio
    async def test_uow_enters_and_exits(self, mock_uow_session):
        """UnitOfWork should enter and exit cleanly without error."""
        mock_factory, mock_session, _ = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            assert uow.session is not None

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uow_commit(self, mock_uow_session):
        """UnitOfWork.commit() should delegate to session.commit()."""
        mock_factory, mock_session, _ = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            await uow.commit()

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uow_rollback(self, mock_uow_session):
        """UnitOfWork.rollback() should delegate to session.rollback()."""
        mock_factory, mock_session, _ = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            await uow.rollback()

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uow_rollback_on_exception(self, mock_uow_session):
        """UnitOfWork should rollback the transaction on exception."""
        mock_factory, mock_session, mock_begin = mock_uow_session

        with pytest.raises(ValueError, match="test error"):
            async with UnitOfWork(mock_factory):
                raise ValueError("test error")

        mock_begin.__aexit__.assert_awaited_once()
        mock_session.close.assert_awaited_once()
