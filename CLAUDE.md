# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary System — virtual secretary with voice cloning (XTTS v2, OpenVoice), pre-trained voices (Piper), local LLM (vLLM + Qwen/Llama/DeepSeek), cloud LLM fallback (Gemini, Kimi, OpenAI, Claude, DeepSeek, OpenRouter), and Claude Code CLI bridge. Features GSM telephony (SIM7600E-H), amoCRM integration (OAuth2, contacts, leads, pipelines, sync), Vue 3 PWA admin panel, i18n (ru/en), multi-instance Telegram bots with sales/payments, website chat widgets, and LoRA fine-tuning.

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
Guest demo: demo / demo (read-only access)

### User Management

```bash
python scripts/manage_users.py list                          # List all users
python scripts/manage_users.py create <user> <pass> --role user  # Create user (admin|user|guest)
python scripts/manage_users.py set-password <user> <pass>    # Reset password
python scripts/manage_users.py set-role <user> <role>        # Change role
python scripts/manage_users.py disable <user>                # Deactivate user
python scripts/manage_users.py enable <user>                 # Reactivate user
python scripts/manage_users.py delete <user>                 # Delete user
```

### Database Migrations

```bash
python scripts/migrate_json_to_db.py         # Initial JSON → SQLite migration
python scripts/migrate_to_instances.py       # Multi-instance bot/widget architecture
python scripts/migrate_users.py              # Create users table, seed admin + demo
python scripts/migrate_user_ownership.py     # Add owner_id to resource tables
python scripts/migrate_persona_rename.py     # Persona name migration (Гуля→Анна, Лидия→Марина)
python scripts/migrate_gsm_tables.py         # GSM call/SMS log tables
python scripts/migrate_amocrm.py             # amoCRM config tables
python scripts/migrate_sales_bot.py          # Sales funnel tables
python scripts/migrate_add_payment_fields.py # Payment fields for sales
python scripts/migrate_legal_compliance.py   # Legal compliance tables
python scripts/seed_tz_generator.py          # Seed TZ generator bot data
python scripts/seed_tz_widget.py             # Seed TZ widget data
```

### Lint & Format

