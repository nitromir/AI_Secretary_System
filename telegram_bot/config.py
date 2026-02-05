"""Telegram bot configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class TelegramSettings(BaseSettings):
    """Telegram bot settings loaded from environment variables."""

    # Bot token from @BotFather
    bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")

    # Comma-separated list of allowed Telegram user IDs
    allowed_users: str = Field(default="", alias="TELEGRAM_ALLOWED_USERS")

    # Default model for new conversations
    default_model: str = Field(default="sonnet", alias="TELEGRAM_DEFAULT_MODEL")

    # System prompt for the assistant (inline or path to file)
    system_prompt: str = Field(
        default="You are a helpful assistant.", alias="TELEGRAM_SYSTEM_PROMPT"
    )

    # Path to system prompt file (overrides system_prompt if set)
    system_prompt_file: str | None = Field(default=None, alias="TELEGRAM_SYSTEM_PROMPT_FILE")

    def get_system_prompt(self) -> str:
        """Get system prompt from file or inline setting."""
        if self.system_prompt_file:
            try:
                with open(self.system_prompt_file, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                pass
        return self.system_prompt

    # Minimum interval between message edits during streaming (seconds)
    stream_edit_interval: float = Field(default=1.5, alias="TELEGRAM_STREAM_EDIT_INTERVAL")

    # Minimum new characters before editing message during streaming
    stream_edit_min_chars: int = Field(default=100, alias="TELEGRAM_STREAM_EDIT_MIN_CHARS")

    # Bridge connection
    bridge_url: str = Field(default="http://127.0.0.1:8000", alias="BRIDGE_URL")
    bridge_api_key: str | None = Field(default=None, alias="BRIDGE_API_KEY")

    # Session limits
    max_messages_per_session: int = Field(default=100, alias="TELEGRAM_MAX_MESSAGES")

    # Sales funnel settings
    sales_db_path: str = Field(default="sales.db", alias="SALES_DB_PATH")
    sales_admin_ids: str = Field(default="", alias="SALES_ADMIN_IDS")
    sales_github_repo: str = Field(
        default="ShaerWare/AI_Secretary_System", alias="SALES_GITHUB_REPO"
    )

    # Payment settings (Telegram Payments API)
    # Get token from @BotFather -> Payments -> select provider
    payment_provider_token: str | None = Field(default=None, alias="TELEGRAM_PAYMENT_TOKEN")
    # Price in kopecks (5000 RUB = 500000 kopecks)
    payment_price_basic: int = Field(
        default=500000,
        alias="PAYMENT_PRICE_BASIC",  # 5000 RUB
    )
    payment_currency: str = Field(default="RUB", alias="PAYMENT_CURRENCY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_admin_ids(self) -> set[int]:
        """Parse admin user IDs from comma-separated string."""
        if not self.sales_admin_ids.strip():
            return set()
        return {int(x.strip()) for x in self.sales_admin_ids.split(",") if x.strip().isdigit()}

    def get_allowed_user_ids(self) -> set[int]:
        """Parse allowed user IDs from comma-separated string."""
        if not self.allowed_users.strip():
            return set()
        ids = set()
        for part in self.allowed_users.split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return ids


@lru_cache
def get_telegram_settings() -> TelegramSettings:
    """Get cached telegram settings instance."""
    return TelegramSettings()
