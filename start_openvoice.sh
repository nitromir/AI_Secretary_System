#!/bin/bash
# Запуск OpenVoice TTS на GPU 0 (P104-100, 8GB, CC 6.1)

export CUDA_VISIBLE_DEVICES=0
export OPENVOICE_PORT=8003
export VOICE_SAMPLES_DIR=./Марина
export OPENVOICE_CHECKPOINTS=./checkpoints_v2

cd "$(dirname "$0")"

echo "=========================================="
echo "  OpenVoice TTS Service"
echo "  GPU: P104-100 (8GB, CC 6.1)"
echo "  Port: $OPENVOICE_PORT"
echo "=========================================="

# Активация виртуального окружения
source ./openvoice_env/bin/activate

# Проверка GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')" 2>/dev/null || echo "GPU check failed"

# Запуск сервиса
python openvoice_service.py --port $OPENVOICE_PORT
