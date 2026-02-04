"""Response caching for identical requests."""

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from ..config import get_settings


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with value and metadata."""

    value: dict[str, Any]
    created_at: float
    ttl: int
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return time.time() - self.created_at > self.ttl


class ResponseCache:
    """LRU cache for response caching with TTL support."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = threading.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _make_key(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> str:
        """
        Create a cache key from request parameters.

        Note: Streaming requests are not cached.
        """
        # Include relevant parameters in the key
        key_data = {
            "messages": messages,
            "model": model,
            "temperature": kwargs.get("temperature"),
            "max_tokens": kwargs.get("max_tokens"),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        messages: list[dict[str, Any]],
        model: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """
        Get cached response if available.

        Returns:
            Cached response or None if not found/expired
        """
        settings = get_settings()
        if not settings.cache_enabled:
            return None

        key = self._make_key(messages, model, **kwargs)

        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            entry = self._cache[key]

            if entry.is_expired:
                del self._cache[key]
                self._stats["misses"] += 1
                logger.debug(f"Cache entry expired: {key[:8]}...")
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {key[:8]}... (hits: {entry.hits})")

            return entry.value

    def set(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: dict[str, Any],
        ttl: int | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Cache a response.

        Args:
            messages: Request messages
            model: Model name
            response: Response to cache
            ttl: Time to live in seconds (default from settings)
            **kwargs: Additional request parameters for key
        """
        settings = get_settings()
        if not settings.cache_enabled:
            return

        key = self._make_key(messages, model, **kwargs)
        ttl = ttl or settings.cache_ttl

        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
                logger.debug(f"Cache eviction: {oldest_key[:8]}...")

            self._cache[key] = CacheEntry(
                value=response,
                created_at=time.time(),
                ttl=ttl,
            )
            logger.debug(f"Cache set: {key[:8]}... (ttl: {ttl}s)")

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

            return {
                "enabled": get_settings().cache_enabled,
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_percent": hit_rate,
                "evictions": self._stats["evictions"],
            }


# Global cache instance
_cache: ResponseCache | None = None


def get_cache() -> ResponseCache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = ResponseCache(
            max_size=settings.cache_max_size,
            default_ttl=settings.cache_ttl,
        )
    return _cache
