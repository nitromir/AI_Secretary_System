# Backup (Резервное копирование)

Экспорт и импорт конфигурации системы для резервного копирования и миграции между окружениями.

## Скриншот

<!-- Вставьте скриншот страницы Backup -->
![Backup](images/backup.png)

## Концепция

Backup-система позволяет:
- **Экспортировать** конфигурацию и данные в JSON-файлы
- **Импортировать** конфигурацию из JSON обратно в систему
- **Мигрировать** настройки между окружениями (dev → prod)
- **Версионировать** конфигурацию через Git

Всё управление происходит из раздела **Settings → Export/Import**.

## Типы экспорта

### 1. FAQ (База знаний)

Экспортирует все FAQ-записи (вопрос-ответ пары):

```json
{
  "faq": [
    {
      "question": "Как настроить бота?",
      "answer": "Перейдите в раздел Telegram...",
      "category": "Общие",
      "enabled": true,
      "owner_id": 1
    }
  ],
  "exported_at": "2026-02-11T12:00:00Z",
  "version": "1.0"
}
```

**Формат:** `faq_backup_YYYYMMDD_HHMMSS.json`

**Размер:** ~10KB на 100 записей

### 2. TTS Presets (Пресеты голосов)

Экспортирует все пресеты TTS (XTTS v2, OpenVoice, Piper):

```json
{
  "tts_presets": [
    {
      "name": "Anna Default",
      "engine": "xtts",
      "voice_id": "anna",
      "speed": 1.0,
      "pitch": 1.0,
      "owner_id": 1
    }
  ],
  "exported_at": "2026-02-11T12:00:00Z",
  "version": "1.0"
}
```

**Формат:** `tts_presets_backup_YYYYMMDD_HHMMSS.json`

**Размер:** ~5KB на 50 пресетов

### 3. Full Config (Полная конфигурация)

Экспортирует **всю систему**:

```json
{
  "version": "1.0",
  "exported_at": "2026-02-11T12:00:00Z",
  "faq": [...],
  "tts_presets": [...],
  "cloud_llm_providers": [
    {
      "name": "Gemini Pro",
      "provider_type": "gemini",
      "api_key": "***MASKED***",
      "model_name": "gemini-2.0-flash-exp",
      "owner_id": 1
    }
  ],
  "bot_instances": [
    {
      "bot_id": "sales-bot",
      "bot_token": "***MASKED***",
      "bot_username": "SalesBot",
      "system_prompt": "Ты — менеджер по продажам...",
      "llm_backend": "cloud:1",
      "tts_engine": "xtts",
      "voice_id": "anna",
      "enabled": true,
      "auto_start": true,
      "owner_id": 1
    }
  ],
  "widget_instances": [
    {
      "instance_id": "support-widget",
      "display_name": "Support Chat",
      "system_prompt": "Ты — агент поддержки...",
      "llm_backend": "vllm",
      "persona": "anna",
      "appearance_config": {
        "title": "Поддержка 24/7",
        "greeting": "Здравствуйте! Чем могу помочь?",
        "primary_color": "#c2410c"
      },
      "enabled": true,
      "owner_id": 1
    }
  ]
}
```

**Формат:** `full_config_backup_YYYYMMDD_HHMMSS.json`

**Размер:** Зависит от количества ботов и виджетов (~100KB для средней системы)

### Маскировка sensitive данных

При экспорте автоматически **маскируются**:
- `api_key` → `"***MASKED***"`
- `bot_token` → `"***MASKED***"`
- `client_secret` → `"***MASKED***"`
- `notification_secret` → `"***MASKED***"`

При импорте:
- Если значение = `"***MASKED***"` → **не обновляется** (остаётся старое)
- Если значение != `"***MASKED***"` → **обновляется**

## Импорт

### Загрузка файла

1. Перейдите в **Settings → Import**
2. Нажмите **"Выбрать файл"**
3. Выберите JSON-бэкап (любого типа: FAQ, TTS Presets или Full Config)
4. Нажмите **"Импортировать"**

### Стратегия слияния

Импорт использует **merge стратегию** (не полная перезапись):

| Ситуация | Действие |
|----------|----------|
| **Запись существует** (по ID или уникальному полю) | Обновляется (merge) |
| **Запись новая** | Создаётся |
| **Запись есть в системе, но нет в импорте** | **Не удаляется** (остаётся) |

### Пример

**Текущая система:**
- FAQ: 100 записей
- Боты: 5 ботов

**Импорт файла:**
- FAQ: 50 записей (20 новых, 30 обновлений)
- Боты: 3 бота (1 новый, 2 обновления)

**Результат:**
- FAQ: **120 записей** (100 + 20 новых)
- Боты: **6 ботов** (5 + 1 новый)

