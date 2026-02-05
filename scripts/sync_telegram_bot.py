#!/usr/bin/env python3
"""
Sync Telegram bot from claude-telegram-bridge to AI_Secretary_System.

This script:
1. Clones/updates the source repository
2. Copies files with transformations
3. Replaces Claude calls with Qwen (except for TZ generation)

Usage:
    python scripts/sync_telegram_bot.py
    python scripts/sync_telegram_bot.py --source /path/to/local/repo
    python scripts/sync_telegram_bot.py --pull  # Pull latest changes first
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TARGET_DIR = PROJECT_ROOT / "telegram_bot"
DEFAULT_SOURCE = Path("/tmp/claude-telegram-bridge")
REPO_URL = "https://github.com/ShaerWare/claude-telegram-bridge.git"

# Files to copy (source relative path -> target relative path)
FILE_MAPPING = {
    # Core
    "src/telegram/__init__.py": "__init__.py",
    "src/telegram/__main__.py": "__main__.py",
    "src/telegram/bot.py": "bot.py",
    "src/telegram/config.py": "config.py",
    # Handlers
    "src/telegram/handlers/__init__.py": "handlers/__init__.py",
    "src/telegram/handlers/messages.py": "handlers/messages.py",
    "src/telegram/handlers/commands.py": "handlers/commands.py",
    "src/telegram/handlers/callbacks.py": "handlers/callbacks.py",
    "src/telegram/handlers/tz.py": "handlers/tz.py",
    "src/telegram/handlers/news.py": "handlers/news.py",
    "src/telegram/handlers/files.py": "handlers/files.py",
    # Sales handlers
    "src/telegram/handlers/sales/__init__.py": "handlers/sales/__init__.py",
    "src/telegram/handlers/sales/welcome.py": "handlers/sales/welcome.py",
    "src/telegram/handlers/sales/quiz.py": "handlers/sales/quiz.py",
    "src/telegram/handlers/sales/diy.py": "handlers/sales/diy.py",
    "src/telegram/handlers/sales/basic.py": "handlers/sales/basic.py",
    "src/telegram/handlers/sales/custom.py": "handlers/sales/custom.py",
    "src/telegram/handlers/sales/common.py": "handlers/sales/common.py",
    "src/telegram/handlers/sales/payment.py": "handlers/sales/payment.py",
    # Services (except bridge_client which we replace)
    "src/telegram/services/__init__.py": "services/__init__.py",
    "src/telegram/services/session_store.py": "services/session_store.py",
    "src/telegram/services/github_news.py": "services/github_news.py",
    "src/telegram/services/social_proof.py": "services/social_proof.py",
    "src/telegram/services/stream_renderer.py": "services/stream_renderer.py",
    # Sales module
    "src/telegram/sales/__init__.py": "sales/__init__.py",
    "src/telegram/sales/database.py": "sales/database.py",
    "src/telegram/sales/keyboards.py": "sales/keyboards.py",
    "src/telegram/sales/states.py": "sales/states.py",
    "src/telegram/sales/texts.py": "sales/texts.py",
    "src/telegram/sales/segments.py": "sales/segments.py",
    # Middleware
    "src/telegram/middleware/__init__.py": "middleware/__init__.py",
    "src/telegram/middleware/access.py": "middleware/access.py",
    # Prompts
    "src/telegram/prompts/smm_news.md": "prompts/smm_news.md",
}

# Files where we keep Claude (TZ generation)
KEEP_CLAUDE_FILES = {"handlers/tz.py"}

# Files where we explicitly use Qwen
USE_QWEN_FILES = {"services/github_news.py", "handlers/messages.py"}


def clone_or_update_repo(source_path: Path, pull: bool = False) -> bool:
    """Clone repo or pull latest changes."""
    if source_path.exists():
        if pull:
            print(f"Pulling latest changes in {source_path}...")
            result = subprocess.run(
                ["git", "pull"],
                cwd=source_path,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(f"Warning: git pull failed: {result.stderr}")
            else:
                print("Updated to latest version")
        return True

    print(f"Cloning {REPO_URL} to {source_path}...")
    result = subprocess.run(
        ["git", "clone", REPO_URL, str(source_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error cloning repo: {result.stderr}")
        return False
    print("Clone complete")
    return True


def transform_imports(content: str) -> str:
    """Replace bridge_client imports with llm_router."""
    # Replace various import patterns
    content = content.replace(
        "from ..services.bridge_client import get_bridge_client",
        "from ..services.llm_router import get_llm_router",
    )
    content = content.replace(
        "from .services.bridge_client import get_bridge_client",
        "from .services.llm_router import get_llm_router",
    )

    # Replace client initialization
    content = content.replace(
        "client = get_bridge_client()",
        "router = get_llm_router()",
    )

    # Replace client.close() with router.close()
    content = content.replace(
        "await client.close()",
        "await router.close()",
    )

    return content


def transform_tz_file(content: str) -> str:
    """
    Transform TZ handler to use Claude via LLM Router.

    TZ generation is one of the few places where Claude is used
    because it requires sophisticated document structuring.
    """
    content = transform_imports(content)

    # Replace the entire _generate_tz function body
    # Find and replace the streaming call with router.generate_tz()

    # Pattern to match the old streaming implementation
    old_pattern = r"""full_text = ""
    async for chunk in client\.chat_completion_stream\(
        messages=messages,
        model="sonnet",
    \):
        if chunk\.get\("choices"\):
            delta = chunk\["choices"\]\[0\]\.get\("delta", \{\}\)
            if content := delta\.get\("content"\):
                full_text \+= content

    return full_text\.strip\(\)"""

    new_code = """# Use Claude via LLM Router (expensive but smart)
    return await router.generate_tz(TZ_SYSTEM_PROMPT, user_message)"""

    content = re.sub(old_pattern, new_code, content)

    return content


def transform_news_file(content: str) -> str:
    """
    Transform github_news.py to use Qwen via LLM Router.

    News generation doesn't need Claude's advanced reasoning.
    """
    content = transform_imports(content)

    # Replace the streaming call with router.generate_news_post()

    # Remove the unused messages variable and replace streaming with direct call
    old_pattern = r'''user_message = f""".*?"""

    messages = \[
        \{"role": "system", "content": smm_prompt\},
        \{"role": "user", "content": user_message\},
    \]

    try:
        # Use non-streaming for simplicity
        full_text = ""
        async for chunk in client\.chat_completion_stream\(
            messages=messages,
            model=".*?",
        \):
            if chunk\.get\("choices"\):
                delta = chunk\["choices"\]\[0\]\.get\("delta", \{\}\)
                if content := delta\.get\("content"\):
                    full_text \+= content

        return full_text\.strip\(\)'''

    new_code = """try:
        # Use Qwen via LLM Router (fast, free) for news generation
        return await router.generate_news_post(smm_prompt, json.dumps(pr, ensure_ascii=False))"""

    content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

    return content


def transform_messages_file(content: str) -> str:
    """
    Transform messages.py to use Qwen via LLM Router for general chat.
    """
    content = transform_imports(content)

    # Replace the streaming call with router.chat_stream()

    old_pattern = r"""stream = client\.chat_completion_stream\(
            messages=session\.messages,
            model=session\.model,
            conversation_id=session\.conversation_id,
        \)"""

    new_code = """# Use Qwen via LLM Router for general chat (fast, free)
        stream = router.chat_stream(
            messages=session.messages,
            session_id=session.conversation_id,
        )"""

    content = re.sub(old_pattern, new_code, content)

    # Update error message
    content = content.replace(
        'logger.exception("Bridge request failed for user %s", user_id)',
        'logger.exception("LLM Router request failed for user %s", user_id)',
    )
    content = content.replace(
        'await message.answer("An error occurred while processing your request.")',
        'await message.answer("Произошла ошибка при обработке запроса.")',
    )

    return content


def transform_files_handler(content: str) -> str:
    """
    Transform files.py — disable file upload (not supported via LLM Router).
    """
    # Return a simplified version that informs users files are not supported
    return '''"""File and photo handler.

