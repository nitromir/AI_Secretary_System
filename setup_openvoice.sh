#!/bin/bash
# Установка OpenVoice v2 и зависимостей
# Для GPU P104-100 (CC 6.1)

set -e

cd "$(dirname "$0")"

echo "=========================================="
echo "  OpenVoice v2 Setup"
echo "=========================================="

# 1. Проверка/создание venv
if [ ! -d "openvoice_env" ]; then
    echo "[1/6] Создание виртуального окружения..."
    python3 -m venv openvoice_env
else
    echo "[1/6] Виртуальное окружение уже существует"
fi

source ./openvoice_env/bin/activate
pip install --upgrade pip wheel setuptools

# 2. Установка PyTorch с поддержкой CC 6.1
echo "[2/6] Установка PyTorch (CUDA 12.1)..."
if python -c "import torch" 2>/dev/null; then
    echo "      PyTorch уже установлен: $(python -c 'import torch; print(torch.__version__)')"
else
    # Проверяем есть ли предзагруженный wheel
    if [ -f "/tmp/pytorch_wheels/torch.whl" ]; then
        echo "      Установка из локального файла..."
        pip install /tmp/pytorch_wheels/torch.whl
    else
        echo "      Загрузка и установка из PyPI..."
        pip install torch==2.2.2+cu121 torchaudio==2.2.2+cu121 --index-url https://download.pytorch.org/whl/cu121
    fi
fi

# 3. Клонирование OpenVoice
echo "[3/6] Клонирование OpenVoice..."
if [ ! -d "OpenVoice" ]; then
    git clone https://github.com/myshell-ai/OpenVoice.git
else
    echo "      OpenVoice уже клонирован"
fi

# 4. Установка OpenVoice
echo "[4/6] Установка OpenVoice..."
pip install -e ./OpenVoice/

# 5. Установка MeloTTS
echo "[5/6] Установка MeloTTS..."
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download || echo "unidic уже установлен"

# 6. Скачивание checkpoints
echo "[6/6] Скачивание checkpoints..."
if [ ! -d "checkpoints_v2" ]; then
    echo "      Скачивание с HuggingFace..."
    # Используем huggingface-cli если доступен
    if command -v huggingface-cli &> /dev/null; then
        huggingface-cli download myshell-ai/OpenVoiceV2 --local-dir checkpoints_v2
    else
        pip install huggingface_hub
        python -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='myshell-ai/OpenVoiceV2', local_dir='checkpoints_v2')
"
    fi
else
    echo "      checkpoints_v2 уже существует"
fi

# 7. Установка FastAPI для сервиса
echo "[7/6] Установка FastAPI..."
pip install fastapi uvicorn python-multipart soundfile

# Проверка установки
echo ""
echo "=========================================="
echo "  Проверка установки"
echo "=========================================="

python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU: {torch.cuda.get_device_name(0)}')
    print(f'Compute Capability: {torch.cuda.get_device_capability(0)}')
"

python -c "from openvoice import se_extractor; print('OpenVoice: OK')" || echo "OpenVoice: FAILED"
python -c "from melo.api import TTS; print('MeloTTS: OK')" || echo "MeloTTS: FAILED"

echo ""
echo "=========================================="
echo "  Установка завершена!"
echo ""
echo "  Запуск: ./start_openvoice.sh"
echo "  Тест:   python openvoice_service.py --test"
echo "=========================================="
