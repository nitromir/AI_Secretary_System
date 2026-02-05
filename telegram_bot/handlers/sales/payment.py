"""Payment handlers for Telegram Payments API integration."""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    ContentType,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from ...config import get_telegram_settings
from ...sales.database import get_sales_db
from ...sales.keyboards import contact_kb


logger = logging.getLogger(__name__)
router = Router()

# Payment product info
PRODUCT_TITLE = "AI Secretary — Установка под ключ"
PRODUCT_DESCRIPTION = (
    "Полная установка AI Secretary на ваш сервер:\n"
    "✅ Подключение по SSH\n"
    "✅ Установка за 30 минут\n"
    "✅ Оптимизация под ваш GPU\n"
    "✅ Проверка работоспособности\n"
    "✅ Краткий инструктаж\n"
    "🔒 Гарантия возврата"
)


async def send_invoice(message: Message, user_id: int) -> bool:
    """Send payment invoice to user.

    Args:
        message: Message to reply to
        user_id: Telegram user ID for payload

    Returns:
        True if invoice was sent, False if payments not configured
    """
    settings = get_telegram_settings()

    if not settings.payment_provider_token:
        logger.warning("Payment provider token not configured")
        return False

    prices = [
        LabeledPrice(
            label="Установка AI Secretary",
            amount=settings.payment_price_basic,
        )
    ]

    try:
        await message.answer_invoice(
            title=PRODUCT_TITLE,
            description=PRODUCT_DESCRIPTION,
            payload=f"basic_install_{user_id}_{datetime.utcnow().timestamp()}",
            provider_token=settings.payment_provider_token,
            currency=settings.payment_currency,
            prices=prices,
            start_parameter="basic_install",
            # Optional: photo
            # photo_url="https://...",
            # photo_size=512,
            # photo_width=512,
            # photo_height=512,
            need_name=True,
            need_phone_number=True,
            need_email=True,
            send_phone_number_to_provider=False,
            send_email_to_provider=False,
            is_flexible=False,
            protect_content=False,
        )

        logger.info(f"Invoice sent to user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to send invoice: {e}")
        return False


@router.callback_query(F.data == "sales:basic_pay")
async def basic_pay(callback: CallbackQuery) -> None:
    """Handle payment button — send invoice or fallback to contact."""
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    user_id = callback.from_user.id

    db = await get_sales_db()
    await db.log_event(user_id, "payment_initiated")

    # Try to send invoice
    if await send_invoice(callback.message, user_id):
        await callback.answer("📄 Счёт отправлен!")
    else:
        # Fallback: payments not configured, show contact info
        await callback.message.answer(
            "💳 **Оплата установки — 5,000₽**\n\n"
            "Для оплаты свяжитесь с нами:\n\n"
            "📱 Telegram: @ShaerWare\n\n"
            "Способы оплаты:\n"
            "• Перевод на карту\n"
            "• ЮMoney\n"
            "• Криптовалюта\n\n"
            "После оплаты согласуем время установки.",
            reply_markup=contact_kb(),
        )
        await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    """Handle pre-checkout query — verify the order."""
    user_id = pre_checkout_query.from_user.id

    db = await get_sales_db()
    await db.log_event(
        user_id,
        "pre_checkout",
        {
            "total": pre_checkout_query.total_amount,
            "currency": pre_checkout_query.currency,
        },
    )

    # Always approve (can add validation logic here)
    await pre_checkout_query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {user_id}")


@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message) -> None:
    """Handle successful payment."""
    if not message.from_user or not message.successful_payment:
        return

    user_id = message.from_user.id
    payment = message.successful_payment
    first_name = message.from_user.first_name or "друг"

    db = await get_sales_db()

    # Log payment event with all details
    await db.log_event(
        user_id,
        "payment_successful",
        {
            "total_amount": payment.total_amount,
            "currency": payment.currency,
            "invoice_payload": payment.invoice_payload,
            "telegram_payment_charge_id": payment.telegram_payment_charge_id,
            "provider_payment_charge_id": payment.provider_payment_charge_id,
        },
    )

    # Save payment to database
    customer_name = None
    customer_phone = None
    customer_email = None
    if payment.order_info:
        customer_name = payment.order_info.name
        customer_phone = payment.order_info.phone_number
        customer_email = payment.order_info.email

    await db.save_payment(
        user_id=user_id,
        telegram_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id or "",
        amount=payment.total_amount,
        currency=payment.currency,
        product="basic_install",
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
    )

    # Mark user as converted
    await db.update_user(user_id, funnel_completed=1)

    logger.info(
        f"Payment successful! User {user_id}, "
        f"amount: {payment.total_amount} {payment.currency}, "
        f"charge_id: {payment.telegram_payment_charge_id}"
    )

    # Send confirmation to user
    await message.answer(
        f"🎉 **{first_name}, спасибо за покупку!**\n\n"
        f"✅ Оплата получена: {payment.total_amount // 100} {payment.currency}\n\n"
        f"**Что дальше:**\n"
        f"1. Мы свяжемся с вами в течение 2 часов\n"
        f"2. Согласуем время установки\n"
        f"3. Подключимся к вашему серверу\n"
        f"4. Установим AI Secretary за 30 минут\n\n"
        f"📱 Если нужно связаться срочно: @ShaerWare\n\n"
        f"Номер заказа: `{payment.telegram_payment_charge_id}`"
    )

    # Notify admin about new payment
    settings = get_telegram_settings()
    admin_ids = settings.get_admin_ids()

    for admin_id in admin_ids:
        try:
            from aiogram import Bot

            bot = Bot(token=settings.bot_token)

            admin_message = (
                f"🔔 **НОВЫЙ ЗАКАЗ!**\n\n"
                f"👤 Пользователь: {message.from_user.full_name}\n"
                f"📱 Username: @{message.from_user.username or 'не указан'}\n"
                f"🆔 ID: `{user_id}`\n\n"
                f"💰 Сумма: {payment.total_amount // 100} {payment.currency}\n"
                f"📋 Charge ID: `{payment.telegram_payment_charge_id}`\n\n"
                f"Контакты клиента:"
            )

            if payment.order_info:
                if payment.order_info.name:
                    admin_message += f"\n• Имя: {payment.order_info.name}"
                if payment.order_info.phone_number:
                    admin_message += f"\n• Телефон: {payment.order_info.phone_number}"
                if payment.order_info.email:
                    admin_message += f"\n• Email: {payment.order_info.email}"

            await bot.send_message(admin_id, admin_message)
            await bot.session.close()

        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
