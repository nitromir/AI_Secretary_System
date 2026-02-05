"""Custom path handlers — for business users needing integrations."""

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...sales.database import get_sales_db
from ...sales.keyboards import (
    contact_kb,
    custom_expensive_kb,
    custom_intro_kb,
    custom_quote_kb,
    custom_step_2_kb,
    custom_step_3_kb,
    custom_step_4_kb,
    custom_step_5_kb,
)
from ...sales.segments import INTEGRATION_PRICES, calculate_quote
from ...sales.states import SalesFunnel
from ...sales.texts import (
    CONTACT_TEXT,
    CUSTOM_EXPENSIVE_TEXT,
    CUSTOM_INTRO_TEXT,
    CUSTOM_QUOTE_TEXT,
    CUSTOM_STEP_1_TEXT,
    CUSTOM_STEP_2_TEXT,
    CUSTOM_STEP_3_TEXT,
    CUSTOM_STEP_4_TEXT,
    CUSTOM_STEP_5_TEXT,
)


logger = logging.getLogger(__name__)
router = Router()


async def enter_custom_path(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry point into the Custom path from quiz."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "custom_path_entered")

    if callback.message:
        await callback.message.edit_text(
            CUSTOM_INTRO_TEXT,
            reply_markup=custom_intro_kb(),
        )
    await state.set_state(SalesFunnel.custom_intro)


@router.callback_query(F.data == "sales:custom_start")
async def custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the 5-step discovery."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "custom_discovery_started")

    if callback.message:
        await callback.message.edit_text(CUSTOM_STEP_1_TEXT)
    await state.set_state(SalesFunnel.custom_step_1)
    await callback.answer()


@router.callback_query(F.data == "sales:custom_prices")
async def custom_prices(callback: CallbackQuery, state: FSMContext) -> None:
    """Show pricing overview before discovery."""
    text = (
        "💰 Ориентировочные цены:\n\n"
        "• Базовая система: от 50,000₽\n"
        "• + Интеграция CRM: от 15,000₽\n"
        "• + Телефония: от 30,000₽\n"
        "• Полный комплекс: от 100,000₽\n\n"
        "Точная цена зависит от задачи.\n"
        "Пройдите 5 вопросов — и я дам расчёт."
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=custom_intro_kb())
    await callback.answer()


# ── Step 1: Free-text task description ─────────────────────


@router.message(SalesFunnel.custom_step_1, F.text)
async def step_1_text(message: Message, state: FSMContext) -> None:
    """Receive the task description, move to step 2."""
    if not message.from_user or not message.text:
        return

    db = await get_sales_db()
    await db.save_discovery_step(message.from_user.id, 1, message.text)
    await state.update_data(custom_task=message.text)

    await message.answer(CUSTOM_STEP_2_TEXT, reply_markup=custom_step_2_kb())
    await state.set_state(SalesFunnel.custom_step_2)


# ── Step 2: Volume ─────────────────────────────────────────


@router.callback_query(F.data.startswith("sales:cv_"))
async def step_2_volume(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle volume selection, move to step 3."""
    if not callback.data or not callback.from_user:
        return

    volume = callback.data.replace("sales:cv_", "")
    db = await get_sales_db()
    await db.save_discovery_step(callback.from_user.id, 2, volume)
    await state.update_data(custom_volume=volume, custom_integrations=set())

    if callback.message:
        await callback.message.edit_text(
            CUSTOM_STEP_3_TEXT,
            reply_markup=custom_step_3_kb(),
        )
    await state.set_state(SalesFunnel.custom_step_3)
    await callback.answer()


# ── Step 3: Integrations (multi-select) ────────────────────


@router.callback_query(F.data.startswith("sales:ci_"))
async def step_3_integration_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    """Toggle an integration option or finalize."""
    if not callback.data or not callback.from_user:
        return

    action = callback.data.replace("sales:ci_", "")

    if action == "done":
        # Finalize integrations and move to step 4
        data = await state.get_data()
        selected = data.get("custom_integrations", set())
        if isinstance(selected, list):
            selected = set(selected)

        db = await get_sales_db()
        await db.save_discovery_step(callback.from_user.id, 3, json.dumps(list(selected)))

        if callback.message:
            await callback.message.edit_text(
                CUSTOM_STEP_4_TEXT,
                reply_markup=custom_step_4_kb(),
            )
        await state.set_state(SalesFunnel.custom_step_4)
        await callback.answer()
        return

    # Toggle the integration
    data = await state.get_data()
    selected = set(data.get("custom_integrations", []))

    if action == "int_none":
        selected = {"int_none"}
    elif "int_none" in selected:
        selected.discard("int_none")
        selected.add(action)
    elif action in selected:
        selected.discard(action)
    else:
        selected.add(action)

    await state.update_data(custom_integrations=list(selected))

    if callback.message:
        await callback.message.edit_text(
            CUSTOM_STEP_3_TEXT,
            reply_markup=custom_step_3_kb(selected),
        )
    await callback.answer()


# ── Step 4: Timeline ───────────────────────────────────────


@router.callback_query(F.data.startswith("sales:ct_"))
async def step_4_timeline(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle timeline selection, move to step 5."""
    if not callback.data or not callback.from_user:
        return

    timeline = callback.data.replace("sales:ct_", "")
    db = await get_sales_db()
    await db.save_discovery_step(callback.from_user.id, 4, timeline)
    await state.update_data(custom_timeline=timeline)

    if callback.message:
        await callback.message.edit_text(
            CUSTOM_STEP_5_TEXT,
            reply_markup=custom_step_5_kb(),
        )
    await state.set_state(SalesFunnel.custom_step_5)
    await callback.answer()


# ── Step 5: Budget ─────────────────────────────────────────


@router.callback_query(F.data.startswith("sales:cb_"))
async def step_5_budget(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle budget selection, generate and show quote."""
    if not callback.data or not callback.from_user:
        return

    budget = callback.data.replace("sales:cb_", "")
    user_id = callback.from_user.id

    db = await get_sales_db()
    await db.save_discovery_step(user_id, 5, budget)
    await db.log_event(user_id, "custom_discovery_completed")

    data = await state.get_data()

    # Build discovery dict for quote calculation
    discovery = {
        "step_1_task": data.get("custom_task", "Не указана"),
        "step_2_volume": data.get("custom_volume", "vol_unknown"),
        "step_3_integrations": list(data.get("custom_integrations", [])),
        "step_4_timeline": data.get("custom_timeline", "time_research"),
        "step_5_budget": budget,
    }

    quote = calculate_quote(discovery)

    # Format volume label
    volume_labels = {
        "vol_low": "До 50/день",
        "vol_mid": "50-200/день",
        "vol_high": "200-1000/день",
        "vol_enterprise": "1000+/день",
        "vol_unknown": "Не определён",
    }
    volume_text = volume_labels.get(discovery["step_2_volume"], "Не указан")

    # Format integrations label
    int_list = discovery["step_3_integrations"]
    if not int_list or "int_none" in int_list:
        int_text = "Не нужны"
    else:
        int_names = []
        for k in int_list:
            if k in INTEGRATION_PRICES:
                int_names.append(INTEGRATION_PRICES[k][0])
        int_text = ", ".join(int_names) if int_names else "Не указаны"

    # Format price breakdown
    breakdown_lines = []
    for name, price in quote["items"]:
        breakdown_lines.append(f"  {name}: {price:,}₽")
    price_breakdown = "\n".join(breakdown_lines)

    # Truncate task for display
    task_display = discovery["step_1_task"]
    if len(task_display) > 60:
        task_display = task_display[:57] + "..."

    text = CUSTOM_QUOTE_TEXT.format(
        task=task_display,
        volume=volume_text,
        integrations=int_text,
        timeline=quote["timeline"],
        price_breakdown=price_breakdown,
        total_min=quote["total_min"],
        total_max=quote["total_max"],
    )

    if callback.message:
        await callback.message.edit_text(text, reply_markup=custom_quote_kb())
    await state.set_state(SalesFunnel.custom_quote)
    await callback.answer()


# ── Objection: "Too expensive" ─────────────────────────────


@router.callback_query(F.data == "sales:custom_expensive")
async def custom_expensive(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle 'too expensive' objection."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "objection_expensive")

    if callback.message:
        await callback.message.edit_text(
            CUSTOM_EXPENSIVE_TEXT,
            reply_markup=custom_expensive_kb(),
        )
    await state.set_state(SalesFunnel.custom_expensive)
    await callback.answer()


@router.callback_query(F.data.startswith("sales:ce_"))
async def expensive_option(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle cheaper alternative selection."""
    if not callback.data or not callback.from_user:
        return

    option = callback.data.replace("sales:ce_", "")
    db = await get_sales_db()
    await db.log_event(callback.from_user.id, "expensive_option", {"option": option})

    if option == "diy":
        # Redirect to DIY GitHub
        from .diy import enter_diy_path

        await enter_diy_path(callback, state)
    else:
        # MVP and stages — show contact
        if callback.message:
            await callback.message.edit_text(
                f"{'1️⃣ MVP-версия' if option == 'mvp' else '2️⃣ Поэтапное внедрение'}\n\n"
                "Отличный выбор! Давайте обсудим детали.\n\n" + CONTACT_TEXT,
                reply_markup=contact_kb(),
            )
        await state.set_state(SalesFunnel.idle)

    await callback.answer()


@router.callback_query(F.data == "sales:custom_restart")
async def custom_restart(callback: CallbackQuery, state: FSMContext) -> None:
    """Restart the custom discovery from step 1."""
    if callback.message:
        await callback.message.edit_text(CUSTOM_STEP_1_TEXT)
    await state.set_state(SalesFunnel.custom_step_1)
    await callback.answer()
