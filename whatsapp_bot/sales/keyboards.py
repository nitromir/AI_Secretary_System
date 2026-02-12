"""WhatsApp keyboard builders.

Builds interactive message payloads for WhatsApp Cloud API.
Equivalent of telegram_bot/sales/keyboards.py but using
WhatsApp quick-reply buttons (max 3) and list messages (max 10 rows).

Naming convention:
  *_buttons() → quick-reply (≤3 buttons, titles ≤20 chars)
  *_list()    → list message (≤10 sections, ≤10 rows each)
"""

from typing import Any


# ─── Internal helpers ─────────────────────────────────────────


def _quick_reply(
    body: str,
    buttons: list[tuple[str, str]],
    header: str = "",
    footer: str = "",
) -> dict[str, Any]:
    """Build quick-reply button payload.

    Args:
        body: Message body text.
        buttons: List of (reply_id, title) tuples. Max 3, titles max 20 chars.
        header: Optional header text.
        footer: Optional footer text.
    """
    action_buttons = [
        {"type": "reply", "reply": {"id": rid, "title": title[:20]}} for rid, title in buttons[:3]
    ]
    result: dict[str, Any] = {
        "type": "button",
        "body": {"text": body},
        "action": {"buttons": action_buttons},
    }
    if header:
        result["header"] = {"type": "text", "text": header}
    if footer:
        result["footer"] = {"text": footer}
    return result


def _list_message(
    body: str,
    button_text: str,
    sections: list[dict[str, Any]],
    header: str = "",
    footer: str = "",
) -> dict[str, Any]:
    """Build list message payload.

    Args:
        body: Message body text.
        button_text: Text on the list-open button (max 20 chars).
        sections: List of {"title": str, "rows": [{"id", "title", "description"}]}.
        header: Optional header text.
        footer: Optional footer text.
    """
    result: dict[str, Any] = {
        "type": "list",
        "body": {"text": body},
        "action": {
            "button": button_text[:20],
            "sections": sections[:10],
        },
    }
    if header:
        result["header"] = {"type": "text", "text": header}
    if footer:
        result["footer"] = {"text": footer}
    return result


# ─── Welcome ──────────────────────────────────────────────────


def welcome_buttons() -> dict[str, Any]:
    """Welcome message with 3 quick-reply buttons."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:start_quiz", "🎯 Подобрать"),
            ("sales:github", "📦 GitHub"),
            ("sales:faq", "❓ FAQ"),
        ],
    )


def what_is_buttons() -> dict[str, Any]:
    """What-is-this screen: quiz, GitHub link, back."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:start_quiz", "🚀 Подобрать"),
            ("sales:github", "📦 GitHub"),
            ("sales:back_welcome", "← Назад"),
        ],
    )


