# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System - virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama/DeepSeek), and Gemini fallback. Features a Vue 3 PWA admin panel with 13 tabs, i18n (ru/en), themes, ~80 API endpoints, website chat widget, and Telegram bot integration.

## Architecture

```
                              ┌──────────────────────────────────────────┐
                              │        Orchestrator (port 8002)          │
                              │           orchestrator.py                │
                              │                                          │
                              │  ┌────────────────────────────────────┐  │
                              │  │  Vue 3 Admin Panel (13 tabs, PWA)  │  │
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

**Request flow:**
1. User message → FAQ check (instant) OR vLLM/Gemini LLM
2. Response text → TTS (XTTS/Piper based on `current_voice_config`)
3. Audio returned to user

## Commands

```bash
# Start system
./start_gpu.sh              # GPU: XTTS + Qwen2.5-7B + LoRA (recommended)
./start_gpu.sh --llama      # GPU: XTTS + Llama-3.1-8B
./start_gpu.sh --deepseek   # GPU: XTTS + DeepSeek-LLM-7B
./start_cpu.sh              # CPU: Piper + Gemini API
./start_qwen.sh             # Start only vLLM (debugging)

# Health check
curl http://localhost:8002/health

# System integration test (requires running system)
./test_system.sh

# View logs
tail -f logs/orchestrator.log
tail -f logs/vllm.log
```

### Admin Panel

**Single entry point:** http://localhost:8002/admin/ (login: admin / admin)

```bash
# First-time setup
cd admin && npm install     # Install dependencies once

# Production mode (default) - serve built Vue app
cd admin && npm run build   # Build once
./start_gpu.sh              # Start orchestrator

# Development mode - hot reload via Vite proxy
cd admin && npm run dev     # Start Vite at :5173
DEV_MODE=1 ./start_gpu.sh   # Orchestrator proxies /admin to Vite

# Always access via: http://localhost:8002/admin/
# (DEV_MODE proxies static files to Vite for hot reload)

# Lint
cd admin && npm run lint
```

### External Access (ngrok/Cloudflare Tunnel)

For website widget and Telegram bot to work with external services, you need to expose the local server:

```bash
# Option 1: ngrok (recommended for development)
# Install: https://ngrok.com/download
ngrok http 8002

# Option 2: Cloudflare Tunnel (recommended for production)
# Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
cloudflared tunnel --url http://localhost:8002

# Option 3: Helper script (auto-detects available tool)
./start_with_tunnel.sh
```

After starting tunnel, use the generated HTTPS URL in:
- Widget settings (Admin → Widget → API URL)
- Telegram webhook will be set automatically when bot starts

### Telegram Bot

```bash
# Start Telegram bot (requires orchestrator running)
./start_telegram_bot.sh

# Or via admin panel: Admin → Telegram → Start Bot
```

**Setup:**
1. Create bot via [@BotFather](https://t.me/BotFather), get token
2. Add token in Admin → Telegram → Bot Token
3. Configure allowed users (optional whitelist)
4. Start bot

### Fine-tuning (separate venv)

```bash
cd finetune
source /home/shaerware/qwen-finetune/train_venv/bin/activate

python prepare_dataset.py   # Convert Telegram export to JSONL
python train.py             # Train LoRA adapters
python merge_lora.py        # Merge LoRA with base (needs ~30GB RAM)

