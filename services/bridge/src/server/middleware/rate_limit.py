"""Rate limiting middleware."""

import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...config import get_settings


logger = logging.getLogger("cli_bridge.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.

    Limits requests per API key (or IP if no auth).
    Returns 429 Too Many Requests when limit exceeded.

    Configuration via environment:
    - RATE_LIMIT_ENABLED: Enable/disable rate limiting
    - RATE_LIMIT_REQUESTS: Max requests per window (default: 60)
    - RATE_LIMIT_WINDOW: Time window in seconds (default: 60)
    """

    # Endpoints exempt from rate limiting
    EXEMPT_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app):
        super().__init__(app)
        self.settings = get_settings()
        # Track requests: {client_id: {"tokens": float, "last_update": float}}
        self._buckets: dict[str, dict] = defaultdict(
            lambda: {"tokens": self.settings.rate_limit_requests, "last_update": time.time()}
        )

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from API key or IP."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Use API key as identifier
            return f"key:{auth_header[7:20]}..."  # Truncated for privacy
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        return f"ip:{client.host if client else 'unknown'}"

    def _check_rate_limit(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if request is allowed using token bucket algorithm.

        Returns:
            Tuple of (allowed: bool, info: dict with remaining/reset info)
        """
        now = time.time()
        bucket = self._buckets[client_id]

        # Refill tokens based on time elapsed
        elapsed = now - bucket["last_update"]
        refill_rate = self.settings.rate_limit_requests / self.settings.rate_limit_window
        bucket["tokens"] = min(
            self.settings.rate_limit_requests, bucket["tokens"] + (elapsed * refill_rate)
        )
        bucket["last_update"] = now

        # Check if we have tokens available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True, {
                "remaining": int(bucket["tokens"]),
                "limit": self.settings.rate_limit_requests,
                "reset": int(now + self.settings.rate_limit_window),
            }

        # Rate limited
        retry_after = (1 - bucket["tokens"]) / refill_rate
        return False, {
            "remaining": 0,
            "limit": self.settings.rate_limit_requests,
            "reset": int(now + retry_after),
            "retry_after": int(retry_after) + 1,
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()

        # Skip if rate limiting disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        client_id = self._get_client_id(request)
        allowed, info = self._check_rate_limit(client_id)

        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id}")
            return Response(
                content='{"error": {"message": "Rate limit exceeded. Please slow down.", "type": "rate_limit_error"}}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"]),
                    "Retry-After": str(info["retry_after"]),
                },
            )

        # Process request and add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])

        return response

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "active_clients": len(self._buckets),
            "config": {
                "requests_per_window": self.settings.rate_limit_requests,
                "window_seconds": self.settings.rate_limit_window,
            },
        }


# Singleton instance
_rate_limiter: RateLimitMiddleware | None = None


def get_rate_limiter() -> RateLimitMiddleware | None:
    """Get the rate limiter instance (if registered)."""
    return _rate_limiter


def set_rate_limiter(limiter: RateLimitMiddleware) -> None:
    """Set the rate limiter instance."""
    global _rate_limiter
    _rate_limiter = limiter
