# Finetune (Дообучение)

Система дообучения включает два независимых пайплайна: **LLM fine-tuning** (LoRA-адаптеры для языковой модели) и **TTS fine-tuning** (дообучение голосовой модели Qwen3-TTS). Оба доступны из админ-панели на вкладке Finetune (две подвкладки: LLM и TTS).

## Скриншот

<!-- Вставьте скриншот страницы Finetune -->
![Finetune](images/finetune.png)

---

## LLM Fine-tuning (LoRA)

Дообучение языковой модели методом **LoRA (Low-Rank Adaptation)** — модифицируются только малоранговые матрицы в attention-слоях, что требует значительно меньше VRAM и времени, чем полное дообучение.

Базовая модель: `Qwen/Qwen2.5-7B-Instruct`. Квантизация: 4-bit NF4 (bitsandbytes). Target modules: `q_proj`, `k_proj`, `v_proj`.

### Порядок процесса

```
1. Подготовка данных    →  Upload Telegram JSON или генерация из проекта
2. Обработка датасета   →  Парсинг → фильтрация → JSONL
3. Настройка параметров →  Выбор пресета или ручная настройка
4. Обучение             →  Запуск train.py как subprocess, мониторинг в реальном времени
5. Активация адаптера   →  Выбор адаптера → рестарт vLLM
```

### 1. Подготовка данных

Два способа получить обучающий датасет:

#### Из Telegram-экспорта

1. Экспортируйте чат из Telegram Desktop (формат JSON — файл `result.json`)
2. На вкладке Finetune → LLM нажмите **"Загрузить датасет"** и выберите файл
3. Настройте параметры обработки:

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| **owner_name** | Имя владельца (чьи сообщения станут ответами assistant) | — |
| **transcribe_voice** | Транскрибировать голосовые сообщения через Whisper | false |
| **min_dialog_messages** | Минимум сообщений в диалоге для включения | 2 |
| **max_message_length** | Максимальная длина сообщения (символов) | 2000 |
| **max_dialog_length** | Максимум сообщений в одном диалоге (длинные нарезаются) | 20 |
| **include_groups** | Включать групповые чаты | false |

4. Нажмите **"Обработать"** — система парсит JSON, фильтрует, объединяет последовательные сообщения от одного автора, нарезает на чанки

**Формат выходного JSONL:**

```json
{"messages": [{"from": "user", "value": "Привет, как дела?"}, {"from": "assistant", "value": "Здравствуйте! Всё отлично, чем могу помочь?"}]}
```

Файл сохраняется в `finetune/datasets/{output_name}_dataset.jsonl`.

#### Генерация из проекта

Кнопка **"Сгенерировать датасет из проекта"** создаёт обучающие данные автоматически из нескольких источников:

| Источник | Флаг | Что включает |
|----------|------|-------------|
| **Сценарии продаж** | include_tz | Диалоги из ТЗ бота (docs/tz/) |
| **FAQ** | include_faq | Все пары вопрос-ответ из базы данных |
| **Документация** | include_docs | Технические Q&A из CLAUDE.md и docs/ |
| **Эскалация** | include_escalation | Шаблоны передачи клиента оператору |
| **Код** | include_code | Python-роутеры, ORM-модели, Pydantic-схемы, docstrings |
| **GitHub** | github_url + branch | Shallow clone внешнего репозитория, парсинг *.py и *.md |

Результат: `finetune/datasets/project_dataset.jsonl`.

### 2. Настройка параметров обучения

Три готовых пресета и ручная настройка:

| Параметр | Quick | Standard | Thorough | Описание |
|----------|-------|----------|----------|----------|
| **LoRA Rank** | 4 | 8 | 16 | Ранг адаптера (больше = больше параметров) |
| **LoRA Alpha** | 8 | 16 | 32 | Масштабирующий коэффициент |
| **LoRA Dropout** | 0.05 | 0.05 | 0.05 | Dropout в LoRA-слоях |
| **Batch Size** | 1 | 1 | 1 | Размер батча (ограничен VRAM) |
| **Grad Accumulation** | 32 | 64 | 128 | Шагов аккумуляции (эффективный батч) |
| **Learning Rate** | 2e-4 | 2e-4 | 2e-4 | Начальная скорость обучения |
| **Epochs** | 1 | 1 | 2 | Количество эпох |
| **Max Seq Length** | 512 | 768 | 1024 | Максимальная длина последовательности |

