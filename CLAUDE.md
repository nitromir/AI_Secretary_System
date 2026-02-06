# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System — virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama/DeepSeek), cloud LLM fallback (Gemini, Kimi, OpenAI, Claude, DeepSeek, OpenRouter), and Claude Code CLI bridge. Features GSM telephony (SIM7600E-H), Vue 3 PWA admin panel, i18n (ru/en), multi-instance Telegram bots with sales/payments, website chat widgets, and LoRA fine-tuning.

## Commands

### Build & Run

```bash
# Docker (recommended)
cp .env.docker.example .env && docker compose up -d          # GPU mode
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d  # CPU mode

# Local
./start_gpu.sh              # GPU: XTTS + Qwen2.5-7B + LoRA
./start_cpu.sh              # CPU: Piper + Gemini API
curl http://localhost:8002/health
```

### Admin Panel

```bash
cd admin && npm install     # First-time setup
cd admin && npm run build   # Production build (served at /admin/)
cd admin && npm run dev     # Dev server (:5173)
DEV_MODE=1 ./start_gpu.sh   # Backend proxies to Vite dev server
```

Default login: admin / admin

### Lint & Format

```bash
# Python (requires .venv with ruff installed)
ruff check .                # Lint (see pyproject.toml for full rule config)
ruff check . --fix          # Auto-fix
ruff format .               # Format

# Frontend
cd admin && npm run lint

# All pre-commit hooks
pre-commit run --all-files
```

### Testing

```bash
pytest tests/                          # All tests
pytest tests/unit/test_db.py -v        # Single file
pytest -k "test_chat" -v               # By name pattern
pytest -m "not slow" -v                # Exclude slow tests
pytest -m "not integration" -v         # Exclude integration (needs external services)
pytest -m "not gpu" -v                 # Exclude GPU-required tests
cd admin && npm test                   # Frontend tests
```

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main`/`develop` and on PRs:
- `lint-backend` — ruff check + format check + mypy
- `lint-frontend` — npm ci + eslint + build (includes type check)
- `security` — Trivy vulnerability scanner

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Orchestrator (port 8002)                     │
│  orchestrator.py + app/routers/ (18 routers, ~236 endpoints) │
│  ┌────────────────────────────────────────────────────────┐  │
│  │        Vue 3 Admin Panel (19 views, PWA)                │  │
│  │                admin/dist/                              │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────┬──────────────┬──────────────┬───────────────────┘
             │              │              │
     ┌───────┴──┐    ┌──────┴───┐   ┌─────┴─────┐
     │ LLM      │    │ TTS      │   │ STT       │
     │ vLLM /   │    │ XTTS v2 /│   │ Vosk /    │
     │ Cloud    │    │ Piper    │   │ Whisper   │
     └──────────┘    └──────────┘   └───────────┘
```

**GPU mode (RTX 3060 12GB):** vLLM ~6GB (50% GPU) + XTTS v2 ~5GB

**Request flow:** User message → FAQ check (instant match) OR LLM → TTS → Audio response

### Key Architectural Decisions

**Global state in orchestrator.py** (~3200 lines): This is the FastAPI entry point. It initializes all services as module-level globals, populates the `ServiceContainer`, and includes all routers. Legacy endpoints (OpenAI-compatible `/v1/*`) still live here alongside the modular router system.

**ServiceContainer (`app/dependencies.py`)**: Singleton holding references to all initialized services (TTS, LLM, STT). Routers get services via FastAPI `Depends`. Populated during app startup in `orchestrator.py`.

**Database layer** (`db/`): Async SQLAlchemy with aiosqlite. `db/database.py` creates the engine and `AsyncSessionLocal` factory. `db/integration.py` provides backward-compatible manager classes (e.g., `AsyncChatManager`, `AsyncFAQManager`) that wrap repository calls — these are used as module-level singletons imported by `orchestrator.py` and routers. Repositories in `db/repositories/` inherit from `BaseRepository` with generic CRUD.

