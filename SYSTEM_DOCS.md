# AI Secretary System - Системная документация

## Обзор системы

AI Secretary "Лидия" - система синтеза речи с клонированием голоса, интегрированная с LLM для работы виртуального секретаря.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      OpenWebUI (порт 3000)                   │
│                    LLM API (Gemini backend)                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ /api/chat/completions
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (порт 8002)                   │
│                     orchestrator.py                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │ STT Service │  │ LLM Service │  │ TTS Service │          │
│  │  (Whisper)  │  │  (Gemini)   │  │  (XTTS v2)  │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 PHONE SERVICE (порт 8001)                    │
│                   phone_service.py                           │
│                  (Twilio webhooks)                           │
└─────────────────────────────────────────────────────────────┘
```

## Конфигурация (.env)

```bash
# Gemini API
GEMINI_API_KEY=AIzaSy...          # Ключ Google Gemini API
GEMINI_MODEL=gemini-2.5-pro-latest

# OpenWebUI интеграция
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_API_KEY=                 # Получить в Settings > Account > API Keys

# Порты (8000 занят Portainer)
ORCHESTRATOR_PORT=8002
TTS_SERVER_PORT=5002

# Голосовые образцы
VOICE_SAMPLES_DIR=./Лидия          # 54 WAV файла
```

## Текущее окружение

| Сервис | Порт | Статус |
|--------|------|--------|
| OpenWebUI | 3000 | ✅ Работает |
| ai-proxy-app | 8080 | ✅ Работает |
| Portainer | 8000, 9443 | ✅ Работает |
| PostgreSQL | 5435 | ✅ Работает |
| Redis | 6379 | ✅ Работает |
| **Orchestrator** | **8002** | ⏳ Требует запуска |
| Phone Service | 8001 | ⏳ Требует запуска |

## GPU ресурсы

| GPU | VRAM | Свободно |
|-----|------|----------|
| NVIDIA P104-100 | 8 GB | ~8 GB |
| NVIDIA RTX 3060 | 12 GB | ~11 GB |

## Зависимости

### Установленные (venv)
- fastapi, uvicorn
- piper-tts, edge-tts
- onnxruntime
- numpy, pydantic

### Требуют установки
- **torch** (780 MB CUDA версия) - загружается
- **TTS** (Coqui XTTS v2)
- **faster-whisper** / openai-whisper
- google-generativeai
- twilio

## API Endpoints

### Orchestrator (порт 8002)

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Информация о сервисе |
| `/health` | GET | Проверка здоровья |
| `/tts` | POST | Синтез речи (JSON: text, language) |
| `/stt` | POST | Распознавание речи (multipart: audio) |
| `/chat` | POST | LLM ответ (JSON: text) |
| `/process_call` | POST | Полный цикл: STT → LLM → TTS |
| `/reset_conversation` | POST | Сброс истории диалога |

### OpenWebUI API (порт 3000)

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/chat/completions` | POST | Chat Completions (OpenAI-compatible) |

**Аутентификация:** `Authorization: Bearer YOUR_API_KEY`

## Голосовые образцы

**Папка:** `./Лидия/`
**Файлов:** 54 WAV
**Размер:** ~50 MB
**Формат:** WAV, 16-bit

Используются первые 3 файла для XTTS v2 voice cloning:
- 20251114_130111.wav
- 20251114_130223.wav
- 20251114_130804.wav

## Запуск

### Локально
```bash
source venv/bin/activate
python orchestrator.py    # порт 8002
python phone_service.py   # порт 8001
```

### Docker
```bash
docker-compose up -d
```

## Тестирование

```bash
# Health check
curl http://localhost:8002/health

# TTS тест
curl -X POST http://localhost:8002/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, это тест", "language": "ru"}' \
  --output test.wav

# Chat тест
curl -X POST http://localhost:8002/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Здравствуйте"}'
```

## Интеграция с OpenWebUI

### Вариант 1: TTS для озвучки ответов

OpenWebUI поддерживает Custom TTS Engine. Настройка:
1. Settings → Audio → Text-to-Speech
2. Выбрать "Custom TTS"
3. Base URL: `http://localhost:8002`
4. API Key: (не требуется)

Требуемые endpoints для OpenWebUI TTS:
- `GET /v1/models` - список моделей
- `POST /v1/audio/speech` - генерация аудио

### Вариант 2: OpenWebUI как LLM backend

Изменить `llm_service.py` для использования OpenWebUI API вместо прямого Gemini.

```python
# Вместо google.generativeai использовать:
import requests

response = requests.post(
    "http://localhost:3000/api/chat/completions",
    headers={"Authorization": f"Bearer {OPENWEBUI_API_KEY}"},
    json={
        "model": "gemini-pro",
        "messages": [{"role": "user", "content": user_message}]
    }
)
```

## Известные проблемы

1. **Порт 8000 занят** - Portainer использует порт 8000, orchestrator перенесён на 8002
2. **Медленная загрузка torch** - ~24 KB/s, hash mismatch при обрыве
3. **OpenWebUI требует аутентификации** - нужен API ключ

## Файловая структура

```
AI_Secretary_System/
├── orchestrator.py          # Главный координатор
├── phone_service.py         # Twilio webhooks
├── voice_clone_service.py   # XTTS v2 TTS
├── stt_service.py           # Whisper STT
├── llm_service.py           # Gemini LLM
├── .env                     # Конфигурация
├── requirements.txt         # Зависимости
├── Лидия/                   # 54 голосовых образца
├── models/                  # ONNX модели (fallback)
├── temp/                    # Временные файлы
├── calls_log/               # Логи звонков
└── venv/                    # Python окружение
```

---
*Обновлено: 2026-01-13*
