"""Callback query handlers (inline keyboard)."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..services.session_store import get_session_store


router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("model:"))
async def on_model_selected(callback: CallbackQuery) -> None:
    """Handle model selection from inline keyboard."""
    if not callback.data or not callback.from_user:
        return

    model_id = callback.data.split(":", 1)[1]
    store = get_session_store()
    session = store.set_model(callback.from_user.id, model_id)

    await callback.answer(f"Model set to {model_id}")
    if callback.message:
        await callback.message.edit_text(f"Model: {session.model}")
