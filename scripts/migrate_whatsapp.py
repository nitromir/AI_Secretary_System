#!/usr/bin/env python3
"""
Migration: Create whatsapp_instances table.

Creates the table for WhatsApp bot instances with:
  - WhatsApp Cloud API credentials (phone_number_id, waba_id, access_token, etc.)
  - AI configuration (llm_backend, system_prompt)
  - TTS configuration (tts_enabled, tts_engine, tts_voice)
  - Access control (allowed_phones, blocked_phones)
  - Rate limiting (rate_limit_count, rate_limit_hours)
  - Instance management (enabled, auto_start, owner_id)

Safe to run multiple times (checks if table exists).
"""

import sqlite3
import sys
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS whatsapp_instances (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT 1,
    auto_start BOOLEAN DEFAULT 0,
    owner_id INTEGER REFERENCES users(id),

    -- WhatsApp Cloud API credentials
    phone_number_id VARCHAR(50) DEFAULT '',
    waba_id VARCHAR(50),
    access_token VARCHAR(500),
    verify_token VARCHAR(100),
    app_secret VARCHAR(200),

    -- Webhook settings
    webhook_port INTEGER DEFAULT 8003,

    -- AI configuration
    llm_backend VARCHAR(50) DEFAULT 'vllm',
    system_prompt TEXT,
    llm_params TEXT,

    -- TTS configuration
    tts_enabled BOOLEAN DEFAULT 0,
    tts_engine VARCHAR(20) DEFAULT 'xtts',
    tts_voice VARCHAR(50) DEFAULT 'anna',
    tts_preset VARCHAR(50),

    -- Access control
    allowed_phones TEXT,
    blocked_phones TEXT,

    -- Rate limiting
    rate_limit_count INTEGER,
    rate_limit_hours INTEGER,

    -- Timestamps
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_whatsapp_instances_name ON whatsapp_instances(name)",
    "CREATE INDEX IF NOT EXISTS ix_whatsapp_instances_enabled ON whatsapp_instances(enabled)",
    "CREATE INDEX IF NOT EXISTS ix_whatsapp_instances_owner_id ON whatsapp_instances(owner_id)",
]


def migrate():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        print("Run the app first to create the database.")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='whatsapp_instances'"
    )
    exists = cursor.fetchone() is not None

    if exists:
        print("Table 'whatsapp_instances' already exists — no changes needed.")
        conn.close()
        return

    # Create table
    cursor.execute(CREATE_TABLE)
    print("Created table: whatsapp_instances")

    # Create indexes
    for idx_sql in CREATE_INDEXES:
        cursor.execute(idx_sql)
    print("Created indexes: name, enabled, owner_id")

    conn.commit()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    print("Migrating database: adding whatsapp_instances table...")
    migrate()
