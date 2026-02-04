"""GPT CLI (Shell-GPT) provider implementation."""

import asyncio
import logging
from typing import Any, AsyncIterator

from ...config import get_settings
from ...utils.content import extract_content
from ...utils.subprocess import create_subprocess
from ..base import BaseProvider


logger = logging.getLogger(__name__)


class GPTProvider(BaseProvider):
    """Provider for GPT via Shell-GPT CLI."""

    name = "gpt"

    # Default model list (used if GPT_MODELS env var is empty)
    DEFAULT_MODELS = [
        # GPT-4o (latest)
        "gpt-4o",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        # GPT-4 Turbo
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-turbo-preview",
        # GPT-4
        "gpt-4",
        "gpt-4-0613",
        # GPT-3.5
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        # O1 reasoning models
        "o1",
        "o1-2024-12-17",
        "o1-preview",
        "o1-preview-2024-09-12",
        "o1-mini",
        "o1-mini-2024-09-12",
        # O3 (newest)
        "o3-mini",
        "o3-mini-2025-01-31",
    ]

    def __init__(self, cli_path: str = "sgpt"):
        self.cli_path = cli_path
        self.settings = get_settings()

    def supports_streaming(self) -> bool:
        return True

    def supports_thinking(self) -> bool:
        # GPT doesn't have native thinking mode like Claude
        return False

    def _get_configured_models(self) -> list[str]:
        """Get models from settings or use defaults."""
        if self.settings.gpt_models:
            return [m.strip() for m in self.settings.gpt_models.split(",") if m.strip()]
        return self.DEFAULT_MODELS

    def get_models(self) -> list[str]:
        return self._get_configured_models()

    async def list_models(self) -> list[str]:
        return self._get_configured_models()

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """Format messages into a prompt for Shell-GPT."""
        parts = []

        for msg in messages:
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            content = extract_content(raw_content)

            if role == "system":
                # Shell-GPT handles system prompts differently
                parts.append(f"[System: {content}]")
            elif role == "user":
                parts.append(content)
            elif role == "assistant":
                parts.append(f"Assistant: {content}")

        return "\n\n".join(parts)

    def _normalize_model(self, model: str) -> str:
        """Strip provider prefix from model name if present."""
        if model.startswith("gpt:"):
            return model[4:]  # Remove "gpt:" prefix
        return model

    def _build_command(
        self,
        prompt: str,
        model: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Build CLI command."""
        cmd = [self.cli_path]

        # Model selection - strip provider prefix if present
        normalized_model = self._normalize_model(model)
        cmd.extend(["--model", normalized_model])

        # Disable shell mode (we want chat mode)
        cmd.append("--no-shell")

        # Add the prompt
        cmd.append(prompt)

        return cmd

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
        """Generate completion using Shell-GPT."""

        prompt = self._format_messages(messages)
        cmd = self._build_command(prompt, model, stream, **kwargs)

        logger.debug(f"Running command: {' '.join(cmd)}")

        if stream:
            return self._stream_complete(cmd, model)
        else:
            return await self._sync_complete(cmd, model)

    async def _sync_complete(
        self,
        cmd: list[str],
        model: str,
    ) -> dict[str, Any]:
        """Non-streaming completion."""
        try:
            process = await create_subprocess(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.settings.cli_timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Shell-GPT error: {error_msg}")
                raise RuntimeError(f"Shell-GPT failed: {error_msg}")

            content = stdout.decode().strip()

            return {
                "content": content,
                "thinking": None,
            }

        except asyncio.TimeoutError:
            logger.error("Shell-GPT timeout")
            raise

    async def _stream_complete(
        self,
        cmd: list[str],
        model: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming completion."""
        try:
            process = await create_subprocess(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            while True:
                chunk = await asyncio.wait_for(
                    process.stdout.read(100),
                    timeout=self.settings.stream_timeout,
                )

                if not chunk:
                    break

                text = chunk.decode()
                yield {
                    "content": text,
                    "thinking": None,
                    "done": False,
                }

            yield {
                "content": None,
                "thinking": None,
                "done": True,
            }

            await process.wait()

        except asyncio.TimeoutError:
            logger.error("Shell-GPT stream timeout")
            raise
