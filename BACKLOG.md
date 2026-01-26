# BACKLOG.md

Roadmap и план работ для AI Secretary System. Этот файл используется для отслеживания прогресса и планирования разработки.

**Последнее обновление:** 2026-01-26 (v4 — Database Integration)
**Контекст:** Офлайн-first система + телефония через SIM7600G-H Waveshare

---

## Текущий статус проекта

- [x] Базовая архитектура (orchestrator, TTS, LLM)
- [x] Vue 3 админ-панель (12 табов)
- [x] JWT аутентификация
- [x] FAQ система
- [x] Fine-tuning pipeline
- [x] XTTS v2 + Piper TTS
- [x] vLLM + Gemini fallback + hot-switching
- [x] **Chat TTS playback** — озвучивание ответов ассистента в чате
- [x] **Локальный STT (Vosk)** — VoskSTTService + UnifiedSTTService + API endpoints
- [x] **Website Widget** — встраиваемый чат-виджет для сайтов
- [x] **Telegram Bot** — интеграция с Telegram (python-telegram-bot)
- [x] **Database Integration** — SQLite + Redis (транзакции, кэширование, миграция)
- [ ] **Телефония SIM7600** — в планах
- [ ] **Enterprise-функции** — в планах

---

## Фаза 1: Core Enterprise (4-6 недель)

### 1.1 Audit Log + Export
**Статус:** `in_progress` (база готова, нужен UI)
**Приоритет:** P0 (критичный)
**Сложность:** 2/10 (база уже есть)
**Оценка:** 0.5-1 неделя
**Влияние:** ★★★★★

**Описание:**
Полное логирование действий пользователей с возможностью экспорта в JSON/CSV.

**Задачи:**
- [x] Создать persistent storage (SQLite) — `db/repositories/audit.py`
- [x] Модель `AuditLog` в `db/models.py`
- [x] `AuditRepository` с методами: `log()`, `get_logs()`, `get_recent()`
- [x] `AsyncAuditLogger` wrapper в `db/integration.py`
- [ ] Логировать: login/logout, изменения FAQ, изменения конфигов, TTS генерации
- [ ] API эндпоинты: `GET /admin/audit/logs`, `GET /admin/audit/export`
- [ ] Фильтрация по дате, пользователю, типу события
- [ ] Таб "Audit" в админке с таблицей и экспортом
- [ ] Ротация логов (retention policy)

**Файлы (существующие):**
```
db/models.py              # AuditLog модель
db/repositories/audit.py  # AuditRepository
db/integration.py         # AsyncAuditLogger
```

**Файлы (нужно создать):**
```
admin/src/views/AuditView.vue
admin/src/api/audit.ts
```

---

### 1.2 Telephony Gateway (SIM7600)
**Статус:** `planned`
**Приоритет:** P0 (ключевой дифференциатор)
**Сложность:** 6/10
**Оценка:** 2-2.5 недели
**Влияние:** ★★★★★

**Описание:**
Интеграция с GSM модулем SIM7600G-H для приёма/совершения звонков.

**Задачи:**
- [ ] Создать `telephony_service.py` с AT-командами
- [ ] Обработка входящих звонков (RING detection)
- [ ] Исходящие звонки (ATD команда)
- [ ] SMS отправка/приём
- [ ] Audio streaming через USB audio interface
- [ ] Call state machine (idle → ringing → active → hangup)
- [ ] Интеграция с orchestrator
- [ ] Таб "Telephony" в админке

**AT-команды:**
```
AT+CPIN?        # Проверка SIM
AT+CSQ          # Уровень сигнала
AT+COPS?        # Оператор
ATA             # Ответить на звонок
ATH             # Положить трубку
ATD+7xxx;       # Исходящий звонок
AT+CMGS         # Отправить SMS
```

**Файлы:**
```
telephony_service.py      # Новый сервис
admin/src/views/TelephonyView.vue
admin/src/api/telephony.ts
```

**Зависимости:**
- pyserial
- aioserial (async)

---

### 1.3 Local STT (Vosk)
**Статус:** `done`
**Приоритет:** P0 (требуется для телефонии)
**Сложность:** 5/10
**Оценка:** 1-1.5 недели
**Влияние:** ★★★★☆

**Описание:**
Замена faster-whisper на Vosk для realtime офлайн распознавания речи.

