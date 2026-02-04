#!/usr/bin/env python3
"""
Migration script for sales bot tables.
Creates tables and seeds default data (agent prompts, quiz, segments, hardware, followups, testimonials).

Usage:
    python scripts/migrate_sales_bot.py [bot_id]

    bot_id: Optional bot instance ID to seed defaults for (default: "default")
"""

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

# ---------------------------------------------------------------------------
# Default data (imported inline so the script stays self-contained)
# ---------------------------------------------------------------------------

DEFAULT_AGENT_PROMPTS = [
    {
        "prompt_key": "welcome",
        "name": "Приветствие",
        "description": "Первое сообщение + social proof + приглашение в квиз",
        "system_prompt": (
            "Ты — AI-ассистент проекта AI Secretary от ShaerWare. "
            "Твоя задача — приветствовать нового пользователя, кратко рассказать о проекте "
            "(голосовой AI на своём сервере, без абонентки, клонирование голоса, работает офлайн), "
            "показать social proof (звёзды GitHub, отзывы) и пригласить пройти "
            "2-минутный квиз для подбора лучшего варианта. "
            "Тон: дружелюбный, уверенный, не навязчивый. Русский язык."
        ),
        "temperature": 0.7,
        "max_tokens": 512,
        "order": 1,
    },
    {
        "prompt_key": "diy_techie",
        "name": "DIY — Технарь",
        "description": "Для технически подкованных пользователей, которые хотят ставить сами",
        "system_prompt": (
            "Ты — технический консультант проекта AI Secretary. "
            "Пользователь — технарь, хочет установить систему самостоятельно. "
            "Давай технические детали: GPU требования, модели LLM, Docker-команды, "
            "конфигурацию. Ссылайся на GitHub (github.com/ShaerWare/AI_Secretary_System) "
            "и вики (github.com/ShaerWare/AI_Secretary_System/wiki). "
            "Предлагай поставить звезду на GitHub если проект полезен. "
            "Тон: технический, конкретный, без воды."
        ),
        "temperature": 0.3,
        "max_tokens": 1024,
        "order": 2,
    },
    {
        "prompt_key": "basic_busy",
        "name": "Basic — Занятой",
        "description": "Для пользователей, которые хотят готовое решение",
        "system_prompt": (
            "Ты — менеджер по продажам проекта AI Secretary. "
            "Пользователь хочет готовое решение, не хочет разбираться в технических деталях. "
            "Фокусируйся на: экономии (vs SaaS-боты 15K₽/мес), простоте установки (30 мин), "
            "приватности данных (152-ФЗ), отсутствии абонентки. "
            "Предлагай услугу установки. Показывай ROI. "
            "Тон: профессиональный, убедительный, с конкретными цифрами."
        ),
        "temperature": 0.7,
        "max_tokens": 768,
        "order": 3,
    },
    {
        "prompt_key": "custom_business",
        "name": "Custom — Бизнес",
        "description": "Для бизнес-клиентов с задачами интеграции",
        "system_prompt": (
            "Ты — бизнес-консультант проекта AI Secretary. "
            "Пользователь — представитель бизнеса, ему нужна кастомная интеграция "
            "(CRM, телефония, кастомные сценарии). "
            "Рассказывай о кейсах: автосалон -70% нагрузки, клиника +40% записей. "
            "Задавай квалифицирующие вопросы: задача, объём, интеграции, бюджет, сроки. "
            "Формируй предварительный расчёт. "
            "Тон: деловой, экспертный, с кейсами."
        ),
        "temperature": 0.5,
        "max_tokens": 1024,
        "order": 4,
    },
    {
        "prompt_key": "faq_answer",
        "name": "FAQ ответ",
        "description": "Точные ответы по документации проекта",
        "system_prompt": (
            "Ты — справочный бот проекта AI Secretary. "
            "Отвечай кратко и точно на вопросы о проекте, опираясь на документацию. "
            "Если не знаешь ответа — честно скажи и предложи посмотреть вики "
            "(github.com/ShaerWare/AI_Secretary_System/wiki) или задать вопрос автору. "
            "Русский язык. Максимум 3-4 предложения."
        ),
        "temperature": 0.2,
        "max_tokens": 512,
        "order": 5,
    },
    {
        "prompt_key": "hardware_audit",
        "name": "Аудит железа",
        "description": "Рекомендация модели LLM/TTS по характеристикам GPU",
        "system_prompt": (
            "Ты — технический эксперт по AI-инфраструктуре. "
            "На основе модели GPU пользователя рекомендуй оптимальную конфигурацию "
            "AI Secretary: модель LLM (Qwen/Llama/DeepSeek), TTS движок (XTTS/Piper), "
            "оценку качества (1-5 звёзд), скорость ответа. "
            "Если GPU слабая — предложи CPU-режим + Cloud LLM. "
            "Формат: структурированный список с emoji."
        ),
        "temperature": 0.2,
        "max_tokens": 768,
        "order": 6,
    },
    {
        "prompt_key": "roi_calculator",
        "name": "ROI калькулятор",
        "description": "Расчёт экономии vs SaaS-решения",
        "system_prompt": (
            "Ты — финансовый консультант. Рассчитай экономию от использования "
            "AI Secretary (self-hosted, разовая оплата 5000₽) vs типичного SaaS-бота "
            "(15000₽/мес). Покажи экономию за 1 год, 3 года. "
            "Добавь бонусы: приватность данных, работа офлайн, кастомизация, клонирование голоса. "
            "Формат: таблица сравнения + итог."
        ),
        "temperature": 0.3,
        "max_tokens": 768,
        "order": 7,
    },
    {
        "prompt_key": "discovery_summary",
        "name": "Итог discovery",
        "description": "Генерация коммерческого предложения по результатам discovery",
        "system_prompt": (
            "Ты — менеджер проектов. На основе ответов discovery-анкеты "
            "(задача, объём, интеграции, сроки, бюджет) сформируй предварительный расчёт. "
            "Укажи: что входит, стоимость каждого компонента, итоговую вилку цен, "
            "сроки реализации. Добавь пометку что это предварительная оценка. "
            "Формат: структурированное КП."
        ),
        "temperature": 0.4,
        "max_tokens": 1024,
        "order": 8,
    },
    {
        "prompt_key": "objection_price",
        "name": "Возражение: дорого",
        "description": "Работа с возражением по цене",
        "system_prompt": (
            "Пользователь считает цену высокой. Предложи альтернативы: "
            "1) MVP-версия без интеграций (дешевле), "
            "2) Поэтапное внедрение (оплата по частям), "
            "3) Self-hosted с консультацией (самый бюджетный). "
            "Не давить, а показать варианты. Тон: понимающий, гибкий."
        ),
        "temperature": 0.6,
        "max_tokens": 768,
        "order": 9,
    },
    {
        "prompt_key": "objection_nogpu",
        "name": "Возражение: нет GPU",
        "description": "Варианты работы без GPU",
        "system_prompt": (
            "У пользователя нет GPU. Предложи 3 варианта: "
            "1) CPU-режим + Cloud LLM (бесплатный tier Gemini), "
            "2) Аренда VPS с GPU (от 3000₽/мес), "
            "3) Свой мини-сервер (RTX 3060 б/у ~25000₽, окупается за 8 мес). "
            "Сравни плюсы и минусы каждого. Тон: помогающий."
        ),
        "temperature": 0.5,
        "max_tokens": 768,
        "order": 10,
    },
    {
        "prompt_key": "followup_gentle",
        "name": "Follow-up мягкий",
        "description": "Мягкое напоминание для follow-up сообщений",
        "system_prompt": (
            "Напиши мягкое follow-up сообщение для пользователя, который давно не заходил. "
            "Расскажи о новых фичах проекта, предложи помощь. "
            "Обязательно дай возможность отписаться. "
            "Максимум 3 предложения. Не навязывай."
        ),
        "temperature": 0.7,
        "max_tokens": 256,
        "order": 11,
    },
    {
        "prompt_key": "pr_comment",
        "name": "Комментарий к PR",
        "description": "AI-саммари для GitHub Pull Request",
        "system_prompt": (
            "Ты — AI-ассистент проекта AI Secretary. "
            "Напиши краткий информативный комментарий к Pull Request на русском. "
            "Формат: заголовок '## 🤖 AI Secretary Bot Summary', "
            "затем секции: 'Что изменилось' (3-5 буллетов), "
            "'Кому важно' (для каких пользователей), "
            "'Breaking changes' (есть или нет). "
            "В конце подпись: *Сгенерировано AI Secretary Bot*."
        ),
        "temperature": 0.3,
        "max_tokens": 1024,
        "order": 12,
    },
    {
        "prompt_key": "pr_news",
        "name": "Новость о PR",
        "description": "Telegram-рассылка о новом PR/обновлении",
        "system_prompt": (
            "Сформируй короткую новость для Telegram-подписчиков о новом обновлении проекта "
            "AI Secretary на основе Pull Request. 2-3 предложения, emoji уместны. "
            "Добавь ссылку на PR. Предложи поставить звезду на GitHub. "
            "Русский язык. Максимум 5 строк."
        ),
        "temperature": 0.6,
        "max_tokens": 256,
        "order": 13,
    },
    {
        "prompt_key": "general_chat",
        "name": "Свободный чат",
        "description": "Общение с AI-ассистентом вне воронки",
        "system_prompt": (
            "Ты — AI-ассистент проекта AI Secretary (github.com/ShaerWare/AI_Secretary_System). "
            "Отвечай на любые вопросы о проекте. Если вопрос не про проект — "
            "вежливо направь обратно. Ссылайся на вики и README. "
            "Автор проекта: github.com/ShaerWare. "
            "Тон: дружелюбный, компетентный."
        ),
        "temperature": 0.7,
        "max_tokens": 1024,
        "order": 14,
    },
]

