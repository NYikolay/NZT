"""Tests for the health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """GET /health should return 200 with status 'healthy'."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_health_check_method_not_allowed(client: AsyncClient):
    """POST /health should return 405."""
    response = await client.post("/health")
    assert response.status_code == 405
