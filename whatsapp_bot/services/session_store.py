"""In-memory session storage for WhatsApp users.

Similar to telegram_bot session store but keyed by phone number (str)
instead of Telegram user_id (int).
"""

import uuid
from dataclasses import dataclass, field

from ..config import get_whatsapp_settings
from ..state import get_bot_config


@dataclass
class UserSession:
    """A single user's conversation session."""

    phone: str
    conversation_id: str
    model: str
    messages: list[dict] = field(default_factory=list)

    def append_message(self, role: str, content: str | list) -> None:
        """Add a message and trim if over limit."""
        self.messages.append({"role": role, "content": content})

        bot_config = get_bot_config()
        limit = (
            bot_config.max_messages_per_session
            if bot_config
            else get_whatsapp_settings().max_messages_per_session
        )

        if len(self.messages) > limit:
            system_msgs = [m for m in self.messages if m["role"] == "system"]
            other_msgs = [m for m in self.messages if m["role"] != "system"]
            keep = limit - len(system_msgs)
            self.messages = system_msgs + other_msgs[-keep:]


class SessionStore:
    """In-memory store keyed by phone number."""

    def __init__(self) -> None:
        self._sessions: dict[str, UserSession] = {}

    def get(self, phone: str) -> UserSession | None:
        return self._sessions.get(phone)

    def get_or_create(self, phone: str) -> UserSession:
        """Get existing session or create a new one."""
        session = self._sessions.get(phone)
        if session is None:
            session = self._create(phone)
        return session

    def _create(self, phone: str) -> UserSession:
        settings = get_whatsapp_settings()
        conversation_id = f"wa-{phone}-{uuid.uuid4().hex[:8]}"
        session = UserSession(
            phone=phone,
            conversation_id=conversation_id,
            model=settings.default_model,
        )
        # Add system prompt: prefer BotConfig (from DB), fallback to env var
        bot_config = get_bot_config()
        system_prompt = (
            bot_config.system_prompt
            if bot_config and bot_config.system_prompt
            else settings.system_prompt
        )
        if system_prompt:
            session.messages.append({"role": "system", "content": system_prompt})
        self._sessions[phone] = session
        return session

    def reset(self, phone: str) -> UserSession:
        """Clear the session and create a fresh one."""
        self._sessions.pop(phone, None)
        return self._create(phone)

    def set_model(self, phone: str, model: str) -> UserSession:
        """Update the model for a user's session."""
        session = self.get_or_create(phone)
        session.model = model
        return session


# Singleton
_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore()
    return _store
