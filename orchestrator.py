#!/usr/bin/env python3
"""
Главный оркестратор - координирует все сервисы
STT (Whisper) -> LLM (Gemini) -> TTS (XTTS v2)
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from pydantic import BaseModel

# Modular routers
from app.routers import (
    audit,
    auth,
    bot_sales,
    chat,
    faq,
    github_webhook,
    gsm,
    llm,
    monitor,
    services,
    stt,
    telegram,
    tts,
    widget,
    yoomoney_webhook,
)
from auth_manager import (
    LoginRequest,
    LoginResponse,
    User,
    authenticate_user,
    create_access_token,
    get_auth_status,
    get_current_user,
)

# Cloud LLM service for multi-provider support
from cloud_llm_service import PROVIDER_TYPES, CloudLLMService

# Database integration
from db.integration import (
    async_audit_logger,
    async_cloud_provider_manager,
    async_config_manager,
    async_faq_manager,
    async_preset_manager,
    async_widget_instance_manager,
    get_database_status,
    init_database,
    shutdown_database,
)
from finetune_manager import get_finetune_manager
from llm_service import LLMService
from model_manager import get_model_manager

# Multi-bot manager
from piper_tts_service import PiperTTSService
from service_manager import get_service_manager
from stt_service import STTService
from system_monitor import get_system_monitor
from tts_finetune_manager import get_tts_finetune_manager

# Импорты наших сервисов
from voice_clone_service import VoiceCloneService


# vLLM импорт (опциональный - локальная Llama через vLLM)
try:
    from vllm_llm_service import VLLMLLMService

    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    VLLMLLMService = None

# OpenVoice импорт (опциональный - для GPU P104-100)
try:
    from openvoice_service import OpenVoiceService

    OPENVOICE_AVAILABLE = True
except ImportError:
    OPENVOICE_AVAILABLE = False
    OpenVoiceService = None

# Определяем какой LLM backend использовать
LLM_BACKEND = os.getenv("LLM_BACKEND", "gemini").lower()  # "gemini" или "vllm"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== Streaming TTS Manager ==============
class StreamingTTSManager:
    """
    Менеджер для параллельного синтеза TTS во время streaming LLM.

    Архитектура:
    1. Во время streaming chat/completions - накапливаем текст и при завершении
       предложения запускаем синтез в фоновом потоке
    2. Храним синтезированные сегменты в кэше по хэшу полного текста
    3. При запросе /v1/audio/speech - склеиваем готовые сегменты
    """

    def __init__(self, max_cache_size: int = 50, cache_ttl: int = 300):
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl  # секунд

        # Кэш: response_hash -> {"segments": [...], "full_audio": np.array, "timestamp": float}
        self._cache: OrderedDict[str, Dict] = OrderedDict()
        self._cache_lock = threading.Lock()

        # Текущие сессии синтеза: session_id -> {"text": str, "segments": [...], "futures": [...]}
        self._active_sessions: Dict[str, Dict] = {}
        self._session_lock = threading.Lock()

        # Thread pool для фонового синтеза
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tts_")

        # Регулярка для разбиения на предложения
        self._sentence_pattern = re.compile(r"([^.!?]*[.!?]+)")

        logger.info("🎙️ StreamingTTSManager инициализирован")

    def _get_text_hash(self, text: str) -> str:
        """Вычисляет хэш текста для кэширования"""
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def _clean_old_cache(self):
        """Удаляет устаревшие записи из кэша"""
        now = time.time()
        with self._cache_lock:
            keys_to_delete = []
            for key, value in self._cache.items():
                if now - value.get("timestamp", 0) > self.cache_ttl:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del self._cache[key]
                logger.debug(f"🗑️ Удалён устаревший кэш: {key}")

            # Ограничиваем размер кэша
            while len(self._cache) > self.max_cache_size:
                self._cache.popitem(last=False)

    def start_session(self, session_id: str) -> None:
        """Начинает новую сессию streaming синтеза"""
        with self._session_lock:
            self._active_sessions[session_id] = {
                "text_buffer": "",
                "full_text": "",
                "segments": [],  # [(text, audio_data, sample_rate), ...]
                "pending_futures": [],
                "start_time": time.time(),
            }
        logger.info(f"🎬 Начата сессия TTS: {session_id}")

    def add_text_chunk(self, session_id: str, chunk: str, voice_service) -> None:
        """
        Добавляет chunk текста и запускает синтез при завершении предложения.
        Вызывается из streaming LLM response.
        """
        with self._session_lock:
            if session_id not in self._active_sessions:
                return

            session = self._active_sessions[session_id]
            session["text_buffer"] += chunk
            session["full_text"] += chunk

            # Проверяем, есть ли завершённые предложения
            buffer = session["text_buffer"]
            sentences = self._sentence_pattern.findall(buffer)

            if sentences:
                # Синтезируем каждое завершённое предложение
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 3:  # Игнорируем слишком короткие
                        future = self._executor.submit(
                            self._synthesize_segment, sentence, voice_service, session_id
                        )
                        session["pending_futures"].append((sentence, future))
                        logger.info(f"🔄 Запущен синтез: '{sentence[:40]}...'")

                # Удаляем обработанные предложения из буфера
                last_sentence = sentences[-1]
                idx = buffer.rfind(last_sentence) + len(last_sentence)
                session["text_buffer"] = buffer[idx:]

    def _synthesize_segment(self, text: str, voice_service, session_id: str) -> tuple:
        """Синтезирует один сегмент (выполняется в thread pool)"""
        try:
            wav, sr = voice_service.synthesize(
                text=text,
                preset="natural",
                preprocess_text=True,
                split_sentences=False,  # Уже разбили
            )
            logger.info(f"✅ Синтезирован сегмент: '{text[:30]}...'")
            return (text, wav, sr)
        except Exception as e:
            logger.error(f"❌ Ошибка синтеза сегмента: {e}")
            return (text, None, None)

    def finish_session(self, session_id: str, voice_service) -> None:
        """
        Завершает сессию: синтезирует оставшийся текст и кэширует результат.
        """
        with self._session_lock:
            if session_id not in self._active_sessions:
                return

            session = self._active_sessions[session_id]

            # Синтезируем остаток буфера если есть
            remaining = session["text_buffer"].strip()
            if remaining and len(remaining) > 3:
                future = self._executor.submit(
                    self._synthesize_segment, remaining, voice_service, session_id
                )
                session["pending_futures"].append((remaining, future))
                logger.info(f"🔄 Запущен синтез остатка: '{remaining[:40]}...'")

            # Ждём завершения всех futures
            for text, future in session["pending_futures"]:
                try:
                    result = future.result(timeout=60)
                    if result[1] is not None:
                        session["segments"].append(result)
                except Exception as e:
                    logger.error(f"❌ Ошибка получения результата синтеза: {e}")

            # Склеиваем сегменты
            full_text = session["full_text"]
            if session["segments"]:
                self._cache_full_audio(full_text, session["segments"])

            elapsed = time.time() - session["start_time"]
            logger.info(
                f"✅ Сессия {session_id} завершена за {elapsed:.2f}s, "
                f"сегментов: {len(session['segments'])}"
            )

            # Удаляем сессию
            del self._active_sessions[session_id]

    def _cache_full_audio(self, full_text: str, segments: list) -> None:
        """Склеивает сегменты и кэширует полное аудио"""
        if not segments:
            return

        # Получаем sample rate из первого сегмента
        sample_rate = segments[0][2]

        # Склеиваем аудио с небольшими паузами
        pause_samples = int(0.1 * sample_rate)  # 100ms пауза
        pause = np.zeros(pause_samples, dtype=np.float32)

        audio_parts = []
        for text, wav, sr in segments:
            if wav is not None:
                if isinstance(wav, list):
                    wav = np.array(wav, dtype=np.float32)
                audio_parts.append(wav)
                audio_parts.append(pause)

        if audio_parts:
            full_audio = np.concatenate(audio_parts[:-1])  # Убираем последнюю паузу

            text_hash = self._get_text_hash(full_text)
            with self._cache_lock:
                self._cache[text_hash] = {
                    "full_audio": full_audio,
                    "sample_rate": sample_rate,
                    "full_text": full_text,
                    "timestamp": time.time(),
                    "segments_count": len(segments),
                }
                logger.info(
                    f"💾 Закэшировано аудио: {text_hash} ({len(full_audio) / sample_rate:.2f}s)"
                )

            self._clean_old_cache()

    def get_cached_audio(self, text: str) -> Optional[tuple]:
        """
        Получает закэшированное аудио для текста.
        Returns: (audio_data, sample_rate) или None
        """
        text_hash = self._get_text_hash(text)

        with self._cache_lock:
            if text_hash in self._cache:
                cached = self._cache[text_hash]
                logger.info(f"⚡ Cache HIT: {text_hash}")
                return (cached["full_audio"], cached["sample_rate"])

        logger.info(f"❌ Cache MISS: {text_hash}")
        return None

    def get_stats(self) -> dict:
        """Возвращает статистику менеджера"""
        with self._cache_lock:
            cache_size = len(self._cache)
        with self._session_lock:
            active_sessions = len(self._active_sessions)

        return {
            "cache_size": cache_size,
            "active_sessions": active_sessions,
            "max_cache_size": self.max_cache_size,
        }


# Глобальный менеджер streaming TTS
streaming_tts_manager: Optional[StreamingTTSManager] = None

app = FastAPI(title="AI Secretary Orchestrator", version="1.0.0")

# CORS для доступа из браузера
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include modular routers
# NOTE: These routers use the ServiceContainer from app.dependencies
# which is populated in startup_event
app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(services.router)
app.include_router(monitor.router)
app.include_router(faq.router)
app.include_router(stt.router)
app.include_router(llm.router)
app.include_router(tts.router)
app.include_router(chat.router)
app.include_router(telegram.router)
app.include_router(widget.router)
app.include_router(gsm.router)
app.include_router(bot_sales.router)
app.include_router(github_webhook.router)
app.include_router(yoomoney_webhook.router)

# Глобальные сервисы
voice_service: Optional[VoiceCloneService] = None  # XTTS (Лидия) - GPU CC >= 7.0
gulya_voice_service: Optional[VoiceCloneService] = None  # XTTS (Гуля) - GPU CC >= 7.0
piper_service: Optional[PiperTTSService] = None  # Piper (Dmitri, Irina) - CPU
openvoice_service: Optional["OpenVoiceService"] = None  # OpenVoice v2 (Лидия) - GPU CC 6.1+
stt_service: Optional[STTService] = None
llm_service: Optional[LLMService] = None

# Конфигурация текущего голоса
# engine: "xtts" (Лидия/Гуля на GPU CC>=7.0), "piper" (Dmitri/Irina на CPU), "openvoice" (Лидия на GPU CC 6.1+)
# По умолчанию используем Гулю (XTTS) если доступна, иначе Piper
current_voice_config = {
    "engine": "xtts",
    "voice": "gulya",  # gulya / lidia / dmitri / irina / lidia_openvoice
}

# Папка для временных файлов
TEMP_DIR = Path("./temp")
TEMP_DIR.mkdir(exist_ok=True)

# Папка для логов звонков
CALLS_LOG_DIR = Path("./calls_log")
CALLS_LOG_DIR.mkdir(exist_ok=True)


# Helper functions for loading data from database at startup
async def _reload_llm_faq():
    """Загружает FAQ из БД и обновляет LLM сервис."""
    if llm_service and hasattr(llm_service, "reload_faq"):
        faq_dict = await async_faq_manager.get_all()
        llm_service.reload_faq(faq_dict)


async def _reload_voice_presets():
    """Загружает пресеты из БД и обновляет voice сервисы."""
    presets_dict = await async_preset_manager.get_custom()
    for svc in [voice_service, gulya_voice_service]:
        if svc and hasattr(svc, "reload_presets"):
            svc.reload_presets(presets_dict)


async def _auto_start_telegram_bots():
    """Auto-start Telegram bots that have auto_start=True."""
    from db.integration import async_bot_instance_manager
    from multi_bot_manager import MultiBotManager

    try:
        instances = await async_bot_instance_manager.get_auto_start_instances()
        if not instances:
            logger.info("📱 No Telegram bots configured for auto-start")
            return

        manager = MultiBotManager()
        started = 0
        for instance in instances:
            instance_id = instance["id"]
            try:
                result = await manager.start_bot(instance_id)
                if result.get("status") in ["started", "already_running"]:
                    started += 1
                    logger.info(f"📱 Auto-started Telegram bot: {instance['name']}")
                else:
                    logger.warning(f"📱 Failed to auto-start bot {instance_id}: {result}")
            except Exception as e:
                logger.error(f"📱 Error auto-starting bot {instance_id}: {e}")

        if started > 0:
            logger.info(f"📱 Auto-started {started}/{len(instances)} Telegram bots")
    except Exception as e:
        logger.error(f"📱 Error during Telegram bot auto-start: {e}")


class ConversationRequest(BaseModel):
    text: str
    session_id: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    language: str = "ru"


class OpenAISpeechRequest(BaseModel):
    """OpenAI-compatible TTS request for OpenWebUI integration"""

    model: str = "lidia-voice"
    input: str
    voice: str = "lidia"
    response_format: str = "wav"
    speed: float = 1.0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""

    model: str = "gulya-secretary-qwen"  # Format: {persona}-secretary-{backend}
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@app.on_event("startup")
async def startup_event():
    """Инициализация всех сервисов при старте"""
    global \
        voice_service, \
        gulya_voice_service, \
        piper_service, \
        openvoice_service, \
        stt_service, \
        llm_service, \
        streaming_tts_manager

    logger.info("🚀 Запуск AI Secretary Orchestrator")

    # Initialize database first
    await init_database()

    try:
        # Инициализация Piper TTS (Dmitri, Irina) - CPU, загружаем первым
        logger.info("📦 Загрузка Piper TTS Service (CPU)...")
        try:
            piper_service = PiperTTSService()
        except Exception as e:
            logger.warning(f"⚠️ Piper TTS недоступен: {e}")
            piper_service = None

        # Инициализация OpenVoice v2 (Лидия) - GPU CC 6.1+ (P104-100)
        if OPENVOICE_AVAILABLE:
            logger.info("📦 Загрузка OpenVoice TTS Service (GPU CC 6.1+)...")
            try:
                openvoice_service = OpenVoiceService()
                logger.info("✅ OpenVoice v2 загружен (P104-100)")
            except Exception as e:
                logger.warning(f"⚠️ OpenVoice недоступен: {e}")
                openvoice_service = None
        else:
            logger.info("⏭️ OpenVoice не установлен (пропускаем)")
            openvoice_service = None

        # Инициализация XTTS (Гуля) - GPU CC >= 7.0, по умолчанию
        logger.info("📦 Загрузка Voice Clone Service (XTTS - Гуля)...")
        try:
            gulya_voice_service = VoiceCloneService(voice_samples_dir="./Гуля")
            logger.info(
                f"✅ XTTS (Гуля) загружен: {len(gulya_voice_service.voice_samples)} образцов"
            )
        except Exception as e:
            logger.warning(f"⚠️ XTTS (Гуля) недоступен: {e}")
            gulya_voice_service = None

        # Инициализация XTTS (Лидия) - GPU CC >= 7.0, опционально
        logger.info("📦 Загрузка Voice Clone Service (XTTS - Лидия)...")
        try:
            voice_service = VoiceCloneService(voice_samples_dir="./Лидия")
            logger.info(f"✅ XTTS (Лидия) загружен: {len(voice_service.voice_samples)} образцов")
        except Exception as e:
            logger.warning(f"⚠️ XTTS (Лидия) недоступен (требуется GPU CC >= 7.0): {e}")
            voice_service = None

        # Устанавливаем голос по умолчанию
        global current_voice_config
        if gulya_voice_service:
            current_voice_config = {"engine": "xtts", "voice": "gulya"}
            logger.info("🎤 Голос по умолчанию: Гуля (XTTS)")
        elif voice_service:
            current_voice_config = {"engine": "xtts", "voice": "lidia"}
            logger.info("🎤 Голос по умолчанию: Лидия (XTTS)")
        elif piper_service:
            current_voice_config = {"engine": "piper", "voice": "dmitri"}
            logger.info("🎤 Голос по умолчанию: Дмитрий (Piper)")

        # Инициализация LLM Service (vLLM или Gemini)
        if LLM_BACKEND == "vllm" and VLLM_AVAILABLE:
            logger.info("📦 Загрузка vLLM LLM Service (Llama-3.1-8B)...")
            try:
                llm_service = VLLMLLMService()
                if llm_service.is_available():
                    logger.info("✅ vLLM подключен")
                else:
                    logger.warning("⚠️ vLLM не отвечает, пробуем Gemini...")
                    llm_service = LLMService()
            except Exception as e:
                logger.warning(f"⚠️ vLLM недоступен ({e}), используем Gemini")
                llm_service = LLMService()
        else:
            logger.info("📦 Загрузка Gemini LLM Service...")
            llm_service = LLMService()

        # Инициализация Streaming TTS Manager
        logger.info("📦 Инициализация Streaming TTS Manager...")
        streaming_tts_manager = StreamingTTSManager(max_cache_size=50, cache_ttl=300)

        # STT отключён временно - для текстового чата не нужен
        # Модель faster-whisper зависает при загрузке
        logger.info("⏭️ STT отключён (для текстового чата не нужен)")
        stt_service = None

        # Load FAQ and presets from database into services
        logger.info("📦 Загрузка FAQ и пресетов из БД...")
        try:
            await _reload_llm_faq()
            await _reload_voice_presets()
            logger.info("✅ FAQ и пресеты загружены из БД")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки данных из БД: {e}")

        # Check for deprecated legacy JSON files
        legacy_files = [
            ("typical_responses.json", "FAQ"),
            ("custom_presets.json", "TTS presets"),
            ("chat_sessions.json", "chat sessions"),
            ("widget_config.json", "widget config"),
            ("telegram_config.json", "telegram config"),
        ]
        found_legacy = []
        for filename, description in legacy_files:
            if Path(filename).exists():
                found_legacy.append(f"{filename} ({description})")

        if found_legacy:
            logger.warning("=" * 60)
            logger.warning("⚠️  DEPRECATED: Найдены legacy JSON файлы:")
            for f in found_legacy:
                logger.warning(f"    • {f}")
            logger.warning("    Данные теперь хранятся в SQLite (data/secretary.db).")
            logger.warning("    Legacy файлы можно удалить после проверки миграции:")
            logger.warning("    python scripts/migrate_json_to_db.py")
            logger.warning("=" * 60)

        # Populate service container for modular routers
        from app.dependencies import get_container

        container = get_container()
        container.voice_service = voice_service
        container.gulya_voice_service = gulya_voice_service
        container.piper_service = piper_service
        container.openvoice_service = openvoice_service
        container.stt_service = stt_service
        container.llm_service = llm_service
        container.streaming_tts_manager = streaming_tts_manager
        container.current_voice_config = current_voice_config
        logger.info("✅ Service container populated for modular routers")

        # Auto-start Telegram bots that were running before restart
        await _auto_start_telegram_bots()

        logger.info("✅ Основные сервисы загружены успешно")

    except Exception as e:
        logger.error(f"❌ Ошибка инициализации: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down AI Secretary Orchestrator")
    await shutdown_database()
    logger.info("✅ Shutdown complete")


@app.get("/")
async def root():
    """Проверка работоспособности"""
    return {
        "status": "ok",
        "service": "AI Secretary Orchestrator",
        "endpoints": {
            "health": "/health",
            "process_call": "/process_call (POST)",
            "tts": "/tts (POST)",
            "stt": "/stt (POST)",
            "chat": "/chat (POST)",
        },
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья всех сервисов"""
    # Используем llm_service из container (может быть обновлён через router)
    from app.dependencies import get_container

    container = get_container()
    current_llm_service = container.llm_service if container.llm_service else llm_service

    # Определяем тип LLM сервиса
    llm_backend_type = "unknown"
    if current_llm_service:
        if hasattr(current_llm_service, "api_url"):  # vLLM
            llm_backend_type = f"vllm ({current_llm_service.model_name})"
        elif hasattr(current_llm_service, "model_name"):  # Gemini
            llm_backend_type = f"gemini ({current_llm_service.model_name})"

    services_status = {
        "voice_clone_xtts_gulya": gulya_voice_service is not None,
        "voice_clone_xtts_lidia": voice_service is not None,
        "voice_clone_openvoice": openvoice_service is not None,
        "piper_tts": piper_service is not None,
        "stt": stt_service is not None,
        "llm": current_llm_service is not None,
        "llm_backend": llm_backend_type,
        "streaming_tts": streaming_tts_manager is not None,
        "current_voice": current_voice_config,
    }

    # Для health check достаточно любой TTS + llm
    any_tts = (
        services_status["voice_clone_xtts_gulya"]
        or services_status["voice_clone_xtts_lidia"]
        or services_status["voice_clone_openvoice"]
        or services_status["piper_tts"]
    )
    core_ok = any_tts and services_status["llm"]

    # Get database status
    db_status = await get_database_status()

    result = {
        "status": "healthy" if core_ok else "degraded",
        "services": services_status,
        "database": db_status.get("database", {}),
        "timestamp": datetime.now().isoformat(),
    }

    # Добавляем статистику streaming TTS если доступен
    if streaming_tts_manager is not None:
        result["streaming_tts_stats"] = streaming_tts_manager.get_stats()

    return result