DEFAULT_QUIZ_QUESTIONS = [
    {
        "question_key": "tech_level",
        "text": "Вопрос 1 из 2\n\nКак вы относитесь к технической стороне?",
        "order": 1,
        "options": [
            {"label": "Люблю сам разбираться в настройках", "value": "diy", "icon": ""},
            {"label": "Предпочитаю готовое решение", "value": "ready", "icon": ""},
            {"label": "У меня бизнес-задача, нужна интеграция", "value": "business", "icon": ""},
        ],
    },
    {
        "question_key": "infrastructure",
        "text": "Вопрос 2 из 2\n\nЕсть ли у вас сервер для установки?",
        "order": 2,
        "options": [
            {"label": "Да, есть сервер с GPU", "value": "gpu", "icon": ""},
            {"label": "Есть сервер, но без GPU", "value": "cpu", "icon": ""},
            {"label": "Нет сервера", "value": "none", "icon": ""},
            {"label": "Не знаю / Нужна консультация", "value": "unknown", "icon": ""},
        ],
    },
]

DEFAULT_SEGMENTS = [
    # DIY path
    {
        "segment_key": "diy_ready",
        "name": "DIY Ready",
        "path": "diy",
        "match_rules": {"tech_level": "diy", "infrastructure": "gpu"},
        "agent_prompt_key": "diy_techie",
        "priority": 10,
    },
    {
        "segment_key": "diy_need_advice",
        "name": "DIY нужен совет",
        "path": "diy",
        "match_rules": {"tech_level": "diy", "infrastructure": "cpu"},
        "agent_prompt_key": "diy_techie",
        "priority": 9,
    },
    {
        "segment_key": "diy_need_hw",
        "name": "DIY нужно железо",
        "path": "diy",
        "match_rules": {"tech_level": "diy", "infrastructure": "none"},
        "agent_prompt_key": "diy_techie",
        "priority": 8,
    },
    {
        "segment_key": "diy_need_audit",
        "name": "DIY нужен аудит",
        "path": "diy",
        "match_rules": {"tech_level": "diy", "infrastructure": "unknown"},
        "agent_prompt_key": "diy_techie",
        "priority": 7,
    },
    # Basic path
    {
        "segment_key": "basic_hot",
        "name": "Basic горячий",
        "path": "basic",
        "match_rules": {"tech_level": "ready", "infrastructure": "gpu"},
        "agent_prompt_key": "basic_busy",
        "priority": 10,
    },
    {
        "segment_key": "basic_warm",
        "name": "Basic тёплый",
        "path": "basic",
        "match_rules": {"tech_level": "ready", "infrastructure": "cpu"},
        "agent_prompt_key": "basic_busy",
        "priority": 9,
    },
    {
        "segment_key": "basic_cold",
        "name": "Basic холодный",
        "path": "basic",
        "match_rules": {"tech_level": "ready", "infrastructure": "none"},
        "agent_prompt_key": "basic_busy",
        "priority": 8,
    },
    {
        "segment_key": "basic_audit",
        "name": "Basic аудит",
        "path": "basic",
        "match_rules": {"tech_level": "ready", "infrastructure": "unknown"},
        "agent_prompt_key": "basic_busy",
        "priority": 7,
    },
    # Custom path
    {
        "segment_key": "custom_hot",
        "name": "Custom горячий",
        "path": "custom",
        "match_rules": {"tech_level": "business", "infrastructure": "gpu"},
        "agent_prompt_key": "custom_business",
        "priority": 10,
    },
    {
        "segment_key": "custom_warm",
        "name": "Custom тёплый",
        "path": "custom",
        "match_rules": {"tech_level": "business", "infrastructure": "cpu"},
        "agent_prompt_key": "custom_business",
        "priority": 9,
    },
    {
        "segment_key": "custom_full",
        "name": "Custom под ключ",
        "path": "custom",
        "match_rules": {"tech_level": "business", "infrastructure": "none"},
        "agent_prompt_key": "custom_business",
        "priority": 10,
    },
    {
        "segment_key": "custom_discovery",
        "name": "Custom discovery",
        "path": "custom",
        "match_rules": {"tech_level": "business", "infrastructure": "unknown"},
        "agent_prompt_key": "custom_business",
        "priority": 8,
    },
]

