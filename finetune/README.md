# Lydia Fine-tuning Pipeline

Дообучение LLM для создания персонального ассистента "Марина" для ООО "Shaerware Digital".

## Структура

```
finetune/
├── train.py                 # Дообучение Qwen2.5-7B (LoRA)
├── prepare_dataset.py       # Подготовка датасета из Telegram
├── merge_lora.py            # Объединение LoRA с базовой моделью
├── quantize_awq.py          # Квантизация модели (W4A16)
├── datasets/                # Датасеты (симлинки, не в git)
│   ├── result.json          # Экспорт чатов из Telegram
│   ├── lydia_dataset_v2.jsonl
│   └── lydia_dataset_v3.jsonl
└── adapters/                # Модели (симлинки, не в git)
    └── qwen2.5-7b-lydia-lora/
```

**Данные хранятся в:** `/home/shaerware/qwen-finetune/`

## Пайплайн

### 1. Подготовка датасета

```bash
cd finetune
source /home/shaerware/qwen-finetune/train_venv/bin/activate
python prepare_dataset.py
```

Преобразует экспорт Telegram в формат для обучения:
- Личные чаты → диалоги user/assistant
- Склеивает последовательные сообщения
- Разбивает на куски по 20 сообщений

### 2. Дообучение (LoRA)

```bash
python train.py
```

| Параметр | Значение |
|----------|----------|
| Базовая модель | Qwen/Qwen2.5-7B-Instruct |
| Метод | LoRA (rank 8, alpha 16) |
| Target modules | q_proj, k_proj, v_proj |
| Квантизация | 4-bit NF4 |
| GPU | RTX 3060 (12GB) |

### 3. Объединение модели (опционально)

```bash
python merge_lora.py
```

Объединяет LoRA с базовой моделью. Требует ~30GB RAM.

### 4. Квантизация (опционально)

```bash
source /home/shaerware/qwen-finetune/quant_venv/bin/activate
python quantize_awq.py
```

## Использование с vLLM

Обученный адаптер используется в основной системе:

```bash
# Из корня AI_Secretary_System
./start_gpu.sh    # Запускает vLLM + LoRA + Orchestrator
./start_qwen.sh   # Только vLLM с LoRA
```

LoRA автоматически загружается из `finetune/adapters/qwen2.5-7b-lydia-lora/final/`

## Добавление новых данных

1. Экспортируй чаты из Telegram (JSON)
2. Положи `result.json` в `datasets/`
3. Измени `OWNER_NAME` в `prepare_dataset.py` если нужно
4. Запусти пайплайн:

```bash
python prepare_dataset.py
python train.py
```
