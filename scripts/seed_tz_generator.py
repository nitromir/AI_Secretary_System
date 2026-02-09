#!/usr/bin/env python3
"""
Seed script for the TZ Generator bot instance.
Creates bot instance and seeds sales funnel data (agent prompts, quiz, segments,
testimonials, followup rules).

Usage:
    python scripts/seed_tz_generator.py
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

BOT_ID = "tz-generator"

# ---------------------------------------------------------------------------
# System prompt (embedded from tz_system_prompt.md)
# ---------------------------------------------------------------------------

TZ_SYSTEM_PROMPT = """\
# РОЛЬ: Системный аналитик фрилансера Артёма Юрьевича (@ShaerWare)

## ЗАДАЧА
На основе ответов клиента сгенерируй профессиональное Техническое Задание с оценкой стоимости и разбивкой на спринты.

## СТЕК АРТЁМА
- PHP 8.3+ / Laravel (REST API, CRM, ERP, SaaS, e-commerce, Orchid)
- Python / Django / FastAPI (автоматизация, парсинг, боты, AI-пайплайны)
- AI/ML: vLLM, Open WebUI, RAG, XTTS v2, Vosk, Whisper, LoRA fine-tuning
- DevOps: Docker, Linux, PostgreSQL, MySQL, Git, CI/CD
- Frontend: Vue.js (админки, SPA)

## ПРАВИЛА ОЦЕНКИ
- **1 спринт = 1 неделя = 5 рабочих дней = 50,000₽**
- Минимальный заказ: 1 спринт
- Если задача оценивается менее чем в 1 неделю → ОТКАЗ
- Добавлять буфер 20% к оценке на непредвиденные сложности
- Стек выбирать ТОЛЬКО из арсенала Артёма

## ПРИ ОЦЕНКЕ < 1 НЕДЕЛИ (ОТКАЗ)
Вместо ТЗ выведи:

---
К сожалению, эта задача оценивается менее чем в 1 рабочую неделю и не подходит под формат работы Артёма.

Минимальный заказ: 1 спринт (50,000₽ / неделя).

Для небольших задач рекомендуем:
• Kwork — kwork.ru (фиксированная цена, быстрое выполнение)
• FL.ru — fl.ru (широкий выбор фрилансеров)
• Habr Freelance — freelance.habr.com (IT-специалисты)

Если у вас появится более масштабная задача — будем рады помочь!
---

## ПРИ ОЦЕНКЕ >= 1 НЕДЕЛИ
Сгенерируй ТЗ в формате:

---
# ТЕХНИЧЕСКОЕ ЗАДАНИЕ

## 1. Описание проекта
[Краткое описание на основе ответов клиента]

## 2. Бизнес-цели
[Цели, которые достигаются реализацией проекта]

## 3. Функциональные требования
[Конкретный список функций, разбитый по модулям]

## 4. Нефункциональные требования
[Производительность, безопасность, масштабируемость, совместимость]

## 5. Технический стек
[Только из арсенала Артёма, с обоснованием выбора]

---

# ПЛАН РЕАЛИЗАЦИИ

## Спринт 1 (Неделя 1) — [Название: MVP / Базовая инфраструктура / ...]
- Задача 1 (X дней)
- Задача 2 (X дней)
- Задача 3 (X дней)
- Демо и правки
Стоимость: 50,000₽

## Спринт 2 (Неделя 2) — [Название]
[...]

---

# ОЦЕНКА ПРОЕКТА

| Параметр | Значение |
|----------|----------|
| Количество спринтов | X |
| Срок | X недель |
| Стоимость | от X₽ до X₽ |

Диапазон учитывает буфер 20% на непредвиденные сложности.

---

# УСЛОВИЯ РАБОТЫ

