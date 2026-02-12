"""Central sales action dispatcher.

Routes all `sales:*` button IDs to the correct handler function.
Called from interactive.py — replaces the old catch-all placeholder.
"""

import logging

from ...sales.keyboards import contact_buttons, welcome_buttons
from ...sales.texts import CONTACT_TEXT, WELCOME_TEXT
from ..interactive import _send_buttons
from . import basic, custom, diy, quiz, welcome


logger = logging.getLogger(__name__)


async def route_sales_action(phone: str, action: str) -> None:
    """Route a sales:* action to the correct handler."""

    # ── Welcome / navigation ──────────────────────────────
    if action == "back_welcome":
        await welcome.handle_welcome(phone)
        return

    if action == "what_is":
        from ...sales.keyboards import what_is_buttons
        from ...sales.texts import WHAT_IS_TEXT

        await _send_buttons(phone, WHAT_IS_TEXT, what_is_buttons())
        return

    if action == "contact":
        await _send_buttons(phone, CONTACT_TEXT, contact_buttons())
        return

    if action == "github":
        await diy.handle_diy_github(phone)
        return

    if action == "faq":
        from ...sales.keyboards import faq_list
        from ...sales.texts import FAQ_MENU_TEXT
        from ..interactive import _send_list

        await _send_list(phone, FAQ_MENU_TEXT, faq_list())
        return

    # ── Quiz ──────────────────────────────────────────────
    if action == "start_quiz":
        await quiz.handle_quiz_start(phone)
        return

    if action.startswith("qt_"):
        await quiz.handle_quiz_tech(phone, action)
        return

    if action.startswith("qi_"):
        await quiz.handle_quiz_infra(phone, action)
        return

    # ── DIY path ──────────────────────────────────────────
    if action.startswith("gpu_"):
        gpu_key = action[4:]  # "gpu_rtx_30xx_low" -> "rtx_30xx_low"
        if gpu_key == "other":
            await diy.handle_gpu_custom_prompt(phone)
        else:
            await diy.handle_gpu_selected(phone, gpu_key)
        return

    if action == "diy_github":
        await diy.handle_diy_github(phone)
        return

    if action == "diy_install_5k":
        await diy.handle_diy_install_5k(phone)
        return

    if action == "diy_gpu_list":
        await diy.handle_diy_path(phone)
        return

    # ── Basic path ────────────────────────────────────────
    if action == "basic_checkout":
        await basic.handle_basic_checkout(phone)
        return

    if action == "basic_demo":
        await basic.handle_basic_demo(phone)
        return

    if action == "basic_pay":
        await basic.handle_basic_pay(phone)
        return

    if action == "basic_no_gpu":
        await basic.handle_basic_no_gpu(phone)
        return

    if action == "basic_back_value":
        await basic.handle_basic_path(phone)
        return

    if action.startswith("nogpu_") or (action == "contact"):
        await basic.handle_no_gpu_option(phone, action)
        return

    # ── Custom path ───────────────────────────────────────
    if action == "custom_start":
        await custom.handle_custom_start(phone)
        return

    if action == "custom_prices":
        await custom.handle_custom_prices(phone)
        return

    if action == "custom_expensive":
        await custom.handle_custom_expensive(phone)
        return

    if action == "custom_restart":
        await custom.handle_custom_restart(phone)
        return

    if action.startswith("cv_"):
        volume = action[3:]  # "cv_vol_low" -> "vol_low"
        await custom.handle_custom_volume(phone, volume)
        return

    if action.startswith("ci_"):
        int_key = action[3:]  # "ci_int_bitrix" -> "int_bitrix"
        if int_key == "more":
            await custom.handle_custom_integration_more(phone)
        elif int_key == "done":
            await custom.handle_custom_integration_done(phone)
        else:
            await custom.handle_custom_integration(phone, int_key)
        return

    if action.startswith("ct_"):
        timeline = action[3:]  # "ct_time_urgent" -> "time_urgent"
        await custom.handle_custom_timeline(phone, timeline)
        return

    if action.startswith("cb_"):
        budget = action[3:]  # "cb_budget_50" -> "budget_50"
        await custom.handle_custom_budget(phone, budget)
        return

    if action.startswith("ce_"):
        await custom.handle_expensive_option(phone, action)
        return

    # ── Fallback ──────────────────────────────────────────
    logger.warning("Unhandled sales action: %s from %s", action, phone)
    await _send_buttons(phone, WELCOME_TEXT, welcome_buttons())