DEFAULT_HARDWARE_SPECS = [
    {
        "gpu_name": "GTX 1660 Super",
        "gpu_vram_gb": 6,
        "gpu_family": "gtx_16xx",
        "recommended_llm": "Qwen2.5-3B",
        "recommended_tts": "openvoice",
        "quality_stars": 2,
        "speed_note": "~3-5 сек",
        "order": 1,
    },
    {
        "gpu_name": "GTX 1070/1080",
        "gpu_vram_gb": 8,
        "gpu_family": "gtx_10xx",
        "recommended_llm": "Qwen2.5-3B",
        "recommended_tts": "openvoice",
        "quality_stars": 2,
        "speed_note": "~3-4 сек",
        "order": 2,
    },
    {
        "gpu_name": "RTX 3060",
        "gpu_vram_gb": 12,
        "gpu_family": "rtx_30xx",
        "recommended_llm": "Qwen2.5-7B",
        "recommended_tts": "xtts",
        "quality_stars": 3,
        "speed_note": "~2 сек",
        "order": 3,
    },
    {
        "gpu_name": "RTX 3070",
        "gpu_vram_gb": 8,
        "gpu_family": "rtx_30xx",
        "recommended_llm": "Qwen2.5-7B-AWQ",
        "recommended_tts": "xtts",
        "quality_stars": 3,
        "speed_note": "~2 сек",
        "order": 4,
    },
    {
        "gpu_name": "RTX 3080",
        "gpu_vram_gb": 10,
        "gpu_family": "rtx_30xx",
        "recommended_llm": "Qwen2.5-7B",
        "recommended_tts": "xtts",
        "quality_stars": 3,
        "speed_note": "~1.5 сек",
        "order": 5,
    },
    {
        "gpu_name": "RTX 3090",
        "gpu_vram_gb": 24,
        "gpu_family": "rtx_30xx",
        "recommended_llm": "Qwen2.5-14B",
        "recommended_tts": "xtts",
        "quality_stars": 4,
        "speed_note": "~1.5 сек",
        "order": 6,
    },
    {
        "gpu_name": "RTX 4080",
        "gpu_vram_gb": 16,
        "gpu_family": "rtx_40xx",
        "recommended_llm": "Qwen2.5-14B-AWQ",
        "recommended_tts": "xtts",
        "quality_stars": 4,
        "speed_note": "~1 сек",
        "order": 7,
    },
    {
        "gpu_name": "RTX 4090",
        "gpu_vram_gb": 24,
        "gpu_family": "rtx_40xx",
        "recommended_llm": "Qwen2.5-32B-AWQ",
        "recommended_tts": "xtts",
        "quality_stars": 5,
        "speed_note": "~0.8 сек",
        "order": 8,
    },
]

