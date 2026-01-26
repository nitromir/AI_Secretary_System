"""
SQLAlchemy ORM models for AI Secretary System.

Tables:
- chat_sessions: Chat session metadata
- chat_messages: Individual chat messages
- faq_entries: FAQ question-answer pairs
- tts_presets: Custom TTS voice presets
- system_config: Key-value system configuration
- telegram_sessions: Telegram user sessions
- audit_log: System audit trail
"""

from datetime import datetime
from typing import Optional, List
import json

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class ChatSession(Base):
    """Chat session with optional system prompt"""
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="Новый чат")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created",
    )

    def to_dict(self, include_messages: bool = True) -> dict:
        result = {
            "id": self.id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }
        if include_messages:
            result["messages"] = [m.to_dict() for m in self.messages]
        return result

    def to_summary(self) -> dict:
        """Return summary for list view"""
        messages = self.messages or []
        last_msg = messages[-1].content[:100] if messages else None
        return {
            "id": self.id,
            "title": self.title,
            "message_count": len(messages),
            "last_message": last_msg,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }


class ChatMessage(Base):
    """Individual message in a chat session"""
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    edited: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_created", "session_id", "created"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "edited": self.edited,
            "timestamp": self.created.isoformat() if self.created else None,
        }


class FAQEntry(Base):
    """FAQ question-answer pair with fuzzy matching support"""
    __tablename__ = "faq_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    answer: Mapped[str] = mapped_column(Text)
    keywords: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "keywords": json.loads(self.keywords) if self.keywords else [],
            "enabled": self.enabled,
            "hit_count": self.hit_count,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }

    @classmethod
    def from_legacy(cls, question: str, answer: str) -> "FAQEntry":
        """Create from legacy JSON format (question: answer)"""
        return cls(question=question.lower(), answer=answer, enabled=True)


class TTSPreset(Base):
    """Custom TTS voice preset with parameters"""
    __tablename__ = "tts_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    params: Mapped[str] = mapped_column(Text)  # JSON object with TTS parameters
    builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "params": json.loads(self.params) if self.params else {},
            "builtin": self.builtin,
        }

    def get_params(self) -> dict:
        return json.loads(self.params) if self.params else {}

    def set_params(self, params: dict):
        self.params = json.dumps(params, ensure_ascii=False)


class SystemConfig(Base):
    """Key-value system configuration store"""
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text)  # JSON value
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_value(self) -> any:
        """Parse JSON value"""
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value

    def set_value(self, value: any):
        """Serialize value to JSON"""
        self.value = json.dumps(value, ensure_ascii=False)


class TelegramSession(Base):
    """Telegram user session mapping"""
    __tablename__ = "telegram_sessions"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_session_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
    )
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "chat_session_id": self.chat_session_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "created": self.created.isoformat() if self.created else None,
            "updated": self.updated.isoformat() if self.updated else None,
        }


class AuditLog(Base):
    """System audit trail for compliance"""
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)  # create, update, delete, login, etc.
    resource: Mapped[str] = mapped_column(String(100))  # chat, faq, tts, config, etc.
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON

    __table_args__ = (
        Index("ix_audit_log_timestamp_action", "timestamp", "action"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "user_ip": self.user_ip,
            "details": json.loads(self.details) if self.details else None,
        }
