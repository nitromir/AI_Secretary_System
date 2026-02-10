#!/usr/bin/env python3
"""
Apply cloud-mode patches to make GPU/TTS/STT imports optional.
Run after git pull to patch files for servers without torch/GPU.
Uses sed-like replacements — idempotent (safe to run multiple times).
"""

import re
from pathlib import Path


REPO = "/opt/ai-secretary"


def patch_file(path: str, patches: list[tuple[str, str]]) -> None:
    with open(path) as f:
        content = f.read()
    original = content
    for old, new in patches:
        if old in content and new not in content:
            content = content.replace(old, new, 1)
    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print(f"  PATCHED: {path}")
    else:
        print(f"  OK: {path}")


# ─── orchestrator.py ───

def patch_orchestrator():
    path = f"{REPO}/orchestrator.py"
    with open(path) as f:
        content = f.read()
    original = content

    # 0. Add async_chat_manager to db.integration imports (needed for public widget endpoints)
    if "async_chat_manager," not in content:
        content = content.replace(
            "    async_audit_logger,\n    async_cloud_provider_manager,",
            "    async_audit_logger,\n    async_chat_manager,\n    async_cloud_provider_manager,",
        )

    # 1. Make piper import optional
    if "PIPER_AVAILABLE" not in content:
        content = content.replace(
            "from piper_tts_service import PiperTTSService\nfrom service_manager",
            "try:\n    from piper_tts_service import PiperTTSService\n    PIPER_AVAILABLE = True\nexcept ImportError:\n    PIPER_AVAILABLE = False\n    PiperTTSService = None\n\nfrom service_manager",
        )
    # Legacy: if piper was already removed but PIPER_AVAILABLE missing
    if "PIPER_AVAILABLE" not in content:
        content = content.replace(
            "from service_manager import get_service_manager\nfrom system_monitor",
            "try:\n    from piper_tts_service import PiperTTSService\n    PIPER_AVAILABLE = True\nexcept ImportError:\n    PIPER_AVAILABLE = False\n    PiperTTSService = None\n\nfrom service_manager import get_service_manager\nfrom system_monitor",
        )

    # 2. Make STT import optional
    content = content.replace(
        "from stt_service import STTService\nfrom system_monitor",
        "from system_monitor",
    )
    if "STT_AVAILABLE" not in content:
        content = content.replace(
            "from system_monitor import get_system_monitor",
            "try:\n    from stt_service import STTService\n    STT_AVAILABLE = True\nexcept ImportError:\n    STT_AVAILABLE = False\n    STTService = None\n\nfrom system_monitor import get_system_monitor",
        )

    # 3. Make tts_finetune optional
    if "TTS_FINETUNE_AVAILABLE" not in content:
        content = content.replace(
            "from tts_finetune_manager import get_tts_finetune_manager\n",
            "try:\n    from tts_finetune_manager import get_tts_finetune_manager\n    TTS_FINETUNE_AVAILABLE = True\nexcept ImportError:\n    TTS_FINETUNE_AVAILABLE = False\n    get_tts_finetune_manager = None\n",
        )

    # 4. Make voice_clone optional
    if "XTTS_AVAILABLE" not in content:
        content = content.replace(
            "from voice_clone_service import VoiceCloneService\n",
            "try:\n    from voice_clone_service import VoiceCloneService\n    XTTS_AVAILABLE = True\nexcept ImportError:\n    XTTS_AVAILABLE = False\n    VoiceCloneService = None\n",
        )

    # 5. Guard Piper init
    content = content.replace(
        '        # Инициализация Piper TTS (Dmitri, Irina) - CPU, загружаем первым\n        logger.info("📦 Загрузка Piper TTS Service (CPU)...")\n        try:\n            piper_service = PiperTTSService()\n        except Exception as e:\n            logger.warning(f"⚠️ Piper TTS недоступен: {e}")\n            piper_service = None',
        '        # Инициализация Piper TTS (Dmitri, Irina) - CPU, загружаем первым\n        if PIPER_AVAILABLE:\n            logger.info("📦 Загрузка Piper TTS Service (CPU)...")\n            try:\n                piper_service = PiperTTSService()\n            except Exception as e:\n                logger.warning(f"⚠️ Piper TTS недоступен: {e}")\n                piper_service = None\n        else:\n            logger.info("⏭️ Piper TTS не установлен (пропускаем)")\n            piper_service = None',
    )

    # 6. Guard XTTS Анна init
    content = content.replace(
        '        # Инициализация XTTS (Анна) - GPU CC >= 7.0, по умолчанию\n        logger.info("📦 Загрузка Voice Clone Service (XTTS - Анна)...")\n        try:\n            anna_voice_service = VoiceCloneService(voice_samples_dir="./Анна")\n            logger.info(\n                f"✅ XTTS (Анна) загружен: {len(anna_voice_service.voice_samples)} образцов"\n            )\n        except Exception as e:\n            logger.warning(f"⚠️ XTTS (Анна) недоступен: {e}")\n            anna_voice_service = None',
        '        # Инициализация XTTS (Анна) - GPU CC >= 7.0, по умолчанию\n        if XTTS_AVAILABLE:\n            logger.info("📦 Загрузка Voice Clone Service (XTTS - Анна)...")\n            try:\n                anna_voice_service = VoiceCloneService(voice_samples_dir="./Анна")\n                logger.info(\n                    f"✅ XTTS (Анна) загружен: {len(anna_voice_service.voice_samples)} образцов"\n                )\n            except Exception as e:\n                logger.warning(f"⚠️ XTTS (Анна) недоступен: {e}")\n                anna_voice_service = None\n        else:\n            logger.info("⏭️ XTTS не установлен (пропускаем)")\n            anna_voice_service = None',
    )

    # 7. Guard XTTS Марина init
    content = content.replace(
        '        # Инициализация XTTS (Марина) - GPU CC >= 7.0, опционально\n        logger.info("📦 Загрузка Voice Clone Service (XTTS - Марина)...")\n        try:\n            voice_service = VoiceCloneService(voice_samples_dir="./Марина")\n            logger.info(f"✅ XTTS (Марина) загружен: {len(voice_service.voice_samples)} образцов")\n        except Exception as e:\n            logger.warning(f"⚠️ XTTS (Марина) недоступен (требуется GPU CC >= 7.0): {e}")\n            voice_service = None',
        '        # Инициализация XTTS (Марина) - GPU CC >= 7.0, опционально\n        if XTTS_AVAILABLE:\n            logger.info("📦 Загрузка Voice Clone Service (XTTS - Марина)...")\n            try:\n                voice_service = VoiceCloneService(voice_samples_dir="./Марина")\n                logger.info(f"✅ XTTS (Марина) загружен: {len(voice_service.voice_samples)} образцов")\n            except Exception as e:\n                logger.warning(f"⚠️ XTTS (Марина) недоступен (требуется GPU CC >= 7.0): {e}")\n                voice_service = None\n        else:\n            voice_service = None',
    )

    # 8. Make LLM init optional for cloud backend
    if 'elif LLM_BACKEND.startswith("cloud:")' not in content:
        content = content.replace(
            '        else:\n            logger.info("📦 Загрузка Gemini LLM Service...")\n            llm_service = LLMService()',
            '        elif LLM_BACKEND.startswith("cloud:"):\n            logger.info(f"☁️ LLM backend: {LLM_BACKEND} (cloud provider)")\n            try:\n                llm_service = LLMService()\n            except Exception as e:\n                logger.warning(f"⚠️ Gemini fallback недоступен ({e}), только облачные провайдеры")\n                llm_service = None\n        else:\n            logger.info("📦 Загрузка Gemini LLM Service...")\n            llm_service = LLMService()',
        )

    # 9. Guard stt/tts router includes
    if "if stt is not None:" not in content:
        content = content.replace(
            "app.include_router(stt.router)\n",
            "if stt is not None:\n    app.include_router(stt.router)\n",
        )
    if "if tts is not None:" not in content:
        content = content.replace(
            "app.include_router(tts.router)\n",
            "if tts is not None:\n    app.include_router(tts.router)\n",
        )

    # 10. Fix type annotations to use string literals (avoid NameError at module level)
    content = content.replace(
        'Optional[VoiceCloneService] = None',
        'Optional["VoiceCloneService"] = None',
    )
    content = content.replace(
        'Optional[PiperTTSService] = None',
        'Optional["PiperTTSService"] = None',
    )
    content = content.replace(
        'Optional[STTService] = None',
        'Optional["STTService"] = None',
    )

    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print(f"  PATCHED: {path}")
    else:
        print(f"  OK: {path}")


