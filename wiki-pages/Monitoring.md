# Monitoring (Мониторинг)

Полный мониторинг системы: GPU, CPU, RAM, диски, Docker контейнеры, сеть, процессы и логи.

> **Видимость:** Скрыта в режиме `cloud` и для роли `web`.

## Обзор

Страница мониторинга использует `SystemMonitor` (`system_monitor.py`) для сбора данных через nvidia-smi, psutil и Docker CLI. Данные обновляются в реальном времени через SSE с fallback на polling.

## GPU метрики

### Графики реального времени

| Метрика | Описание | Источник |
|---------|----------|----------|
| **Utilization** | Загрузка GPU (%) | nvidia-smi |
| **VRAM Usage** | Использование видеопамяти (MB) | nvidia-smi |
| **Temperature** | Температура (°C) | nvidia-smi |
| **Power Draw** | Потребление энергии (W) | nvidia-smi |
| **Fan Speed** | Скорость вентилятора (%) | nvidia-smi |

Графики на Chart.js, история за 5 минут (60 точек с интервалом 5 сек).

### Детальная информация о GPU

| Поле | Описание |
|------|----------|
| **Название** | NVIDIA RTX 3060 и т.д. |
| **Driver** | Версия драйвера NVIDIA |
| **Compute Capability** | CC версия (напр. 8.6) |
| **PCIe** | Поколение и ширина шины |
| **Memory** | Total / Used / Free (MB) |

Fallback: если nvidia-smi недоступен, данные берутся через PyTorch (`torch.cuda`).

## CPU метрики

| Метрика | Описание |
|---------|----------|
| **Model** | Модель процессора |
| **Cores** | Физические / логические ядра |
| **Frequency** | Текущая / максимальная частота (MHz) |
| **Usage** | Общая загрузка (%) |
| **Per-core** | Загрузка каждого ядра |
| **Temperature** | Температура CPU (coretemp/k10temp) |
| **Load Average** | 1m / 5m / 15m |

## Память

| Метрика | Описание |
|---------|----------|
| **RAM** | Total / Used / Free / Available (GB) + процент |
| **Swap** | Total / Used (GB) + процент |

## Диски

Для каждого раздела (без squashfs/tmpfs/snap):

| Поле | Описание |
|------|----------|
| **Device** | `/dev/sda1` и т.д. |
| **Mount** | Точка монтирования |
| **Type** | Файловая система (ext4, xfs) |
| **Usage** | Total / Used / Free (GB) + процент |

## Docker контейнеры

Если Docker доступен — таблица всех контейнеров:

| Поле | Описание |
|------|----------|
| **Name** | Имя контейнера |
| **Image** | Docker образ |
| **Status** | Running / Exited / Created |
| **CPU** | Использование CPU (%) |
| **Memory** | Использование RAM (MB / лимит) |
| **Ports** | Проброшенные порты |
| **Uptime** | Время работы |

## Сеть

Для каждого физического интерфейса (без lo/docker/veth):

| Поле | Описание |
|------|----------|
| **Interface** | Имя (eth0, ens3) |
| **IP** | IPv4 адрес |
| **MAC** | MAC адрес |
| **Traffic** | Sent / Received (MB) |
| **Packets** | Sent / Received |
| **Status** | Up / Down |

## Процессы

Топ-10 процессов по CPU + RAM:

| Поле | Описание |
|------|----------|
| **PID** | ID процесса |
| **Name** | Имя |
| **CPU** | Использование CPU (%) |
| **Memory** | Использование RAM (%) и MB |
| **Status** | Running / Sleeping / Zombie |
| **Command** | Командная строка (первые 100 символов) |

## Системная информация

| Поле | Описание |
|------|----------|
| **Hostname** | Имя хоста |
| **OS** | ОС и версия ядра |
| **Uptime** | Время работы системы |
| **Boot Time** | Время последней загрузки |

## SSE vs Polling

| Режим | Поведение |
|-------|-----------|
| **SSE** (предпочтительно) | Мгновенные обновления через `/admin/monitor/gpu/stream` |
| **Polling** (fallback) | Запрос каждые 5 секунд к `/admin/monitor/gpu` |

Переключение автоматическое: SSE → при ошибке → polling.

## API

| Endpoint | Описание |
|----------|----------|
| `GET /admin/monitor/gpu` | GPU статистика |
| `GET /admin/monitor/gpu/stream` | SSE поток GPU |
| `GET /admin/monitor/health` | Компонентный health check |
| `GET /admin/monitor/metrics` | Метрики запросов |
| `GET /admin/monitor/errors` | Последние ошибки |
| `POST /admin/monitor/metrics/reset` | Сброс счётчиков |
| `GET /admin/monitor/system` | Полный статус (GPU + CPU + RAM + Disk + Docker + Network + Processes) |

---

← [[Finetune]] | [[Models]] →
