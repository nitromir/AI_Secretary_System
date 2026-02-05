# Bot Sync Architecture: claude-telegram-bridge → AI Secretary System

## Overview

This document describes how to sync the Telegram bot from `claude-telegram-bridge` repository to `AI_Secretary_System`, with a key modification: **Claude is used ONLY for TZ generation**, everything else uses local Qwen 2.5.

---

## LLM Routing Strategy

```
                    INCOMING MESSAGE
                           │
                           ▼
              ┌────────────────────────┐
              │    INTENT CLASSIFIER   │
              │  (rule-based, fast)    │
              └───────────┬────────────┘
                          │
    ┌─────────────────────┼─────────────────────┐
    │                     │                     │
    ▼                     ▼                     ▼
┌─────────┐        ┌─────────────┐       ┌─────────────┐
│ CLAUDE  │        │   QWEN      │       │   QWEN      │
│  (5%)   │        │ NEWS (10%)  │       │ OTHER (85%) │
├─────────┤        ├─────────────┤       ├─────────────┤
│ TZ gen  │        │ SMM posts   │       │ Chat        │
│ Custom  │        │ PR → News   │       │ FAQ         │
│ quotes  │        │             │       │ Support     │
└─────────┘        └─────────────┘       └─────────────┘
```

### When to use Claude (expensive, smart)

| Trigger | Function | Reason |
|---------|----------|--------|
| `_generate_tz()` | TZ generation | Complex document, needs reasoning |
| Custom discovery | Quote generation | Business analysis |

### When to use Qwen (free, fast)

| Trigger | Function | Reason |
|---------|----------|--------|
| `generate_news_post()` | SMM posts | Template-based, low complexity |
| `on_text_message()` | General chat | FAQ, support, simple questions |
| `handle_callback_query()` | Sales funnel | State machine, no AI needed |
| Everything else | — | Default backend |

---

## File Mapping

### Source (claude-telegram-bridge) → Target (AI_Secretary_System)

```
claude-telegram-bridge/               AI_Secretary_System/
│                                     │
├── src/telegram/                     ├── telegram_bot/           # NEW MODULE
│   ├── bot.py                        │   ├── bot.py
│   ├── config.py                     │   ├── config.py
│   ├── handlers/                     │   ├── handlers/
│   │   ├── messages.py               │   │   ├── messages.py
│   │   ├── tz.py                     │   │   ├── tz.py         # Uses Claude
│   │   ├── news.py                   │   │   ├── news.py       # Uses Qwen
│   │   ├── commands.py               │   │   ├── commands.py
│   │   ├── callbacks.py              │   │   ├── callbacks.py
│   │   └── sales/                    │   │   └── sales/
│   │       ├── welcome.py            │   │       ├── welcome.py
│   │       ├── quiz.py               │   │       ├── quiz.py
│   │       ├── diy.py                │   │       ├── diy.py
│   │       ├── basic.py              │   │       ├── basic.py
│   │       ├── custom.py             │   │       ├── custom.py
│   │       └── payment.py            │   │       └── payment.py
│   ├── services/                     │   ├── services/
│   │   ├── bridge_client.py          │   │   ├── llm_router.py   # NEW: Claude/Qwen router
│   │   ├── session_store.py          │   │   ├── session_store.py
│   │   ├── github_news.py            │   │   ├── github_news.py  # Modified: uses Qwen
│   │   └── social_proof.py           │   │   └── social_proof.py
│   ├── sales/                        │   ├── sales/
│   │   ├── database.py               │   │   ├── database.py
│   │   ├── keyboards.py              │   │   ├── keyboards.py
│   │   ├── states.py                 │   │   ├── states.py
│   │   ├── texts.py                  │   │   ├── texts.py
│   │   └── segments.py               │   │   └── segments.py
│   └── prompts/                      │   └── prompts/
│       └── smm_news.md               │       └── smm_news.md
│                                     │
└── .env.example                      ├── telegram_bot/.env.example
                                      │
                                      └── (existing)
                                          ├── telegram_bot_service.py  # LEGACY
                                          ├── multi_bot_manager.py     # Keep for multi-instance
                                          └── app/services/sales_funnel.py
```

