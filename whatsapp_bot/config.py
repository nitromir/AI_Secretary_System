"""WhatsApp bot configuration."""

import logging
import os
from dataclasses import dataclass
from functools import lru_cache

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class WhatsAppSettings(BaseSettings):
    """WhatsApp bot settings loaded from environment variables."""

    # WhatsApp Cloud API credentials
    phone_number_id: str = Field(default="", alias="WHATSAPP_PHONE_NUMBER_ID")
    access_token: str = Field(default="", alias="WHATSAPP_ACCESS_TOKEN")
    verify_token: str = Field(default="", alias="WHATSAPP_VERIFY_TOKEN")
    app_secret: str = Field(default="", alias="WHATSAPP_APP_SECRET")

    # Graph API version
    api_version: str = Field(default="v21.0", alias="WHATSAPP_API_VERSION")

    # Webhook server
    webhook_host: str = Field(default="0.0.0.0", alias="WHATSAPP_WEBHOOK_HOST")
    webhook_port: int = Field(default=8003, alias="WHATSAPP_WEBHOOK_PORT")

    # Default model for new conversations
    default_model: str = Field(default="sonnet", alias="WHATSAPP_DEFAULT_MODEL")

    # System prompt for the assistant
    system_prompt: str = Field(
        default="You are a helpful assistant.", alias="WHATSAPP_SYSTEM_PROMPT"
    )

    # Session limits
    max_messages_per_session: int = Field(default=100, alias="WHATSAPP_MAX_MESSAGES")

    # Orchestrator connection
    orchestrator_url: str = Field(default="http://localhost:8002", alias="ORCHESTRATOR_URL")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_whatsapp_settings() -> WhatsAppSettings:
    """Get cached WhatsApp settings instance."""
    return WhatsAppSettings()


# ─── Multi-instance config ───────────────────────────────────────────────


@dataclass
class WhatsAppBotConfig:
    """Dynamic bot configuration loaded from orchestrator API.

    Used in multi-instance mode when WA_INSTANCE_ID is set.
    """

    instance_id: str
    phone_number_id: str
    access_token: str
    verify_token: str
    app_secret: str
    name: str = "WhatsApp Bot"
    llm_backend: str = "vllm"
    system_prompt: str | None = None
    tts_enabled: bool = False
    tts_preset_id: str | None = None
    rate_limit_count: int = 30
    rate_limit_hours: int = 1
    auto_start: bool = False

    # Merged settings for convenience
    max_messages_per_session: int = 100
    api_version: str = "v21.0"
    webhook_port: int = 8003


def get_wa_instance_id() -> str | None:
    """Get WA_INSTANCE_ID from environment."""
    return os.environ.get("WA_INSTANCE_ID")


def get_orchestrator_url() -> str:
    """Get orchestrator URL from environment."""
    return os.environ.get("ORCHESTRATOR_URL", "http://localhost:8002")


async def load_config_from_api(instance_id: str) -> WhatsAppBotConfig:
    """Load WhatsApp bot configuration from orchestrator API.

    Args:
        instance_id: WhatsApp instance ID from database

    Returns:
        WhatsAppBotConfig with all settings from API

    Raises:
        httpx.HTTPError: If API request fails
    """
    api_url = get_orchestrator_url()
    url = f"{api_url}/admin/whatsapp/instances/{instance_id}"

    logger.info(f"Loading WhatsApp config from API: {url}")

    headers = {}
    internal_token = os.environ.get("WA_INTERNAL_TOKEN")
    if internal_token:
        headers["Authorization"] = f"Bearer {internal_token}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params={"include_token": "true"}, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    instance = data["instance"]

    return WhatsAppBotConfig(
        instance_id=instance["id"],
        phone_number_id=instance["phone_number_id"],
        access_token=instance["access_token"],
        verify_token=instance.get("verify_token", ""),
        app_secret=instance.get("app_secret", ""),
        name=instance.get("name", "WhatsApp Bot"),
        llm_backend=instance.get("llm_backend", "vllm"),
        system_prompt=instance.get("system_prompt"),
        tts_enabled=instance.get("tts_enabled", False),
        tts_preset_id=instance.get("tts_preset_id"),
        rate_limit_count=instance.get("rate_limit_count", 30),
        rate_limit_hours=instance.get("rate_limit_hours", 1),
        auto_start=instance.get("auto_start", False),
    )
