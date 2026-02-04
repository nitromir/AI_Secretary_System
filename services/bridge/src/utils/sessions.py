"""Session management for multi-turn conversations."""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class Session:
    """Represents a conversation session.

    Note: We don't store full message history because OpenAI clients send
    full conversation in each request. We only track:
    - CLI session IDs for providers with native session support (e.g., Claude)
    - Conversation summary for long conversations (optional)
    """

    id: str  # OpenAI-compatible conversation ID
    provider: str  # claude, gemini, gpt
    cli_session_id: str | None = None  # CLI-specific session ID (e.g., Claude)
    model: str = ""
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    message_count: int = 0
    # Conversation summary for token optimization
    summary: str | None = None
    summary_up_to_index: int = 0  # Messages summarized up to this index
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self):
        """Update last used timestamp."""
        self.last_used_at = time.time()
        self.message_count += 1

    def set_summary(self, summary: str, up_to_index: int):
        """Store conversation summary."""
        self.summary = summary
        self.summary_up_to_index = up_to_index


class SessionManager:
    """Manages conversation sessions across providers."""

    def __init__(
        self,
        max_sessions: int = 100,
        ttl_seconds: int = 3600,  # 1 hour
    ):
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        session_id: str,
        provider: str,
        model: str = "",
        cli_session_id: str | None = None,
    ) -> Session:
        """Create a new session."""
        with self._lock:
            # Cleanup if at capacity
            if len(self._sessions) >= self.max_sessions:
                self._cleanup_expired()
                if len(self._sessions) >= self.max_sessions:
                    self._evict_oldest()

            session = Session(
                id=session_id,
                provider=provider,
                model=model,
                cli_session_id=cli_session_id,
            )
            self._sessions[session_id] = session
            logger.debug(f"Created session: {session_id} (provider={provider})")
            return session

    def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                # Check if expired
                if time.time() - session.last_used_at > self.ttl_seconds:
                    del self._sessions[session_id]
                    return None
                session.touch()
            return session

    def update_cli_session_id(self, session_id: str, cli_session_id: str) -> bool:
        """Update the CLI session ID for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.cli_session_id = cli_session_id
                session.touch()
                logger.debug(f"Updated CLI session ID: {session_id} -> {cli_session_id}")
                return True
            return False

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"Deleted session: {session_id}")
                return True
            return False

    def list_sessions(self, provider: str | None = None) -> list[Session]:
        """List all sessions, optionally filtered by provider."""
        with self._lock:
            self._cleanup_expired()
            sessions = list(self._sessions.values())
            if provider:
                sessions = [s for s in sessions if s.provider == provider]
            return sessions

    def _cleanup_expired(self) -> int:
        """Remove expired sessions. Must be called with lock held."""
        now = time.time()
        expired = [
            sid
            for sid, session in self._sessions.items()
            if now - session.last_used_at > self.ttl_seconds
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    def cleanup_expired(self) -> int:
        """Remove expired sessions (public API)."""
        with self._lock:
            return self._cleanup_expired()

    def _evict_oldest(self) -> bool:
        """Evict the oldest session. Must be called with lock held."""
        if not self._sessions:
            return False

        oldest = min(self._sessions.values(), key=lambda s: s.last_used_at)
        del self._sessions[oldest.id]
        logger.debug(f"Evicted oldest session: {oldest.id}")
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get session statistics."""
        with self._lock:
            self._cleanup_expired()

            by_provider: dict[str, int] = {}
            for session in self._sessions.values():
                by_provider[session.provider] = by_provider.get(session.provider, 0) + 1

            return {
                "total_sessions": len(self._sessions),
                "max_sessions": self.max_sessions,
                "ttl_seconds": self.ttl_seconds,
                "by_provider": by_provider,
            }


# Global session manager instance
_session_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
