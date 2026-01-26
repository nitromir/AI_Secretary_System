# BACKLOG.md

Roadmap и план работ для AI Secretary System. Этот файл используется для отслеживания прогресса и планирования разработки.

**Последнее обновление:** 2026-01-26 (v3 — Vosk STT)
**Контекст:** Офлайн-first система + телефония через SIM7600G-H Waveshare

---

## Текущий статус проекта

- [x] Базовая архитектура (orchestrator, TTS, LLM)
- [x] Vue 3 админ-панель (9 табов)
- [x] JWT аутентификация
- [x] FAQ система
- [x] Fine-tuning pipeline
- [x] XTTS v2 + Piper TTS
- [x] vLLM + Gemini fallback
- [x] **Chat TTS playback** — озвучивание ответов ассистента в чате
- [x] **Локальный STT (Vosk)** — VoskSTTService + UnifiedSTTService + API endpoints
- [ ] **Телефония SIM7600** — в планах
- [ ] **Enterprise-функции** — в планах

---

## Фаза 1: Core Enterprise (4-6 недель)

### 1.1 Audit Log + Export
**Статус:** `planned`
**Приоритет:** P0 (критичный)
**Сложность:** 4/10
**Оценка:** 1-1.5 недели
**Влияние:** ★★★★★

**Описание:**
Полное логирование действий пользователей с возможностью экспорта в JSON/CSV.

**Задачи:**
- [ ] Создать `audit_service.py` с persistent storage (SQLite)
- [ ] Логировать: login/logout, изменения FAQ, изменения конфигов, TTS генерации
- [ ] API эндпоинты: `GET /admin/audit/logs`, `GET /admin/audit/export`
- [ ] Фильтрация по дате, пользователю, типу события
- [ ] Таб "Audit" в админке с таблицей и экспортом
- [ ] Ротация логов (retention policy)

**Файлы:**
```
audit_service.py          # Новый сервис
audit.db                  # SQLite база
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

### 1.4 Backup & Restore
**Статус:** `planned`
**Приоритет:** P1
**Сложность:** 4/10
**Оценка:** 1 неделя
**Влияние:** ★★★★☆

**Описание:**
Полный бэкап системы одним кликом: конфигурация, FAQ, голоса, LoRA адаптеры.

**Задачи:**
- [ ] API: `POST /admin/backup/create`, `POST /admin/backup/restore`
- [ ] Создание ZIP архива со структурой
- [ ] Валидация при восстановлении
- [ ] Список бэкапов с метаданными
- [ ] UI в Settings или отдельный таб

**Структура бэкапа:**
```
backup_2026-01-26_143000.zip
├── manifest.json           # Версия, дата, checksums
├── config/
│   ├── typical_responses.json
│   ├── custom_presets.json
│   └── system_config.json
├── voices/
│   ├── Гуля/
│   └── Лидия/
├── adapters/               # LoRA (опционально, большие файлы)
│   └── lydia/
├── audit/
│   └── audit.db
└── chat_sessions.json
```

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
