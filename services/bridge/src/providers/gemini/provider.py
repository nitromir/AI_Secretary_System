"""Gemini CLI provider implementation."""

import asyncio
import codecs
import json
import logging
from typing import Any, AsyncIterator

from ...config import get_settings
from ...utils.content import extract_content
from ...utils.subprocess import create_subprocess
from ..base import BaseProvider


logger = logging.getLogger(__name__)


class GeminiProvider(BaseProvider):
    """Provider for Gemini CLI.

    Note: Gemini CLI is an agentic CLI tool, not a direct LLM wrapper.
    Some OpenAI parameters (temperature, top_p, top_k, system_prompt)
    are not supported as they're not exposed by the CLI.

    Supported parameters:
    - model: Model name via -m/--model
    - stream: Via -o/--output-format stream-json
    - thinking: Via auto-selecting thinking-enabled models

    Thinking Mode (via model selection):
    Gemini CLI doesn't expose a thinkingBudget parameter directly.
    Workaround: When thinking is enabled, auto-switch to thinking models:
    - gemini-2.0-flash-thinking-exp (experimental thinking model)
    - gemini-2.5-pro (has built-in reasoning capabilities)

    Unsupported (not exposed by CLI):
    - temperature, top_p, top_k
    - system_prompt (workaround: prepended to prompt)
    """

    name = "gemini"

    # Default model list (used if GEMINI_MODELS env var is empty)
    DEFAULT_MODELS = [
        # Gemini 3 (latest - Dec 2025)
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        # Gemini 2.5
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # Gemini 2.0
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        # Gemini 1.5
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        # Legacy
        "gemini-pro",
    ]

    # Mapping from base models to their thinking-enabled variants
    THINKING_MODEL_MAP = {
        "gemini-2.5-flash": "gemini-3-flash-preview",
        "gemini-2.5-flash-lite": "gemini-3-flash-preview",
        "gemini-2.0-flash": "gemini-3-flash-preview",
        "gemini-2.0-flash-lite": "gemini-3-flash-preview",
        "gemini-1.5-flash": "gemini-3-flash-preview",
        "gemini-1.5-pro": "gemini-3-flash-preview",
        "gemini-pro": "gemini-3-flash-preview",
    }

    # Models with native thinking/reasoning capabilities
    THINKING_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-pro",  # Pro models have reasoning
    ]

    def __init__(self, cli_path: str = "gemini"):
        self.cli_path = cli_path
        self.settings = get_settings()

    def supports_streaming(self) -> bool:
        return True

    def supports_thinking(self) -> bool:
        # Supported via model selection (auto-switch to thinking models)
        return True

    def _get_thinking_model(
        self,
        model: str,
        thinking: dict[str, Any] | None,
    ) -> str:
        """
        Get appropriate model for thinking mode.

        Args:
            model: Requested model
            thinking: Thinking config with 'enabled' flag

        Returns:
            Model name (possibly upgraded to thinking variant)
        """
        if not thinking or not thinking.get("enabled"):
            return model

        # Already a thinking model
        if model in self.THINKING_MODELS:
            return model

        # Map to thinking variant
        thinking_model = self.THINKING_MODEL_MAP.get(model)
        if thinking_model:
            logger.info(f"Thinking enabled: switching {model} -> {thinking_model}")
            return thinking_model

        # No mapping available, use default thinking model
        logger.warning(f"No thinking variant for {model}, using gemini-2.0-flash-thinking-exp")
        return "gemini-2.0-flash-thinking-exp"

    def _get_configured_models(self) -> list[str]:
        """Get models from settings or use defaults."""
        if self.settings.gemini_models:
            return [m.strip() for m in self.settings.gemini_models.split(",") if m.strip()]
        return self.DEFAULT_MODELS

    def get_models(self) -> list[str]:
        return self._get_configured_models()

    async def list_models(self) -> list[str]:
        return self._get_configured_models()

    def _format_messages(self, messages: list[dict[str, Any]]) -> str:
        """
        Format messages into a single prompt.

        Note: Gemini CLI doesn't support system prompts or conversation
        history directly. We format everything as a single prompt with
        clear role markers that the model understands.
        """
        system_parts = []
        conversation_parts = []

        for msg in messages:
            role = msg.get("role", "user")
            raw_content = msg.get("content", "")
            content = extract_content(raw_content)

            if role == "system":
                system_parts.append(content)
            elif role == "user":
                conversation_parts.append(f"[User]: {content}")
            elif role == "assistant":
                conversation_parts.append(f"[Assistant]: {content}")

        # Build the final prompt
        parts = []

        # Add system prompt as a structured preamble
        if system_parts:
            system_content = " ".join(system_parts)
            parts.append(f"<system>{system_content}</system>")

        # Add conversation history and current message
        # Use a clear conversation format the model can follow
        if conversation_parts:
            # For multi-turn, add context instruction
            if len(conversation_parts) > 1:
                parts.append("<conversation>")
                parts.append(" ".join(conversation_parts))
                parts.append("</conversation>")
                parts.append("[Assistant]:")
            else:
                # Single message - just send it directly
                # Strip the [User]: prefix for single messages
                single_msg = conversation_parts[0]
                if single_msg.startswith("[User]: "):
                    parts.append(single_msg[8:])
                else:
                    parts.append(single_msg)

        return " ".join(parts)

    def _normalize_model(self, model: str) -> str:
        """Strip provider prefix from model name if present."""
        if model.startswith("gemini:"):
            return model[7:]  # Remove "gemini:" prefix
        return model

    def _build_command(
        self,
        model: str,
        stream: bool = False,
        **kwargs: Any,
    ) -> list[str]:
        """Build CLI command with correct Gemini CLI parameters."""
        cmd = [self.cli_path]

        # Model selection - strip provider prefix if present
        normalized_model = self._normalize_model(model)
        cmd.extend(["-m", normalized_model])

        # Output format
        if stream:
            cmd.extend(["-o", "stream-json"])
        else:
            cmd.extend(["-o", "json"])

        # Permission level settings
        permission_level = self.settings.gemini_permission_level.lower()
        if permission_level == "chat":
            # Chat-only: NO local operations - pure LLM text completion
            # Disables all tools: no file access, no shell, no web - safe for Aider/clients
            cmd.extend(["--allowed-tools", ""])
        elif permission_level == "readonly":
            # Read-only: only allow read operations
            cmd.extend(["--allowed-tools", "read_file,list_directory,grep,find_files"])
            cmd.extend(["--approval-mode", "default"])
        elif permission_level == "edit":
            # Edit: auto-approve edits, but not shell commands
            cmd.extend(["--approval-mode", "auto_edit"])
        else:  # full
            # Full: auto-approve everything (yolo mode)
            cmd.extend(["--approval-mode", "yolo"])

        # Note: --sandbox requires Docker/Podman, so we rely on working directory
        # isolation via create_subprocess's sandbox dir instead

        # Note: prompt is passed via stdin to avoid command-line length limits

        return cmd

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model: str,
        stream: bool = False,
        thinking: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
        """Generate completion using Gemini CLI."""

        # Select thinking model if thinking is enabled
        effective_model = self._get_thinking_model(model, thinking)

        prompt = self._format_messages(messages)
        cmd = self._build_command(effective_model, stream, **kwargs)

        logger.debug(f"Running command: {' '.join(cmd)} (prompt via stdin, {len(prompt)} chars)")

        if stream:
            return self._stream_complete(cmd, model, prompt)
        else:
            return await self._sync_complete(cmd, model, prompt)

    async def _sync_complete(
        self,
        cmd: list[str],
        model: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Non-streaming completion."""
        try:
            process = await create_subprocess(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=prompt.encode()),
                timeout=self.settings.cli_timeout,
            )

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Gemini CLI error: {error_msg}")
                raise RuntimeError(f"Gemini CLI failed: {error_msg}")

            output = stdout.decode().strip()

            # Parse JSON output - find the JSON object in the output
            # (CLI may output startup messages before the JSON)
            try:
                # Find the start of JSON object
                json_start = output.find("{")
                if json_start == -1:
                    return {
                        "content": output,
                        "thinking": None,
                    }

                json_str = output[json_start:]
                data = json.loads(json_str)

                # Extract content from Gemini's JSON format
                # The response is in the "response" field
                content = data.get("response", "")
                return {
                    "content": content,
                    "thinking": None,
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw output
                return {
                    "content": output,
                    "thinking": None,
                }

        except asyncio.TimeoutError:
            logger.error("Gemini CLI timeout")
            raise

    async def _stream_complete(
        self,
        cmd: list[str],
        model: str,
        prompt: str,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming completion using stream-json format."""
        try:
            process = await create_subprocess(
                cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Write prompt to stdin and close it
            process.stdin.write(prompt.encode())
            await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()

            buffer = ""
            decoder = codecs.getincrementaldecoder("utf-8")("replace")

            while True:
                chunk = await asyncio.wait_for(
                    process.stdout.read(1024),
                    timeout=self.settings.stream_timeout,
                )

                if not chunk:
                    # Flush any remaining bytes
                    buffer += decoder.decode(b"", final=True)
                    break

                buffer += decoder.decode(chunk)

                # Parse JSON lines from stream-json format
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        msg_type = data.get("type")
                        role = data.get("role")
                        is_delta = data.get("delta", False)

                        # Only output assistant message deltas
                        # Skip: init, user messages, non-delta messages
                        if msg_type == "message" and role == "assistant" and is_delta:
                            content = data.get("content", "")
                            if content:
                                yield {
                                    "content": content,
                                    "thinking": None,
                                    "done": False,
                                }
                    except json.JSONDecodeError:
                        # Skip non-JSON lines (CLI startup messages, etc.)
                        logger.debug(f"Skipping non-JSON line: {line[:50]}")

            # Final chunk
            yield {
                "content": None,
                "thinking": None,
                "done": True,
            }

            await process.wait()

        except asyncio.TimeoutError:
            logger.error("Gemini CLI stream timeout")
            raise
