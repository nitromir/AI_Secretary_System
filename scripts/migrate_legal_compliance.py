#!/usr/bin/env python3
"""
Migration: Create user_consents table for GDPR compliance.

Creates table:
  - user_consents (user consent tracking for legal compliance)

Safe to run multiple times (checks if table exists).
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

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_consents'")
    if cursor.fetchone():
        print("Table user_consents already exists — no changes needed.")
        conn.close()
        return

    # Create user_consents table
    cursor.execute("""
        CREATE TABLE user_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id VARCHAR(100) NOT NULL,
            user_type VARCHAR(20) NOT NULL,
            consent_type VARCHAR(50) NOT NULL,
            consent_version VARCHAR(20) DEFAULT '1.0',
            granted BOOLEAN DEFAULT 0,
            granted_at DATETIME,
            revoked_at DATETIME,
            ip_address VARCHAR(45),
            user_agent TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  Created table: user_consents")

    # Create indexes for faster lookups
    cursor.execute("CREATE INDEX idx_user_consents_user_id ON user_consents(user_id)")
    print("  Created index: idx_user_consents_user_id")

    cursor.execute("CREATE INDEX idx_user_consents_consent_type ON user_consents(consent_type)")
    print("  Created index: idx_user_consents_consent_type")

    cursor.execute(
        "CREATE UNIQUE INDEX idx_user_consents_unique ON user_consents(user_id, consent_type)"
    )
    print("  Created unique index: idx_user_consents_unique")

    conn.commit()
    conn.close()

    print("\nMigration complete: user_consents table created.")


if __name__ == "__main__":
    print("Migrating database for legal compliance support...")
    migrate()
