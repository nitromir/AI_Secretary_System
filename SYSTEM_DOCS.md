# AI Secretary System - Системная документация

## Обзор системы

AI Secretary "Лидия" - система синтеза речи с клонированием голоса и GPU-ускорением, интегрированная с LLM для работы виртуального секретаря.

## Текущий статус (2026-01-14)

| Компонент | Статус | Производительность |
|-----------|--------|-------------------|
| Voice Clone Service | ✅ Работает | RTF 0.95x на GPU |
| GPU RTX 3060 | ✅ Активен | 10 GB / 12 GB |
| GPU P104-100 | ❌ Не поддерживается | CC 6.1 < 7.0 |
| Кэш speaker latents | ✅ Включён | `./cache/` |
| Пресеты интонаций | ✅ 5 штук | warm, calm, energetic, natural, neutral |
| Препроцессинг текста | ✅ Включён | Е→Ё, паузы |
| PyTorch | ✅ 2.9.1 | CUDA 12.8 |
| coqui-tts | ✅ 0.27.3 | XTTS v2 |

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
│  └─────────────┘  └─────────────┘  └──────┬──────┘          │
└─────────────────────────────────────────────┼───────────────┘
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │  RTX 3060 GPU   │
                                    │   12 GB VRAM    │
                                    │  CUDA 12.8      │
                                    └─────────────────┘
```

## GPU конфигурация

### Доступные GPU

| GPU | VRAM | Compute Capability | Поддержка |
|-----|------|-------------------|-----------|
| RTX 3060 | 12 GB | 8.6 | ✅ Используется |
| P104-100 | 8 GB | 6.1 | ❌ CC < 7.0 |

### Автоопределение GPU

Система автоматически выбирает совместимый GPU:
```python
def get_optimal_gpu():
    # Выбирает GPU с CC >= 7.0 и максимальной памятью
    # Fallback на CPU если нет совместимых
```

### Оптимизации CUDA

- TF32 для матричных операций
- cuDNN benchmark mode
- Автоочистка кэша после синтеза

## Voice Clone Service

### Инициализация

```python
from voice_clone_service import VoiceCloneService

# Автоопределение GPU
service = VoiceCloneService()

# Принудительно CPU
service = VoiceCloneService(force_cpu=True)

# Ограничить количество образцов
service = VoiceCloneService(max_samples=20)
```

### Пресеты интонаций

| Пресет | temperature | rep_penalty | speed | Описание |
|--------|-------------|-------------|-------|----------|
| `natural` | 0.75 | 4.0 | 0.98 | Естественный (по умолчанию) |
| `warm` | 0.85 | 3.0 | 0.95 | Тёплый, дружелюбный |
| `calm` | 0.5 | 6.0 | 0.9 | Спокойный, профессиональный |
| `energetic` | 0.9 | 2.5 | 1.1 | Энергичный, быстрый |
| `neutral` | 0.7 | 5.0 | 1.0 | Нейтральный деловой |

### Параметры синтеза

```python
wav, sr = service.synthesize(
    text="Текст для синтеза",
    language="ru",
    preset="warm",              # или None для default
    # Тонкие настройки (переопределяют пресет):
    temperature=0.8,            # 0.1-1.0: экспрессивность
    repetition_penalty=4.0,     # 1.0-10.0: убирает "ммм"
    top_k=50,                   # 1-100: разнообразие
    top_p=0.85,                 # 0.1-1.0: стабильность
    speed=1.0,                  # 0.5-2.0: скорость
    gpt_cond_len=20,           # 6-30: длина кондиционирования
    gpt_cond_chunk_len=5,      # 3-6: размер чанков
    preprocess_text=True,       # Е→Ё, паузы
    split_sentences=True,       # Разбивать на предложения
)
```

### Препроцессинг текста

**Замена Е→Ё** (автоматически):
- `все` → `всё`
- `еще` → `ещё`
- `идет` → `идёт`
- `берет` → `берёт`
- и ~50 других слов

**Паузы**:
- Двойной пробел `"  "` → `"... "`
- После вводных слов автоматически добавляется запятая

**Вводные слова**:
- "Здравствуйте", "Да", "Нет", "Конечно"
- "К сожалению", "Пожалуйста", "Спасибо"

### Кэширование speaker latents

```
./cache/
└── speaker_latents_c45d0fc3a2dbb6ee.pkl  # Хэш от списка файлов
```

- Предвычисляются при первом запуске из всех 53 образцов
- Загружаются мгновенно при повторном запуске
- Инвалидируются при изменении образцов

## Производительность

### Бенчмарк (RTX 3060)

```
Тест: 3 фразы общей длительностью 21.3 сек

Результаты:
- Общее время синтеза: 20.32 сек
- Средний RTF: 0.95x (почти реальное время!)
- Пик GPU памяти: 10.12 GB
```

### Сравнение CPU vs GPU

| Метрика | CPU | GPU (RTX 3060) |
|---------|-----|----------------|
| RTF | 5-6x | 0.95x |
| 6 сек аудио | ~32 сек | ~9 сек |
| Ускорение | - | **~3-5x** |

## API Endpoints

### Orchestrator (порт 8002)

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/` | GET | Информация о сервисе |
| `/health` | GET | Проверка здоровья |
| `/tts` | POST | Синтез речи |
| `/stt` | POST | Распознавание речи |
| `/chat` | POST | LLM ответ |
| `/process_call` | POST | Полный цикл: STT → LLM → TTS |
| `/v1/audio/speech` | POST | OpenAI-совместимый TTS |

### Примеры запросов

**TTS:**
```bash
curl -X POST http://localhost:8002/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет!", "language": "ru"}' \
  -o output.wav
```

**Полный цикл:**
```bash
curl -X POST http://localhost:8002/process_call \
  -F "audio=@input.wav" \
  -o response.wav
```

## Конфигурация

### .env

```bash
# Обязательно
GEMINI_API_KEY=AIzaSy...

# Порты
ORCHESTRATOR_PORT=8002
TTS_SERVER_PORT=5002

# Голосовые образцы
VOICE_SAMPLES_DIR=./Лидия

# Опционально (телефония)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...

# OpenWebUI
OPENWEBUI_URL=http://localhost:3000
```

## Файловая структура

```
AI_Secretary_System/
├── voice_clone_service.py   # TTS с GPU-ускорением
├── orchestrator.py          # Координатор сервисов
├── stt_service.py           # Whisper STT
├── llm_service.py           # Gemini LLM
├── phone_service.py         # Twilio webhooks
├── .env                     # Конфигурация
├── requirements.txt         # Зависимости
├── CLAUDE.md               # Контекст для Claude Code
├── SYSTEM_DOCS.md          # Эта документация
├── Лидия/                  # 53 голосовых образца WAV
├── cache/                  # Кэш speaker latents
├── calls_log/              # Логи звонков
├── temp/                   # Временные файлы
└── venv/                   # Python окружение
```

## Решённые проблемы

1. **Импорт coqui_tts** → `from TTS.api import TTS`
2. **GPU P104-100** → Автоопределение совместимых GPU (CC >= 7.0)
3. **Лицензия XTTS** → `COQUI_TOS_AGREED=1`
4. **Медленный синтез** → GPU + кэширование latents
5. **Неестественное произношение** → Препроцессинг Е→Ё, паузы

## Следующие шаги (TODO)

- [ ] Интеграция с оркестратором (передать preset через API)
- [ ] WebSocket для streaming TTS
- [ ] Настройка Twilio webhooks
- [ ] A/B тестирование пресетов интонаций
- [ ] Мониторинг GPU памяти в production

---
*Обновлено: 2026-01-14*