# ─── app/routers/__init__.py ───

def patch_routers_init():
    path = f"{REPO}/app/routers/__init__.py"
    with open(path) as f:
        content = f.read()
    original = content

    # Remove stt and tts from main import if present
    content = content.replace("    stt,\n    telegram,\n", "    telegram,\n")
    content = content.replace("    tts,\n    usage,\n", "    usage,\n")

    # Add optional imports if not present
    if "STT router is optional" not in content:
        content = content.replace(
            ")\n\n\n__all__",
            ')\n\n# STT router is optional (requires torch/vosk/whisper)\ntry:\n    from app.routers import stt\nexcept ImportError:\n    stt = None  # type: ignore[assignment]\n\n# TTS router is optional (requires torch for XTTS)\ntry:\n    from app.routers import tts\nexcept ImportError:\n    tts = None  # type: ignore[assignment]\n\n\n__all__',
        )

    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print(f"  PATCHED: {path}")
    else:
        print(f"  OK: {path}")


# ─── db/models.py ───

def patch_models():
    path = f"{REPO}/db/models.py"
    with open(path) as f:
        content = f.read()

    # Fix duplicate index: UsageLimits has index=True on service_type
    # AND explicit Index in __table_args__ with same auto-generated name
    new = re.sub(
        r'(class UsageLimits.*?__tablename__.*?\n.*?service_type.*?)index=True(.*?# "tts", "stt", "llm")',
        r'\1\2# "tts", "stt", "llm"',
        content,
        flags=re.DOTALL,
    )
    if new != content:
        with open(path, "w") as f:
            f.write(new)
        print(f"  PATCHED: {path}")
    else:
        print(f"  OK: {path}")


# ─── admin/vite.config.ts ───

def patch_vite_config():
    path = f"{REPO}/admin/vite.config.ts"
    with open(path) as f:
        content = f.read()
    original = content

    # Add VITE_BASE_PATH support if not present
    if "VITE_BASE_PATH" not in content:
        content = content.replace(
            "base: isDemo ? '/' : '/admin/',",
            "base: env.VITE_BASE_PATH || (isDemo ? '/' : '/admin/'),",
        )

    if content != original:
        with open(path, "w") as f:
            f.write(content)
        print(f"  PATCHED: {path}")
    else:
        print(f"  OK: {path}")


# ─── admin/.env.production.local ───

def ensure_env_production_local():
    path = f"{REPO}/admin/.env.production.local"
    if not Path(path).exists():
        with open(path, "w") as f:
            f.write("VITE_BASE_PATH=/\n")
        print(f"  CREATED: {path}")
    else:
        print(f"  OK: {path}")


if __name__ == "__main__":
    print("Applying cloud-mode patches...")
    patch_orchestrator()
    patch_routers_init()
    patch_models()
    patch_vite_config()
    ensure_env_production_local()
    print("Done!")
