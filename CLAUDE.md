# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System - virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama), and Gemini fallback. Features a full Vue 3 admin panel with 7 tabs and ~45 API endpoints.

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

**GPU Mode (Single GPU - RTX 3060):**
```
RTX 3060 (12GB, CC 8.6):
  - vLLM Qwen2.5-7B + Lydia LoRA (default, 70% GPU = ~8.4GB, port 11434)
  - XTTS v2 voice cloning (remaining ~3.6GB)
```

**Request flow:**
1. User message → FAQ check (instant) OR vLLM/Gemini LLM
2. Response text → TTS (XTTS/Piper based on `current_voice_config`)
3. Audio returned to user

## Commands

```bash
# GPU Mode: XTTS + Qwen2.5-7B + Lydia LoRA (recommended)
./start_gpu.sh

# GPU Mode with Llama (fallback)
./start_gpu.sh --llama

# CPU-only mode (Piper TTS + Gemini API)
./start_cpu.sh

# Start Qwen vLLM separately (for debugging)
./start_qwen.sh

# Health check
curl http://localhost:8002/health

# Admin Panel (dev mode)
cd admin && npm install && npm run dev
# Open http://localhost:5173

# Admin Panel (production)
# http://localhost:8002/admin (served by FastAPI)

# Build admin panel
cd admin && npm run build

# View logs
tail -f logs/orchestrator.log
tail -f logs/vllm.log
```

## Admin Panel

Vue 3 admin panel with 7 tabs:

| Tab | View File | Description |
|-----|-----------|-------------|
| Dashboard | `DashboardView.vue` | Service status, GPU metrics, health |
| Services | `ServicesView.vue` | Start/stop vLLM, log viewer |
| LLM | `LlmView.vue` | Backend toggle, persona, params |
| TTS | `TtsView.vue` | Voice selection, presets, params |
| FAQ | `FaqView.vue` | FAQ CRUD editor |
| Finetune | `FinetuneView.vue` | Training pipeline, adapters |
| Monitoring | `MonitoringView.vue` | GPU/CPU charts, errors |

**Admin Tech Stack:**
- Vue 3 + Composition API + TypeScript
- Vite (build)
- Tailwind CSS (dark theme)
- Pinia (state)
- TanStack Query (data fetching)
- SSE for real-time updates

## Key Components

### Service Manager (`service_manager.py`)
Controls external services (vLLM) and monitors internal services.

```python
class ServiceManager:
    SERVICES = {
        "vllm": {"start_script": "start_qwen.sh", "port": 11434, ...},
        "xtts_gulya": {"internal": True, "gpu_required": True},
        "xtts_lidia": {"internal": True, "gpu_required": True},
        "piper": {"internal": True, "cpu_only": True},
        "openvoice": {"internal": True, "gpu_required": True}
    }

    async def start_service(name) -> dict
    async def stop_service(name) -> dict
    def get_all_status() -> dict
    def read_log(service, lines=100) -> dict
    async def stream_log(service) -> AsyncGenerator  # SSE
```

### Finetune Manager (`finetune_manager.py`)
Full fine-tuning pipeline: dataset → training → adapters.

```python
@dataclass
class TrainingConfig:
    lora_rank: int = 8
    batch_size: int = 1
    gradient_accumulation: int = 64
    learning_rate: float = 2e-4
    epochs: int = 1

class FinetuneManager:
    # Dataset
    async def upload_dataset(content, filename) -> dict
    async def process_dataset() -> dict
    def get_dataset_stats() -> dict

    # Training
    async def start_training(config) -> dict
    async def stop_training() -> dict
    def get_training_status() -> TrainingStatus
    async def stream_training_log() -> AsyncGenerator  # SSE

    # Adapters
    def list_adapters() -> List[AdapterInfo]
    async def activate_adapter(name) -> dict  # hot-swap
    async def delete_adapter(name) -> dict
```

