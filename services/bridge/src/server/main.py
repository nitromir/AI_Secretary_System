"""FastAPI server entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..config import get_settings
from ..utils import (
    check_all_clis,
    get_cache,
    get_metrics,
    get_request_queue,
    get_session_manager,
    log_cli_status,
)
from .middleware import (
    AuthenticationMiddleware,
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    set_rate_limiter,
)
from .routes import chat_router, files_router, models_router


settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting CLI-OpenAI Bridge on {settings.host}:{settings.port}")

    # Health check CLIs on startup
    if settings.health_check_on_startup:
        logger.info("Checking CLI availability...")
        statuses = await check_all_clis(settings)
        log_cli_status(statuses)

        # Store statuses for health endpoint
        app.state.cli_statuses = statuses

    # Log authentication status
    if settings.api_key:
        logger.info("Authentication enabled (BRIDGE_API_KEY is set)")
    else:
        logger.info("Authentication disabled (no BRIDGE_API_KEY)")

    # Log cache status
    if settings.cache_enabled:
        logger.info(
            f"Response caching enabled (TTL: {settings.cache_ttl}s, max: {settings.cache_max_size})"
        )
    else:
        logger.info("Response caching disabled")

    # Log rate limit status
    if settings.rate_limit_enabled:
        logger.info(
            f"Rate limiting enabled ({settings.rate_limit_requests} requests per {settings.rate_limit_window}s)"
        )
    else:
        logger.info("Rate limiting disabled")

    # Log queue status
    if settings.queue_enabled:
        logger.info(
            f"Request queue enabled (max size: {settings.queue_max_size}, timeout: {settings.queue_timeout}s)"
        )
    else:
        logger.info("Request queue disabled")

    # Load persistent metrics from previous sessions
    if settings.metrics_enabled:
        metrics = get_metrics()
        if metrics.load_from_file():
            logger.info("Loaded metrics from previous session")

    # Start background session cleanup task
    session_manager = get_session_manager()
    cleanup_task = asyncio.create_task(_session_cleanup_loop(session_manager))
    app.state.cleanup_task = cleanup_task

    yield

    # Graceful shutdown
    logger.info("Shutting down CLI-OpenAI Bridge...")

    # Cancel session cleanup task
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Gracefully shutdown queue
    if settings.queue_enabled:
        request_queue = get_request_queue()
        await request_queue.shutdown(timeout=30.0)

    # Save metrics for next session
    if settings.metrics_enabled:
        metrics = get_metrics()
        if metrics.save_to_file():
            logger.info("Metrics saved for next session")

    logger.info("Shutdown complete")


async def _session_cleanup_loop(session_manager, interval: int = 300):
    """Background task to cleanup expired sessions every 5 minutes."""
    while True:
        try:
            await asyncio.sleep(interval)
            cleaned = session_manager.cleanup_expired()
            if cleaned > 0:
                logger.debug(f"Cleaned up {cleaned} expired sessions")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


app = FastAPI(
    title="CLI-OpenAI Bridge",
    description="Bridge CLI AI tools to OpenAI-compatible API",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware (order matters - first added = outermost)
# Authentication should be checked first
app.add_middleware(AuthenticationMiddleware)

# Rate limiting (after auth so we can use API key as identifier)
if settings.rate_limit_enabled:
    rate_limiter = RateLimitMiddleware(app)
    set_rate_limiter(rate_limiter)
    app.add_middleware(RateLimitMiddleware)

# Request logging
if settings.log_requests:
    app.add_middleware(RequestLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(files_router)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"

# Content type mapping for static files
CONTENT_TYPES = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".html": "text/html",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files (goes through auth middleware)."""
    file = STATIC_DIR / file_path
    if file.exists() and file.is_file():
        content_type = CONTENT_TYPES.get(file.suffix, "application/octet-stream")
        return FileResponse(file, media_type=content_type)
    return JSONResponse({"error": "File not found"}, status_code=404)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Serve the web dashboard."""
    dashboard_file = STATIC_DIR / "dashboard.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(), status_code=200)
    return HTMLResponse(content="Dashboard not found", status_code=404)


@app.get("/health")
async def health_check():
    """Health check endpoint with CLI status and queue stats."""
    cli_statuses = getattr(app.state, "cli_statuses", {})

    providers = {}
    all_healthy = True

    for name, status in cli_statuses.items():
        providers[name] = {
            "available": status.available,
            "path": status.path,
            "version": status.version,
            "error": status.error,
        }
        if not status.available:
            all_healthy = False

    # Get queue stats for health assessment
    queue_stats = None
    if settings.queue_enabled:
        request_queue = get_request_queue()
        queue_stats = request_queue.get_stats()
        # Consider degraded if queue is near capacity
        total_pending = queue_stats.get("total_pending", 0)
        if total_pending > settings.queue_max_size * 0.8:
            all_healthy = False

    # Get session stats
    session_manager = get_session_manager()
    session_stats = session_manager.get_stats()

    return {
        "status": "healthy" if all_healthy else "degraded",
        "version": "0.1.0",
        "providers": providers,
        "queue": queue_stats,
        "sessions": session_stats,
    }


@app.get("/metrics")
async def get_usage_metrics():
    """Get usage metrics."""
    if not settings.metrics_enabled:
        return {"error": "Metrics collection is disabled"}

    metrics = get_metrics()
    cache = get_cache()

    return {
        "requests": metrics.get_stats(),
        "cache": cache.get_stats(),
    }


@app.post("/metrics/reset")
async def reset_metrics():
    """Reset usage metrics."""
    if not settings.metrics_enabled:
        return {"error": "Metrics collection is disabled"}

    metrics = get_metrics()
    metrics.reset()
    return {"status": "ok", "message": "Metrics reset"}


@app.post("/cache/clear")
async def clear_cache():
    """Clear response cache."""
    cache = get_cache()
    cache.clear()
    return {"status": "ok", "message": "Cache cleared"}


@app.get("/queue")
async def get_queue_stats():
    """Get request queue statistics."""
    if not settings.queue_enabled:
        return {"enabled": False, "message": "Request queue is disabled"}

    from ..utils import get_request_queue

    queue = get_request_queue()
    stats = queue.get_stats()
    stats["enabled"] = True
    return stats


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CLI-OpenAI Bridge",
        "version": "0.1.0",
        "dashboard": "/dashboard",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "models": "/v1/models",
            "files": "/v1/files",
            "health": "/health",
            "metrics": "/metrics",
            "queue": "/queue",
            "dashboard": "/dashboard",
        },
        "features": {
            "authentication": bool(settings.api_key),
            "caching": settings.cache_enabled,
            "metrics": settings.metrics_enabled,
            "retry": settings.retry_enabled,
            "rate_limiting": settings.rate_limit_enabled,
        },
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": str(exc),
                "type": "server_error",
            }
        },
    )


def main():
    """Run the server."""
    import uvicorn

    uvicorn.run(
        "src.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
