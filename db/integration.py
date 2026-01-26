"""
Database integration helpers for orchestrator.

Provides backward-compatible wrapper classes that match the old API
while using the new database repositories internally.
"""

import time
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from db.database import AsyncSessionLocal, init_db, close_db, get_db_status
from db.redis_client import init_redis, close_redis, get_redis_status
from db.repositories import (
    ChatRepository,
    FAQRepository,
    PresetRepository,
    ConfigRepository,
    TelegramRepository,
    AuditRepository,
)

logger = logging.getLogger(__name__)


# ============== Database Manager ==============

class DatabaseManager:
    """
    Singleton manager for database operations.
    Provides async context managers for repository access.
    """
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Initialize database and Redis connections."""
        if self._initialized:
            return

        logger.info("🗄️ Initializing database...")
        await init_db()

        logger.info("🔴 Initializing Redis...")
        redis_ok = await init_redis()
        if not redis_ok:
            logger.warning("⚠️ Redis not available, caching disabled")

        self._initialized = True
        logger.info("✅ Database ready")

    async def shutdown(self):
        """Close all connections."""
        await close_db()
        await close_redis()
        self._initialized = False
        logger.info("🗄️ Database connections closed")

    async def get_status(self) -> dict:
        """Get database and Redis status for health checks."""
        db_status = await get_db_status()
        redis_status = await get_redis_status()
        return {
            "database": {
                "sqlite": db_status,
                "redis": redis_status,
            }
        }


# Global database manager
db_manager = DatabaseManager()


# ============== Chat Manager (Backward-Compatible) ==============

class AsyncChatManager:
    """
    Async-compatible ChatManager that uses database.
    Provides same API as the old synchronous ChatManager for easy migration.
    """

    def _generate_id(self) -> str:
        return f"chat_{int(time.time() * 1000)}"

    def _generate_message_id(self) -> str:
        ts = str(time.time())
        return f"msg_{int(time.time() * 1000)}_{hashlib.md5(ts.encode()).hexdigest()[:6]}"

    async def list_sessions(self) -> List[dict]:
        """List all sessions with summary info."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.list_sessions()

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get full session with messages."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.get_session(session_id)

    async def create_session(
        self,
        title: str = None,
        system_prompt: str = None,
    ) -> dict:
        """Create new session."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.create_session(title, system_prompt)

    async def update_session(
        self,
        session_id: str,
        title: str = None,
        system_prompt: str = None,
    ) -> Optional[dict]:
        """Update session title or system prompt."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.update_session(session_id, title, system_prompt)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.delete_session(session_id)

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Optional[dict]:
        """Add message to session."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.add_message(session_id, role, content)

    async def edit_message(
        self,
        session_id: str,
        message_id: str,
        content: str,
    ) -> Optional[dict]:
        """Edit message."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.edit_message(session_id, message_id, content)

    async def delete_message(
        self,
        session_id: str,
        message_id: str,
    ) -> bool:
        """Delete message and all subsequent messages."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.delete_message(session_id, message_id)

    async def get_messages_for_llm(
        self,
        session_id: str,
        system_prompt: str = None,
    ) -> List[dict]:
        """Get messages in LLM format."""
        async with AsyncSessionLocal() as session:
            repo = ChatRepository(session)
            return await repo.get_messages_for_llm(session_id, system_prompt)


# ============== FAQ Manager ==============

class AsyncFAQManager:
    """Async FAQ manager using database with caching."""

    async def get_all(self) -> Dict[str, str]:
        """Get all FAQ as question->answer dict."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.get_as_dict()

    async def get_all_entries(self) -> List[dict]:
        """Get all FAQ entries with full details."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.get_all_entries(enabled_only=False)

    async def find_answer(self, question: str) -> Optional[str]:
        """Find exact match answer for question."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.find_answer(question)

    async def add(self, question: str, answer: str) -> dict:
        """Add new FAQ entry."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.create_entry(question, answer)

    async def update(self, old_question: str, question: str, answer: str) -> Optional[dict]:
        """Update FAQ entry."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)

            # If question changed, need to find by old and delete + create
            if old_question != question:
                existing = await repo.get_by_question(old_question)
                if existing:
                    await repo.delete_by_question(old_question)
                return await repo.create_entry(question, answer)
            else:
                existing = await repo.get_by_question(question)
                if existing:
                    return await repo.update_entry(
                        existing["id"],
                        question=question,
                        answer=answer,
                    )
            return None

    async def delete(self, question: str) -> bool:
        """Delete FAQ entry."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.delete_by_question(question)

    async def search(self, query: str) -> List[dict]:
        """Search FAQ entries."""
        async with AsyncSessionLocal() as session:
            repo = FAQRepository(session)
            return await repo.search(query)


# ============== Preset Manager ==============

class AsyncPresetManager:
    """Async TTS preset manager using database."""

    async def get_all(self) -> Dict[str, dict]:
        """Get all presets."""
        async with AsyncSessionLocal() as session:
            repo = PresetRepository(session)
            return await repo.get_all_presets()

    async def get_custom(self) -> Dict[str, dict]:
        """Get only custom presets."""
        async with AsyncSessionLocal() as session:
            repo = PresetRepository(session)
            return await repo.get_custom_presets()

    async def create(self, name: str, params: dict) -> dict:
        """Create new preset."""
        async with AsyncSessionLocal() as session:
            repo = PresetRepository(session)
            return await repo.create_preset(name, params)

    async def update(self, name: str, params: dict) -> Optional[dict]:
        """Update preset."""
        async with AsyncSessionLocal() as session:
            repo = PresetRepository(session)
            return await repo.update_preset(name, params)

    async def delete(self, name: str) -> bool:
        """Delete preset."""
        async with AsyncSessionLocal() as session:
            repo = PresetRepository(session)
            return await repo.delete_preset(name)


# ============== Config Manager ==============

class AsyncConfigManager:
    """Async config manager using database."""

    async def get(self, key: str, default: Any = None) -> Any:
        """Get config value."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.get_config(key, default)

    async def set(self, key: str, value: Any) -> bool:
        """Set config value."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.set_config(key, value)

    async def get_telegram(self) -> dict:
        """Get Telegram config."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.get_telegram_config()

    async def set_telegram(self, config: dict) -> bool:
        """Set Telegram config."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.set_telegram_config(config)

    async def get_widget(self) -> dict:
        """Get widget config."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.get_widget_config()

    async def set_widget(self, config: dict) -> bool:
        """Set widget config."""
        async with AsyncSessionLocal() as session:
            repo = ConfigRepository(session)
            return await repo.set_widget_config(config)