```bash
# Python (requires .venv with ruff installed)
ruff check .                # Lint (see pyproject.toml for full rule config)
ruff check . --fix          # Auto-fix
ruff format .               # Format
ruff format --check .       # Check formatting (CI uses this)

# Frontend
cd admin && npm run lint       # Lint + auto-fix
cd admin && npm run lint:check # Lint without auto-fix (CI-style)

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

Pytest uses `asyncio_mode = "auto"` — async test functions run without needing `@pytest.mark.asyncio`. Custom markers: `slow`, `integration`, `gpu`.

### CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push to `main`/`develop` and on PRs:
- `lint-backend` — ruff check + format check + mypy (mypy is soft — `|| true`, won't fail build)
- `lint-frontend` — npm ci + eslint + build (includes type check)
- `security` — Trivy vulnerability scanner

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Orchestrator (port 8002)                     │
│  orchestrator.py + app/routers/ (19 routers, ~348 endpoints) │
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

**Global state in orchestrator.py** (~3200 lines, ~106 endpoints): This is the FastAPI entry point. It initializes all services as module-level globals, populates the `ServiceContainer`, and includes all routers. Legacy endpoints (OpenAI-compatible `/v1/*`) still live here alongside the modular router system.

**ServiceContainer (`app/dependencies.py`)**: Singleton holding references to all initialized services (TTS, LLM, STT). Routers get services via FastAPI `Depends`. Populated during app startup in `orchestrator.py`.

**Database layer** (`db/`): Async SQLAlchemy with aiosqlite. `db/database.py` creates the engine and `AsyncSessionLocal` factory. `db/integration.py` provides backward-compatible manager classes (e.g., `AsyncChatManager`, `AsyncFAQManager`) that wrap repository calls — these are used as module-level singletons imported by `orchestrator.py` and routers. Repositories in `db/repositories/` inherit from `BaseRepository` with generic CRUD.

**Telegram bots**: Run as subprocesses managed by `multi_bot_manager.py`. Each bot instance has independent config (LLM backend, TTS, prompts). Bots with `auto_start=true` restart on app startup.

**Two service layers**: Core AI services live at project root (`cloud_llm_service.py`, `vllm_llm_service.py`, `voice_clone_service.py`, `openvoice_service.py`, `piper_tts_service.py`, `stt_service.py`, `llm_service.py`). Orchestration services also at root: `service_manager.py`, `multi_bot_manager.py`, `telegram_bot_service.py`, `system_monitor.py`, `tts_finetune_manager.py`. Domain-specific services live in `app/services/` (`amocrm_service.py`, `gsm_service.py`, `backup_service.py`, `sales_funnel.py`, `yoomoney_service.py`, `audio_pipeline.py`).

**Cloud LLM routing**: `cloud_llm_service.py` (project root) has `CloudLLMService` with a factory pattern. OpenAI-compatible providers use `OpenAICompatibleProvider` automatically. Custom SDKs (Gemini) get their own provider class inheriting `BaseLLMProvider`. Provider types defined in `PROVIDER_TYPES` dict in `db/models.py`.

**amoCRM integration**: `app/services/amocrm_service.py` is a pure async HTTP client (no DB) with optional proxy support (`AMOCRM_PROXY` env var for Docker/VPN environments). `app/routers/amocrm.py` handles OAuth2 flow, token auto-refresh, and proxies API calls. Config/tokens stored via `AsyncAmoCRMManager` in `db/integration.py`. Webhook at `POST /webhooks/amocrm`. For private amoCRM integrations, auth codes are obtained from the integration settings (not OAuth redirect). If Docker can't reach amoCRM (VPN on host), run `scripts/amocrm_proxy.py` on the host.

**GSM telephony**: `app/services/gsm_service.py` manages SIM7600E-H modem via AT commands over serial port (`/dev/ttyUSB2`). Auto-switches to mock mode when hardware is unavailable. `app/routers/gsm.py` exposes call/SMS management endpoints. Call and SMS logs stored via `GSMCallLogRepository` and `GSMSMSLogRepository` in `db/repositories/gsm.py`. Models: `GSMCallLog`, `GSMSMSLog` in `db/models.py`. Manager: `AsyncGSMManager` in `db/integration.py`. Migration: `scripts/migrate_gsm_tables.py`.

**Multi-user RBAC**: `User` model in `db/models.py` with roles: `guest` (read-only), `user` (own resources), `admin` (full access). `auth_manager.py` provides DB-backed auth with salted password hashing, JWT tokens with `user_id`, and `require_not_guest` dependency for write endpoints. Resources with `owner_id` column (ChatSession, BotInstance, WidgetInstance, CloudLLMProvider, TTSPreset) are filtered by ownership for non-admin users. `UserRepository` in `db/repositories/user.py`, `AsyncUserManager` in `db/integration.py`. Profile/password endpoints in `app/routers/auth.py`. Migration: `scripts/migrate_users.py`, `scripts/migrate_user_ownership.py`. CLI management: `scripts/manage_users.py`.

**Sales & payments**: `app/routers/bot_sales.py` manages Telegram bot sales funnels (quiz, segments, agent prompts, follow-ups, testimonials). `app/services/sales_funnel.py` implements funnel logic with segment paths: `diy`, `basic`, `custom` (original bot), `qualified`, `unqualified`, `needs_analysis` (TZ generator bot). `app/routers/yoomoney_webhook.py` + `app/services/yoomoney_service.py` handle YooMoney payment callbacks. Migration: `scripts/migrate_sales_bot.py`, `scripts/migrate_add_payment_fields.py`. Seed scripts: `scripts/seed_tz_generator.py` (TZ bot), `scripts/seed_tz_widget.py` (TZ widget).

**Backup/restore**: `app/routers/backup.py` + `app/services/backup_service.py` — export/import system configuration and data.

**Widget test chat**: Widget instances can be tested live from the admin panel. `app/routers/chat.py` accepts an optional `widget_instance_id` parameter on streaming endpoints, which overrides LLM/TTS settings to match the widget's config. Frontend in `WidgetView.vue` test tab. The embeddable widget (`web-widget/ai-chat-widget.js`) performs a runtime enabled check via `GET /widget/status` (public, no auth) — if the instance is disabled, the widget icon won't render on the site.

**Other routers**: `usage.py` (usage statistics/analytics), `legal.py` (legal compliance, migration: `scripts/migrate_legal_compliance.py`), `github_webhook.py` (GitHub CI/CD webhook handler).

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

**RBAC auth guards** (3 levels in `auth_manager.py`):
- `Depends(get_current_user)` — any authenticated user (read endpoints)
- `Depends(require_not_guest)` — user + admin only (write endpoints)
- `Depends(require_admin)` — admin only (vLLM, GSM, backups, models)
- Data isolation: `owner_id = None if user.role == "admin" else user.id` in routers

**Adding i18n translations:**
1. Edit `admin/src/plugins/i18n.ts` — add keys to both `ru` and `en` message objects

**Database migrations:** Manual scripts in `scripts/migrate_*.py` (no Alembic). New tables auto-created by `Base.metadata.create_all` on startup; schema changes to existing tables need migration scripts.

**API URL patterns:**
- `GET/POST /admin/{resource}` — List/create
- `GET/PUT/DELETE /admin/{resource}/{id}` — CRUD
- `POST /admin/{resource}/{id}/action` — Actions (start, stop, test)
- `GET /admin/{resource}/stream` — SSE endpoints
- `POST /webhooks/{service}` — External webhooks (amocrm, yoomoney, github)
- `POST /v1/chat/completions`, `POST /v1/audio/speech`, `GET /v1/models` — OpenAI-compatible

## Key Environment Variables

```bash
LLM_BACKEND=vllm                    # "vllm", "gemini", or "cloud:{provider_id}"
VLLM_API_URL=http://localhost:11434 # Auto-normalized: trailing /v1 is stripped
SECRETARY_PERSONA=anna             # "anna" or "marina"
ORCHESTRATOR_PORT=8002
ADMIN_JWT_SECRET=...                # Auto-generated if empty
ADMIN_USERNAME=admin                # Legacy fallback when users table is empty
ADMIN_PASSWORD_HASH=...             # Legacy fallback (SHA-256 of password)
REDIS_URL=redis://localhost:6379/0  # Optional, graceful fallback if unavailable
DEV_MODE=1                          # Makes backend proxy to Vite dev server (:5173)
AMOCRM_PROXY=http://host:8888      # Optional, for Docker/VPN environments
```

## Codebase Conventions

- **Python 3.11+**, line length 100, double quotes (ruff format)
- **Cyrillic strings are normal** — RUF001/002/003 disabled; Russian is used in UI text, logging, persona prompts
- **FastAPI Depends pattern** — `B008` (function-call-in-default-argument) is disabled for this reason
- **Optional imports** — Services like vLLM and OpenVoice use try/except at module level with `*_AVAILABLE` flags
- **SQLAlchemy mapped_column style** — Models use `Mapped[T]` with `mapped_column()` (declarative 2.0)
- **Repository pattern** — `BaseRepository(Generic[T])` provides get_by_id, get_all, create, update, delete. Domain repos extend with custom queries.
- **Admin panel**: Vue 3 + Composition API + Pinia stores + vue-i18n. API clients in `admin/src/api/`, one per domain.
- **mypy strict scope** — Only `db/`, `auth_manager.py`, `service_manager.py` require typed defs; other modules are relaxed. mypy is soft in CI (`|| true`).
- **Pre-commit hooks** — ruff lint+format, mypy (core only), eslint, hadolint (Docker), plus standard checks (trailing whitespace, large files ≤1MB, private key detection, merge conflicts). See `.pre-commit-config.yaml`.

## Known Issues

1. **Vosk model required** — Download to `models/vosk/` for STT
2. **XTTS requires CC >= 7.0** — RTX 3060+; use OpenVoice for older GPUs
3. **GPU memory** — vLLM 50% (~6GB) + XTTS ~5GB must fit within 12GB
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost` for API URL
5. **Docker + vLLM** — First run needs `docker pull vllm/vllm-openai:latest` (~9GB)
6. **xray-core for VLESS** — Included in Docker image; for local dev, download to `./bin/xray`
