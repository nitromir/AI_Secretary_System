#!/usr/bin/env python3
"""
Migration: Add chat message branching fields.

Adds columns to chat_messages:
  - parent_id (TEXT, nullable, FK to chat_messages.id)
  - is_active (BOOLEAN, default 1)

Chains existing messages: for each session, msg[i].parent_id = msg[i-1].id.
First message in each session gets parent_id = NULL.

Safe to run multiple times (checks if columns exist).
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check existing columns
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(chat_messages)")}

    added = 0

    if "parent_id" not in existing:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN parent_id TEXT")
        print("Added column: parent_id (TEXT)")
        added += 1
    else:
        print("Column already exists: parent_id")

    if "is_active" not in existing:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("Added column: is_active (BOOLEAN DEFAULT 1)")
        added += 1
    else:
        print("Column already exists: is_active")

    # Set is_active = 1 for any NULL values (existing rows)
    cursor.execute("UPDATE chat_messages SET is_active = 1 WHERE is_active IS NULL")
    updated_active = cursor.rowcount
    if updated_active:
        print(f"Set is_active=1 on {updated_active} existing row(s)")

    # Chain existing messages: set parent_id for messages that don't have one yet
    # Get all sessions
    cursor.execute("SELECT DISTINCT session_id FROM chat_messages")
    session_ids = [row[0] for row in cursor.fetchall()]

    chained = 0
    for session_id in session_ids:
        # Get messages ordered by created timestamp
        cursor.execute(
            "SELECT id FROM chat_messages "
            "WHERE session_id = ? AND parent_id IS NULL "
            "ORDER BY created ASC",
            (session_id,),
        )
        msg_ids = [row[0] for row in cursor.fetchall()]

        if len(msg_ids) <= 1:
            # 0 or 1 message — nothing to chain
            continue

        # Chain: msg[1].parent = msg[0], msg[2].parent = msg[1], etc.
        for i in range(1, len(msg_ids)):
            cursor.execute(
                "UPDATE chat_messages SET parent_id = ? WHERE id = ?",
                (msg_ids[i - 1], msg_ids[i]),
            )
            chained += 1

    # Create index on parent_id if it doesn't exist
    try:
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_parent_id ON chat_messages(parent_id)"
        )
    except sqlite3.OperationalError:
        pass  # Index may already exist

    conn.commit()
    conn.close()

    print("\nMigration complete:")
    print(f"  Columns added: {added}")
    print(f"  Messages chained: {chained} across {len(session_ids)} session(s)")


if __name__ == "__main__":
    print("Migrating chat_messages for branching support...\n")
    migrate()
