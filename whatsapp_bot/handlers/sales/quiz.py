"""Quiz handler — tech level + infrastructure questions, then route to path."""

import logging

from telegram_bot.sales.segments import UserSegment, determine_segment

from ...sales.database import get_sales_db
from ...sales.keyboards import quiz_infra_list, quiz_tech_buttons
from ...sales.texts import QUIZ_INFRA_TEXT, QUIZ_TECH_TEXT
from ..interactive import _send_buttons, _send_list
from . import basic, custom, diy


logger = logging.getLogger(__name__)

# Button ID → internal key mapping
_TECH_MAP = {"qt_diy": "diy", "qt_ready": "ready", "qt_business": "business"}
_INFRA_MAP = {"qi_gpu": "gpu", "qi_cpu": "cpu", "qi_none": "none", "qi_unknown": "unknown"}


async def handle_quiz_start(phone: str) -> None:
    """Start the quiz — send tech question."""
    db = await get_sales_db()
    await db.log_event(phone, "quiz_started")
    await _send_buttons(phone, QUIZ_TECH_TEXT, quiz_tech_buttons())


async def handle_quiz_tech(phone: str, tech_key: str) -> None:
    """Save tech answer, send infra question."""
    internal_key = _TECH_MAP.get(tech_key, "diy")
    db = await get_sales_db()
    await db.upsert_user(phone)
    await db.update_user(phone, quiz_tech=internal_key)
    await _send_list(phone, QUIZ_INFRA_TEXT, quiz_infra_list())


async def handle_quiz_infra(phone: str, infra_key: str) -> None:
    """Save infra answer, determine segment, route to path."""
    internal_key = _INFRA_MAP.get(infra_key, "unknown")
    db = await get_sales_db()
    user = await db.get_user(phone)
    tech = user["quiz_tech"] if user else "diy"

    segment, sub_segment = determine_segment(tech, internal_key)
    await db.update_user(
        phone,
        quiz_infra=internal_key,
        segment=segment.value,
        sub_segment=sub_segment,
    )
    await db.log_event(phone, "quiz_completed", {"segment": segment.value, "sub": sub_segment})

    if segment == UserSegment.DIY:
        await diy.handle_diy_path(phone)
    elif segment == UserSegment.BASIC:
        await basic.handle_basic_path(phone)
    elif segment == UserSegment.CUSTOM:
        await custom.handle_custom_intro(phone)
    else:
        # Unknown segment — default to basic
        await basic.handle_basic_path(phone)
