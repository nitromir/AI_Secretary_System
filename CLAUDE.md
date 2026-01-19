# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Secretary "Лидия" - virtual secretary with voice cloning (XTTS v2) and pre-trained voices (Piper). Handles phone calls via Twilio with STT → LLM → TTS pipeline. Integrated with OpenWebUI for text chat with voice responses.

## Architecture

```
                         ┌─────────────────────────────────────┐
                         │     Orchestrator (port 8002)        │
                         │         orchestrator.py             │
                         └──────────────┬──────────────────────┘
                                        │
        ┌───────────────┬───────────────┼───────────────┬───────────────┬──────────────────┐
        ↓               ↓               ↓               ↓               ↓                  ↓
   STT Service     LLM Service    Voice Clone    OpenVoice v2     Piper TTS        Admin Panel
  (disabled)      llm_service.py  (XTTS v2)     openvoice_       piper_tts_service admin_web.html
                        │         voice_clone_   service.py       (CPU)
                        │         service.py     (GPU CC 6.1+)
                        │         (GPU CC 7.0+)
                        ↓
                  FAQ System
              typical_responses.json
```

**GPU Distribution (Multi-GPU Setup):**
```
GPU 0: P104-100  (8GB, CC 6.1)  → OpenVoice TTS (port 8003)
GPU 1: RTX 3060  (12GB, CC 8.6) → vLLM Llama-3.1-8B (port 11434)
```

**Request flow:**
1. User message → FAQ check (instant) OR Gemini LLM
2. Response text → TTS (XTTS/Piper based on `current_voice_config`)
3. Audio returned to user

## Commands

```bash
# Start all services (Multi-GPU: OpenVoice + vLLM)
./start_all.sh

# Start orchestrator with GPU (XTTS voice cloning)
COQUI_TOS_AGREED=1 ./venv/bin/python orchestrator.py

# Start orchestrator CPU-only (Piper TTS)
./start_cpu.sh

# Start individual services
./start_openvoice.sh    # OpenVoice on GPU 0 (P104-100)
./start_vllm.sh         # vLLM on GPU 1 (RTX 3060)

# Health check
curl http://localhost:8002/health

# Test individual services
./venv/bin/python voice_clone_service.py    # Test XTTS (requires GPU CC >= 7.0)
./venv/bin/python piper_tts_service.py      # Test Piper
./venv/bin/python llm_service.py            # Test LLM + FAQ
./openvoice_env/bin/python openvoice_service.py --test  # Test OpenVoice

# Run integration tests
./test_system.sh

# First-time setup
./setup.sh && cp .env.example .env          # Edit .env: add GEMINI_API_KEY

# Setup OpenVoice (for P104-100 GPU)
./setup_openvoice.sh
```

## Key Components

### Multi-Voice TTS System
Four voices available, switchable via admin panel or API:

| Voice | Engine | GPU | Speed | Quality |
|-------|--------|-----|-------|---------|
| lidia | XTTS v2 | CC >= 7.0 | ~5-10s | Best cloning quality |
| lidia_openvoice | OpenVoice v2 | CC >= 6.1 | ~2-4s | Good cloning, works on P104-100 |
| dmitri | Piper | CPU | ~0.5s | Pre-trained male |
| irina | Piper | CPU | ~0.5s | Pre-trained female |

**Voice switching:**
- Admin: http://localhost:8002/admin → TTS tab
- API: `POST /admin/voice {"voice": "lidia_openvoice"}`
- Code: `current_voice_config` dict in orchestrator.py:294

### FAQ System (`typical_responses.json`)
Bypasses LLM for common questions. Checked before every Gemini API call in `llm_service.py:79`.

```json
{
  "привет": "Здравствуйте! Чем могу помочь?",
  "сколько времени": "Сейчас {current_time}."
}
```

Templates: `{current_time}`, `{current_date}`, `{day_of_week}`

Hot reload: `llm_service.reload_faq()`

