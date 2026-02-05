"""Segmentation quiz handlers (2 questions)."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from ...sales.database import get_sales_db
from ...sales.keyboards import quiz_infra_kb, quiz_tech_kb
from ...sales.segments import UserSegment, determine_segment
from ...sales.states import SalesFunnel
from ...sales.texts import QUIZ_INFRA_TEXT, QUIZ_TECH_TEXT


logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "sales:start_quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    """Begin the segmentation quiz — question 1."""
    if not callback.from_user:
        return

    db = await get_sales_db()
    await db.log_event(callback.from_user.id, "quiz_started")

    if callback.message:
        await callback.message.edit_text(
            QUIZ_TECH_TEXT,
            reply_markup=quiz_tech_kb(),
        )
    await state.set_state(SalesFunnel.quiz_tech)
    await callback.answer()


@router.callback_query(F.data.startswith("sales:qt_"))
async def quiz_tech_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle answer to Q1 (tech level), show Q2."""
    if not callback.data:
        return

    tech = callback.data.replace("sales:qt_", "")  # diy | ready | business
    await state.update_data(quiz_tech=tech)

    if callback.message:
        await callback.message.edit_text(
            QUIZ_INFRA_TEXT,
            reply_markup=quiz_infra_kb(),
        )
    await state.set_state(SalesFunnel.quiz_infra)
    await callback.answer()


@router.callback_query(F.data.startswith("sales:qi_"))
async def quiz_infra_answer(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle answer to Q2 (infrastructure), route to path."""
    if not callback.data or not callback.from_user:
        return

    infra = callback.data.replace("sales:qi_", "")  # gpu | cpu | none | unknown
    data = await state.get_data()
    tech = data.get("quiz_tech", "ready")

    segment, sub_segment = determine_segment(tech, infra)

    # Persist to DB
    user_id = callback.from_user.id
    db = await get_sales_db()
    await db.update_user(
        user_id,
        segment=segment.value,
        quiz_tech=tech,
        quiz_infra=infra,
        sub_segment=sub_segment,
    )
    await db.log_event(
        user_id,
        "quiz_completed",
        {
            "tech": tech,
            "infra": infra,
            "segment": segment.value,
            "sub_segment": sub_segment,
        },
    )

    await state.update_data(
        quiz_infra=infra,
        segment=segment.value,
        sub_segment=sub_segment,
    )

    # Route to the appropriate path
    if segment == UserSegment.DIY:
        from .diy import enter_diy_path

        await enter_diy_path(callback, state)
    elif segment == UserSegment.BASIC:
        from .basic import enter_basic_path

        await enter_basic_path(callback, state)
    else:
        from .custom import enter_custom_path

        await enter_custom_path(callback, state)

    await callback.answer()