# For quantization (different venv)
source /home/shaerware/qwen-finetune/quant_venv/bin/activate
python quantize_awq.py      # W4A16 quantization
```

## Key Components

### Backend (Python)

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, ~90 endpoints, serves admin panel |
| `cloud_llm_service.py` | Cloud LLM factory (Gemini, Kimi, OpenAI, Claude, DeepSeek) |
| `auth_manager.py` | JWT authentication |
| `service_manager.py` | Process control (vLLM) |
| `finetune_manager.py` | LoRA training pipeline |
| `voice_clone_service.py` | XTTS v2 with custom presets |
| `openvoice_service.py` | OpenVoice v2 (older GPUs) |
| `piper_tts_service.py` | Piper ONNX CPU TTS |
| `stt_service.py` | Vosk (realtime) + Whisper (batch) STT |
| `vllm_llm_service.py` | vLLM API + `SECRETARY_PERSONAS` dict |
| `llm_service.py` | Gemini API fallback |
| `telegram_bot_service.py` | Async Telegram bot (python-telegram-bot) |

### Admin Panel (Vue 3)

**Tabs:** Dashboard, Chat, Services, LLM, TTS, FAQ, Finetune, Monitoring, Models, Widget, Telegram, Audit, Settings

| Directory | Purpose |
|-----------|---------|
| `admin/src/views/` | 13 main views + LoginView |
| `admin/src/api/` | API clients + SSE helpers |
| `admin/src/stores/` | Pinia stores (auth, theme, toast, audit, services, llm) |
| `admin/src/composables/` | useSSE, useRealtimeMetrics, useExportImport |
| `admin/src/plugins/i18n.ts` | vue-i18n translations (ru/en) |

**Chat features:**
- Streaming LLM responses (SSE)
- Message edit/regenerate/delete
- Custom system prompts per session
- TTS playback for assistant messages (Volume2 button on hover)
- Voice mode toggle (auto-play TTS on response)
- Voice input via microphone (STT transcription)
- Default prompt editing from chat settings

### Data Files

| File | Purpose |
|------|---------|
| `data/secretary.db` | SQLite database (primary storage) |
| `typical_responses.json` | FAQ (legacy, synced from DB) |
| `custom_presets.json` | TTS presets (legacy, synced from DB) |
| `chat_sessions.json` | Chat history (legacy, synced from DB) |
| `widget_config.json` | Widget settings (legacy, synced from DB) |
| `telegram_config.json` | Telegram settings (legacy, synced from DB) |
| `./Гуля/`, `./Лидия/` | Voice sample WAV files |
| `web-widget/` | Embeddable chat widget source |
| `finetune/datasets/` | Training data symlinks (not in git) |
| `finetune/adapters/` | LoRA model symlinks (not in git) |

### Database (SQLite + Redis)

**SQLite tables:**
| Table | Purpose |
|-------|---------|
| `chat_sessions` | Chat session metadata |
| `chat_messages` | Individual chat messages |
| `faq_entries` | FAQ question-answer pairs |
| `tts_presets` | Custom TTS voice presets |
| `system_config` | Key-value system config (telegram, widget, etc.) |
| `telegram_sessions` | Telegram user → chat session mapping |
| `audit_log` | System audit trail |
| `cloud_llm_providers` | Cloud LLM provider credentials (API keys, URLs) |

**Redis keys (optional, for caching):**
| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `chat:session:{id}` | Cached chat sessions | 5 min |
| `faq:cache` | FAQ question→answer dict | 10 min |
| `config:{key}` | System config cache | 5 min |
| `ratelimit:{ip}:{endpoint}` | Rate limiting | 1 min |

**Migration from JSON:**
```bash
# First time setup - migrate existing JSON data to SQLite
python scripts/migrate_json_to_db.py
```

**Database location:** `data/secretary.db`

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
REDIS_URL=redis://localhost:6379/0  # Optional, for caching
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

**Adding a new cloud LLM provider type:**
1. Add entry to `PROVIDER_TYPES` dict in `db/models.py`
2. If OpenAI-compatible, `OpenAICompatibleProvider` in `cloud_llm_service.py` handles it
3. For custom SDK, create new provider class inheriting `BaseLLMProvider`
4. Register in `CloudLLMService.PROVIDER_CLASSES`

## API Quick Reference

**OpenAI-compatible (for OpenWebUI):**
- `POST /v1/chat/completions` — Chat with streaming
- `POST /v1/audio/speech` — TTS with current voice
- `GET /v1/models` — Available models

**Admin Chat API:**
- `GET/POST /admin/chat/sessions` — List/create sessions
- `GET/PUT/DELETE /admin/chat/sessions/{id}` — Session CRUD
- `POST /admin/chat/sessions/{id}/stream` — SSE streaming chat
- `POST /admin/chat/sessions/{id}/messages/{msg_id}/regenerate` — Regenerate response

**Admin API (JWT required):**
- `POST /admin/auth/login` — Get JWT token
- `GET/POST /admin/services/*` — Service control
- `GET/POST /admin/llm/*` — Backend, persona, params
- `GET/POST/PUT/DELETE /admin/llm/providers/*` — Cloud LLM providers CRUD
- `GET/POST /admin/tts/*` — TTS config, test playback
- `GET/POST /admin/stt/*` — STT status, transcribe, test
- `GET/POST/PUT/DELETE /admin/faq/*` — FAQ CRUD
- `POST /admin/finetune/*` — Training pipeline
- `GET /admin/monitor/*` — GPU stats, SSE metrics
- `GET/POST /admin/widget/*` — Widget config, generate code
- `GET/POST /admin/telegram/*` — Telegram bot config, start/stop
- `GET /admin/audit/*` — Audit log viewing, filtering, export
- `GET /widget.js` — Dynamic widget script (public)

## Known Issues

1. **Vosk model required** — Download `vosk-model-ru-0.42` (~1.5GB) to `models/vosk/` for STT:
   ```bash
   mkdir -p models/vosk && cd models/vosk
   wget https://alphacephei.com/vosk/models/vosk-model-ru-0.42.zip && unzip vosk-model-ru-0.42.zip
   ```
2. **XTTS requires CC >= 7.0** — RTX 3060 or newer; use OpenVoice for older GPUs (CC >= 6.1)
3. **GPU memory sharing** — vLLM 50% (~6GB) + XTTS ~5GB on 12GB GPU
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost` for API URL
5. **Model quality** — Lydia LoRA may produce repetitive responses; adjust `repetition_penalty` in LLM tab

## Roadmap & Backlog

См. [BACKLOG.md](./BACKLOG.md) для полного плана разработки.

**Текущий фокус:** Офлайн-first + телефония через SIM7600G-H Waveshare

**Выполнено:**
- ✅ Local STT (Vosk) — VoskSTTService + UnifiedSTTService для realtime распознавания
- ✅ Chat TTS playback — озвучивание ответов ассистента
- ✅ Website Widget — встраиваемый чат-виджет для сайтов (web-widget/)
- ✅ Telegram Bot — интеграция с Telegram (telegram_bot_service.py)
- ✅ Database Integration — SQLite + Redis для надёжного хранения (db/)
- ✅ Hot-switching LLM — переключение vLLM/Gemini без перезапуска
- ✅ Audit Log UI — просмотр и фильтрация логов действий (AuditView.vue)
- ✅ Voice Mode — auto-play TTS при получении ответа
- ✅ Voice Input (STT) — голосовой ввод через микрофон в чате
- ✅ Prompt Editor — редактирование дефолтного промпта из чата
- ✅ DeepSeek LLM — третья модель (./start_gpu.sh --deepseek)
- ✅ LLM Models UI — отображение доступных моделей в админке
- ✅ Cloud LLM Providers — подключение облачных LLM (Gemini, Kimi, OpenAI, Claude, DeepSeek)

**Ближайшие задачи (Фаза 1):**
1. Telephony Gateway — интеграция с SIM7600 (AT-команды)
2. Backup & Restore — полный бэкап системы
3. Docker Compose — one-command deployment
4. Legacy JSON Removal — полная миграция на SQLite

**Hardware:** Raspberry Pi + SIM7600G-H для GSM-телефонии