### Multi-Voice TTS System
Five voices available, switchable via admin panel or API:

| Voice | Engine | GPU | Speed | Quality | Default |
|-------|--------|-----|-------|---------|---------|
| gulya | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning | Yes |
| lidia | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning | |
| lidia_openvoice | OpenVoice v2 | CC >= 6.1 | ~2-4s | Good cloning | |
| dmitri | Piper | CPU | ~0.5s | Pre-trained male | |
| irina | Piper | CPU | ~0.5s | Pre-trained female | |

**Voice samples:**
- Гуля: `./Гуля/` (122 WAV files)
- Лидия: `./Лидия/` (WAV files)

**Voice switching:**
- Admin: http://localhost:8002/admin → TTS tab
- API: `POST /admin/voice {"voice": "gulya"}`
- Code: `current_voice_config` dict in `orchestrator.py`

### Secretary Personas
Two personas available:

| Persona | Name | Description |
|---------|------|-------------|
| gulya | Гуля (Гульнара) | Default persona |
| lidia | Лидия | Alternative persona |

**Persona switching:**
- Admin: http://localhost:8002/admin → LLM tab
- API: `POST /admin/llm/persona {"persona": "lidia"}`
- Env: `SECRETARY_PERSONA=gulya`
- Code: `SECRETARY_PERSONAS` dict in `vllm_llm_service.py`

### LLM Backend Selection
- `vllm` — Local LLM via vLLM (default)
- `gemini` — Google Gemini API (fallback)

**Switching:**
- Admin: http://localhost:8002/admin → LLM tab
- API: `POST /admin/llm/backend {"backend": "vllm"}`
- Env: `LLM_BACKEND=vllm`

### FAQ System (`typical_responses.json`)
Bypasses LLM for common questions. Hot-reloadable via admin panel.

Templates: `{current_time}`, `{current_date}`, `{day_of_week}`

## API Quick Reference

**OpenAI-compatible (for OpenWebUI):**
- `POST /v1/chat/completions` — Chat with streaming
- `POST /v1/audio/speech` — TTS with current voice
- `GET /v1/models` — Available models

**Admin API (~45 endpoints):**

```python
# Services
GET  /admin/services/status
POST /admin/services/{service}/start
POST /admin/services/{service}/stop
POST /admin/services/{service}/restart
GET  /admin/logs/{logfile}
GET  /admin/logs/stream/{logfile}  # SSE

# LLM
GET/POST /admin/llm/backend
GET/POST /admin/llm/persona
GET/POST /admin/llm/params
GET/POST /admin/llm/prompt/{persona}

# TTS
GET  /admin/voices
POST /admin/voice
POST /admin/voice/test
GET/POST /admin/tts/xtts/params
GET/POST /admin/tts/presets/custom
PUT/DELETE /admin/tts/presets/custom/{name}

# FAQ
GET    /admin/faq
POST   /admin/faq
PUT    /admin/faq/{trigger}
DELETE /admin/faq/{trigger}
POST   /admin/faq/reload
POST   /admin/faq/test

# Fine-tuning
POST /admin/finetune/dataset/upload
POST /admin/finetune/dataset/process
GET  /admin/finetune/dataset/stats
GET/POST /admin/finetune/config
POST /admin/finetune/train/start
POST /admin/finetune/train/stop
GET  /admin/finetune/train/status
GET  /admin/finetune/train/log  # SSE
GET  /admin/finetune/adapters
POST /admin/finetune/adapters/activate
DELETE /admin/finetune/adapters/{name}

# Monitoring
GET  /admin/monitor/gpu
GET  /admin/monitor/gpu/stream  # SSE
GET  /admin/monitor/health
GET  /admin/monitor/metrics
```

## OpenWebUI Integration

```
URL: http://172.17.0.1:8002/v1  (Docker bridge IP)
API Key: sk-dummy (any value)
TTS Voice: gulya (or lidia)
Model: gulya-secretary-qwen
```

