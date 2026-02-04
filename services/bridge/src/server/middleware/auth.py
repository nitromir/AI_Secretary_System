"""Authentication middleware."""

import base64
import logging
import secrets
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...config import get_settings


logger = logging.getLogger("cli_bridge.auth")


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Optional API key authentication middleware.

    If BRIDGE_API_KEY is set in config:
    - API endpoints require: Authorization: Bearer <api_key>
    - Dashboard/static require: HTTP Basic Auth (any username, api_key as password)

    If BRIDGE_API_KEY is not set, authentication is disabled.
    """

    # Endpoints that never require authentication
    PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}

    # Endpoints that use HTTP Basic Auth (browser-friendly)
    BASIC_AUTH_PATHS = {"/dashboard"}
    BASIC_AUTH_PREFIXES = ("/static/",)

    def _check_basic_auth(self, request: Request, api_key: str) -> bool:
        """Validate HTTP Basic Auth credentials."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Basic "):
            return False

        try:
            # Decode base64 credentials
            encoded = auth_header[6:]
            decoded = base64.b64decode(encoded).decode("utf-8")
            # Format is "username:password" - we only check password
            if ":" in decoded:
                _, password = decoded.split(":", 1)
                return secrets.compare_digest(password, api_key)
        except Exception:
            pass
        return False

    def _basic_auth_response(self) -> Response:
        """Return 401 response requesting Basic Auth."""
        return Response(
            content="Authentication required",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="CLI-OpenAI Bridge"'},
        )

    def _is_basic_auth_path(self, path: str) -> bool:
        """Check if path requires Basic Auth."""
        if path in self.BASIC_AUTH_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in self.BASIC_AUTH_PREFIXES)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        path = request.url.path

        # Skip auth if no API key configured
        if not settings.api_key:
            return await call_next(request)

        # Skip auth for public paths
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Use Basic Auth for dashboard and static files
        if self._is_basic_auth_path(path):
            if not self._check_basic_auth(request, settings.api_key):
                return self._basic_auth_response()
            return await call_next(request)

        # Bearer token auth for API endpoints
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"Missing Authorization header for {path}")
            return Response(
                content='{"error": {"message": "Missing Authorization header", "type": "authentication_error"}}',
                status_code=401,
                media_type="application/json",
            )

        # Parse Bearer token
        if not auth_header.startswith("Bearer "):
            logger.warning(f"Invalid Authorization format for {path}")
            return Response(
                content='{"error": {"message": "Invalid Authorization format. Use: Bearer <api_key>", "type": "authentication_error"}}',
                status_code=401,
                media_type="application/json",
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token (constant-time comparison to prevent timing attacks)
        if not secrets.compare_digest(token, settings.api_key):
            logger.warning(f"Invalid API key for {path}")
            return Response(
                content='{"error": {"message": "Invalid API key", "type": "authentication_error"}}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