def menu_buttons() -> dict[str, Any]:
    """Main menu buttons."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:start_quiz", "🚀 Подобрать"),
            ("sales:contact", "📞 Связаться"),
            ("sales:faq", "❓ FAQ"),
        ],
    )


def contact_buttons() -> dict[str, Any]:
    """Contact screen — back to menu."""
    return _quick_reply(
        body="Напишите нам или вернитесь в меню 👇",
        buttons=[
            ("nav:welcome", "← Главное меню"),
        ],
    )


# ─── Quiz (WA-10) ────────────────────────────────────────────


def quiz_tech_buttons() -> dict[str, Any]:
    """Quiz Q1: Technical attitude (3 options)."""
    return _quick_reply(
        body="Как вы относитесь к технической стороне?",
        buttons=[
            ("sales:qt_diy", "🛠️ Сам разберусь"),
            ("sales:qt_ready", "🤝 Готовое решение"),
            ("sales:qt_business", "🏢 Бизнес-задача"),
        ],
    )


def quiz_infra_list() -> dict[str, Any]:
    """Quiz Q2: Infrastructure (4 options -> list)."""
    return _list_message(
        body="Есть ли у вас сервер для установки?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Инфраструктура",
                "rows": [
                    {
                        "id": "sales:qi_gpu",
                        "title": "✅ Есть GPU",
                        "description": "Сервер с видеокартой",
                    },
                    {
                        "id": "sales:qi_cpu",
                        "title": "💻 Есть без GPU",
                        "description": "Сервер без видеокарты",
                    },
                    {
                        "id": "sales:qi_none",
                        "title": "❌ Нет сервера",
                        "description": "Нужна помощь",
                    },
                    {
                        "id": "sales:qi_unknown",
                        "title": "🤷 Не знаю",
                        "description": "Нужна консультация",
                    },
                ],
            }
        ],
    )


# ─── DIY Path (WA-10) ────────────────────────────────────────


def diy_audit_result_buttons() -> dict[str, Any]:
    """After GPU audit — action buttons."""
    return _quick_reply(
        body="Готовы к установке?",
        buttons=[
            ("sales:diy_github", "📦 GitHub"),
            ("sales:diy_install_5k", "⚡ Установить 5К₽"),
            ("sales:contact", "❓ Есть вопросы"),
        ],
    )


def diy_gpu_list() -> dict[str, Any]:
    """GPU model selection (5 options -> list)."""
    return _list_message(
        body="Какая у вас видеокарта?",
        button_text="Выбрать GPU",
        sections=[
            {
                "title": "Видеокарты",
                "rows": [
                    {
                        "id": "sales:gpu_gtx_16xx",
                        "title": "GTX 1660/1070/1080",
                        "description": "6-8 GB VRAM",
                    },
                    {
                        "id": "sales:gpu_rtx_30xx_low",
                        "title": "RTX 3060/3070",
                        "description": "8-12 GB VRAM",
                    },
                    {
                        "id": "sales:gpu_rtx_30xx_high",
                        "title": "RTX 3080/3090",
                        "description": "10-24 GB VRAM",
                    },
                    {
                        "id": "sales:gpu_rtx_40xx",
                        "title": "RTX 4080/4090",
                        "description": "16-24 GB VRAM",
                    },
                    {
                        "id": "sales:gpu_other",
                        "title": "Другая",
                        "description": "Напишу модель",
                    },
                ],
            }
        ],
    )


# ─── Basic Path (WA-10) ──────────────────────────────────────


def basic_value_buttons() -> dict[str, Any]:
    """After value proposition — next steps."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:basic_checkout", "⚡ Установить 5К₽"),
            ("sales:basic_demo", "🎬 Демо"),
            ("sales:contact", "❓ Вопросы"),
        ],
    )


def basic_demo_buttons() -> dict[str, Any]:
    """After demo — next steps."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:basic_checkout", "⚡ Хочу такое!"),
            ("sales:contact", "❓ Вопросы"),
            ("sales:basic_back_value", "← Назад"),
        ],
    )


def basic_checkout_buttons() -> dict[str, Any]:
    """Checkout screen buttons."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:basic_pay", "💳 Оплатить 5К₽"),
            ("sales:basic_no_gpu", "❓ Нет GPU"),
            ("sales:contact", "📞 Вопрос"),
        ],
    )


def basic_no_gpu_list() -> dict[str, Any]:
    """No-GPU options (4 items -> list)."""
    return _list_message(
        body="Нет GPU? Не проблема! Выберите вариант:",
        button_text="Варианты",
        sections=[
            {
                "title": "Без GPU",
                "rows": [
                    {
                        "id": "sales:nogpu_cpu",
                        "title": "1️⃣ CPU режим",
                        "description": "Cloud LLM бесплатно",
                    },
                    {
                        "id": "sales:nogpu_vps",
                        "title": "2️⃣ Аренда VPS",
                        "description": "От 3,000₽/мес",
                    },
                    {
                        "id": "sales:nogpu_own",
                        "title": "3️⃣ Свой сервер",
                        "description": "RTX 3060 б/у ~25К₽",
                    },
                    {
                        "id": "sales:contact",
                        "title": "🤔 Помогите выбрать",
                        "description": "Консультация",
                    },
                ],
            }
        ],
    )


# ─── Custom Path (WA-10) ─────────────────────────────────────


def custom_intro_buttons() -> dict[str, Any]:
    """Custom project intro buttons."""
    return _quick_reply(
        body="Расскажете о вашей задаче?",
        buttons=[
            ("sales:custom_start", "🎯 Опишу задачу"),
            ("sales:custom_prices", "💰 Сначала цены"),
            ("sales:contact", "📞 Позвоните"),
        ],
    )


def custom_quote_buttons() -> dict[str, Any]:
    """After quote — next steps."""
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            ("sales:contact", "📞 Обсудить"),
            ("sales:custom_expensive", "🤔 Дорого"),
            ("sales:custom_restart", "✏️ Изменить"),
        ],
    )