---

## LLM Router Service

### New file: `telegram_bot/services/llm_router.py`

```python
"""
LLM Router — routes requests to Claude or Qwen based on task type.

Cost optimization:
- Claude (Claude Code CLI bridge): TZ generation, complex analysis
- Qwen (vLLM local): Everything else (news, chat, FAQ, support)
"""

import logging
from enum import Enum
from typing import AsyncIterator

logger = logging.getLogger(__name__)


class LLMBackend(Enum):
    CLAUDE = "claude"  # Claude Code CLI bridge
    QWEN = "qwen"      # Local Qwen 2.5 via vLLM


class LLMRouter:
    """Routes LLM requests to appropriate backend."""

    def __init__(
        self,
        orchestrator_url: str = "http://localhost:8002",
        claude_provider_id: str = "claude-bridge",
    ):
        self.orchestrator_url = orchestrator_url.rstrip("/")
        self.claude_provider_id = claude_provider_id
        self._http_client = None

    async def _get_client(self):
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client

    async def generate(
        self,
        messages: list[dict],
        backend: LLMBackend = LLMBackend.QWEN,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """
        Generate response using specified backend.

        Args:
            messages: Chat messages in OpenAI format
            backend: Which LLM to use
            stream: Whether to stream response

        Yields:
            Response chunks (or full response if stream=False)
        """
        client = await self._get_client()

        # Determine backend string for API
        if backend == LLMBackend.CLAUDE:
            llm_backend = f"cloud:{self.claude_provider_id}"
        else:
            llm_backend = "vllm"

        # Create temporary session and send message
        # (simplified — in production use proper session management)
        payload = {
            "content": messages[-1]["content"],  # Last user message
            "llm_override": {
                "llm_backend": llm_backend,
                "system_prompt": messages[0]["content"] if messages[0]["role"] == "system" else None,
            }
        }

        # Use streaming endpoint
        endpoint = f"{self.orchestrator_url}/admin/chat/sessions/temp/stream"

        async with client.stream("POST", endpoint, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    import json
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "chunk" and data.get("content"):
                            yield data["content"]
                        elif data.get("type") in ("done", "assistant_message"):
                            break
                    except json.JSONDecodeError:
                        pass

    async def generate_tz(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """Generate TZ document using Claude (expensive, but smart)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        full_text = ""
        async for chunk in self.generate(messages, backend=LLMBackend.CLAUDE):
            full_text += chunk

        return full_text.strip()

    async def generate_news_post(
        self,
        system_prompt: str,
        user_message: str,
    ) -> str:
        """Generate news post using Qwen (cheap, fast)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        full_text = ""
        async for chunk in self.generate(messages, backend=LLMBackend.QWEN):
            full_text += chunk

        return full_text.strip()

    async def chat(
        self,
        messages: list[dict],
    ) -> AsyncIterator[str]:
        """General chat using Qwen."""
        async for chunk in self.generate(messages, backend=LLMBackend.QWEN):
            yield chunk

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton
_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router
```

---

## Sync Script

### `scripts/sync_telegram_bot.py`

