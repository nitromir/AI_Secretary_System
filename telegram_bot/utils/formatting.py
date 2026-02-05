"""Markdown → Telegram MarkdownV2 conversion utilities."""

# Characters that must be escaped in MarkdownV2 (outside of code blocks)
_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2.

    Handles code blocks (``` and `) by leaving their contents unescaped.
    """
    result: list[str] = []
    i = 0
    length = len(text)

    while i < length:
        # Fenced code block ```
        if text[i : i + 3] == "```":
            end = text.find("```", i + 3)
            if end == -1:
                # Unclosed — treat rest as code block
                result.append(text[i:])
                break
            result.append(text[i : end + 3])
            i = end + 3
            continue

        # Inline code `
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end == -1:
                result.append(text[i:])
                break
            result.append(text[i : end + 1])
            i = end + 1
            continue

        # Regular character — escape if needed
        if text[i] in _ESCAPE_CHARS:
            result.append(f"\\{text[i]}")
        else:
            result.append(text[i])
        i += 1

    return "".join(result)
