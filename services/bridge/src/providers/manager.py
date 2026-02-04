"""Provider manager for routing requests to appropriate CLI providers."""

import logging
from typing import TYPE_CHECKING

from ..config import get_settings
from ..models import Model


if TYPE_CHECKING:
    from .base import BaseProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Manages CLI providers and routes requests."""

    def __init__(self):
        self._providers: dict[str, "BaseProvider"] = {}
        self._model_to_provider: dict[str, str] = {}
        self._initialized = False

    def _initialize(self):
        """Initialize providers lazily."""
        if self._initialized:
            return

        settings = get_settings()

        # Import providers here to avoid circular imports
        from .claude.provider import ClaudeProvider
        from .gemini.provider import GeminiProvider
        from .gpt.provider import GPTProvider

        # Register providers
        self._providers = {
            "claude": ClaudeProvider(settings.claude_cli_path),
            "gemini": GeminiProvider(settings.gemini_cli_path),
            "gpt": GPTProvider(settings.gpt_cli_path),
        }

        # Build model -> provider mapping
        for provider_name, provider in self._providers.items():
            for model in provider.get_models():
                self._model_to_provider[model] = provider_name

        self._initialized = True

    def get_provider(self, model: str) -> "BaseProvider | None":
        """Get provider for a model."""
        self._initialize()

        # Check direct model match
        if model in self._model_to_provider:
            provider_name = self._model_to_provider[model]
            return self._providers.get(provider_name)

        # Check provider prefix (e.g., "claude:sonnet" -> claude provider)
        if ":" in model:
            provider_name = model.split(":")[0]
            return self._providers.get(provider_name)

        # Check if model name contains provider hint
        model_lower = model.lower()
        for provider_name in self._providers:
            if provider_name in model_lower:
                return self._providers.get(provider_name)

        return None

    async def list_all_models(self) -> list[Model]:
        """List all available models from all providers.

        If HIDE_UNAVAILABLE_MODELS is enabled, only includes models from
        CLIs that are accessible.
        """
        self._initialize()
        settings = get_settings()

        # Check which CLIs are available (if filtering is enabled)
        available_providers = set(self._providers.keys())
        if settings.hide_unavailable_models:
            from ..utils.health import check_all_clis

            statuses = await check_all_clis(settings)
            available_providers = {name for name, status in statuses.items() if status.available}
            if len(available_providers) < len(self._providers):
                unavailable = set(self._providers.keys()) - available_providers
                logger.debug(f"Hiding models for unavailable CLIs: {unavailable}")

        models = []
        for provider in self._providers.values():
            if provider.name not in available_providers:
                continue
            for model_id in provider.get_models():
                models.append(
                    Model(
                        id=model_id,
                        owned_by=provider.name,
                        supports_streaming=provider.supports_streaming(),
                        supports_thinking=provider.supports_thinking(),
                    )
                )
        return models


# Singleton instance
_manager: ProviderManager | None = None


def _get_manager() -> ProviderManager:
    """Get or create provider manager singleton."""
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager


def get_provider_for_model(model: str) -> "BaseProvider | None":
    """Get provider for a given model."""
    return _get_manager().get_provider(model)


async def get_all_models() -> list[Model]:
    """Get all available models."""
    return await _get_manager().list_all_models()
