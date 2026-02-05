"""GitHub news service — fetches merged PRs and generates news posts."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from ..services.llm_router import get_llm_router


if TYPE_CHECKING:
    from aiogram import Bot

logger = logging.getLogger(__name__)

GITHUB_REPO = "ShaerWare/AI_Secretary_System"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}"

# Load SMM prompt
SMM_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "smm_news.md"


@lru_cache(maxsize=1)
def _get_smm_prompt() -> str:
    """Load SMM prompt from file."""
    if SMM_PROMPT_PATH.exists():
        return SMM_PROMPT_PATH.read_text(encoding="utf-8")
    return "Ты SMM-копирайтер. Напиши новость о PR на русском языке."


async def fetch_merged_prs(
    days: int = 7,
    limit: int = 20,
) -> list[dict]:
    """Fetch recently merged pull requests from GitHub.

    Args:
        days: Look back this many days
        limit: Maximum number of PRs to return

    Returns:
        List of PR data dicts
    """
    since = datetime.utcnow() - timedelta(days=days)

    url = f"{GITHUB_API_URL}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100,  # Fetch more to filter merged ones
    }

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Secretary-Bot",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            all_prs = response.json()

            # Filter merged PRs within the date range
            merged_prs = []
            for pr in all_prs:
                if not pr.get("merged_at"):
                    continue

                merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                if merged_at.replace(tzinfo=None) < since:
                    continue

                merged_prs.append(
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "body": pr.get("body") or "",
                        "merged_at": pr["merged_at"],
                        "author": pr["user"]["login"],
                        "labels": [label["name"] for label in pr.get("labels", [])],
                        "html_url": pr["html_url"],
                    }
                )

                if len(merged_prs) >= limit:
                    break

            return merged_prs

    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch PRs from GitHub: {e}")
        return []


async def generate_news_post(pr: dict) -> str:
    """Generate a news post for a PR using AI.

    Args:
        pr: PR data dict from fetch_merged_prs

    Returns:
        Generated news post text
    """
    router = get_llm_router()
    smm_prompt = _get_smm_prompt()

    try:
        # Use Qwen via LLM Router (fast, free) for news generation
        return await router.generate_news_post(smm_prompt, json.dumps(pr, ensure_ascii=False))

    except Exception as e:
        logger.error(f"Failed to generate news post: {e}")
        # Fallback to simple format
        return (
            f"🆕 **{pr['title']}**\n\n"
            f"Новое обновление в AI Secretary!\n\n"
            f"🔗 {pr['html_url']}\n\n"
            f"#AISecretary #обновление"
        )


async def get_latest_news(days: int = 7, limit: int = 3) -> list[dict]:
    """Get latest news with generated posts.

    Args:
        days: Look back this many days
        limit: Maximum number of news items

    Returns:
        List of dicts with 'pr' and 'post' keys
    """
    prs = await fetch_merged_prs(days=days, limit=limit)

    news = []
    for pr in prs:
        post = await generate_news_post(pr)
        news.append(
            {
                "pr": pr,
                "post": post,
            }
        )

    return news


async def format_news_digest(days: int = 7) -> str:
    """Format a news digest message.

    Args:
        days: Look back this many days

    Returns:
        Formatted digest message
    """
    prs = await fetch_merged_prs(days=days, limit=5)

    if not prs:
        return (
            "📰 **Новости AI Secretary**\n\n"
            f"За последние {days} дней новых обновлений не было.\n\n"
            "Следите за обновлениями в репозитории:\n"
            f"🔗 https://github.com/{GITHUB_REPO}"
        )

    digest = f"📰 **Новости AI Secretary** (за {days} дней)\n\n"

    for i, pr in enumerate(prs, 1):
        merged_date = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")).strftime(
            "%d.%m"
        )

        digest += f"{i}. **{pr['title']}** ({merged_date})\n"

    digest += f"\n🔗 https://github.com/{GITHUB_REPO}/pulls?q=is%3Apr+is%3Amerged"

    return digest


# ── Broadcast to subscribers ────────────────────────────────────


async def broadcast_news_to_subscribers(bot: "Bot", post_text: str) -> int:
    """Send news post to all subscribed users.

    Args:
        bot: Telegram bot instance
        post_text: Generated news post text

    Returns:
        Number of successfully sent messages
    """
    from ..sales.database import get_sales_db

    db = await get_sales_db()
    subscribers = await db.get_subscribed_users()

    if not subscribers:
        logger.info("No subscribers to broadcast to")
        return 0

    sent_count = 0
    for user_id in subscribers:
        try:
            await bot.send_message(
                chat_id=user_id,
                text=post_text,
            )
            sent_count += 1
            # Small delay to avoid hitting rate limits
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"Failed to send news to user {user_id}: {e}")

    logger.info(f"Broadcast sent to {sent_count}/{len(subscribers)} subscribers")
    return sent_count


async def check_and_broadcast_news(bot: "Bot", skip_initial: bool = True) -> None:
    """Check for new PRs and broadcast to subscribers if any.

    This function:
    1. Fetches recent merged PRs
    2. Filters out already broadcast ones
    3. Generates posts for new PRs
    4. Sends to all subscribers

    Args:
        bot: Telegram bot instance
        skip_initial: If True and no broadcasts exist yet, mark all current PRs
                      as seen without sending (to avoid spam on first run)
    """
    from ..sales.database import get_sales_db

    logger.info("Checking for new PRs to broadcast...")

    try:
        # Fetch recent PRs (last 7 days)
        prs = await fetch_merged_prs(days=7, limit=10)

        if not prs:
            logger.info("No recent PRs found")
            return

        db = await get_sales_db()

        # Filter to get only unbroadcast PRs
        pr_numbers = [pr["number"] for pr in prs]
        unbroadcast_numbers = await db.get_unbroadcast_pr_numbers(pr_numbers)

        if not unbroadcast_numbers:
            logger.info("All recent PRs already broadcast")
            return

        # Check if this is first run (no broadcasts yet)
        if skip_initial and len(unbroadcast_numbers) == len(pr_numbers):
            # First run — mark all as seen without sending
            logger.info(f"First run: marking {len(pr_numbers)} existing PRs as seen (no broadcast)")
            for pr_num in pr_numbers:
                await db.mark_pr_broadcast(pr_num, 0)
            return

        # Get PRs that need broadcasting
        new_prs = [pr for pr in prs if pr["number"] in unbroadcast_numbers]
        logger.info(f"Found {len(new_prs)} new PRs to broadcast")

        # Process each new PR
        for pr in new_prs:
            try:
                # Check if we have cached post, otherwise generate
                cached_post = await db.get_cached_news(pr["number"])

                if cached_post:
                    post_text = cached_post
                else:
                    logger.info(f"Generating post for PR #{pr['number']}")
                    post_text = await generate_news_post(pr)
                    await db.save_news_cache(pr["number"], pr["title"], post_text)

                # Broadcast to subscribers
                sent_count = await broadcast_news_to_subscribers(bot, post_text)

                # Mark as broadcast
                await db.mark_pr_broadcast(pr["number"], sent_count)
                logger.info(f"PR #{pr['number']} broadcast complete: {sent_count} recipients")

            except Exception as e:
                logger.error(f"Failed to broadcast PR #{pr['number']}: {e}")

    except Exception as e:
        logger.error(f"Error in check_and_broadcast_news: {e}")


async def news_broadcast_scheduler(bot: "Bot", interval_hours: int = 1) -> None:
    """Background task that checks for news every N hours.

    Args:
        bot: Telegram bot instance
        interval_hours: Check interval in hours (default: 1)
    """
    logger.info(f"News broadcast scheduler started (interval: {interval_hours}h)")

    while True:
        try:
            await check_and_broadcast_news(bot)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

        # Wait for next check
        await asyncio.sleep(interval_hours * 3600)
