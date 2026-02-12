# AI Secretary System - Memory

## Machine Role
- **Role**: `server` (cloud VPS)
- **Hardware**: No GPU, cloud-only deployment
- **Capabilities**: Cloud LLM providers, Docker, bot management, production
- **Git branch prefix**: `server/*`
- **Primary file ownership**: cloud services, Docker config, deployment, bot runtime
- See CLAUDE.md "Parallel Development" section for full rules

## Project Patterns
- Frontend build: `cd admin && npm run build` (vue-tsc + vite)
- Python lint: `ruff check .`
- Frontend lint: `cd admin && npm run lint`
- No GPU available — skip vLLM, XTTS, OpenVoice services
- LLM backend is always `cloud:{provider_id}`, never `vllm`

## Lessons Learned
- Migration scripts follow pattern in `scripts/migrate_*.py` - use raw sqlite3, check table/column existence
