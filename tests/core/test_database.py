"""Tests for the database module (session factory + UnitOfWork)."""

import pytest
from unittest.mock import MagicMock, patch

from src.core.database import (
    create_session_factory,
    create_engine_from_settings,
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
