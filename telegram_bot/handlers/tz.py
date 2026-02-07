"""TZ (Technical Specification) handlers — quiz and document generation."""

import json
import logging
from datetime import datetime

import httpx
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from ..config import get_telegram_settings
from ..sales.database import get_sales_db
from ..sales.keyboards import (
    tz_budget_kb,
    tz_business_goal_kb,
    tz_project_type_kb,
    tz_result_kb,
    tz_timeline_kb,
    tz_unqualified_kb,
)
from ..sales.states import SalesFunnel
from ..services.llm_router import get_llm_router


logger = logging.getLogger(__name__)
router = Router()

# 20 MB limit (Telegram Bot API file download limit)
MAX_FILE_SIZE = 20 * 1024 * 1024


async def _upload_tg_file(message: Message, file_id: str, filename: str, mime: str) -> dict:
    """Download file from Telegram and upload to bridge, return file metadata."""
    settings = get_telegram_settings()
    tg_file = await message.bot.get_file(file_id)
    bio = await message.bot.download_file(tg_file.file_path)
    file_bytes = bio.read()

    headers = {}
    if settings.bridge_api_key:
        headers["Authorization"] = f"Bearer {settings.bridge_api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.bridge_url}/v1/files",
            headers=headers,
            files={"file": (filename, file_bytes, mime)},
            data={"purpose": "assistants"},
        )
        resp.raise_for_status()
        result = resp.json()

    return {"file_id": result["id"], "filename": filename, "mime": mime}


# TZ generation prompt template
TZ_SYSTEM_PROMPT = """Ты — опытный системный аналитик и технический лид.
Твоя задача — создать техническое задание (ТЗ) на основе собранных требований.

## ВАЖНЫЕ ПРАВИЛА:

1. **Спринт = 1 неделя (5 рабочих дней) = 50,000₽**
2. **Минимальный заказ = 1 спринт (50,000₽)**
3. Количество спринтов не ограничено — сколько нужно для проекта
4. Каждый спринт должен давать работающий инкремент
5. Если проект занимает меньше 5 рабочих дней — это НЕ наш клиент

## КВАЛИФИКАЦИЯ ЛИДА:

Если задача слишком мелкая (меньше недели работы), вежливо откажи:
- Предложи самостоятельное решение (GitHub, документация)
- Или порекомендуй фрилансера на разовую задачу
- Мы работаем только с проектами от 50,000₽

## Формат ответа (СТРОГО):

# 🎯 ТЕХНИЧЕСКОЕ ЗАДАНИЕ

## 1. Описание проекта
[Краткое описание на основе данных клиента]

## 2. Бизнес-цели
[На основе выбранной цели]

## 3. Функциональные требования
[Детализированный список функций на основе описания]

## 4. Нефункциональные требования
- Производительность
- Безопасность
- Масштабируемость

## 5. Технический стек (рекомендация)
[Исходя из типа проекта]

---

# ⚡ ПЛАН РЕАЛИЗАЦИИ

Создай столько спринтов, сколько реально нужно для проекта.
Каждый спринт = 1 неделя = 5 рабочих дней = 50,000₽.

## Спринт 1 (неделя 1) — [Название этапа]
[3-5 конкретных задач с оценкой в днях]
- Задача 1 (1 день)
- Задача 2 (2 дня)
- ...
**Итого:** 5 дней | **Стоимость:** 50,000₽

## Спринт 2 (неделя 2) — [Название этапа]
[3-5 конкретных задач]
**Итого:** 5 дней | **Стоимость:** 50,000₽

[...продолжай пока не опишешь весь скоуп проекта...]

---

# 📊 ОЦЕНКА ПРОЕКТА

| Параметр | Значение |
|----------|----------|
| Количество спринтов | X |
| Общий срок | X недель |
| Базовая стоимость | X₽ |
| Риск-буфер (20%) | X₽ |
| **ИТОГО** | **X₽** |

---

# 💳 УСЛОВИЯ РАБОТЫ

- **Оплата:** поспринтовая (50,000₽ за спринт)
- **Первый платёж:** 50,000₽ (запуск MVP)
- **Демо:** после каждого спринта
- **Правки:** включены в стоимость спринта
- **Гарантия:** возврат если не устроит качество

💡 **Следующий шаг:** Оплатите первый спринт (50,000₽), чтобы начать разработку.
"""

