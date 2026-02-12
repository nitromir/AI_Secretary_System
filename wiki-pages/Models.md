# Models (Модели)

Управление AI-моделями: загрузка из HuggingFace Hub, просмотр, удаление, переключение.

> **Видимость:** Скрыта в режиме `cloud` и для роли `web`.

## Категории моделей

### LLM модели (для vLLM)

| Модель | Параметры | Формат | VRAM | Скорость |
|--------|-----------|--------|------|----------|
| Qwen2.5-7B-Instruct-AWQ | 7B | AWQ-Int4 | ~6 GB | Быстро |
| Qwen2.5-7B-Instruct | 7B | FP16 | ~14 GB | Быстро |
| Llama-3.1-8B-Instruct-GPTQ | 8B | GPTQ-Int4 | ~8 GB | Быстро |
| DeepSeek-7B-Chat | 7B | FP16 | ~14 GB | Средне |

**Рекомендация:** AWQ/GPTQ модели для GPU с 12 GB VRAM.

### TTS модели

| Модель | Движок | Размер | GPU |
|--------|--------|--------|-----|
| XTTS v2 | Coqui TTS | ~2 GB | CC ≥ 7.0 |
| ru_RU-dmitri-medium | Piper | ~60 MB | CPU |
| ru_RU-irina-medium | Piper | ~60 MB | CPU |

XTTS скачивается автоматически при первом использовании в `~/.cache/tts_models/`. Piper модели лежат в `models/piper/`.

### STT модели

| Модель | Движок | Язык | Размер |
|--------|--------|------|--------|
| vosk-model-ru-0.42 | Vosk | Русский | ~1.5 GB |
| vosk-model-small-ru | Vosk | Русский (мини) | ~45 MB |
| Whisper | OpenAI Whisper | Мульти | Авто |

Vosk модель нужно скачать вручную в `models/vosk/`. Whisper скачивается автоматически.

### LoRA адаптеры

Обученные LoRA адаптеры из [[Finetune]]:

| Адаптер | База | Назначение |
|---------|------|------------|
| qwen2.5-7b-anna-lora | Qwen2.5-7B | Персона Анна |
| qwen2.5-7b-marina-lora | Qwen2.5-7B | Персона Марина |

Расположение: `models/lora/` или `finetune/output/`.

## Загрузка модели

### Через админ-панель

1. Нажмите "Скачать модель"
2. Введите HuggingFace ID: `Qwen/Qwen2.5-7B-Instruct-AWQ`
3. Дождитесь загрузки (прогресс-бар, скорость, ETA)
4. Модель появится в списке

### Через API

```bash
POST /admin/llm/models/download
{"model_id": "Qwen/Qwen2.5-7B-Instruct-AWQ"}
```

Прогресс через SSE: `GET /admin/llm/models/download/progress`

## Управление

### Удаление

1. Выберите модель → иконка корзины
2. Подтвердите удаление

Нельзя удалить модель, которая используется активным vLLM.

### Активация LoRA

```bash
POST /admin/finetune/adapters/activate
{"adapter": "qwen2.5-7b-anna-lora"}
```

Hot-swap без перезапуска vLLM (если vLLM поддерживает).

## Пути хранения

| Тип | Путь |
|-----|------|
| LLM | `~/.cache/huggingface/` (HF Hub cache) |
| XTTS | `~/.cache/tts_models/` |
| Piper | `models/piper/` |
| Vosk | `models/vosk/` |
| LoRA | `models/lora/` или `finetune/output/` |

## Выбор модели по VRAM

| VRAM | Рекомендация |
|------|-------------|
| 8 GB | Qwen2.5-7B AWQ (+ Piper TTS) |
| 12 GB | Qwen2.5-7B AWQ + XTTS v2 |
| 16 GB+ | Llama-3.1-8B FP16 + XTTS v2 |
| Без GPU | Cloud LLM + Piper TTS |

## API

| Endpoint | Описание |
|----------|----------|
| `GET /admin/llm/models` | Список моделей |
| `POST /admin/llm/models/download` | Начать загрузку |
| `GET /admin/llm/models/download/progress` | SSE прогресса |
| `DELETE /admin/llm/models/{model_id}` | Удалить модель |
| `GET /admin/finetune/adapters` | Список LoRA адаптеров |
| `POST /admin/finetune/adapters/activate` | Активировать LoRA |

---

← [[Monitoring]] | [[Widget]] →
