"""Conversation summarization for token optimization.

When conversations grow long, this module provides utilities to summarize
older messages while keeping recent ones verbatim. This reduces token
usage for providers without native session support.
"""

import logging
from typing import Any


logger = logging.getLogger(__name__)

# Prompt for generating conversation summaries
SUMMARIZE_PROMPT = """Summarize the following conversation concisely. Focus on:
- Key topics discussed
- Important decisions or conclusions
- Relevant context needed for continuation

Keep the summary brief but comprehensive enough to continue the conversation meaningfully.

Conversation to summarize:
{conversation}

Provide only the summary, no additional commentary."""


def format_messages_for_summary(messages: list[dict[str, Any]]) -> str:
    """Format messages into a string for summarization.

    Args:
        messages: List of messages to format

    Returns:
        Formatted conversation string
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Handle content that might be a list (multi-modal)
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
                elif isinstance(item, str):
                    text_parts.append(item)
            content = " ".join(text_parts)

        if content:
            if role == "system":
                parts.append(f"[System]: {content}")
            elif role == "user":
                parts.append(f"[User]: {content}")
            elif role == "assistant":
                parts.append(f"[Assistant]: {content}")

    return "\n\n".join(parts)


async def generate_summary(
    messages: list[dict[str, Any]],
    provider,
    model: str | None = None,
) -> str:
    """Generate a summary of the given messages.

    Args:
        messages: Messages to summarize
        provider: Provider instance to use for summarization
        model: Optional model override

    Returns:
        Summary string
    """
    conversation_text = format_messages_for_summary(messages)
    prompt = SUMMARIZE_PROMPT.format(conversation=conversation_text)

    try:
        result = await provider.complete(
            messages=[{"role": "user", "content": prompt}],
            model=model or "sonnet",  # Default to fast model
            stream=False,
        )
        summary = result.get("content", "").strip()
        logger.info(f"Generated summary: {len(summary)} chars from {len(messages)} messages")
        return summary
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        # Return a basic fallback
        return f"[Conversation of {len(messages)} messages]"


def needs_summarization(
    messages: list[dict[str, Any]],
    threshold: int,
    existing_summary_index: int = 0,
) -> bool:
    """Check if conversation needs summarization.

    Args:
        messages: Current messages
        threshold: Message count threshold for summarization
        existing_summary_index: Index up to which we already have a summary

    Returns:
        True if summarization is needed
    """
    # Count non-system messages (system prompts don't count toward threshold)
    non_system_count = sum(1 for m in messages if m.get("role") != "system")

    # Check if we have enough new messages since last summary
    new_messages_count = non_system_count - existing_summary_index

    return new_messages_count >= threshold


def apply_summary_to_messages(
    messages: list[dict[str, Any]],
    summary: str,
    keep_recent: int,
) -> list[dict[str, Any]]:
    """Apply summary to messages, keeping recent ones verbatim.

    Args:
        messages: Full message list
        summary: Generated summary of older messages
        keep_recent: Number of recent messages to keep verbatim

    Returns:
        Condensed message list with summary
    """
    if not messages:
        return messages

    # Separate system messages (always keep them)
    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if len(non_system_messages) <= keep_recent:
        # Not enough messages to summarize
        return messages

    # Keep the last N non-system messages
    recent_messages = non_system_messages[-keep_recent:]

    # Build condensed message list
    result = system_messages.copy()

    # Add summary as a system context message
    if summary:
        result.append({"role": "system", "content": f"[Previous conversation summary]\n{summary}"})

    # Add recent messages
    result.extend(recent_messages)

    logger.debug(
        f"Applied summary: {len(messages)} messages -> {len(result)} messages "
        f"(kept {keep_recent} recent)"
    )

    return result


def get_messages_to_summarize(
    messages: list[dict[str, Any]],
    keep_recent: int,
    existing_summary_index: int = 0,
) -> list[dict[str, Any]]:
    """Get messages that need to be summarized.

    Args:
        messages: Full message list
        keep_recent: Number of recent messages to keep
        existing_summary_index: Index up to which we already have a summary

    Returns:
        Messages to summarize (excluding system and recent)
    """
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    if len(non_system_messages) <= keep_recent:
        return []

    # Get messages to summarize (from after existing summary to before recent)
    messages_to_summarize = non_system_messages[existing_summary_index:-keep_recent]

    return messages_to_summarize
