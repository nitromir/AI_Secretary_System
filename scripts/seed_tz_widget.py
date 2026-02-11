#!/usr/bin/env python3
"""
Seed script for the TZ Generator widget instance.
Creates a widget instance that uses the TZ system prompt for website embeds.

Usage:
    python scripts/seed_tz_widget.py
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

WIDGET_ID = "tz-generator"

# Reuse the same system prompt from the bot seed script
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


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    now = datetime.now(timezone.utc).isoformat()

    # Check if already exists
    cursor.execute("SELECT 1 FROM widget_instances WHERE id = ?", (WIDGET_ID,))
    if cursor.fetchone():
        print(f"Widget instance '{WIDGET_ID}' already exists, skipping.")
        conn.close()
        return

    cursor.execute(
        "INSERT INTO widget_instances "
        "(id, name, description, enabled, title, greeting, placeholder, "
        "primary_color, position, allowed_domains, tunnel_url, "
        "llm_backend, llm_persona, system_prompt, llm_params, "
        "tts_engine, tts_voice, tts_preset, created, updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            WIDGET_ID,
            "TZ Generator",
            "Генератор ТЗ для сайта фрилансера",
            True,
            "Оценка проекта",
            "Здравствуйте! Я помогу оценить ваш проект и составить Техническое Задание.\n\nРасскажите, что нужно сделать?",
            "Опишите ваш проект...",
            "#10b981",
            "right",
            "[]",
            "",
            "cloud:gemini-default",
            "anna",
            TZ_SYSTEM_PROMPT,
            json.dumps({"temperature": 0.7, "max_tokens": 4096}),
            "piper",
            "anna",
            None,
            now,
            now,
        ),
    )

    conn.commit()
    conn.close()

    print(f"Widget instance '{WIDGET_ID}' created successfully.")
    print(f'Embed: <script src="https://YOUR_DOMAIN/widget.js?instance={WIDGET_ID}"></script>')


if __name__ == "__main__":
    main()