### Streaming TTS Manager
Pre-synthesizes audio during LLM streaming for faster response. Caches audio by text hash.
- Location: `orchestrator.py:38` (`StreamingTTSManager` class)
- Active during `/v1/chat/completions` streaming
- Cache checked in `/v1/audio/speech` before synthesis

### XTTS Voice Presets
Defined in `voice_clone_service.py:120` (`INTONATION_PRESETS`)

```python
service.synthesize(text, preset="warm")      # Тёплый
service.synthesize(text, preset="calm")      # Спокойный
service.synthesize(text, preset="energetic") # Энергичный
service.synthesize(text, preset="natural")   # Default
service.synthesize(text, preset="neutral")   # Деловой
```

## API Quick Reference

**OpenAI-compatible (for OpenWebUI):**
- `POST /v1/chat/completions` — Chat with streaming
- `POST /v1/audio/speech` — TTS with current voice
- `GET /v1/models` — Available models

**Admin voice control:**
- `GET /admin/voices` — List all voices
- `POST /admin/voice` — Set voice `{"voice": "irina"}`
- `POST /admin/voice/test` — Test synthesis

**Admin TTS/LLM:**
- `GET/POST /admin/tts/preset` — XTTS preset
- `GET/POST /admin/llm/model` — Gemini model
- `DELETE /admin/llm/history` — Clear conversation

## OpenWebUI Integration

```
URL: http://172.17.0.1:8002/v1  (Docker bridge IP)
API Key: sk-dummy (any value)
TTS Voice: lidia
Model: lidia-gemini
```

## Environment Variables

Required:
```bash
GEMINI_API_KEY=...           # Google AI Studio API key
```

Optional:
```bash
ORCHESTRATOR_PORT=8002       # Default port
VOICE_SAMPLES_DIR=./Лидия    # XTTS samples directory
GEMINI_MODEL=gemini-2.5-pro-latest
```

## Key Files

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, routes, voice switching, StreamingTTSManager |
| `voice_clone_service.py` | XTTS v2, GPU synthesis (CC >= 7.0), presets, Е→Ё replacement |
| `openvoice_service.py` | OpenVoice v2, GPU synthesis (CC >= 6.1), voice cloning |
| `piper_tts_service.py` | Piper ONNX wrapper (CPU) |
| `llm_service.py` | Gemini API + FAQ system |
| `typical_responses.json` | FAQ data (hot-reloadable) |
| `admin_web.html` | Admin panel UI |
| `Лидия/` | WAV samples for voice cloning |
| `models/*.onnx` | Piper voice models (dmitri, irina) |
| `checkpoints_v2/` | OpenVoice v2 model checkpoints |
| `start_all.sh` | Launch all services (multi-GPU) |
| `start_openvoice.sh` | Launch OpenVoice on GPU 0 |
| `start_vllm.sh` | Launch vLLM on GPU 1 |
| `setup_openvoice.sh` | Install OpenVoice dependencies |

## Known Issues

1. **STT disabled** — faster-whisper hangs on load; use text chat only
2. **XTTS on P104-100** — XTTS requires CC >= 7.0, use OpenVoice instead for CC 6.1
3. **Gemini 429** — Quota exceeded; use `gemini-2.5-flash` not `pro`
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost`
5. **OpenVoice Russian** — Russian not native, uses cross-lingual cloning (quality varies)

## Code Patterns

**Adding a new Piper voice:**
1. Add ONNX model to `./models/`
2. Add entry to `PiperTTSService.VOICES` dict in `piper_tts_service.py:26`
3. Voice auto-appears in admin panel

**Adding FAQ response:**
1. Edit `typical_responses.json`
2. Call `llm_service.reload_faq()` or restart orchestrator

**Changing default TTS for all endpoints:**
1. Modify `current_voice_config` dict in `orchestrator.py:285`
2. Or use API: `POST /admin/voice {"voice": "irina"}`

**Text preprocessing for TTS:**
- Е→Ё replacement: `voice_clone_service.py:69` (`YO_REPLACEMENTS` dict)
- Add pause words: `voice_clone_service.py:210` (`add_pauses` method)
