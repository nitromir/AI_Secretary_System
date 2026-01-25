# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System - virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama), and Gemini fallback. Features a Vue 3 PWA admin panel with 8 tabs, i18n, themes, and ~45 API endpoints.

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

**GPU Mode (Single GPU - RTX 3060 12GB):**
- vLLM Qwen2.5-7B + Lydia LoRA: ~8.4GB (70% GPU, port 11434)
- XTTS v2 voice cloning: ~3.6GB (remaining)

**Request flow:**
1. User message → FAQ check (instant) OR vLLM/Gemini LLM
2. Response text → TTS (XTTS/Piper based on `current_voice_config`)
3. Audio returned to user

## Commands

```bash
# Start system
./start_gpu.sh              # GPU: XTTS + Qwen2.5-7B + LoRA (recommended)
./start_gpu.sh --llama      # GPU: XTTS + Llama-3.1-8B
./start_cpu.sh              # CPU: Piper + Gemini API
./start_qwen.sh             # Start only vLLM (debugging)

# Health check
curl http://localhost:8002/health

# Admin Panel (dev)
cd admin && npm install && npm run dev   # http://localhost:5173
# Login: admin / admin

# Admin Panel (production)
# http://localhost:8002/admin (served by FastAPI)

# Build admin panel
cd admin && npm run build

# Lint admin panel
cd admin && npm run lint

# View logs
tail -f logs/orchestrator.log
tail -f logs/vllm.log

# System test (requires running system)
./test_system.sh
```

## Key Components

### Backend Services (Python)

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, ~45 admin endpoints, serves admin panel |
| `auth_manager.py` | JWT authentication for admin panel |
| `service_manager.py` | External service process control (vLLM) |
| `finetune_manager.py` | LoRA training pipeline |
| `voice_clone_service.py` | XTTS v2 with custom presets |
| `openvoice_service.py` | OpenVoice v2 (older GPUs) |
| `piper_tts_service.py` | Piper ONNX CPU TTS |
| `vllm_llm_service.py` | vLLM API with runtime params |
| `llm_service.py` | Gemini API fallback |

### Admin Panel (Vue 3)

8 tabs: Dashboard, Services, LLM, TTS, FAQ, Finetune, Monitoring, Settings

| Directory | Purpose |
|-----------|---------|
| `admin/src/views/` | 8 main views (one per tab) |
| `admin/src/api/` | API clients + SSE helpers |
| `admin/src/stores/` | Pinia stores (auth, theme, toast, audit, services, llm) |
| `admin/src/composables/` | useSSE, useRealtimeMetrics, useExportImport |
| `admin/src/plugins/i18n.ts` | vue-i18n (ru/en translations) |
| `admin/src/components/charts/` | Chart.js sparklines |

### Data Files

| File | Purpose |
|------|---------|
| `typical_responses.json` | FAQ database (hot-reloadable) |
| `custom_presets.json` | TTS custom presets |
| `./Гуля/`, `./Лидия/` | Voice sample WAV files |

## API Quick Reference

**OpenAI-compatible (for OpenWebUI):**
- `POST /v1/chat/completions` — Chat with streaming
- `POST /v1/audio/speech` — TTS with current voice
- `GET /v1/models` — Available models

**Admin API (JWT required):**
- `POST /admin/auth/login` — Get JWT token
- `GET/POST /admin/services/*` — Service control
- `GET/POST /admin/llm/*` — Backend, persona, params
- `GET/POST /admin/voices`, `/admin/voice`, `/admin/tts/*` — TTS config
- `GET/POST/PUT/DELETE /admin/faq/*` — FAQ CRUD
- `POST /admin/finetune/*` — Training pipeline
- `GET /admin/monitor/*` — GPU stats, health, metrics (SSE available)

## Environment Variables

```bash
LLM_BACKEND=vllm                    # "vllm" or "gemini"
VLLM_API_URL=http://localhost:11434
VLLM_MODEL_NAME=lydia               # LoRA adapter name
SECRETARY_PERSONA=gulya             # "gulya" or "lidia"
GEMINI_API_KEY=...                  # Only for gemini backend
ORCHESTRATOR_PORT=8002
CUDA_VISIBLE_DEVICES=1
ADMIN_JWT_SECRET=...                # Auto-generated if empty
```

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

## Known Issues

1. **STT disabled** — faster-whisper hangs; use text chat only
2. **XTTS requires CC >= 7.0** — RTX 3060 or newer
3. **GPU memory sharing** — vLLM 70% (~8.4GB), XTTS ~3.6GB
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost`
