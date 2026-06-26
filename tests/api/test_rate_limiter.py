"""Tests for the in-memory rate limiter middleware."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limiter_allows_normal_requests(client: AsyncClient):
    """A few requests within the limit should pass."""
    for _ in range(5):
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_excludes_health_path(client: AsyncClient):
    """Health endpoint should not be rate-limited."""
    for _ in range(200):
        response = await client.get("/health")
        assert response.status_code == 200
