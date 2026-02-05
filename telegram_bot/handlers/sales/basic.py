"""Basic path handlers — for users who want a ready-made solution."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from ...sales.database import get_sales_db
from ...sales.keyboards import (
    basic_checkout_kb,
    basic_demo_kb,
    basic_no_gpu_kb,
    basic_value_kb,
)
from ...sales.states import SalesFunnel
from ...sales.texts import (
    BASIC_CHECKOUT_TEXT,
    BASIC_DEMO_TEXT,
    BASIC_NO_GPU_TEXT,
    BASIC_VALUE_TEXT,
)


logger = logging.getLogger(__name__)
router = Router()


async def enter_basic_path(callback: CallbackQuery, state: FSMContext) -> None:
    """Entry point into the Basic path from quiz."""
    first_name = "друг"
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "basic_path_entered")
        await db.log_event(callback.from_user.id, "value_shown")
        first_name = callback.from_user.first_name or "друг"

    # Store name in state for later use
    await state.update_data(user_name=first_name)

    if callback.message:
        await callback.message.edit_text(
            BASIC_VALUE_TEXT.format(name=first_name),
            reply_markup=basic_value_kb(),
        )
    await state.set_state(SalesFunnel.basic_value)


@router.callback_query(F.data == "sales:basic_demo")
async def basic_demo(callback: CallbackQuery, state: FSMContext) -> None:
    """Show demo screen."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "demo_viewed")

    if callback.message:
        await callback.message.edit_text(
            BASIC_DEMO_TEXT,
            reply_markup=basic_demo_kb(),
        )
    await state.set_state(SalesFunnel.basic_demo)
    await callback.answer()


@router.callback_query(F.data == "sales:basic_back_value")
async def basic_back_value(callback: CallbackQuery, state: FSMContext) -> None:
    """Back to ROI value screen."""
    # Get name from state or user
    data = await state.get_data()
    first_name = data.get("user_name", "друг")
    if not first_name and callback.from_user:
        first_name = callback.from_user.first_name or "друг"

    if callback.message:
        await callback.message.edit_text(
            BASIC_VALUE_TEXT.format(name=first_name),
            reply_markup=basic_value_kb(),
        )
    await state.set_state(SalesFunnel.basic_value)
    await callback.answer()


@router.callback_query(F.data == "sales:basic_checkout")
async def basic_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Show checkout screen."""
    await _show_checkout(callback, state)
    await callback.answer()


async def _show_checkout(callback: CallbackQuery, state: FSMContext) -> None:
    """Display the checkout screen (shared with DIY redirect)."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "checkout_started")

    if callback.message:
        await callback.message.edit_text(
            BASIC_CHECKOUT_TEXT,
            reply_markup=basic_checkout_kb(),
        )
    await state.set_state(SalesFunnel.basic_checkout)


@router.callback_query(F.data == "sales:basic_no_gpu")
async def basic_no_gpu(callback: CallbackQuery, state: FSMContext) -> None:
    """Show 'no GPU' options."""
    if callback.message:
        await callback.message.edit_text(
            BASIC_NO_GPU_TEXT,
            reply_markup=basic_no_gpu_kb(),
        )
    await state.set_state(SalesFunnel.basic_no_gpu)
    await callback.answer()


@router.callback_query(F.data.startswith("sales:nogpu_"))
async def no_gpu_option(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle no-GPU option selection — redirect to checkout or contact."""
    option = callback.data.replace("sales:nogpu_", "") if callback.data else ""

    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "nogpu_selected", {"option": option})

    if option == "cpu":
        # CPU mode is free, redirect to GitHub
        from .diy import enter_diy_path

        await enter_diy_path(callback, state)
    else:
        # VPS or own server — redirect to checkout
        await _show_checkout(callback, state)

    await callback.answer()