```python
#!/usr/bin/env python3
"""
Sync Telegram bot from claude-telegram-bridge to AI_Secretary_System.

Usage:
    python scripts/sync_telegram_bot.py [--source /path/to/claude-telegram-bridge]

This script:
1. Copies files from source repo
2. Replaces bridge_client with llm_router
3. Modifies imports to use local orchestrator API
"""

import argparse
import re
import shutil
from pathlib import Path

SOURCE_REPO = Path("/tmp/claude-telegram-bridge")
TARGET_DIR = Path(__file__).parent.parent / "telegram_bot"

# Files to copy (source -> target)
FILE_MAPPING = {
    "src/telegram/bot.py": "bot.py",
    "src/telegram/config.py": "config.py",
    "src/telegram/handlers/__init__.py": "handlers/__init__.py",
    "src/telegram/handlers/messages.py": "handlers/messages.py",
    "src/telegram/handlers/commands.py": "handlers/commands.py",
    "src/telegram/handlers/callbacks.py": "handlers/callbacks.py",
    "src/telegram/handlers/tz.py": "handlers/tz.py",
    "src/telegram/handlers/news.py": "handlers/news.py",
    "src/telegram/handlers/files.py": "handlers/files.py",
    "src/telegram/handlers/sales/__init__.py": "handlers/sales/__init__.py",
    "src/telegram/handlers/sales/welcome.py": "handlers/sales/welcome.py",
    "src/telegram/handlers/sales/quiz.py": "handlers/sales/quiz.py",
    "src/telegram/handlers/sales/diy.py": "handlers/sales/diy.py",
    "src/telegram/handlers/sales/basic.py": "handlers/sales/basic.py",
    "src/telegram/handlers/sales/custom.py": "handlers/sales/custom.py",
    "src/telegram/handlers/sales/common.py": "handlers/sales/common.py",
    "src/telegram/handlers/sales/payment.py": "handlers/sales/payment.py",
    "src/telegram/services/__init__.py": "services/__init__.py",
    "src/telegram/services/session_store.py": "services/session_store.py",
    "src/telegram/services/github_news.py": "services/github_news.py",
    "src/telegram/services/social_proof.py": "services/social_proof.py",
    "src/telegram/services/stream_renderer.py": "services/stream_renderer.py",
    "src/telegram/sales/__init__.py": "sales/__init__.py",
    "src/telegram/sales/database.py": "sales/database.py",
    "src/telegram/sales/keyboards.py": "sales/keyboards.py",
    "src/telegram/sales/states.py": "sales/states.py",
    "src/telegram/sales/texts.py": "sales/texts.py",
    "src/telegram/sales/segments.py": "sales/segments.py",
    "src/telegram/prompts/smm_news.md": "prompts/smm_news.md",
    "src/telegram/middleware/__init__.py": "middleware/__init__.py",
    "src/telegram/middleware/access.py": "middleware/access.py",
}

# Import replacements
IMPORT_REPLACEMENTS = [
    # Replace bridge_client with llm_router
    (
        r"from \.\.services\.bridge_client import get_bridge_client",
        "from ..services.llm_router import get_llm_router"
    ),
    (
        r"from \.services\.bridge_client import get_bridge_client",
        "from .services.llm_router import get_llm_router"
    ),
    # Replace client calls
    (
        r"client = get_bridge_client\(\)",
        "router = get_llm_router()"
    ),
    (
        r"client\.chat_completion_stream\(",
        "router.chat("
    ),
]

# Files that need Claude (TZ generation only)
CLAUDE_FILES = ["handlers/tz.py"]

# Files that should use Qwen (news, chat, etc.)
QWEN_FILES = ["services/github_news.py", "handlers/messages.py"]


def replace_imports(content: str, file_path: str) -> str:
    """Replace imports and function calls."""
    for pattern, replacement in IMPORT_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    # Special handling for TZ (uses Claude)
    if any(f in file_path for f in CLAUDE_FILES):
        content = content.replace(
            "router.chat(",
            "router.generate(messages, backend=LLMBackend.CLAUDE, "
        )
        # Add import for LLMBackend
        if "from ..services.llm_router" in content:
            content = content.replace(
                "from ..services.llm_router import get_llm_router",
                "from ..services.llm_router import get_llm_router, LLMBackend"
            )

    # Special handling for news (explicitly use Qwen)
    if "github_news.py" in file_path:
        content = content.replace(
            "await generate_news_post(pr)",
            "await router.generate_news_post(smm_prompt, user_message)"
        )

    return content


def sync_files(source_repo: Path):
    """Copy and transform files from source to target."""
    print(f"Syncing from: {source_repo}")
    print(f"Target dir: {TARGET_DIR}")

    # Create target directories
    for target_path in FILE_MAPPING.values():
        target_full = TARGET_DIR / target_path
        target_full.parent.mkdir(parents=True, exist_ok=True)

    # Copy and transform files
    for source_path, target_path in FILE_MAPPING.items():
        source_full = source_repo / source_path
        target_full = TARGET_DIR / target_path

        if not source_full.exists():
            print(f"  SKIP (not found): {source_path}")
            continue

        content = source_full.read_text(encoding="utf-8")

        # Apply transformations for Python files
        if target_path.endswith(".py"):
            content = replace_imports(content, target_path)

        target_full.write_text(content, encoding="utf-8")
        print(f"  SYNC: {source_path} -> {target_path}")

    # Create llm_router.py (new file, not copied)
    router_path = TARGET_DIR / "services" / "llm_router.py"
    if not router_path.exists():
        print(f"  CREATE: services/llm_router.py (template)")
        # Would write the LLMRouter class here

    print("\nSync complete!")
    print(f"\nNext steps:")
    print(f"1. Review {TARGET_DIR}")
    print(f"2. Create services/llm_router.py with proper implementation")
    print(f"3. Update imports as needed")
    print(f"4. Test the bot")


def main():
    parser = argparse.ArgumentParser(description="Sync Telegram bot")
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_REPO,
        help="Path to claude-telegram-bridge repo"
    )
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source repo not found: {args.source}")
        print("Clone it first: gh repo clone ShaerWare/claude-telegram-bridge /tmp/claude-telegram-bridge")
        return

    sync_files(args.source)


if __name__ == "__main__":
    main()
```

