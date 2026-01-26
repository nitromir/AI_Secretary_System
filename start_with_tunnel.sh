#!/bin/bash
# Start AI Secretary with ngrok/cloudflare tunnel for external access

set -e

TUNNEL_TYPE="${1:-cloudflare}"  # cloudflare or ngrok

echo "🚀 Starting AI Secretary with $TUNNEL_TYPE tunnel..."

# Start AI Secretary in background
echo "📦 Starting AI Secretary..."
./start_gpu.sh &
AI_PID=$!

# Wait for orchestrator to be ready
echo "⏳ Waiting for orchestrator to start..."
for i in {1..30}; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        echo "✅ Orchestrator is ready"
        break
    fi
    sleep 2
done

# Check if ready
if ! curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "❌ Orchestrator failed to start"
    exit 1
fi

# Start tunnel
echo ""
echo "🌐 Starting $TUNNEL_TYPE tunnel..."
echo "=========================================="

if [ "$TUNNEL_TYPE" = "cloudflare" ]; then
    # Cloudflare tunnel (no registration needed)
    if ! command -v cloudflared &> /dev/null; then
        echo "❌ cloudflared not found. Install:"
        echo "   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb"
        echo "   sudo dpkg -i cloudflared.deb"
        exit 1
    fi

    echo "📌 Copy the URL below for your website:"
    echo ""
    cloudflared tunnel --url http://localhost:8002

elif [ "$TUNNEL_TYPE" = "ngrok" ]; then
    # ngrok tunnel
    if ! command -v ngrok &> /dev/null; then
        echo "❌ ngrok not found. Install from https://ngrok.com/download"
        exit 1
    fi

    echo "📌 Copy the 'Forwarding' URL for your website:"
    echo ""
    ngrok http 8002

else
    echo "❌ Unknown tunnel type: $TUNNEL_TYPE"
    echo "Usage: $0 [cloudflare|ngrok]"
    exit 1
fi
