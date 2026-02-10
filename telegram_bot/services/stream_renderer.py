"""SSE stream renderer — edits a Telegram message as chunks arrive."""

import asyncio
import logging
import time

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

from ..config import get_telegram_settings
from ..utils.chunking import split_message


logger = logging.getLogger(__name__)

# Telegram message length limit
TG_MSG_LIMIT = 4096


async def render_stream(
    bot: Bot,
    chat_id: int,
    stream,
    *,
    parse_mode: str | None = None,
) -> str:
    """Consume an async stream of SSE chunks, progressively edit a TG message.

    Args:
        bot: aiogram Bot instance.
        chat_id: Telegram chat to send into.
        stream: AsyncIterator of parsed SSE chunk dicts.
        parse_mode: Optional parse mode for final message.

    Returns:
        The full accumulated assistant text.
    """
    settings = get_telegram_settings()
    edit_interval = settings.stream_edit_interval
    min_chars = settings.stream_edit_min_chars

    # Send placeholder
    placeholder = await bot.send_message(chat_id, "\u23f3")
    msg_id = placeholder.message_id

    full_text = ""
    last_edit_time = 0.0
    last_edit_len = 0
    sent_messages: list[int] = [msg_id]  # track all message IDs

    async def _safe_edit(text: str, message_id: int, final: bool = False) -> None:
        """Edit message with retry-after handling."""
        nonlocal last_edit_time, last_edit_len
        display = text[:TG_MSG_LIMIT] if len(text) > TG_MSG_LIMIT else text
        if not display.strip():
            display = "\u23f3"
        try:
            if parse_mode and final:
                await bot.edit_message_text(
                    display,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode=parse_mode,
                )
            else:
                await bot.edit_message_text(
                    display,
                    chat_id=chat_id,
                    message_id=message_id,
                )
            last_edit_time = time.monotonic()
            last_edit_len = len(text)
        except TelegramRetryAfter as e:
            logger.warning("Rate limited, waiting %s seconds", e.retry_after)
            await asyncio.sleep(e.retry_after)
            await _safe_edit(text, message_id, final)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass  # Ignore — text hasn't changed
            else:
                logger.error("Edit failed: %s", e)

    try:
        async for chunk in stream:
            # Support both plain string chunks (from LLMRouter) and
            # OpenAI-compatible dicts (choices[].delta.content)
            if isinstance(chunk, str):
                content = chunk
            else:
                choices = chunk.get("choices", [])
                if not choices:
                    continue
                delta = choices[0].get("delta", {})
                content = delta.get("content")
            if not content:
                continue

            full_text += content

            now = time.monotonic()
            new_chars = len(full_text) - last_edit_len
            elapsed = now - last_edit_time

            if elapsed >= edit_interval or new_chars >= min_chars:
                await _safe_edit(full_text, msg_id)

    except Exception:
        logger.exception("Error during stream rendering")

    # Final edit with the complete text
    if not full_text.strip():
        full_text = "(empty response)"

    if len(full_text) <= TG_MSG_LIMIT:
        await _safe_edit(full_text, msg_id, final=True)
    else:
        # Split into multiple messages
        parts = split_message(full_text)
        # Edit the first message with the first part
        await _safe_edit(parts[0], msg_id, final=True)
        # Send remaining parts as new messages
        for part in parts[1:]:
            try:
                extra = await bot.send_message(
                    chat_id,
                    part,
                    parse_mode=parse_mode if parse_mode else None,
                )
                sent_messages.append(extra.message_id)
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                extra = await bot.send_message(
                    chat_id,
                    part,
                    parse_mode=parse_mode if parse_mode else None,
                )
                sent_messages.append(extra.message_id)

    return full_text
