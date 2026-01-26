#!/bin/bash
# Start Telegram Bot for AI Secretary

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🤖 Starting Telegram Bot..."

# Check if config exists
if [ ! -f telegram_config.json ]; then
    echo "⚠️  telegram_config.json not found."
    echo "   Configure the bot via admin panel: http://localhost:8002/admin/#/telegram"
    exit 1
fi

# Check if enabled
ENABLED=$(python3 -c "import json; print(json.load(open('telegram_config.json')).get('enabled', False))" 2>/dev/null || echo "False")
if [ "$ENABLED" != "True" ]; then
    echo "⚠️  Telegram bot is disabled in config."
    echo "   Enable it via admin panel: http://localhost:8002/admin/#/telegram"
    exit 1
fi

# Check if token exists
HAS_TOKEN=$(python3 -c "import json; print(bool(json.load(open('telegram_config.json')).get('bot_token', '')))" 2>/dev/null || echo "False")
if [ "$HAS_TOKEN" != "True" ]; then
    echo "❌ Bot token not configured!"
    echo "   Get token from @BotFather and add it in admin panel"
    exit 1
fi

# Check dependencies
if ! python3 -c "import telegram" 2>/dev/null; then
    echo "📦 Installing python-telegram-bot..."
    pip install python-telegram-bot aiohttp
fi

# Start bot
echo "✅ Starting bot..."
python3 telegram_bot_service.py
