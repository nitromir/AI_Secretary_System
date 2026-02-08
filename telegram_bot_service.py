#!/usr/bin/env python3
"""
Telegram Bot Service for AI Secretary
Connects Telegram users to the AI assistant

Supports multi-instance mode via BOT_INSTANCE_ID environment variable.
Each bot instance has its own configuration loaded from the database.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Dict, Optional

import aiohttp
from telegram import KeyboardButton, LabeledPrice, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from app.services.sales_funnel import SalesFunnelHandler


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
BOT_INSTANCE_ID = os.environ.get("BOT_INSTANCE_ID", "default")
CONFIG_FILE = Path(__file__).parent / "telegram_config.json"
SESSIONS_FILE = Path(__file__).parent / "telegram_sessions.json"

DEFAULT_CONFIG = {
    "enabled": False,
    "bot_token": "",
    "api_url": "http://localhost:8002",
    "allowed_users": [],  # Empty = all users allowed
    "admin_users": [],  # Users who can manage the bot
    "welcome_message": "Здравствуйте! Я AI-ассистент компании Шаервэй. Чем могу помочь?",
    "unauthorized_message": "Извините, у вас нет доступа к этому боту.",
    "error_message": "Произошла ошибка. Попробуйте позже.",
    "typing_enabled": True,
    "max_message_length": 4096,
}


class TelegramBotService:
    def __init__(self, instance_id: str = None):
        self.instance_id = instance_id or BOT_INSTANCE_ID
        self.config: Dict = {}
        self.sessions: Dict[int, str] = {}  # user_id -> session_id
        self.user_modes: Dict[int, Optional[str]] = {}  # user_id -> action_id or None
        self.action_buttons: list = []  # Action buttons configuration
        self.app: Optional[Application] = None
        self.running = False
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._config_loaded = False
        self.sales_funnel = SalesFunnelHandler(self.instance_id)

        logger.info(f"Initializing TelegramBotService for instance: {self.instance_id}")

    async def _load_config_from_api(self) -> Optional[Dict]:
        """Load configuration from API (database)."""
        api_url = os.environ.get("ORCHESTRATOR_API_URL", "http://localhost:8002")

        try:
            session = await self.get_http_session()
            endpoint = f"{api_url}/admin/telegram/instances/{self.instance_id}?include_token=true"

            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    instance = data.get("instance", {})

                    # Map instance fields to config format
                    config = {
                        "enabled": instance.get("enabled", False),
                        "bot_token": instance.get("bot_token", ""),
                        "api_url": api_url,
                        "allowed_users": instance.get("allowed_users", []),
                        "admin_users": instance.get("admin_users", []),
                        "welcome_message": instance.get(
                            "welcome_message", DEFAULT_CONFIG["welcome_message"]
                        ),
                        "unauthorized_message": instance.get(
                            "unauthorized_message", DEFAULT_CONFIG["unauthorized_message"]
                        ),
                        "error_message": instance.get(
                            "error_message", DEFAULT_CONFIG["error_message"]
                        ),
                        "typing_enabled": instance.get("typing_enabled", True),
                        "max_message_length": DEFAULT_CONFIG["max_message_length"],
                        # AI config
                        "llm_backend": instance.get("llm_backend", "vllm"),
                        "llm_persona": instance.get("llm_persona", "anna"),
                        "system_prompt": instance.get("system_prompt"),
                        "llm_params": instance.get("llm_params", {}),
                        "tts_engine": instance.get("tts_engine", "xtts"),
                        "tts_voice": instance.get("tts_voice", "anna"),
                        # Action buttons
                        "action_buttons": instance.get("action_buttons", []),
                        # Payment
                        "payment_enabled": instance.get("payment_enabled", False),
                        "yookassa_provider_token": instance.get("yookassa_provider_token"),
                        "stars_enabled": instance.get("stars_enabled", False),
                        "payment_products": instance.get("payment_products", []),
                        "payment_success_message": instance.get(
                            "payment_success_message",
                            "Спасибо за оплату! Ваш платёж успешно обработан.",
                        ),
                        # YooMoney
                        "yoomoney_wallet_id": instance.get("yoomoney_wallet_id"),
                        "yoomoney_configured": instance.get("yoomoney_configured", False),
                    }

                    logger.info(f"Loaded config from API for instance {self.instance_id}")
                    return config
                elif resp.status == 404:
                    logger.warning(f"Instance {self.instance_id} not found in database")
                else:
                    logger.warning(f"Failed to load config from API: {resp.status}")

        except Exception as e:
            logger.warning(f"Could not load config from API: {e}")

        return None

    def _load_config_from_file(self) -> Dict:
        """Load configuration from legacy file (fallback for 'default' instance)."""
        if self.instance_id == "default" and CONFIG_FILE.exists():
            try:
                config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return {**DEFAULT_CONFIG, **config}
            except Exception as e:
                logger.error(f"Error loading config from file: {e}")
        return DEFAULT_CONFIG.copy()

    async def load_config(self) -> Dict:
        """Load configuration (API first, then file fallback)."""
        # Try API first
        config = await self._load_config_from_api()

        if config is None:
            # Fallback to file for default instance
            config = self._load_config_from_file()
            logger.info(f"Using file-based config for instance {self.instance_id}")

        self.config = config
        self.action_buttons = config.get("action_buttons", [])
        self._config_loaded = True
        return config

    def _save_config(self, config: Dict):
        """Save configuration to file (only for default instance)."""
        if self.instance_id == "default":
            CONFIG_FILE.write_text(
                json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        self.config = config

    def _load_sessions(self) -> Dict[int, str]:
        """Load user sessions from file (legacy, only for default instance)."""
        if self.instance_id == "default" and SESSIONS_FILE.exists():
            try:
                data = json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
                # Convert string keys back to int
                return {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Error loading sessions: {e}")
        return {}

    def _save_sessions(self):
        """Save user sessions to file (legacy, only for default instance)."""
        if self.instance_id == "default":
            SESSIONS_FILE.write_text(
                json.dumps(self.sessions, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    async def reload_config(self):
        """Reload configuration from API/file"""
        await self.load_config()
        logger.info(f"Configuration reloaded for instance {self.instance_id}")

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

    def get_main_keyboard(self) -> Optional[ReplyKeyboardMarkup]:
        """Build reply keyboard with enabled action buttons."""
        enabled_buttons = [b for b in self.action_buttons if b.get("enabled", True)]

        # Add payment button if payments are enabled
        has_payment = self.config.get("payment_enabled") and (
            self.config.get("stars_enabled")
            or self.config.get("yookassa_provider_token")
            or self.config.get("yoomoney_configured")
        )

        if not enabled_buttons and not has_payment:
            return None

        # Sort by order (handle None values explicitly)
        enabled_buttons.sort(key=lambda x: x.get("order") if x.get("order") is not None else 0)

        # Create rows of buttons (2 per row)
        keyboard = []
        row = []
        for button in enabled_buttons:
            icon = button.get("icon", "")
            label = f"{icon} {button['label']}" if icon else button["label"]
            row.append(KeyboardButton(label))
            if len(row) >= 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        # Add payment button as separate row
        if has_payment:
            keyboard.append([KeyboardButton("💳 Оплата")])

        return ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True,
            one_time_keyboard=False,
        )

    def find_button_by_label(self, text: str) -> Optional[dict]:
        """Find action button by displayed label text."""
        text = text.strip()
        for button in self.action_buttons:
            if not button.get("enabled", True):
                continue
            icon = button.get("icon", "")
            label = f"{icon} {button['label']}" if icon else button["label"]
            if text == label.strip():
                return button
        return None

    def get_user_mode(self, user_id: int) -> Optional[str]:
        """Get user's current action mode."""
        return self.user_modes.get(user_id)

    def set_user_mode(self, user_id: int, mode_id: Optional[str]):
        """Set user's current action mode."""
        if mode_id is None:
            self.user_modes.pop(user_id, None)
        else:
            self.user_modes[user_id] = mode_id

    async def get_llm_config_for_user_async(self, user_id: int) -> dict:
        """Get LLM configuration based on user's segment prompt or action mode."""
        # Priority 1: Action button mode (explicitly selected by user)
        action_id = self.user_modes.get(user_id)
        if action_id:
            for button in self.action_buttons:
                if button["id"] == action_id:
                    return {
                        "llm_backend": button.get("llm_backend")
                        or self.config.get("llm_backend", "vllm"),
                        "system_prompt": button.get("system_prompt")
                        or self.config.get("system_prompt"),
                        "llm_params": button.get("llm_params") or self.config.get("llm_params", {}),
                    }

        # Priority 2: Segment-based agent prompt (from sales funnel quiz)
        try:
            segment_prompt = await self.sales_funnel.get_prompt_for_user(user_id)
            if segment_prompt:
                return {
                    "llm_backend": self.config.get("llm_backend", "vllm"),
                    "system_prompt": segment_prompt["system_prompt"],
                    "llm_params": {
                        "temperature": segment_prompt.get("temperature", 0.7),
                        "max_tokens": segment_prompt.get("max_tokens", 1024),
                    },
                }
        except Exception as e:
            logger.debug(f"Could not get segment prompt for user {user_id}: {e}")

        # Priority 3: Default bot config
        return {
            "llm_backend": self.config.get("llm_backend", "vllm"),
            "system_prompt": self.config.get("system_prompt"),
            "llm_params": self.config.get("llm_params", {}),
        }

    def get_llm_config_for_user(self, user_id: int) -> dict:
        """Sync fallback — returns default config (async version preferred)."""
        action_id = self.user_modes.get(user_id)
        if action_id:
            for button in self.action_buttons:
                if button["id"] == action_id:
                    return {
                        "llm_backend": button.get("llm_backend")
                        or self.config.get("llm_backend", "vllm"),
                        "system_prompt": button.get("system_prompt")
                        or self.config.get("system_prompt"),
                        "llm_params": button.get("llm_params") or self.config.get("llm_params", {}),
                    }
        return {
            "llm_backend": self.config.get("llm_backend", "vllm"),
            "system_prompt": self.config.get("system_prompt"),
            "llm_params": self.config.get("llm_params", {}),
        }

    async def get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def get_or_create_session(self, user_id: int, user_info: Dict = None) -> str:
        """Get existing session or create new one for user."""
        if user_id in self.sessions:
            return self.sessions[user_id]

        # Create new session via API
        api_url = self.config.get("api_url", "http://localhost:8002")
        session = await self.get_http_session()

        user_info = user_info or {}
        username = user_info.get("username", "")
        first_name = user_info.get("first_name", "")

        title = f"Telegram: {first_name or username or user_id}"
        if self.instance_id != "default":
            title = f"[{self.instance_id}] {title}"

        try:
            # Create chat session
            async with session.post(
                f"{api_url}/admin/chat/sessions",
                json={
                    "title": title,
                    "system_prompt": self.config.get("system_prompt"),
                    "source": "telegram",
                    "source_id": f"{self.instance_id}:{user_id}",
                },
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    session_id = data["session"]["id"]
                    self.sessions[user_id] = session_id
                    self._save_sessions()

                    # Also store in telegram_sessions table with bot_id
                    try:
                        await session.post(
                            f"{api_url}/admin/telegram/instances/{self.instance_id}/sessions",
                            json={
                                "user_id": user_id,
                                "chat_session_id": session_id,
                                "username": username,
                                "first_name": first_name,
                                "last_name": user_info.get("last_name", ""),
                            },
                        )
                    except Exception as e:
                        logger.warning(f"Failed to register telegram session: {e}")

                    logger.info(
                        f"Created new session {session_id} for user {user_id} in bot {self.instance_id}"
                    )
                    return session_id
                else:
                    error_text = await resp.text()
                    logger.error(f"Failed to create session: {resp.status} - {error_text}")
                    raise Exception(f"Failed to create session: {resp.status}")
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def send_message_to_ai(
        self, user_id: int, message: str, user_info: Dict = None, llm_config: Dict = None
    ) -> str:
        """Send message to AI and get response"""
        session_id = await self.get_or_create_session(user_id, user_info=user_info)
        api_url = self.config.get("api_url", "http://localhost:8002")
        session = await self.get_http_session()

        try:
            # Build request payload
            payload = {"content": message}

            # Add LLM override if in action mode
            if llm_config:
                payload["llm_override"] = llm_config

            # Use streaming endpoint
            async with session.post(
                f"{api_url}/admin/chat/sessions/{session_id}/stream",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
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
                    line = line.decode("utf-8").strip()
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

        except TimeoutError:
            logger.error("Request timeout")
            return self.config.get("error_message", DEFAULT_CONFIG["error_message"])
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return self.config.get("error_message", DEFAULT_CONFIG["error_message"])

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command — sales funnel welcome with quiz CTA."""
        user = update.effective_user
        user_id = user.id

        if not self.is_user_allowed(user_id):
            await update.message.reply_text(
                self.config.get("unauthorized_message", DEFAULT_CONFIG["unauthorized_message"])
            )
            logger.warning(f"Unauthorized user {user_id} ({user.username}) tried to access bot")
            return

        # Reset user mode to default
        self.set_user_mode(user_id, None)

        # Log start event
        await self.sales_funnel.log_start_event(user_id)

        # Build welcome with social proof + quiz CTA (inline keyboard)
        welcome = await self.sales_funnel.build_welcome_message(user.first_name)
        inline_kb = self.sales_funnel.build_welcome_keyboard()

        # Send welcome with inline keyboard
        await update.message.reply_text(welcome, reply_markup=inline_kb)

        # Also send reply keyboard for action buttons (if configured)
        keyboard = self.get_main_keyboard()
        if keyboard:
            await update.message.reply_text("Или выберите действие:", reply_markup=keyboard)

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

        # Reset user mode to default
        self.set_user_mode(user_id, None)

        keyboard = self.get_main_keyboard()
        await update.message.reply_text(
            "Начинаем новый диалог. Чем могу помочь?", reply_markup=keyboard
        )
        logger.info(f"User {user_id} started new conversation")

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command (admin only)"""
        user_id = update.effective_user.id

        if not self.is_admin(user_id):
            return

        status = f"""📊 Статус бота:

🟢 Бот активен
👥 Активных сессий: {len(self.sessions)}
🔒 Режим доступа: {"Whitelist" if self.config.get("allowed_users") else "Открытый"}
📍 API: {self.config.get("api_url")}"""

        await update.message.reply_text(status)

    async def handle_action_button(self, user_id: int, button: dict, update: Update) -> None:
        """Handle action button press - switch mode and notify user."""
        action_id = button["id"]

        if action_id == "main_menu":
            # Reset to default mode
            self.set_user_mode(user_id, None)
            keyboard = self.get_main_keyboard()
            await update.message.reply_text(
                "Возврат в главное меню. Чем могу помочь?", reply_markup=keyboard
            )
            logger.info(f"User {user_id} returned to main menu")
            return

        # Switch to action mode
        self.set_user_mode(user_id, action_id)

        # Send confirmation with action-specific hint
        icon = button.get("icon", "")
        label = button.get("label", action_id)
        keyboard = self.get_main_keyboard()

        await update.message.reply_text(
            f"{icon} Режим: {label}\n\nОпишите ваш запрос.", reply_markup=keyboard
        )
        logger.info(f"User {user_id} switched to mode: {action_id}")

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callback queries (quiz, actions, subscribe)."""
        query = update.callback_query
        if not query or not query.data:
            return

        user_id = query.from_user.id
        data = query.data

        if data == "quiz:start":
            # Start the segmentation quiz
            await query.answer()
            started = await self.sales_funnel.start_quiz(update, user_id)
            if not started:
                await query.message.reply_text("Квиз пока не настроен. Задайте любой вопрос!")
            return

        if data == "quiz:skip":
            # Skip quiz, go to free chat
            await query.answer()
            await query.message.reply_text(
                "Хорошо! Задайте любой вопрос о проекте AI Secretary.",
                reply_markup=self.get_main_keyboard(),
            )
            return

        if data.startswith("quiz:"):
            # Quiz answer callback
            segment_key = await self.sales_funnel.handle_quiz_callback(update, context)
            if segment_key:
                # Quiz completed — show segment result
                text, buttons = await self.sales_funnel.build_segment_result_message(segment_key)
                await query.message.reply_text(text, reply_markup=buttons)

                # Also show the reply keyboard
                keyboard = self.get_main_keyboard()
                if keyboard:
                    await query.message.reply_text("Или задайте вопрос:", reply_markup=keyboard)
            return

        if data.startswith("action:"):
            # Action callback (subscribe, hardware_audit, roi_calc, etc.)
            response = await self.sales_funnel.handle_action_callback(update, context)
            if response:
                await query.message.reply_text(response, reply_markup=self.get_main_keyboard())
            return

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

        # Check if message matches an action button
        button = self.find_button_by_label(message_text)
        if button:
            await self.handle_action_button(user_id, button, update)
            return

        # Check if payment button clicked
        if message_text.strip() in ("💳 Оплата", "/pay"):
            await self.handle_pay(update, context)
            return

        logger.info(
            f"[{self.instance_id}] Message from {user_id} ({user.username}): {message_text[:50]}..."
        )

        # Show typing indicator
        if self.config.get("typing_enabled", True):
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING
            )

        # Prepare user info for session creation
        user_info = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

        # Get LLM config for this user's current mode
        llm_config = await self.get_llm_config_for_user_async(user_id)

        # Get AI response
        response = await self.send_message_to_ai(
            user_id, message_text, user_info=user_info, llm_config=llm_config
        )

        # Split long messages
        max_length = self.config.get("max_message_length", 4096)
        keyboard = self.get_main_keyboard()
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

            for i, part in enumerate(parts):
                # Attach keyboard to the last part only
                if i == len(parts) - 1:
                    await update.message.reply_text(part, reply_markup=keyboard)
                else:
                    await update.message.reply_text(part)
        else:
            await update.message.reply_text(response, reply_markup=keyboard)

        logger.info(f"Sent response to {user_id}: {response[:50]}...")

    # ============== Payment Handlers ==============

    async def handle_pay(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /pay command — show available payment products."""
        user_id = update.effective_user.id
        if not self.is_user_allowed(user_id):
            return

        if not self.config.get("payment_enabled"):
            await update.message.reply_text(
                "Оплата временно недоступна.",
                reply_markup=self.get_main_keyboard(),
            )
            return

        products = self.config.get("payment_products", [])
        if not products:
            await update.message.reply_text(
                "Нет доступных услуг для оплаты.",
                reply_markup=self.get_main_keyboard(),
            )
            return

        for product in products:
            if self.config.get("stars_enabled"):
                await self._send_stars_invoice(update, product)
            elif self.config.get("yookassa_provider_token"):
                await self._send_yookassa_invoice(update, product)
            elif self.config.get("yoomoney_configured"):
                await self._send_yoomoney_link(update, product)
            else:
                await update.message.reply_text(
                    "Платёжная система не настроена.",
                    reply_markup=self.get_main_keyboard(),
                )
                return

    async def _send_stars_invoice(self, update: Update, product: dict):
        """Send Telegram Stars invoice."""
        price_stars = product.get("price_stars", 100)
        await update.message.reply_invoice(
            title=product.get("title", "Услуга"),
            description=product.get("description", ""),
            payload=f"stars_{product.get('id', 'unknown')}_{update.effective_user.id}",
            provider_token="",  # Empty string for Telegram Stars
            currency="XTR",
            prices=[LabeledPrice(label=product.get("title", "Услуга"), amount=price_stars)],
        )

    async def _send_yookassa_invoice(self, update: Update, product: dict):
        """Send YooKassa invoice."""
        provider_token = self.config.get("yookassa_provider_token", "")
        price_rub = product.get("price_rub", 50000)  # in kopecks (500.00 RUB)
        await update.message.reply_invoice(
            title=product.get("title", "Услуга"),
            description=product.get("description", ""),
            payload=f"yookassa_{product.get('id', 'unknown')}_{update.effective_user.id}",
            provider_token=provider_token,
            currency="RUB",
            prices=[LabeledPrice(label=product.get("title", "Услуга"), amount=price_rub)],
        )

    async def _send_yoomoney_link(self, update: Update, product: dict):
        """Send YooMoney quickpay link as inline button."""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        from app.services.yoomoney_service import build_quickpay_url

        wallet_id = self.config.get("yoomoney_wallet_id", "")
        if not wallet_id:
            await update.message.reply_text(
                "Платёжная система настраивается. Попробуйте позже.",
                reply_markup=self.get_main_keyboard(),
            )
            return

        price_rub = product.get("price_rub", 50000)  # kopecks
        amount = price_rub / 100  # convert to rubles
        user_id = update.effective_user.id
        label = f"{self.instance_id}_{product.get('id', 'pay')}_{user_id}"

        pay_url = build_quickpay_url(
            wallet_id=wallet_id,
            amount=amount,
            label=label,
            target=product.get("title", "Оплата услуги"),
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        f"💳 Оплатить {amount:.0f} ₽ — {product.get('title', 'Услуга')}",
                        url=pay_url,
                    )
                ]
            ]
        )

        await update.message.reply_text(
            f"💳 **{product.get('title', 'Услуга')}**\n\n"
            f"{product.get('description', '')}\n\n"
            f"Сумма: **{amount:.0f} ₽**\n\n"
            "Нажмите кнопку ниже для оплаты через ЮMoney:",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    async def handle_precheckout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle PreCheckoutQuery — MUST answer within 10 seconds."""
        query = update.pre_checkout_query
        await query.answer(ok=True)
        logger.info(f"Pre-checkout approved for user {query.from_user.id}: {query.invoice_payload}")

    async def handle_successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle successful payment confirmation."""
        payment = update.message.successful_payment
        user = update.effective_user

        # Parse payload: "stars_consultation_12345" or "yookassa_consultation_12345"
        payload = payment.invoice_payload
        parts = payload.split("_", 2)
        payment_type = parts[0] if parts else "unknown"
        product_id = parts[1] if len(parts) > 1 else "unknown"

        logger.info(
            f"Payment received: user={user.id}, type={payment_type}, "
            f"product={product_id}, amount={payment.total_amount} {payment.currency}"
        )

        # Log payment via API
        try:
            session = await self.get_http_session()
            api_url = self.config.get("api_url", "http://localhost:8002")
            await session.post(
                f"{api_url}/admin/telegram/instances/{self.instance_id}/payments",
                json={
                    "user_id": user.id,
                    "username": user.username,
                    "payment_type": payment_type,
                    "product_id": product_id,
                    "amount": payment.total_amount,
                    "currency": payment.currency,
                    "telegram_payment_id": payment.telegram_payment_charge_id,
                    "provider_payment_id": payment.provider_payment_charge_id,
                },
            )
        except Exception as e:
            logger.error(f"Failed to log payment: {e}")

        # Send success message
        success_msg = self.config.get(
            "payment_success_message",
            "Спасибо за оплату! Ваш платёж успешно обработан.",
        )
        await update.message.reply_text(
            success_msg,
            reply_markup=self.get_main_keyboard(),
        )

    async def start(self):
        """Start the bot"""
        # Load config if not already loaded
        if not self._config_loaded:
            await self.load_config()

        # Load sessions from file (legacy, for default instance)
        self.sessions = self._load_sessions()

        if not self.config.get("bot_token"):
            logger.error(f"Bot token not configured for instance {self.instance_id}")
            return False

        if not self.config.get("enabled", False):
            logger.warning(f"Bot is disabled in config for instance {self.instance_id}")
            return False

        try:
            self.app = Application.builder().token(self.config["bot_token"]).build()

            # Add handlers
            self.app.add_handler(CommandHandler("start", self.handle_start))
            self.app.add_handler(CommandHandler("help", self.handle_help))
            self.app.add_handler(CommandHandler("new", self.handle_new))
            self.app.add_handler(CommandHandler("status", self.handle_status))
            self.app.add_handler(CommandHandler("pay", self.handle_pay))

            # Inline keyboard callback handler (quiz, actions, subscribe)
            self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))

            # Payment handlers (must be before general message handler)
            self.app.add_handler(PreCheckoutQueryHandler(self.handle_precheckout))
            self.app.add_handler(
                MessageHandler(filters.SUCCESSFUL_PAYMENT, self.handle_successful_payment)
            )

            self.app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
            )

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
            "instance_id": self.instance_id,
            "running": self.running,
            "enabled": self.config.get("enabled", False),
            "has_token": bool(self.config.get("bot_token")),
            "active_sessions": len(self.sessions),
            "allowed_users_count": len(self.config.get("allowed_users", [])),
            "admin_users_count": len(self.config.get("admin_users", [])),
        }


# Global instances (one per instance_id)
_bot_services: Dict[str, TelegramBotService] = {}


def get_telegram_service(instance_id: str = None) -> TelegramBotService:
    """Get or create Telegram bot service instance"""
    instance_id = instance_id or BOT_INSTANCE_ID

    if instance_id not in _bot_services:
        _bot_services[instance_id] = TelegramBotService(instance_id=instance_id)
    return _bot_services[instance_id]


async def main():
    """Main entry point for standalone execution"""
    instance_id = BOT_INSTANCE_ID
    logger.info(f"Starting Telegram bot service for instance: {instance_id}")

    service = get_telegram_service(instance_id)

    # Handle shutdown gracefully
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info(f"Shutdown signal received for instance {instance_id}")
        asyncio.create_task(service.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    if await service.start():
        # Keep running
        logger.info(f"Bot instance {instance_id} started successfully")
        try:
            while service.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await service.stop()
    else:
        logger.error(f"Failed to start bot instance {instance_id}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
