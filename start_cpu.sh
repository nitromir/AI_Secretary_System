#!/bin/bash
# Запуск AI Secretary на CPU (без GPU)
# Используется Piper TTS вместо XTTS

export CUDA_VISIBLE_DEVICES=""
export COQUI_TOS_AGREED=1

cd "$(dirname "$0")"

echo "🚀 Запуск AI Secretary (CPU mode)"
echo "   TTS: Piper (irina/dmitri)"
echo "   GPU: отключен"
echo ""

./venv/bin/python orchestrator.py
