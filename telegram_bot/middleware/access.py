"""Access control middleware — whitelist filter by Telegram user ID."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from ..config import get_telegram_settings


logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Drop updates from users not in the whitelist.

    If TELEGRAM_ALLOWED_USERS is empty, all users are allowed.
    """

    def __init__(self) -> None:
        super().__init__()
        settings = get_telegram_settings()
        self._allowed = settings.get_allowed_user_ids()
        if self._allowed:
            logger.info("Access whitelist: %s", self._allowed)
        else:
            logger.warning("TELEGRAM_ALLOWED_USERS is empty — bot is open to everyone")

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # No whitelist configured — allow all
        if not self._allowed:
            return await handler(event, data)

        user_id: int | None = None
        if (isinstance(event, Message) and event.from_user) or (
            isinstance(event, CallbackQuery) and event.from_user
        ):
            user_id = event.from_user.id

        if user_id is None or user_id not in self._allowed:
            logger.debug("Blocked user_id=%s", user_id)
            return None  # silently drop

        return await handler(event, data)
