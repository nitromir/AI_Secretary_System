"""
Telegram repository for managing Telegram user sessions.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import TelegramSession
from db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Legacy JSON file path for backward compatibility
LEGACY_SESSIONS_FILE = Path(__file__).parent.parent.parent / "telegram_sessions.json"


class TelegramRepository(BaseRepository[TelegramSession]):
    """Repository for Telegram user sessions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TelegramSession)

    async def _sync_to_legacy_file(self):
        """Write sessions to legacy JSON file for backward compatibility."""
        try:
            sessions = await self.get_sessions_as_dict()
            LEGACY_SESSIONS_FILE.write_text(
                json.dumps(sessions, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logger.warning(f"Failed to sync telegram sessions to legacy file: {e}")

    async def get_session(self, user_id: int) -> Optional[str]:
        """Get chat session ID for Telegram user."""
        session = await self.session.get(TelegramSession, user_id)
        return session.chat_session_id if session else None

    async def set_session(
        self,
        user_id: int,
        chat_session_id: str,
        username: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> TelegramSession:
        """Create or update Telegram user session."""
        telegram_session = await self.session.get(TelegramSession, user_id)

        if telegram_session:
            telegram_session.chat_session_id = chat_session_id
            telegram_session.username = username
            telegram_session.first_name = first_name
            telegram_session.last_name = last_name
            telegram_session.updated = datetime.utcnow()
        else:
            telegram_session = TelegramSession(
                user_id=user_id,
                chat_session_id=chat_session_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )
            self.session.add(telegram_session)

        await self.session.commit()
        await self._sync_to_legacy_file()
        return telegram_session

    async def delete_session(self, user_id: int) -> bool:
        """Delete Telegram user session."""
        result = await self.session.execute(
            delete(TelegramSession).where(TelegramSession.user_id == user_id)
        )
        await self.session.commit()
        await self._sync_to_legacy_file()
        return result.rowcount > 0

    async def get_all_sessions(self) -> List[dict]:
        """Get all Telegram sessions."""
        result = await self.session.execute(
            select(TelegramSession).order_by(TelegramSession.updated.desc())
        )
        sessions = result.scalars().all()
        return [s.to_dict() for s in sessions]

    async def clear_all_sessions(self) -> int:
        """Clear all Telegram sessions. Returns count of deleted sessions."""
        result = await self.session.execute(delete(TelegramSession))
        await self.session.commit()
        await self._sync_to_legacy_file()
        return result.rowcount

    async def get_sessions_as_dict(self) -> Dict[int, str]:
        """Get sessions as user_id -> chat_session_id dict (legacy format)."""
        result = await self.session.execute(select(TelegramSession))
        sessions = result.scalars().all()
        return {s.user_id: s.chat_session_id for s in sessions}

    async def import_from_dict(self, sessions: Dict[int, str]) -> int:
        """
        Import sessions from legacy dict format.
        Returns number of imported sessions.
        """
        count = 0
        for user_id, chat_session_id in sessions.items():
            existing = await self.session.get(TelegramSession, user_id)
            if existing:
                continue

            session = TelegramSession(
                user_id=user_id,
                chat_session_id=chat_session_id,
                created=datetime.utcnow(),
                updated=datetime.utcnow(),
            )
            self.session.add(session)
            count += 1

        await self.session.commit()
        return count

    async def get_session_count(self) -> int:
        """Get total number of Telegram sessions."""
        return await self.count()