## Environment Variables

```bash
LLM_BACKEND=vllm                    # "vllm" or "gemini"
VLLM_API_URL=http://localhost:11434
VLLM_MODEL_NAME=lydia
SECRETARY_PERSONA=gulya             # "gulya" or "lidia"
GEMINI_API_KEY=...                  # Only for gemini backend
ORCHESTRATOR_PORT=8002
CUDA_VISIBLE_DEVICES=1
```

## Key Files

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, ~45 admin endpoints |
| `service_manager.py` | Service process control, log streaming |
| `finetune_manager.py` | Training pipeline, adapter management |
| `voice_clone_service.py` | XTTS v2, custom presets |
| `openvoice_service.py` | OpenVoice v2 |
| `piper_tts_service.py` | Piper ONNX (CPU) |
| `vllm_llm_service.py` | vLLM API, runtime params |
| `llm_service.py` | Gemini API fallback |
| `typical_responses.json` | FAQ data |
| `custom_presets.json` | TTS custom presets |
| `admin/` | Vue 3 admin panel |
| `admin/src/views/` | 7 main view components |
| `admin/src/api/` | API client modules |
| `admin/src/stores/` | Pinia stores |

### Admin Panel Structure

```
admin/
├── src/
│   ├── main.ts              # App entry
│   ├── App.vue              # Main layout, tab navigation
│   ├── router.ts            # Vue Router
│   ├── api/
│   │   ├── client.ts        # Base fetch, SSE helper
│   │   ├── services.ts      # Services API
│   │   ├── llm.ts           # LLM API
│   │   ├── tts.ts           # TTS API
│   │   ├── faq.ts           # FAQ API
│   │   ├── finetune.ts      # Finetune API
│   │   └── monitor.ts       # Monitoring API
│   ├── stores/
│   │   ├── services.ts
│   │   ├── llm.ts
│   │   ├── tts.ts
│   │   └── settings.ts
│   ├── composables/
│   │   ├── useSSE.ts        # SSE connection
│   │   └── useGpuStats.ts   # GPU polling
│   └── views/
│       ├── DashboardView.vue
│       ├── ServicesView.vue
│       ├── LlmView.vue
│       ├── TtsView.vue
│       ├── FaqView.vue
│       ├── FinetuneView.vue
│       └── MonitoringView.vue
├── vite.config.ts           # Proxy to :8002
├── tailwind.config.js       # Dark theme
└── package.json
```

## Known Issues

1. **STT disabled** — faster-whisper hangs on load; use text chat only
2. **XTTS requires CC >= 7.0** — Use RTX 3060 or newer GPU
3. **GPU memory sharing** — vLLM uses 70% (~8.4GB), XTTS needs ~3.6GB
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost`

## Code Patterns

**Adding a new XTTS voice:**
1. Create folder with WAV samples: `./NewVoice/`
2. Add service instance in `orchestrator.py`
3. Add voice ID to admin endpoints
4. Voice appears in admin panel TTS tab

**Adding a new secretary persona:**
1. Add entry to `SECRETARY_PERSONAS` dict in `vllm_llm_service.py`
2. Persona available via API and admin panel

**Adding FAQ response:**
1. Via admin panel: FAQ tab → Add
2. Via API: `POST /admin/faq {"trigger": "...", "response": "..."}`
3. Via file: Edit `typical_responses.json`, call `POST /admin/faq/reload`

**Modifying LLM params at runtime:**
```python
# vllm_llm_service.py
llm_service.set_params(temperature=0.9, max_tokens=1024)
```

**Adding custom TTS preset:**
```python
# voice_clone_service.py
voice_service.save_custom_preset("my_preset", {
    "temperature": 0.65,
    "top_p": 0.85,
    "speed": 1.0
})
```

## Session Log

For detailed implementation history, see:
- `docs/ADMIN_PANEL_SESSION_LOG.md` - Admin panel implementation details
