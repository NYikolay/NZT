"""Tests for the API exception handlers and error classes."""

import pytest
from httpx import AsyncClient

from src.api.exceptions import (
    build_error_response,
    AccessDeniedError,
    AuthenticationError,
    RateLimitExceededError,
    UpstreamServiceError,
    UpstreamTimeoutError,
    InternalError,
    ValidationError,
)
from src.domain.exceptions import BaseAppError


class TestBuildErrorResponse:
    def test_build_error_response_minimal(self):
        """build_error_response should produce a minimal error body."""
        exc = BaseAppError(message="test", error_code="TEST")
        body = build_error_response(exc)
        assert body["error"] is True
        assert body["code"] == "TEST"
        assert body["message"] == "test"

    def test_build_error_response_with_error_id(self):
        """build_error_response should include error_id if provided."""
        exc = BaseAppError(message="test", error_code="TEST")
        body = build_error_response(exc, error_id="abc123")
        assert body["error_id"] == "abc123"

    def test_build_error_response_with_details(self):
        """build_error_response should include details if present."""
        exc = BaseAppError(
            message="test",
            error_code="TEST",
            details={"field": "name", "reason": "required"},
        )
        body = build_error_response(exc)
        assert body["details"] == {"field": "name", "reason": "required"}


class TestAPICustomErrors:
    def test_access_denied_error(self):
        exc = AccessDeniedError()
        assert exc.status_code == 403
        assert exc.error_code == "ACCESS_DENIED"

    def test_authentication_error(self):
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "UNAUTHORIZED"

    def test_rate_limit_exceeded_error(self):
        exc = RateLimitExceededError(retry_after=30)
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.details["retry_after"] == 30

    def test_upstream_service_error(self):
        exc = UpstreamServiceError(service="OpenAI", detail="timeout")
        assert exc.status_code == 502
        assert "OpenAI" in exc.message

    def test_upstream_timeout_error(self):
        exc = UpstreamTimeoutError(service="OpenAI")
        assert exc.status_code == 504
        assert "OpenAI" in exc.message

    def test_internal_error(self):
        exc = InternalError()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"

    def test_validation_error(self):
        exc = ValidationError(details=[{"field": "name", "message": "required"}])
        assert exc.status_code == 422
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details == [{"field": "name", "message": "required"}]


@pytest.mark.asyncio
async def test_health_does_not_return_500(client: AsyncClient):
    """The health endpoint should work and not crash."""
    response = await client.get("/health")
    assert response.status_code == 200
