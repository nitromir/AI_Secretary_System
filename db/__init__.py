"""
Database package for AI Secretary System.

Provides:
- SQLite for persistent storage (chat sessions, FAQ, presets, configs)
- Redis for caching and realtime data (sessions, metrics, rate limiting)
"""

from db.database import (
    get_async_session,
    init_db,
    close_db,
    get_db_status,
    AsyncSessionLocal,
)
from db.redis_client import (
    get_redis,
    close_redis,
    redis_client,
)
from db.models import (
    Base,
    ChatSession,
    ChatMessage,
    FAQEntry,
    TTSPreset,
    SystemConfig,
    TelegramSession,
    AuditLog,
)

__all__ = [
    # Database
    "get_async_session",
    "init_db",
    "close_db",
    "get_db_status",
    "AsyncSessionLocal",
    # Redis
    "get_redis",
    "close_redis",
    "redis_client",
    # Models
    "Base",
    "ChatSession",
    "ChatMessage",
    "FAQEntry",
    "TTSPreset",
    "SystemConfig",
    "TelegramSession",
    "AuditLog",
]
