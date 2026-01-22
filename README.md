# AI Secretary System (Лидия)

Интеллектуальная система виртуального секретаря с клонированием голоса, способная принимать телефонные звонки и общаться с клиентами.

## Архитектура

```
                         ┌─────────────────────────────────────┐
                         │     Orchestrator (port 8002)        │
                         │         orchestrator.py             │
                         └──────────────┬──────────────────────┘
                                        │
        ┌───────────────┬───────────────┼───────────────┬───────────────┬──────────────────┐──────────────────┐
        ↓               ↓               ↓               ↓               ↓                  ↓
   STT Service     LLM Service    Voice Clone    OpenVoice v2     Piper TTS          Admin Panel          RAG (fine Tunning)
  (disabled)       vLLM/Gemini   (XTTS v2)        openvoice_       piper_tts_       admin_web.html
               vLLM/Llama-3.1-8B   voice_clone_   service.py       service.py
                        │         service.py       (GPU CC 6.1+)     (CPU)
                        │        (GPU CC 7.0+)
                        ↓
                  FAQ System
              typical_responses.json
```

### Компоненты

1. **Voice Clone Service** (`voice_clone_service.py`)
   - Клонирование голоса на базе XTTS v2
   - Использует образцы из папки `Лидия/`
   - Синтез речи с клонированным голосом

2. **STT Service** (`stt_service.py`)
   - Распознавание речи через Whisper/Faster-Whisper
   - Поддержка русского языка
   - Voice Activity Detection (VAD)

3. **LLM Service** (`llm_service.py`)
   - Интеграция с Gemini API
   - Системный промпт секретаря
   - История диалога

4. **Orchestrator** (`orchestrator.py`)
   - FastAPI сервер
   - Координация STT → LLM → TTS
   - API endpoints для всех операций

5. **Phone Service** (`phone_service.py`)
   - Интеграция с Twilio
   - Обработка входящих звонков
   - TwiML генерация

## Требования

### Железо
- GPU: NVIDIA с 12GB+ VRAM (например, RTX 3060)
- RAM: 16GB+ (64GB рекомендуется)
- Диск: 10GB свободного места

### ПО
- Ubuntu 20.04+ / Debian 11+
- Python 3.11+
- CUDA 11.8+ (для GPU)
- Docker + Docker Compose (опционально)
- ffmpeg

## Установка

### Вариант 1: Локальная установка

```bash
# 1. Клонирование и переход в директорию
cd /path/to/voice-tts

# 2. Запуск установки
./setup.sh

# 3. Настройка .env
cp .env.example .env
nano .env  # Добавьте GEMINI_API_KEY

# 4. Запуск
./run.sh
```

### Вариант 2: Docker

```bash
# 1. Настройка .env
cp .env.example .env
nano .env  # Добавьте API ключи

# 2. Сборка и запуск
docker-compose up -d

# 3. Проверка логов
docker-compose logs -f
```

## Настройка

### 1. Gemini API

Получите API ключ на https://makersuite.google.com/app/apikey

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-pro-latest
```

### 2. Twilio (для телефонии)

1. Зарегистрируйтесь на https://www.twilio.com
2. Получите телефонный номер
3. Настройте Webhook для входящих звонков:
   - URL: `https://your-domain.com/incoming_call`
   - Method: POST

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

### 3. Образцы голоса

Поместите WAV файлы в папку `Лидия/`:
- Формат: WAV, 16kHz или 44.1kHz
- Длительность: 3-30 секунд каждый
- Количество: минимум 3, рекомендуется 10+
- Качество: чистая речь без шума

## Использование

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Синтез речи (TTS)
```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, это тест", "language": "ru"}' \
  -o output.wav
```

#### Распознавание речи (STT)
```bash
curl -X POST http://localhost:8000/stt \
  -F "audio=@input.wav"
```

#### Чат с LLM
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Здравствуйте, какой график работы?"}'
```

#### Полный цикл обработки
```bash
curl -X POST http://localhost:8000/process_call \
  -F "audio=@voice_message.wav" \
  -o response.wav
```

### Тестирование

```bash
# Запуск тестов
./test_system.sh

# Ручной тест TTS
python voice_clone_service.py

# Ручной тест STT
python stt_service.py

# Ручной тест LLM
python llm_service.py
```

## Интеграция с OpenWebUI

Оркестратор предоставляет OpenAI-совместимый API, который позволяет использовать голос Лидии и LLM прямо в OpenWebUI.

### Предварительные требования

1. OpenWebUI запущен в Docker
2. Оркестратор запущен: `COQUI_TOS_AGREED=1 ./venv/bin/python orchestrator.py`
3. Проверьте доступность: `curl http://localhost:8002/health`

### Шаг 1: Подключение модели (Chat)

1. Откройте **OpenWebUI** в браузере
2. Нажмите на **иконку профиля** (правый верхний угол) → **Admin Panel**
3. Перейдите в **Settings** → **Connections**
4. Найдите раздел **OpenAI API**
5. Заполните поля:
   - **API Base URL**: `http://172.17.0.1:8002/v1`
   - **API Key**: `sk-dummy` (любое значение, не проверяется)
