# Troubleshooting (Решение проблем)

Часто встречающиеся проблемы, их причины и способы устранения.

## vLLM / LLM

### vLLM не запускается

**Симптомы:**
- Ошибка "CUDA out of memory"
- Контейнер vllm падает при старте
- Таймаут при обращении к vLLM API

**Причины и решения:**

| Причина | Решение |
|---------|---------|
| Недостаточно GPU памяти | vLLM требует ~6GB. Проверьте `nvidia-smi`, закройте другие GPU процессы |
| Несовместимая версия CUDA | Обновите драйвера NVIDIA (требуется CUDA 11.8+) |
| Образ не загружен | Выполните `docker pull vllm/vllm-openai:latest` (~9GB) |
| Модель не загружена | Проверьте путь к модели в `docker-compose.yml` |

**Проверка:**
```bash
# Логи vLLM контейнера
docker logs ai-secretary-vllm

# Доступность API
curl http://localhost:11434/v1/models
```

### Cloud LLM не отвечает

**Симптомы:**
- Таймаут при запросе к облачному провайдеру
- Ошибка "API key invalid"
- 429 Too Many Requests

**Решения:**

| Проблема | Решение |
|----------|---------|
| Неверный API ключ | Проверьте ключ в Admin Panel → Services → LLM → Cloud Providers |
| Провайдер недоступен | Нажмите "Тест" для проверки доступности |
| Gemini заблокирован | Настройте VLESS прокси (см. [[VLESS-Proxy]]) |
| Превышен лимит | Переключитесь на другого провайдера или дождитесь сброса квоты |

**Проверка:**
```bash
# Тест Gemini через API
curl -X POST http://localhost:8002/admin/cloud-llm/test/1 \
  -H "Authorization: Bearer <token>"
```

### Медленные ответы от LLM

**Причины:**
- Модель слишком большая (>7B параметров)
- GPU загружен другими задачами
- Высокая температура / max_tokens

**Решения:**
1. Переключитесь на более быструю модель (Qwen2.5-3B вместо 7B)
2. Проверьте GPU utilization в Admin Panel → Monitoring
3. Уменьшите `max_tokens` в настройках LLM (2048 → 1024)
4. Снизьте `temperature` для более предсказуемых ответов

## TTS (синтез речи)

### XTTS ошибка CUDA

**Симптомы:**
- "RuntimeError: CUDA error: no kernel image is available"
- TTS не работает после переключения на XTTS

**Причина:** XTTS требует GPU с Compute Capability >= 7.0

| GPU | Compute Capability | Поддержка XTTS |
|-----|-------------------|----------------|
| RTX 3060+ | 8.6 | ✅ |
| RTX 2060+ | 7.5 | ✅ |
| GTX 1080 Ti | 6.1 | ❌ (используйте OpenVoice) |
| GTX 1060 | 6.1 | ❌ (используйте Piper) |

**Решение:** Переключитесь на OpenVoice или Piper в Admin Panel → Services → TTS

### Нет звука в чате

**Проверка:**
1. Admin Panel → Services → TTS → выберите TTS engine (XTTS, OpenVoice, Piper)
2. Admin Panel → Services → TTS → выберите voice preset
3. Протестируйте голос: введите текст → "Test Voice"

**Возможные причины:**

| Проблема | Решение |
|----------|---------|
| TTS engine не выбран | Выберите XTTS, OpenVoice или Piper |
| Voice preset отсутствует | Создайте пресет в Admin Panel → TTS |
| Ошибка синтеза | Проверьте логи orchestrator: `docker logs ai-secretary-orchestrator` |

### GPU out of memory при TTS

**Симптомы:**
- XTTS работает, но через время падает с OOM
- После синтеза нескольких аудио система зависает

**Причина:** vLLM (50%, ~6GB) + XTTS (~5GB) не помещаются в 12GB GPU

**Решения:**
1. Используйте XTTS только для коротких фраз (<100 символов)
2. Переключитесь на Piper (работает на CPU, 0 GPU памяти)
3. Уменьшите vLLM `gpu_memory_utilization` до 0.4 в `docker-compose.yml`
4. Используйте OpenVoice (требует меньше GPU памяти)

## Telegram боты

### Бот не запускается

**Симптомы:**
- Статус "stopped" в Admin Panel → Telegram Bots
- Ошибка в логах: "Unauthorized"

**Проверка:**
```bash
# Логи бота (ID из админки)
cat logs/telegram_bot_1.log

# Или в реальном времени
tail -f logs/telegram_bot_1.log
```

**Решения:**

| Ошибка | Решение |
|--------|---------|
| "401 Unauthorized" | Неверный токен — получите новый у @BotFather |
| "Conflict: terminated by other getUpdates" | Бот запущен в другом месте — остановите дубликат |
| "Network error" | Проверьте интернет-соединение |

### Бот не отвечает на сообщения

**Причины:**

1. **LLM backend не настроен:** Admin Panel → Telegram Bots → [Bot] → AI Settings → выберите LLM backend
2. **vLLM недоступен:** проверьте `curl http://localhost:11434/v1/models`
3. **Cloud LLM провайдер выключен:** Admin Panel → Services → LLM → Cloud Providers → включите провайдера
4. **Ошибка в промпте:** проверьте системный промпт бота на корректность

**Дебаг:**
```bash
# Проверить статус бота
curl -X GET http://localhost:8002/admin/telegram/bots/1 \
  -H "Authorization: Bearer <token>"

# Отправить тестовое сообщение
curl -X POST http://localhost:8002/admin/telegram/bots/1/test \
  -H "Authorization: Bearer <token>"
```

