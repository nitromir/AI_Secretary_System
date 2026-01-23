#!/bin/bash
# Запуск vLLM с Qwen2.5-7B-AWQ + Lydia LoRA на GPU 1 (RTX 3060, 12GB)
# Основная модель для AI Secretary System
#
# Базовая модель: Qwen/Qwen2.5-7B-Instruct-AWQ (квантизация INT4)
# LoRA адаптер: /home/shaerware/qwen-finetune/qwen2.5-7b-lydia-lora/final
#
# AWQ квантизация уменьшает модель с ~14GB до ~4GB

# ВАЖНО: CUDA_DEVICE_ORDER=PCI_BUS_ID чтобы GPU нумеровались по PCI bus
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1

LORA_PATH="/home/shaerware/qwen-finetune/qwen2.5-7b-lydia-lora/final"
BASE_MODEL="Qwen/Qwen2.5-7B-Instruct-AWQ"

echo "=========================================="
echo "  vLLM Server - Qwen2.5-7B-AWQ + Lydia LoRA"
echo "  GPU: RTX 3060 (12GB)"
echo "  Port: 11434"
echo "=========================================="
echo ""
echo "  Base model: $BASE_MODEL"
echo "  LoRA: $LORA_PATH"
echo ""

source ~/vllm_env/venv/bin/activate

# Проверка GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')" 2>/dev/null || echo "GPU check failed"

# Проверка LoRA
if [ ! -f "$LORA_PATH/adapter_config.json" ]; then
    echo "WARNING: LoRA adapter not found at $LORA_PATH"
    echo "Running without LoRA..."
    LORA_ARGS=""
else
    echo "LoRA adapter found!"
    LORA_ARGS="--enable-lora --lora-modules lydia=$LORA_PATH"
fi

echo "Starting vLLM..."

# Запуск vLLM с AWQ квантизацией
# AWQ не требует --quantization флага (автоопределение)
vllm serve "$BASE_MODEL" \
    --gpu-memory-utilization 0.70 \
    --max-model-len 4096 \
    --dtype float16 \
    --max-num-seqs 32 \
    --port 11434 \
    --enforce-eager \
    --trust-remote-code \
    $LORA_ARGS
