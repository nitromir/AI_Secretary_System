#!/usr/bin/env python3
"""Migration script for amoCRM integration tables.

Creates:
- amocrm_config: Singleton config (OAuth tokens, sync settings)
- amocrm_sync_log: Sync event history

Usage: python scripts/migrate_amocrm.py
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS amocrm_config (
        id INTEGER PRIMARY KEY DEFAULT 1,
        subdomain VARCHAR(100),
        client_id VARCHAR(255),
        client_secret VARCHAR(255),
        redirect_uri VARCHAR(500),
        access_token TEXT,
        refresh_token TEXT,
        token_expires_at DATETIME,
        sync_contacts BOOLEAN DEFAULT 1,
        sync_leads BOOLEAN DEFAULT 1,
        sync_tasks BOOLEAN DEFAULT 0,
        auto_create_lead BOOLEAN DEFAULT 1,
        lead_pipeline_id INTEGER,
        lead_status_id INTEGER,
        webhook_url VARCHAR(500),
        webhook_secret VARCHAR(255),
        last_sync_at DATETIME,
        contacts_count INTEGER DEFAULT 0,
        leads_count INTEGER DEFAULT 0,
        account_info TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS amocrm_sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction VARCHAR(20) NOT NULL,
        entity_type VARCHAR(50) NOT NULL,
        entity_id INTEGER,
        action VARCHAR(20) NOT NULL,
        details TEXT,
        status VARCHAR(20) DEFAULT 'success',
        error_message TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_amocrm_sync_log_created
        ON amocrm_sync_log (created)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_amocrm_sync_log_entity
        ON amocrm_sync_log (entity_type, entity_id)
    """,
]


def migrate() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("Creating amoCRM tables...")
    for ddl in TABLE_DDL:
        cursor.execute(ddl)
    conn.commit()
    conn.close()
    print(f"Done. Database: {DB_PATH}")


if __name__ == "__main__":
    migrate()