### Платежи не работают

**YooMoney (ЮMoney):**

1. Проверьте Payment Config в настройках бота
2. Убедитесь, что указан корректный webhook URL
3. Проверьте секретный ключ в настройках ЮMoney

**Telegram Stars:**

1. Убедитесь, что Stars включён в настройках бота (Payment tab)
2. Проверьте, что бот имеет права на приём платежей (@BotFather → /mybots → Bot Settings → Payments)

## Виджеты

### Виджет не отображается на сайте

**Симптомы:**
- Скрипт `ai-chat-widget.js` загружается, но иконка не появляется
- Консоль браузера: "Widget instance disabled"

**Причины:**

| Проблема | Решение |
|----------|---------|
| Виджет выключен | Admin Panel → Chat Widgets → включите виджет |
| Домен не в whitelist | Добавьте домен в `allowed_domains` (например: `example.com`) |
| `/widget/status` возвращает `enabled: false` | Проверьте статус виджета через API |

**Проверка статуса (публичный эндпоинт):**
```bash
curl http://localhost:8002/widget/status?instance_id=123
# Ответ: {"enabled": true, "name": "My Widget"}
```

### CORS ошибки

**Симптомы:**
- Браузер блокирует запросы к API
- Ошибка "Access-Control-Allow-Origin"

**Решение:** `ai-chat-widget.js` автоматически добавляет заголовок `Access-Control-Allow-Origin: *`. Если проблема сохраняется:

1. Проверьте, что используете актуальную версию виджета
2. Убедитесь, что tunnel URL корректен (ngrok, cloudflare, etc.)
3. Проверьте настройки CORS в orchestrator (должно быть разрешено `*` для widget endpoints)

## amoCRM

### Не удаётся подключиться к amoCRM

**Симптомы:**
- OAuth redirect не работает
- Ошибка "invalid_client"
- Таймаут при тесте подключения

**Решения:**

| Проблема | Решение |
|----------|---------|
| Неверный subdomain | Проверьте: должно быть `yourcompany` (не `yourcompany.amocrm.ru`) |
| Неверный client_id / secret | Скопируйте из настроек интеграции в amoCRM |
| Неверный redirect_uri | Должен совпадать с указанным в интеграции (например: `http://localhost:8002/admin/amocrm/callback`) |

**Для частных интеграций:**
1. Получите код авторизации из настроек интеграции в amoCRM
2. Вставьте в Admin Panel → Services → amoCRM → "Authorization Code"
3. Нажмите "Сохранить" — система обменяет код на токены

### Docker не видит amoCRM (VPN на хосте)

**Симптомы:**
- amoCRM API доступен с хоста, но не из Docker контейнера
- Ошибка "Connection timeout"

**Причина:** VPN настроен только на хосте, Docker bridge не имеет доступа

**Решение:** Запустите прокси на хосте

1. **Запустите прокси скрипт на хосте:**
```bash
python scripts/amocrm_proxy.py
# Прокси слушает на http://localhost:8899
```

2. **Настройте env переменную в Docker:**
```bash
AMOCRM_PROXY=http://host.docker.internal:8899
```

3. **Перезапустите orchestrator:**
```bash
docker compose restart orchestrator
```

Теперь все запросы к amoCRM будут идти через хост-прокси с доступом к VPN.

## Общие проблемы

### Vosk модель не найдена

**Симптомы:**
- STT не работает
- Ошибка "Model path not found"

**Решение:** Скачайте модель Vosk:

```bash
mkdir -p models/vosk
cd models/vosk
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 model
```

Путь должен быть: `models/vosk/model/am/`, `models/vosk/model/graph/`, и т.д.

### OpenWebUI не подключается к vLLM

**Симптомы:**
- OpenWebUI не видит модели
- Ошибка "Connection refused"

**Причина:** В Docker используется `localhost`, который указывает внутрь контейнера

**Решение:** В настройках OpenWebUI укажите:
```
http://172.17.0.1:11434
```
Это IP Docker bridge, доступный из контейнеров.

### База данных ошибка

**Симптомы:**
- "database is locked"
- "unable to open database file"

**Решения:**

| Проблема | Решение |
|----------|---------|
| Недостаточно места на диске | Очистите диск: `df -h`, удалите старые логи |
| Файл БД повреждён | Восстановите из бэкапа: Admin Panel → Settings → Backup |
| Миграция не применена | Запустите миграции: `python scripts/migrate_*.py` |

**Проверка целостности БД:**
```bash
sqlite3 data.db "PRAGMA integrity_check;"
# Ответ должен быть: ok
```

## Логи и мониторинг

### Где искать логи

| Сервис | Путь к логам |
|--------|--------------|
| Orchestrator | `docker logs ai-secretary-orchestrator` |
| vLLM | `docker logs ai-secretary-vllm` |
| Telegram бот | `logs/telegram_bot_{id}.log` |
| GSM | `logs/gsm_service.log` |

### Полезные команды

```bash
# Все логи в реальном времени
docker compose logs -f

# Только orchestrator
docker compose logs -f orchestrator

# Последние 100 строк
docker compose logs --tail=100 orchestrator

# Статус сервисов
curl http://localhost:8002/health

# Мониторинг GPU
nvidia-smi -l 1
```

## Дополнительная помощь

Если проблема не решена:

1. Проверьте [[Installation]] — возможно, пропущен шаг установки
2. Изучите [[API-Reference]] — убедитесь, что запросы корректны
3. Откройте issue на GitHub с логами и описанием проблемы
4. Задайте вопрос в Telegram-чате проекта

---

← [[API-Reference]] | [[Home]] →
