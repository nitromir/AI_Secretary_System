#!/bin/bash
# Запуск всех сервисов AI Secretary System
#
# GPU распределение:
#   GPU 0 (P104-100, 8GB):  OpenVoice TTS
#   GPU 1 (RTX 3060, 12GB): vLLM Llama-3.1-8B
#
# Порты:
#   8002: Orchestrator (главный API)
#   8003: OpenVoice TTS
#   11434: vLLM

cd "$(dirname "$0")"

echo "=========================================="
echo "  AI Secretary System - Full Stack"
echo "=========================================="
echo ""
echo "  Сервисы:"
echo "    - Orchestrator:  http://localhost:8002"
echo "    - OpenVoice TTS: http://localhost:8003"
echo "    - vLLM:          http://localhost:11434"
echo ""
echo "  GPU:"
echo "    - GPU 0: P104-100  -> OpenVoice"
echo "    - GPU 1: RTX 3060  -> vLLM"
echo ""
echo "=========================================="

# Создаём папку для логов
mkdir -p logs

# Функция для остановки всех процессов
cleanup() {
    echo ""
    echo "Остановка сервисов..."
    kill $VLLM_PID $OPENVOICE_PID $ORCHESTRATOR_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# 1. Запуск vLLM (фоновый процесс)
echo "[1/3] Запуск vLLM..."
CUDA_VISIBLE_DEVICES=1 bash ./start_vllm.sh > logs/vllm.log 2>&1 &
VLLM_PID=$!
echo "      PID: $VLLM_PID, лог: logs/vllm.log"

# Ждём пока vLLM запустится (обычно 30-60 сек)
echo "      Ожидание запуска vLLM..."
for i in {1..60}; do
    if curl -s http://localhost:11434/health > /dev/null 2>&1; then
        echo "      vLLM готов!"
        break
    fi
    sleep 2
done

# 2. Запуск OpenVoice TTS (фоновый процесс)
echo "[2/3] Запуск OpenVoice TTS..."
CUDA_VISIBLE_DEVICES=0 bash ./start_openvoice.sh > logs/openvoice.log 2>&1 &
OPENVOICE_PID=$!
echo "      PID: $OPENVOICE_PID, лог: logs/openvoice.log"

# Ждём пока OpenVoice запустится
echo "      Ожидание запуска OpenVoice..."
for i in {1..30}; do
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo "      OpenVoice готов!"
        break
    fi
    sleep 2
done

# 3. Запуск Orchestrator (основной процесс)
echo "[3/3] Запуск Orchestrator..."
export COQUI_TOS_AGREED=1
./venv/bin/python orchestrator.py &
ORCHESTRATOR_PID=$!
echo "      PID: $ORCHESTRATOR_PID"

echo ""
echo "=========================================="
echo "  Все сервисы запущены!"
echo ""
echo "  Логи: tail -f logs/*.log"
echo "  Ctrl+C для остановки"
echo "=========================================="

# Ждём завершения любого из процессов
wait $ORCHESTRATOR_PID
