"""Custom path handler — 5-step discovery, quote calculation, alternatives."""

import json
import logging

from telegram_bot.sales.segments import INTEGRATION_PRICES, calculate_quote

from ...sales.database import get_sales_db
from ...sales.keyboards import (
    contact_buttons,
    custom_expensive_buttons,
    custom_intro_buttons,
    custom_quote_buttons,
    custom_step_2_list,
    custom_step_3_list,
    custom_step_3_more_buttons,
    custom_step_4_list,
    custom_step_5_list,
    welcome_buttons,
)
from ...sales.texts import (
    CONTACT_TEXT,
    CUSTOM_EXPENSIVE_TEXT,
    CUSTOM_INTEGRATION_SELECTED_TEXT,
    CUSTOM_INTRO_TEXT,
    CUSTOM_PRICES_TEXT,
    CUSTOM_QUOTE_TEXT,
    CUSTOM_STEP_1_TEXT,
    CUSTOM_STEP_2_TEXT,
    CUSTOM_STEP_3_TEXT,
    CUSTOM_STEP_4_TEXT,
    CUSTOM_STEP_5_TEXT,
)
from ...services.whatsapp_client import get_whatsapp_client
from ..interactive import _send_buttons, _send_list


logger = logging.getLogger(__name__)

# Volume key → display name
_VOLUME_NAMES = {
    "vol_low": "До 50/день",
    "vol_mid": "50-200/день",
    "vol_high": "200-1000/день",
    "vol_enterprise": "1000+/день",
    "vol_unknown": "Не определён",
}


async def handle_custom_intro(phone: str) -> None:
    """Enter custom path — show intro with action buttons."""
    db = await get_sales_db()
    await db.log_event(phone, "custom_path_entered")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=CUSTOM_INTRO_TEXT)
    await _send_buttons(phone, "Расскажете о вашей задаче?", custom_intro_buttons())


async def handle_custom_start(phone: str) -> None:
    """Start custom discovery — step 1 (free-text task description)."""
    db = await get_sales_db()
    await db.log_event(phone, "custom_discovery_started")
    await db.set_user_state(phone, "custom_step_1")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=CUSTOM_STEP_1_TEXT)


async def handle_custom_prices(phone: str) -> None:
    """Show pricing overview."""
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=CUSTOM_PRICES_TEXT)
    await _send_buttons(phone, "Расскажете о вашей задаче?", custom_intro_buttons())


async def handle_custom_step_1_text(phone: str, text: str) -> None:
    """Save step 1 (task description), show step 2 (volume list)."""
    db = await get_sales_db()
    await db.set_user_state(phone, None)
    await db.save_discovery_step(phone, 1, text)
    await _send_list(phone, CUSTOM_STEP_2_TEXT, custom_step_2_list())


async def handle_custom_volume(phone: str, volume: str) -> None:
    """Save step 2 (volume), show step 3 (integrations list)."""
    db = await get_sales_db()
    await db.save_discovery_step(phone, 2, volume)
    await _send_list(phone, CUSTOM_STEP_3_TEXT, custom_step_3_list())


async def handle_custom_integration(phone: str, int_key: str) -> None:
    """Handle integration selection (step 3).

    WhatsApp lists are single-select, so we accumulate selections:
    - "int_none" → save ["int_none"], move to step 4
    - Other → append to JSON array, show "more/done" buttons
    """
    db = await get_sales_db()
    discovery = await db.get_discovery(phone)

    if int_key == "int_none":
        await db.save_discovery_step(phone, 3, json.dumps(["int_none"]))
        await _send_list(phone, CUSTOM_STEP_4_TEXT, custom_step_4_list())
        return

    # Accumulate selections
    current: list[str] = []
    if discovery and discovery.get("step_3_integrations"):
        try:
            current = json.loads(discovery["step_3_integrations"])
        except (json.JSONDecodeError, TypeError):
            current = []

    if int_key not in current:
        current.append(int_key)

    await db.save_discovery_step(phone, 3, json.dumps(current))

    # Show accumulated selections + more/done buttons
    names = []
    for k in current:
        if k in INTEGRATION_PRICES:
            names.append(INTEGRATION_PRICES[k][0])
    selected_text = CUSTOM_INTEGRATION_SELECTED_TEXT.format(selected=", ".join(names))
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=selected_text)
    await _send_buttons(phone, "Добавить ещё или продолжить?", custom_step_3_more_buttons())


