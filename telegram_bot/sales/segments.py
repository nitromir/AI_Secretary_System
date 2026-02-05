"""Segmentation matrix: quiz answers -> user segment."""

from enum import Enum


class UserSegment(str, Enum):
    DIY = "diy"
    BASIC = "basic"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


# (tech_level, infrastructure) -> (segment, sub_segment)
SEGMENT_MATRIX: dict[tuple[str, str], tuple[UserSegment, str]] = {
    ("diy", "gpu"): (UserSegment.DIY, "diy_ready"),
    ("diy", "cpu"): (UserSegment.DIY, "diy_need_advice"),
    ("diy", "none"): (UserSegment.DIY, "diy_need_hw"),
    ("diy", "unknown"): (UserSegment.DIY, "diy_need_audit"),
    ("ready", "gpu"): (UserSegment.BASIC, "basic_hot"),
    ("ready", "cpu"): (UserSegment.BASIC, "basic_warm"),
    ("ready", "none"): (UserSegment.BASIC, "basic_cold"),
    ("ready", "unknown"): (UserSegment.BASIC, "basic_audit"),
    ("business", "gpu"): (UserSegment.CUSTOM, "custom_hot"),
    ("business", "cpu"): (UserSegment.CUSTOM, "custom_warm"),
    ("business", "none"): (UserSegment.CUSTOM, "custom_full"),
    ("business", "unknown"): (UserSegment.CUSTOM, "custom_discovery"),
}


def determine_segment(tech_level: str, infrastructure: str) -> tuple[UserSegment, str]:
    """Return (segment, sub_segment) based on quiz answers."""
    return SEGMENT_MATRIX.get(
        (tech_level, infrastructure),
        (UserSegment.UNKNOWN, "unknown"),
    )


# GPU audit data: gpu_key -> (model_name, llm, tts_ok, stt_ok, quality, speed, upgrade_hint)
GPU_AUDIT = {
    "gtx_16xx": {
        "name": "GTX 1660/1070/1080 (6-8 GB)",
        "llm": "Qwen2.5-3B",
        "quality": 2,
        "speed": "~3 сек на ответ",
        "hint": "С RTX 3060 (12GB) можно использовать Qwen-7B — ответы значительно умнее.",
    },
    "rtx_30xx_low": {
        "name": "RTX 3060/3070 (8-12 GB)",
        "llm": "Qwen2.5-7B",
        "quality": 3,
        "speed": "~2 сек на ответ",
        "hint": "С RTX 3090 можно использовать Qwen-14B — ещё умнее.",
    },
    "rtx_30xx_high": {
        "name": "RTX 3080/3090 (10-24 GB)",
        "llm": "Qwen2.5-14B",
        "quality": 4,
        "speed": "~1.5 сек на ответ",
        "hint": "Отличная конфигурация! RTX 4090 даст ещё больше скорости.",
    },
    "rtx_40xx": {
        "name": "RTX 4080/4090 (16-24 GB)",
        "llm": "Qwen2.5-32B",
        "quality": 5,
        "speed": "~1 сек на ответ",
        "hint": "Топовая конфигурация! Максимальное качество ответов.",
    },
}


def get_gpu_audit(gpu_key: str) -> dict | None:
    """Return GPU audit data for display."""
    return GPU_AUDIT.get(gpu_key)


# Pricing logic for custom quotes
BASE_PRICE = 50_000
INTEGRATION_PRICES = {
    "int_bitrix": ("Bitrix24", 20_000),
    "int_amo": ("amoCRM", 20_000),
    "int_1c": ("1С", 25_000),
    "int_phone": ("Телефония", 30_000),
    "int_custom": ("Своя система (API)", 15_000),
}
VOLUME_MULTIPLIERS = {
    "vol_low": 1.0,
    "vol_mid": 1.0,
    "vol_high": 1.3,
    "vol_enterprise": 1.5,
    "vol_unknown": 1.0,
}
TIMELINE_MAP = {
    "time_urgent": "1-2 недели",
    "time_month": "2-3 недели",
    "time_quarter": "3-4 недели",
    "time_research": "По согласованию",
}


def calculate_quote(discovery: dict) -> dict:
    """Generate a price quote from custom discovery answers."""
    integrations = discovery.get("step_3_integrations", [])
    volume = discovery.get("step_2_volume", "vol_unknown")

    items = [("Базовая система", BASE_PRICE)]
    for int_key in integrations:
        if int_key in INTEGRATION_PRICES and int_key != "int_none":
            name, price = INTEGRATION_PRICES[int_key]
            items.append((f"Интеграция {name}", price))

    subtotal = sum(p for _, p in items)
    multiplier = VOLUME_MULTIPLIERS.get(volume, 1.0)
    if multiplier > 1.0:
        extra = int(subtotal * (multiplier - 1))
        items.append((f"Высокий объём (x{multiplier})", extra))

    total = int(subtotal * multiplier)
    timeline = TIMELINE_MAP.get(discovery.get("step_4_timeline", ""), "По согласованию")

    return {
        "items": items,
        "total_min": total,
        "total_max": int(total * 1.25),
        "timeline": timeline,
    }
