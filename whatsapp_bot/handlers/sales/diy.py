"""DIY path handler — GPU audit, GitHub CTA, install redirect."""

import logging

from telegram_bot.sales.segments import get_gpu_audit

from ...sales.database import get_sales_db
from ...sales.keyboards import (
    diy_audit_result_buttons,
    diy_audit_unknown_buttons,
    diy_gpu_list,
    welcome_buttons,
)
from ...sales.texts import (
    DIY_AUDIT_CUSTOM_TEXT,
    DIY_AUDIT_RESULT_TEXT,
    DIY_AUDIT_TEXT,
    DIY_AUDIT_UNKNOWN_TEXT,
    DIY_GITHUB_TEXT,
)
from ...services.whatsapp_client import get_whatsapp_client
from ..interactive import _send_buttons, _send_list
from . import basic


logger = logging.getLogger(__name__)


async def handle_diy_path(phone: str) -> None:
    """Enter DIY path — show GPU selection list."""
    db = await get_sales_db()
    await db.log_event(phone, "diy_path_entered")
    await _send_list(phone, DIY_AUDIT_TEXT, diy_gpu_list())


async def handle_gpu_selected(phone: str, gpu_key: str) -> None:
    """Look up GPU audit data and send result."""
    audit = get_gpu_audit(gpu_key)
    if not audit:
        await handle_gpu_custom_prompt(phone)
        return

    stars = "⭐" * audit["quality"]
    text = DIY_AUDIT_RESULT_TEXT.format(
        gpu_name=audit["name"],
        llm=audit["llm"],
        stars=stars,
        speed=audit["speed"],
        hint=audit["hint"],
    )
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=text)
    await _send_buttons(phone, "Готовы к установке?", diy_audit_result_buttons())


async def handle_gpu_custom_prompt(phone: str) -> None:
    """Ask user to type their GPU model."""
    db = await get_sales_db()
    await db.set_user_state(phone, "diy_gpu_custom")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=DIY_AUDIT_CUSTOM_TEXT)


async def handle_gpu_custom_text(phone: str, text: str) -> None:
    """Handle free-text GPU model input — show unknown result."""
    db = await get_sales_db()
    await db.set_user_state(phone, None)
    await db.log_event(phone, "gpu_custom_input", {"text": text})
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=DIY_AUDIT_UNKNOWN_TEXT)
    await _send_buttons(phone, "Выберите действие 👇", diy_audit_unknown_buttons())


async def handle_diy_github(phone: str) -> None:
    """Send GitHub CTA + welcome buttons."""
    db = await get_sales_db()
    await db.log_event(phone, "cta_clicked", {"action": "github"})
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=DIY_GITHUB_TEXT)
    await _send_buttons(phone, "Что дальше?", welcome_buttons())


async def handle_diy_install_5k(phone: str) -> None:
    """Redirect to basic checkout."""
    await basic.handle_basic_checkout(phone)
