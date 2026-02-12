"""Basic path handler — value prop, demo, checkout, no-GPU options."""

import logging

from ...sales.database import get_sales_db
from ...sales.keyboards import (
    basic_checkout_buttons,
    basic_demo_buttons,
    basic_no_gpu_list,
    basic_pay_buttons,
    basic_value_buttons,
    welcome_buttons,
)
from ...sales.texts import (
    BASIC_CHECKOUT_TEXT,
    BASIC_DEMO_TEXT,
    BASIC_NO_GPU_TEXT,
    BASIC_PAY_TEXT,
    BASIC_VALUE_TEXT,
)
from ...services.whatsapp_client import get_whatsapp_client
from ..interactive import _send_buttons, _send_list


logger = logging.getLogger(__name__)


async def handle_basic_path(phone: str) -> None:
    """Enter basic path — show value proposition."""
    db = await get_sales_db()
    await db.log_event(phone, "basic_path_entered")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=BASIC_VALUE_TEXT)
    await _send_buttons(phone, "Выберите действие 👇", basic_value_buttons())


async def handle_basic_demo(phone: str) -> None:
    """Show demo credentials."""
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=BASIC_DEMO_TEXT)
    await _send_buttons(phone, "Выберите действие 👇", basic_demo_buttons())


async def handle_basic_checkout(phone: str) -> None:
    """Show checkout info."""
    db = await get_sales_db()
    await db.log_event(phone, "checkout_started")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=BASIC_CHECKOUT_TEXT)
    await _send_buttons(phone, "Выберите действие 👇", basic_checkout_buttons())


async def handle_basic_pay(phone: str) -> None:
    """Send YooMoney payment link + contact buttons."""
    db = await get_sales_db()
    await db.log_event(phone, "payment_initiated")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=BASIC_PAY_TEXT)
    await _send_buttons(phone, "Выберите действие 👇", basic_pay_buttons())


async def handle_basic_no_gpu(phone: str) -> None:
    """Show no-GPU options."""
    await _send_list(phone, BASIC_NO_GPU_TEXT, basic_no_gpu_list())


async def handle_no_gpu_option(phone: str, option: str) -> None:
    """Route no-GPU option selection."""
    from . import diy

    if option == "nogpu_cpu":
        await diy.handle_diy_github(phone)
    elif option in ("nogpu_vps", "nogpu_own"):
        await handle_basic_checkout(phone)
    elif option == "contact":
        from ...sales.keyboards import contact_buttons
        from ...sales.texts import CONTACT_TEXT

        await _send_buttons(phone, CONTACT_TEXT, contact_buttons())
    else:
        logger.warning("Unknown no-GPU option: %s", option)
        await _send_buttons(phone, "Выберите действие 👇", welcome_buttons())
