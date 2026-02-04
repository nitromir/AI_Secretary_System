"""Request queue for rate limiting and scheduling."""

import asyncio
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Coroutine


logger = logging.getLogger(__name__)


@dataclass
class QueuedRequest:
    """A request waiting in the queue."""

    id: str
    provider: str
    created_at: float = field(default_factory=time.time)
    future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


@dataclass
class QueueStats:
    """Statistics for a provider queue."""

    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    total_wait_time: float = 0.0
    total_process_time: float = 0.0
    # Streaming stats
    streaming_active: int = 0
    streaming_completed: int = 0
    streaming_failed: int = 0


class RequestQueue:
    """
    Manages request queuing and scheduling per provider.

    Features:
    - Per-provider queues to prevent one slow provider blocking others
    - Configurable concurrency limits per provider
    - FIFO ordering within each queue
    - Timeout handling
    - Queue statistics and monitoring

    Usage:
        queue = RequestQueue(max_concurrent={"claude": 2, "gemini": 3})
        result = await queue.execute("claude", my_async_function, arg1, arg2)
    """

    def __init__(
        self,
        max_concurrent: dict[str, int] | None = None,
        default_max_concurrent: int = 2,
        max_queue_size: int = 100,
        request_timeout: float = 300.0,  # 5 minutes
    ):
        """
        Initialize the request queue.

        Args:
            max_concurrent: Per-provider concurrency limits
            default_max_concurrent: Default limit for unlisted providers
            max_queue_size: Maximum pending requests per provider
            request_timeout: Maximum time a request can wait + execute
        """
        self.max_concurrent = max_concurrent or {}
        self.default_max_concurrent = default_max_concurrent
        self.max_queue_size = max_queue_size
        self.request_timeout = request_timeout

        # Per-provider state
        self._queues: dict[str, deque[QueuedRequest]] = {}
        self._active: dict[str, int] = {}
        self._stats: dict[str, QueueStats] = {}
        self._locks: dict[str, asyncio.Lock] = {}

        # Semaphores for streaming requests (shared concurrency pool)
        self._semaphores: dict[str, asyncio.Semaphore] = {}

        # Global lock for initialization
        self._init_lock = asyncio.Lock()

        # Shutdown flag
        self._shutting_down = False

    def _get_max_concurrent(self, provider: str) -> int:
        """Get concurrency limit for a provider."""
        return self.max_concurrent.get(provider, self.default_max_concurrent)

    async def _ensure_provider(self, provider: str) -> None:
        """Ensure provider queues are initialized."""
        if provider not in self._queues:
            async with self._init_lock:
                if provider not in self._queues:
                    self._queues[provider] = deque()
                    self._active[provider] = 0
                    self._stats[provider] = QueueStats()
                    self._locks[provider] = asyncio.Lock()
                    # Create semaphore for streaming concurrency control
                    max_concurrent = self._get_max_concurrent(provider)
                    self._semaphores[provider] = asyncio.Semaphore(max_concurrent)

    async def execute(
        self,
        provider: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute a function through the queue.

        Args:
            provider: Provider name for queue selection
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Result from the function

        Raises:
            asyncio.QueueFull: If queue is at capacity
            asyncio.TimeoutError: If request times out
        """
        await self._ensure_provider(provider)

        request_id = f"{provider}-{int(time.time() * 1000)}"
        request = QueuedRequest(id=request_id, provider=provider)

        # Check queue capacity
        if len(self._queues[provider]) >= self.max_queue_size:
            logger.warning(f"Queue full for provider {provider}")
            raise asyncio.QueueFull(f"Request queue full for {provider}")

        # Add to queue
        self._queues[provider].append(request)
        self._stats[provider].pending += 1
        logger.debug(f"Queued request {request_id}, position: {len(self._queues[provider])}")

        # Start processor if needed
        asyncio.create_task(self._process_queue(provider, func, args, kwargs))

        # Wait for result with timeout
        try:
            result = await asyncio.wait_for(request.future, timeout=self.request_timeout)
            return result
        except asyncio.TimeoutError:
            self._stats[provider].failed += 1
            logger.error(f"Request {request_id} timed out")
            raise

    async def _process_queue(
        self,
        provider: str,
        func: Callable[..., Coroutine[Any, Any, Any]],
        args: tuple,
        kwargs: dict,
    ) -> None:
        """Process requests from the queue."""
        async with self._locks[provider]:
            max_concurrent = self._get_max_concurrent(provider)

            while self._queues[provider] and self._active[provider] < max_concurrent:
                request = self._queues[provider].popleft()
                self._stats[provider].pending -= 1
                self._active[provider] += 1
                self._stats[provider].processing += 1

                # Track wait time
                wait_time = time.time() - request.created_at
                self._stats[provider].total_wait_time += wait_time

                # Execute in background
                asyncio.create_task(self._execute_request(provider, request, func, args, kwargs))

    async def _execute_request(
        self,
        provider: str,
        request: QueuedRequest,
        func: Callable[..., Coroutine[Any, Any, Any]],
        args: tuple,
        kwargs: dict,
    ) -> None:
        """Execute a single request and handle completion."""
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            request.future.set_result(result)
            self._stats[provider].completed += 1
            logger.debug(f"Request {request.id} completed")
        except Exception as e:
            request.future.set_exception(e)
            self._stats[provider].failed += 1
            logger.error(f"Request {request.id} failed: {e}")
        finally:
            # Track process time
            process_time = time.time() - start_time
            self._stats[provider].total_process_time += process_time

            # Release slot
            self._active[provider] -= 1
            self._stats[provider].processing -= 1

            # Process more if waiting
            if self._queues[provider]:
                asyncio.create_task(self._process_queue(provider, func, args, kwargs))

    @asynccontextmanager
    async def acquire_stream_slot(self, provider: str) -> AsyncIterator[None]:
        """
        Acquire a slot for streaming request.

        Use as async context manager:
            async with queue.acquire_stream_slot("claude"):
                async for chunk in stream_generator():
                    yield chunk

        Args:
            provider: Provider name for concurrency control

        Raises:
            asyncio.QueueFull: If at capacity and can't acquire slot immediately
        """
        await self._ensure_provider(provider)

        if self._shutting_down:
            raise asyncio.QueueFull("Server is shutting down")

        semaphore = self._semaphores[provider]
        stats = self._stats[provider]

        # Try to acquire with timeout to prevent indefinite blocking
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=self.request_timeout)
        except asyncio.TimeoutError:
            stats.streaming_failed += 1
            logger.warning(f"Streaming slot acquisition timed out for {provider}")
            raise asyncio.QueueFull(f"Streaming queue timeout for {provider}")

        stats.streaming_active += 1
        logger.debug(f"Acquired streaming slot for {provider}, active: {stats.streaming_active}")

        try:
            yield
            stats.streaming_completed += 1
        except Exception:
            stats.streaming_failed += 1
            raise
        finally:
            stats.streaming_active -= 1
            semaphore.release()
            logger.debug(
                f"Released streaming slot for {provider}, active: {stats.streaming_active}"
            )

    def get_stats(self, provider: str | None = None) -> dict[str, Any]:
        """Get queue statistics."""
        if provider:
            stats = self._stats.get(provider, QueueStats())
            total_requests = stats.completed + stats.failed
            return {
                "provider": provider,
                "pending": stats.pending,
                "processing": stats.processing,
                "completed": stats.completed,
                "failed": stats.failed,
                "avg_wait_time": stats.total_wait_time / total_requests if total_requests else 0,
                "avg_process_time": stats.total_process_time / total_requests
                if total_requests
                else 0,
                "max_concurrent": self._get_max_concurrent(provider),
                # Streaming stats
                "streaming": {
                    "active": stats.streaming_active,
                    "completed": stats.streaming_completed,
                    "failed": stats.streaming_failed,
                },
            }

        # All providers
        all_stats = {}
        for prov in self._stats:
            all_stats[prov] = self.get_stats(prov)

        return {
            "providers": all_stats,
            "total_pending": sum(s.pending for s in self._stats.values()),
            "total_processing": sum(s.processing for s in self._stats.values()),
            "total_streaming_active": sum(s.streaming_active for s in self._stats.values()),
            "max_queue_size": self.max_queue_size,
            "request_timeout": self.request_timeout,
            "shutting_down": self._shutting_down,
        }

    def get_position(self, provider: str) -> int:
        """Get current queue length for a provider."""
        return len(self._queues.get(provider, []))

    async def shutdown(self, timeout: float = 30.0) -> bool:
        """
        Gracefully shutdown the queue.

        Waits for active requests to complete up to timeout.

        Args:
            timeout: Maximum seconds to wait for requests to complete

        Returns:
            True if all requests completed, False if timed out
        """
        self._shutting_down = True
        logger.info("Queue shutdown initiated, waiting for active requests...")

        start = time.time()
        while time.time() - start < timeout:
            # Check if any requests are still active
            total_active = sum(s.processing + s.streaming_active for s in self._stats.values())
            total_pending = sum(s.pending for s in self._stats.values())

            if total_active == 0 and total_pending == 0:
                logger.info("Queue shutdown complete - all requests finished")
                return True

            logger.debug(f"Shutdown waiting: {total_active} active, {total_pending} pending")
            await asyncio.sleep(0.5)

        # Timed out
        total_active = sum(s.processing + s.streaming_active for s in self._stats.values())
        total_pending = sum(s.pending for s in self._stats.values())
        logger.warning(
            f"Queue shutdown timed out after {timeout}s - "
            f"{total_active} active, {total_pending} pending requests remaining"
        )
        return False


# Global queue instance
_request_queue: RequestQueue | None = None


def get_request_queue() -> RequestQueue:
    """Get or create global request queue with settings from config."""
    global _request_queue
    if _request_queue is None:
        from ..config import get_settings

        settings = get_settings()

        _request_queue = RequestQueue(
            max_concurrent={
                "claude": settings.queue_claude_concurrent,
                "gemini": settings.queue_gemini_concurrent,
                "gpt": settings.queue_gpt_concurrent,
            },
            default_max_concurrent=settings.queue_default_concurrent,
            max_queue_size=settings.queue_max_size,
            request_timeout=float(settings.queue_timeout),
        )
    return _request_queue
