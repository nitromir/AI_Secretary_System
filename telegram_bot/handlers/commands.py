"""Command handlers: /new, /model.

Note: /start is handled by handlers/sales/welcome.py (sales funnel).
      /chat and /menu are handled by handlers/sales/common.py.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..services.session_store import get_session_store


router = Router()
logger = logging.getLogger(__name__)

MODELS = [
    ("sonnet", "Claude Sonnet"),
    ("opus", "Claude Opus"),
    ("haiku", "Claude Haiku"),
]


@router.message(Command("new"))
async def cmd_new(message: Message) -> None:
    """Handle /new — reset the conversation."""
    if not message.from_user:
        return
    store = get_session_store()
    session = store.reset(message.from_user.id)
    await message.answer(f"Conversation cleared. Model: {session.model}")


@router.message(Command("model"))
async def cmd_model(message: Message) -> None:
    """Handle /model — show inline keyboard for model selection."""
    buttons = [
        [InlineKeyboardButton(text=label, callback_data=f"model:{model_id}")]
        for model_id, label in MODELS
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Choose a model:", reply_markup=keyboard)