# ============== Telegram Session Manager ==============

class AsyncTelegramSessionManager:
    """Async Telegram session manager using database."""

    async def get_session(self, user_id: int) -> Optional[str]:
        """Get chat session ID for user."""
        async with AsyncSessionLocal() as session:
            repo = TelegramRepository(session)
            return await repo.get_session(user_id)

    async def set_session(
        self,
        user_id: int,
        chat_session_id: str,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ):
        """Set or update user session."""
        async with AsyncSessionLocal() as session:
            repo = TelegramRepository(session)
            return await repo.set_session(
                user_id, chat_session_id, username, first_name, last_name
            )

    async def get_all_sessions(self) -> List[dict]:
        """Get all sessions."""
        async with AsyncSessionLocal() as session:
            repo = TelegramRepository(session)
            return await repo.get_all_sessions()

    async def get_sessions_dict(self) -> Dict[int, str]:
        """Get sessions as user_id -> session_id dict."""
        async with AsyncSessionLocal() as session:
            repo = TelegramRepository(session)
            return await repo.get_sessions_as_dict()

    async def clear_all(self) -> int:
        """Clear all sessions."""
        async with AsyncSessionLocal() as session:
            repo = TelegramRepository(session)
            return await repo.clear_all_sessions()


# ============== Audit Logger ==============

class AsyncAuditLogger:
    """Async audit logger using database."""

    async def log(
        self,
        action: str,
        resource: str,
        resource_id: str = None,
        user_id: str = None,
        user_ip: str = None,
        details: dict = None,
    ):
        """Log audit event."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.log(action, resource, resource_id, user_id, user_ip, details)

    async def get_logs(
        self,
        action: str = None,
        resource: str = None,
        limit: int = 100,
    ) -> List[dict]:
        """Get audit logs."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.get_logs(action=action, resource=resource, limit=limit)

    async def get_recent(self, hours: int = 24) -> List[dict]:
        """Get recent logs."""
        async with AsyncSessionLocal() as session:
            repo = AuditRepository(session)
            return await repo.get_recent(hours)


# ============== Global Instances ==============

# These can be used directly in orchestrator
async_chat_manager = AsyncChatManager()
async_faq_manager = AsyncFAQManager()
async_preset_manager = AsyncPresetManager()
async_config_manager = AsyncConfigManager()
async_telegram_manager = AsyncTelegramSessionManager()
async_audit_logger = AsyncAuditLogger()


# ============== Initialization Function ==============

async def init_database():
    """Initialize database - call this on startup."""
    await db_manager.initialize()


async def shutdown_database():
    """Shutdown database - call this on shutdown."""
    await db_manager.shutdown()


async def get_database_status() -> dict:
    """Get database status for health checks."""
    return await db_manager.get_status()
