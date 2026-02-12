"""Welcome handler — entry point for the sales funnel."""

import logging

from ...sales.database import get_sales_db
from ...sales.keyboards import welcome_buttons
from ...sales.texts import WELCOME_TEXT
from ..interactive import _send_buttons


logger = logging.getLogger(__name__)


async def handle_welcome(phone: str) -> None:
    """Upsert user, log start event, send welcome buttons."""
    db = await get_sales_db()
    await db.upsert_user(phone)
    await db.log_event(phone, "start")
    await _send_buttons(phone, WELCOME_TEXT, welcome_buttons())