DEFAULT_FOLLOWUP_RULES = [
    {
        "name": "GitHub без возврата (24ч)",
        "trigger": "clicked_github_no_return",
        "delay_hours": 24,
        "segment_filter": "diy",
        "message_template": (
            "Привет! Как успехи с установкой AI Secretary?\n\n"
            "Если всё работает — буду рад звезде на GitHub\n\n"
            "Если застряли — напишите, помогу разобраться."
        ),
        "buttons": [
            {"text": "Всё работает!", "callback_data": "github_success"},
            {"text": "Есть вопросы", "callback_data": "faq_ask"},
            {"text": "Установите за меня", "callback_data": "install_5k"},
        ],
        "max_sends": 2,
        "order": 1,
    },
    {
        "name": "Посмотрел цену (48ч)",
        "trigger": "viewed_price_no_action",
        "delay_hours": 48,
        "segment_filter": "basic",
        "message_template": (
            "Вы интересовались установкой AI Secretary.\n\nМожет, остались вопросы?"
        ),
        "buttons": [
            {"text": "Хочу установить", "callback_data": "install_5k"},
            {"text": "Есть вопросы", "callback_data": "faq_ask"},
            {"text": "Не актуально", "callback_data": "followup_stop"},
        ],
        "max_sends": 2,
        "order": 2,
    },
    {
        "name": "Неактивный 7 дней",
        "trigger": "inactive_7_days",
        "delay_hours": 168,
        "segment_filter": None,
        "message_template": (
            "Давно не виделись!\n\n"
            "Если AI Secretary всё ещё актуален — заходите, "
            "появились новые возможности."
        ),
        "buttons": [
            {"text": "Что нового?", "callback_data": "changelog"},
            {"text": "Подписаться на обновления", "callback_data": "subscribe"},
            {"text": "Отписаться", "callback_data": "unsubscribe"},
        ],
        "max_sends": 1,
        "order": 3,
    },
]

