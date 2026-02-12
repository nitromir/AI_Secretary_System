"""Text message handler — main conversation flow for WhatsApp.

Receives text from webhook, routes through LLM, sends response back.
Unlike Telegram, WhatsApp doesn't support message editing, so we collect
the full response before sending (no streaming to user).
"""

import asyncio
import logging

from ..services.llm_router import get_llm_router
from ..services.session_store import get_session_store
from ..services.whatsapp_client import MAX_TEXT_LENGTH, get_whatsapp_client


logger = logging.getLogger(__name__)

# Per-user locks to serialize requests
_user_locks: dict[str, asyncio.Lock] = {}


def _get_lock(phone: str) -> asyncio.Lock:
    if phone not in _user_locks:
        _user_locks[phone] = asyncio.Lock()
    return _user_locks[phone]


async def handle_text_message(phone: str, text: str, message_id: str) -> None:
    """Handle an incoming text message from WhatsApp.

    Args:
        phone: Sender phone number (E.164 without +)
        text: Message text content
        message_id: WhatsApp message ID (wamid)
    """
    lock = _get_lock(phone)

    async with lock:
        await _process_message(phone, text, message_id)


async def _process_message(phone: str, text: str, message_id: str) -> None:
    """Core logic: mark as read, call LLM, send response."""
    wa_client = get_whatsapp_client()
    store = get_session_store()
    router = get_llm_router()

    # Mark as read (blue checkmarks)
    try:
        await wa_client.mark_as_read(message_id)
    except Exception:
        logger.debug("Failed to mark message as read", exc_info=True)

    session = store.get_or_create(phone)
    session.append_message("user", text)

    try:
        # Non-streaming: collect full response (WhatsApp can't edit messages)
        response = await router.chat(messages=session.messages)

        # Split long responses into multiple messages
        chunks = _split_text(response)
        for chunk in chunks:
            await wa_client.send_text(to=phone, text=chunk)

        session.append_message("assistant", response)

    except Exception:
        logger.exception("LLM request failed for phone %s", phone)
        await wa_client.send_text(
            to=phone,
            text="Произошла ошибка при обработке запроса. Попробуйте позже.",
        )


def _split_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> list[str]:
    """Split text into chunks that fit WhatsApp's message size limit.

    Tries to split on paragraph boundaries, then sentence boundaries,
    then hard-splits at max_length.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to split at paragraph boundary
        split_pos = remaining.rfind("\n\n", 0, max_length)
        if split_pos == -1:
            # Try sentence boundary
            split_pos = remaining.rfind(". ", 0, max_length)
            if split_pos != -1:
                split_pos += 1  # include the period
        if split_pos == -1:
            # Try newline
            split_pos = remaining.rfind("\n", 0, max_length)
        if split_pos == -1:
            # Hard split
            split_pos = max_length

        chunks.append(remaining[:split_pos].rstrip())
        remaining = remaining[split_pos:].lstrip()

    return chunks
