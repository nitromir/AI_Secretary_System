# Services (Сервисы)

Управление фоновыми сервисами системы: запуск, остановка, перезапуск, мониторинг статуса и просмотр логов.

> **Видимость:** Скрыта в режиме `cloud` и для роли `web` (нет локальных сервисов).

## Зарегистрированные сервисы

`ServiceManager` (`service_manager.py`) управляет следующими сервисами:

| Сервис | Описание | Порт | GPU | Управление |
|--------|----------|------|-----|------------|
| **vLLM** | Локальный LLM сервер | 11434 | Да | Subprocess / Docker |
| **Orchestrator** | Основной FastAPI сервер | 8002 | — | Internal (systemd) |
| **XTTS** | Клонирование голоса | — | Да (CC ≥ 7.0) | Internal |
| **OpenVoice** | Альтернативный TTS | — | Да (CC ≥ 6.1) | Internal |
| **Piper** | Предобученный TTS (CPU) | — | Нет | Internal |
| **STT** | Распознавание речи | — | Нет | Internal |

**Internal** сервисы запускаются вместе с orchestrator и не могут управляться отдельно.

### vLLM в Docker режиме

Если обнаружен Docker, vLLM управляется через Docker API:
- Создание/запуск контейнера `ai-secretary-vllm` с GPU
- Переключение моделей: удаление контейнера → создание нового
- Автоматическое подключение к сети `ai-secretary`

## Карточки статуса

Каждый сервис отображается как карточка:

| Поле | Описание |
|------|----------|
| **Состояние** | Running (зелёный) / Stopped (серый) / Error (красный) |
| **PID** | ID процесса (или container_id для Docker) |
| **Memory** | Использование RAM (MB) |
| **Uptime** | Время работы с последнего запуска |
| **Last Error** | Последняя ошибка (если была) |

## Управление

### Кнопки

| Кнопка | Действие | API |
|--------|----------|-----|
| **Start** | Запустить сервис | `POST /admin/services/{name}/start` |
| **Stop** | Остановить (SIGTERM → SIGKILL через 10 сек) | `POST /admin/services/{name}/stop` |
| **Restart** | Перезапустить (stop → wait 2s → start) | `POST /admin/services/{name}/restart` |
| **Start All** | Запустить все внешние сервисы | `POST /admin/services/start-all` |
| **Stop All** | Остановить все внешние сервисы | `POST /admin/services/stop-all` |

### Переключение модели vLLM

1. Укажите HuggingFace ID модели (напр. `Qwen/Qwen2.5-7B-Instruct-AWQ`)
2. Система удалит текущий контейнер и создаст новый
3. Загрузка модели занимает 2-3 минуты

## Логи

### Список лог-файлов

`GET /admin/logs` возвращает все доступные логи: из конфигураций сервисов + файлы в `logs/`.

### Просмотр логов

| Функция | Описание |
|---------|----------|
| **Чтение** | Последние N строк (`GET /admin/logs/{logfile}?lines=100&offset=0`) |
| **Поиск** | Фильтрация по подстроке (`&search=ERROR`) |
| **SSE стриминг** | Новые строки в реальном времени (`GET /admin/logs/stream/{logfile}`) |

### Доступные логи

| Лог | Путь |
|-----|------|
| **orchestrator** | `logs/orchestrator.log` |
| **vllm** | `logs/vllm.log` |
| **telegram_bot** | `logs/telegram_bot_{instance_id}.log` |
| **whatsapp_bot** | `logs/whatsapp_bot_{instance_id}.log` |

## Конфигурация vLLM

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `VLLM_API_URL` | URL API сервера | `http://localhost:11434` |
| `VLLM_CONTAINER_NAME` | Имя Docker контейнера | `ai-secretary-vllm` |
| `VLLM_GPU_ID` | ID GPU для контейнера | `1` |
| `GPU_MEMORY_UTILIZATION` | Лимит VRAM | `0.5` (50%) |

## API

| Endpoint | Описание |
|----------|----------|
| `GET /admin/services/status` | Статус всех сервисов |
| `POST /admin/services/{name}/start` | Запустить |
| `POST /admin/services/{name}/stop` | Остановить |
| `POST /admin/services/{name}/restart` | Перезапустить |
| `POST /admin/services/start-all` | Запустить все |
| `POST /admin/services/stop-all` | Остановить все |
| `GET /admin/logs` | Список лог-файлов |
| `GET /admin/logs/{logfile}` | Чтение лога |
| `GET /admin/logs/stream/{logfile}` | SSE стриминг лога |

---

← [[Chat]] | [[LLM]] →
