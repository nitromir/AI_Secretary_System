#!/bin/bash
# AI Secretary - Quick Start Admin Panel
# Usage: ./start_admin.sh [--gpu|--cpu]

set -e
cd "$(dirname "$0")"

MODE="${1:---gpu}"
ADMIN_URL="http://localhost:8002/admin/"

echo "========================================"
echo "  AI Secretary System - Starting..."
echo "========================================"
echo ""

# Check if already running
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "[INFO] Orchestrator already running"
    echo "[INFO] Opening admin panel..."
    xdg-open "$ADMIN_URL" 2>/dev/null || open "$ADMIN_URL" 2>/dev/null || echo "Open: $ADMIN_URL"
    exit 0
fi

# Start based on mode
case "$MODE" in
    --gpu|-g)
        echo "[INFO] Starting in GPU mode (XTTS + vLLM)..."
        ./start_gpu.sh &
        ;;
    --cpu|-c)
        echo "[INFO] Starting in CPU mode (Piper + Gemini)..."
        ./start_cpu.sh &
        ;;
    *)
        echo "[INFO] Starting in GPU mode (default)..."
        ./start_gpu.sh &
        ;;
esac

# Wait for server
echo "[INFO] Waiting for server to start..."
for i in {1..30}; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        echo "[OK] Server is ready!"
        break
    fi
    sleep 1
    echo -n "."
done
echo ""

# Open browser
echo "[INFO] Opening admin panel..."
sleep 2
xdg-open "$ADMIN_URL" 2>/dev/null || open "$ADMIN_URL" 2>/dev/null || echo "Open: $ADMIN_URL"

echo ""
echo "========================================"
echo "  Admin Panel: $ADMIN_URL"
echo "  Login: admin / admin"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop watching logs"
echo ""

# Show logs
tail -f logs/orchestrator.log 2>/dev/null || echo "[INFO] Logs at: logs/orchestrator.log"
