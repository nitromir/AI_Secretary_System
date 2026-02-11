# Payments (Платежи)

Настройка приёма платежей в Telegram-ботах через Telegram Stars, YooKassa и YooMoney.

## Скриншот

<!-- Вставьте скриншот страницы Payments -->
![Payments](images/payments.png)

## Концепция

Каждый Telegram-бот может принимать платежи тремя способами:
- **Telegram Stars (XTR)** — нативная валюта Telegram, без комиссии
- **YooKassa (RUB)** — через Telegram Payments API с поддержкой банковских карт
- **YooMoney (RUB)** — OAuth2 интеграция с кошельком ЮMoney

Все три метода работают параллельно — можно настроить один или несколько для каждого бота.

## Telegram Stars (XTR)

### Настройка

| Параметр | Описание |
|----------|----------|
| **Включён** | Переключатель активации |
| **Star Rate** | Курс конвертации 1 XTR = N рублей (для расчёта цен) |

### Как работает

```
1. Бот получает команду /buy или inline-кнопку оплаты
2. Создаёт Telegram Invoice с ценой в stars (XTR)
3. Пользователь оплачивает stars через Telegram
4. Telegram отправляет PreCheckoutQuery → бот подтверждает
5. После успешной оплаты → SuccessfulPayment update
6. Бот обрабатывает платёж и выдаёт продукт
```

### Преимущества

- **Без комиссии** для получателя
- **Мгновенная обработка** — нет задержек
- **Кроссплатформенность** — работает везде, где есть Telegram

## YooKassa (RUB)

### Настройка

| Параметр | Описание |
|----------|----------|
| **Включён** | Переключатель активации |
| **Provider Token** | Токен магазина YooKassa для Telegram Payments |

### Получение Provider Token

