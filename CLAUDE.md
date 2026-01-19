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

**GPU Mode (Single GPU - RTX 3060):**
```
RTX 3060 (12GB, CC 8.6):
  - vLLM Llama-3.1-8B (70% GPU memory = ~8.4GB)
  - XTTS v2 voice cloning (remaining ~3.6GB)
```

**Request flow:**
1. User message → FAQ check (instant) OR vLLM/Gemini LLM
2. Response text → TTS (XTTS/Piper based on `current_voice_config`)
3. Audio returned to user

## Commands

```bash
# GPU Mode: XTTS + vLLM on RTX 3060 (recommended)
./start_gpu.sh

# CPU-only mode (Piper TTS + Gemini API)
./start_cpu.sh

# Start vLLM separately (for debugging)
./start_vllm.sh

# Health check
curl http://localhost:8002/health

# Test individual services
./venv/bin/python voice_clone_service.py    # Test XTTS (requires GPU CC >= 7.0)
./venv/bin/python piper_tts_service.py      # Test Piper
./venv/bin/python llm_service.py            # Test Gemini LLM + FAQ
./venv/bin/python vllm_llm_service.py       # Test vLLM (requires running vLLM server)

# First-time setup
./setup.sh && cp .env.example .env          # Edit .env: add GEMINI_API_KEY (optional with vLLM)
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

```bash
# LLM Backend selection
LLM_BACKEND=vllm             # "vllm" (local Llama) or "gemini" (cloud API)
VLLM_API_URL=http://localhost:11434  # vLLM server URL

# Gemini (only needed if LLM_BACKEND=gemini)
GEMINI_API_KEY=...           # Google AI Studio API key

# Optional
ORCHESTRATOR_PORT=8002       # Default port
VOICE_SAMPLES_DIR=./Лидия    # XTTS samples directory
CUDA_VISIBLE_DEVICES=1       # GPU index for RTX 3060
```

## Key Files

| File | Purpose |
|------|---------|
| `orchestrator.py` | FastAPI server, routes, voice switching, StreamingTTSManager |
| `voice_clone_service.py` | XTTS v2, GPU synthesis (CC >= 7.0), presets, Е→Ё replacement |
| `piper_tts_service.py` | Piper ONNX wrapper (CPU) |
| `llm_service.py` | Gemini API + FAQ system |
| `vllm_llm_service.py` | vLLM API (local Llama-3.1-8B) + FAQ system |
| `typical_responses.json` | FAQ data (hot-reloadable) |
| `admin_web.html` | Admin panel UI |
| `Лидия/` | WAV samples for voice cloning |
| `models/*.onnx` | Piper voice models (dmitri, irina) |
| `start_gpu.sh` | Launch XTTS + vLLM on RTX 3060 |
| `start_cpu.sh` | Launch Piper + Gemini (CPU mode) |
| `start_vllm.sh` | Launch vLLM separately |

## Known Issues

1. **STT disabled** — faster-whisper hangs on load; use text chat only
2. **XTTS requires CC >= 7.0** — Use RTX 3060 or newer GPU
3. **GPU memory sharing** — vLLM uses 70% (~8.4GB), XTTS needs ~3.6GB, works on 12GB GPU
4. **OpenWebUI Docker** — Use `172.17.0.1` not `localhost`

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
