"""Application settings and configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server
    host: str = Field(default="0.0.0.0", alias="BRIDGE_HOST")
    port: int = Field(default=8000, alias="BRIDGE_PORT")
    debug: bool = Field(default=False, alias="BRIDGE_DEBUG")

    # Authentication (optional - if set, requires Bearer token)
    api_key: str | None = Field(default=None, alias="BRIDGE_API_KEY")

    # CLI paths
    claude_cli_path: str = Field(default="claude", alias="CLAUDE_CLI_PATH")
    gemini_cli_path: str = Field(default="gemini", alias="GEMINI_CLI_PATH")
    gpt_cli_path: str = Field(default="sgpt", alias="GPT_CLI_PATH")

    # Global timeouts (seconds) - used as defaults
    cli_timeout: int = Field(default=300, alias="CLI_TIMEOUT")
    stream_timeout: int = Field(default=600, alias="STREAM_TIMEOUT")

    # Per-provider timeouts (seconds) - override global if set
    claude_timeout: int | None = Field(default=None, alias="CLAUDE_TIMEOUT")
    gemini_timeout: int | None = Field(default=None, alias="GEMINI_TIMEOUT")
    gpt_timeout: int | None = Field(default=None, alias="GPT_TIMEOUT")

    # Retry settings
    retry_enabled: bool = Field(default=True, alias="RETRY_ENABLED")
    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    retry_delay: float = Field(default=1.0, alias="RETRY_DELAY")
    retry_backoff: float = Field(default=2.0, alias="RETRY_BACKOFF")

    # Caching
    cache_enabled: bool = Field(default=False, alias="CACHE_ENABLED")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")  # seconds
    cache_max_size: int = Field(default=1000, alias="CACHE_MAX_SIZE")

    # Metrics
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=False, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")  # requests per window
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # window in seconds

    # Request queue (for managing concurrent CLI requests)
    queue_enabled: bool = Field(default=True, alias="QUEUE_ENABLED")
    queue_max_size: int = Field(
        default=50, alias="QUEUE_MAX_SIZE"
    )  # max pending requests per provider
    queue_timeout: int = Field(
        default=300, alias="QUEUE_TIMEOUT"
    )  # max wait+execute time (seconds)
    queue_default_concurrent: int = Field(default=2, alias="QUEUE_DEFAULT_CONCURRENT")
    queue_claude_concurrent: int = Field(default=2, alias="QUEUE_CLAUDE_CONCURRENT")
    queue_gemini_concurrent: int = Field(default=3, alias="QUEUE_GEMINI_CONCURRENT")
    queue_gpt_concurrent: int = Field(default=2, alias="QUEUE_GPT_CONCURRENT")

    # CLI Permission Levels (per provider)
    # Levels: chat, readonly, edit, full
    #   - chat: Pure text completion only - NO local operations whatsoever
    #           (no file access, no shell, no tools - ideal for Aider/LLM clients)
    #   - readonly: Only read operations (view files, search)
    #   - edit: Read + file edits, no shell commands
    #   - full: All operations allowed (default)
    claude_permission_level: str = Field(default="full", alias="CLAUDE_PERMISSION_LEVEL")
    gemini_permission_level: str = Field(default="full", alias="GEMINI_PERMISSION_LEVEL")
    gpt_permission_level: str = Field(default="full", alias="GPT_PERMISSION_LEVEL")

    # Conversation Summarization (for providers without native sessions)
    # When enabled, long conversations are summarized to reduce token usage
    summarize_enabled: bool = Field(default=False, alias="SUMMARIZE_ENABLED")
    summarize_threshold: int = Field(
        default=50, alias="SUMMARIZE_THRESHOLD"
    )  # messages before summarizing
    summarize_keep_recent: int = Field(
        default=4, alias="SUMMARIZE_KEEP_RECENT"
    )  # messages to keep verbatim
    # Provider for summarization: "auto" = same as request, or specific provider (claude, gemini, gpt)
    summarize_provider: str = Field(default="auto", alias="SUMMARIZE_PROVIDER")

    # Custom model lists (comma-separated, empty = use defaults)
    # Example: CLAUDE_MODELS=sonnet,opus,haiku,claude-opus-4-5-20251101
    claude_models: str = Field(default="", alias="CLAUDE_MODELS")
    gemini_models: str = Field(default="", alias="GEMINI_MODELS")
    gpt_models: str = Field(default="", alias="GPT_MODELS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_requests: bool = Field(default=True, alias="LOG_REQUESTS")

    # Health check settings
    health_check_on_startup: bool = Field(default=True, alias="HEALTH_CHECK_ON_STARTUP")
    hide_unavailable_models: bool = Field(default=False, alias="HIDE_UNAVAILABLE_MODELS")

    # Optional API keys (not used for CLI bridge, but reserved)
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_provider_timeout(self, provider: str) -> int:
        """Get timeout for a specific provider."""
        provider_timeouts = {
            "claude": self.claude_timeout,
            "gemini": self.gemini_timeout,
            "gpt": self.gpt_timeout,
        }
        return provider_timeouts.get(provider) or self.cli_timeout


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