def custom_expensive_buttons() -> dict[str, Any]:
    """Cheaper alternatives."""
    return _quick_reply(
        body="Какой вариант интереснее?",
        buttons=[
            ("sales:ce_mvp", "1️⃣ MVP"),
            ("sales:ce_stages", "2️⃣ Этапы"),
            ("sales:ce_diy", "3️⃣ DIY"),
        ],
    )


def custom_step_2_list() -> dict[str, Any]:
    """Custom Q2: Volume (5 options -> list)."""
    return _list_message(
        body="📊 Какой объём обращений в день?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Объём обращений",
                "rows": [
                    {
                        "id": "sales:cv_vol_low",
                        "title": "До 50",
                        "description": "Малый объём",
                    },
                    {
                        "id": "sales:cv_vol_mid",
                        "title": "50-200",
                        "description": "Средний объём",
                    },
                    {
                        "id": "sales:cv_vol_high",
                        "title": "200-1000",
                        "description": "Большой объём",
                    },
                    {
                        "id": "sales:cv_vol_enterprise",
                        "title": "Больше 1000",
                        "description": "Корпоративный",
                    },
                    {
                        "id": "sales:cv_vol_unknown",
                        "title": "Пока не знаю",
                        "description": "Нужен расчёт",
                    },
                ],
            }
        ],
    )


def custom_step_3_list() -> dict[str, Any]:
    """Custom Q3: Integrations (6 options -> list)."""
    return _list_message(
        body="🔗 С чем нужна интеграция?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Интеграции",
                "rows": [
                    {
                        "id": "sales:ci_int_bitrix",
                        "title": "Bitrix24",
                        "description": "CRM Битрикс24",
                    },
                    {
                        "id": "sales:ci_int_amo",
                        "title": "amoCRM",
                        "description": "CRM amoCRM",
                    },
                    {
                        "id": "sales:ci_int_1c",
                        "title": "1С",
                        "description": "Бухгалтерия / ERP",
                    },
                    {
                        "id": "sales:ci_int_phone",
                        "title": "Телефония",
                        "description": "Asterisk / SIP",
                    },
                    {
                        "id": "sales:ci_int_custom",
                        "title": "Своя система",
                        "description": "Через API",
                    },
                    {
                        "id": "sales:ci_int_none",
                        "title": "Не нужны",
                        "description": "Без интеграций",
                    },
                ],
            }
        ],
    )


def custom_step_4_list() -> dict[str, Any]:
    """Custom Q4: Timeline (4 options -> list)."""
    return _list_message(
        body="⏰ Когда нужно запустить?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Сроки",
                "rows": [
                    {
                        "id": "sales:ct_time_urgent",
                        "title": "🔥 1-2 недели",
                        "description": "Срочно",
                    },
                    {
                        "id": "sales:ct_time_month",
                        "title": "📅 В течение месяца",
                        "description": "Стандартный срок",
                    },
                    {
                        "id": "sales:ct_time_quarter",
                        "title": "📆 В течение квартала",
                        "description": "Без спешки",
                    },
                    {
                        "id": "sales:ct_time_research",
                        "title": "🔍 Пока изучаю",
                        "description": "Исследую варианты",
                    },
                ],
            }
        ],
    )


def custom_step_5_list() -> dict[str, Any]:
    """Custom Q5: Budget (5 options -> list)."""
    return _list_message(
        body="💰 Какой бюджет планируете?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Бюджет",
                "rows": [
                    {
                        "id": "sales:cb_budget_50",
                        "title": "50-100К₽",
                        "description": "Начальный бюджет",
                    },
                    {
                        "id": "sales:cb_budget_100",
                        "title": "100-200К₽",
                        "description": "Средний бюджет",
                    },
                    {
                        "id": "sales:cb_budget_200",
                        "title": "200-500К₽",
                        "description": "Расширенный",
                    },
                    {
                        "id": "sales:cb_budget_500",
                        "title": "500К₽+",
                        "description": "Корпоративный",
                    },
                    {
                        "id": "sales:cb_budget_unknown",
                        "title": "💡 Нужен расчёт",
                        "description": "Помогите оценить",
                    },
                ],
            }
        ],
    )


# ─── TZ Quiz (WA-10) ─────────────────────────────────────────


def tz_result_buttons() -> dict[str, Any]:
    """After TZ generation — action buttons."""
    return _quick_reply(
        body="Что дальше?",
        buttons=[
            ("tz:pay_sprint", "💳 Оплатить спринт"),
            ("tz:restart", "✏️ Уточнить"),
            ("nav:welcome", "← Меню"),
        ],
    )


