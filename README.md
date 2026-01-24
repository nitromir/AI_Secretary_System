# AI Secretary System

Интеллектуальная система виртуального секретаря с клонированием голоса (XTTS v2, OpenVoice), предобученными голосами (Piper), локальным LLM (vLLM + Qwen/Llama) и облачным fallback (Gemini). Включает полнофункциональную Vue 3 админ-панель.

## Features

- **Multi-Voice TTS**: 5 голосов (2 клонированных XTTS, 1 OpenVoice, 2 Piper)
- **Multi-Persona LLM**: 2 персоны секретаря (Гуля, Лидия)
- **Local LLM**: vLLM с Qwen2.5-7B + LoRA fine-tuning
- **FAQ System**: Мгновенные ответы на типичные вопросы
- **Admin Panel**: Полнофункциональная Vue 3 админка с 7 вкладками
- **OpenAI-compatible API**: Интеграция с OpenWebUI
- **Fine-tuning Pipeline**: Загрузка датасета → Обучение → Hot-swap адаптеров

## Architecture

```
                              ┌──────────────────────────────────────────┐
                              │        Orchestrator (port 8002)          │
                              │           orchestrator.py                │
                              │                                          │
                              │  ┌────────────────────────────────────┐  │
                              │  │     Vue 3 Admin Panel (7 tabs)     │  │
                              │  │         admin/dist/                │  │
                              │  └────────────────────────────────────┘  │
                              └──────────────────┬───────────────────────┘
                                                 │
      ┌──────────────┬──────────────┬────────────┼────────────┬─────────────┬──────────────┐
      ↓              ↓              ↓            ↓            ↓             ↓              ↓
 Service        Finetune        LLM         Voice Clone   OpenVoice    Piper TTS       FAQ
 Manager        Manager       Service         XTTS v2       v2          (CPU)         System
service_      finetune_      vLLM/Gemini   voice_clone_  openvoice_   piper_tts_   typical_
manager.py    manager.py                   service.py    service.py   service.py   responses.json
```

### GPU Configuration (RTX 3060 12GB)

```
vLLM Qwen2.5-7B + LoRA  →  ~8.4GB (70% GPU, port 11434)
XTTS v2 voice cloning   →  ~3.6GB (remaining)
────────────────────────────────────────────────────────
Total                   →  12GB
```

## Quick Start

```bash
# First-time setup
./setup.sh
cp .env.example .env
# Edit .env: GEMINI_API_KEY (optional if using vLLM)

# GPU Mode (recommended): XTTS + Qwen2.5-7B + LoRA
./start_gpu.sh

# CPU Mode: Piper + Gemini API
./start_cpu.sh

# Health check
curl http://localhost:8002/health

# Admin Panel
open http://localhost:8002/admin
```

## Admin Panel

Полнофункциональная Vue 3 админ-панель с 7 вкладками:

| Tab | Description |
|-----|-------------|
| **Dashboard** | Статусы сервисов, GPU метрики, health |
| **Services** | Запуск/остановка vLLM, просмотр логов |
| **LLM** | Переключение backend, персоны, параметры генерации |
| **TTS** | Выбор голоса, пресеты XTTS, кастомные настройки |
| **FAQ** | Редактирование типичных ответов (CRUD) |
| **Finetune** | Загрузка датасета, обучение, управление адаптерами |
| **Monitoring** | GPU/CPU графики, логи ошибок |

### Development Mode

```bash
cd admin
npm install
npm run dev
# Open http://localhost:5173
```

### Technology Stack

- **Frontend**: Vue 3 + Composition API + TypeScript
- **Build**: Vite
- **Styling**: Tailwind CSS (dark theme)
- **State**: Pinia
- **Data**: TanStack Query (for caching)
- **Real-time**: SSE (Server-Sent Events)

## Voices

| Voice | Engine | GPU Required | Speed | Quality |
|-------|--------|--------------|-------|---------|
| `gulya` | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning |
| `lidia` | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning |
| `lidia_openvoice` | OpenVoice v2 | CC >= 6.1 | ~2-4s | Good cloning |
| `dmitri` | Piper | CPU | ~0.5s | Pre-trained male |
| `irina` | Piper | CPU | ~0.5s | Pre-trained female |

**Voice Samples:**
- `./Гуля/` - 122 WAV files
- `./Лидия/` - WAV files

**Switching Voice:**
```bash
# Via API
curl -X POST http://localhost:8002/admin/voice \
  -H "Content-Type: application/json" \
  -d '{"voice": "gulya"}'

# Via Admin Panel
open http://localhost:8002/admin → TTS tab
```

## Personas

| Persona | Name | Description |
|---------|------|-------------|
| `gulya` | Гуля (Гульнара) | Дружелюбный цифровой секретарь (default) |
| `lidia` | Лидия | Альтернативная персона |

