#!/bin/bash
# Запуск vLLM с DeepSeek-LLM-7B-Chat на GPU 1 (RTX 3060, 12GB)
# Отдельный скрипт для тестирования DeepSeek
#
# DeepSeek-LLM-7B-Chat — модель от DeepSeek AI
# Сильная в reasoning и коде
#
# Порт: 11434 (OpenAI-compatible API)

# ВАЖНО: CUDA_DEVICE_ORDER=PCI_BUS_ID чтобы GPU нумеровались по PCI bus
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1

MODEL="deepseek-ai/deepseek-llm-7b-chat"

echo "=========================================="
echo "  vLLM Server - DeepSeek-LLM-7B-Chat"
echo "  GPU: RTX 3060 (12GB)"
echo "  Port: 11434"
echo "=========================================="
echo ""
echo "  Model: $MODEL"
echo "  Memory: 50% GPU utilization"
echo ""

source ~/vllm_env/venv/bin/activate

# Проверка GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')" 2>/dev/null || echo "GPU check failed"

echo "Starting vLLM with DeepSeek..."

# Запуск vLLM
vllm serve "$MODEL" \
    --gpu-memory-utilization 0.50 \
    --max-model-len 4096 \
    --dtype float16 \
    --max-num-seqs 32 \
    --port 11434 \
    --enforce-eager \
    --trust-remote-code
