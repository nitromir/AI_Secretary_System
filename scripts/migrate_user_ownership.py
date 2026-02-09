#!/usr/bin/env python3
"""Migration: Add owner_id column to tables for multi-user data isolation.

Tables modified:
  - chat_sessions
  - bot_instances
  - widget_instances
  - cloud_llm_providers
  - tts_presets

Existing rows keep owner_id = NULL (treated as admin-owned legacy data).

Usage:
  python scripts/migrate_user_ownership.py
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

TABLES = [
    "chat_sessions",
    "bot_instances",
    "widget_instances",
    "cloud_llm_providers",
    "tts_presets",
]


def has_column(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Start the application first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    for table in TABLES:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cursor.fetchone():
            print(f"  SKIP  {table} — table does not exist")
            continue

        if has_column(cursor, table, "owner_id"):
            print(f"  OK    {table}.owner_id — already exists")
            continue

        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER REFERENCES users(id)")
            cursor.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_owner_id ON {table}(owner_id)")
            print(f"  ADD   {table}.owner_id — column and index created")
        except Exception as e:
            print(f"  ERR   {table}.owner_id — {e}")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    migrate()
