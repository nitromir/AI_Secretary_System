"""OpenAI-compatible tools/function calling support.

This module provides utilities to:
1. Convert tool definitions to system prompts for CLI tools
2. Parse AI responses to extract tool calls
3. Format tool calls in OpenAI's format
"""

import json
import logging
import re
import uuid
from typing import Any


logger = logging.getLogger(__name__)

# System prompt template for tool use
# Note: Double braces {{ }} are escaped - they become single braces in output
TOOL_SYSTEM_PROMPT = """You have access to the following tools/functions. When you need to use a tool, respond with a JSON object in this exact format:

```tool_call
{{
  "name": "function_name",
  "arguments": {{
    "param1": "value1",
    "param2": "value2"
  }}
}}
```

You can make multiple tool calls by including multiple ```tool_call``` blocks.

Available tools:
{tool_descriptions}

IMPORTANT RULES:
- ONLY use tools from the list above - do NOT invent or assume other tools exist
- If a tool you need is not listed, respond with text explaining what you need instead
- Always use the exact ```tool_call``` format when calling tools
- If you don't need to use a tool, respond normally without any tool_call blocks
- Arguments must be valid JSON matching the function's parameters schema
- Never use tools like "todo", "memory", "search" etc. unless explicitly listed above
"""

# Regex pattern to extract tool calls from response
TOOL_CALL_PATTERN = re.compile(r"```tool_call\s*\n?\s*(\{[\s\S]*?\})\s*\n?```", re.MULTILINE)


def generate_tool_descriptions(tools: list[dict[str, Any]]) -> str:
    """Generate human-readable tool descriptions for the system prompt.

    Args:
        tools: List of tool definitions in OpenAI format

    Returns:
        Formatted string describing all tools
    """
    descriptions = []

    for tool in tools:
        if tool.get("type") != "function":
            continue

        func = tool.get("function", {})
        name = func.get("name", "unknown")
        desc = func.get("description", "No description provided")
        params = func.get("parameters", {})

        # Build parameter description
        param_desc = ""
        if params and params.get("properties"):
            required = params.get("required", [])
            param_lines = []
            for param_name, param_info in params["properties"].items():
                param_type = param_info.get("type", "any")
                param_description = param_info.get("description", "")
                is_required = param_name in required
                req_marker = " (required)" if is_required else " (optional)"
                param_lines.append(
                    f"    - {param_name}: {param_type}{req_marker} - {param_description}"
                )
            param_desc = "\n  Parameters:\n" + "\n".join(param_lines)

        descriptions.append(f"- {name}: {desc}{param_desc}")

    return "\n\n".join(descriptions)


def create_tool_system_prompt(tools: list[dict[str, Any]], tool_choice: Any = None) -> str:
    """Create a system prompt that instructs the AI about available tools.

    Args:
        tools: List of tool definitions in OpenAI format
        tool_choice: Tool choice setting (none, auto, required, or specific function)

    Returns:
        System prompt string
    """
    if not tools:
        return ""

    tool_descriptions = generate_tool_descriptions(tools)
    prompt = TOOL_SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

    # Add tool_choice instructions
    if tool_choice == "none":
        prompt += "\n\nIMPORTANT: Do NOT use any tools. Respond with text only."
    elif tool_choice == "required":
        prompt += "\n\nIMPORTANT: You MUST use at least one tool in your response."
    elif isinstance(tool_choice, dict) and tool_choice.get("type") == "function":
        func_name = tool_choice.get("function", {}).get("name", "")
        if func_name:
            prompt += f"\n\nIMPORTANT: You MUST use the '{func_name}' tool in your response."

    return prompt


def parse_tool_calls(
    response_text: str,
    valid_tool_names: set[str] | None = None,
) -> tuple[list[dict[str, Any]], str]:
    """Parse tool calls from AI response.

    Args:
        response_text: The AI's response text
        valid_tool_names: Optional set of valid tool names. If provided,
            only tool calls with matching names are included. Hallucinated
            tools are logged and ignored. All tool_call blocks are still
            stripped from content regardless of validity.

    Returns:
        Tuple of (list of tool calls, remaining text content)
    """
    tool_calls = []

    # Find all tool_call blocks
    matches = TOOL_CALL_PATTERN.findall(response_text)

    for match in matches:
        try:
            # Parse the JSON
            call_data = json.loads(match)

            # Extract name and arguments
            name = call_data.get("name", "")
            arguments = call_data.get("arguments", {})

            if name:
                # Validate against provided tools if specified
                if valid_tool_names is not None and name not in valid_tool_names:
                    logger.warning(f"Ignoring hallucinated tool call: {name}")
                    continue

                tool_calls.append(
                    {
                        "id": f"call_{uuid.uuid4().hex[:12]}",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(arguments)
                            if isinstance(arguments, dict)
                            else str(arguments),
                        },
                    }
                )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse tool call JSON: {e}")
            continue

    # Remove ALL tool_call blocks from content (including invalid ones)
    remaining_text = TOOL_CALL_PATTERN.sub("", response_text).strip()

    return tool_calls, remaining_text


