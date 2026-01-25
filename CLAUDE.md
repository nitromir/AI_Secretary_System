# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System - virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama), and Gemini fallback. Features a **Vue 3 PWA admin panel with 9 tabs** (including built-in Chat), i18n, themes, and ~55 API endpoints.

## Architecture

```
                              ┌──────────────────────────────────────────┐
                              │        Orchestrator (port 8002)          │
                              │           orchestrator.py                │
                              │                                          │
                              │  ┌────────────────────────────────────┐  │
                              │  │   Vue 3 Admin Panel (9 tabs, PWA)  │  │
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
- vLLM Qwen2.5-7B + Lydia LoRA: ~6GB (50% GPU, port 11434)
- XTTS v2 voice cloning: ~5GB (remaining)

**Fine-tuned model:**
- LoRA adapter: `finetune/adapters/qwen2.5-7b-lydia-lora/` (symlink to `/home/shaerware/qwen-finetune/`)
- Base model: `Qwen/Qwen2.5-7B-Instruct-AWQ` (cached in ~/.cache/huggingface/)

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
| `orchestrator.py` | FastAPI server, ~55 admin endpoints, serves admin panel |
| `auth_manager.py` | JWT authentication for admin panel |
| `service_manager.py` | External service process control (vLLM) |
| `finetune_manager.py` | LoRA training pipeline |
| `voice_clone_service.py` | XTTS v2 with custom presets |
| `openvoice_service.py` | OpenVoice v2 (older GPUs) |
| `piper_tts_service.py` | Piper ONNX CPU TTS |
| `vllm_llm_service.py` | vLLM API with runtime params |
| `llm_service.py` | Gemini API fallback |

### Admin Panel (Vue 3)

**9 tabs:** Dashboard, **Chat**, Services, LLM, TTS, FAQ, Finetune, Monitoring, Settings

| Directory | Purpose |
|-----------|---------|
| `admin/src/views/` | 9 main views (one per tab) + LoginView |
| `admin/src/api/` | API clients (chat.ts, tts.ts, llm.ts, etc.) + SSE helpers |
| `admin/src/stores/` | Pinia stores (auth, theme, toast, audit, services, llm) |
| `admin/src/composables/` | useSSE, useRealtimeMetrics, useExportImport |
| `admin/src/plugins/i18n.ts` | vue-i18n (ru/en translations) |
| `admin/src/components/charts/` | Chart.js sparklines |

### Data Files

| File | Purpose |
|------|---------|
| `typical_responses.json` | FAQ database (hot-reloadable) |
| `custom_presets.json` | TTS custom presets |
| `chat_sessions.json` | Chat history storage |
| `./Гуля/`, `./Лидия/` | Voice sample WAV files |

### Fine-tuning (`finetune/`)

| File | Purpose |
|------|---------|
| `train.py` | LoRA fine-tuning script (Qwen2.5-7B) |
| `prepare_dataset.py` | Convert Telegram export to training format |
| `merge_lora.py` | Merge LoRA with base model |
| `quantize_awq.py` | W4A16 quantization |
| `datasets/` | Symlinks to training data (not in git) |
| `adapters/` | Symlinks to trained models (not in git) |

## API Quick Reference

**OpenAI-compatible (for OpenWebUI):**
- `POST /v1/chat/completions` — Chat with streaming
- `POST /v1/audio/speech` — TTS with current voice
- `GET /v1/models` — Available models

**Admin Chat API (~10 endpoints):**
- `GET /admin/chat/sessions` — List chat sessions
- `POST /admin/chat/sessions` — Create new session
- `GET /admin/chat/sessions/{id}` — Get session with messages
- `PUT /admin/chat/sessions/{id}` — Update title/system prompt
- `DELETE /admin/chat/sessions/{id}` — Delete session
- `POST /admin/chat/sessions/{id}/messages` — Send message (non-streaming)
- `POST /admin/chat/sessions/{id}/stream` — Send message (SSE streaming)
- `PUT /admin/chat/sessions/{id}/messages/{msg_id}` — Edit message & regenerate
- `DELETE /admin/chat/sessions/{id}/messages/{msg_id}` — Delete message
- `POST /admin/chat/sessions/{id}/messages/{msg_id}/regenerate` — Regenerate response

**Admin API (JWT required):**
- `POST /admin/auth/login` — Get JWT token
- `GET/POST /admin/services/*` — Service control
- `GET/POST /admin/llm/*` — Backend, persona, params
- `GET/POST /admin/voices`, `/admin/voice`, `/admin/tts/*` — TTS config
- `POST /admin/tts/test` — TTS test (returns audio file for browser playback)
- `GET/POST/PUT/DELETE /admin/faq/*` — FAQ CRUD
- `GET /admin/finetune/dataset/list` — List available datasets
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

## Recent Changes (Session 2026-01-25)

1. **Chat Tab Added** - Full-featured chat interface in admin panel:
   - Multiple chat sessions with history
   - Custom system prompt per chat
   - Edit user messages & regenerate responses
   - Streaming responses (SSE)
   - Sessions saved to `chat_sessions.json`

2. **TTS Test Playback** - Audio now plays in browser instead of saving to file

3. **Finetune Datasets List** - New endpoint and UI to list available datasets

4. **GPU Memory Optimization** - vLLM now uses 50% GPU (was 70%) to coexist with XTTS

## Known Issues

1. **STT disabled** — faster-whisper hangs; use text chat only
2. **XTTS requires CC >= 7.0** — RTX 3060 or newer
3. **GPU memory sharing** — vLLM 50% (~6GB), XTTS ~5GB on 12GB GPU
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost`
5. **Model quality** — Lydia LoRA may produce repetitive responses; adjust repetition_penalty