**Switching Persona:**
```bash
# Environment variable
export SECRETARY_PERSONA=lidia

# Via API
curl -X POST http://localhost:8002/admin/llm/persona \
  -H "Content-Type: application/json" \
  -d '{"persona": "lidia"}'

# Via Admin Panel
open http://localhost:8002/admin → LLM tab
```

## LLM Backends

| Backend | Model | Speed | Requirements |
|---------|-------|-------|--------------|
| `vllm` | Qwen2.5-7B + LoRA | Fast | GPU 12GB+ |
| `vllm` | Llama-3.1-8B GPTQ | Fast | GPU 12GB+ |
| `gemini` | Gemini 2.5 Pro | Variable | API key |

**Switching Backend:**
```bash
# Environment variable
export LLM_BACKEND=vllm  # or "gemini"

# Via API
curl -X POST http://localhost:8002/admin/llm/backend \
  -H "Content-Type: application/json" \
  -d '{"backend": "vllm"}'
```

## API Reference

### OpenAI-Compatible (for OpenWebUI)

```bash
# Chat completion
curl -X POST http://localhost:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "gulya-secretary-qwen", "messages": [{"role": "user", "content": "Привет!"}]}'

# Text-to-Speech
curl -X POST http://localhost:8002/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Привет!", "voice": "gulya"}' \
  -o output.wav

# List models
curl http://localhost:8002/v1/models
```

### Admin API (~45 endpoints)

```bash
# Services
GET  /admin/services/status          # All services status
POST /admin/services/{name}/start    # Start service
POST /admin/services/{name}/stop     # Stop service
POST /admin/services/{name}/restart  # Restart service
GET  /admin/logs/{logfile}           # Read log file
GET  /admin/logs/stream/{logfile}    # SSE log stream

# LLM
GET  /admin/llm/backend              # Current backend
POST /admin/llm/backend              # Set backend
GET  /admin/llm/persona              # Current persona
POST /admin/llm/persona              # Set persona
GET  /admin/llm/params               # Generation params
POST /admin/llm/params               # Update params
GET  /admin/llm/prompt/{persona}     # System prompt
POST /admin/llm/prompt/{persona}     # Update prompt

# TTS
GET  /admin/voices                   # List voices
POST /admin/voice                    # Set voice
POST /admin/voice/test               # Test synthesis
GET  /admin/tts/xtts/params          # XTTS params
POST /admin/tts/xtts/params          # Update XTTS params
GET  /admin/tts/presets/custom       # Custom presets
POST /admin/tts/presets/custom       # Create preset

# FAQ
GET    /admin/faq                    # List all FAQ
POST   /admin/faq                    # Add FAQ entry
PUT    /admin/faq/{trigger}          # Update entry
DELETE /admin/faq/{trigger}          # Delete entry
POST   /admin/faq/reload             # Hot reload
POST   /admin/faq/test               # Test matching

# Fine-tuning
POST /admin/finetune/dataset/upload  # Upload Telegram export
POST /admin/finetune/dataset/process # Run prepare_telegram.py
GET  /admin/finetune/dataset/stats   # Dataset statistics
GET  /admin/finetune/config          # Training config
POST /admin/finetune/config          # Update config
POST /admin/finetune/train/start     # Start training
POST /admin/finetune/train/stop      # Stop training
GET  /admin/finetune/train/status    # Training progress
GET  /admin/finetune/adapters        # List LoRA adapters
POST /admin/finetune/adapters/activate # Hot-swap adapter

# Monitoring
GET  /admin/monitor/gpu              # GPU stats
GET  /admin/monitor/gpu/stream       # SSE GPU stream
GET  /admin/monitor/health           # Health check
GET  /admin/monitor/metrics          # Request metrics
```

## Fine-tuning Pipeline

Полный цикл обучения LoRA адаптера:

```bash
# 1. Export Telegram chat (JSON)
# 2. Upload via Admin Panel → Finetune → Upload Dataset

# Or via API:
curl -X POST http://localhost:8002/admin/finetune/dataset/upload \
  -F "file=@result.json"

# 3. Process dataset
curl -X POST http://localhost:8002/admin/finetune/dataset/process

# 4. View statistics
curl http://localhost:8002/admin/finetune/dataset/stats

# 5. Configure training
curl -X POST http://localhost:8002/admin/finetune/config \
  -H "Content-Type: application/json" \
  -d '{
    "lora_rank": 8,
    "batch_size": 1,
    "gradient_accumulation": 64,
    "learning_rate": 2e-4,
    "epochs": 1
  }'

# 6. Start training
curl -X POST http://localhost:8002/admin/finetune/train/start

# 7. Monitor progress
curl http://localhost:8002/admin/finetune/train/status

# 8. Activate new adapter (hot-swap)
curl -X POST http://localhost:8002/admin/finetune/adapters/activate \
  -H "Content-Type: application/json" \
  -d '{"adapter": "qwen2.5-7b-lydia-lora-new"}'
```

## OpenWebUI Integration