Note: File upload to LLM is temporarily disabled.
The LLM Router currently supports text-only interactions.
File analysis will be added in a future update.
"""

import logging

from aiogram import F, Router
from aiogram.types import Message


router = Router()
logger = logging.getLogger(__name__)

# 20 MB limit (Telegram Bot API file download limit)
MAX_FILE_SIZE = 20 * 1024 * 1024

# Temporary message while file processing is not supported
FILE_NOT_SUPPORTED_MSG = (
    "Анализ файлов временно недоступен.\\n\\n"
    "Сейчас бот поддерживает только текстовые сообщения.\\n"
    "Функция анализа файлов будет добавлена в следующем обновлении."
)


@router.message(F.document)
async def on_document(message: Message) -> None:
    """Handle document uploads — currently not supported."""
    if not message.from_user or not message.document:
        return

    await message.answer(FILE_NOT_SUPPORTED_MSG)
    logger.info(
        "File upload attempted by user %s (not supported yet)",
        message.from_user.id,
    )


@router.message(F.photo)
async def on_photo(message: Message) -> None:
    """Handle photo uploads — currently not supported."""
    if not message.from_user or not message.photo:
        return

    await message.answer(FILE_NOT_SUPPORTED_MSG)
    logger.info(
        "Photo upload attempted by user %s (not supported yet)",
        message.from_user.id,
    )
'''


def transform_file(content: str, target_path: str) -> str:
    """Apply all transformations to a file."""
    # Skip non-Python files
    if not target_path.endswith(".py"):
        return content

    # Apply file-specific transformations
    if target_path in KEEP_CLAUDE_FILES:
        return transform_tz_file(content)
    elif "github_news.py" in target_path:
        return transform_news_file(content)
    elif "messages.py" in target_path:
        return transform_messages_file(content)
    elif "files.py" in target_path:
        return transform_files_handler(content)
    else:
        # Default: just replace imports
        return transform_imports(content)


def sync_files(source_path: Path, dry_run: bool = False):
    """Copy and transform files from source to target."""
    print(f"\nSyncing from: {source_path}")
    print(f"Target dir: {TARGET_DIR}")
    print(f"Dry run: {dry_run}\n")

    # Create target directories
    for target_rel in FILE_MAPPING.values():
        target_full = TARGET_DIR / target_rel
        if not dry_run:
            target_full.parent.mkdir(parents=True, exist_ok=True)

    # Track changes
    synced = []
    skipped = []
    errors = []

    for source_rel, target_rel in FILE_MAPPING.items():
        source_full = source_path / source_rel
        target_full = TARGET_DIR / target_rel

        if not source_full.exists():
            skipped.append((source_rel, "not found"))
            continue

        try:
            content = source_full.read_text(encoding="utf-8")
            content = transform_file(content, target_rel)

            if not dry_run:
                target_full.write_text(content, encoding="utf-8")

            synced.append(target_rel)
            print(f"  [SYNC] {source_rel} -> {target_rel}")

        except Exception as e:
            errors.append((source_rel, str(e)))
            print(f"  [ERROR] {source_rel}: {e}")

    # Print summary
    print(f"\n{'=' * 60}")
    print("SYNC SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Synced: {len(synced)} files")
    print(f"  Skipped: {len(skipped)} files")
    print(f"  Errors: {len(errors)} files")

    if skipped:
        print("\nSkipped files:")
        for path, reason in skipped:
            print(f"  - {path}: {reason}")

    if errors:
        print("\nErrors:")
        for path, error in errors:
            print(f"  - {path}: {error}")

    # Check for llm_router.py
    router_path = TARGET_DIR / "services" / "llm_router.py"
    if router_path.exists():
        print(f"\n[OK] LLM Router exists: {router_path}")
    else:
        print(f"\n[WARN] LLM Router not found: {router_path}")
        print("       Create it manually or copy from docs/BOT_SYNC_ARCHITECTURE.md")

    print(f"\n{'=' * 60}")
    print("NEXT STEPS")
    print(f"{'=' * 60}")
    print("1. Review synced files in telegram_bot/")
    print("2. Ensure llm_router.py is properly configured")
    print("3. Update .env with required variables")
    print("4. Test: python -m telegram_bot.bot")
    print("5. Verify TZ uses Claude, everything else uses Qwen")


def main():
    parser = argparse.ArgumentParser(description="Sync Telegram bot from claude-telegram-bridge")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"Path to source repo (default: {DEFAULT_SOURCE})",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Pull latest changes before syncing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    args = parser.parse_args()

    # Clone or update repo
    if not clone_or_update_repo(args.source, pull=args.pull):
        sys.exit(1)

    # Sync files
    sync_files(args.source, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
