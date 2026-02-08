# AI Chat Widget

Встраиваемый чат-виджет для любого сайта с поддержкой нескольких независимых инстансов.

## Архитектура

```
┌─────────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  shaerware.digital  │ ───► │  ngrok / tunnel  │ ───► │ localhost:8002  │
│  (GitHub Pages)     │      │  (публичный URL) │      │ (AI Secretary)  │
└─────────────────────┘      └──────────────────┘      └─────────────────┘
```

## Шаг 1: Установка ngrok

```bash
# Ubuntu/Debian
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
  | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null \
  && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
  | sudo tee /etc/apt/sources.list.d/ngrok.list \
  && sudo apt update \
  && sudo apt install ngrok

# Или скачать напрямую
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# Авторизация (бесплатный аккаунт на https://ngrok.com)
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

## Шаг 2: Запуск туннеля

```bash
# Запустить AI Secretary
./start_gpu.sh

# В другом терминале - запустить ngrok
ngrok http 8002

# Получите URL вида: https://abc123.ngrok-free.app
```

### Альтернатива: Cloudflare Tunnel (бесплатно, стабильнее)

```bash
# Установка
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# Быстрый туннель (без регистрации)
cloudflared tunnel --url http://localhost:8002

# Получите URL вида: https://random-name.trycloudflare.com
```

## Шаг 3: Интеграция на сайт

В файле `index.html` (и других страницах) **замените** блок Replain:

```html
<!-- БЫЛО (удалить): -->
<script>
  window.replainSettings = { id: 'ed7683ce-0512-4eac-a027-81886cb27c0b' };
  ...
</script>

<!-- СТАЛО (добавить перед </body>): -->
<script>
  window.aiChatSettings = {
    apiUrl: 'https://YOUR-NGROK-URL.ngrok-free.app',  // ← Ваш URL туннеля
    title: 'Марина - AI Ассистент',
    greeting: 'Здравствуйте! Компания Шаервэй Ди-Иджитал, чем могу помочь?',
    placeholder: 'Введите сообщение...',
    primaryColor: '#6366f1',  // Цвет кнопки
    position: 'right'         // 'left' или 'right'
  };
</script>
<script src="https://shaerware.github.io/cdn/ai-chat-widget.js"></script>
```

## Шаг 4: Загрузка виджета в репозиторий

```bash
# Клонировать репозиторий сайта
git clone https://github.com/ShaerWare/shaerware.github.io.git
cd shaerware.github.io

# Создать папку для CDN файлов
mkdir -p cdn

# Скопировать виджет
cp /path/to/AI_Secretary_System/web-widget/ai-chat-widget.js cdn/

# Закоммитить
git add cdn/ai-chat-widget.js
git commit -m "feat: add AI chat widget"
git push
```

## Multi-Instance Support

Можно создавать несколько виджетов с разными настройками (LLM, TTS, персона):

### Настройка через Admin Panel

1. Admin → Widget → Create New Widget
2. Настройте название, цвета, LLM, TTS
3. Получите код интеграции

### Интеграция разных инстансов

```html
<!-- Инстанс для продаж -->
<script src="https://api.example.com/widget.js?instance=sales"></script>

<!-- Инстанс для поддержки -->
<script src="https://api.example.com/widget.js?instance=support"></script>

<!-- Default инстанс (без параметра) -->
<script src="https://api.example.com/widget.js"></script>
```

### API управления инстансами

```bash
# Список инстансов
curl http://localhost:8002/admin/widget/instances

# Создать инстанс
curl -X POST http://localhost:8002/admin/widget/instances \
  -H "Content-Type: application/json" \
  -d '{"name": "Sales Widget", "title": "Sales Assistant", "primary_color": "#10b981"}'

# Обновить инстанс
curl -X PUT http://localhost:8002/admin/widget/instances/{id} \
  -H "Content-Type: application/json" \
  -d '{"llm_backend": "cloud:gemini-id", "tts_voice": "marina"}'
```

## Настройки виджета

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `apiUrl` | URL туннеля к AI Secretary | (обязательный) |
| `title` | Заголовок окна чата | `AI Ассистент` |
| `greeting` | Приветственное сообщение | `Здравствуйте!...` |
| `placeholder` | Placeholder в поле ввода | `Введите сообщение...` |
| `primaryColor` | Цвет кнопки и акцентов | `#6366f1` |
| `position` | Позиция кнопки | `right` |
| `sessionKey` | Ключ localStorage | `ai_chat_session` |

## JavaScript API

```javascript
// Открыть чат программно
window.aiChat.open();

// Закрыть чат
window.aiChat.close();

// Очистить сессию (новый разговор)
window.aiChat.clearSession();
```

## Интеграция с cookie consent

Если нужно загружать виджет только после согласия:

```javascript
function loadAIChat() {
  if (document.getElementById('ai-chat-script')) return;

  window.aiChatSettings = {
    apiUrl: 'https://YOUR-NGROK-URL.ngrok-free.app',
    title: 'Марина - AI Ассистент'
  };

  const script = document.createElement('script');
  script.id = 'ai-chat-script';
  script.src = 'https://shaerware.github.io/cdn/ai-chat-widget.js';
  document.body.appendChild(script);
}

// Вызвать после принятия cookies
if (localStorage.getItem('cookieConsent') === 'accepted') {
  loadAIChat();
}
```

## Постоянный URL (рекомендуется)

Для production рекомендуется:

1. **Cloudflare Tunnel с фиксированным доменом:**
   ```bash
   cloudflared tunnel login
   cloudflared tunnel create ai-secretary
   cloudflared tunnel route dns ai-secretary ai.shaerware.digital
   cloudflared tunnel run ai-secretary
   ```

2. **Или VPS с публичным IP** + nginx reverse proxy

3. **Или ngrok с резервированным доменом** (платная функция)

## Проверка работы

1. Откройте https://shaerware.digital
2. Нажмите на кнопку чата в правом нижнем углу
3. Отправьте сообщение
4. Проверьте логи: `tail -f logs/orchestrator.log`

## Отладка

```bash
# Проверить что API доступен через туннель
curl https://YOUR-NGROK-URL.ngrok-free.app/health

# Проверить CORS
curl -I -X OPTIONS https://YOUR-NGROK-URL.ngrok-free.app/admin/chat/sessions \
  -H "Origin: https://shaerware.digital"
```
