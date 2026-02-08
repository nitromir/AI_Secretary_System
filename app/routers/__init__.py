# app/routers/__init__.py
"""API routers for admin and public endpoints."""

from app.routers import (
    amocrm,
    audit,
    auth,
    backup,
    bot_sales,
    chat,
    faq,
    github_webhook,
    gsm,
    legal,
    llm,
    monitor,
    services,
    stt,
    telegram,
    tts,
    usage,
    widget,
    yoomoney_webhook,
)


__all__ = [
    "amocrm",
    "auth",
    "audit",
    "backup",
    "services",
    "monitor",
    "faq",
    "stt",
    "llm",
    "tts",
    "chat",
    "telegram",
    "usage",
    "widget",
    "gsm",
    "bot_sales",
    "legal",
    "github_webhook",
    "yoomoney_webhook",
]
