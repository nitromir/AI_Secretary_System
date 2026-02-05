"""Telegram bot handlers."""

from aiogram import Router

from .callbacks import router as callbacks_router
from .commands import router as commands_router
from .files import router as files_router
from .messages import router as messages_router
from .news import router as news_router
from .sales import get_sales_router
from .tz import router as tz_router


def get_main_router() -> Router:
    """Create and configure the main router with all sub-routers."""
    main_router = Router()
    # Sales funnel first — handles /start, sales: callbacks, FSM text input
    main_router.include_router(get_sales_router())
    # TZ (technical specification) quiz
    main_router.include_router(tz_router)
    # News handler
    main_router.include_router(news_router)
    # AI chat commands (/new, /model) — /start removed, handled by sales
    main_router.include_router(commands_router)
    main_router.include_router(callbacks_router)
    main_router.include_router(files_router)
    # Catch-all MUST be last
    main_router.include_router(messages_router)
    return main_router