def tz_project_type_list() -> dict[str, Any]:
    """TZ Q1: Project type (6 options -> list)."""
    return _list_message(
        body="🎯 Какой тип проекта?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Тип проекта",
                "rows": [
                    {
                        "id": "tz:type_chatbot",
                        "title": "🤖 AI-ассистент",
                        "description": "Чат-бот",
                    },
                    {
                        "id": "tz:type_voice",
                        "title": "📞 Голосовой бот",
                        "description": "Телефония",
                    },
                    {
                        "id": "tz:type_integration",
                        "title": "🔗 Интеграция",
                        "description": "CRM / 1С",
                    },
                    {
                        "id": "tz:type_web",
                        "title": "🌐 Веб-приложение",
                        "description": "SaaS",
                    },
                    {
                        "id": "tz:type_telegram",
                        "title": "📱 Telegram-бот",
                        "description": "Мессенджер",
                    },
                    {
                        "id": "tz:type_other",
                        "title": "🔧 Другое",
                        "description": "Опишу задачу",
                    },
                ],
            }
        ],
    )


def tz_business_goal_list() -> dict[str, Any]:
    """TZ Q2: Business goal (5 options -> list)."""
    return _list_message(
        body="📊 Какая бизнес-цель?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Бизнес-цель",
                "rows": [
                    {
                        "id": "tz:goal_cost",
                        "title": "📉 Снизить расходы",
                        "description": "На персонал",
                    },
                    {
                        "id": "tz:goal_sales",
                        "title": "📈 Увеличить продажи",
                        "description": "Рост выручки",
                    },
                    {
                        "id": "tz:goal_automation",
                        "title": "⏱️ Автоматизация",
                        "description": "Рутинные задачи",
                    },
                    {
                        "id": "tz:goal_service",
                        "title": "🎯 Клиентский сервис",
                        "description": "Улучшить обслуживание",
                    },
                    {
                        "id": "tz:goal_scale",
                        "title": "🚀 Масштабирование",
                        "description": "Рост бизнеса",
                    },
                ],
            }
        ],
    )


def tz_timeline_list() -> dict[str, Any]:
    """TZ Q3: Timeline (4 options -> list)."""
    return _list_message(
        body="⏰ Когда нужно запустить?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Сроки",
                "rows": [
                    {
                        "id": "tz:time_urgent",
                        "title": "🔥 1-2 недели",
                        "description": "Срочно",
                    },
                    {
                        "id": "tz:time_month",
                        "title": "📅 В течение месяца",
                        "description": "Стандартный срок",
                    },
                    {
                        "id": "tz:time_quarter",
                        "title": "📆 В течение квартала",
                        "description": "Без спешки",
                    },
                    {
                        "id": "tz:time_research",
                        "title": "🔍 Пока изучаю",
                        "description": "Исследую варианты",
                    },
                ],
            }
        ],
    )


def tz_budget_list() -> dict[str, Any]:
    """TZ Q4: Budget (5 options -> list)."""
    return _list_message(
        body="💰 Какой бюджет планируете?",
        button_text="Выбрать",
        sections=[
            {
                "title": "Бюджет",
                "rows": [
                    {
                        "id": "tz:budget_50",
                        "title": "50-100К₽",
                        "description": "Начальный",
                    },
                    {
                        "id": "tz:budget_100",
                        "title": "100-200К₽",
                        "description": "Средний",
                    },
                    {
                        "id": "tz:budget_200",
                        "title": "200-500К₽",
                        "description": "Расширенный",
                    },
                    {
                        "id": "tz:budget_500",
                        "title": "500К₽+",
                        "description": "Корпоративный",
                    },
                    {
                        "id": "tz:budget_calculate",
                        "title": "💡 Нужен расчёт",
                        "description": "Помогите оценить",
                    },
                ],
            }
        ],
    )


# ─── FAQ ──────────────────────────────────────────────────────


def faq_menu_buttons() -> dict[str, Any]:
    """FAQ category selector (3 quick-reply buttons)."""
    return _quick_reply(
        body="Выберите раздел 👇",
        buttons=[
            ("faq:cat_product", "🤖 Продукт"),
            ("faq:cat_install", "🛠️ Установка"),
            ("faq:cat_pricing", "💰 Цены"),
        ],
    )


def faq_back_buttons(section: str) -> dict[str, Any]:
    """Back-navigation after FAQ answer.

    Args:
        section: Which section to return to ('product', 'install', 'pricing').
    """
    return _quick_reply(
        body="Выберите действие 👇",
        buttons=[
            (f"faq:back_{section}", "← К вопросам"),
            ("faq:back_menu", "← К разделам"),
            ("nav:welcome", "🏠 Домой"),
        ],
    )


