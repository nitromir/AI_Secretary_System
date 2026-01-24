# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System - virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama), and Gemini fallback. Features a full Vue 3 PWA admin panel with 8 tabs, i18n, themes, and ~45 API endpoints.

## Architecture

```
                              ┌──────────────────────────────────────────┐
                              │        Orchestrator (port 8002)          │
                              │           orchestrator.py                │
                              │                                          │
                              │  ┌────────────────────────────────────┐  │
                              │  │   Vue 3 Admin Panel (8 tabs, PWA)  │  │
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
# Login: admin / admin

# Admin Panel (production)
# http://localhost:8002/admin (served by FastAPI)

# Build admin panel
cd admin && npm run build

# View logs
tail -f logs/orchestrator.log
tail -f logs/vllm.log
```

## Admin Panel

Vue 3 PWA admin panel with 8 tabs:

| Tab | View File | Description |
|-----|-----------|-------------|
| Dashboard | `DashboardView.vue` | Service status, GPU sparklines, health |
| Services | `ServicesView.vue` | Start/stop vLLM, SSE log viewer |
| LLM | `LlmView.vue` | Backend toggle, persona, params |
| TTS | `TtsView.vue` | Voice selection, presets, test |
| FAQ | `FaqView.vue` | FAQ CRUD editor |
| Finetune | `FinetuneView.vue` | Training pipeline, adapters |
| Monitoring | `MonitoringView.vue` | GPU/CPU charts, errors |
| Settings | `SettingsView.vue` | Language, theme, export/import, audit |

### Admin Panel Features

| Feature | Files | Description |
|---------|-------|-------------|
| **JWT Auth** | `stores/auth.ts`, `auth_manager.py` | Login with dev fallback |
| **Multi-user Roles** | `stores/auth.ts` | admin, operator, viewer |
| **i18n (ru/en)** | `plugins/i18n.ts` | Full translations |
| **Themes** | `stores/theme.ts`, `main.css` | Light, Dark, Night-Eyes |
| **PWA** | `manifest.json`, `sw.js` | Installable, offline |
| **Real-time** | `composables/useRealtimeMetrics.ts` | SSE + polling fallback |
| **Charts** | `components/charts/*.vue` | Chart.js sparklines |
| **Search** | `stores/search.ts`, `SearchPalette.vue` | ⌘K command palette |
| **Audit Log** | `stores/audit.ts` | User action logging |
| **Export/Import** | `composables/useExportImport.ts` | Config backup |
| **Responsive** | `App.vue` | Mobile sidebar overlay |
| **Toasts** | `stores/toast.ts` | Notifications |
| **Confirm** | `stores/confirm.ts` | Danger dialogs |

### Admin Tech Stack

- Vue 3 + Composition API + TypeScript
- Vite (build)
- Tailwind CSS (4 themes)
- Pinia + persistedstate
- TanStack Query (caching)
- Chart.js + vue-chartjs
- vue-i18n (ru/en)
- Lucide icons

### Dev Mode Login

```
Username: admin
Password: admin
```

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

### Auth Manager (`auth_manager.py`)
JWT authentication for admin panel.

```python
JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", secrets.token_hex(32))

def create_access_token(username: str, role: str = "admin") -> tuple[str, int]
def authenticate_user(username: str, password: str) -> Optional[User]
async def get_current_user(credentials) -> Optional[User]
```

### Multi-Voice TTS System
Five voices available:

| Voice | Engine | GPU | Speed | Quality |
|-------|--------|-----|-------|---------|
| gulya | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning |
| lidia | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning |
| lidia_openvoice | OpenVoice v2 | CC >= 6.1 | ~2-4s | Good cloning |
| dmitri | Piper | CPU | ~0.5s | Pre-trained |
| irina | Piper | CPU | ~0.5s | Pre-trained |

### Secretary Personas

| Persona | Name | Description |
|---------|------|-------------|
| gulya | Гуля (Гульнара) | Default persona |
| lidia | Лидия | Alternative persona |

### LLM Backend Selection
- `vllm` — Local LLM via vLLM (default)
- `gemini` — Google Gemini API (fallback)

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
# Auth
POST /admin/auth/login

# Services
GET  /admin/services/status
POST /admin/services/{service}/start
POST /admin/services/{service}/stop
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