**Задачи:**
- [x] Создать `stt_service.py` с Vosk (VoskSTTService, UnifiedSTTService)
- [ ] Скачать модель `vosk-model-ru-0.42` (~1.5GB) или `vosk-model-small-ru-0.22` (~45MB)
- [x] Streaming распознавание для телефонии (`stream_recognize()`)
- [x] Batch распознавание для записей (`transcribe()`)
- [ ] WebSocket endpoint для realtime STT
- [x] API endpoints: `/admin/stt/status`, `/admin/stt/transcribe`, `/admin/stt/test`

**Модели:**
| Модель | Размер | Качество | Использование |
|--------|--------|----------|---------------|
| vosk-model-ru-0.42 | 1.5GB | Высокое | Основная |
| vosk-model-small-ru-0.22 | 45MB | Среднее | Fallback |
| vosk-model-en-us-0.22 | 1.8GB | Высокое | English |

**Файлы:**
```
stt_service.py            # Новый сервис
models/vosk/              # Директория для моделей
```

**Зависимости:**
- vosk
- sounddevice (для микрофона)

---

### 1.4 Database Integration (SQLite + Redis)
**Статус:** `done`
**Приоритет:** P0 (критичный для надёжности)
**Сложность:** 6/10
**Влияние:** ★★★★★

**Описание:**
Миграция всех JSON файлов в SQLite для надёжного хранения с транзакциями.

**Задачи:**
- [x] Создать `db/` пакет с SQLAlchemy async
- [x] Модели: ChatSession, ChatMessage, FAQEntry, TTSPreset, SystemConfig, TelegramSession, AuditLog
- [x] Репозитории с CRUD операциями
- [x] Redis кэширование (опционально, graceful fallback)
- [x] Миграция существующих JSON данных
- [x] Обновить orchestrator.py
- [x] Backward-compatible sync с JSON
- [x] Health endpoint с БД статусом

**Архитектура:**
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ Orchestrator│───▶│ Repositories │───▶│   SQLite    │
│   API       │    │   (async)    │    │ + Redis     │
└─────────────┘    └──────────────┘    └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │ JSON Sync   │
                   │ (compat)    │
                   └─────────────┘
```

**Файлы:**
```
db/
├── __init__.py
├── database.py           # SQLite engine
├── models.py             # 7 ORM models
├── redis_client.py       # Caching
├── integration.py        # Backward-compat managers
└── repositories/
    ├── base.py
    ├── chat.py
    ├── faq.py
    ├── preset.py
    ├── config.py
    ├── telegram.py
    └── audit.py

scripts/
├── migrate_json_to_db.py
├── test_db.py
└── setup_db.sh

data/
└── secretary.db          # ~72KB
```

---

### 1.5 Backup & Restore
**Статус:** `planned` (упростился благодаря единой БД)
**Приоритет:** P1
**Сложность:** 3/10 (теперь проще — одна SQLite база)
**Оценка:** 0.5-1 неделя
**Влияние:** ★★★★☆

**Описание:**
Полный бэкап системы одним кликом: конфигурация, FAQ, голоса, LoRA адаптеры.

**Задачи:**
- [ ] API: `POST /admin/backup/create`, `POST /admin/backup/restore`
- [ ] Создание ZIP архива со структурой
- [ ] Валидация при восстановлении
- [ ] Список бэкапов с метаданными
- [ ] UI в Settings или отдельный таб

**Структура бэкапа (упрощённая):**
```
backup_2026-01-26_143000.zip
├── manifest.json           # Версия, дата, checksums
├── data/
│   └── secretary.db        # ВСЕ данные в одной базе
├── voices/
│   ├── Гуля/
│   └── Лидия/
└── adapters/               # LoRA (опционально)
    └── lydia/
