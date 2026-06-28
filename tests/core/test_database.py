"""Tests for the database module (session factory + UnitOfWork)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.database import (
    create_session_factory,
    create_engine_from_settings,
    UnitOfWork,
)


class TestCreateSessionFactory:
    def test_should_create_factory_when_engine_provided(self):
        """Should create a session factory bound to the provided engine."""
        mock_engine = MagicMock()
        factory = create_session_factory(engine=mock_engine)
        assert factory is not None
        assert callable(factory)

    def test_should_require_engine_parameter(self):
        """Should raise TypeError when engine is not provided."""
        with pytest.raises(TypeError, match="engine"):
            create_session_factory()


class TestCreateEngineFromSettings:
    def test_should_create_engine_from_settings(self):
        """Should create an engine using settings values."""
        with patch("src.core.database.create_async_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            engine = create_engine_from_settings()

            mock_create_engine.assert_called_once()
            assert engine is mock_engine

    def test_should_pass_pool_config_from_settings(self):
        """Should forward pool_size, max_overflow, and pool_recycle from settings."""
        with patch("src.core.database.create_async_engine") as mock_create_engine:
            mock_create_engine.return_value = MagicMock()
            with patch("src.core.database.settings") as mock_settings:
                mock_settings.db.SQLALCHEMY_DATABASE_URI = (
                    "postgresql+asyncpg://u:p@h:5432/db"
                )
                mock_settings.db.ECHO = False
                mock_settings.db.POOL_SIZE = 5
                mock_settings.db.MAX_OVERFLOW = 10
                mock_settings.db.POOL_RECYCLE = 1800

                create_engine_from_settings()

                call_kwargs = mock_create_engine.call_args[1]
                assert call_kwargs["pool_size"] == 5
                assert call_kwargs["max_overflow"] == 10
                assert call_kwargs["pool_recycle"] == 1800
                assert call_kwargs["pool_pre_ping"] is True
                assert call_kwargs["echo"] is False


class TestUnitOfWork:
    """Tests for the UnitOfWork context manager."""

    @pytest.fixture
    def mock_uow_session(self):
        """Create a mock session that behaves like an async SQLAlchemy session."""
        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_session.name = "mock_session"
        mock_factory.return_value = mock_session
        return mock_factory, mock_session

    @pytest.mark.asyncio
    async def test_should_enter_and_exit_cleanly(self, mock_uow_session):
        """UnitOfWork should enter and exit cleanly without error."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            assert uow.session is not None

        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_commit_on_explicit_call(self, mock_uow_session):
        """UnitOfWork.commit() should delegate to session.commit()."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            await uow.commit()

        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_rollback_on_explicit_call(self, mock_uow_session):
        """UnitOfWork.rollback() should delegate to session.rollback()."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            await uow.rollback()

        mock_session.rollback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_rollback_on_exception(self, mock_uow_session):
        """UnitOfWork should rollback the transaction on exception."""
        mock_factory, mock_session = mock_uow_session

        with pytest.raises(ValueError, match="test error"):
            async with UnitOfWork(mock_factory):
                raise ValueError("test error")

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_not_rollback_on_clean_exit(self, mock_uow_session):
        """UnitOfWork should NOT rollback when exiting without exception."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory):
            pass

        mock_session.rollback.assert_not_awaited()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_close_session_even_after_rollback(self, mock_uow_session):
        """Session should be closed even when rollback is called explicitly."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            await uow.rollback()

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_set_session_to_none_on_exit(self, mock_uow_session):
        """Session should be set to None after exiting the context manager."""
        mock_factory, mock_session = mock_uow_session

        async with UnitOfWork(mock_factory) as uow:
            assert uow.session is not None

        assert uow.session is None