---

## Modifications Summary

### 1. TZ Generation (`handlers/tz.py`)

**Before (uses Claude via bridge):**
```python
client = get_bridge_client()
async for chunk in client.chat_completion_stream(messages, model="sonnet"):
    ...
```

**After (explicitly uses Claude):**
```python
router = get_llm_router()
response = await router.generate_tz(TZ_SYSTEM_PROMPT, user_message)
```

### 2. News Generation (`services/github_news.py`)

**Before (uses Claude):**
```python
client = get_bridge_client()
async for chunk in client.chat_completion_stream(messages, model="sonnet"):
    ...
```

**After (uses Qwen):**
```python
router = get_llm_router()
response = await router.generate_news_post(smm_prompt, user_message)
```

### 3. General Chat (`handlers/messages.py`)

**Before:**
```python
client = get_bridge_client()
stream = client.chat_completion_stream(messages, model=session.model)
```

**After:**
```python
router = get_llm_router()
async for chunk in router.chat(messages):
    ...
```

---

## Environment Variables

Add to `.env`:

```bash
# Telegram Bot (aiogram-based)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=123456,789012
TELEGRAM_DEFAULT_MODEL=qwen2.5-7b

# LLM Routing
ORCHESTRATOR_URL=http://localhost:8002
CLAUDE_PROVIDER_ID=claude-bridge  # ID in cloud_llm_providers table

# Sales & Analytics
SALES_DB_PATH=data/sales.db
SALES_ADMIN_IDS=123456
```

---

## CI/CD Integration

### GitHub Action: Auto-sync on release

```yaml
# .github/workflows/sync-bot.yml
name: Sync Telegram Bot

on:
  repository_dispatch:
    types: [bot-updated]
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Clone source repo
        run: |
          gh repo clone ShaerWare/claude-telegram-bridge /tmp/source
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Run sync script
        run: python scripts/sync_telegram_bot.py --source /tmp/source

      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: Sync Telegram bot from upstream"
          body: "Automated sync from claude-telegram-bridge"
          branch: bot-sync-${{ github.run_number }}
```

---

## Testing

```bash
# 1. Sync files
python scripts/sync_telegram_bot.py

# 2. Install dependencies
pip install aiogram aiosqlite httpx pydantic-settings

# 3. Run bot
cd telegram_bot
python -m bot

# 4. Test TZ generation (should use Claude)
# Send: /tz

# 5. Test news (should use Qwen)
# Send: /news

# 6. Check logs for backend usage
# Look for: "Using LLM backend: claude" vs "Using LLM backend: qwen"
```

---

## Migration from Legacy Bot

The legacy `telegram_bot_service.py` (python-telegram-bot based) will be deprecated.
New bot uses:
- **aiogram 3.x** — async, modern, better FSM support
- **Modular handlers** — easier to maintain
- **SQLite persistence** — sales funnel data, analytics

Migration path:
1. Run new bot alongside old (different tokens)
2. Test all flows
3. Switch production token to new bot
4. Archive old `telegram_bot_service.py`

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-05 | 1.0 | Initial architecture |
