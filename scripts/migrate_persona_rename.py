#!/usr/bin/env python3
"""Migration script for persona rename: Гуля→Анна, Лидия→Марина.

Updates existing DB records that reference old persona/voice IDs.

Usage: python scripts/migrate_persona_rename.py
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

# Mapping of old values to new values
RENAMES = {
    "gulya": "anna",
    "lidia": "marina",
    "lidia_openvoice": "marina_openvoice",
    "xtts_gulya": "xtts_anna",
    "xtts_lidia": "xtts_marina",
}

# Tables and columns to update
UPDATES = [
    ("bot_instances", "llm_persona"),
    ("bot_instances", "tts_voice"),
    ("widget_instances", "llm_persona"),
    ("widget_instances", "tts_voice"),
    ("system_config", "value"),
    ("llm_presets", "id"),
]


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Nothing to migrate (fresh install will use new names).")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    total_updated = 0

    for table, column in UPDATES:
        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        if not cursor.fetchone():
            print(f"  Table '{table}' does not exist, skipping.")
            continue

        # Check if column exists
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        if column not in columns:
            print(f"  Column '{table}.{column}' does not exist, skipping.")
            continue

        for old_val, new_val in RENAMES.items():
            cursor.execute(
                f"UPDATE {table} SET {column} = ? WHERE {column} = ?",
                (new_val, old_val),
            )
            if cursor.rowcount > 0:
                print(f"  {table}.{column}: '{old_val}' -> '{new_val}' ({cursor.rowcount} rows)")
                total_updated += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"\nDone. Updated {total_updated} rows total.")


if __name__ == "__main__":
    print("Persona rename migration: Гуля→Анна, Лидия→Марина")
    print(f"Database: {DB_PATH}")
    print()
    migrate()
