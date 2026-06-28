"""Tests for authentication and registration endpoints."""

from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# CurrentUser dependency tests (no DB mocking needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_current_user_returns_401_for_invalid_token(app):
    """Protected endpoint with invalid token should return 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/send_message",
            json={"message": "hello"},
            headers={"Authorization": "Bearer invalid_token_here"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_current_user_returns_validation_error_for_missing_token(app):
    """Protected endpoint with no token header should return 422 (FastAPI validation error)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/send_message",
            json={"message": "hello"},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Valid token tests (dependency overrides)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_returns_user_when_registered(app):
    """Protected endpoint should succeed when CurrentUser is overridden to return a user."""
    from src.api.dependencies import get_current_user_tg_provider

    mock_user = MagicMock()
    mock_user.id = "00000000-0000-0000-0000-000000000001"

    async def _mock_dependency():
        return mock_user

    app.dependency_overrides[get_current_user_tg_provider] = _mock_dependency

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat/send_message",
            json={"message": "hello"},
            headers={"Authorization": "Bearer valid_token"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Register endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_returns_422_for_empty_body(app):
    """POST /auth/register with no body should return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_returns_422_for_invalid_body(app):
    """POST /auth/register with missing telegram_profile fields should return 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={"telegram_profile": {"id": 12345}},  # missing required fields
        )

    assert response.status_code == 422