Дополнительно: `warmup_ratio` (0.03), `weight_decay` (0.01), `gradient_checkpointing` (true), `fp16` (true).

Конфигурация сохраняется в `finetune/training_config.json`.

### 3. Обучение

**Запуск:** нажмите **"Начать обучение"**. Система запускает `finetune/train.py` как subprocess в отдельном virtualenv (`~/qwen-finetune/train_venv`) с `CUDA_VISIBLE_DEVICES=1`.

**Мониторинг в реальном времени:**

- **Прогресс-бар** — текущий шаг / всего шагов, процент
- **Метрики** — epoch, loss, learning rate, ETA (расчётное время до конца)
- **Логи** — последние 100 строк в прокручиваемом окне (хранится до 10K строк)
- **SSE-стрим** — `GET /admin/finetune/train/log` для real-time логов

**Остановка:** кнопка **"Остановить"** завершает процесс. Чекпоинты сохраняются каждые 200 шагов.

> Одновременно может работать только одно обучение (process-level lock).

### 4. Управление адаптерами

После завершения обучения адаптер появляется в списке. Хранение: `finetune/adapters/{name}/final/` (файлы `adapter_config.json` + `adapter_model.safetensors`).

| Действие | Описание |
|----------|----------|
| **Активировать** | Пометить адаптер как активный (записывается в `finetune/adapters/.active`) |
| **Удалить** | Удалить директорию адаптера |

**Деплой:** после активации адаптера необходимо **перезапустить vLLM** — при старте он читает `.active` файл и загружает указанный адаптер. Горячая замена через API vLLM пока в планах.

**Альтернатива — слияние весов:** скрипт `finetune/merge_lora.py` объединяет LoRA-веса с базовой моделью в единую модель. Требует ~30GB RAM (загрузка на CPU). После слияния адаптер не нужен при инференсе.

### Статистика датасета

На вкладке отображается статистика текущего датасета:
- Количество сессий/диалогов
- Общее количество сообщений
- Приблизительное число токенов
- Размер файла
- Распределение по источникам (для проектного датасета)

---

## TTS Fine-tuning (Qwen3-TTS)

Дообучение голосовой модели для создания пользовательского голоса.

Базовая модель: `Qwen/Qwen3-TTS-12Hz-1.7B-Base`. Базовая директория: `~/qwen3-tts/`.

### Порядок процесса

```
1. Загрузка голосовых сэмплов  →  WAV/MP3/OGG файлы
2. Транскрибация               →  Whisper (авто) или ручной ввод текста
3. Подготовка датасета          →  Извлечение audio codes через токенизатор
4. Обучение                    →  sft_12hz.py, чекпоинты по эпохам
```

### 1. Загрузка голосовых сэмплов

Загрузите аудиофайлы (WAV, MP3, OGG) через кнопку **"Upload"**. Система автоматически извлекает длительность через `soundfile`. Метаданные хранятся в `~/qwen3-tts/samples_metadata.json`.

Для каждого сэмпла отображается: имя файла, длительность, размер, транскрипт.

### 2. Транскрибация

Кнопка **"Transcribe with Whisper"** запускает распознавание речи на всех сэмплах.

| Параметр | Описание | Варианты |
|----------|----------|----------|
| **whisper_model** | Размер модели Whisper | tiny, base, small, medium, large |
| **language** | Язык | ru, en и др. |
| **min_duration_sec** | Минимальная длительность сэмпла | 1.0 |
| **max_duration_sec** | Максимальная длительность сэмпла | 30.0 |

Транскрипт можно отредактировать вручную через кнопку редактирования рядом с каждым сэмплом.

### 3. Подготовка датасета

Кнопка **"Prepare Dataset"** вызывает `prepare_data.py`, который:
1. Создаёт raw JSONL с путями к аудио и транскриптами
2. Извлекает audio codes через токенизатор базовой модели
3. Формирует финальный JSONL для обучения

### 4. Обучение

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| **batch_size** | 2 | Размер батча |
| **gradient_accumulation_steps** | 4 | Шагов аккумуляции |
| **learning_rate** | 2e-5 | Скорость обучения |
| **num_epochs** | 3 | Количество эпох |

Чекпоинты сохраняются по эпохам: `checkpoint-epoch-1/`, `checkpoint-epoch-2/` и т.д.

Мониторинг аналогичен LLM: прогресс, loss, логи.

### Обученные модели

