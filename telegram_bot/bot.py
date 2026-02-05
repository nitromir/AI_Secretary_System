"""Telegram bot entry point.

Run with:  python -m src.telegram.bot
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import get_telegram_settings
from .handlers import get_main_router
from .middleware.access import AccessMiddleware
from .sales.database import get_sales_db
from .services.github_news import news_broadcast_scheduler
from .services.llm_router import get_llm_router


logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_telegram_settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register access middleware on all update types
    dp.message.middleware(AccessMiddleware())
    dp.callback_query.middleware(AccessMiddleware())

    # Initialize sales database
    db = await get_sales_db()
    logger.info("Sales DB initialized: %s", settings.sales_db_path)

    # Register routers
    dp.include_router(get_main_router())

    logger.info("Starting Telegram bot (polling)…")
    logger.info("Bridge URL: %s", settings.bridge_url)
    allowed = settings.get_allowed_user_ids()
    if allowed:
        logger.info("Allowed users: %s", allowed)

    # Start news broadcast scheduler (checks every hour)
    scheduler_task = asyncio.create_task(news_broadcast_scheduler(bot, interval_hours=1))
    logger.info("News broadcast scheduler started")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "pre_checkout_query"],
        )
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        router = get_llm_router()
        await router.close()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


def run() -> None:
    """Entry point for ``python -m src.telegram.bot``."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