```yaml
# Settings → Connections → OpenAI API
API Base URL: http://172.17.0.1:8002/v1
API Key: sk-dummy

# Settings → Audio → TTS
TTS Engine: OpenAI
API Base URL: http://172.17.0.1:8002/v1
TTS Voice: gulya
```

**Available Models:**
- `gulya-secretary-qwen` - Гуля + Qwen2.5-7B + LoRA
- `lidia-secretary-qwen` - Лидия + Qwen2.5-7B + LoRA
- `gulya-secretary-llama` - Гуля + Llama-3.1-8B
- `gulya-secretary-gemini` - Гуля + Gemini API

## Environment Variables

```bash
# Required
LLM_BACKEND=vllm                    # "vllm" or "gemini"

# vLLM configuration
VLLM_API_URL=http://localhost:11434
VLLM_MODEL_NAME=lydia               # LoRA adapter name

# Optional
SECRETARY_PERSONA=gulya             # "gulya" or "lidia"
GEMINI_API_KEY=...                  # Only for gemini backend
ORCHESTRATOR_PORT=8002
CUDA_VISIBLE_DEVICES=1              # GPU index
```

## File Structure

```
AI_Secretary_System/
├── orchestrator.py          # FastAPI server + 45 admin endpoints
├── service_manager.py       # Service process control
├── finetune_manager.py      # Fine-tuning pipeline
├── voice_clone_service.py   # XTTS v2 + custom presets
├── openvoice_service.py     # OpenVoice v2
├── piper_tts_service.py     # Piper TTS (CPU)
├── vllm_llm_service.py      # vLLM + runtime params
├── llm_service.py           # Gemini fallback
├── typical_responses.json   # FAQ database
├── custom_presets.json      # TTS custom presets
├── admin/                   # Vue 3 admin panel
│   ├── src/
│   │   ├── views/          # 7 main views
│   │   ├── api/            # API clients
│   │   ├── stores/         # Pinia stores
│   │   └── composables/    # SSE, GPU stats
│   └── dist/               # Production build
├── Гуля/                    # Voice samples (122 WAV)
├── Лидия/                   # Voice samples
├── models/                  # Piper ONNX models
├── logs/                    # Service logs
├── start_gpu.sh             # Launch GPU mode
├── start_cpu.sh             # Launch CPU mode
└── setup.sh                 # First-time setup
```

## Commands

```bash
# GPU Mode: XTTS + Qwen + LoRA (default)
./start_gpu.sh

# GPU Mode: XTTS + Llama
./start_gpu.sh --llama

# CPU Mode: Piper + Gemini
./start_cpu.sh

# OpenVoice Mode (older GPUs)
./start_openvoice.sh

# Start only vLLM
./start_qwen.sh   # Qwen + LoRA
./start_vllm.sh   # Llama

# Admin Panel (dev mode)
cd admin && npm run dev

# View logs
tail -f logs/orchestrator.log
tail -f logs/vllm.log
```

## Requirements

### Hardware
- **GPU**: NVIDIA RTX 3060+ (12GB VRAM) for full mode
- **GPU (OpenVoice)**: NVIDIA CC 6.1+ (P104-100, GTX 1080)
- **CPU**: 8+ cores for Piper-only mode
- **RAM**: 16GB+ (32GB recommended)
- **Disk**: 20GB for models

### Software
- Ubuntu 20.04+ / Debian 11+
- Python 3.11+
- Node.js 18+ (for admin panel dev)
- CUDA 12.x
- ffmpeg

## Troubleshooting

### CUDA out of memory
```bash
# Reduce vLLM GPU allocation in start_qwen.sh:
--gpu-memory-utilization 0.6  # Instead of 0.7
```

### Voice quality issues
- Add more WAV samples to voice folder
- Use clean recordings without background noise
- Ensure 16kHz or 44.1kHz sample rate

### Admin panel not loading
```bash
# Check if backend is running
curl http://localhost:8002/health

# Rebuild admin panel
cd admin && npm run build

# Check nginx/proxy configuration
```

### vLLM connection refused
```bash
# Check vLLM is running
curl http://localhost:11434/health

# View vLLM logs
tail -f logs/vllm.log
```

## Development

### Running Tests
```bash
# Backend
./venv/bin/pytest tests/

# Frontend
cd admin && npm test
```

### Building Admin Panel
```bash
cd admin
npm install
npm run build
# Output in admin/dist/, served by FastAPI
```

### Adding New Voice
1. Create folder with WAV samples: `./NewVoice/`
2. Add service instance in `orchestrator.py`
3. Add voice ID to admin endpoints
4. Voice appears in admin panel

### Adding New Persona
1. Edit `SECRETARY_PERSONAS` in `vllm_llm_service.py`
2. Restart orchestrator
3. Available via API and admin panel

## License

MIT

## Support

Issues: https://github.com/ShaerWare/AI_Secretary_System/issues