# FAQ
GET    /admin/faq
POST   /admin/faq
PUT    /admin/faq/{trigger}
DELETE /admin/faq/{trigger}
POST   /admin/faq/reload

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

# Monitoring
GET  /admin/monitor/gpu
GET  /admin/monitor/gpu/stream  # SSE
GET  /admin/monitor/health
GET  /admin/monitor/metrics
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
ADMIN_JWT_SECRET=...                # Auto-generated if empty
```

## Key Files

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, ~45 admin endpoints |
| `auth_manager.py` | JWT authentication |
| `service_manager.py` | Service process control |
| `finetune_manager.py` | Training pipeline |
| `voice_clone_service.py` | XTTS v2, custom presets |
| `openvoice_service.py` | OpenVoice v2 |
| `piper_tts_service.py` | Piper ONNX (CPU) |
| `vllm_llm_service.py` | vLLM API, runtime params |
| `llm_service.py` | Gemini API fallback |
| `typical_responses.json` | FAQ data |
| `custom_presets.json` | TTS custom presets |

### Admin Panel Structure

```
admin/
├── src/
│   ├── main.ts              # App entry + plugins (i18n, pinia persist)
│   ├── App.vue              # Main layout, responsive sidebar
│   ├── router.ts            # Vue Router + auth guard
│   │
│   ├── api/
│   │   ├── client.ts        # Base fetch, generic SSE
│   │   ├── services.ts
│   │   ├── llm.ts
│   │   ├── tts.ts
│   │   ├── faq.ts
│   │   ├── finetune.ts
│   │   └── monitor.ts
│   │
│   ├── stores/
│   │   ├── auth.ts          # JWT + roles (admin/operator/viewer)
│   │   ├── theme.ts         # 4 themes (light/dark/night-eyes/system)
│   │   ├── toast.ts         # Notifications
│   │   ├── confirm.ts       # Confirmation dialogs
│   │   ├── search.ts        # Command palette
│   │   ├── audit.ts         # Action logging
│   │   ├── services.ts
│   │   └── llm.ts
│   │
│   ├── composables/
│   │   ├── useSSE.ts        # Generic SSE connection
│   │   ├── useRealtimeMetrics.ts  # GPU stats with fallback
│   │   └── useExportImport.ts     # Config backup
│   │
│   ├── plugins/
│   │   └── i18n.ts          # vue-i18n (ru/en)
│   │
│   ├── components/
│   │   ├── charts/          # SparklineChart, GpuChart, MetricsChart
│   │   ├── ToastContainer.vue
│   │   ├── ConfirmDialog.vue
│   │   ├── SearchPalette.vue
│   │   ├── ThemeToggle.vue
│   │   └── ErrorBoundary.vue
│   │
│   ├── views/
│   │   ├── DashboardView.vue
│   │   ├── ServicesView.vue
│   │   ├── LlmView.vue
│   │   ├── TtsView.vue
│   │   ├── FaqView.vue
│   │   ├── FinetuneView.vue
│   │   ├── MonitoringView.vue
│   │   ├── SettingsView.vue
│   │   └── LoginView.vue
│   │
│   └── assets/
│       └── main.css         # Tailwind + 4 themes
│
├── public/
│   ├── manifest.json        # PWA manifest
│   └── sw.js               # Service Worker
│
├── docs/
│   └── ADMIN_PANEL_SESSION_LOG.md  # Implementation history
│
├── index.html               # PWA meta tags
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

## Known Issues

1. **STT disabled** — faster-whisper hangs; use text chat only
2. **XTTS requires CC >= 7.0** — RTX 3060 or newer
3. **GPU memory sharing** — vLLM 70% (~8.4GB), XTTS ~3.6GB
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

**Adding a new theme:**
1. Add CSS variables in `admin/src/assets/main.css`
2. Update `Theme` type in `admin/src/stores/theme.ts`
3. Add translations in `admin/src/plugins/i18n.ts`

**Adding i18n translations:**
1. Edit `admin/src/plugins/i18n.ts`
2. Add keys to both `ru` and `en` message objects
3. Use in templates: `{{ t('key.path') }}`

**Adding new role permission:**
1. Add permission to `ROLE_PERMISSIONS` in `admin/src/stores/auth.ts`
2. Check with `authStore.hasPermission('resource.action')`

## Session Log

For detailed implementation history, see:
- `admin/docs/ADMIN_PANEL_SESSION_LOG.md` - Admin panel implementation details