# Response for unqualified leads (projects < 1 week)
TZ_UNQUALIFIED_RESPONSE = """
❌ **Проект слишком мал для нашего формата**

Судя по описанию, задача займёт меньше недели работы.

**Мы работаем с проектами от 50,000₽** (1 неделя = 5 рабочих дней).

**Альтернативы для вас:**

1. **Самостоятельно** — наш проект на GitHub бесплатный:
   🔗 github.com/ShaerWare/AI_Secretary_System

2. **Фрилансер** — для разовых задач рекомендуем:
   • Kwork.ru
   • Habr Freelance
   • FL.ru

3. **Базовая установка за 5,000₽** — если нужна только установка AI Secretary без кастомизации

Если у вас более масштабный проект — опишите подробнее!
"""


def _format_tz_data(data: dict) -> str:
    """Format collected TZ data for AI prompt."""
    project_types = {
        "chatbot": "AI-ассистент / Чат-бот",
        "voice": "Голосовой бот / Телефония",
        "integration": "Интеграция с CRM/1С",
        "web": "Веб-приложение / SaaS",
        "telegram": "Telegram-бот",
        "other": "Другое",
    }

    goals = {
        "cost": "Снизить расходы на персонал",
        "sales": "Увеличить продажи",
        "automation": "Автоматизировать рутину",
        "service": "Улучшить клиентский сервис",
        "scale": "Масштабировать бизнес",
    }

    timelines = {
        "urgent": "Срочно (1-2 недели)",
        "month": "В течение месяца",
        "quarter": "В течение квартала",
        "research": "Пока изучаю варианты",
    }

    budgets = {
        "50": "50-100К₽",
        "100": "100-200К₽",
        "200": "200-500К₽",
        "500": "500К₽+",
        "calculate": "Нужен расчёт",
    }

    return f"""
## Собранные требования:

**Тип проекта:** {project_types.get(data.get("project_type", ""), "Не указан")}

**Описание проекта:**
{data.get("project_desc", "Не указано")}

**Бизнес-цель:** {goals.get(data.get("business_goal", ""), "Не указана")}

**Ключевые функции:**
{data.get("features", "Не указаны")}

**Сроки:** {timelines.get(data.get("timeline", ""), "Не указаны")}

**Бюджет:** {budgets.get(data.get("budget", ""), "Не указан")}

**Контакт:** {data.get("contact", "Не указан")}
"""


# ── Entry Point ────────────────────────────────────────────


@router.message(F.text == "📋 Рассчитать заказ")
async def start_tz_quiz(message: Message, state: FSMContext) -> None:
    """Start TZ quiz from reply keyboard button."""
    if not message.from_user:
        return

    db = await get_sales_db()
    await db.log_event(message.from_user.id, "tz_started")

    # Clear any previous TZ data
    await state.update_data(tz_data={})
    await state.set_state(SalesFunnel.tz_project_type)

    name = message.from_user.first_name or "друг"

    await message.answer(
        f"📋 **Расчёт заказа**\n\n"
        f"Привет, {name}! Я помогу составить техническое задание "
        f"и рассчитать стоимость проекта.\n\n"
        f"Это займёт ~2 минуты. В конце вы получите:\n"
        f"• 📄 Готовое ТЗ\n"
        f"• ⚡ Разбивку на спринты\n"
        f"• 💰 Предварительную оценку\n\n"
        f"**Шаг 1/6:** Какой тип проекта вас интересует?",
        reply_markup=tz_project_type_kb(),
    )


@router.message(Command("tz"))
async def cmd_tz(message: Message, state: FSMContext) -> None:
    """Handle /tz command."""
    await start_tz_quiz(message, state)


# ── Step 1: Project Type ────────────────────────────────────────────


