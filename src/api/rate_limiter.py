"""Rate limiter middleware for FastAPI.

Uses an in-memory sliding-window counter. For production, swap with Redis.
"""

import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.api.exceptions import RateLimitExceededError


class InMemoryRateLimiter(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    Allows up to `max_requests` requests per `window_seconds` per client IP.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60,
        exclude_paths: set[str] | None = None,
    ):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.exclude_paths = exclude_paths or {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        # {client_ip: [timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Sliding window: remove timestamps outside the window
        window_start = now - self.window_seconds
        timestamps = self._requests[client_ip]
        self._requests[client_ip] = [t for t in timestamps if t > window_start]

        # Check limit
        if len(self._requests[client_ip]) >= self.max_requests:
            raise RateLimitExceededError(
                retry_after=int(
                    self._requests[client_ip][0] + self.window_seconds - now
                )
            )

        # Record the request
        self._requests[client_ip].append(now)

        response = await call_next(request)
        return response