DEFAULT_TESTIMONIALS = [
    {
        "text": "Поставил за вечер, работает как часы. Клонировал свой голос — клиенты не отличают от живого!",
        "author": "Дмитрий, IT-компания",
        "rating": 5,
        "order": 1,
    },
    {
        "text": "Сэкономили 180К в год на SaaS-ботах. Окупилось за первый месяц.",
        "author": "Алексей, автосалон",
        "rating": 5,
        "order": 2,
    },
    {
        "text": "Отличный проект для тех, кто ценит приватность данных. Всё на своём сервере.",
        "author": "Мария, клиника",
        "rating": 4,
        "order": 3,
    },
]

# ---------------------------------------------------------------------------
# Table DDL (must match SQLAlchemy models in db/models.py exactly)
# ---------------------------------------------------------------------------

TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS bot_agent_prompts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        prompt_key VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        system_prompt TEXT NOT NULL,
        temperature FLOAT DEFAULT 0.7,
        max_tokens INTEGER DEFAULT 1024,
        enabled BOOLEAN DEFAULT 1,
        "order" INTEGER DEFAULT 0,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bot_agent_prompts_bot_key
        ON bot_agent_prompts (bot_id, prompt_key)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_agent_prompts_bot_id
        ON bot_agent_prompts (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_agent_prompts_prompt_key
        ON bot_agent_prompts (prompt_key)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_quiz_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        question_key VARCHAR(50) NOT NULL,
        text TEXT NOT NULL,
        "order" INTEGER DEFAULT 0,
        enabled BOOLEAN DEFAULT 1,
        options TEXT NOT NULL,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_quiz_questions_bot_key
        ON bot_quiz_questions (bot_id, question_key)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_quiz_questions_bot_id
        ON bot_quiz_questions (bot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_segments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        segment_key VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        path VARCHAR(20) NOT NULL,
        match_rules TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        agent_prompt_key VARCHAR(50),
        enabled BOOLEAN DEFAULT 1,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bot_segments_bot_key
        ON bot_segments (bot_id, segment_key)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_segments_bot_id
        ON bot_segments (bot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        user_id INTEGER NOT NULL,
        username VARCHAR(100),
        first_name VARCHAR(100),
        state VARCHAR(50) DEFAULT 'new',
        segment VARCHAR(50),
        path VARCHAR(20),
        quiz_answers TEXT,
        discovery_data TEXT,
        custom_data TEXT,
        ref_source VARCHAR(100),
        followup_optout BOOLEAN DEFAULT 0,
        followup_ignore_count INTEGER DEFAULT 0,
        last_followup_at DATETIME,
        last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bot_user_profiles_bot_user
        ON bot_user_profiles (bot_id, user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_user_profiles_segment
        ON bot_user_profiles (bot_id, segment)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_user_profiles_state
        ON bot_user_profiles (bot_id, state)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_user_profiles_bot_id
        ON bot_user_profiles (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_user_profiles_user_id
        ON bot_user_profiles (user_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_followup_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        trigger VARCHAR(50) NOT NULL,
        delay_hours INTEGER DEFAULT 24,
        segment_filter VARCHAR(50),
        message_template TEXT NOT NULL,
        buttons TEXT,
        max_sends INTEGER DEFAULT 2,
        enabled BOOLEAN DEFAULT 1,
        "order" INTEGER DEFAULT 0,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_rules_bot_id
        ON bot_followup_rules (bot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_followup_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        user_id INTEGER NOT NULL,
        rule_id INTEGER NOT NULL,
        scheduled_at DATETIME NOT NULL,
        sent_at DATETIME,
        status VARCHAR(20) DEFAULT 'pending',
        send_count INTEGER DEFAULT 0,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_bot_id
        ON bot_followup_queue (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_user_id
        ON bot_followup_queue (user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_rule_id
        ON bot_followup_queue (rule_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_scheduled_at
        ON bot_followup_queue (scheduled_at)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_status
        ON bot_followup_queue (status)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_followup_queue_pending
        ON bot_followup_queue (status, scheduled_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        user_id INTEGER NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        event_data TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_events_bot_id
        ON bot_events (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_events_user_id
        ON bot_events (user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_events_event_type
        ON bot_events (event_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_events_created
        ON bot_events (created)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_events_bot_type_created
        ON bot_events (bot_id, event_type, created)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_testimonials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        text TEXT NOT NULL,
        author VARCHAR(100) DEFAULT '***',
        rating INTEGER DEFAULT 5,
        enabled BOOLEAN DEFAULT 1,
        "order" INTEGER DEFAULT 0,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_testimonials_bot_id
        ON bot_testimonials (bot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_hardware_specs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        gpu_name VARCHAR(100) NOT NULL,
        gpu_vram_gb INTEGER NOT NULL,
        gpu_family VARCHAR(50) NOT NULL,
        recommended_llm VARCHAR(100) NOT NULL,
        recommended_tts VARCHAR(50) NOT NULL,
        recommended_stt VARCHAR(50) DEFAULT 'whisper',
        quality_stars INTEGER DEFAULT 3,
        speed_note VARCHAR(100),
        notes TEXT,
        enabled BOOLEAN DEFAULT 1,
        "order" INTEGER DEFAULT 0
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_hardware_specs_bot_id
        ON bot_hardware_specs (bot_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_ab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        name VARCHAR(100) NOT NULL,
        test_key VARCHAR(50) NOT NULL,
        variants TEXT NOT NULL,
        metric VARCHAR(50) NOT NULL,
        min_sample INTEGER DEFAULT 100,
        active BOOLEAN DEFAULT 1,
        results TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_ab_tests_bot_id
        ON bot_ab_tests (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_ab_tests_bot_key
        ON bot_ab_tests (bot_id, test_key)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_discovery_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        user_id INTEGER NOT NULL,
        step INTEGER NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_discovery_bot_user
        ON bot_discovery_responses (bot_id, user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_discovery_responses_bot_id
        ON bot_discovery_responses (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_discovery_responses_user_id
        ON bot_discovery_responses (user_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL,
        user_id INTEGER NOT NULL,
        subscribed BOOLEAN DEFAULT 1,
        subscribed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        unsubscribed_at DATETIME
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bot_subscribers_bot_user
        ON bot_subscribers (bot_id, user_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_subscribers_active
        ON bot_subscribers (bot_id, subscribed)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_subscribers_bot_id
        ON bot_subscribers (bot_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_bot_subscribers_user_id
        ON bot_subscribers (user_id)
    """,
    """
    CREATE TABLE IF NOT EXISTS bot_github_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bot_id VARCHAR(50) NOT NULL UNIQUE,
        repo_owner VARCHAR(100) DEFAULT 'ShaerWare',
        repo_name VARCHAR(100) DEFAULT 'AI_Secretary_System',
        github_token VARCHAR(255),
        webhook_secret VARCHAR(255),
        comment_enabled BOOLEAN DEFAULT 1,
        broadcast_enabled BOOLEAN DEFAULT 1,
        comment_prompt TEXT,
        broadcast_prompt TEXT,
        events TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS ix_bot_github_configs_bot_id
        ON bot_github_configs (bot_id)
    """,
]


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_agent_prompts(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for p in DEFAULT_AGENT_PROMPTS:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_agent_prompts "
            "(bot_id, prompt_key, name, description, system_prompt, temperature, max_tokens, "
            'enabled, "order", created, updated) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                bot_id,
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


def seed_quiz_questions(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for q in DEFAULT_QUIZ_QUESTIONS:
        cursor.execute(
            "SELECT 1 FROM bot_quiz_questions WHERE bot_id = ? AND question_key = ?",
            (bot_id, q["question_key"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_quiz_questions "
            '(bot_id, question_key, text, "order", enabled, options, created, updated) '
            "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
            (
                bot_id,
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


def seed_segments(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for s in DEFAULT_SEGMENTS:
        cursor.execute(
            "INSERT OR IGNORE INTO bot_segments "
            "(bot_id, segment_key, name, description, path, match_rules, priority, "
            "agent_prompt_key, enabled, created) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                bot_id,
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


def seed_hardware_specs(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for h in DEFAULT_HARDWARE_SPECS:
        # Use gpu_name + bot_id to detect duplicates
        cursor.execute(
            "SELECT 1 FROM bot_hardware_specs WHERE bot_id = ? AND gpu_name = ?",
            (bot_id, h["gpu_name"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_hardware_specs "
            "(bot_id, gpu_name, gpu_vram_gb, gpu_family, recommended_llm, recommended_tts, "
            'recommended_stt, quality_stars, speed_note, notes, enabled, "order") '
            "VALUES (?, ?, ?, ?, ?, ?, 'whisper', ?, ?, NULL, 1, ?)",
            (
                bot_id,
                h["gpu_name"],
                h["gpu_vram_gb"],
                h["gpu_family"],
                h["recommended_llm"],
                h["recommended_tts"],
                h["quality_stars"],
                h.get("speed_note"),
                h["order"],
            ),
        )
        inserted += 1
        print(f"  + hardware spec: {h['gpu_name']} ({h['gpu_vram_gb']}GB)")
    return inserted


def seed_followup_rules(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for f in DEFAULT_FOLLOWUP_RULES:
        # Use trigger + bot_id to detect duplicates
        cursor.execute(
            "SELECT 1 FROM bot_followup_rules WHERE bot_id = ? AND trigger = ?",
            (bot_id, f["trigger"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_followup_rules "
            "(bot_id, name, trigger, delay_hours, segment_filter, message_template, "
            'buttons, max_sends, enabled, "order", created, updated) '
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
            (
                bot_id,
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


def seed_testimonials(cursor: sqlite3.Cursor, bot_id: str) -> int:
    inserted = 0
    for t in DEFAULT_TESTIMONIALS:
        # Use text + bot_id to detect duplicates
        cursor.execute(
            "SELECT 1 FROM bot_testimonials WHERE bot_id = ? AND text = ?",
            (bot_id, t["text"]),
        )
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO bot_testimonials "
            '(bot_id, text, author, rating, enabled, "order", created) '
            "VALUES (?, ?, ?, ?, 1, ?, ?)",
            (
                bot_id,
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


def seed_github_config(cursor: sqlite3.Cursor, bot_id: str) -> int:
    cursor.execute(
        "SELECT 1 FROM bot_github_configs WHERE bot_id = ?",
        (bot_id,),
    )
    if cursor.fetchone():
        print("  GitHub config already exists, skipping")
        return 0

    # Find pr_comment and pr_news prompts for the default prompts
    comment_prompt = None
    broadcast_prompt = None
    for p in DEFAULT_AGENT_PROMPTS:
        if p["prompt_key"] == "pr_comment":
            comment_prompt = p["system_prompt"]
        elif p["prompt_key"] == "pr_news":
            broadcast_prompt = p["system_prompt"]

    cursor.execute(
        "INSERT INTO bot_github_configs "
        "(bot_id, repo_owner, repo_name, comment_prompt, broadcast_prompt, events, "
        "created, updated) "
        "VALUES (?, 'ShaerWare', 'AI_Secretary_System', ?, ?, ?, ?, ?)",
        (
            bot_id,
            comment_prompt,
            broadcast_prompt,
            json.dumps(["opened", "merged"]),
            _now_iso(),
            _now_iso(),
        ),
    )
    print("  + github config: ShaerWare/AI_Secretary_System")
    return 1


# ---------------------------------------------------------------------------
# Main migration
# ---------------------------------------------------------------------------


def migrate(bot_id: str = "default") -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database, or ensure data/ directory exists.")
        # Create data dir and empty db so tables can still be created
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {DB_PATH.parent}")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # ---- Step 1: Create tables ----
    print("\nStep 1: Creating tables...")
    for ddl in TABLE_DDL:
        cursor.execute(ddl)
    conn.commit()
    print("  All tables and indexes created (IF NOT EXISTS).")

    # ---- Step 2: Seed default data ----
    print(f"\nStep 2: Seeding default data for bot_id='{bot_id}'...")

    counts = {}

    print("\n  [Agent Prompts]")
    counts["agent_prompts"] = seed_agent_prompts(cursor, bot_id)

    print("\n  [Quiz Questions]")
    counts["quiz_questions"] = seed_quiz_questions(cursor, bot_id)

    print("\n  [Segments]")
    counts["segments"] = seed_segments(cursor, bot_id)

    print("\n  [Hardware Specs]")
    counts["hardware_specs"] = seed_hardware_specs(cursor, bot_id)

    print("\n  [Follow-up Rules]")
    counts["followup_rules"] = seed_followup_rules(cursor, bot_id)

    print("\n  [Testimonials]")
    counts["testimonials"] = seed_testimonials(cursor, bot_id)

    print("\n  [GitHub Config]")
    counts["github_config"] = seed_github_config(cursor, bot_id)

    conn.commit()
    conn.close()

    # ---- Summary ----
    total = sum(counts.values())
    print(f"\n{'=' * 50}")
    print(f"Migration complete for bot_id='{bot_id}'")
    print(f"{'=' * 50}")
    print(f"  Agent prompts:   {counts['agent_prompts']} inserted")
    print(f"  Quiz questions:  {counts['quiz_questions']} inserted")
    print(f"  Segments:        {counts['segments']} inserted")
    print(f"  Hardware specs:  {counts['hardware_specs']} inserted")
    print(f"  Follow-up rules: {counts['followup_rules']} inserted")
    print(f"  Testimonials:    {counts['testimonials']} inserted")
    print(f"  GitHub config:   {counts['github_config']} inserted")
    print("  -------")
    print(f"  Total:           {total} rows inserted")
    if total == 0:
        print("\n  No changes needed — all data already exists.")
    print(f"\n  Database: {DB_PATH}")


if __name__ == "__main__":
    bot_id = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"Sales Bot Migration — seeding data for bot_id='{bot_id}'")
    migrate(bot_id)
