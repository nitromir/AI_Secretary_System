# Установка AI Secretary System

Пошаговая инструкция по установке и запуску системы. Поддерживается два режима: **Docker** (рекомендуется) и **локальная установка**.

## Системные требования

### Минимальные (CPU режим — облачные LLM)

- ОС: Ubuntu 22.04+ / Debian 12+ / любой Linux с Docker
- CPU: 2 ядра
- RAM: 4 ГБ
- Диск: 5 ГБ
- API-ключ облачного LLM (Gemini, OpenAI, Claude, DeepSeek и др.)

### Рекомендуемые (GPU режим — локальный LLM + клонирование голоса)

- ОС: Ubuntu 22.04+ с NVIDIA драйверами
- GPU: NVIDIA RTX 3060 12GB или лучше (CUDA CC >= 7.0)
- CPU: 4 ядра
- RAM: 16 ГБ
- Диск: 30 ГБ (модели ~15GB + Docker образы ~9GB)

### Распределение GPU памяти (RTX 3060 12GB)

| Сервис | Память | Назначение |
|--------|--------|------------|
| vLLM | ~6 ГБ (50%) | Локальная языковая модель (Qwen/Llama/DeepSeek) |
| XTTS v2 | ~5 ГБ | Клонирование голоса |
| Система | ~1 ГБ | Буфер |

## Способ 1: Docker (рекомендуется)

### Предварительные требования

```bash
# Docker и Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогиньтесь после этой команды

# Для GPU: NVIDIA Container Toolkit
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Установка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/ShaerWare/AI_Secretary_System.git
cd AI_Secretary_System

# 2. Создайте файл конфигурации
cp .env.docker.example .env

# 3. Отредактируйте .env — укажите ключи API (если используете облачные LLM)
nano .env

# 4. Запуск
docker compose up -d          # GPU режим
# или
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d  # CPU режим
```

### Проверка

```bash
# Статус контейнеров
docker compose ps

# Логи
docker compose logs -f orchestrator

# Проверка здоровья
curl http://localhost:8002/health
```

### Доступ

- Админ-панель: `http://localhost:8002/admin/`
- Логин: `admin`
- Пароль: `admin`

## Способ 2: Локальная установка

### Предварительные требования

```bash
# Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev

# Node.js 18+ (для админ-панели)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Системные зависимости
sudo apt install -y git ffmpeg redis-server
```

### Установка

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/ShaerWare/AI_Secretary_System.git
cd AI_Secretary_System

# 2. Создайте виртуальное окружение Python
python3.11 -m venv venv
source venv/bin/activate

# 3. Установите Python-зависимости
pip install --upgrade pip
pip install -r requirements.txt

# Для CPU режима (без тяжёлых TTS/STT):
pip install fastapi uvicorn python-multipart websockets slowapi \
    aiosqlite sqlalchemy[asyncio] redis pydantic python-dotenv \
    psutil aiohttp requests google-generativeai \
    python-telegram-bot aiogram piper-tts

# 4. Соберите админ-панель
cd admin
npm install
npm run build
cd ..

# 5. Создайте .env
cp .env.example .env
nano .env

# 6. Инициализируйте базу данных
python scripts/migrate_users.py
```

### Запуск

```bash
# CPU режим (Piper TTS + облачные LLM)
./start_cpu.sh

# GPU режим (XTTS + vLLM + LoRA)
./start_gpu.sh

# GPU с выбором модели
./start_gpu.sh --llama      # Llama-3.1-8B
./start_gpu.sh --deepseek   # DeepSeek-7B
```

### Проверка

```bash
curl http://localhost:8002/health
```

## Настройка после установки

### 1. Создание пользователей

```bash
# Создать обычного пользователя
python scripts/manage_users.py create myuser mypassword --role user

# Создать веб-пользователя (ограниченный доступ)
python scripts/manage_users.py create webuser webpass --role web

# Список пользователей
python scripts/manage_users.py list
```

Роли:
- `admin` — полный доступ ко всем функциям
- `user` — чтение + запись своих ресурсов, полная админ-панель
- `web` — как user, но без серверных настроек (vLLM, TTS, Models)
- `guest` — только чтение (демо-доступ)

### 2. Подключение облачного LLM

1. Откройте админ-панель → LLM
2. Нажмите «Добавить провайдера»
3. Выберите тип (Gemini, OpenAI, Claude, DeepSeek, OpenRouter, Kimi)
4. Введите API-ключ
5. Нажмите «Тест» для проверки
6. Переключите LLM backend на облачного провайдера

### 3. Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Скопируйте токен бота
3. Админ-панель → Telegram → «Добавить инстанс»
4. Вставьте токен, настройте LLM backend и промпт
5. Нажмите «Запустить»

### 4. Настройка веб-виджета

1. Админ-панель → Widget → «Добавить инстанс»
2. Настройте внешний вид и LLM backend
3. Скопируйте код встраивания:

```html
<script src="http://your-server:8002/widget/ai-chat-widget.js"
        data-instance-id="1"></script>
```

### 5. Загрузка базы знаний

1. Админ-панель → Fine-tune → Cloud AI (или для web-пользователя: Fine-tune)
2. Нажмите «Загрузить документ» — поддерживаются `.md` и `.txt` файлы
3. После загрузки нажмите «Переиндексировать»
4. Используйте «Тестовый поиск» для проверки

Документы хранятся в папке `wiki-pages/` на сервере.

## Ключевые переменные окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `LLM_BACKEND` | `vllm` | `vllm` (локальный GPU) или `cloud:{id}` (облачный провайдер) |
| `ORCHESTRATOR_PORT` | `8002` | Порт приложения |
| `SECRETARY_PERSONA` | `anna` | Персона секретаря: `anna` или `marina` |
| `ADMIN_JWT_SECRET` | (авто) | Секрет для JWT токенов (задайте для продакшена) |
| `GEMINI_API_KEY` | — | API-ключ Gemini (для fallback при недоступности vLLM) |
| `HF_TOKEN` | — | Токен Hugging Face (для закрытых моделей типа Llama) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis (опционально, кэширование) |
| `RATE_LIMIT_ENABLED` | `true` | Включить rate limiting |
| `DEV_MODE` | — | `1` для проксирования на Vite dev server (:5173) |

## Обновление

```bash
# Обновить код
git pull origin main

# Пересобрать админ-панель
cd admin && npm install && npm run build && cd ..

# Выполнить новые миграции (если есть)
python scripts/migrate_knowledge_base.py  # Пример

# Перезапустить
# Docker:
docker compose restart

# Локально:
# Остановите текущий процесс (Ctrl+C) и запустите заново
./start_cpu.sh
```

## Устранение неполадок

### Сервер не запускается

```bash
# Проверьте логи
tail -50 logs/orchestrator.log

# Проверьте зависимости
./venv/bin/pip install slowapi  # Частая причина: не установлен slowapi
```

### vLLM не запускается (GPU)

```bash
# Проверьте GPU
nvidia-smi

# Проверьте логи vLLM
tail -50 logs/vllm.log

# Первый запуск скачивает модель (~5-7GB) — подождите
```

### XTTS требует GPU с CUDA CC >= 7.0

- RTX 3060 и выше — работает
- Для старых GPU используйте OpenVoice или CPU режим с Piper TTS

### Админ-панель не открывается

```bash
# Пересоберите
cd admin && npm install && npm run build && cd ..

# Проверьте что файлы на месте
ls admin/dist/index.html
```

### Redis недоступен

Redis опционален. Система работает и без него — в логах будет предупреждение, но всё функционирует.
