"""Shared bot state — avoids circular imports between bot.py and handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .config import WhatsAppBotConfig


_bot_config: WhatsAppBotConfig | None = None


def get_bot_config() -> WhatsAppBotConfig | None:
    """Get current bot config (None in standalone mode)."""
    return _bot_config


def set_bot_config(config: WhatsAppBotConfig | None) -> None:
    """Set current bot config."""
    global _bot_config
    _bot_config = config
