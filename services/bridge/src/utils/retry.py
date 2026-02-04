"""Retry logic for transient failures."""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

from ..config import get_settings


logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, message: str, last_error: Exception | None = None):
        super().__init__(message)
        self.last_error = last_error


# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (
    asyncio.TimeoutError,
    ConnectionError,
    OSError,
)


def is_retryable(error: Exception) -> bool:
    """Check if an error is retryable."""
    # Check direct instance
    if isinstance(error, RETRYABLE_EXCEPTIONS):
        return True

    # Check for specific error messages that indicate transient issues
    error_msg = str(error).lower()
    retryable_messages = [
        "connection reset",
        "connection refused",
        "temporary failure",
        "try again",
        "overloaded",
        "rate limit",
        "timeout",
    ]
    return any(msg in error_msg for msg in retryable_messages)


async def retry_async(
    func: Callable[..., T],
    *args: Any,
    max_attempts: int | None = None,
    delay: float | None = None,
    backoff: float | None = None,
    **kwargs: Any,
) -> T:
    """
    Retry an async function with exponential backoff.

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_attempts: Max retry attempts (default from settings)
        delay: Initial delay between retries (default from settings)
        backoff: Backoff multiplier (default from settings)
        **kwargs: Keyword arguments for func

    Returns:
        Result of the function

    Raises:
        RetryError: If all attempts fail
    """
    settings = get_settings()

    if not settings.retry_enabled:
        return await func(*args, **kwargs)

    max_attempts = max_attempts or settings.retry_max_attempts
    delay = delay or settings.retry_delay
    backoff = backoff or settings.retry_backoff

    last_error: Exception | None = None
    current_delay = delay

    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_error = e

            if not is_retryable(e):
                logger.debug(f"Non-retryable error: {e}")
                raise

            if attempt < max_attempts:
                logger.warning(
                    f"Attempt {attempt}/{max_attempts} failed: {e}. "
                    f"Retrying in {current_delay:.1f}s..."
                )
                await asyncio.sleep(current_delay)
                current_delay *= backoff
            else:
                logger.error(f"All {max_attempts} attempts failed")

    raise RetryError(
        f"All {max_attempts} retry attempts exhausted",
        last_error=last_error,
    )


def with_retry(
    max_attempts: int | None = None,
    delay: float | None = None,
    backoff: float | None = None,
):
    """
    Decorator to add retry logic to an async function.

    Usage:
        @with_retry(max_attempts=3)
        async def my_function():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_async(
                func,
                *args,
                max_attempts=max_attempts,
                delay=delay,
                backoff=backoff,
                **kwargs,
            )

        return wrapper

    return decorator