def faq_list() -> dict[str, Any]:
    """Full FAQ as a list message (3 sections, all 11 questions)."""
    return _list_message(
        body="📚 Выберите вопрос:",
        button_text="Открыть FAQ",
        sections=[
            {
                "title": "Продукт",
                "rows": [
                    {
                        "id": "faq:what_is",
                        "title": "Что это?",
                        "description": "О системе",
                    },
                    {
                        "id": "faq:offline",
                        "title": "Офлайн работа",
                        "description": "Работает без интернета?",
                    },
                    {
                        "id": "faq:security",
                        "title": "Безопасность",
                        "description": "Данные в безопасности?",
                    },
                    {
                        "id": "faq:vs_cloud",
                        "title": "Отличия от облаков",
                        "description": "Vs ChatGPT/Claude",
                    },
                    {
                        "id": "faq:cloud_models",
                        "title": "Облачные модели",
                        "description": "Работает с облаком?",
                    },
                ],
            },
            {
                "title": "Установка",
                "rows": [
                    {
                        "id": "faq:hardware",
                        "title": "Требования",
                        "description": "Какое железо нужно?",
                    },
                    {
                        "id": "faq:install",
                        "title": "Установка",
                        "description": "Как установить?",
                    },
                    {
                        "id": "faq:integrations",
                        "title": "Интеграции",
                        "description": "Какие интеграции?",
                    },
                ],
            },
            {
                "title": "Цены и поддержка",
                "rows": [
                    {
                        "id": "faq:price",
                        "title": "Стоимость",
                        "description": "Сколько стоит?",
                    },
                    {
                        "id": "faq:support",
                        "title": "Поддержка",
                        "description": "Есть ли техподдержка?",
                    },
                    {
                        "id": "faq:free_trial",
                        "title": "Пробный период",
                        "description": "Можно попробовать?",
                    },
                ],
            },
        ],
    )


def faq_product_list() -> dict[str, Any]:
    """FAQ Product section questions."""
    return _list_message(
        body="🤖 Раздел: Продукт\n\nВыберите вопрос:",
        button_text="Вопросы",
        sections=[
            {
                "title": "Продукт",
                "rows": [
                    {
                        "id": "faq:what_is",
                        "title": "Что это?",
                        "description": "Об AI Secretary",
                    },
                    {
                        "id": "faq:offline",
                        "title": "Офлайн работа",
                        "description": "Работает без интернета?",
                    },
                    {
                        "id": "faq:security",
                        "title": "Безопасность",
                        "description": "Данные в безопасности?",
                    },
                    {
                        "id": "faq:vs_cloud",
                        "title": "Отличия от облаков",
                        "description": "Vs ChatGPT/Claude",
                    },
                    {
                        "id": "faq:cloud_models",
                        "title": "Облачные модели",
                        "description": "Работает с облаком?",
                    },
                ],
            }
        ],
    )


def faq_install_list() -> dict[str, Any]:
    """FAQ Installation section questions."""
    return _list_message(
        body="🛠️ Раздел: Установка\n\nВыберите вопрос:",
        button_text="Вопросы",
        sections=[
            {
                "title": "Установка",
                "rows": [
                    {
                        "id": "faq:hardware",
                        "title": "Требования",
                        "description": "Какое железо нужно?",
                    },
                    {
                        "id": "faq:install",
                        "title": "Установка",
                        "description": "Как установить?",
                    },
                    {
                        "id": "faq:integrations",
                        "title": "Интеграции",
                        "description": "Какие интеграции?",
                    },
                ],
            }
        ],
    )


def faq_pricing_list() -> dict[str, Any]:
    """FAQ Pricing & Support section questions."""
    return _list_message(
        body="💰 Раздел: Цены и поддержка\n\nВыберите вопрос:",
        button_text="Вопросы",
        sections=[
            {
                "title": "Цены и поддержка",
                "rows": [
                    {
                        "id": "faq:price",
                        "title": "Стоимость",
                        "description": "Сколько стоит?",
                    },
                    {
                        "id": "faq:support",
                        "title": "Поддержка",
                        "description": "Есть ли техподдержка?",
                    },
                    {
                        "id": "faq:free_trial",
                        "title": "Пробный период",
                        "description": "Можно попробовать?",
                    },
                ],
            }
        ],
    )
