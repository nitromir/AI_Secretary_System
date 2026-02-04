#!/bin/bash
# CLI-OpenAI Bridge Server Starter (Linux/macOS)

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Start the server
python3 -m src.server.main
