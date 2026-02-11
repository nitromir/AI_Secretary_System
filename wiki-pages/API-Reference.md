# API Reference (Справочник API)

Полная документация по REST API AI Secretary System с примерами запросов и ответов.

## Аутентификация

### Получение токена

```bash
POST /admin/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin"
}
```

**Ответ:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer"
}
```

### Использование токена

Добавьте JWT токен в заголовок `Authorization` для всех защищённых эндпоинтов:

```bash
GET /admin/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Эндпоинты аутентификации

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/admin/auth/login` | Вход (получение JWT) |
| GET | `/admin/auth/me` | Текущий пользователь |
| GET | `/admin/auth/status` | Статус аутентификации |
| GET | `/admin/auth/profile` | Профиль пользователя |
| PUT | `/admin/auth/profile` | Обновление профиля |
| POST | `/admin/auth/change-password` | Смена пароля |

## OpenAI-совместимые эндпоинты

Для интеграции с OpenWebUI и другими клиентами, поддерживающими OpenAI API.

### Список моделей

```bash
GET /v1/models
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "data": [
    {
      "id": "anna-secretary-vllm",
      "object": "model",
      "created": 1234567890,
      "owned_by": "system"
    },
    {
      "id": "marina-secretary-gemini",
      "object": "model",
      "created": 1234567890,
      "owned_by": "system"
    }
  ]
}
```

Формат ID: `{persona}-secretary-{backend}` (например, `anna-secretary-vllm`, `marina-secretary-cloud_1`)

### Список голосов

```bash
GET /v1/voices
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "voices": [
    {"id": "anna_ru", "name": "Анна (Russian)"},
    {"id": "marina_ru", "name": "Марина (Russian)"}
  ]
}
```

### Синтез речи (TTS)

```bash
POST /v1/audio/speech
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "tts-1",
  "input": "Привет, это Анна",
  "voice": "anna_ru"
}
```

**Ответ:** WAV аудиофайл (audio/wav)

**Особенности:**
- Поддержка streaming cache optimization
- Автоматическое кеширование аудио

### Чат (streaming)

```bash
POST /v1/chat/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "anna-secretary-vllm",
  "messages": [
    {"role": "user", "content": "Привет"}
  ],
  "stream": true
}
```

**Ответ (SSE):**
```
data: {"choices":[{"delta":{"content":"Привет"}}]}

data: {"choices":[{"delta":{"content":"!"}}]}

data: [DONE]
```

**Особенности:**
- Background TTS synthesis (аудио генерируется параллельно)
- Non-streaming режим (stream: false) возвращает полный JSON

## Базовые эндпоинты

### TTS (синтез речи)

```bash
POST /tts
Content-Type: application/json

{
  "text": "Привет, это Анна",
  "voice_id": "anna_ru"
}
```

**Ответ:** WAV аудиофайл

### STT (распознавание речи)

```bash
POST /stt
Content-Type: multipart/form-data

file: <audio.wav>
```

**Ответ:**
```json
{
  "text": "Привет, это Анна"
}
```

### Чат

```bash
POST /chat
Content-Type: application/json

{
  "message": "Привет",
  "persona": "anna"
}
```

**Ответ:**
```json
{
  "response": "Здравствуйте! Чем могу помочь?"
}
```

### Обработка звонка

```bash
POST /process_call
Content-Type: multipart/form-data

audio: <call.wav>
```

**Ответ:**
```json
{
  "transcription": "Текст звонка",
  "response": "Ответ секретаря",
  "audio_url": "/path/to/response.wav"
}
```

### Сброс контекста

```bash
POST /reset_conversation
```

**Ответ:**
```json
{
  "status": "ok",
  "message": "Контекст сброшен"
}
```

## Health check

```bash
GET /health
```

**Ответ:**
```json
{
  "status": "healthy",
  "services": {
    "tts": "running",
    "stt": "running",
    "llm": "running"
  },
  "database": "connected",
  "llm_backend": "vllm"
}
```

## URL паттерны

### CRUD ресурсов

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `GET /admin/{resource}` | Список всех | `/admin/chat/sessions` |
| `POST /admin/{resource}` | Создать новый | `/admin/telegram/bots` |
| `GET /admin/{resource}/{id}` | Получить один | `/admin/telegram/bots/123` |
| `PUT /admin/{resource}/{id}` | Обновить | `/admin/telegram/bots/123` |
| `DELETE /admin/{resource}/{id}` | Удалить | `/admin/telegram/bots/123` |

### Действия над ресурсами

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `POST /admin/{resource}/{id}/action` | Выполнить действие | `/admin/telegram/bots/123/start` |

**Примеры действий:**
- `/admin/telegram/bots/{id}/start` — запустить бота
- `/admin/telegram/bots/{id}/stop` — остановить бота
- `/admin/telegram/bots/{id}/test` — тестовое сообщение

### SSE streaming

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `GET /admin/{resource}/stream` | Server-Sent Events | `/admin/chat/stream` |

**Формат SSE:**
```
data: {"message": "chunk"}\n\n
data: [DONE]\n\n
```

### Webhooks

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `POST /webhooks/{service}` | Внешние вебхуки | `/webhooks/amocrm` |

**Доступные вебхуки:**
- `/webhooks/amocrm` — amoCRM webhook
- `/webhooks/yoomoney` — YooMoney payments
- `/webhooks/github` — GitHub CI/CD

## RBAC (контроль доступа)

Система использует 3 уровня защиты эндпоинтов:

| Dependency | Роли | Применение |
|------------|------|------------|
| `get_current_user` | Любой авторизованный | Read endpoints |
| `require_not_guest` | user, web, admin | Write endpoints |
| `require_admin` | admin | Sensitive operations |

### Роли пользователей

| Роль | Права | Ограничения |
|------|-------|-------------|
| **admin** | Полный доступ | Видит все ресурсы всех пользователей |
| **user** | Read + Write своих ресурсов | Полный доступ к админ-панели |
| **web** | Как user, но упрощённый UI | Скрыты: Dashboard, Services, vLLM, Models |
| **guest** | Read-only (demo) | Только просмотр, без изменений |

### Изоляция данных

Для пользователей с ролью `user` и `web` применяется фильтрация по `owner_id`:

```python
owner_id = None if user.role == "admin" else user.id
# Пользователь видит только свои ресурсы
```

Ресурсы с `owner_id`: ChatSession, BotInstance, WidgetInstance, CloudLLMProvider, TTSPreset

## Формат ошибок

Все ошибки возвращаются в единообразном JSON формате:

```json
{
  "detail": "Описание ошибки"
}
```

### HTTP статус-коды

| Код | Описание |
|-----|----------|
| 200 | Успех |
| 201 | Создано |
| 400 | Некорректный запрос |
| 401 | Требуется аутентификация |
| 403 | Доступ запрещён |
| 404 | Не найдено |
| 422 | Ошибка валидации |
| 500 | Внутренняя ошибка сервера |

## Примеры интеграции

### cURL

```bash
# Получить токен
TOKEN=$(curl -s -X POST http://localhost:8002/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' | jq -r .access_token)

# Запрос к API
curl -X GET http://localhost:8002/v1/models \
  -H "Authorization: Bearer $TOKEN"
```

### Python

```python
import requests

# Аутентификация
response = requests.post(
    "http://localhost:8002/admin/auth/login",
    json={"username": "admin", "password": "admin"}
)
token = response.json()["access_token"]

# Запрос с токеном
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8002/v1/models", headers=headers)
print(response.json())
```

---

← [[Personas]] | [[Troubleshooting]] →
