"""Shared fixtures for all tests."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def app():
    """Create a FastAPI app instance with a mock engine (in-memory testing)."""
    mock_engine = MagicMock()
    application = create_app(engine=mock_engine)
    return application


@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client against the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_session():
    """Return a mock AsyncSession for service-layer testing."""
    return AsyncMock()
