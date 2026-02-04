"""Request/response logging middleware."""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger("cli_bridge.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Log request
        start_time = time.time()

        # Get request body for POST requests (chat completions)
        body_summary = ""
        if request.method == "POST" and "/chat/completions" in request.url.path:
            try:
                body = await request.body()
                # Store for later use
                request.state.body = body
                # Truncate for logging
                body_str = body.decode()[:200]
                body_summary = f" | body: {body_str}..."
            except Exception:
                pass

        logger.info(f"[{request_id}] → {request.method} {request.url.path}{body_summary}")

        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Log response
            logger.info(f"[{request_id}] ← {response.status_code} | {duration:.3f}s")

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{request_id}] ✗ Error: {e!s} | {duration:.3f}s")
            raise