@router.callback_query(F.data.startswith("tz:type_"))
async def tz_project_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle project type selection."""
    project_type = callback.data.split("_", 1)[1]

    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    tz_data["project_type"] = project_type
    await state.update_data(tz_data=tz_data)

    await callback.answer()

    if project_type == "other":
        await state.set_state(SalesFunnel.tz_project_desc)
        if callback.message:
            await callback.message.edit_text(
                "📋 **Шаг 2/6:** Опишите ваш проект\n\n"
                "Напишите свободным текстом:\n"
                "• Что должна делать система?\n"
                "• Какую проблему решает?\n"
                "• Кто будет пользоваться?"
            )
    else:
        await state.set_state(SalesFunnel.tz_project_desc)
        if callback.message:
            await callback.message.edit_text(
                "📋 **Шаг 2/6:** Опишите детали проекта\n\n"
                "Напишите свободным текстом:\n"
                "• Что конкретно должна делать система?\n"
                "• Какие основные сценарии использования?\n"
                "• Есть ли примеры или референсы?"
            )


# ── Step 2: Project Description (free text) ────────────────────────────────


@router.message(SalesFunnel.tz_project_desc)
async def tz_project_desc(message: Message, state: FSMContext) -> None:
    """Handle project description input (text, photo, or document)."""
    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    files = tz_data.get("files", [])
    text = None

    if message.text:
        text = message.text
    elif message.photo:
        photo = message.photo[-1]  # largest resolution
        try:
            meta = await _upload_tg_file(message, photo.file_id, "photo.jpg", "image/jpeg")
            files.append(meta)
            text = message.caption or ""
            await message.answer("📎 Фото принято!")
        except Exception:
            logger.exception("Failed to upload photo in TZ step 2")
            await message.answer("Не удалось загрузить фото, попробуйте ещё раз.")
            return
    elif message.document:
        doc = message.document
        if doc.file_size and doc.file_size > MAX_FILE_SIZE:
            await message.answer("Файл слишком большой (макс. 20 МБ).")
            return
        try:
            meta = await _upload_tg_file(
                message,
                doc.file_id,
                doc.file_name or "document",
                doc.mime_type or "application/octet-stream",
            )
            files.append(meta)
            text = message.caption or ""
            await message.answer("📎 Документ принят!")
        except Exception:
            logger.exception("Failed to upload document in TZ step 2")
            await message.answer("Не удалось загрузить файл, попробуйте ещё раз.")
            return
    else:
        await message.answer("Отправьте текст, фото или документ.")
        return

    tz_data["project_desc"] = text
    tz_data["files"] = files
    await state.update_data(tz_data=tz_data)

    await state.set_state(SalesFunnel.tz_business_goal)

    await message.answer(
        "📋 **Шаг 3/6:** Какая главная бизнес-цель?",
        reply_markup=tz_business_goal_kb(),
    )


# ── Step 3: Business Goal ────────────────────────────────────────────


@router.callback_query(F.data.startswith("tz:goal_"))
async def tz_business_goal(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle business goal selection."""
    goal = callback.data.split("_", 1)[1]

    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    tz_data["business_goal"] = goal
    await state.update_data(tz_data=tz_data)

    await callback.answer()
    await state.set_state(SalesFunnel.tz_features)

    if callback.message:
        await callback.message.edit_text(
            "📋 **Шаг 4/6:** Опишите ключевые функции\n\n"
            "Перечислите основные возможности, которые должны быть:\n"
            "• Какие действия пользователь должен выполнять?\n"
            "• С какими системами нужна интеграция?\n"
            "• Какие отчёты/уведомления нужны?"
        )


# ── Step 4: Features (free text) ────────────────────────────────────────────


@router.message(SalesFunnel.tz_features)
async def tz_features(message: Message, state: FSMContext) -> None:
    """Handle features description input (text, photo, or document)."""
    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    files = tz_data.get("files", [])
    text = None

    if message.text:
        text = message.text
    elif message.photo:
        photo = message.photo[-1]
        try:
            meta = await _upload_tg_file(message, photo.file_id, "photo.jpg", "image/jpeg")
            files.append(meta)
            text = message.caption or ""
            await message.answer("📎 Фото принято!")
        except Exception:
            logger.exception("Failed to upload photo in TZ step 4")
            await message.answer("Не удалось загрузить фото, попробуйте ещё раз.")
            return
    elif message.document:
        doc = message.document
        if doc.file_size and doc.file_size > MAX_FILE_SIZE:
            await message.answer("Файл слишком большой (макс. 20 МБ).")
            return
        try:
            meta = await _upload_tg_file(
                message,
                doc.file_id,
                doc.file_name or "document",
                doc.mime_type or "application/octet-stream",
            )
            files.append(meta)
            text = message.caption or ""
            await message.answer("📎 Документ принят!")
        except Exception:
            logger.exception("Failed to upload document in TZ step 4")
            await message.answer("Не удалось загрузить файл, попробуйте ещё раз.")
            return
    else:
        await message.answer("Отправьте текст, фото или документ.")
        return

    tz_data["features"] = text
    tz_data["files"] = files
    await state.update_data(tz_data=tz_data)

    await state.set_state(SalesFunnel.tz_timeline)

    await message.answer(
        "📋 **Шаг 5/6:** В какие сроки нужен проект?",
        reply_markup=tz_timeline_kb(),
    )


