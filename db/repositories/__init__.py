"""
Repository pattern implementations for database access.

Each repository handles CRUD operations for a specific domain entity,
with optional Redis caching for frequently accessed data.
"""

from db.repositories.base import BaseRepository
from db.repositories.chat import ChatRepository
from db.repositories.faq import FAQRepository
from db.repositories.preset import PresetRepository
from db.repositories.config import ConfigRepository
from db.repositories.telegram import TelegramRepository
from db.repositories.audit import AuditRepository

__all__ = [
    "BaseRepository",
    "ChatRepository",
    "FAQRepository",
    "PresetRepository",
    "ConfigRepository",
    "TelegramRepository",
    "AuditRepository",
]
