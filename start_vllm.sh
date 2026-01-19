#!/bin/bash
# Запуск vLLM на GPU 1 (RTX 3060, 12GB)
# Llama-3.1-8B GPTQ INT4

export CUDA_VISIBLE_DEVICES=1

echo "=========================================="
echo "  vLLM Server - Llama-3.1-8B GPTQ"
echo "  GPU: RTX 3060 (12GB)"
echo "  Port: 11434"
echo "=========================================="

source ~/vllm_env/venv/bin/activate

# Проверка GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')" 2>/dev/null || echo "GPU check failed"

vllm serve "fbaldassarri/meta-llama_Llama-3.1-8B-Instruct-auto_gptq-int4-gs128-sym" \
  --gpu-memory-utilization 0.70 \
  --max-model-len 4096 \
  --quantization gptq \
  --dtype float16 \
  --max-num-seqs 32 \
  --port 11434 \
  --enforce-eager \
  --trust-remote-code
  