def format_tool_calls_response(
    tool_calls: list[dict[str, Any]], content: str | None = None
) -> dict[str, Any]:
    """Format tool calls for OpenAI-compatible response.

    Args:
        tool_calls: List of parsed tool calls
        content: Optional text content alongside tool calls

    Returns:
        Dict with content and tool_calls formatted for response
    """
    result = {
        "content": content if content else None,
        "tool_calls": tool_calls if tool_calls else None,
        "finish_reason": "tool_calls" if tool_calls else "stop",
    }

    return result


def has_tool_calls(response_text: str) -> bool:
    """Check if response contains tool calls.

    Args:
        response_text: The AI's response text

    Returns:
        True if tool calls are present
    """
    return bool(TOOL_CALL_PATTERN.search(response_text))


def format_tool_results_for_prompt(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert tool result messages to a format suitable for CLI prompts.

    Tool messages (role="tool") are converted to user messages that describe
    the tool execution results in a clear format the AI can understand.

    Args:
        messages: List of messages that may include tool results

    Returns:
        Messages with tool results formatted as user messages
    """
    formatted = []
    pending_tool_calls = {}  # tool_call_id -> tool_call info

    for msg in messages:
        role = msg.get("role")

        if role == "assistant" and msg.get("tool_calls"):
            # Store tool calls for reference
            for tc in msg.get("tool_calls", []):
                tc_id = tc.get("id")
                if tc_id:
                    pending_tool_calls[tc_id] = tc
            # Include the assistant message - use original content or skip if empty
            # (tool results that follow will provide the context)
            if msg.get("content"):
                formatted.append({"role": "assistant", "content": msg.get("content")})

        elif role == "tool":
            # Convert tool result to user message format
            tool_call_id = msg.get("tool_call_id")
            content = msg.get("content", "")

            # Try to find the matching tool call
            tool_call = pending_tool_calls.get(tool_call_id, {})
            func_info = tool_call.get("function", {})
            func_name = func_info.get("name", "unknown_function")

            # Format compactly - just function name and result
            # Avoid verbose format that might be echoed by CLI
            tool_result_text = f"[{func_name}] {content}"

            formatted.append({"role": "user", "content": tool_result_text})

        else:
            # Pass through other messages unchanged
            formatted.append(msg)

    return formatted


def _has_tool_instructions(messages: list[dict[str, Any]]) -> bool:
    """Check if messages already contain tool formatting instructions.

    Some clients (like AiderDesk) send comprehensive tool instructions.
    We skip adding our own prompt to avoid confusion/duplication.
    """
    if not messages:
        return False

    # Check system message for tool instruction patterns
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            # Look for signs of existing tool instructions
            if "```tool_call" in content or "tool_call```" in content:
                return True
            if "Available tools:" in content and "Parameters:" in content:
                return True
    return False


def prepare_messages_for_cli(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any = None,
) -> list[dict[str, Any]]:
    """Prepare messages for CLI by adding tool prompt and formatting tool results.

    Args:
        messages: Original messages
        tools: List of tool definitions
        tool_choice: Tool choice setting

    Returns:
        Messages ready for CLI consumption
    """
    # First, format any tool result messages
    formatted_messages = format_tool_results_for_prompt(messages)

    # Then add tool system prompt if tools are provided
    if not tools:
        return formatted_messages

    # Skip adding our tool prompt if client already provided tool instructions
    # (e.g., AiderDesk sends comprehensive prompts with tool_call format)
    if _has_tool_instructions(messages):
        logger.debug("Skipping tool prompt injection - client already provided instructions")
        return formatted_messages

    tool_prompt = create_tool_system_prompt(tools, tool_choice)
    if not tool_prompt:
        return formatted_messages

    # Prepend as system message or append to existing system message
    if formatted_messages and formatted_messages[0].get("role") == "system":
        formatted_messages = formatted_messages.copy()
        formatted_messages[0] = {
            **formatted_messages[0],
            "content": formatted_messages[0].get("content", "") + "\n\n" + tool_prompt,
        }
    else:
        formatted_messages = [{"role": "system", "content": tool_prompt}] + formatted_messages

    return formatted_messages
