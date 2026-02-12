"""WhatsApp keyboard builders.

Builds interactive message payloads for WhatsApp Cloud API.
Equivalent of telegram_bot/sales/keyboards.py but using
WhatsApp quick-reply buttons (max 3) and list messages (max 10 rows).
"""

from typing import Any


# ─── Quick-reply button helpers ────────────────────────────────


def welcome_buttons() -> dict[str, Any]:
    """Welcome message with 3 quick-reply buttons."""
    return {
        "type": "button",
        "body": {"text": "Привет! Чем могу помочь?"},
        "action": {
            "buttons": [
                {
                    "type": "reply",
                    "reply": {"id": "sales:start_quiz", "title": "🎯 Подобрать"},
                },
                {
                    "type": "reply",
                    "reply": {"id": "sales:github", "title": "📦 GitHub"},
                },
                {
                    "type": "reply",
                    "reply": {"id": "sales:faq", "title": "❓ FAQ"},
                },
            ]
        },
    }


# ─── List message helpers ──────────────────────────────────────


def faq_list() -> dict[str, Any]:
    """FAQ categories as a list message."""
    return {
        "type": "list",
        "body": {"text": "Выберите раздел:"},
        "action": {
            "button": "Открыть FAQ",
            "sections": [
                {
                    "title": "Продукт",
                    "rows": [
                        {"id": "faq:what_is", "title": "Что это?", "description": "О системе"},
                        {"id": "faq:offline", "title": "Офлайн работа"},
                        {"id": "faq:security", "title": "Безопасность"},
                    ],
                },
                {
                    "title": "Установка",
                    "rows": [
                        {"id": "faq:hardware", "title": "Требования"},
                        {"id": "faq:install", "title": "Установка"},
                        {"id": "faq:integrations", "title": "Интеграции"},
                    ],
                },
                {
                    "title": "Цены и поддержка",
                    "rows": [
                        {"id": "faq:price", "title": "Стоимость"},
                        {"id": "faq:support", "title": "Поддержка"},
                        {"id": "faq:free_trial", "title": "Пробный период"},
                    ],
                },
            ],
        },
    }
