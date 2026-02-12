"""Interactive message handler — button and list replies.

Handles responses to quick-reply buttons and list selections.
This is the WhatsApp equivalent of Telegram's callback_query handler.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)


async def handle_interactive_reply(phone: str, reply: dict[str, Any]) -> None:
    """Handle an interactive reply (button press or list selection).

    Args:
        phone: Sender phone number
        reply: Interactive reply payload from webhook.
            For buttons: {"type": "button_reply", "button_reply": {"id": "...", "title": "..."}}
            For lists:   {"type": "list_reply", "list_reply": {"id": "...", "title": "...", "description": "..."}}
    """
    reply_type = reply.get("type", "")
    reply_id = ""

    if reply_type == "button_reply":
        reply_id = reply.get("button_reply", {}).get("id", "")
    elif reply_type == "list_reply":
        reply_id = reply.get("list_reply", {}).get("id", "")

    if not reply_id:
        logger.warning("Interactive reply with no ID from %s: %s", phone, reply)
        return

    logger.info("Interactive reply from %s: %s (type=%s)", phone, reply_id, reply_type)

    # TODO (WA-10): Route to sales funnel handlers based on reply_id prefix
    # e.g. "sales:start_quiz" → quiz handler, "faq:what_is" → FAQ handler
