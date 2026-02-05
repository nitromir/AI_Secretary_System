"""File and photo handler.

Note: File upload to LLM is temporarily disabled.
The LLM Router currently supports text-only interactions.
File analysis will be added in a future update.
"""

import logging

from aiogram import F, Router
from aiogram.types import Message


router = Router()
logger = logging.getLogger(__name__)

# 20 MB limit (Telegram Bot API file download limit)
MAX_FILE_SIZE = 20 * 1024 * 1024

# Temporary message while file processing is not supported
FILE_NOT_SUPPORTED_MSG = (
    "Анализ файлов временно недоступен.\n\n"
    "Сейчас бот поддерживает только текстовые сообщения.\n"
    "Функция анализа файлов будет добавлена в следующем обновлении."
)


@router.message(F.document)
async def on_document(message: Message) -> None:
    """Handle document uploads — currently not supported."""
    if not message.from_user or not message.document:
        return

    # If there's a caption, we could process it as text
    # For now, just inform user that files are not supported
    await message.answer(FILE_NOT_SUPPORTED_MSG)
    logger.info(
        "File upload attempted by user %s (not supported yet)",
        message.from_user.id,
    )


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    """Handle photo uploads — currently not supported."""
    if not message.from_user or not message.photo:
        return

    await message.answer(FILE_NOT_SUPPORTED_MSG)
    logger.info(
        "Photo upload attempted by user %s (not supported yet)",
        message.from_user.id,
    )
