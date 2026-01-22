#!/bin/bash
# Запуск vLLM с Qwen2.5-7B + Lydia LoRA на GPU 1 (RTX 3060, 12GB)
# Основная модель для AI Secretary System
#
# Базовая модель: Qwen/Qwen2.5-7B-Instruct
# LoRA адаптер: /home/shaerware/qwen-finetune/qwen2.5-7b-lydia-lora/final

# ВАЖНО: CUDA_DEVICE_ORDER=PCI_BUS_ID чтобы GPU нумеровались по PCI bus
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1

LORA_PATH="/home/shaerware/qwen-finetune/qwen2.5-7b-lydia-lora/final"

echo "=========================================="
echo "  vLLM Server - Qwen2.5-7B + Lydia LoRA"
echo "  GPU: RTX 3060 (12GB)"
echo "  Port: 11434"
echo "=========================================="
echo ""
echo "  Base model: Qwen/Qwen2.5-7B-Instruct"
echo "  LoRA: $LORA_PATH"
echo ""

source ~/vllm_env/venv/bin/activate

# Проверка GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')" 2>/dev/null || echo "GPU check failed"

# Проверка LoRA
if [ ! -f "$LORA_PATH/adapter_config.json" ]; then
    echo "ERROR: LoRA adapter not found at $LORA_PATH"
    exit 1
fi

echo "LoRA adapter found, starting vLLM..."

# Запуск vLLM с LoRA
# --enable-lora включает поддержку LoRA
# --lora-modules задает имя и путь к адаптеру
vllm serve "Qwen/Qwen2.5-7B-Instruct" \
    --gpu-memory-utilization 0.70 \
    --max-model-len 4096 \
    --dtype bfloat16 \
    --max-num-seqs 32 \
    --port 11434 \
    --enforce-eager \
    --trust-remote-code \
    --enable-lora \
    --lora-modules lydia="$LORA_PATH"