async def handle_custom_integration_more(phone: str) -> None:
    """Re-show integrations list for additional selection."""
    await _send_list(phone, CUSTOM_STEP_3_TEXT, custom_step_3_list())


async def handle_custom_integration_done(phone: str) -> None:
    """Finalize integrations, move to step 4 (timeline)."""
    await _send_list(phone, CUSTOM_STEP_4_TEXT, custom_step_4_list())


async def handle_custom_timeline(phone: str, timeline: str) -> None:
    """Save step 4 (timeline), show step 5 (budget list)."""
    db = await get_sales_db()
    await db.save_discovery_step(phone, 4, timeline)
    await _send_list(phone, CUSTOM_STEP_5_TEXT, custom_step_5_list())


async def handle_custom_budget(phone: str, budget: str) -> None:
    """Save step 5 (budget), calculate quote, send result."""
    db = await get_sales_db()
    await db.save_discovery_step(phone, 5, budget)
    discovery = await db.get_discovery(phone)

    if not discovery:
        logger.error("No discovery data for %s after step 5", phone)
        await _send_buttons(phone, "Произошла ошибка. Попробуйте снова.", welcome_buttons())
        return

    # Parse integrations from JSON
    integrations: list[str] = []
    if discovery.get("step_3_integrations"):
        try:
            integrations = json.loads(discovery["step_3_integrations"])
        except (json.JSONDecodeError, TypeError):
            integrations = []

    quote_input = {
        "step_2_volume": discovery.get("step_2_volume", "vol_unknown"),
        "step_3_integrations": integrations,
        "step_4_timeline": discovery.get("step_4_timeline", ""),
    }
    quote = calculate_quote(quote_input)

    # Format price breakdown
    lines = []
    for name, price in quote["items"]:
        lines.append(f"├─ {name}: {price:,}₽")
    price_breakdown = "\n".join(lines)

    # Format integration names
    int_names = []
    for k in integrations:
        if k in INTEGRATION_PRICES:
            int_names.append(INTEGRATION_PRICES[k][0])
        elif k == "int_none":
            int_names.append("Без интеграций")
    integrations_str = ", ".join(int_names) if int_names else "Без интеграций"

    volume_str = _VOLUME_NAMES.get(discovery.get("step_2_volume", ""), "Не указан")
    task_str = discovery.get("step_1_task", "Не указана")
    if len(task_str) > 60:
        task_str = task_str[:57] + "..."

    text = CUSTOM_QUOTE_TEXT.format(
        task=task_str,
        volume=volume_str,
        integrations=integrations_str,
        timeline=quote["timeline"],
        price_breakdown=price_breakdown,
        total_min=quote["total_min"],
        total_max=quote["total_max"],
    )

    await db.log_event(
        phone,
        "quote_generated",
        {"total_min": quote["total_min"], "total_max": quote["total_max"]},
    )

    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=text)
    await _send_buttons(phone, "Выберите действие 👇", custom_quote_buttons())


async def handle_custom_expensive(phone: str) -> None:
    """Handle "too expensive" objection — show alternatives."""
    db = await get_sales_db()
    await db.log_event(phone, "objection_expensive")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=CUSTOM_EXPENSIVE_TEXT)
    await _send_buttons(phone, "Какой вариант интереснее?", custom_expensive_buttons())


async def handle_expensive_option(phone: str, option: str) -> None:
    """Route expensive alternative selection."""
    from . import diy

    if option in ("ce_mvp", "ce_stages"):
        await _send_buttons(phone, CONTACT_TEXT, contact_buttons())
    elif option == "ce_diy":
        await diy.handle_diy_path(phone)
    else:
        logger.warning("Unknown expensive option: %s", option)


async def handle_custom_restart(phone: str) -> None:
    """Reset discovery and restart from step 1."""
    db = await get_sales_db()
    await db.reset_discovery(phone)
    await db.set_user_state(phone, "custom_step_1")
    await db.log_event(phone, "custom_discovery_restarted")
    wa = get_whatsapp_client()
    await wa.send_text(to=phone, text=CUSTOM_STEP_1_TEXT)
