"""DIY path handlers — for technical users who want to self-install."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from ...sales.database import get_sales_db
from ...sales.keyboards import diy_audit_result_kb, diy_github_kb, diy_gpu_kb
from ...sales.segments import get_gpu_audit
from ...sales.states import SalesFunnel
from ...sales.texts import (
    DIY_AUDIT_CUSTOM_TEXT,
    DIY_AUDIT_RESULT_TEXT,
    DIY_AUDIT_TEXT,
    DIY_AUDIT_UNKNOWN_TEXT,
    DIY_GITHUB_TEXT,
)


logger = logging.getLogger(__name__)
router = Router()


async def enter_diy_path(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry point into the DIY path from quiz."""
    first_name = "друг"
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "diy_path_entered")
        first_name = callback.from_user.first_name or "друг"

    if callback.message:
        await callback.message.edit_text(
            DIY_AUDIT_TEXT.format(name=first_name),
            reply_markup=diy_gpu_kb(),
        )
    await state.set_state(SalesFunnel.diy_audit)


@router.callback_query(F.data.startswith("sales:gpu_"))
async def gpu_selected(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle GPU selection."""
    if not callback.data or not callback.from_user:
        return

    gpu_key = callback.data.replace("sales:gpu_", "")

    if gpu_key == "other":
        # Ask for free-text GPU input
        if callback.message:
            await callback.message.edit_text(DIY_AUDIT_CUSTOM_TEXT)
        await state.set_state(SalesFunnel.diy_audit_custom)
        await callback.answer()
        return

    audit = get_gpu_audit(gpu_key)
    if not audit:
        if callback.message:
            await callback.message.edit_text(
                DIY_AUDIT_UNKNOWN_TEXT,
                reply_markup=diy_gpu_kb(),
            )
        await callback.answer()
        return

    db = await get_sales_db()
    await db.log_event(callback.from_user.id, "diy_audit", {"gpu": gpu_key})

    stars = "⭐" * audit["quality"]
    text = DIY_AUDIT_RESULT_TEXT.format(
        gpu_name=audit["name"],
        llm=audit["llm"],
        stars=stars,
        speed=audit["speed"],
        hint=audit["hint"],
    )
    if callback.message:
        await callback.message.edit_text(text, reply_markup=diy_audit_result_kb())
    await state.set_state(SalesFunnel.diy_result)
    await callback.answer()


@router.message(SalesFunnel.diy_audit_custom, F.text)
async def gpu_custom_text(message: Message, state: FSMContext) -> None:
    """Handle free-text GPU model input."""
    if not message.from_user or not message.text:
        return

    db = await get_sales_db()
    await db.log_event(message.from_user.id, "diy_audit_custom", {"gpu": message.text})

    # For custom GPU we show a generic recommendation
    text = (
        f"🔍 Аудит: {message.text}\n\n"
        "Система автоматически определит оптимальные настройки "
        "при установке.\n\n"
        "Рекомендуем начать с установки — если VRAM >= 6GB, "
        "базовая конфигурация будет работать.\n\n"
        "Готовы к установке?"
    )
    await message.answer(text, reply_markup=diy_audit_result_kb())
    await state.set_state(SalesFunnel.diy_result)


@router.callback_query(F.data == "sales:diy_github")
async def diy_github(callback: CallbackQuery, state: FSMContext) -> None:
    """Show GitHub CTA."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "cta_clicked", {"cta": "github"})

    if callback.message:
        await callback.message.edit_text(
            DIY_GITHUB_TEXT,
            reply_markup=diy_github_kb(),
        )
    await state.set_state(SalesFunnel.diy_github)
    await callback.answer()


@router.callback_query(F.data == "sales:diy_install_5k")
async def diy_install_redirect(callback: CallbackQuery, state: FSMContext) -> None:
    """DIY user wants paid installation — redirect to Basic checkout."""
    from .basic import _show_checkout

    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "cta_clicked", {"cta": "install_5k"})

    await _show_checkout(callback, state)
    await callback.answer()
