"""Shared bot state — avoids circular imports between bot.py and handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .sales.keyboards import DEFAULT_ACTION_BUTTONS


if TYPE_CHECKING:
    from .config import BotConfig


_bot_config: BotConfig | None = None
_action_buttons: list[dict[str, Any]] = DEFAULT_ACTION_BUTTONS


def get_bot_config() -> BotConfig | None:
    """Get current bot config (None in standalone mode)."""
    return _bot_config


def set_bot_config(config: BotConfig | None) -> None:
    """Set current bot config."""
    global _bot_config
    _bot_config = config


def get_action_buttons() -> list[dict[str, Any]]:
    """Get current action buttons config."""
    return _action_buttons


def set_action_buttons(buttons: list[dict[str, Any]]) -> None:
    """Set current action buttons config."""
    global _action_buttons
    _action_buttons = buttons