```

**Примечание:** Благодаря миграции на SQLite все данные (чаты, FAQ, конфиги, аудит) теперь в одном файле `data/secretary.db`.

**Файлы:**
```
backup_service.py         # Новый сервис
backups/                  # Директория для бэкапов
```

---

## Фаза 2: Voice Pipeline (3-4 недели)

### 2.1 Audio Pipeline Integration
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 6/10
**Оценка:** 1.5-2 недели

**Описание:**
Связка STT → LLM → TTS для телефонных звонков в realtime.

**Задачи:**
- [ ] PCM audio capture от SIM7600
- [ ] Streaming STT с VAD (Voice Activity Detection)
- [ ] Низколатентная генерация ответа
- [ ] Streaming TTS playback
- [ ] Echo cancellation (опционально)
- [ ] Буферизация для плавного аудио

**Latency targets:**
| Этап | Цель | Допустимо |
|------|------|-----------|
| STT | <500ms | <1s |
| LLM | <2s | <3s |
| TTS | <500ms | <1s |
| **Total** | **<3s** | **<5s** |

---

### 2.2 Call Recording & Transcription
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 4/10
**Оценка:** 1 неделя

**Задачи:**
- [ ] Запись звонков в WAV/MP3
- [ ] Автоматическая транскрипция после завершения
- [ ] Хранение: audio + transcript + metadata
- [ ] Просмотр записей в админке
- [ ] Поиск по транскрипциям

**Файлы:**
```
recordings/
├── 2026-01-26/
│   ├── call_143000_+79001234567.wav
│   ├── call_143000_+79001234567.json  # Metadata + transcript
```

---

### 2.3 IVR Builder
**Статус:** `planned`
**Приоритет:** P2
**Сложность:** 7/10
**Оценка:** 2-3 недели

**Описание:**
Визуальный редактор голосового меню (Interactive Voice Response).

**Задачи:**
- [ ] JSON-схема для IVR flow
- [ ] Визуальный редактор (drag & drop)
- [ ] Условия: время, номер, ключевые слова
- [ ] Действия: озвучить, переключить, записать, повесить
- [ ] Preview и тестирование

**Пример IVR:**
```json
{
  "entry": "greeting",
  "nodes": {
    "greeting": {
      "type": "speak",
      "text": "Здравствуйте! Скажите, чем могу помочь?",
      "next": "listen"
    },
    "listen": {
      "type": "listen",
      "timeout": 5,
      "intents": {
        "schedule": "handle_schedule",
        "support": "handle_support",
        "default": "ai_response"
      }
    },
    "ai_response": {
      "type": "ai",
      "persona": "gulya",
      "next": "listen"
    }
  }
}
```

---

## Фаза 3: Enterprise Features (4-6 недель)

### 3.1 Extended RBAC
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 5/10
**Оценка:** 1.5-2 недели

**Описание:**
Расширенная система ролей и прав доступа.

**Роли:**
| Роль | Права |
|------|-------|
| admin | Полный доступ |
| operator | Чат, звонки, просмотр FAQ |
| editor | Редактирование FAQ, персон |
| viewer | Только просмотр дашборда |

**Задачи:**
- [ ] Расширить `auth_manager.py`
- [ ] Гранулярные права на ресурсы
- [ ] UI управления пользователями
- [ ] Приглашения по email (опционально)

---

### 3.2 Multi-Persona per Department
**Статус:** `planned`
**Приоритет:** P2
**Сложность:** 6/10
**Оценка:** 2-3 недели

**Описание:**
Разные персоны, голоса и FAQ для разных отделов.

**Структура:**
```
departments/
├── sales/
│   ├── persona.json      # Персона "Лидия"
│   ├── faq.json          # FAQ для продаж
│   └── voice_config.json # Голос продаж
├── support/
│   ├── persona.json      # Персона "Гуля"
│   ├── faq.json          # FAQ техподдержки
│   └── voice_config.json
└── reception/
    └── ...
```

**Маршрутизация:**
- По номеру телефона (разные SIM или DID)
- По времени (рабочее/нерабочее)
- По ключевым словам в начале разговора

---

### 3.3 Call & Conversation Analytics
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 6/10
**Оценка:** 2 недели

**Задачи:**
- [ ] Dashboard с метриками звонков
- [ ] Графики: звонки/день, средняя длительность
- [ ] Топ-10 вопросов
- [ ] % успешного распознавания STT
- [ ] Sentiment analysis (опционально)
- [ ] Экспорт отчётов

**Метрики:**
```python
class CallMetrics:
    total_calls: int
    answered_calls: int
    missed_calls: int
    avg_duration: float
    avg_wait_time: float
    stt_accuracy: float      # % успешных распознаваний
    faq_hit_rate: float      # % ответов из FAQ
    top_intents: List[str]
