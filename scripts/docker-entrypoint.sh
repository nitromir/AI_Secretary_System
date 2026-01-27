#!/bin/bash
# =============================================================================
# AI Secretary System - Docker Entrypoint
# =============================================================================
set -e

echo "========================================"
echo "  AI Secretary System"
echo "  Starting container..."
echo "========================================"

# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
echo "[1/4] Initializing database..."

if [ -f "/app/db/database.py" ]; then
    python -c "
from db.database import init_database
import asyncio
asyncio.run(init_database())
print('    Database initialized successfully')
" 2>&1 || echo "    Warning: Database initialization failed, will retry on first request"
else
    echo "    Warning: Database module not found"
fi

# -----------------------------------------------------------------------------
# Models Check
# -----------------------------------------------------------------------------
echo "[2/4] Checking models..."

# Check for Vosk model (STT)
if [ -d "/app/models/vosk-model-ru" ] || [ -d "/app/models/vosk" ]; then
    echo "    Vosk model: OK"
else
    echo "    Vosk model: Not found (STT will be disabled)"
    echo "    Download: https://alphacephei.com/vosk/models"
fi

# Check for Piper models (CPU TTS)
if [ -d "/app/models/piper" ]; then
    echo "    Piper models: OK"
else
    echo "    Piper models: Not found (will use XTTS if available)"
fi

# Create symlink for Vosk if needed
if [ -d "/app/models/vosk" ] && [ ! -d "/app/models/vosk-model-ru" ]; then
    ln -sf /app/models/vosk /app/models/vosk-model-ru
    echo "    Created symlink: vosk -> vosk-model-ru"
fi

# -----------------------------------------------------------------------------
# Directory Permissions
# -----------------------------------------------------------------------------
echo "[3/4] Checking directories..."

for dir in /app/data /app/logs /app/temp /app/cache; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo "    Created: $dir"
    fi
done

# -----------------------------------------------------------------------------
# Legacy File Warning
# -----------------------------------------------------------------------------
echo "[4/4] Checking for deprecated files..."

LEGACY_FILES=(
    "typical_responses.json"
    "custom_presets.json"
    "chat_sessions.json"
    "widget_config.json"
    "telegram_config.json"
)

for f in "${LEGACY_FILES[@]}"; do
    if [ -f "/app/$f" ]; then
        echo "    WARNING: Found legacy file $f"
        echo "    Data is now stored in SQLite (data/secretary.db)"
        echo "    Run: python scripts/migrate_json_to_db.py"
    fi
done

# -----------------------------------------------------------------------------
# Environment Info
# -----------------------------------------------------------------------------
echo ""
echo "========================================"
echo "  Configuration:"
echo "    LLM Backend: ${LLM_BACKEND:-vllm}"
echo "    Persona: ${SECRETARY_PERSONA:-gulya}"
echo "    Port: ${ORCHESTRATOR_PORT:-8002}"
echo "    Redis: ${REDIS_URL:-not configured}"
echo "========================================"
echo ""
echo "Starting application..."
echo ""

# Execute the main command
exec "$@"
