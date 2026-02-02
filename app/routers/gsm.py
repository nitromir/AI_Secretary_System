# app/routers/gsm.py
"""GSM телефония - управление SIM7600E-H модулем."""

import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_manager import User, get_current_user


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/gsm", tags=["gsm"])


# ============== Enums ==============


class ModuleState(str, Enum):
    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    READY = "ready"
    INCOMING_CALL = "incoming_call"
    IN_CALL = "in_call"
    ERROR = "error"


class CallDirection(str, Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class CallState(str, Enum):
    RINGING = "ringing"
    ACTIVE = "active"
    COMPLETED = "completed"
    MISSED = "missed"
    FAILED = "failed"


# ============== Pydantic Models ==============


class GSMStatus(BaseModel):
    """Статус GSM модуля."""

    state: ModuleState = ModuleState.DISCONNECTED
    signal_strength: Optional[int] = None  # 0-31, 99=unknown
    signal_percent: Optional[int] = None
    sim_status: Optional[str] = None  # READY, PIN, PUK, etc
    network_name: Optional[str] = None
    network_registered: bool = False
    phone_number: Optional[str] = None
    at_port: str = "/dev/ttyUSB2"
    audio_port: str = "/dev/ttyUSB4"
    module_info: Optional[str] = None
    last_error: Optional[str] = None


class GSMConfig(BaseModel):
    """Конфигурация GSM модуля."""

    # Порты
    at_port: str = "/dev/ttyUSB2"
    audio_port: str = "/dev/ttyUSB4"
    baud_rate: int = 115200

    # Автоответ
    auto_answer: bool = True
    auto_answer_rings: int = 2

    # Фильтрация номеров
    allowed_numbers: List[str] = []
    blocked_numbers: List[str] = []

    # Сообщения
    greeting_message: str = "Здравствуйте! Чем могу помочь?"
    goodbye_message: str = "До свидания! Хорошего дня!"
    busy_message: str = "Извините, сейчас занято. Оставьте сообщение после сигнала."

    # Таймауты (секунды)
    silence_timeout: int = 5
    max_call_duration: int = 300

    # SMS уведомления
    sms_enabled: bool = True
    sms_notify_number: str = ""
    sms_missed_call_template: str = "Пропущенный звонок от {number} в {time}"
    sms_voicemail_template: str = "Сообщение от {number}: {summary}"

    # LLM
    llm_backend: str = "vllm"
    llm_persona: str = "gulya"

    # TTS
    tts_voice: str = "gulya"
    tts_preset: str = "natural"


class CallInfo(BaseModel):
    """Информация о звонке."""

    id: str
    direction: CallDirection
    state: CallState
    caller_number: str
    started_at: datetime
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript_preview: Optional[str] = None
    sms_sent: bool = False


class ActiveCall(BaseModel):
    """Активный звонок."""

    id: str
    direction: CallDirection
    caller_number: str
    started_at: datetime
    duration_seconds: int = 0
    transcript: List[dict] = []


class SMSMessage(BaseModel):
    """SMS сообщение."""

    id: int
    direction: str  # incoming/outgoing
    number: str
    text: str
    sent_at: datetime
    status: str


class SendSMSRequest(BaseModel):
    """Запрос на отправку SMS."""

    number: str
    text: str


class ATCommandRequest(BaseModel):
    """Запрос AT команды (для отладки)."""

    command: str
    timeout: float = 5.0


class ATCommandResponse(BaseModel):
    """Ответ AT команды."""

    command: str
    response: List[str]
    success: bool
    error: Optional[str] = None


# ============== Global state (будет заменено на GSMService) ==============

# Временное хранилище - будет заменено на реальный сервис
_gsm_config: Optional[GSMConfig] = None
_call_history: List[CallInfo] = []
_sms_history: List[SMSMessage] = []


def _get_config() -> GSMConfig:
    global _gsm_config
    if _gsm_config is None:
        _gsm_config = GSMConfig()
    return _gsm_config


# ============== Status Endpoints ==============


@router.get("/status")
async def gsm_status() -> GSMStatus:
    """Получить статус GSM модуля."""
    config = _get_config()

    # Проверяем наличие USB устройств
    at_port_path = Path(config.at_port)

    if not at_port_path.exists():
        return GSMStatus(
            state=ModuleState.DISCONNECTED,
            at_port=config.at_port,
            audio_port=config.audio_port,
            last_error=f"AT порт {config.at_port} не найден. Подключите модуль.",
        )

    # TODO: Реальная проверка модуля через AT команды
    # Пока возвращаем заглушку
    return GSMStatus(
        state=ModuleState.DISCONNECTED,
        at_port=config.at_port,
        audio_port=config.audio_port,
        last_error="GSM сервис не инициализирован. Модуль не подключен.",
    )


@router.post("/initialize")
async def initialize_module(user: User = Depends(get_current_user)):
    """Инициализировать GSM модуль."""
    config = _get_config()

    if not Path(config.at_port).exists():
        raise HTTPException(
            status_code=503,
            detail=f"AT порт {config.at_port} не найден. Подключите модуль.",
        )

    # TODO: Реальная инициализация через GSMService
    return {
        "status": "ok",
        "message": "Инициализация GSM модуля (заглушка - модуль не подключен)",
    }


# ============== Config Endpoints ==============


@router.get("/config")
async def get_gsm_config() -> GSMConfig:
    """Получить конфигурацию GSM."""
    return _get_config()


@router.put("/config")
async def update_gsm_config(config: GSMConfig, user: User = Depends(get_current_user)) -> GSMConfig:
    """Обновить конфигурацию GSM."""
    global _gsm_config
    _gsm_config = config
    logger.info(f"GSM config updated by {user.username}")
    return config


# ============== Call Endpoints ==============


@router.get("/calls")
async def list_calls(limit: int = 50, offset: int = 0, state: Optional[CallState] = None) -> dict:
    """Список звонков."""
    calls = _call_history

    if state:
        calls = [c for c in calls if c.state == state]

    total = len(calls)
    calls = calls[offset : offset + limit]

    return {"calls": calls, "total": total, "limit": limit, "offset": offset}


@router.get("/calls/active")
async def get_active_call() -> Optional[ActiveCall]:
    """Получить активный звонок."""
    # TODO: Реальная проверка через GSMService
    return None


@router.get("/calls/{call_id}")
async def get_call(call_id: str) -> CallInfo:
    """Детали звонка."""
    for call in _call_history:
        if call.id == call_id:
            return call
    raise HTTPException(status_code=404, detail="Звонок не найден")


@router.post("/calls/answer")
async def answer_call(user: User = Depends(get_current_user)):
    """Ответить на входящий звонок."""
    # TODO: GSMService.answer_call()
    return {"status": "ok", "message": "Команда ответа отправлена (заглушка)"}


@router.post("/calls/hangup")
async def hangup_call(user: User = Depends(get_current_user)):
    """Завершить текущий звонок."""
    # TODO: GSMService.hangup()
    return {"status": "ok", "message": "Команда завершения отправлена (заглушка)"}


@router.post("/calls/dial")
async def dial_number(number: str, user: User = Depends(get_current_user)):
    """Позвонить на номер."""
    # TODO: GSMService.dial()
    return {
        "status": "ok",
        "message": f"Звонок на {number} (заглушка - модуль не подключен)",
    }


# ============== SMS Endpoints ==============


@router.get("/sms")
async def list_sms(limit: int = 50, offset: int = 0) -> dict:
    """Список SMS."""
    total = len(_sms_history)
    messages = _sms_history[offset : offset + limit]
    return {"messages": messages, "total": total, "limit": limit, "offset": offset}


@router.post("/sms")
async def send_sms(request: SendSMSRequest, user: User = Depends(get_current_user)):
    """Отправить SMS."""
    # TODO: GSMService.send_sms()
    return {
        "status": "ok",
        "message": f"SMS на {request.number} (заглушка - модуль не подключен)",
    }


# ============== Debug Endpoints ==============


@router.post("/at")
async def execute_at_command(
    request: ATCommandRequest, user: User = Depends(get_current_user)
) -> ATCommandResponse:
    """Выполнить AT команду (для отладки)."""
    config = _get_config()

    if not Path(config.at_port).exists():
        return ATCommandResponse(
            command=request.command,
            response=[],
            success=False,
            error=f"AT порт {config.at_port} не найден",
        )

    # TODO: Реальное выполнение через serial
    return ATCommandResponse(
        command=request.command,
        response=["Заглушка - модуль не подключен"],
        success=False,
        error="GSM сервис не инициализирован",
    )


@router.get("/ports")
async def list_serial_ports() -> dict:
    """Список доступных serial портов."""
    dev_path = Path("/dev")

    usb_ports = [str(p) for p in dev_path.glob("ttyUSB*")]
    acm_ports = [str(p) for p in dev_path.glob("ttyACM*")]

    return {
        "usb_ports": sorted(usb_ports),
        "acm_ports": sorted(acm_ports),
        "total": len(usb_ports) + len(acm_ports),
    }
