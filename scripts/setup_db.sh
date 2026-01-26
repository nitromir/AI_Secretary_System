#!/bin/bash
# Database setup script for AI Secretary System
# Usage: ./scripts/setup_db.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== AI Secretary Database Setup ==="
echo ""

# Check if requirements are installed
echo "1. Checking dependencies..."
python3 -c "import sqlalchemy; import aiosqlite" 2>/dev/null || {
    echo "   Installing database dependencies..."
    pip install aiosqlite sqlalchemy[asyncio] alembic redis
}
echo "   Dependencies OK"

# Create data directory
echo ""
echo "2. Creating data directory..."
mkdir -p data
echo "   Created: data/"

# Run migration
echo ""
echo "3. Running migration from JSON to SQLite..."
python3 scripts/migrate_json_to_db.py

echo ""
echo "=== Database setup complete! ==="
echo ""
echo "Database location: data/secretary.db"
echo "Backups location: data/backup/"
echo ""
echo "You can now start the orchestrator with ./start_gpu.sh"