**Telegram bots**: Run as subprocesses managed by `multi_bot_manager.py`. Each bot instance has independent config (LLM backend, TTS, prompts). Bots with `auto_start=true` restart on app startup.

**Cloud LLM routing**: `cloud_llm_service.py` has `CloudLLMService` with a factory pattern. OpenAI-compatible providers use `OpenAICompatibleProvider` automatically. Custom SDKs (Gemini) get their own provider class inheriting `BaseLLMProvider`. Provider types defined in `PROVIDER_TYPES` dict in `db/models.py`.

## Code Patterns

**Adding a new API endpoint:**
1. Create or edit router in `app/routers/`
2. Use `ServiceContainer` from `app/dependencies.py` for DI
3. Add router to imports and `__all__` in `app/routers/__init__.py`
4. Register router in `orchestrator.py` with `app.include_router()`

**Adding a new cloud LLM provider type:**
1. Add entry to `PROVIDER_TYPES` dict in `db/models.py`
2. If OpenAI-compatible, it works automatically via `OpenAICompatibleProvider`
3. For custom SDK, create provider class inheriting `BaseLLMProvider` in `cloud_llm_service.py`
4. Register in `CloudLLMService.PROVIDER_CLASSES`

**Adding a new secretary persona:**
1. Add entry to `SECRETARY_PERSONAS` dict in `vllm_llm_service.py`

**Adding i18n translations:**
1. Edit `admin/src/plugins/i18n.ts` — add keys to both `ru` and `en` message objects

**Database migrations:** Manual scripts in `scripts/migrate_*.py` (no Alembic). New tables auto-created by `Base.metadata.create_all` on startup; schema changes to existing tables need migration scripts.

**API URL patterns:**
- `GET/POST /admin/{resource}` — List/create
- `GET/PUT/DELETE /admin/{resource}/{id}` — CRUD
- `POST /admin/{resource}/{id}/action` — Actions (start, stop, test)
- `GET /admin/{resource}/stream` — SSE endpoints
- `POST /v1/chat/completions`, `POST /v1/audio/speech`, `GET /v1/models` — OpenAI-compatible

## Key Environment Variables

```bash
LLM_BACKEND=vllm                    # "vllm", "gemini", or "cloud:{provider_id}"
VLLM_API_URL=http://localhost:11434 # Auto-normalized: trailing /v1 is stripped
SECRETARY_PERSONA=gulya             # "gulya" or "lidia"
ORCHESTRATOR_PORT=8002
ADMIN_JWT_SECRET=...                # Auto-generated if empty
REDIS_URL=redis://localhost:6379/0  # Optional, graceful fallback if unavailable
DEV_MODE=1                          # Makes backend proxy to Vite dev server (:5173)
```

## Codebase Conventions

- **Python 3.11+**, line length 100, double quotes (ruff format)
- **Cyrillic strings are normal** — RUF001/002/003 disabled; Russian is used in UI text, logging, persona prompts
- **FastAPI Depends pattern** — `B008` (function-call-in-default-argument) is disabled for this reason
- **Optional imports** — Services like vLLM and OpenVoice use try/except at module level with `*_AVAILABLE` flags
- **SQLAlchemy mapped_column style** — Models use `Mapped[T]` with `mapped_column()` (declarative 2.0)
- **Repository pattern** — `BaseRepository(Generic[T])` provides get_by_id, get_all, create, update, delete. Domain repos extend with custom queries.
- **Admin panel**: Vue 3 + Composition API + Pinia stores + vue-i18n. API clients in `admin/src/api/`, one per domain.

## Known Issues

1. **Vosk model required** — Download to `models/vosk/` for STT
2. **XTTS requires CC >= 7.0** — RTX 3060+; use OpenVoice for older GPUs
3. **GPU memory** — vLLM 50% (~6GB) + XTTS ~5GB must fit within 12GB
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost` for API URL
5. **Docker + vLLM** — First run needs `docker pull vllm/vllm-openai:latest` (~9GB)
6. **xray-core for VLESS** — Included in Docker image; for local dev, download to `./bin/xray`