```

---

### 3.4 Multi-Instance Bots & Widgets
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 7/10
**Оценка:** 2-3 недели
**Влияние:** ★★★★★

**Описание:**
Возможность создавать неограниченное количество Telegram ботов и чат-виджетов. Каждый инстанс имеет собственные настройки: выбор LLM модели, системный промпт, персона, голос TTS.

**Задачи:**
- [ ] Новые таблицы: `bot_instances`, `widget_instances`
- [ ] CRUD API для ботов: `/admin/telegram/bots`, `/admin/telegram/bots/{id}`
- [ ] CRUD API для виджетов: `/admin/widget/instances`, `/admin/widget/instances/{id}`
- [ ] Настройки каждого инстанса:
  - Выбор LLM backend (vLLM/Gemini)
  - Выбор модели (Qwen, Llama, Lydia LoRA, etc.)
  - Системный промпт (кастомный или персона)
  - Выбор голоса TTS
  - Персона секретаря
  - FAQ set (опционально — разные FAQ для разных ботов)
- [ ] Параллельный запуск нескольких Telegram ботов
- [ ] Динамическая генерация `/widget.js?instance=xxx`
- [ ] UI для управления инстансами
- [ ] Статистика по каждому боту/виджету

**Структура данных:**
```python
class BotInstance(Base):
    __tablename__ = "bot_instances"

    id: str                    # UUID
    name: str                  # "Sales Bot", "Support Bot"
    platform: str              # "telegram", "widget"
    enabled: bool

    # Telegram-specific
    bot_token: str
    allowed_users: List[int]
    admin_users: List[int]

    # LLM Settings
    llm_backend: str           # "vllm", "gemini"
    llm_model: str             # "lydia", "Qwen/Qwen2.5-7B-Instruct-AWQ"
    system_prompt: str         # Custom system prompt
    persona: str               # "gulya", "lidia", "custom"
    temperature: float
    max_tokens: int

    # TTS Settings
    tts_voice: str             # "gulya", "lidia", "dmitri", "irina"
    tts_preset: str            # "neutral", "expressive", etc.

    # Messages
    welcome_message: str
    error_message: str

    created_at: datetime
    updated_at: datetime
```

**UI компоненты:**
```
admin/src/views/
├── TelegramBotsView.vue      # Список ботов + создание
├── TelegramBotEditView.vue   # Редактирование бота
├── WidgetInstancesView.vue   # Список виджетов + создание
└── WidgetInstanceEditView.vue # Редактирование виджета
```

**API endpoints:**
```bash
# Telegram Bots
GET    /admin/telegram/bots              # Список ботов
POST   /admin/telegram/bots              # Создать бота
GET    /admin/telegram/bots/{id}         # Получить бота
PUT    /admin/telegram/bots/{id}         # Обновить бота
DELETE /admin/telegram/bots/{id}         # Удалить бота
POST   /admin/telegram/bots/{id}/start   # Запустить бота
POST   /admin/telegram/bots/{id}/stop    # Остановить бота
GET    /admin/telegram/bots/{id}/stats   # Статистика бота

# Widget Instances
GET    /admin/widget/instances           # Список виджетов
POST   /admin/widget/instances           # Создать виджет
GET    /admin/widget/instances/{id}      # Получить виджет
PUT    /admin/widget/instances/{id}      # Обновить виджет
DELETE /admin/widget/instances/{id}      # Удалить виджет
GET    /widget.js?instance={id}          # Скрипт виджета
```

**Пример использования:**
```javascript
// Разные виджеты для разных отделов
<script src="https://api.example.com/widget.js?instance=sales"></script>
<script src="https://api.example.com/widget.js?instance=support"></script>
```

**Примечание:** Эта фича позволит:
- Один сервер — много ботов с разными токенами
- Разные промпты/персоны для sales, support, reception
- A/B тестирование разных моделей
- Мультитенантность (разные клиенты, разные боты)

---

## Фаза 4: Scale & Reliability (опционально)

### 4.1 High Availability
**Статус:** `backlog`
**Приоритет:** P3
**Сложность:** 8/10
**Оценка:** 3-5 недель

**Задачи:**
- [ ] Health checks для всех сервисов
- [ ] Автоматический failover LLM
- [ ] Поддержка 2+ GPU нод
- [ ] Load balancing
- [ ] Redis для shared state

---

### 4.2 SSO/LDAP Integration
**Статус:** `backlog`
**Приоритет:** P3
**Сложность:** 7/10
**Оценка:** 2.5-4 недели

**Задачи:**
- [ ] LDAP bind для аутентификации
- [ ] SAML 2.0 (опционально)
- [ ] OAuth2 (Google, Azure AD)
- [ ] Sync групп AD → роли

**Примечание:** Актуально только если есть AD/LDAP инфраструктура.

---

### 4.3 API Rate Limiting
**Статус:** `backlog`
**Приоритет:** P3
**Сложность:** 5/10
**Оценка:** 1-2 недели

**Примечание:** Для офлайн системы менее критично. Реализовать при необходимости.

---

## Технические заметки

### Hardware Setup (SIM7600G-H)

```
Raspberry Pi 4/5 или USB к основному серверу
         │
         ├── USB0: AT-команды (/dev/ttyUSB0)
         ├── USB1: Modem/PPP (/dev/ttyUSB1)
         ├── USB2: AT-команды (/dev/ttyUSB2)
         └── USB Audio: PCM аудио
