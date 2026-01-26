#!/usr/bin/env python3
"""
Telegram Bot Service for AI Secretary
Connects Telegram users to the AI assistant
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional, Dict, Set
from datetime import datetime

import aiohttp
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ChatAction, ParseMode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG_FILE = Path(__file__).parent / "telegram_config.json"
SESSIONS_FILE = Path(__file__).parent / "telegram_sessions.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "bot_token": "",
    "api_url": "http://localhost:8002",
    "allowed_users": [],  # Empty = all users allowed
    "admin_users": [],    # Users who can manage the bot
    "welcome_message": "Здравствуйте! Я AI-ассистент компании Шаервэй. Чем могу помочь?",
    "unauthorized_message": "Извините, у вас нет доступа к этому боту.",
    "error_message": "Произошла ошибка. Попробуйте позже.",
    "typing_enabled": True,
    "max_message_length": 4096,
}


class TelegramBotService:
    def __init__(self):
        self.config: Dict = self._load_config()
        self.sessions: Dict[int, str] = self._load_sessions()  # user_id -> session_id
        self.app: Optional[Application] = None
        self.running = False
        self._http_session: Optional[aiohttp.ClientSession] = None

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
                return {**DEFAULT_CONFIG, **config}
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()

    def _save_config(self, config: Dict):
        """Save configuration to file"""
        CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        self.config = config

    def _load_sessions(self) -> Dict[int, str]:
        """Load user sessions from file"""
        if SESSIONS_FILE.exists():
            try:
                data = json.loads(SESSIONS_FILE.read_text(encoding='utf-8'))
                # Convert string keys back to int
                return {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
        return {}

    def _save_sessions(self):
        """Save user sessions to file"""
        SESSIONS_FILE.write_text(
            json.dumps(self.sessions, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )

    def reload_config(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")

    def get_config(self) -> Dict:
        """Get current configuration"""
        return self.config.copy()

    def update_config(self, new_config: Dict) -> Dict:
        """Update configuration"""
        config = {**self.config, **new_config}
        self._save_config(config)
        logger.info("Configuration updated")
        return config

    def is_user_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to use the bot"""
        allowed = self.config.get("allowed_users", [])
        if not allowed:  # Empty list = all users allowed
            return True
        return user_id in allowed

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.config.get("admin_users", [])

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def get_or_create_session(self, user_id: int) -> str:
        """Get existing session or create new one for user"""
        if user_id in self.sessions:
            return self.sessions[user_id]

        # Create new session via API
        api_url = self.config.get("api_url", "http://localhost:8002")
        session = await self.get_http_session()

        try:
            async with session.post(f"{api_url}/admin/chat/sessions") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    session_id = data["session"]["id"]
                    self.sessions[user_id] = session_id
                    self._save_sessions()
                    logger.info(f"Created new session {session_id} for user {user_id}")
                    return session_id
                else:
                    logger.error(f"Failed to create session: {resp.status}")
                    raise Exception("Failed to create session")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def send_message_to_ai(self, user_id: int, message: str) -> str:
        """Send message to AI and get response"""
        session_id = await self.get_or_create_session(user_id)
        api_url = self.config.get("api_url", "http://localhost:8002")
        session = await self.get_http_session()

        try:
            # Use streaming endpoint
            async with session.post(
                f"{api_url}/admin/chat/sessions/{session_id}/stream",
                json={"content": message},
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status != 200:
                    # Session might be invalid, try to recreate
                    if resp.status == 404:
                        del self.sessions[user_id]
                        self._save_sessions()
                        return await self.send_message_to_ai(user_id, message)
                    raise Exception(f"API error: {resp.status}")

                # Parse SSE response
                full_response = ""
                async for line in resp.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            if data.get("type") == "chunk" and data.get("content"):
                                full_response += data["content"]
                            elif data.get("type") in ("done", "assistant_message"):
                                break
                            elif data.get("type") == "error":
                                raise Exception(data.get("content", "Unknown error"))
                        except json.JSONDecodeError:
                            pass

                return full_response or "Не удалось получить ответ."

        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return self.config.get("error_message", DEFAULT_CONFIG["error_message"])
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return self.config.get("error_message", DEFAULT_CONFIG["error_message"])

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_id = user.id

        if not self.is_user_allowed(user_id):
            await update.message.reply_text(
                self.config.get("unauthorized_message", DEFAULT_CONFIG["unauthorized_message"])
            )
            logger.warning(f"Unauthorized user {user_id} ({user.username}) tried to access bot")
            return

        welcome = self.config.get("welcome_message", DEFAULT_CONFIG["welcome_message"])
        await update.message.reply_text(welcome)
        logger.info(f"User {user_id} ({user.username}) started bot")

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """Доступные команды:

/start - Начать диалог
/new - Начать новый диалог (очистить историю)
/help - Показать эту справку

Просто отправьте сообщение, и я отвечу."""

        await update.message.reply_text(help_text)

    async def handle_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /new command - start new conversation"""
        user_id = update.effective_user.id

        if not self.is_user_allowed(user_id):
            await update.message.reply_text(
                self.config.get("unauthorized_message", DEFAULT_CONFIG["unauthorized_message"])
            )
            return

        # Delete existing session
        if user_id in self.sessions:
            del self.sessions[user_id]
            self._save_sessions()

        await update.message.reply_text("Начинаем новый диалог. Чем могу помочь?")
        logger.info(f"User {user_id} started new conversation")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command (admin only)"""
        user_id = update.effective_user.id

        if not self.is_admin(user_id):
            return

        status = f"""📊 Статус бота:

🟢 Бот активен
👥 Активных сессий: {len(self.sessions)}
🔒 Режим доступа: {'Whitelist' if self.config.get('allowed_users') else 'Открытый'}
📍 API: {self.config.get('api_url')}"""

        await update.message.reply_text(status)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user = update.effective_user
        user_id = user.id
        message_text = update.message.text

        if not self.is_user_allowed(user_id):
            await update.message.reply_text(
                self.config.get("unauthorized_message", DEFAULT_CONFIG["unauthorized_message"])
            )
            logger.warning(f"Unauthorized message from {user_id}")
            return

        logger.info(f"Message from {user_id} ({user.username}): {message_text[:50]}...")

        # Show typing indicator
        if self.config.get("typing_enabled", True):
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )

        # Get AI response
        response = await self.send_message_to_ai(user_id, message_text)

        # Split long messages
        max_length = self.config.get("max_message_length", 4096)
        if len(response) > max_length:
            # Split by paragraphs or sentences
            parts = []
            current_part = ""
            for line in response.split("\n"):
                if len(current_part) + len(line) + 1 > max_length:
                    if current_part:
                        parts.append(current_part)
                    current_part = line
                else:
                    current_part += ("\n" if current_part else "") + line
            if current_part:
                parts.append(current_part)

            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response)

        logger.info(f"Sent response to {user_id}: {response[:50]}...")

    async def start(self):
        """Start the bot"""
        if not self.config.get("bot_token"):
            logger.error("Bot token not configured")
            return False

        if not self.config.get("enabled", False):
            logger.warning("Bot is disabled in config")
            return False

        try:
            self.app = Application.builder().token(self.config["bot_token"]).build()

            # Add handlers
            self.app.add_handler(CommandHandler("start", self.handle_start))
            self.app.add_handler(CommandHandler("help", self.handle_help))
            self.app.add_handler(CommandHandler("new", self.handle_new))
            self.app.add_handler(CommandHandler("status", self.handle_status))
            self.app.add_handler(MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            ))

            # Start polling
            self.running = True
            logger.info("🤖 Telegram bot starting...")

            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)

            logger.info("🤖 Telegram bot started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            self.running = False
            return False

    async def stop(self):
        """Stop the bot"""
        if self.app:
            logger.info("Stopping Telegram bot...")
            try:
                await self.app.updater.stop()
                await self.app.stop()
                await self.app.shutdown()
            except Exception as e:
                logger.error(f"Error stopping bot: {e}")

        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

        self.running = False
        logger.info("Telegram bot stopped")

    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            "running": self.running,
            "enabled": self.config.get("enabled", False),
            "has_token": bool(self.config.get("bot_token")),
            "active_sessions": len(self.sessions),
            "allowed_users_count": len(self.config.get("allowed_users", [])),
            "admin_users_count": len(self.config.get("admin_users", []))
        }


# Global instance
_bot_service: Optional[TelegramBotService] = None


def get_telegram_service() -> TelegramBotService:
    """Get or create Telegram bot service instance"""
    global _bot_service
    if _bot_service is None:
        _bot_service = TelegramBotService()
    return _bot_service


async def main():
    """Main entry point for standalone execution"""
    service = get_telegram_service()

    # Handle shutdown gracefully
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(service.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    if await service.start():
        # Keep running
        try:
            while service.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await service.stop()
    else:
        logger.error("Failed to start bot")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