# ── Step 5: Timeline ────────────────────────────────────────────


@router.callback_query(F.data.startswith("tz:time_"))
async def tz_timeline(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle timeline selection."""
    timeline = callback.data.split("_", 1)[1]

    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    tz_data["timeline"] = timeline
    await state.update_data(tz_data=tz_data)

    await callback.answer()
    await state.set_state(SalesFunnel.tz_budget)

    if callback.message:
        await callback.message.edit_text(
            "📋 **Шаг 6/6:** Какой бюджет вы рассматриваете?",
            reply_markup=tz_budget_kb(),
        )


# ── Step 6: Budget ────────────────────────────────────────────


@router.callback_query(F.data.startswith("tz:budget_"))
async def tz_budget(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle budget selection and start TZ generation."""
    budget = callback.data.split("_", 1)[1]

    data = await state.get_data()
    tz_data = data.get("tz_data", {})
    tz_data["budget"] = budget
    await state.update_data(tz_data=tz_data)

    await callback.answer("⏳ Генерирую ТЗ...")

    if callback.message:
        await callback.message.edit_text(
            "⏳ **Генерирую техническое задание...**\n\n"
            "Анализирую требования и составляю план работ.\n"
            "Это займёт около минуты."
        )

    await state.set_state(SalesFunnel.tz_generating)

    # Generate TZ
    try:
        tz_document = await _generate_tz(tz_data)

        # Save to database
        if callback.from_user:
            db = await get_sales_db()
            await db.log_event(
                callback.from_user.id,
                "tz_generated",
                tz_data,
            )

        await state.set_state(SalesFunnel.tz_result)

        # Check if it's an unqualified lead (project too small)
        is_unqualified = (
            "❌ **Проект слишком мал" in tz_document or "слишком мал" in tz_document.lower()
        )

        # Choose appropriate keyboard
        result_kb = tz_unqualified_kb() if is_unqualified else tz_result_kb()

        # Log qualification status
        if callback.from_user:
            await db.log_event(
                callback.from_user.id,
                "tz_qualified" if not is_unqualified else "tz_unqualified",
            )

        # Send TZ document
        if callback.message:
            # Split if too long (Telegram limit is 4096)
            if len(tz_document) > 4000:
                parts = [tz_document[i : i + 4000] for i in range(0, len(tz_document), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        await callback.message.answer(part, reply_markup=result_kb)
                    else:
                        await callback.message.answer(part)
            else:
                await callback.message.answer(tz_document, reply_markup=result_kb)

    except Exception as e:
        logger.error(f"Failed to generate TZ: {e}")
        if callback.message:
            await callback.message.answer(
                "❌ Не удалось сгенерировать ТЗ.\n\n"
                "Попробуйте ещё раз или свяжитесь с менеджером: @ShaerWare",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔄 Попробовать снова",
                                callback_data="tz:restart",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="📞 Связаться с менеджером",
                                url="https://t.me/ShaerWare",
                            )
                        ],
                    ]
                ),
            )


