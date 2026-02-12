# Deployment Profiles (Профили развёртывания)

Управление режимом работы системы через переменную окружения `DEPLOYMENT_MODE`. Позволяет запускать один и тот же код на GPU-сервере (полный набор) и в облаке (только облачные LLM, без тяжёлых GPU-зависимостей).

## Зачем это нужно

Без профилей развёртывания система **всегда** загружает все сервисы — XTTS, Piper, OpenVoice, STT, GSM, GPU-мониторинг. На облачном сервере без GPU это:
- Лишние ошибки в логах при попытке инициализации
- Бессмысленные вкладки в админке (TTS, Models, Monitoring)
- Ненужные роутеры и эндпоинты в API

Deployment Profiles решают это на уровне **инфраструктуры**, ортогонально ролям пользователей (которые контролируют **права доступа**).

## Три режима

| Режим | Переменная | Что загружается |
|-------|-----------|-----------------|
| **Full** (по умолчанию) | `DEPLOYMENT_MODE=full` | Все сервисы: GPU, TTS, STT, GSM, облачные LLM |
| **Cloud** | `DEPLOYMENT_MODE=cloud` | Только облачные LLM, боты, виджеты, FAQ, Wiki RAG |
| **Local** | `DEPLOYMENT_MODE=local` | То же что Full (явный opt-in для ясности конфигурации) |

## Настройка

### Docker

Добавьте в `.env`:

```bash
DEPLOYMENT_MODE=cloud    # Для облачного сервера без GPU
```

Затем пересоберите:

```bash
docker compose build && docker compose up -d
```

### Локальная установка

Добавьте в `.env` или экспортируйте перед запуском:

```bash
export DEPLOYMENT_MODE=cloud
./start_cpu.sh
```

### Проверка

```bash
# Health endpoint покажет текущий режим
curl -s http://localhost:8002/health | python3 -m json.tool

# Или напрямую
curl -s http://localhost:8002/admin/deployment-mode
# → {"mode": "cloud"}
```

## Что отключается в Cloud-режиме

### Backend (orchestrator.py)

**Роутеры, которые НЕ регистрируются:**
- `services.router` — управление vLLM (start/stop/restart)
- `monitor.router` — GPU-метрики, логи
- `gsm.router` — GSM-телефония (SIM7600E-H)
- `stt.router` — распознавание речи (Vosk/Whisper)
- `tts.router` — пресеты голосов (XTTS/Piper)

**Сервисы, которые НЕ инициализируются:**
- Piper TTS
- OpenVoice v2
- XTTS v2 (Анна и Марина)
- STT (Vosk/Whisper)
- GSM Service

**Что работает в Cloud-режиме:**
- Облачные LLM (Gemini, OpenAI, Claude, DeepSeek, Kimi, OpenRouter)
- Чат (с облачными LLM)
- Telegram боты
- WhatsApp боты
- Веб-виджеты
- FAQ система
- Wiki RAG (база знаний)
- amoCRM интеграция
- Аудит и использование
- Воронка продаж и платежи
- Бэкапы и настройки

**Health endpoint** — в Cloud-режиме статус `healthy` не требует TTS (только LLM).

### Frontend (админ-панель)

**Скрытые вкладки в Cloud-режиме:**

| Вкладка | Причина |
|---------|---------|
| Dashboard | GPU-спарклайны бессмысленны без GPU |
| Services | vLLM start/stop недоступен |
| TTS | Пресеты XTTS/Piper не нужны |
| Monitoring | GPU/CPU-метрики нерелевантны |
| Models | HuggingFace модели не загружаются |
| Finetune | LoRA обучение требует GPU |
| GSM | Аппаратный модем отсутствует |

При попытке прямого перехода по URL на скрытую вкладку — редирект на `/chat`.

## Deployment Mode vs Роли пользователей

Это два **ортогональных** механизма:

| Аспект | Deployment Mode | Роли (admin/user/web/guest) |
|--------|----------------|----------------------------|
| **Контролирует** | Что **существует** | Кто **может делать** |
| **Уровень** | Инфраструктура | Авторизация |
| **Где настраивается** | `.env` файл | БД пользователей |
| **Влияет на** | Роутеры, сервисы, вкладки | Права доступа, видимость |

Примеры:
- `DEPLOYMENT_MODE=cloud` + роль `admin` — полный доступ к облачным функциям, но вкладок GPU нет
- `DEPLOYMENT_MODE=full` + роль `web` — GPU-сервисы загружены, но `web`-пользователь их не видит
- `DEPLOYMENT_MODE=cloud` + роль `guest` — только демо-чат и FAQ

## API

### GET /admin/deployment-mode

Возвращает текущий режим развёртывания.

**Ответ:**

```json
{
  "mode": "cloud"
}
```

Не требует авторизации. Используется фронтендом для определения видимости вкладок.

### GET /health

Включает `deployment_mode` в ответ:

```json
{
  "status": "healthy",
  "deployment_mode": "cloud",
  "services": {
    "voice_clone_xtts_anna": false,
    "voice_clone_xtts_marina": false,
    "piper_tts": false,
    "stt": false,
    "llm": true,
    "llm_backend": "cloud (gemini: gemini-2.5-flash)"
  }
}
```

### GET /admin/auth/me

Включает `deployment_mode` в ответ пользователя:

```json
{
  "id": 1,
  "username": "admin",
  "role": "admin",
  "deployment_mode": "cloud"
}
```

## Типичные сценарии развёртывания

### Облачный VPS (2 CPU, 4GB RAM)

```bash
DEPLOYMENT_MODE=cloud
LLM_BACKEND=cloud:1          # Gemini/OpenAI
```

Минимальные ресурсы, только облачные LLM и боты.

### Локальная рабочая станция с GPU

```bash
DEPLOYMENT_MODE=full          # или просто не задавать
LLM_BACKEND=vllm
```

Полный набор: vLLM + XTTS + STT + GSM.

### Демо-сервер

```bash
DEPLOYMENT_MODE=cloud
VITE_DEMO_MODE=true
```

Облачный LLM для демонстрации. Гости видят только чат и FAQ.