1. Зарегистрируйтесь в [YooKassa](https://yookassa.ru/)
2. Создайте магазин
3. Откройте настройки → Telegram Payments API
4. Скопируйте `provider_token`

### Как работает

```
1. Бот создаёт Telegram Invoice с provider_token
2. Цена указывается в копейках (100 = 1₽)
3. Пользователь оплачивает картой через Telegram
4. YooKassa обрабатывает платёж
5. Telegram отправляет PreCheckoutQuery → бот подтверждает
6. SuccessfulPayment → продукт выдан
```

### Комиссия

- **YooKassa**: 2.8% + 10₽ за транзакцию (стандартный тариф)

## YooMoney (RUB)

### Концепция

YooMoney интегрируется через **OAuth2 + Quickpay URL**:
- Бот получает доступ к кошельку ЮMoney через OAuth2
- Генерирует персонализированные ссылки на оплату (Quickpay)
- Получает уведомления о платежах через webhook

### Настройка OAuth2

#### Шаг 1: Регистрация приложения

1. Откройте [YooMoney Apps](https://yoomoney.ru/myservices/new)
2. Создайте приложение типа **"Веб-сервис"**
3. Укажите Redirect URI: `https://your-server.com/admin/telegram/instances/{bot_id}/yoomoney/callback`
4. Получите `client_id` и `client_secret`

#### Шаг 2: Настройка в админке

| Параметр | Описание |
|----------|----------|
| **Включён** | Переключатель активации |
| **Client ID** | ID приложения из YooMoney |
| **Client Secret** | Секретный ключ приложения |
| **Wallet ID** | Номер кошелька ЮMoney (410...) |
| **Notification Secret** | Секретная строка для проверки подписи вебхуков |

#### Шаг 3: Авторизация

1. Нажмите **"Получить ссылку авторизации"**
2. Перейдите по ссылке и подтвердите доступ к кошельку
3. После редиректа система автоматически обменяет `code` на `access_token`
4. Токен сохраняется в БД

### OAuth2 Flow

```
1. GET /admin/telegram/instances/{id}/yoomoney/auth-url
   → возвращает authorization URL

2. Пользователь переходит по ссылке → подтверждает доступ

3. YooMoney редиректит на callback с ?code=...

4. GET /admin/telegram/instances/{id}/yoomoney/callback?code=...
   → система обменивает code на access_token

5. Token сохраняется в yoomoney_access_token (БД)
```

### Quickpay URL

Бот генерирует персональные ссылки для оплаты:

```
https://yoomoney.ru/quickpay/confirm?
  receiver={wallet_id}&
  quickpay-form=shop&
  targets={description}&
  paymentType=PC&
  sum={amount}&
  label={bot_id}_{product_id}_{user_id}&
  successURL={success_url}
```

| Параметр | Описание |
|----------|----------|
| **receiver** | Номер кошелька получателя |
| **targets** | Описание платежа (например, "Оплата услуги X") |
| **sum** | Сумма в рублях |
| **label** | Метка для идентификации (формат: `bot_id_product_id_user_id`) |
| **successURL** | URL для редиректа после оплаты |

### Webhook

YooMoney отправляет уведомления о платежах на `POST /webhooks/yoomoney`.

#### Настройка в YooMoney

1. Откройте настройки кошелька → Уведомления
2. Укажите URL: `https://your-server.com/webhooks/yoomoney`
3. Включите HTTP-уведомления
4. Укажите `notification_secret` (та же строка, что в админке)

#### Формат уведомления

```http
POST /webhooks/yoomoney
Content-Type: application/x-www-form-urlencoded

notification_type=p2p-incoming&
operation_id=123456789&
amount=100.00&
currency=643&
datetime=2026-02-11T12:00:00Z&
sender=410011234567890&
codepro=false&
label=bot-instance-id_product_1_user_12345&
sha1_hash=abcdef1234567890
```

#### Проверка подписи

Вебхук вычисляет SHA-1 от строки:

```
notification_type&operation_id&amount&currency&datetime&sender&codepro&notification_secret&label
```

Если `sha1_hash` из запроса совпадает — платёж подтверждён.

#### Обработка

```
1. Webhook получает уведомление
2. Проверяет sha1_hash
3. Парсит label → извлекает bot_id, product_id, user_id
4. Сохраняет платёж в БД (PaymentRepository)
5. Записывает JSON-файл в data/payment_notifications/{operation_id}.json
6. Бот читает файл и выдаёт продукт пользователю
```

### Проверка статуса

API: `GET /admin/telegram/instances/{id}/yoomoney/status`

```json
{
  "configured": true,
  "connected": true,
  "wallet_id": "410011234567890"
}
```

### Отключение

API: `POST /admin/telegram/instances/{id}/yoomoney/disconnect`

Удаляет `access_token` из БД (OAuth2 токен становится недействительным на стороне YooMoney только после явной отмены в настройках кошелька).

## Продукты

Каждый бот имеет список продуктов для продажи:

| Поле | Описание |
|------|----------|
| **Title** | Название продукта |
| **Description** | Описание (до 255 символов) |
| **Price (RUB)** | Цена в рублях (для YooKassa и YooMoney) |
| **Price (Stars)** | Цена в XTR (для Telegram Stars) |

Продукты настраиваются в разделе **Sales** (см. [[Sales]]).

## Статистика платежей

### Список платежей

API: `GET /admin/telegram/instances/{id}/payments`

Возвращает все платежи для конкретного бота:

```json
{
  "payments": [
    {
      "id": 1,
      "bot_instance_id": "sales-bot",
      "user_id": 12345,
      "product_id": 1,
      "amount": 100.00,
      "currency": "RUB",
      "payment_method": "yoomoney",
      "status": "completed",
      "created_at": "2026-02-11T12:00:00Z"
    }
  ]
}
```

### Агрегированная статистика

API: `GET /admin/telegram/instances/{id}/payments/stats`

```json
{
  "total_revenue": 15000.00,
  "total_payments": 150,
  "by_method": {
    "telegram_stars": 80,
    "yookassa": 50,
    "yoomoney": 20
  },
  "by_product": {
    "product_1": 12000.00,
    "product_2": 3000.00
  }
}
```

## API эндпоинты

### YooMoney OAuth2

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/admin/telegram/instances/{id}/yoomoney/auth-url` | Получить OAuth2 authorization URL |
| GET | `/admin/telegram/instances/{id}/yoomoney/callback` | OAuth2 callback (обмен code на token) |
| GET | `/admin/telegram/instances/{id}/yoomoney/status` | Статус подключения |
| POST | `/admin/telegram/instances/{id}/yoomoney/disconnect` | Отключить интеграцию |

### Платежи

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/admin/telegram/instances/{id}/payments` | Список платежей бота |
| GET | `/admin/telegram/instances/{id}/payments/stats` | Статистика платежей |

### Webhook (публичный, без JWT)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/webhooks/yoomoney` | Приём уведомлений от YooMoney |

## RBAC

- **Admin** — видит и управляет платежами всех ботов
- **User/Web** — только свои боты (`owner_id`)
- **Guest** — только просмотр статистики (без доступа к sensitive данным: tokens, secrets)

## Безопасность

| Механизм | Описание |
|----------|----------|
| **SHA-1 проверка** | YooMoney webhook проверяет подпись `sha1_hash` |
| **Label format** | Метка `bot_id_product_id_user_id` однозначно идентифицирует платёж |
| **Notification secret** | Хранится в БД, не передаётся в API responses |
| **OAuth2 tokens** | `access_token` хранится зашифрованным в БД (если настроено) |

## Типичные проблемы

### YooMoney webhook не срабатывает

**Решение:**
1. Проверьте, что в настройках кошелька ЮMoney включены HTTP-уведомления
2. Убедитесь, что `notification_secret` совпадает в админке и в настройках кошелька
3. Проверьте логи: `data/payment_notifications/` — записываются ли файлы?

### Telegram Stars недоступны

**Решение:**
- Убедитесь, что бот зарегистрирован через [@BotFather](https://t.me/BotFather)
- Telegram Stars доступны только для верифицированных ботов

### YooKassa PreCheckoutQuery отклоняется

**Решение:**
1. Проверьте правильность `provider_token`
2. Убедитесь, что магазин в YooKassa активен
3. Проверьте логи бота на наличие ошибок при обработке `PreCheckoutQuery`

---

← [[Telegram]] | [[Sales]] →