### Валидация

Перед импортом система проверяет:
- ✅ JSON валиден
- ✅ Версия формата совместима
- ✅ Обязательные поля присутствуют
- ✅ Типы данных корректны

Если ошибка → импорт откатывается (rollback), система остаётся в исходном состоянии.

## Архитектура

### Сервис

`app/services/backup_service.py` — основная логика экспорта/импорта:

```python
class BackupService:
    async def export_faq() -> dict
    async def export_tts_presets() -> dict
    async def export_full_config() -> dict
    async def import_config(data: dict) -> ImportResult
```

### Роутер

`app/routers/backup.py` — HTTP API:

```python
@router.get("/admin/backup/export/faq")
@router.get("/admin/backup/export/presets")
@router.get("/admin/backup/export/full")
@router.post("/admin/backup/import")
```

### Формат даты

Все timestamps в ISO 8601: `2026-02-11T12:00:00Z`

## API эндпоинты

### Экспорт

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/admin/backup/export/faq` | Скачать FAQ (JSON) |
| GET | `/admin/backup/export/presets` | Скачать TTS пресеты (JSON) |
| GET | `/admin/backup/export/full` | Скачать полную конфигурацию (JSON) |

### Импорт

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/admin/backup/import` | Загрузить и импортировать JSON |

**Формат запроса (multipart/form-data):**

```http
POST /admin/backup/import
Content-Type: multipart/form-data

------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="backup.json"
Content-Type: application/json

{...}
------WebKitFormBoundary--
```

**Ответ:**

```json
{
  "success": true,
  "message": "Импорт завершён",
  "imported": {
    "faq": 20,
    "tts_presets": 5,
    "bot_instances": 2,
    "widget_instances": 1
  },
  "updated": {
    "faq": 30,
    "bot_instances": 2
  }
}
```

## RBAC

| Роль | Экспорт FAQ | Экспорт Full | Импорт |
|------|-------------|--------------|--------|
| **Admin** | ✅ Все FAQ | ✅ Вся система | ✅ Любые данные |
| **User/Web** | ✅ Свои FAQ | ❌ Запрещено | ✅ Свои FAQ |
| **Guest** | ❌ Запрещено | ❌ Запрещено | ❌ Запрещено |

## Использование

### Резервное копирование

**Еженедельный бэкап:**

```bash
# Скачать полную конфигурацию
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/admin/backup/export/full \
  -o backup_$(date +%Y%m%d).json

# Сохранить в Git
git add backups/
git commit -m "Backup $(date +%Y-%m-%d)"
git push
```

### Миграция dev → prod

```bash
# 1. Экспортировать с dev-сервера
curl -H "Authorization: Bearer $DEV_TOKEN" \
  https://dev.example.com/admin/backup/export/full \
  -o dev_config.json

# 2. Отредактировать sensitive данные (API keys, tokens)
vim dev_config.json

# 3. Импортировать на prod
curl -H "Authorization: Bearer $PROD_TOKEN" \
  -F "file=@dev_config.json" \
  https://prod.example.com/admin/backup/import
```

### Восстановление после сбоя

```bash
# Импортировать последний бэкап
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@backup_latest.json" \
  https://api.example.com/admin/backup/import
```

## Безопасность

| Механизм | Описание |
|----------|----------|
| **Sensitive маскировка** | API keys и токены экспортируются как `***MASKED***` |
| **RBAC проверка** | Admin-only для Full Config экспорта/импорта |
| **Rollback** | Импорт откатывается при ошибках |
| **Аудит лог** | Все импорты логируются с `user_id` и timestamp |

## Ограничения

- **Не экспортируются:**
  - Чат-сессии (`ChatSession`)
  - Логи звонков GSM (`GSMCallLog`, `GSMSMSLog`)
  - История платежей (`Payment`)
  - Wiki RAG индекс (переиндексируется автоматически)
  - Пользователи (`User`) — только через `scripts/manage_users.py`

- **Максимальный размер файла импорта:** 50MB

- **Формат версии:** Система проверяет совместимость версий; импорт старых форматов может требовать миграции

## Типичные проблемы

### Импорт не обновляет bot_token

**Причина:** Токен замаскирован (`"***MASKED***"`)

**Решение:** Отредактируйте JSON перед импортом и укажите реальный токен

### Ошибка "Invalid JSON format"

**Причина:** Файл повреждён или неправильный формат

**Решение:** Проверьте валидность JSON через `jq` или JSON-валидатор

### Импорт прерван, система в неконсистентном состоянии

**Причина:** Rollback не сработал (баг)

**Решение:** Восстановите из предыдущего бэкапа или пересоздайте БД через миграции

---

← [[Settings]] | [[Home]] →
