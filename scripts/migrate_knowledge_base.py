#!/usr/bin/env python3
"""Migration script for knowledge base documents table.

Creates:
- knowledge_documents: Tracks uploaded documents in wiki-pages/

Usage: python scripts/migrate_knowledge_base.py
"""

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "secretary.db"

TABLE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS knowledge_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename VARCHAR(255) NOT NULL UNIQUE,
        title VARCHAR(500) NOT NULL,
        source_type VARCHAR(50) DEFAULT 'manual',
        file_size_bytes INTEGER DEFAULT 0,
        section_count INTEGER DEFAULT 0,
        owner_id INTEGER REFERENCES users(id),
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_knowledge_documents_filename
        ON knowledge_documents (filename)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_knowledge_documents_owner_id
        ON knowledge_documents (owner_id)
    """,
]


def migrate() -> None:
    if not DB_PATH.exists():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    print("Creating knowledge_documents table...")
    for ddl in TABLE_DDL:
        cursor.execute(ddl)
    conn.commit()
    conn.close()
    print(f"Done. Database: {DB_PATH}")


if __name__ == "__main__":
    migrate()
