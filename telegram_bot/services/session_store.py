"""In-memory session storage for Telegram users."""

import uuid
from dataclasses import dataclass, field

from ..config import get_telegram_settings
from ..state import get_bot_config


@dataclass
class UserSession:
    """A single user's conversation session."""

    user_id: int
    conversation_id: str
    model: str
    messages: list[dict] = field(default_factory=list)

    def append_message(self, role: str, content: str | list) -> None:
        """Add a message and trim if over limit."""
        self.messages.append({"role": role, "content": content})
        settings = get_telegram_settings()
        limit = settings.max_messages_per_session
        if len(self.messages) > limit:
            # Keep system messages + trim oldest non-system messages
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            other_msgs = [m for m in self.messages if m["role"] != "system"]
            # Keep only the most recent messages within the limit
            keep = limit - len(system_msgs)
            self.messages = system_msgs + other_msgs[-keep:]


class SessionStore:
    """In-memory store keyed by Telegram user_id."""

    def __init__(self) -> None:
        self._sessions: dict[int, UserSession] = {}

    def get(self, user_id: int) -> UserSession | None:
        return self._sessions.get(user_id)

    def get_or_create(self, user_id: int) -> UserSession:
        """Get existing session or create a new one."""
        session = self._sessions.get(user_id)
        if session is None:
            session = self._create(user_id)
        return session

    def _create(self, user_id: int) -> UserSession:
        settings = get_telegram_settings()
        conversation_id = f"tg-{user_id}-{uuid.uuid4().hex[:8]}"
        session = UserSession(
            user_id=user_id,
            conversation_id=conversation_id,
            model=settings.default_model,
        )
        # Add system prompt: prefer BotConfig (from DB), fallback to env var
        bot_config = get_bot_config()
        system_prompt = (
            bot_config.system_prompt
            if bot_config and bot_config.system_prompt
            else settings.get_system_prompt()
        )
        if system_prompt:
            session.messages.append({"role": "system", "content": system_prompt})
        self._sessions[user_id] = session
        return session

    def reset(self, user_id: int) -> UserSession:
        """Clear the session and create a fresh one."""
        self._sessions.pop(user_id, None)
        return self._create(user_id)

    def set_model(self, user_id: int, model: str) -> UserSession:
        """Update the model for a user's session."""
        session = self.get_or_create(user_id)
        session.model = model
        return session


# Singleton
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