6. Нажмите кнопку **Verify connection** (иконка галочки)
7. Должно появиться сообщение об успешном подключении
8. Нажмите **Save**

> **Примечание**: `172.17.0.1` — это IP Docker bridge. Если OpenWebUI запущен не в Docker, используйте `localhost`.

### Шаг 2: Настройка голоса (TTS)

1. Нажмите на **иконку профиля** → **Settings** (не Admin Panel!)
2. Перейдите в раздел **Audio**
3. В секции **Text-to-Speech (TTS)** настройте:
   - **TTS Engine**: выберите `OpenAI` (НЕ "Web API"!)
   - **API Base URL**: `http://172.17.0.1:8002/v1`
   - **API Key**: `sk-dummy`
   - **TTS Voice**: `lidia`
4. Включите **Auto-playback Response** для автоматического воспроизведения
5. Нажмите **Save**

> **Важно**: Если выбран "Web API" — будет использоваться встроенный браузерный синтезатор, а не голос Лидии!

### Шаг 3: Использование

1. Вернитесь на главную страницу чата
2. В выпадающем списке моделей выберите **lidia-gemini**
3. Напишите сообщение — ответ будет озвучен голосом Лидии

### Доступные модели

| Модель | Описание |
|--------|----------|
| `lidia-gemini` | Чат-модель (Gemini 2.5 Flash) |
| `lidia-Llama` | Чат-модель (Llama-3.1-8B-Instruct) |
| `lidia-voice` | TTS-модель (XTTS v2 с клонированным голосом) |

### Решение проблем 

**Модели не появляются в списке:**
- Убедитесь, что оркестратор запущен (`curl http://localhost:8002/health`)
- Проверьте URL: должен быть `http://172.17.0.1:8002/v1` (без trailing slash)
- Нажмите Verify connection и обновите страницу (F5)

**"Извините, возникла техническая проблема":**
- Проверьте лимиты Gemini API (бесплатный тариф: 20 запросов/минуту)
- Смотрите логи оркестратора для деталей ошибки

**Голос браузерный, не Лидия:**
- Проверьте Settings → Audio → TTS Engine = `OpenAI` (не "Web API")
- Убедитесь, что API Base URL указан: `http://172.17.0.1:8002/v1`
- TTS Voice должен быть `lidia`

**Network error при подключении:**
- Проверьте, что порт 8002 открыт: `curl http://172.17.0.1:8002/v1/models`
- Если OpenWebUI в Docker — используйте `172.17.0.1`, не `localhost`

## Системный промпт

Промпт секретаря настраивается в `llm_service.py`:

```python
def _default_system_prompt(self) -> str:
    return """Ты - профессиональный виртуальный секретарь по имени Лидия.

    [Ваши инструкции здесь]
    """
```

Вы можете изменить:
- Имя секретаря
- Стиль общения
- Специфические инструкции для вашего бизнеса
- Информацию о компании

## Производительность

### Типичные задержки

- **STT (Whisper base)**: ~0.5-2 секунды на 10 сек аудио
- **LLM (Gemini)**: ~1-3 секунды
- **TTS (XTTS v2)**: ~2-5 секунд на предложение
- **Общий цикл**: ~5-10 секунд

### Оптимизация

1. **GPU**: Используйте CUDA для ускорения
2. **Модели**:
   - STT: `base` для скорости, `medium` для качества
   - LLM: `gemini-flash` для скорости, `gemini-pro` для качества
3. **Batch processing**: Обрабатывайте несколько запросов параллельно

## Логи и отладка

```bash
# Логи вызовов
ls -lh calls_log/

# Структура:
# call_20240101_120000_input.wav - входящее аудио
# call_20240101_120000_output.wav - ответ секретаря
# call_20240101_120000_transcript.txt - текстовая расшифровка

# Логи сервисов
docker-compose logs -f orchestrator
docker-compose logs -f phone-service
```

## Безопасность

1. **API ключи**: Храните в `.env`, не коммитьте
2. **HTTPS**: Используйте SSL для production
3. **Аутентификация**: Добавьте API tokens для endpoints
4. **Firewall**: Ограничьте доступ к портам

## Troubleshooting

### CUDA out of memory
```bash
# Уменьшите размер моделей
# В stt_service.py: model_size = "small"
# В voice_clone_service.py: используйте CPU fallback
```

### Плохое качество голоса
- Добавьте больше образцов в папку `Лидия/`
- Используйте чистые записи без шума
- Проверьте качество исходных WAV файлов

### Медленная работа
- Используйте faster-whisper вместо обычного Whisper
- Переключитесь на gemini-flash
- Увеличьте количество GPU workers

## Roadmap

- [ ] Поддержка нескольких голосов
- [ ] WebRTC для браузерных звонков
- [ ] Asterisk/FreeSWITCH интеграция
- [ ] Real-time streaming TTS
- [ ] Multi-language support
- [ ] Календарная интеграция
- [ ] CRM интеграция

## Лицензия

MIT

## Поддержка

Для вопросов и багов создавайте Issues в репозитории.
