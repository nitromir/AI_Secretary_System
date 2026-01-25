#!/bin/bash
# Запуск AI Secretary System на RTX 3060 (GPU 1)
# XTTS (Лидия) + vLLM работают вместе на одном GPU
#
# По умолчанию используется Qwen2.5-7B + Lydia LoRA
# Для запуска с Llama: ./start_gpu.sh --llama
#
# Распределение памяти RTX 3060 (12GB):
#   vLLM:  70% = ~8.4GB
#   XTTS:  остаток ~3.6GB (достаточно для модели)
#
# Порты:
#   8002:  Orchestrator (главный API)
#   11434: vLLM (OpenAI-compatible API)

cd "$(dirname "$0")"

# Определяем модель (по умолчанию Qwen)
MODEL="qwen"
# LoRA adapter path (symlink to /home/shaerware/qwen-finetune/qwen2.5-7b-lydia-lora)
LORA_PATH="$(dirname "$0")/finetune/adapters/qwen2.5-7b-lydia-lora/final"

if [[ "$1" == "--llama" ]]; then
    MODEL="llama"
fi

echo "=========================================="
echo "  AI Secretary System - GPU Mode"
echo "  RTX 3060 (12GB)"
echo "=========================================="
echo ""

if [[ "$MODEL" == "qwen" ]]; then
    echo "  LLM: Qwen2.5-7B-AWQ + Lydia LoRA (default)"
    echo "  LoRA: $LORA_PATH"
else
    echo "  LLM: Llama-3.1-8B GPTQ"
fi

echo ""
echo "  Сервисы:"
echo "    - Orchestrator + XTTS: http://localhost:8002"
echo "    - vLLM: http://localhost:11434"
echo ""
echo "  GPU memory:"
echo "    - vLLM:  70% (~8.4GB)"
echo "    - XTTS:  ~3.6GB"
echo ""
echo "=========================================="

# Создаём папку для логов
mkdir -p logs

# Функция для остановки всех процессов
cleanup() {
    echo ""
    echo "Остановка сервисов..."
    kill $VLLM_PID $ORCHESTRATOR_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Устанавливаем GPU 1 (RTX 3060) для всех процессов
# ВАЖНО: CUDA_DEVICE_ORDER=PCI_BUS_ID чтобы GPU нумеровались правильно
export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1

# 1. Запуск vLLM (фоновый процесс)
echo "[1/2] Запуск vLLM..."

if [[ "$MODEL" == "qwen" ]]; then
    echo "      Модель: Qwen2.5-7B-AWQ + Lydia LoRA"
    echo "      Память GPU: 70%"

    # Проверка LoRA (не критично - работает и без)
    if [ ! -f "$LORA_PATH/adapter_config.json" ]; then
        echo "      ⚠ LoRA adapter not found at $LORA_PATH"
        echo "      Running Qwen without LoRA..."
    fi
fi

if [[ "$MODEL" == "qwen" ]]; then
    # Qwen AWQ с LoRA
    LORA_ARGS=""
    if [ -f "$LORA_PATH/adapter_config.json" ]; then
        LORA_ARGS="--enable-lora --lora-modules lydia=$LORA_PATH"
    fi

    (
        export CUDA_DEVICE_ORDER=PCI_BUS_ID
        export CUDA_VISIBLE_DEVICES=1
        source ~/vllm_env/venv/bin/activate
        vllm serve "Qwen/Qwen2.5-7B-Instruct-AWQ" \
            --gpu-memory-utilization 0.70 \
            --max-model-len 4096 \
            --dtype float16 \
            --max-num-seqs 32 \
            --port 11434 \
            --enforce-eager \
            --trust-remote-code \
            $LORA_ARGS
    ) > logs/vllm.log 2>&1 &
else
    # Llama GPTQ
    echo "      Модель: Llama-3.1-8B-Instruct GPTQ INT4"
    echo "      Память GPU: 70%"

    (
        export CUDA_DEVICE_ORDER=PCI_BUS_ID
        export CUDA_VISIBLE_DEVICES=1
        source ~/vllm_env/venv/bin/activate
        vllm serve "fbaldassarri/meta-llama_Llama-3.1-8B-Instruct-auto_gptq-int4-gs128-sym" \
            --gpu-memory-utilization 0.70 \
            --max-model-len 4096 \
            --quantization gptq \
            --dtype float16 \
            --max-num-seqs 32 \
            --port 11434 \
            --enforce-eager \
            --trust-remote-code
    ) > logs/vllm.log 2>&1 &
fi

VLLM_PID=$!
echo "      PID: $VLLM_PID, лог: logs/vllm.log"

# Ждём пока vLLM запустится
echo "      Ожидание запуска vLLM (может занять 30-90 сек)..."
for i in {1..120}; do
    if curl -s http://localhost:11434/health > /dev/null 2>&1; then
        echo "      ✓ vLLM готов!"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "      ✗ vLLM упал! Проверьте logs/vllm.log"
        tail -30 logs/vllm.log
        exit 1
    fi
    sleep 2
done

# Проверяем финальный статус vLLM
if ! curl -s http://localhost:11434/health > /dev/null 2>&1; then
    echo "      ⚠ vLLM не ответил за 240 сек, продолжаем..."
fi

# 2. Запуск Orchestrator с XTTS (основной процесс)
echo ""
echo "[2/2] Запуск Orchestrator + XTTS..."
echo "      XTTS загрузится на оставшуюся память GPU"

export COQUI_TOS_AGREED=1
export LLM_BACKEND=vllm  # Указываем использовать vLLM вместо Gemini
export VLLM_API_URL=http://localhost:11434

# Передаём информацию о модели для правильного выбора имени
if [[ "$MODEL" == "qwen" ]]; then
    export VLLM_MODEL_NAME="lydia"  # LoRA adapter name
else
    export VLLM_MODEL_NAME=""  # Auto-detect
fi

./venv/bin/python orchestrator.py > logs/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
echo "      PID: $ORCHESTRATOR_PID, лог: logs/orchestrator.log"

# Ждём пока orchestrator запустится
echo "      Ожидание запуска Orchestrator..."
for i in {1..60}; do
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        echo "      ✓ Orchestrator готов!"
        break
    fi
    if ! kill -0 $ORCHESTRATOR_PID 2>/dev/null; then
        echo "      ✗ Orchestrator упал! Проверьте logs/orchestrator.log"
        tail -20 logs/orchestrator.log
        exit 1
    fi
    sleep 2
done

echo ""
echo "=========================================="
echo "  ✓ Все сервисы запущены!"
echo ""
if [[ "$MODEL" == "qwen" ]]; then
    echo "  Модель: Qwen2.5-7B-AWQ + Lydia LoRA"
else
    echo "  Модель: Llama-3.1-8B GPTQ"
fi
echo ""
echo "  Логи: tail -f logs/*.log"
echo "  Admin: http://localhost:8002/admin"
echo "  Ctrl+C для остановки"
echo "=========================================="

# Ждём завершения любого из процессов
wait $ORCHESTRATOR_PID $VLLM_PID
