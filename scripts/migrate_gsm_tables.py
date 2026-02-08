#!/usr/bin/env python3
"""Migration script for GSM telephony tables.

Creates:
- gsm_call_logs: Call history
- gsm_sms_logs: SMS message history

Usage: python scripts/migrate_gsm_tables.py
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS gsm_call_logs (
        id VARCHAR(50) PRIMARY KEY,
        direction VARCHAR(10) NOT NULL,
        state VARCHAR(20) NOT NULL,
        caller_number VARCHAR(20) NOT NULL,
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        answered_at DATETIME,
        ended_at DATETIME,
        duration_seconds INTEGER,
        transcript_preview TEXT,
        audio_file_path VARCHAR(255),
        sms_sent BOOLEAN DEFAULT 0
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_call_logs_direction
        ON gsm_call_logs (direction)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_call_logs_state
        ON gsm_call_logs (state)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_call_logs_caller
        ON gsm_call_logs (caller_number)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_call_logs_started
        ON gsm_call_logs (started_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS gsm_sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction VARCHAR(10) NOT NULL,
        number VARCHAR(20) NOT NULL,
        text TEXT NOT NULL,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(20) NOT NULL
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_sms_logs_direction
        ON gsm_sms_logs (direction)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_sms_logs_number
        ON gsm_sms_logs (number)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_gsm_sms_logs_sent_at
        ON gsm_sms_logs (sent_at)
    """,
]


def migrate() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("Creating GSM telephony tables...")
    for ddl in TABLE_DDL:
        cursor.execute(ddl)
    conn.commit()
    conn.close()
    print(f"Done. Database: {DB_PATH}")


if __name__ == "__main__":
    migrate()