Список обученных моделей отображается с указанием количества эпох и даты модификации.

---

## Требования

| Ресурс | LLM Fine-tuning | TTS Fine-tuning |
|--------|-----------------|-----------------|
| **GPU** | RTX 3060+ (12GB VRAM) | RTX 3060+ (12GB VRAM) |
| **RAM** | 16GB+ (30GB для merge_lora) | 16GB+ |
| **Диск** | ~50MB на адаптер | ~500MB на чекпоинт |
| **Virtualenv** | `~/qwen-finetune/train_venv` | `~/qwen3-tts/tts_venv` |

> Всё обучение происходит локально, данные не отправляются в облако.

---

## API-эндпоинты

### LLM Fine-tuning

```
# Датасет
POST /admin/finetune/dataset/upload              # Загрузить Telegram-экспорт
POST /admin/finetune/dataset/process             # Обработать в JSONL
GET  /admin/finetune/dataset/config              # Настройки обработки
POST /admin/finetune/dataset/config              # Обновить настройки
GET  /admin/finetune/dataset/processing-status   # Прогресс обработки
GET  /admin/finetune/dataset/stats               # Статистика датасета
GET  /admin/finetune/dataset/list                # Список датасетов
POST /admin/finetune/dataset/generate-project    # Генерация из проекта

# Обучение
GET  /admin/finetune/config                      # Параметры обучения + пресеты
POST /admin/finetune/config                      # Обновить параметры
POST /admin/finetune/train/start                 # Запустить обучение
POST /admin/finetune/train/stop                  # Остановить обучение
GET  /admin/finetune/train/status                # Прогресс обучения
GET  /admin/finetune/train/log                   # SSE-стрим логов

# Адаптеры
GET    /admin/finetune/adapters                  # Список адаптеров
POST   /admin/finetune/adapters/activate         # Активировать адаптер
DELETE /admin/finetune/adapters/{name}            # Удалить адаптер
```

### TTS Fine-tuning

```
# Сэмплы
GET    /admin/tts-finetune/samples                        # Список сэмплов
POST   /admin/tts-finetune/samples/upload                 # Загрузить аудио
DELETE /admin/tts-finetune/samples/{filename}              # Удалить сэмпл
PUT    /admin/tts-finetune/samples/{filename}/transcript   # Задать транскрипт

# Обработка
POST /admin/tts-finetune/transcribe              # Транскрибировать сэмплы
POST /admin/tts-finetune/prepare                 # Подготовить датасет
GET  /admin/tts-finetune/processing-status       # Прогресс обработки

# Обучение
GET  /admin/tts-finetune/config                  # Конфигурация
POST /admin/tts-finetune/config                  # Обновить конфигурацию
POST /admin/tts-finetune/train/start             # Запустить обучение
POST /admin/tts-finetune/train/stop              # Остановить обучение
GET  /admin/tts-finetune/train/status            # Прогресс обучения
GET  /admin/tts-finetune/train/log               # Логи обучения
GET  /admin/tts-finetune/models                  # Список обученных моделей
```

---

## Структура файлов

```
finetune/                              # Скрипты и данные LLM fine-tuning
├── train.py                           # SFT-тренер (HuggingFace TRL)
├── prepare_dataset.py                 # Парсер Telegram JSON → JSONL
├── merge_lora.py                      # Слияние LoRA-весов с базовой моделью
├── quantize_awq.py                    # AWQ-квантизация
├── training_config.json               # Сохранённые параметры обучения
├── datasets/
│   ├── result.json                    # Raw Telegram-экспорт
│   └── *_dataset.jsonl                # Обработанные датасеты
└── adapters/
    ├── .active                        # Имя активного адаптера
    └── {adapter_name}/final/
        ├── adapter_config.json        # Конфигурация LoRA
        └── adapter_model.safetensors  # Веса адаптера

finetune_manager.py                    # Менеджер LLM fine-tuning (singleton)
tts_finetune_manager.py                # Менеджер TTS fine-tuning (singleton)

~/qwen3-tts/                           # TTS fine-tuning (внешняя директория)
├── voice_samples/                     # Загруженные аудиофайлы
├── samples_metadata.json              # Метаданные сэмплов
├── tts_config.json                    # Конфигурация TTS обучения
├── finetuning/                        # Данные для обучения
└── tts_venv/                          # Python virtualenv
```

---

← [[FAQ]] | [[Monitoring]] →
