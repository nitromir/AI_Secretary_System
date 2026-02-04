"""Token counting utilities."""

import logging
from typing import Any


logger = logging.getLogger("cli_bridge.tokens")

# Lazy import tiktoken to avoid import errors if not installed
_tiktoken = None


def _get_tiktoken():
    """Lazy load tiktoken."""
    global _tiktoken
    if _tiktoken is None:
        try:
            import tiktoken

            _tiktoken = tiktoken
        except ImportError:
            logger.warning("tiktoken not installed, token counting will use approximations")
            _tiktoken = False
    return _tiktoken


class TokenCounter:
    """
    Token counter supporting multiple model families.

    Uses tiktoken for accurate counting when available,
    falls back to character-based approximation otherwise.
    """

    # Model family to tiktoken encoding mapping
    ENCODING_MAP = {
        # OpenAI models
        "gpt-4": "cl100k_base",
        "gpt-4o": "o200k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "o1": "o200k_base",
        "o1-mini": "o200k_base",
        "o1-preview": "o200k_base",
        # Claude models (use cl100k as approximation - similar tokenizer)
        "claude": "cl100k_base",
        "sonnet": "cl100k_base",
        "opus": "cl100k_base",
        "haiku": "cl100k_base",
        # Gemini (use cl100k as approximation)
        "gemini": "cl100k_base",
    }

    # Average characters per token for approximation (when tiktoken unavailable)
    CHARS_PER_TOKEN = 4

    def __init__(self):
        self._encodings: dict[str, Any] = {}

    def _get_encoding(self, model: str) -> Any | None:
        """Get tiktoken encoding for a model."""
        tiktoken = _get_tiktoken()
        if not tiktoken:
            return None

        # Find encoding name for model
        encoding_name = None
        model_lower = model.lower()
        for prefix, enc in self.ENCODING_MAP.items():
            if model_lower.startswith(prefix):
                encoding_name = enc
                break

        if not encoding_name:
            # Default to cl100k_base for unknown models
            encoding_name = "cl100k_base"

        # Cache encodings
        if encoding_name not in self._encodings:
            try:
                self._encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.warning(f"Failed to get encoding {encoding_name}: {e}")
                return None

        return self._encodings[encoding_name]

    def count_text(self, text: str, model: str = "gpt-4") -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for
            model: Model name for tokenizer selection

        Returns:
            Token count
        """
        if not text:
            return 0

        encoding = self._get_encoding(model)
        if encoding:
            try:
                return len(encoding.encode(text))
            except Exception as e:
                logger.warning(f"Token encoding failed, using approximation: {e}")

        # Fallback: character-based approximation
        return len(text) // self.CHARS_PER_TOKEN

    def count_messages(
        self,
        messages: list[dict[str, Any]],
        model: str = "gpt-4",
    ) -> int:
        """
        Count tokens in a list of messages.

        Accounts for message formatting overhead (role, separators).

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name for tokenizer selection

        Returns:
            Total token count
        """
        total = 0

        # Per-message overhead (varies by model, using conservative estimate)
        message_overhead = 4  # <role>, content, separators

        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total += self.count_text(content, model)
            elif isinstance(content, list):
                # Multi-part content (e.g., with images)
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        total += self.count_text(part.get("text", ""), model)
            total += message_overhead

        # Conversation overhead
        total += 3  # conversation framing tokens

        return total

    def estimate_response_tokens(self, text: str, model: str = "gpt-4") -> int:
        """
        Estimate tokens in a response text.

        Args:
            text: Response text
            model: Model name

        Returns:
            Estimated token count
        """
        return self.count_text(text, model)


# Singleton instance
_counter: TokenCounter | None = None


def get_token_counter() -> TokenCounter:
    """Get the token counter singleton."""
    global _counter
    if _counter is None:
        _counter = TokenCounter()
    return _counter


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Convenience function to count tokens in text."""
    return get_token_counter().count_text(text, model)


def count_message_tokens(messages: list[dict[str, Any]], model: str = "gpt-4") -> int:
    """Convenience function to count tokens in messages."""
    return get_token_counter().count_messages(messages, model)
