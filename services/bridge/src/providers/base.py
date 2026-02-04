"""Base provider interface for CLI tools."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class BaseProvider(ABC):
    """Abstract base class for CLI provider implementations."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
        """
        Generate a completion from messages.

        Args:
            messages: List of chat messages in OpenAI format
            model: Model identifier
            stream: Whether to stream the response
            thinking: Thinking mode configuration (if supported)
            **kwargs: Additional provider-specific parameters

        Returns:
            Complete response dict or async iterator of chunks
        """
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """
        Return available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming responses."""
        pass

    @abstractmethod
    def supports_thinking(self) -> bool:
        """Whether this provider supports thinking/reasoning mode."""
        pass

    @abstractmethod
    def get_models(self) -> list[str]:
        """Return list of model IDs this provider supports."""
        pass

    def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: Model identifier

        Returns:
            Model information dict
        """
        return {
            "id": model,
            "object": "model",
            "owned_by": self.name,
        }