def synthesize_with_current_voice(text: str, output_path: str, language: str = "ru"):
    """
    Синтезирует речь с текущим выбранным голосом.
    Учитывает current_voice_config.

    Engines:
    - piper: CPU, быстрый, предобученные голоса (dmitri, irina)
    - openvoice: GPU CC 6.1+, клонирование голоса (lidia_openvoice)
    - xtts: GPU CC >= 7.0, лучшее качество клонирования (gulya, lidia)
    """
    engine = current_voice_config["engine"]
    voice = current_voice_config["voice"]

    if engine == "piper" and piper_service:
        logger.info(f"🎙️ Piper синтез ({voice}): '{text[:40]}...'")
        piper_service.synthesize_to_file(text, output_path, voice=voice)
    elif engine == "openvoice" and openvoice_service:
        logger.info(f"🎙️ OpenVoice синтез (Лидия): '{text[:40]}...'")
        openvoice_service.synthesize_to_file(text, output_path, language=language)
    elif engine == "xtts" and voice == "gulya" and gulya_voice_service:
        logger.info(f"🎙️ XTTS синтез (Гуля): '{text[:40]}...'")
        gulya_voice_service.synthesize_to_file(text, output_path, language=language)
    elif engine == "xtts" and voice == "lidia" and voice_service:
        logger.info(f"🎙️ XTTS синтез (Лидия): '{text[:40]}...'")
        voice_service.synthesize_to_file(text, output_path, language=language)
    elif gulya_voice_service:
        # Fallback to Гуля if available (default)
        logger.info(f"🎙️ XTTS синтез (Гуля fallback): '{text[:40]}...'")
        gulya_voice_service.synthesize_to_file(text, output_path, language=language)
    elif voice_service:
        # Fallback to Лидия if available
        logger.info(f"🎙️ XTTS синтез (Лидия fallback): '{text[:40]}...'")
        voice_service.synthesize_to_file(text, output_path, language=language)
    elif openvoice_service:
        # Fallback to OpenVoice if XTTS not available
        logger.info(f"🎙️ OpenVoice синтез (fallback): '{text[:40]}...'")
        openvoice_service.synthesize_to_file(text, output_path, language=language)
    elif piper_service:
        # Fallback to Piper
        logger.info(f"🎙️ Piper синтез (fallback): '{text[:40]}...'")
        piper_service.synthesize_to_file(text, output_path, voice="irina")
    else:
        raise RuntimeError("No TTS service available")


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Синтез речи с текущим выбранным голосом
    """
    if not voice_service and not piper_service:
        raise HTTPException(status_code=503, detail="No TTS service initialized")

    try:
        # Генерируем уникальное имя файла
        output_file = TEMP_DIR / f"tts_{datetime.now().timestamp()}.wav"

        # Синтезируем с текущим голосом
        synthesize_with_current_voice(
            text=request.text, output_path=str(output_file), language=request.language
        )

        # Возвращаем файл
        return FileResponse(path=output_file, media_type="audio/wav", filename="response.wav")

    except Exception as e:
        logger.error(f"❌ TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Распознавание речи из аудио файла
    """
    if not stt_service:
        raise HTTPException(status_code=503, detail="STT service not initialized")

    try:
        # Сохраняем загруженный файл
        temp_audio = TEMP_DIR / f"stt_{datetime.now().timestamp()}_{audio.filename}"

        with open(temp_audio, "wb") as f:
            content = await audio.read()
            f.write(content)

        # Распознаем
        result = stt_service.transcribe(temp_audio, language="ru")

        # Удаляем временный файл
        temp_audio.unlink()

        return {
            "text": result["text"],
            "language": result["language"],
            "segments_count": len(result.get("segments", [])),
        }

    except Exception as e:
        logger.error(f"❌ STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: ConversationRequest):
    """
    Получить ответ от LLM (Gemini)
    """
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")

    try:
        response = llm_service.generate_response(request.text)

        return {"response": response, "session_id": request.session_id}

    except Exception as e:
        logger.error(f"❌ LLM Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process_call")
async def process_call(audio: UploadFile = File(...)):
    """
    Полный цикл обработки звонка:
    1. STT - распознавание речи
    2. LLM - генерация ответа
    3. TTS - синтез речи

    Возвращает аудио с ответом секретаря
    """
    call_id = f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    logger.info(f"📞 Обработка звонка {call_id}")

    try:
        # 1. Сохраняем входящий аудио
        input_audio = CALLS_LOG_DIR / f"{call_id}_input.wav"
        with open(input_audio, "wb") as f:
            content = await audio.read()
            f.write(content)

        # 2. Распознаем речь (STT)
        logger.info(f"🎧 STT для {call_id}")
        stt_result = stt_service.transcribe(input_audio, language="ru")
        recognized_text = stt_result["text"]
        logger.info(f"📝 Распознано: {recognized_text}")

        # Сохраняем транскрипцию
        with open(CALLS_LOG_DIR / f"{call_id}_transcript.txt", "w") as f:
            f.write(f"USER: {recognized_text}\n")

        # 3. Генерируем ответ (LLM)
        logger.info(f"🤖 LLM для {call_id}")
        llm_response = llm_service.generate_response(recognized_text)
        logger.info(f"💬 Ответ: {llm_response}")

        # Дополняем транскрипцию
        with open(CALLS_LOG_DIR / f"{call_id}_transcript.txt", "a") as f:
            f.write(f"ASSISTANT: {llm_response}\n")

        # 4. Синтезируем ответ (TTS)
        logger.info(f"🎙️  TTS для {call_id}")
        output_audio = CALLS_LOG_DIR / f"{call_id}_output.wav"
        voice_service.synthesize_to_file(
            text=llm_response, output_path=str(output_audio), language="ru"
        )

        logger.info(f"✅ Звонок {call_id} обработан")

        # 5. Возвращаем аудио ответ
        return FileResponse(
            path=output_audio,
            media_type="audio/wav",
            filename=f"{call_id}_response.wav",
            headers={
                "X-Call-ID": call_id,
                "X-Recognized-Text": recognized_text,
                "X-Response-Text": llm_response,
            },
        )

    except Exception as e:
        logger.error(f"❌ Ошибка обработки звонка {call_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset_conversation")
async def reset_conversation():
    """Сброс истории диалога"""
    if llm_service:
        llm_service.reset_conversation()
        return {"status": "ok", "message": "Conversation history reset"}
    raise HTTPException(status_code=503, detail="LLM service not initialized")


# ============== OpenAI-Compatible Endpoints for OpenWebUI ==============


@app.get("/v1/models")
@app.get("/v1/models/")
async def list_models():
    """OpenAI-compatible models list for OpenWebUI"""
    # Определяем backend и суффикс для имени модели
    if llm_service and hasattr(llm_service, "api_url"):
        # vLLM backend - проверяем модель
        model_name = getattr(llm_service, "model_name", "unknown")
        if model_name == "lydia" or "qwen" in model_name.lower():
            backend_suffix = "qwen"
            backend_desc = "Qwen2.5-7B + LoRA"
        elif "llama" in model_name.lower():
            backend_suffix = "llama"
            backend_desc = "Llama-3.1-8B"
        else:
            backend_suffix = "vllm"
            backend_desc = model_name
    else:
        backend_suffix = "gemini"
        backend_desc = "Gemini"

    return {
        "object": "list",
        "data": [
            {
                "id": f"gulya-secretary-{backend_suffix}",
                "object": "model",
                "created": 1700000000,
                "owned_by": "ai-secretary",
                "permission": [],
                "root": f"gulya-secretary-{backend_suffix}",
                "parent": None,
                "description": f"Гуля - цифровой секретарь ({backend_desc})",
            },
            {
                "id": f"lidia-secretary-{backend_suffix}",
                "object": "model",
                "created": 1700000000,
                "owned_by": "ai-secretary",
                "permission": [],
                "root": f"lidia-secretary-{backend_suffix}",
                "parent": None,
                "description": f"Лидия - цифровой секретарь ({backend_desc})",
            },
        ],
    }


@app.get("/v1/voices")
async def list_voices():
    """List available voices"""
    voices = []
    if gulya_voice_service:
        voices.append({"voice_id": "gulya", "name": "Гуля", "language": "ru"})
    if voice_service:
        voices.append({"voice_id": "lidia", "name": "Лидия", "language": "ru"})
    if piper_service:
        voices.append({"voice_id": "dmitri", "name": "Дмитрий", "language": "ru"})
        voices.append({"voice_id": "irina", "name": "Ирина", "language": "ru"})
    return {"voices": voices}


@app.post("/v1/audio/speech")
async def openai_speech(request: OpenAISpeechRequest):
    """
    OpenAI-compatible TTS endpoint for OpenWebUI integration
    POST /v1/audio/speech

    Оптимизация: сначала проверяет кэш streaming TTS manager.
    Если аудио уже было предсинтезировано во время streaming LLM - возвращает мгновенно.
    """
    if not voice_service and not piper_service:
        raise HTTPException(status_code=503, detail="No TTS service initialized")

    try:
        output_file = TEMP_DIR / f"speech_{datetime.now().timestamp()}.wav"
        start_time = time.time()

        # Проверяем кэш streaming TTS (только для XTTS)
        cached_audio = None
        if current_voice_config["engine"] == "xtts" and streaming_tts_manager is not None:
            cached_audio = streaming_tts_manager.get_cached_audio(request.input)

        if cached_audio is not None:
            # Cache HIT - используем предсинтезированное аудио
            audio_data, sample_rate = cached_audio
            sf.write(str(output_file), audio_data, sample_rate)
            elapsed = time.time() - start_time
            logger.info(f"⚡ TTS из кэша за {elapsed:.3f}s (vs ~5-10s обычный синтез)")
        else:
            # Cache MISS - синтезируем с текущим голосом
            synthesize_with_current_voice(
                text=request.input, output_path=str(output_file), language="ru"
            )
            elapsed = time.time() - start_time
            logger.info(f"🎙️ TTS синтезирован за {elapsed:.2f}s")

        return FileResponse(path=output_file, media_type="audio/wav", filename="speech.wav")

    except Exception as e:
        logger.error(f"❌ OpenAI TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completions endpoint for OpenWebUI
    Supports both streaming and non-streaming responses.
    При streaming - запускает фоновый синтез TTS по предложениям.
    """
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")

    logger.info(
        f"💬 Chat completions request: stream={request.stream}, messages={len(request.messages)}"
    )

    # Конвертируем Pydantic модели в dict
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    if request.stream:
        # Streaming response (SSE) с фоновым синтезом TTS
        async def generate_stream():
            created = int(time.time())
            chunk_id = f"chatcmpl-{created}"
            session_id = f"tts-{created}"

            # Начинаем сессию streaming TTS если сервисы доступны
            use_streaming_tts = streaming_tts_manager is not None and voice_service is not None

            if use_streaming_tts:
                streaming_tts_manager.start_session(session_id)
                logger.info(f"🎬 Streaming TTS активирован для сессии {session_id}")

            try:
                for text_chunk in llm_service.generate_response_from_messages(
                    messages, stream=True
                ):
                    # Отправляем chunk клиенту
                    chunk_data = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [
                            {"index": 0, "delta": {"content": text_chunk}, "finish_reason": None}
                        ],
                    }
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                    # Параллельно добавляем chunk в streaming TTS manager
                    if use_streaming_tts and text_chunk:
                        streaming_tts_manager.add_text_chunk(session_id, text_chunk, voice_service)

                # Final chunk
                final_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

                # Завершаем сессию TTS (склеивает и кэширует аудио)
                if use_streaming_tts:
                    # Запускаем в отдельном потоке чтобы не блокировать response
                    threading.Thread(
                        target=streaming_tts_manager.finish_session,
                        args=(session_id, voice_service),
                        daemon=True,
                    ).start()

            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                error_chunk = {"error": {"message": str(e), "type": "server_error"}}
                yield f"data: {json.dumps(error_chunk)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    else:
        # Non-streaming response
        try:
            response_text = llm_service.generate_response_from_messages(messages, stream=False)

            # Consume generator if it returns one
            if hasattr(response_text, "__iter__") and not isinstance(response_text, str):
                response_text = "".join(response_text)

            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        except Exception as e:
            logger.error(f"❌ Chat completions error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============== Admin Web Interface ==============
# Vue 3 admin panel served from /admin (see Static Files section below)


# ============== Admin API Endpoints ==============

# ============== Auth Endpoints ==============


@app.post("/admin/auth/login", response_model=LoginResponse)
async def admin_login(request: LoginRequest):
    """
    Authenticate user and return JWT token.

    Default credentials: admin / admin
    Set ADMIN_USERNAME and ADMIN_PASSWORD_HASH env vars for production.
    """
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token, expires_in = create_access_token(user.username, user.role)

    # Audit log
    await async_audit_logger.log(
        action="login", resource="auth", user_id=user.username, details={"role": user.role}
    )

    return LoginResponse(access_token=token, token_type="bearer", expires_in=expires_in)


@app.get("/admin/auth/me")
async def admin_get_current_user(user: User = Depends(get_current_user)):
    """Get current authenticated user info"""
    return {"username": user.username, "role": user.role}


@app.get("/admin/auth/status")
async def admin_auth_status():
    """Get authentication configuration status"""
    return get_auth_status()


# ============== Admin Models ==============


class AdminTTSPresetRequest(BaseModel):
    """Запрос на изменение пресета TTS"""

    preset: str  # warm, calm, energetic, natural, neutral


class AdminLLMPromptRequest(BaseModel):
    """Запрос на изменение системного промпта"""

    prompt: str


class AdminLLMModelRequest(BaseModel):
    """Запрос на изменение модели LLM"""

    model: str  # gemini-2.5-flash, gemini-2.5-pro


class AdminTTSTestRequest(BaseModel):
    """Запрос на тестовый синтез"""

    text: str
    preset: str = "natural"


@app.get("/admin/status")
async def admin_status():
    """Полный статус системы для админки"""
    import torch

    status = {
        "orchestrator": "running",
        "services": {
            "voice_clone": voice_service is not None,
            "llm": llm_service is not None,
            "stt": stt_service is not None,
            "streaming_tts": streaming_tts_manager is not None,
            "piper_tts": piper_service is not None,
        },
        "gpu": None,
        "streaming_tts_stats": None,
        "llm_config": None,
        "tts_config": None,
    }

    # GPU информация
    if torch.cuda.is_available():
        gpu_info = []
        for i in range(torch.cuda.device_count()):
            try:
                name = torch.cuda.get_device_name(i)
                total = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                gpu_info.append(
                    {
                        "id": i,
                        "name": name,
                        "total_gb": round(total, 2),
                        "used_gb": round(allocated, 2),
                    }
                )
            except Exception:
                pass
        status["gpu"] = gpu_info

    # Streaming TTS статистика
    if streaming_tts_manager:
        status["streaming_tts_stats"] = streaming_tts_manager.get_stats()

    # LLM конфигурация
    if llm_service:
        if hasattr(llm_service, "get_config"):
            status["llm_config"] = llm_service.get_config()
        else:
            # Для vLLM и других сервисов без get_config
            status["llm_config"] = {
                "model_name": getattr(llm_service, "model_name", "unknown"),
                "api_url": getattr(llm_service, "api_url", None),
                "backend": "vllm" if hasattr(llm_service, "api_url") else "gemini",
            }

    # TTS конфигурация
    xtts_svc = gulya_voice_service or voice_service
    if xtts_svc:
        status["tts_config"] = {
            "device": xtts_svc.device,
            "default_preset": xtts_svc.default_preset,
            "samples_count": len(xtts_svc.voice_samples),
            "cache_dir": str(xtts_svc.cache_dir),
        }

    return status


@app.get("/admin/llm/prompt")
async def admin_get_llm_prompt():
    """Получить текущий системный промпт LLM"""
    if llm_service:
        persona = getattr(llm_service, "current_persona", None) or os.getenv(
            "SECRETARY_PERSONA", "gulya"
        )
        return {
            "prompt": llm_service.system_prompt,
            "model": llm_service.model_name,
            "persona": persona,
        }
    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.post("/admin/llm/prompt")
async def admin_set_llm_prompt(request: AdminLLMPromptRequest):
    """Установить новый системный промпт LLM"""
    if llm_service:
        llm_service.set_system_prompt(request.prompt)
        return {
            "status": "ok",
            "prompt": request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
        }
    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.get("/admin/llm/model")
async def admin_get_llm_model():
    """Получить текущую модель LLM"""
    if llm_service:
        return {"model": llm_service.model_name}
    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.post("/admin/llm/model")
async def admin_set_llm_model(request: AdminLLMModelRequest):
    """Изменить модель LLM"""
    allowed_models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

    if request.model not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестная модель: {request.model}. Доступные: {allowed_models}",
        )

    if llm_service:
        try:
            llm_service.set_model(request.model)
            return {"status": "ok", "model": request.model}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.delete("/admin/llm/history")
async def admin_clear_llm_history():
    """Очистить историю диалога LLM"""
    if llm_service:
        count = len(llm_service.conversation_history)
        llm_service.reset_conversation()
        return {"status": "ok", "cleared_messages": count}
    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.get("/admin/llm/history")
async def admin_get_llm_history():
    """Получить историю диалога LLM"""
    if llm_service:
        return {
            "history": llm_service.conversation_history,
            "count": len(llm_service.conversation_history),
        }
    raise HTTPException(status_code=503, detail="LLM service not initialized")


# ============== Voice Selection API ==============


class AdminVoiceRequest(BaseModel):
    voice: str  # gulya / lidia / dmitri / irina


@app.get("/admin/voices")
async def admin_get_voices():
    """Получить список всех доступных голосов"""
    voices = []

    # XTTS голос (Гуля) - требует GPU CC >= 7.0 (по умолчанию)
    if gulya_voice_service:
        voices.append(
            {
                "id": "gulya",
                "name": "Гуля (XTTS)",
                "engine": "xtts",
                "description": "Клонированный голос Гули (XTTS v2, GPU CC >= 7.0)",
                "available": True,
                "samples_count": len(gulya_voice_service.voice_samples),
                "default": True,
            }
        )

    # XTTS голос (Лидия) - требует GPU CC >= 7.0
    if voice_service:
        voices.append(
            {
                "id": "lidia",
                "name": "Лидия (XTTS)",
                "engine": "xtts",
                "description": "Клонированный голос Лидии (XTTS v2, GPU CC >= 7.0)",
                "available": True,
                "samples_count": len(voice_service.voice_samples),
            }
        )

    # OpenVoice голос (Лидия) - работает на GPU CC 6.1+
    if openvoice_service:
        voices.append(
            {
                "id": "lidia_openvoice",
                "name": "Лидия (OpenVoice)",
                "engine": "openvoice",
                "description": "Клонированный голос (OpenVoice v2, GPU CC 6.1+)",
                "available": True,
                "samples_count": len(openvoice_service.voice_samples)
                if openvoice_service.voice_samples
                else 0,
            }
        )

    # Piper голоса (CPU)
    if piper_service:
        piper_voices = piper_service.get_available_voices()
        for voice_id, info in piper_voices.items():
            voices.append(
                {
                    "id": voice_id,
                    "name": info["name"],
                    "engine": "piper",
                    "description": info["description"],
                    "available": info["available"],
                }
            )

    return {
        "voices": voices,
        "current": current_voice_config,
    }


@app.get("/admin/voice")
async def admin_get_current_voice():
    """Получить текущий выбранный голос"""
    return current_voice_config


@app.post("/admin/voice")
async def admin_set_voice(request: AdminVoiceRequest):
    """Установить активный голос"""
    global current_voice_config

    voice_id = request.voice.lower()

    # Проверяем доступность голоса
    if voice_id == "gulya":
        if not gulya_voice_service:
            raise HTTPException(
                status_code=503, detail="XTTS service (Гуля) not available (requires GPU CC >= 7.0)"
            )
        current_voice_config = {"engine": "xtts", "voice": "gulya"}
        logger.info("🎤 Голос изменён на: Гуля (XTTS)")

    elif voice_id == "lidia":
        if not voice_service:
            raise HTTPException(
                status_code=503,
                detail="XTTS service (Лидия) not available (requires GPU CC >= 7.0)",
            )
        current_voice_config = {"engine": "xtts", "voice": "lidia"}
        logger.info("🎤 Голос изменён на: Лидия (XTTS)")

    elif voice_id == "lidia_openvoice":
        if not openvoice_service:
            raise HTTPException(status_code=503, detail="OpenVoice service not available")
        current_voice_config = {"engine": "openvoice", "voice": "lidia_openvoice"}
        logger.info("🎤 Голос изменён на: Лидия (OpenVoice)")

    elif voice_id in ["dmitri", "irina"]:
        if not piper_service:
            raise HTTPException(status_code=503, detail="Piper TTS service not available")
        piper_voices = piper_service.get_available_voices()
        if voice_id not in piper_voices or not piper_voices[voice_id]["available"]:
            raise HTTPException(status_code=400, detail=f"Voice model not found: {voice_id}")
        current_voice_config = {"engine": "piper", "voice": voice_id}
        logger.info(f"🎤 Голос изменён на: {piper_voices[voice_id]['name']} (Piper)")

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown voice: {voice_id}. Available: gulya, lidia, lidia_openvoice, dmitri, irina",
        )

    # Sync with service container for modular routers
    from app.dependencies import get_container

    container = get_container()
    container.current_voice_config = current_voice_config

    return {"status": "ok", **current_voice_config}


@app.post("/admin/voice/test")
async def admin_test_voice(request: AdminVoiceRequest):
    """Тестовый синтез выбранным голосом"""
    voice_id = request.voice.lower()
    test_text = "Здравствуйте! Это тестовое сообщение для проверки голоса."

    output_path = TEMP_DIR / f"voice_test_{voice_id}_{int(time.time())}.wav"

    try:
        if voice_id == "gulya":
            if not gulya_voice_service:
                raise HTTPException(
                    status_code=503, detail="XTTS (Гуля) not available (requires GPU CC >= 7.0)"
                )
            gulya_voice_service.synthesize_to_file(test_text, str(output_path), preset="natural")

        elif voice_id == "lidia":
            if not voice_service:
                raise HTTPException(
                    status_code=503, detail="XTTS (Лидия) not available (requires GPU CC >= 7.0)"
                )
            voice_service.synthesize_to_file(test_text, str(output_path), preset="natural")

        elif voice_id == "lidia_openvoice":
            if not openvoice_service:
                raise HTTPException(status_code=503, detail="OpenVoice not available")
            openvoice_service.synthesize_to_file(test_text, str(output_path), language="ru")

        elif voice_id in ["dmitri", "irina"]:
            if not piper_service:
                raise HTTPException(status_code=503, detail="Piper not available")
            piper_service.synthesize_to_file(test_text, str(output_path), voice=voice_id)

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown voice: {voice_id}. Available: gulya, lidia, lidia_openvoice, dmitri, irina",
            )

        return FileResponse(output_path, media_type="audio/wav", filename=f"test_{voice_id}.wav")

    except Exception as e:
        logger.error(f"❌ Ошибка тестового синтеза: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_current_tts_service():
    """Возвращает текущий TTS сервис и параметры на основе конфигурации"""
    engine = current_voice_config["engine"]
    voice = current_voice_config["voice"]

    if engine == "xtts" and voice == "gulya":
        return gulya_voice_service, {"preset": "natural"}
    elif engine == "xtts" and voice == "lidia":
        return voice_service, {"preset": "natural"}
    elif engine == "piper":
        return piper_service, {"voice": voice}
    else:
        # Default to gulya if available
        return gulya_voice_service or voice_service, {"preset": "natural"}


# ============== Extended Admin API Endpoints ==============


# Pydantic models for new endpoints
class AdminBackendRequest(BaseModel):
    backend: str  # "vllm", "gemini", or "cloud:{provider_id}"
    stop_unused: bool = False  # Остановить неиспользуемый сервис (vLLM) для освобождения GPU


class CloudProviderCreate(BaseModel):
    """Create cloud LLM provider"""

    name: str
    provider_type: str  # gemini, kimi, openai, claude, deepseek, custom
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: str = ""
    enabled: bool = True
    is_default: bool = False
    config: Optional[Dict] = None
    description: Optional[str] = None


class CloudProviderUpdate(BaseModel):
    """Update cloud LLM provider"""

    name: Optional[str] = None
    provider_type: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    config: Optional[Dict] = None
    description: Optional[str] = None


class AdminPersonaRequest(BaseModel):
    persona: str  # "gulya" or "lidia"


class AdminLLMParamsRequest(BaseModel):
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    repetition_penalty: Optional[float] = None


class AdminXTTSParamsRequest(BaseModel):
    temperature: Optional[float] = None
    repetition_penalty: Optional[float] = None
    top_k: Optional[int] = None
    top_p: Optional[float] = None
    speed: Optional[float] = None
    gpt_cond_len: Optional[int] = None
    gpt_cond_chunk_len: Optional[int] = None


class AdminPiperParamsRequest(BaseModel):
    speed: float = 1.0


class AdminCustomPresetRequest(BaseModel):
    name: str
    params: dict


class AdminFAQRequest(BaseModel):
    trigger: str
    response: str


class AdminFAQTestRequest(BaseModel):
    text: str


class AdminWidgetConfigRequest(BaseModel):
    enabled: bool = True
    title: str = "AI Ассистент"
    greeting: str = "Здравствуйте! Компания Шаервэй Ди-Иджитал, чем могу помочь?"
    placeholder: str = "Введите сообщение..."
    primary_color: str = "#6366f1"
    position: str = "right"  # "left" or "right"
    allowed_domains: List[str] = []
    tunnel_url: str = ""


class AdminTelegramConfigRequest(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    api_url: str = "http://localhost:8002"
    allowed_users: List[int] = []
    admin_users: List[int] = []
    welcome_message: str = "Здравствуйте! Я AI-ассистент компании Шаервэй. Чем могу помочь?"
    unauthorized_message: str = "Извините, у вас нет доступа к этому боту."
    error_message: str = "Произошла ошибка. Попробуйте позже."
    typing_enabled: bool = True


class AdminFinetuneConfigRequest(BaseModel):
    lora_rank: Optional[int] = None
    lora_alpha: Optional[int] = None
    batch_size: Optional[int] = None
    gradient_accumulation_steps: Optional[int] = None
    learning_rate: Optional[float] = None
    num_epochs: Optional[int] = None
    max_seq_length: Optional[int] = None
    output_dir: Optional[str] = None


class AdminAdapterRequest(BaseModel):
    adapter: str


class AdminAuditQueryRequest(BaseModel):
    action: Optional[str] = None
    resource: Optional[str] = None
    user_id: Optional[str] = None
    from_date: Optional[str] = None  # ISO format
    to_date: Optional[str] = None  # ISO format
    limit: int = 100
    offset: int = 0


# ============== Chat Models & Manager ==============


class ChatMessageModel(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    edited: bool = False


class ChatSessionModel(BaseModel):
    id: str
    title: str
    messages: List[ChatMessageModel]
    system_prompt: Optional[str] = None
    created: str
    updated: str


class CreateSessionRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None


class LLMOverrideConfig(BaseModel):
    llm_backend: Optional[str] = None  # "vllm", "gemini", or "cloud:provider-id"
    system_prompt: Optional[str] = None
    llm_params: Optional[dict] = None


class SendMessageRequest(BaseModel):
    content: str
    llm_override: Optional[LLMOverrideConfig] = None


class EditMessageRequest(BaseModel):
    content: str


# ============== Services Endpoints ==============


@app.get("/admin/services/status")
async def admin_services_status():
    """Получить статус всех сервисов"""
    manager = get_service_manager()
    status = manager.get_all_status()

    # Добавляем статус внутренних сервисов из orchestrator
    status["services"]["xtts_gulya"]["is_running"] = gulya_voice_service is not None
    status["services"]["xtts_lidia"]["is_running"] = voice_service is not None
    status["services"]["piper"]["is_running"] = piper_service is not None
    status["services"]["openvoice"]["is_running"] = openvoice_service is not None
    status["services"]["orchestrator"]["is_running"] = True

    return status


@app.post("/admin/services/{service}/start")
async def admin_start_service(service: str):
    """Запустить сервис"""
    manager = get_service_manager()
    return await manager.start_service(service)


@app.post("/admin/services/{service}/stop")
async def admin_stop_service(service: str):
    """Остановить сервис"""
    manager = get_service_manager()
    return await manager.stop_service(service)


@app.post("/admin/services/{service}/restart")
async def admin_restart_service(service: str):
    """Перезапустить сервис"""
    manager = get_service_manager()
    return await manager.restart_service(service)


@app.post("/admin/services/start-all")
async def admin_start_all_services():
    """Запустить все внешние сервисы"""
    manager = get_service_manager()
    results = {}
    for service in ["vllm"]:  # Только внешние сервисы
        results[service] = await manager.start_service(service)
    return {"status": "ok", "results": results}


@app.post("/admin/services/stop-all")
async def admin_stop_all_services():
    """Остановить все внешние сервисы"""
    manager = get_service_manager()
    results = {}
    for service in ["vllm"]:
        results[service] = await manager.stop_service(service)
    return {"status": "ok", "results": results}


# ============== Logs Endpoints ==============


@app.get("/admin/logs")
async def admin_list_logs():
    """Список доступных логов"""
    manager = get_service_manager()
    return {"logs": manager.get_available_logs()}


@app.get("/admin/logs/{logfile}")
async def admin_read_log(
    logfile: str, lines: int = 100, offset: int = 0, search: Optional[str] = None
):
    """Прочитать лог файл"""
    manager = get_service_manager()
    return manager.read_log(logfile, lines=lines, offset=offset, search=search)


@app.get("/admin/logs/stream/{logfile}")
async def admin_stream_log(logfile: str):
    """SSE streaming логов"""
    manager = get_service_manager()

    async def generate():
        async for data in manager.stream_log(logfile):
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# ============== LLM Enhanced Endpoints ==============


@app.get("/admin/llm/backend")
async def admin_get_llm_backend():
    """Получить текущий LLM backend"""
    if llm_service:
        # Detect backend type
        if isinstance(llm_service, CloudLLMService):
            backend = f"cloud:{llm_service.provider_id}"
        elif hasattr(llm_service, "api_url"):
            backend = "vllm"
        else:
            backend = "gemini"

        return {
            "backend": backend,
            "model": getattr(llm_service, "model_name", "unknown"),
            "api_url": getattr(llm_service, "api_url", None),
            "provider_type": getattr(llm_service, "provider_type", None),
        }
    return {"backend": "none", "error": "LLM service not initialized"}


@app.get("/admin/llm/models")
async def admin_get_llm_models():
    """
    Получить список доступных моделей vLLM и текущую модель.
    Возвращает информацию о Qwen, Llama, DeepSeek и других моделях.
    """
    from vllm_llm_service import AVAILABLE_MODELS

    result = {
        "available_models": AVAILABLE_MODELS,
        "current_model": None,
        "loaded_models": [],
        "backend": "none",
    }

    if llm_service:
        is_vllm = hasattr(llm_service, "api_url")
        result["backend"] = "vllm" if is_vllm else "gemini"

        if is_vllm and hasattr(llm_service, "get_current_model_info"):
            result["current_model"] = llm_service.get_current_model_info()
            result["loaded_models"] = llm_service.get_loaded_models()
        elif not is_vllm:
            # Gemini backend
            result["current_model"] = {
                "id": "gemini",
                "name": getattr(llm_service, "model_name", "gemini-2.0-flash"),
                "description": "Google Gemini API",
                "available": True,
            }

    return result


@app.post("/admin/llm/backend")
async def admin_set_llm_backend(
    request: AdminBackendRequest, user: User = Depends(get_current_user)
):
    """Переключить LLM backend с горячей перезагрузкой сервиса"""
    global LLM_BACKEND, llm_service

    # Check if it's a cloud provider
    if request.backend.startswith("cloud:"):
        provider_id = request.backend.split(":", 1)[1]
        return await _switch_to_cloud_provider(provider_id, request.stop_unused, user)

    if request.backend not in ["vllm", "gemini"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid backend. Use 'vllm', 'gemini', or 'cloud:{provider_id}'",
        )

    # Проверяем текущий бэкенд
    current_backend = "vllm" if (llm_service and hasattr(llm_service, "api_url")) else "gemini"
    if request.backend == current_backend:
        return {
            "status": "ok",
            "backend": request.backend,
            "message": f"Уже используется {request.backend}",
        }

    manager = get_service_manager()
    stop_vllm = request.stop_unused if hasattr(request, "stop_unused") else False

    try:
        if request.backend == "vllm":
            # Переключение на vLLM
            logger.info("🔄 Переключение на vLLM...")

            # Проверяем, запущен ли vLLM
            vllm_status = manager.get_service_status("vllm")

            if not vllm_status.get("is_running"):
                # Запускаем vLLM
                logger.info("🚀 Запуск vLLM...")
                start_result = await manager.start_service("vllm")
                if start_result.get("status") != "ok":
                    raise HTTPException(
                        status_code=503,
                        detail=f"Не удалось запустить vLLM: {start_result.get('message', 'Unknown error')}",
                    )

                # Ждём готовности vLLM (до 120 секунд)
                logger.info("⏳ Ожидание готовности vLLM...")
                import httpx

                # Нормализуем URL (удаляем trailing /v1)
                vllm_url = os.getenv("VLLM_API_URL", "http://localhost:11434").rstrip("/")
                if vllm_url.endswith("/v1"):
                    vllm_url = vllm_url[:-3]

                for i in range(60):  # 60 * 2 = 120 секунд
                    await asyncio.sleep(2)
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(f"{vllm_url}/v1/models", timeout=5.0)
                            if resp.status_code == 200:
                                logger.info(f"✅ vLLM готов (попытка {i + 1})")
                                break
                    except Exception:
                        pass
                else:
                    raise HTTPException(
                        status_code=503, detail=f"vLLM не стал доступен за 120 секунд ({vllm_url})"
                    )

            # Создаём новый vLLM сервис
            if VLLMLLMService is None:
                raise HTTPException(status_code=503, detail="VLLMLLMService не доступен")

            new_service = VLLMLLMService()
            if not new_service.is_available():
                raise HTTPException(status_code=503, detail="vLLM запущен, но не отвечает на API")

            llm_service = new_service
            LLM_BACKEND = "vllm"
            os.environ["LLM_BACKEND"] = "vllm"

            logger.info("✅ Переключено на vLLM")

            # Audit log
            await async_audit_logger.log(
                action="update",
                resource="config",
                resource_id="llm_backend",
                user_id=user.username,
                details={"backend": "vllm", "model": getattr(llm_service, "model_name", "unknown")},
            )

            return {
                "status": "ok",
                "backend": "vllm",
                "model": getattr(llm_service, "model_name", "unknown"),
                "message": "Переключено на vLLM",
            }

        else:
            # Переключение на Gemini
            logger.info("🔄 Переключение на Gemini...")

            new_service = LLMService()
            llm_service = new_service
            LLM_BACKEND = "gemini"
            os.environ["LLM_BACKEND"] = "gemini"

            # Опционально останавливаем vLLM для освобождения GPU
            if stop_vllm:
                vllm_status = manager.get_service_status("vllm")
                if vllm_status.get("is_running"):
                    logger.info("🛑 Останавливаем vLLM для освобождения GPU...")
                    await manager.stop_service("vllm")

            logger.info("✅ Переключено на Gemini")

            # Audit log
            await async_audit_logger.log(
                action="update",
                resource="config",
                resource_id="llm_backend",
                user_id=user.username,
                details={
                    "backend": "gemini",
                    "model": getattr(llm_service, "model_name", "unknown"),
                },
            )

            return {
                "status": "ok",
                "backend": "gemini",
                "model": getattr(llm_service, "model_name", "unknown"),
                "message": "Переключено на Gemini" + (" (vLLM остановлен)" if stop_vllm else ""),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка переключения бэкенда: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _switch_to_cloud_provider(provider_id: str, stop_unused: bool, user: User):
    """Helper function to switch to a cloud provider"""
    global LLM_BACKEND, llm_service

    provider_config = await async_cloud_provider_manager.get_provider_with_key(provider_id)
    if not provider_config:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")

    if not provider_config.get("enabled"):
        raise HTTPException(status_code=400, detail=f"Provider {provider_id} is disabled")

    if not provider_config.get("api_key"):
        raise HTTPException(
            status_code=400, detail=f"Provider {provider_id} has no API key configured"
        )

    try:
        new_service = CloudLLMService(provider_config)
        if not new_service.is_available():
            raise HTTPException(status_code=503, detail=f"Provider {provider_id} is not responding")

        llm_service = new_service
        LLM_BACKEND = f"cloud:{provider_id}"
        os.environ["LLM_BACKEND"] = LLM_BACKEND

        # Optionally stop vLLM to free GPU
        if stop_unused:
            manager = get_service_manager()
            vllm_status = manager.get_service_status("vllm")
            if vllm_status.get("is_running"):
                logger.info("🛑 Stopping vLLM to free GPU memory...")
                await manager.stop_service("vllm")

        logger.info(f"✅ Switched to cloud provider: {provider_config.get('name')}")

        # Audit log
        await async_audit_logger.log(
            action="update",
            resource="config",
            resource_id="llm_backend",
            user_id=user.username,
            details={
                "backend": f"cloud:{provider_id}",
                "provider_type": provider_config.get("provider_type"),
                "model": provider_config.get("model_name"),
            },
        )

        return {
            "status": "ok",
            "backend": f"cloud:{provider_id}",
            "provider_id": provider_id,
            "provider_type": provider_config.get("provider_type"),
            "model": provider_config.get("model_name"),
            "message": f"Switched to cloud provider: {provider_config.get('name')}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error switching to cloud provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Cloud LLM Providers API ==============


@app.get("/admin/llm/providers")
async def admin_list_cloud_providers(enabled_only: bool = False):
    """List all cloud LLM providers"""
    providers = await async_cloud_provider_manager.list_providers(enabled_only)
    return {
        "providers": providers,
        "provider_types": PROVIDER_TYPES,
    }


@app.get("/admin/llm/providers/{provider_id}")
async def admin_get_cloud_provider(
    provider_id: str, include_key: bool = False, user: User = Depends(get_current_user)
):
    """Get cloud provider by ID"""
    if include_key:
        provider = await async_cloud_provider_manager.get_provider_with_key(provider_id)
    else:
        provider = await async_cloud_provider_manager.get_provider(provider_id)

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"provider": provider}


@app.post("/admin/llm/providers")
async def admin_create_cloud_provider(
    data: CloudProviderCreate, user: User = Depends(get_current_user)
):
    """Create new cloud LLM provider"""
    try:
        provider = await async_cloud_provider_manager.create_provider(
            name=data.name,
            provider_type=data.provider_type,
            api_key=data.api_key,
            base_url=data.base_url,
            model_name=data.model_name,
            enabled=data.enabled,
            is_default=data.is_default,
            config=data.config,
            description=data.description,
        )

        # Audit log
        await async_audit_logger.log(
            action="create",
            resource="cloud_provider",
            resource_id=provider["id"],
            user_id=user.username,
            details={"name": data.name, "provider_type": data.provider_type},
        )

        return {"status": "ok", "provider": provider}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/admin/llm/providers/{provider_id}")
async def admin_update_cloud_provider(
    provider_id: str, data: CloudProviderUpdate, user: User = Depends(get_current_user)
):
    """Update cloud LLM provider"""
    # Filter out None values
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    provider = await async_cloud_provider_manager.update_provider(provider_id, **update_data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Audit log
    await async_audit_logger.log(
        action="update",
        resource="cloud_provider",
        resource_id=provider_id,
        user_id=user.username,
        details=update_data,
    )

    return {"status": "ok", "provider": provider}


@app.delete("/admin/llm/providers/{provider_id}")
async def admin_delete_cloud_provider(provider_id: str, user: User = Depends(get_current_user)):
    """Delete cloud LLM provider"""
    if not await async_cloud_provider_manager.delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")

    # Audit log
    await async_audit_logger.log(
        action="delete",
        resource="cloud_provider",
        resource_id=provider_id,
        user_id=user.username,
    )

    return {"status": "ok", "message": f"Provider {provider_id} deleted"}


@app.post("/admin/llm/providers/{provider_id}/test")
async def admin_test_cloud_provider(provider_id: str, user: User = Depends(get_current_user)):
    """Test cloud provider connection"""
    provider_config = await async_cloud_provider_manager.get_provider_with_key(provider_id)
    if not provider_config:
        raise HTTPException(status_code=404, detail="Provider not found")

    if not provider_config.get("api_key"):
        return {
            "status": "error",
            "available": False,
            "message": "No API key configured",
        }

    try:
        service = CloudLLMService(provider_config)
        is_available = service.is_available()

        if is_available:
            # Quick test generation
            test_response = service.generate_response("Скажи 'тест ок'", use_history=False)
            return {
                "status": "ok",
                "available": True,
                "test_response": test_response[:200] if test_response else "",
            }
        else:
            return {
                "status": "error",
                "available": False,
                "message": "Provider not responding",
            }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "message": str(e),
        }


@app.post("/admin/llm/providers/{provider_id}/set-default")
async def admin_set_default_cloud_provider(
    provider_id: str, user: User = Depends(get_current_user)
):
    """Set cloud provider as default"""
    if not await async_cloud_provider_manager.set_default(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found or disabled")

    await async_audit_logger.log(
        action="update",
        resource="cloud_provider",
        resource_id=provider_id,
        user_id=user.username,
        details={"is_default": True},
    )

    return {"status": "ok", "message": f"Provider {provider_id} set as default"}


@app.get("/admin/llm/personas")
async def admin_get_personas():
    """Получить список доступных персон"""
    if llm_service and hasattr(llm_service, "get_available_personas"):
        return {"personas": llm_service.get_available_personas()}

    # Fallback для Gemini LLM Service
    from vllm_llm_service import SECRETARY_PERSONAS

    return {
        "personas": {
            pid: {"name": p["name"], "full_name": p.get("full_name", p["name"])}
            for pid, p in SECRETARY_PERSONAS.items()
        }
    }


@app.get("/admin/llm/persona")
async def admin_get_current_persona():
    """Получить текущую персону"""
    if llm_service:
        persona_id = getattr(llm_service, "persona_id", "gulya")
        persona = getattr(llm_service, "persona", {})
        return {
            "id": persona_id,
            "name": persona.get("name", "Unknown"),
        }
    return {"id": "none", "error": "LLM service not initialized"}


@app.post("/admin/llm/persona")
async def admin_set_persona(request: AdminPersonaRequest, user: User = Depends(get_current_user)):
    """Установить персону"""
    if llm_service and hasattr(llm_service, "set_persona"):
        success = llm_service.set_persona(request.persona)
        if success:
            # Audit log
            await async_audit_logger.log(
                action="update",
                resource="config",
                resource_id="llm_persona",
                user_id=user.username,
                details={"persona": request.persona},
            )
            return {"status": "ok", "persona": request.persona}
        raise HTTPException(status_code=400, detail=f"Persona not found: {request.persona}")
    raise HTTPException(status_code=503, detail="LLM service does not support personas")


@app.get("/admin/llm/params")
async def admin_get_llm_params():
    """Получить параметры генерации LLM"""
    if llm_service and hasattr(llm_service, "runtime_params"):
        return {"params": llm_service.runtime_params}

    # Возвращаем значения по умолчанию
    return {
        "params": {"temperature": 0.7, "max_tokens": 512, "top_p": 0.9, "repetition_penalty": 1.1}
    }


@app.post("/admin/llm/params")
async def admin_set_llm_params(request: AdminLLMParamsRequest):
    """Установить параметры генерации LLM"""
    if llm_service and hasattr(llm_service, "set_params"):
        params = {k: v for k, v in request.dict().items() if v is not None}
        llm_service.set_params(**params)
        return {"status": "ok", "params": llm_service.runtime_params}

    # Для vLLM сервиса без set_params - сохраняем в атрибуте
    if llm_service:
        if not hasattr(llm_service, "runtime_params"):
            llm_service.runtime_params = {}
        params = {k: v for k, v in request.dict().items() if v is not None}
        llm_service.runtime_params.update(params)
        return {"status": "ok", "params": llm_service.runtime_params}

    raise HTTPException(status_code=503, detail="LLM service not initialized")


@app.get("/admin/llm/prompt/{persona}")
async def admin_get_persona_prompt(persona: str):
    """Получить системный промпт для персоны"""
    try:
        from vllm_llm_service import SECRETARY_PERSONAS

        if persona in SECRETARY_PERSONAS:
            return {"persona": persona, "prompt": SECRETARY_PERSONAS[persona]["prompt"]}
        raise HTTPException(status_code=404, detail=f"Persona not found: {persona}")
    except ImportError:
        raise HTTPException(status_code=503, detail="vLLM service not available")


@app.post("/admin/llm/prompt/{persona}")
async def admin_set_persona_prompt(persona: str, request: AdminLLMPromptRequest):
    """Установить системный промпт для персоны"""
    try:
        from vllm_llm_service import SECRETARY_PERSONAS

        if persona not in SECRETARY_PERSONAS:
            raise HTTPException(status_code=404, detail=f"Persona not found: {persona}")

        # Обновляем промпт
        SECRETARY_PERSONAS[persona]["prompt"] = request.prompt

        # Если это текущая персона - обновляем в сервисе
        if llm_service and hasattr(llm_service, "persona_id") and llm_service.persona_id == persona:
            llm_service.system_prompt = request.prompt

        return {"status": "ok", "persona": persona}
    except ImportError:
        raise HTTPException(status_code=503, detail="vLLM service not available")


@app.post("/admin/llm/prompt/{persona}/reset")
async def admin_reset_persona_prompt(persona: str):
    """Сбросить системный промпт персоны на значение по умолчанию"""
    # TODO: Реализовать хранение оригинальных промптов
    raise HTTPException(status_code=501, detail="Not implemented yet")


# ============== Fine-tuning Endpoints ==============


@app.post("/admin/finetune/dataset/upload")
async def admin_upload_dataset(file: UploadFile = File(...)):
    """Загрузить датасет (Telegram export JSON)"""
    manager = get_finetune_manager()
    content = await file.read()
    return await manager.upload_dataset(content, file.filename)


class DatasetProcessRequest(BaseModel):
    owner_name: Optional[str] = None
    transcribe_voice: Optional[bool] = None
    min_dialog_messages: Optional[int] = None
    max_message_length: Optional[int] = None
    max_dialog_length: Optional[int] = None
    include_groups: Optional[bool] = None
    output_name: Optional[str] = None


@app.post("/admin/finetune/dataset/process")
async def admin_process_dataset(request: Optional[DatasetProcessRequest] = None):
    """Обработать загруженный датасет"""
    manager = get_finetune_manager()
    config = request.model_dump(exclude_none=True) if request else None
    return await manager.process_dataset(config)


@app.get("/admin/finetune/dataset/config")
async def admin_get_dataset_config():
    """Получить конфигурацию обработки датасета"""
    manager = get_finetune_manager()
    return {"config": manager.get_dataset_config()}


@app.post("/admin/finetune/dataset/config")
async def admin_set_dataset_config(request: DatasetProcessRequest):
    """Установить конфигурацию обработки датасета"""
    manager = get_finetune_manager()
    return manager.set_dataset_config(**request.model_dump(exclude_none=True))


@app.get("/admin/finetune/dataset/processing-status")
async def admin_get_processing_status():
    """Получить статус обработки датасета"""
    manager = get_finetune_manager()
    return {"status": manager.get_processing_status()}


@app.get("/admin/finetune/dataset/stats")
async def admin_get_dataset_stats():
    """Получить статистику датасета"""
    manager = get_finetune_manager()
    stats = manager.get_dataset_stats()
    return {
        "stats": {
            "total_sessions": stats.total_sessions,
            "total_messages": stats.total_messages,
            "total_tokens": stats.total_tokens,
            "avg_tokens_per_message": stats.avg_tokens_per_message,
            "file_path": stats.file_path,
            "file_size_mb": stats.file_size_mb,
            "modified": stats.modified,
        }
    }


@app.get("/admin/finetune/dataset/list")
async def admin_list_datasets():
    """Список доступных датасетов"""
    manager = get_finetune_manager()
    return {"datasets": manager.list_datasets()}


@app.post("/admin/finetune/dataset/augment")
async def admin_augment_dataset():
    """Аугментировать датасет"""
    manager = get_finetune_manager()
    return await manager.augment_dataset()


class GenerateProjectDatasetRequest(BaseModel):
    include_tz: bool = True
    include_faq: bool = True
    include_docs: bool = True
    include_escalation: bool = True
    output_name: str = "project_dataset"


@app.post("/admin/finetune/dataset/generate-project")
async def admin_generate_project_dataset(request: GenerateProjectDatasetRequest):
    """Генерировать датасет из проектных источников (ТЗ, FAQ, документация, эскалации)"""
    manager = get_finetune_manager()
    return await manager.generate_project_dataset(
        include_tz=request.include_tz,
        include_faq=request.include_faq,
        include_docs=request.include_docs,
        include_escalation=request.include_escalation,
        output_name=request.output_name,
    )


@app.get("/admin/finetune/config")
async def admin_get_finetune_config():
    """Получить конфигурацию обучения"""
    manager = get_finetune_manager()
    config = manager.get_config()
    return {
        "config": {
            "base_model": config.base_model,
            "lora_rank": config.lora_rank,
            "lora_alpha": config.lora_alpha,
            "lora_dropout": config.lora_dropout,
            "batch_size": config.batch_size,
            "gradient_accumulation_steps": config.gradient_accumulation_steps,
            "learning_rate": config.learning_rate,
            "num_epochs": config.num_epochs,
            "warmup_ratio": config.warmup_ratio,
            "max_seq_length": config.max_seq_length,
            "output_dir": config.output_dir,
        },
        "presets": {
            name: {
                "lora_rank": p.lora_rank,
                "batch_size": p.batch_size,
                "num_epochs": p.num_epochs,
            }
            for name, p in manager.get_config_presets().items()
        },
    }


@app.post("/admin/finetune/config")
async def admin_set_finetune_config(request: AdminFinetuneConfigRequest):
    """Установить конфигурацию обучения"""
    manager = get_finetune_manager()
    config = manager.get_config()

    # Обновляем только переданные параметры
    if request.lora_rank is not None:
        config.lora_rank = request.lora_rank
    if request.lora_alpha is not None:
        config.lora_alpha = request.lora_alpha
    if request.batch_size is not None:
        config.batch_size = request.batch_size
    if request.gradient_accumulation_steps is not None:
        config.gradient_accumulation_steps = request.gradient_accumulation_steps
    if request.learning_rate is not None:
        config.learning_rate = request.learning_rate
    if request.num_epochs is not None:
        config.num_epochs = request.num_epochs
    if request.max_seq_length is not None:
        config.max_seq_length = request.max_seq_length
    if request.output_dir is not None:
        config.output_dir = request.output_dir

    return manager.set_config(config)


@app.post("/admin/finetune/train/start")
async def admin_start_training():
    """Запустить обучение"""
    manager = get_finetune_manager()
    return await manager.start_training()


@app.post("/admin/finetune/train/stop")
async def admin_stop_training():
    """Остановить обучение"""
    manager = get_finetune_manager()
    return await manager.stop_training()


@app.get("/admin/finetune/train/status")
async def admin_get_training_status():
    """Получить статус обучения"""
    manager = get_finetune_manager()
    status = manager.get_training_status()
    return {
        "status": {
            "is_running": status.is_running,
            "current_step": status.current_step,
            "total_steps": status.total_steps,
            "current_epoch": status.current_epoch,
            "total_epochs": status.total_epochs,
            "loss": status.loss,
            "learning_rate": status.learning_rate,
            "elapsed_seconds": status.elapsed_seconds,
            "eta_seconds": status.eta_seconds,
            "error": status.error,
        }
    }


@app.get("/admin/finetune/train/log")
async def admin_stream_training_log():
    """SSE streaming лога обучения"""
    manager = get_finetune_manager()

    async def generate():
        async for data in manager.stream_training_log():
            yield f"data: {data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/admin/finetune/adapters")
async def admin_list_adapters():
    """Получить список LoRA адаптеров"""
    manager = get_finetune_manager()
    adapters = manager.list_adapters()
    return {
        "adapters": [
            {
                "name": a.name,
                "path": a.path,
                "size_mb": a.size_mb,
                "modified": a.modified,
                "active": a.active,
                "config": a.config,
            }
            for a in adapters
        ],
        "active": manager.active_adapter,
    }


@app.post("/admin/finetune/adapters/activate")
async def admin_activate_adapter(request: AdminAdapterRequest):
    """Активировать LoRA адаптер"""
    manager = get_finetune_manager()
    return await manager.activate_adapter(request.adapter)


@app.delete("/admin/finetune/adapters/{name}")
async def admin_delete_adapter(name: str):
    """Удалить LoRA адаптер"""
    manager = get_finetune_manager()
    return await manager.delete_adapter(name)


# ============== TTS Finetune Endpoints ==============


@app.get("/admin/tts-finetune/config")
async def admin_get_tts_finetune_config():
    """Получить конфигурацию TTS fine-tuning"""
    manager = get_tts_finetune_manager()
    return {"config": manager.get_config()}


@app.post("/admin/tts-finetune/config")
async def admin_set_tts_finetune_config(config: dict):
    """Обновить конфигурацию TTS fine-tuning"""
    manager = get_tts_finetune_manager()
    return {"status": "ok", "config": manager.set_config(config)}


@app.get("/admin/tts-finetune/samples")
async def admin_get_tts_samples():
    """Получить список образцов голоса"""
    manager = get_tts_finetune_manager()
    return {"samples": manager.get_samples()}


@app.post("/admin/tts-finetune/samples/upload")
async def admin_upload_tts_sample(file: UploadFile = File(...)):
    """Загрузить образец голоса"""
    manager = get_tts_finetune_manager()
    content = await file.read()
    sample = manager.add_sample(file.filename, content)
    return {
        "status": "ok",
        "sample": {
            "filename": sample.filename,
            "path": sample.path,
            "duration_sec": sample.duration_sec,
            "size_kb": sample.size_kb,
        },
    }


@app.delete("/admin/tts-finetune/samples/{filename}")
async def admin_delete_tts_sample(filename: str):
    """Удалить образец голоса"""
    manager = get_tts_finetune_manager()
    if manager.delete_sample(filename):
        return {"status": "ok", "message": f"Sample {filename} deleted"}
    raise HTTPException(status_code=404, detail="Sample not found")


@app.put("/admin/tts-finetune/samples/{filename}/transcript")
async def admin_update_tts_transcript(filename: str, request: dict):
    """Обновить транскрипцию образца"""
    manager = get_tts_finetune_manager()
    transcript = request.get("transcript", "")
    sample = manager.update_transcript(filename, transcript)
    if not sample:
        raise HTTPException(status_code=404, detail="Sample not found")
    return {
        "status": "ok",
        "sample": {
            "filename": sample.filename,
            "transcript": sample.transcript,
            "transcript_edited": sample.transcript_edited,
        },
    }


@app.post("/admin/tts-finetune/transcribe")
async def admin_transcribe_tts_samples():
    """Запустить транскрибацию образцов через Whisper"""
    manager = get_tts_finetune_manager()
    if manager.transcribe_samples():
        return {"status": "ok", "message": "Transcription started"}
    return {"status": "error", "message": "Already running or no samples to transcribe"}


@app.post("/admin/tts-finetune/prepare")
async def admin_prepare_tts_dataset():
    """Подготовить датасет (извлечь audio_codes)"""
    manager = get_tts_finetune_manager()
    if manager.prepare_dataset():
        return {"status": "ok", "message": "Dataset preparation started"}
    return {"status": "error", "message": "Already running or no samples with transcripts"}


@app.get("/admin/tts-finetune/processing-status")
async def admin_get_tts_processing_status():
    """Получить статус обработки"""
    manager = get_tts_finetune_manager()
    return {"status": manager.get_processing_status()}


@app.post("/admin/tts-finetune/train/start")
async def admin_start_tts_training():
    """Запустить обучение TTS"""
    manager = get_tts_finetune_manager()
    if manager.start_training():
        return {"status": "ok", "message": "Training started"}
    return {"status": "error", "message": "Already running or dataset not prepared"}


@app.post("/admin/tts-finetune/train/stop")
async def admin_stop_tts_training():
    """Остановить обучение TTS"""
    manager = get_tts_finetune_manager()
    if manager.stop_training():
        return {"status": "ok", "message": "Training stopped"}
    return {"status": "error", "message": "Training not running"}


@app.get("/admin/tts-finetune/train/status")
async def admin_get_tts_training_status():
    """Получить статус обучения TTS"""
    manager = get_tts_finetune_manager()
    return {"status": manager.get_training_status()}


@app.get("/admin/tts-finetune/train/log")
async def admin_get_tts_training_log():
    """Получить лог обучения TTS"""
    manager = get_tts_finetune_manager()
    return {"log": manager.get_training_log()}


@app.get("/admin/tts-finetune/models")
async def admin_get_tts_trained_models():
    """Получить список обученных TTS моделей"""
    manager = get_tts_finetune_manager()
    return {"models": manager.get_trained_models()}


# ============== Monitoring Endpoints ==============


@app.get("/admin/monitor/gpu")
async def admin_get_gpu_stats():
    """Получить статистику GPU"""
    import torch

    if not torch.cuda.is_available():
        return {"available": False, "gpus": []}

    gpus = []
    for i in range(torch.cuda.device_count()):
        try:
            name = torch.cuda.get_device_name(i)
            props = torch.cuda.get_device_properties(i)
            total_memory = props.total_memory / (1024**3)
            allocated = torch.cuda.memory_allocated(i) / (1024**3)
            reserved = torch.cuda.memory_reserved(i) / (1024**3)

            # Пытаемся получить утилизацию через nvidia-smi
            utilization = None
            temperature = None
            try:
                import subprocess

                result = subprocess.run(
                    [
                        "nvidia-smi",
                        f"--id={i}",
                        "--query-gpu=utilization.gpu,temperature.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(",")
                    if len(parts) >= 2:
                        utilization = int(parts[0].strip())
                        temperature = int(parts[1].strip())
            except Exception:
                pass

            gpus.append(
                {
                    "id": i,
                    "name": name,
                    "total_memory_gb": round(total_memory, 2),
                    "allocated_gb": round(allocated, 2),
                    "reserved_gb": round(reserved, 2),
                    "free_gb": round(total_memory - reserved, 2),
                    "utilization_percent": utilization,
                    "temperature_c": temperature,
                    "compute_capability": f"{props.major}.{props.minor}",
                }
            )
        except Exception as e:
            logger.warning(f"Error getting GPU {i} stats: {e}")

    return {"available": True, "gpus": gpus}


@app.get("/admin/monitor/gpu/stream")
async def admin_stream_gpu_stats():
    """SSE streaming статистики GPU"""
    import torch

    async def generate():
        while True:
            if torch.cuda.is_available():
                gpus = []
                for i in range(torch.cuda.device_count()):
                    try:
                        allocated = torch.cuda.memory_allocated(i) / (1024**3)
                        reserved = torch.cuda.memory_reserved(i) / (1024**3)
                        gpus.append(
                            {
                                "id": i,
                                "allocated_gb": round(allocated, 2),
                                "reserved_gb": round(reserved, 2),
                            }
                        )
                    except Exception:
                        pass

                yield f"data: {json.dumps({'gpus': gpus, 'timestamp': datetime.now().isoformat()})}\n\n"
            else:
                yield f"data: {json.dumps({'available': False})}\n\n"

            await asyncio.sleep(5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/admin/monitor/health")
async def admin_get_health():
    """Расширенная проверка здоровья всех компонентов"""
    manager = get_service_manager()
    health = {"timestamp": datetime.now().isoformat(), "overall": "healthy", "components": {}}

    # Orchestrator
    health["components"]["orchestrator"] = {"status": "healthy", "uptime": "running"}

    # LLM
    if llm_service:
        try:
            if hasattr(llm_service, "is_available") and llm_service.is_available():
                health["components"]["llm"] = {"status": "healthy", "backend": "vllm"}
            else:
                health["components"]["llm"] = {"status": "healthy", "backend": "gemini"}
        except Exception as e:
            health["components"]["llm"] = {"status": "unhealthy", "error": str(e)}
            health["overall"] = "degraded"
    else:
        health["components"]["llm"] = {"status": "unavailable"}
        health["overall"] = "degraded"

    # TTS
    if gulya_voice_service or voice_service:
        health["components"]["tts_xtts"] = {"status": "healthy"}
    else:
        health["components"]["tts_xtts"] = {"status": "unavailable"}

    if piper_service:
        health["components"]["tts_piper"] = {"status": "healthy"}
    else:
        health["components"]["tts_piper"] = {"status": "unavailable"}

    # vLLM external process
    vllm_status = manager.get_service_status("vllm")
    if vllm_status["is_running"]:
        health["components"]["vllm_process"] = {"status": "healthy", "pid": vllm_status["pid"]}
    else:
        health["components"]["vllm_process"] = {"status": "stopped"}

    return health


@app.get("/admin/monitor/metrics")
async def admin_get_metrics():
    """Получить метрики системы"""
    import psutil

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 2),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        },
        "streaming_tts": streaming_tts_manager.get_stats() if streaming_tts_manager else None,
    }

    # LLM метрики
    if llm_service:
        metrics["llm"] = {
            "history_length": len(getattr(llm_service, "conversation_history", [])),
            "faq_count": len(getattr(llm_service, "faq", {})),
        }

    return metrics


@app.get("/admin/monitor/errors")
async def admin_get_errors():
    """Получить последние ошибки"""
    manager = get_service_manager()
    return {"errors": manager.last_errors, "timestamp": datetime.now().isoformat()}


@app.post("/admin/monitor/metrics/reset")
async def admin_reset_metrics():
    """Сбросить метрики"""
    # Очищаем кэш TTS
    if streaming_tts_manager:
        with streaming_tts_manager._cache_lock:
            streaming_tts_manager._cache.clear()

    return {"status": "ok", "message": "Metrics reset"}


@app.get("/admin/monitor/system")
async def admin_get_system_status():
    """Полная информация о системе: GPU, CPU, RAM, диски, Docker, сеть"""
    monitor = get_system_monitor()
    return monitor.get_full_status()


# ============== Model Management API ==============


@app.get("/admin/models/list")
async def admin_list_models():
    """Список всех локальных моделей"""
    manager = get_model_manager()
    return {"models": manager.get_cached_models()}


@app.post("/admin/models/scan")
async def admin_scan_models(request: Request):
    """Запустить сканирование моделей"""
    data = await request.json() if request.headers.get("content-type") == "application/json" else {}
    include_system = data.get("include_system", False)

    manager = get_model_manager()
    if manager.scan_all_models(include_system=include_system):
        return {"status": "ok", "message": "Scan started"}
    else:
        return {"status": "error", "message": "Scan already in progress"}


@app.post("/admin/models/scan/cancel")
async def admin_cancel_scan():
    """Отменить сканирование"""
    manager = get_model_manager()
    manager.cancel_scan()
    return {"status": "ok", "message": "Scan cancelled"}


@app.get("/admin/models/scan/status")
async def admin_scan_status():
    """Статус сканирования"""
    manager = get_model_manager()
    return {"status": manager.get_scan_progress()}


@app.post("/admin/models/download")
async def admin_download_model(request: Request):
    """Скачать модель с HuggingFace"""
    data = await request.json()
    repo_id = data.get("repo_id")
    revision = data.get("revision", "main")

    if not repo_id:
        raise HTTPException(status_code=400, detail="repo_id required")

    manager = get_model_manager()
    if manager.download_model(repo_id, revision):
        return {"status": "ok", "message": f"Download started: {repo_id}"}
    else:
        return {"status": "error", "message": "Download already in progress"}


@app.post("/admin/models/download/cancel")
async def admin_cancel_download():
    """Отменить загрузку"""
    manager = get_model_manager()
    manager.cancel_download()
    return {"status": "ok", "message": "Download cancelled"}


@app.get("/admin/models/download/status")
async def admin_download_status():
    """Статус загрузки"""
    manager = get_model_manager()
    return {"status": manager.get_download_progress()}


@app.delete("/admin/models/delete")
async def admin_delete_model(path: str):
    """Удалить модель"""
    manager = get_model_manager()
    result = manager.delete_model(path)
    if result["status"] == "ok":
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get("error", "Delete failed"))


@app.get("/admin/models/search")
async def admin_search_huggingface(query: str, limit: int = 20):
    """Поиск моделей на HuggingFace"""
    manager = get_model_manager()
    results = manager.search_huggingface(query, limit)
    return {"results": results}


@app.get("/admin/models/details/{repo_id:path}")
async def admin_get_model_details(repo_id: str):
    """Получить детали модели с HuggingFace"""
    manager = get_model_manager()
    details = manager.get_model_details(repo_id)
    if details:
        return {"details": details}
    else:
        raise HTTPException(status_code=404, detail="Model not found")


# ============== Widget Script Endpoint ==============


def _escape_js_string(s: str) -> str:
    """Escape a string for safe use in JavaScript."""
    return s.replace("'", "\\'")


@app.get("/widget.js")
async def get_widget_script(request: Request, instance: Optional[str] = None):
    """Динамически генерируемый скрипт виджета.

    Args:
        instance: Optional widget instance ID. If not provided, uses legacy config or 'default' instance.
    """
    config = None

    # Try to load from widget instance if specified
    if instance:
        instance_data = await async_widget_instance_manager.get_instance(instance)
        if instance_data:
            config = instance_data
        else:
            return Response(
                content=f"// Widget instance '{instance}' not found",
                media_type="application/javascript",
                status_code=404,
            )
    else:
        # Try default instance first, fallback to legacy config
        instance_data = await async_widget_instance_manager.get_instance("default")
        if instance_data:
            config = instance_data
        else:
            # Fallback to legacy config
            config = await async_config_manager.get_widget()

    # Проверяем включен ли виджет
    if not config.get("enabled", False):
        return Response(content="// Widget is disabled", media_type="application/javascript")

    # Проверяем домен (если указаны разрешенные)
    origin = request.headers.get("origin", "") or request.headers.get("referer", "")
    allowed_domains = config.get("allowed_domains", [])
    if allowed_domains and origin:
        origin_domain = (
            origin.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        )
        if not any(d in origin_domain for d in allowed_domains):
            return Response(
                content=f"// Widget not allowed for domain: {origin_domain}",
                media_type="application/javascript",
            )

    # Определяем API URL
    api_url = config.get("tunnel_url", "").strip()
    if not api_url:
        # Используем текущий хост если tunnel_url не указан
        api_url = str(request.base_url).rstrip("/")

    # Читаем базовый скрипт виджета
    widget_path = Path(__file__).parent / "web-widget" / "ai-chat-widget.js"
    if not widget_path.exists():
        return Response(
            content="// Widget script not found",
            media_type="application/javascript",
            status_code=404,
        )

    widget_js = widget_path.read_text(encoding="utf-8")

    # Генерируем скрипт с настройками
    instance_id = instance or config.get("id", "default")
    settings_js = f"""
// Auto-generated widget settings
// Instance: {instance_id}
window.aiChatSettings = {{
  apiUrl: '{api_url}',
  instanceId: '{instance_id}',
  title: '{config.get("title", "AI Ассистент")}',
  greeting: '{_escape_js_string(config.get("greeting") or "")}',
  placeholder: '{_escape_js_string(config.get("placeholder") or "")}',
  primaryColor: '{config.get("primary_color", "#6366f1")}',
  position: '{config.get("position", "right")}'
}};

"""
    full_script = settings_js + widget_js

    return Response(
        content=full_script,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ============== Static Files for Vue Admin ==============

DEV_MODE = os.getenv("DEV_MODE", "").lower() in ("1", "true", "yes")
VITE_DEV_URL = os.getenv("VITE_DEV_URL", "http://localhost:5173")

if DEV_MODE:
    # Dev mode: proxy to Vite dev server for hot reload
    import httpx

    @app.api_route("/admin/{path:path}", methods=["GET", "HEAD"])
    async def proxy_to_vite(path: str, request: Request):
        """Proxy static files to Vite dev server"""
        async with httpx.AsyncClient() as client:
            url = f"{VITE_DEV_URL}/admin/{path}"
            try:
                resp = await client.get(url, headers=dict(request.headers))
                return Response(
                    content=resp.content, status_code=resp.status_code, headers=dict(resp.headers)
                )
            except httpx.ConnectError:
                return Response(
                    content=b"Vite dev server not running. Start with: cd admin && npm run dev",
                    status_code=503,
                )

    @app.get("/admin")
    async def proxy_admin_root():
        """Redirect /admin to /admin/"""
        return RedirectResponse(url="/admin/")

    logger.info(f"🔧 DEV MODE: Proxying /admin/* to Vite at {VITE_DEV_URL}")
else:
    # Production: serve built Vue app
    admin_dist_path = Path(__file__).parent / "admin" / "dist"
    if admin_dist_path.exists():
        from fastapi.staticfiles import StaticFiles

        app.mount("/admin", StaticFiles(directory=str(admin_dist_path), html=True), name="admin")
        logger.info(f"📂 Vue admin mounted at /admin from {admin_dist_path}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    port = int(os.getenv("ORCHESTRATOR_PORT", 8002))
    logger.info(f"🎯 Запуск Orchestrator на порту {port}")
    uvicorn.run("orchestrator:app", host="0.0.0.0", port=port, reload=False, log_level="info")