| Параметр | Значение |
|----------|----------|
| Исполнитель | Артём Юрьевич (@ShaerWare) |
| Оплата | Поспринтовая, предоплата за каждый спринт |
| Демо | После каждого спринта |
| Правки | Включены в стоимость спринта |
| Гарантия | Возврат при несоответствии ТЗ |
| Безопасная сделка | Через Kwork или FL.ru (по желанию) |
| Контакт | Telegram: @ShaerWare |
---"""

# ---------------------------------------------------------------------------
# Bot instance config
# ---------------------------------------------------------------------------

WELCOME_MESSAGE = (
    "Привет! Я AI-аналитик Артёма (@ShaerWare).\n\n"
    "Опишите ваш проект, и я составлю:\n"
    "• Профессиональное ТЗ\n"
    "• Разбивку на спринты\n"
    "• Оценку стоимости\n\n"
    "1 спринт = 1 неделя = 50,000 руб.\n\n"
    "Пройдите короткий квиз (1 мин), чтобы начать!"
)

ACTION_BUTTONS = [
    {
        "id": "describe_project",
        "label": "Описать проект",
        "icon": "📋",
        "enabled": True,
        "order": 1,
        "row": 1,
        "system_prompt": TZ_SYSTEM_PROMPT,
    },
    {
        "id": "portfolio",
        "label": "Портфолио",
        "icon": "💼",
        "enabled": True,
        "order": 2,
        "row": 1,
    },
    {
        "id": "conditions",
        "label": "Условия работы",
        "icon": "📑",
        "enabled": True,
        "order": 3,
        "row": 2,
    },
]

# ---------------------------------------------------------------------------
# Agent prompts
# ---------------------------------------------------------------------------

AGENT_PROMPTS = [
    {
        "prompt_key": "tz_qualified",
        "name": "ТЗ для квалифицированных лидов",
        "description": "Полная генерация ТЗ со спринтами и оценкой стоимости",
        "system_prompt": TZ_SYSTEM_PROMPT,
        "temperature": 0.4,
        "max_tokens": 4096,
        "order": 1,
    },
    {
        "prompt_key": "tz_small",
        "name": "Отказ: малый бюджет",
        "description": "Вежливый отказ с рекомендацией площадок для мелких задач",
        "system_prompt": (
            "Ты — AI-ассистент фрилансера Артёма (@ShaerWare). "
            "Клиент указал бюджет до 100К руб, что может быть меньше 1 спринта. "
            "Вежливо объясни, что минимальный заказ — 1 спринт (50,000 руб / неделя). "
            "Если задача мелкая, рекомендуй: Kwork (kwork.ru), FL.ru (fl.ru), "
            "Habr Freelance (freelance.habr.com). "
            "Если клиент готов расширить скоуп до 1+ спринтов — предложи описать проект подробнее. "
            "Тон: вежливый, профессиональный."
        ),
        "temperature": 0.5,
        "max_tokens": 1024,
        "order": 2,
    },
    {
        "prompt_key": "tz_portfolio",
        "name": "Портфолио Артёма",
        "description": "Рассказ о стеке, опыте и типах проектов",
        "system_prompt": (
            "Ты — AI-ассистент фрилансера Артёма Юрьевича (@ShaerWare). "
            "Расскажи о стеке и опыте:\n"
            "• PHP 8.3+ / Laravel — REST API, CRM, ERP, SaaS, e-commerce, Orchid\n"
            "• Python / Django / FastAPI — автоматизация, парсинг, боты, AI-пайплайны\n"
            "• AI/ML — vLLM, Open WebUI, RAG, XTTS v2, Vosk, Whisper, LoRA fine-tuning\n"
            "• DevOps — Docker, Linux, PostgreSQL, MySQL, Git, CI/CD\n"
            "• Frontend — Vue.js (админки, SPA)\n\n"
            "Если клиент спрашивает о конкретных проектах — приведи примеры "
            "(AI-секретарь с клонированием голоса, CRM-интеграции, Telegram-боты). "
            "Тон: профессиональный, уверенный. Русский язык."
        ),
        "temperature": 0.6,
        "max_tokens": 1024,
        "order": 3,
    },
    {
        "prompt_key": "tz_conditions",
        "name": "Условия работы",
        "description": "Информация об условиях сотрудничества с Артёмом",
        "system_prompt": (
            "Ты — AI-ассистент фрилансера Артёма Юрьевича (@ShaerWare). "
            "Расскажи об условиях работы:\n"
            "• 1 спринт = 1 неделя = 5 рабочих дней = 50,000 руб\n"
            "• Оплата поспринтовая, предоплата за каждый спринт\n"
            "• Демо после каждого спринта\n"
            "• Правки включены в стоимость спринта\n"
            "• Гарантия — возврат при несоответствии ТЗ\n"
            "• Безопасная сделка — через Kwork или FL.ru (по желанию)\n"
            "• Контакт: Telegram @ShaerWare\n\n"
            "Если клиент спрашивает о скидках — объясни, что цена фиксирована, "
            "но можно начать с MVP (1-2 спринта) и масштабировать позже. "
            "Тон: деловой, прозрачный."
        ),
        "temperature": 0.3,
        "max_tokens": 1024,
        "order": 4,
    },
]

# ---------------------------------------------------------------------------
# Quiz questions
# ---------------------------------------------------------------------------

QUIZ_QUESTIONS = [
    {
        "question_key": "project_type",
        "text": "Вопрос 1 из 2\n\nКакой тип проекта вас интересует?",
        "order": 1,
        "options": [
            {"label": "AI-ассистент / Чат-бот", "value": "chatbot", "icon": "🤖"},
            {"label": "Веб-приложение / SaaS", "value": "web", "icon": "🌐"},
            {"label": "Интеграция с CRM/1С", "value": "integration", "icon": "🔗"},
            {"label": "Telegram-бот", "value": "telegram", "icon": "📱"},
            {"label": "Автоматизация / Парсинг", "value": "automation", "icon": "⚙️"},
            {"label": "Другое", "value": "other", "icon": "🔧"},
        ],
    },
    {
        "question_key": "budget_range",
        "text": "Вопрос 2 из 2\n\nКакой бюджет вы рассматриваете?",
        "order": 2,
        "options": [
            {"label": "50-100К руб.", "value": "50_100", "icon": "💰"},
            {"label": "100-200К руб.", "value": "100_200", "icon": "💰"},
            {"label": "200-500К руб.", "value": "200_500", "icon": "💎"},
            {"label": "500К+ руб.", "value": "500_plus", "icon": "🏆"},
            {"label": "Нужен расчёт", "value": "calculate", "icon": "🧮"},
        ],
    },
]

# ---------------------------------------------------------------------------
# Segments
# ---------------------------------------------------------------------------

SEGMENTS = [
    {
        "segment_key": "tz_qualified_big",
        "name": "Квалифицированный (200К+)",
        "path": "qualified",
        "match_rules": {"budget_range": ["200_500", "500_plus"]},
        "agent_prompt_key": "tz_qualified",
        "priority": 10,
    },
    {
        "segment_key": "tz_qualified_medium",
        "name": "Квалифицированный (100-200К)",
        "path": "qualified",
        "match_rules": {"budget_range": "100_200"},
        "agent_prompt_key": "tz_qualified",
        "priority": 9,
    },
    {
        "segment_key": "tz_calculate",
        "name": "Нужен расчёт",
        "path": "needs_analysis",
        "match_rules": {"budget_range": "calculate"},
        "agent_prompt_key": "tz_qualified",
        "priority": 7,
    },
    {
        "segment_key": "tz_small_budget",
        "name": "Малый бюджет (50-100К)",
        "path": "unqualified",
        "match_rules": {"budget_range": "50_100"},
        "agent_prompt_key": "tz_small",
        "priority": 5,
    },
]

# ---------------------------------------------------------------------------
# Testimonials
# ---------------------------------------------------------------------------

TESTIMONIALS = [
    {
        "text": "Артём составил ТЗ за час, разбил на спринты. Через 2 недели получили работающий MVP. Рекомендую!",
        "author": "Дмитрий, стартап",
        "rating": 5,
        "order": 1,
    },
    {
        "text": "Чёткая оценка, без сюрпризов по срокам и бюджету. Три спринта — всё по плану.",
        "author": "Алексей, e-commerce",
        "rating": 5,
        "order": 2,
    },
]

# ---------------------------------------------------------------------------
# Follow-up rules
# ---------------------------------------------------------------------------

FOLLOWUP_RULES = [
    {
        "name": "Незавершённый квиз (24ч)",
        "trigger": "quiz_started_no_completion",
        "delay_hours": 24,
        "segment_filter": None,
        "message_template": (
            "Привет! Вы начали описывать проект, но не завершили.\n\n"
            "Если остались вопросы — напишите, помогу разобраться.\n"
            "Или пройдите квиз заново: /start"
        ),
        "buttons": [
            {"text": "Продолжить", "callback_data": "quiz:start"},
            {"text": "Не актуально", "callback_data": "followup_stop"},
        ],
        "max_sends": 1,
        "order": 1,
    },
    {
        "name": "ТЗ без ответа (48ч)",
        "trigger": "tz_generated_no_reply",
        "delay_hours": 48,
        "segment_filter": "qualified",
        "message_template": (
            "Вы получили ТЗ для вашего проекта.\n\n"
            "Готовы начать? Свяжитесь с Артёмом: @ShaerWare\n\n"
            "Есть вопросы по ТЗ? Напишите, уточню детали."
        ),
        "buttons": [
            {"text": "Написать Артёму", "url": "https://t.me/ShaerWare"},
            {"text": "Есть вопросы", "callback_data": "action:describe_project"},
        ],
        "max_sends": 2,
        "order": 2,
    },
]


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_bot_instance(cursor: sqlite3.Cursor) -> int:
    """Create the tz-generator bot instance."""
    cursor.execute("SELECT 1 FROM bot_instances WHERE id = ?", (BOT_ID,))
    if cursor.fetchone():
        print(f"  Bot instance '{BOT_ID}' already exists, skipping")
        return 0

    cursor.execute(
        "INSERT INTO bot_instances "
        "(id, name, description, enabled, auto_start, bot_token, api_url, "
        "allowed_users, admin_users, welcome_message, unauthorized_message, "
        "error_message, typing_enabled, action_buttons, "
        "llm_backend, llm_persona, system_prompt, llm_params, "
        "tts_engine, tts_voice, tts_preset, "
        "payment_enabled, stars_enabled, created, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            BOT_ID,
            "TZ Generator",
            "Генератор Технических Заданий. AI-аналитик фрилансера Артёма (@ShaerWare).",
            True,  # enabled
            False,  # auto_start (user enters token first)
            "",  # bot_token (user fills in admin panel)
            "",  # api_url
            "[]",  # allowed_users (empty = all allowed)
            "[]",  # admin_users
            WELCOME_MESSAGE,
            "Извините, доступ ограничен. Свяжитесь с @ShaerWare.",
            "Произошла ошибка. Попробуйте позже или напишите @ShaerWare.",
            True,  # typing_enabled
            json.dumps(ACTION_BUTTONS, ensure_ascii=False),
            "vllm",  # llm_backend (can be changed to cloud in admin)
            "anna",  # llm_persona
            TZ_SYSTEM_PROMPT,
            json.dumps({"temperature": 0.4, "max_tokens": 4096}),
            "piper",  # tts_engine (text bot, no TTS needed but piper is lightest)
            "dmitri",  # tts_voice
            None,  # tts_preset
            False,  # payment_enabled
            False,  # stars_enabled
            _now_iso(),
            _now_iso(),
        ),
    )
    print(f"  + bot instance: {BOT_ID} (TZ Generator)")
    return 1


def seed_agent_prompts(cursor: sqlite3.Cursor) -> int:
    inserted = 0
    for p in AGENT_PROMPTS:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_agent_prompts "
            "(bot_id, prompt_key, name, description, system_prompt, temperature, max_tokens, "
            'enabled, "order", created, updated) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                BOT_ID,
                p["prompt_key"],
                p["name"],
                p.get("description"),
                p["system_prompt"],
                p["temperature"],
                p["max_tokens"],
                p["order"],
                _now_iso(),
                _now_iso(),
            ),
        )
        if cursor.rowcount:
            inserted += 1
            print(f"  + agent prompt: {p['prompt_key']} ({p['name']})")
    return inserted


def seed_quiz_questions(cursor: sqlite3.Cursor) -> int:
    inserted = 0
    for q in QUIZ_QUESTIONS:
        cursor.execute(
            "SELECT 1 FROM bot_quiz_questions WHERE bot_id = ? AND question_key = ?",
            (BOT_ID, q["question_key"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_quiz_questions "
            '(bot_id, question_key, text, "order", enabled, options, created, updated) '
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (
                BOT_ID,
                q["question_key"],
                q["text"],
                q["order"],
                json.dumps(q["options"], ensure_ascii=False),
                _now_iso(),
                _now_iso(),
            ),
        )
        inserted += 1
        print(f"  + quiz question: {q['question_key']}")
    return inserted


def seed_segments(cursor: sqlite3.Cursor) -> int:
    inserted = 0
    for s in SEGMENTS:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_segments "
            "(bot_id, segment_key, name, description, path, match_rules, priority, "
            "agent_prompt_key, enabled, created) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                BOT_ID,
                s["segment_key"],
                s["name"],
                s.get("description"),
                s["path"],
                json.dumps(s["match_rules"], ensure_ascii=False),
                s["priority"],
                s.get("agent_prompt_key"),
                _now_iso(),
            ),
        )
        if cursor.rowcount:
            inserted += 1
            print(f"  + segment: {s['segment_key']} ({s['name']})")
    return inserted


def seed_testimonials(cursor: sqlite3.Cursor) -> int:
    inserted = 0
    for t in TESTIMONIALS:
        cursor.execute(
            "SELECT 1 FROM bot_testimonials WHERE bot_id = ? AND text = ?",
            (BOT_ID, t["text"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_testimonials "
            '(bot_id, text, author, rating, enabled, "order", created) '
            "VALUES (?, ?, ?, ?, 1, ?, ?)",
            (
                BOT_ID,
                t["text"],
                t["author"],
                t["rating"],
                t["order"],
                _now_iso(),
            ),
        )
        inserted += 1
        print(f"  + testimonial: {t['author']}")
    return inserted


def seed_followup_rules(cursor: sqlite3.Cursor) -> int:
    inserted = 0
    for f in FOLLOWUP_RULES:
        cursor.execute(
            "SELECT 1 FROM bot_followup_rules WHERE bot_id = ? AND trigger = ?",
            (BOT_ID, f["trigger"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_followup_rules "
            "(bot_id, name, trigger, delay_hours, segment_filter, message_template, "
            'buttons, max_sends, enabled, "order", created, updated) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                BOT_ID,
                f["name"],
                f["trigger"],
                f["delay_hours"],
                f.get("segment_filter"),
                f["message_template"],
                json.dumps(f["buttons"], ensure_ascii=False) if f.get("buttons") else None,
                f["max_sends"],
                f["order"],
                _now_iso(),
                _now_iso(),
            ),
        )
        inserted += 1
        print(f"  + followup rule: {f['trigger']} ({f['name']})")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database.")
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {DB_PATH.parent}")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print(f"\nSeeding TZ Generator bot (bot_id='{BOT_ID}')...\n")

    counts = {}

    print("  [Bot Instance]")
    counts["bot_instance"] = seed_bot_instance(cursor)

    print("\n  [Agent Prompts]")
    counts["agent_prompts"] = seed_agent_prompts(cursor)

    print("\n  [Quiz Questions]")
    counts["quiz_questions"] = seed_quiz_questions(cursor)

    print("\n  [Segments]")
    counts["segments"] = seed_segments(cursor)

    print("\n  [Testimonials]")
    counts["testimonials"] = seed_testimonials(cursor)

    print("\n  [Follow-up Rules]")
    counts["followup_rules"] = seed_followup_rules(cursor)

    conn.commit()
    conn.close()

    # Summary
    total = sum(counts.values())
    print(f"\n{'=' * 50}")
    print(f"Seed complete for bot_id='{BOT_ID}'")
    print(f"{'=' * 50}")
    print(f"  Bot instance:    {counts['bot_instance']} inserted")
    print(f"  Agent prompts:   {counts['agent_prompts']} inserted")
    print(f"  Quiz questions:  {counts['quiz_questions']} inserted")
    print(f"  Segments:        {counts['segments']} inserted")
    print(f"  Testimonials:    {counts['testimonials']} inserted")
    print(f"  Follow-up rules: {counts['followup_rules']} inserted")
    print("  -------")
    print(f"  Total:           {total} rows inserted")
    if total == 0:
        print("\n  No changes needed — all data already exists.")
    print(f"\n  Database: {DB_PATH}")


if __name__ == "__main__":
    main()