async def _generate_tz(tz_data: dict) -> str:
    """
    Generate TZ document using Claude (requires complex reasoning).

    TZ generation is one of the few places where Claude is used
    because it requires sophisticated document structuring and
    business analysis capabilities.

    When files are attached, calls the bridge directly with multipart
    content (the orchestrator chat API only supports plain text).
    """
    user_text = f"""Проанализируй требования и создай техническое задание:

{_format_tz_data(tz_data)}

## ВАЖНО — КВАЛИФИКАЦИЯ ЛИДА:

1. **Оцени объём работы** по описанию
2. Если проект займёт **МЕНЬШЕ 5 рабочих дней** (1 недели):
   - Начни ответ с "❌ **Проект слишком мал"
   - Вежливо откажи и предложи альтернативы (GitHub, фрилансеры, базовая установка 5К)
   - НЕ генерируй ТЗ для мелких задач

3. Если проект займёт **5+ рабочих дней**:
   - Создай полное ТЗ по формату из системного промта
   - Разбей на спринты (1 спринт = 1 неделя = 5 дней = 50,000₽)
   - Спринтов может быть сколько угодно — сколько нужно для проекта
   - Каждая задача с оценкой в днях (1-3 дня на задачу)

Будь реалистичен в оценках. Лучше переоценить чем недооценить.
"""

    files = tz_data.get("files", [])
    if files:
        # Call bridge directly with multipart content (files + text)
        return await _generate_tz_with_files(user_text, files)

    # Use Claude via LLM Router (text-only, existing path)
    llm_router = get_llm_router()
    return await llm_router.generate_tz(TZ_SYSTEM_PROMPT, user_text)


async def _generate_tz_with_files(user_text: str, files: list[dict]) -> str:
    """Generate TZ via bridge directly, with file references in the message."""
    settings = get_telegram_settings()

    content_parts: list[dict] = [{"type": "file", "file_id": f["file_id"]} for f in files]
    content_parts.append({"type": "text", "text": user_text})

    messages = [
        {"role": "system", "content": TZ_SYSTEM_PROMPT},
        {"role": "user", "content": content_parts},
    ]

    headers = {"Content-Type": "application/json"}
    if settings.bridge_api_key:
        headers["Authorization"] = f"Bearer {settings.bridge_api_key}"

    payload = {
        "model": "sonnet",
        "messages": messages,
        "stream": True,
    }

    full_text = ""
    async with (
        httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client,
        client.stream(
            "POST",
            f"{settings.bridge_url}/v1/chat/completions",
            headers=headers,
            json=payload,
        ) as resp,
    ):
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                if data.get("choices"):
                    delta = data["choices"][0].get("delta", {})
                    if content := delta.get("content"):
                        full_text += content
            except json.JSONDecodeError:
                pass

    return full_text.strip()


# ── Result Actions ────────────────────────────────────────────


@router.callback_query(F.data == "tz:pay_sprint")
async def tz_pay_sprint(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle payment for first sprint."""
    if callback.from_user:
        db = await get_sales_db()
        await db.log_event(callback.from_user.id, "tz_pay_clicked")

    await callback.answer()

    # Try to send invoice
    from aiogram.types import LabeledPrice

    from ..config import get_telegram_settings

    settings = get_telegram_settings()

    if settings.payment_provider_token and callback.message:
        try:
            await callback.message.answer_invoice(
                title="Первый спринт — MVP",
                description=(
                    "Разработка MVP по вашему ТЗ:\n"
                    "✅ Неделя работы\n"
                    "✅ Базовый функционал\n"
                    "✅ Демо для проверки\n"
                    "✅ Исходный код"
                ),
                payload=f"tz_sprint1_{callback.from_user.id}_{datetime.now().strftime('%Y%m%d')}",
                provider_token=settings.payment_provider_token,
                currency=settings.payment_currency,
                prices=[LabeledPrice(label="Спринт 1 (MVP)", amount=5000000)],  # 50,000₽
                need_name=True,
                need_phone_number=True,
                need_email=True,
            )
            return
        except Exception as e:
            logger.error(f"Failed to send TZ sprint invoice: {e}")

    # Fallback to contact
    if callback.message:
        await callback.message.answer(
            "💳 **Оплата первого спринта — 50,000₽**\n\n"
            "Для оплаты свяжитесь с нами:\n\n"
            "📱 Telegram: @ShaerWare\n\n"
            "После оплаты начнём работу над MVP в течение 24 часов.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📞 Написать менеджеру",
                            url="https://t.me/ShaerWare",
                        )
                    ],
                ]
            ),
        )


@router.callback_query(F.data == "tz:restart")
async def tz_restart(callback: CallbackQuery, state: FSMContext) -> None:
    """Restart TZ quiz."""
    await callback.answer()

    # Clear TZ data
    await state.update_data(tz_data={})
    await state.set_state(SalesFunnel.tz_project_type)

    if callback.message:
        await callback.message.answer(
            "📋 **Давайте начнём заново**\n\n**Шаг 1/6:** Какой тип проекта вас интересует?",
            reply_markup=tz_project_type_kb(),
        )
