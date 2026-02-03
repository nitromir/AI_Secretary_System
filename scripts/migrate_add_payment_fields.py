#!/usr/bin/env python3
"""
Migration: Add payment fields to bot_instances table.

Adds columns:
  - payment_enabled (BOOLEAN DEFAULT 0)
  - yookassa_provider_token (VARCHAR(255))
  - stars_enabled (BOOLEAN DEFAULT 0)
  - payment_products (TEXT)
  - payment_success_message (TEXT)

Safe to run multiple times (checks if columns exist).
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

COLUMNS = [
    ("payment_enabled", "BOOLEAN DEFAULT 0"),
    ("yookassa_provider_token", "VARCHAR(255)"),
    ("stars_enabled", "BOOLEAN DEFAULT 0"),
    ("payment_products", "TEXT"),
    ("payment_success_message", "TEXT"),
]


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Get existing columns
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(bot_instances)")}

    added = 0
    for col_name, col_type in COLUMNS:
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE bot_instances ADD COLUMN {col_name} {col_type}")
            print(f"  Added column: {col_name} ({col_type})")
            added += 1
        else:
            print(f"  Column already exists: {col_name}")

    conn.commit()
    conn.close()

    if added:
        print(f"\nMigration complete: {added} column(s) added.")
    else:
        print("\nNo changes needed — all columns already exist.")


if __name__ == "__main__":
    print("Migrating bot_instances table for payment support...")
    migrate()