```

**Подключение:**
```bash
# Проверка подключения
ls /dev/ttyUSB*
# Ожидается: /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyUSB2

# Тест AT-команд
screen /dev/ttyUSB0 115200
AT
# Ответ: OK
```

### Модели для офлайн

| Компонент | Модель | Размер | Где взять |
|-----------|--------|--------|-----------|
| LLM | Qwen2.5-7B-AWQ | 4GB | HuggingFace |
| LLM (light) | Qwen2.5-3B-GGUF | 2GB | HuggingFace |
| STT | vosk-model-ru-0.42 | 1.5GB | alphacephei.com |
| TTS | XTTS v2 | 1.8GB | Coqui |
| TTS (CPU) | Piper ru_RU | 60MB | GitHub |

### Зависимости для новых модулей

```bash
# Telephony
pip install pyserial aioserial

# STT
pip install vosk sounddevice

# Analytics
pip install pandas plotly

# Backup
pip install zipfile36  # или стандартный zipfile
```

---

## Changelog

### 2026-01-26 (update 5) — Multi-Instance Bots & Widgets
- Добавлена задача **3.4 Multi-Instance Bots & Widgets** в Фазу 3
  - Масштабирование: создание неограниченного количества ботов и виджетов
  - Индивидуальные настройки: LLM модель, системный промпт, персона, голос
  - Новые таблицы: `bot_instances`, `widget_instances`
  - Динамическая генерация виджетов: `/widget.js?instance=xxx`
  - Мультитенантность и A/B тестирование моделей

### 2026-01-26 (update 4) — Database Integration
- **Полная миграция на SQLite + Redis**
  - Создан пакет `db/` с SQLAlchemy async моделями
  - 7 таблиц: chat_sessions, chat_messages, faq_entries, tts_presets, system_config, telegram_sessions, audit_log
  - Redis кэширование с graceful fallback
  - Backward-compatible sync с JSON файлами
- **Новые файлы:**
  ```
  db/__init__.py
  db/database.py           # SQLite connection
  db/models.py             # ORM models
  db/redis_client.py       # Redis helpers
  db/integration.py        # Async managers
  db/repositories/         # Data access layer
  scripts/migrate_json_to_db.py
  scripts/test_db.py
  scripts/setup_db.sh
  ```
- Health endpoint теперь включает статус БД
- Зависимости: aiosqlite, sqlalchemy[asyncio], alembic, redis

### 2026-01-26 (update 3)
- Добавлен Vosk STT в stt_service.py
  - `VoskSTTService` — realtime офлайн распознавание
  - `UnifiedSTTService` — автовыбор Vosk/Whisper
  - `stream_recognize()` — streaming для телефонии
  - `recognize_microphone()` — распознавание с микрофона
- API endpoints: `/admin/stt/status`, `/admin/stt/models`, `/admin/stt/transcribe`, `/admin/stt/test`
- Обновлены зависимости: vosk, sounddevice

### 2026-01-26 (update 2)
- Добавлена кнопка TTS playback в ChatView.vue
  - Иконка Volume2 для сообщений ассистента (появляется при наведении)
  - Состояния: готов → загрузка (Loader2) → воспроизведение (Square/stop)
  - Использует `/admin/tts/test` через `ttsApi.testSynthesize()`
- Обновлена документация CLAUDE.md

### 2026-01-26
- Создан BACKLOG.md
- Определены 4 фазы разработки
- Приоритизированы enterprise-функции для офлайн + телефония

---

## Контакты

**Вопросы по roadmap:** открыть issue в репозитории
