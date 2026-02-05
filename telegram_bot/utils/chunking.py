"""Split long text into Telegram-safe chunks (<=4096 characters)."""

TG_MSG_LIMIT = 4096


def split_message(text: str, limit: int = TG_MSG_LIMIT) -> list[str]:
    """Split *text* into parts no longer than *limit* characters.

    Strategy:
    1. Try to split on double newlines (paragraph boundaries).
    2. Fall back to single newlines.
    3. Fall back to hard cut at *limit*.
    """
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break

        # Try to find a good split point
        chunk = remaining[:limit]
        split_idx = _find_split(chunk)
        parts.append(remaining[:split_idx].rstrip())
        remaining = remaining[split_idx:].lstrip("\n")

    return parts


def _find_split(chunk: str) -> int:
    """Find the best split index within *chunk*."""
    limit = len(chunk)

    # Prefer double newline (paragraph break)
    idx = chunk.rfind("\n\n")
    if idx > limit // 4:
        return idx

    # Single newline
    idx = chunk.rfind("\n")
    if idx > limit // 4:
        return idx

    # Space
    idx = chunk.rfind(" ")
    if idx > limit // 4:
        return idx

    # Hard cut
    return limit
