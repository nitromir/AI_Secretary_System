#!/usr/bin/env python3
"""
Migration script: Convert standalone 'gemini' LLM backend to cloud provider system.

This script:
1. Creates a default Gemini cloud provider if none exists (using GEMINI_API_KEY env var)
2. Updates widget_instances and bot_instances with llm_backend='gemini' to use the new cloud provider
3. Prints the provider ID for reference

Usage:
    python scripts/migrate_gemini_to_cloud.py
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


# Allow running from project root or scripts/
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402


load_dotenv(PROJECT_ROOT / ".env")

DB_PATH = PROJECT_ROOT / "data" / "secretary.db"

DEFAULT_PROVIDER_ID = "gemini-default"
DEFAULT_PROVIDER_NAME = "Gemini (Auto-migrated)"


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}, skipping migration.")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check if cloud_llm_providers table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cloud_llm_providers'"
    )
    if not cursor.fetchone():
        print("Table cloud_llm_providers does not exist yet. Skipping migration.")
        print("(It will be created on app startup by SQLAlchemy)")
        conn.close()
        return

    # Check if a Gemini provider already exists
    cursor.execute("SELECT id FROM cloud_llm_providers WHERE provider_type = 'gemini' LIMIT 1")
    existing = cursor.fetchone()

    if existing:
        provider_id = existing["id"]
        print(f"Gemini cloud provider already exists: {provider_id}")
    else:
        # Create a default Gemini provider from env vars
        api_key = os.getenv("GEMINI_API_KEY", "")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        if not api_key:
            print("WARNING: GEMINI_API_KEY not set. Creating provider without API key.")
            print("You will need to configure it in the admin panel.")

        provider_id = DEFAULT_PROVIDER_ID

        cursor.execute(
            """INSERT INTO cloud_llm_providers
               (id, name, provider_type, api_key, base_url, model_name,
                enabled, is_default, owner_id, config, description, created, updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                provider_id,
                DEFAULT_PROVIDER_NAME,
                "gemini",
                api_key,
                None,
                model_name,
                1,  # enabled
                1,  # is_default
                None,  # owner_id (admin-owned)
                json.dumps({"temperature": 0.7}),
                "Auto-migrated from standalone gemini backend",
                now,
                now,
            ),
        )
        conn.commit()
        print(f"Created Gemini cloud provider: {provider_id} (model: {model_name})")

    # Update widget_instances with llm_backend='gemini'
    cloud_backend = f"cloud:{provider_id}"

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='widget_instances'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) as cnt FROM widget_instances WHERE llm_backend = 'gemini'")
        count = cursor.fetchone()["cnt"]
        if count > 0:
            cursor.execute(
                "UPDATE widget_instances SET llm_backend = ? WHERE llm_backend = 'gemini'",
                (cloud_backend,),
            )
            conn.commit()
            print(f"Updated {count} widget instance(s): gemini -> {cloud_backend}")
        else:
            print("No widget instances with llm_backend='gemini' found.")

    # Update bot_instances with llm_backend='gemini'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_instances'")
    if cursor.fetchone():
        cursor.execute("SELECT COUNT(*) as cnt FROM bot_instances WHERE llm_backend = 'gemini'")
        count = cursor.fetchone()["cnt"]
        if count > 0:
            cursor.execute(
                "UPDATE bot_instances SET llm_backend = ? WHERE llm_backend = 'gemini'",
                (cloud_backend,),
            )
            conn.commit()
            print(f"Updated {count} bot instance(s): gemini -> {cloud_backend}")
        else:
            print("No bot instances with llm_backend='gemini' found.")

    conn.close()
    print(f"\nMigration complete. Default Gemini provider ID: {provider_id}")
    print(f"Use LLM_BACKEND={cloud_backend} in your .env file.")


if __name__ == "__main__":
    migrate()
