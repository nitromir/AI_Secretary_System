import type { DemoRoute } from './types'
import { daysAgo } from './store'

const prompts = [
  { id: 1, bot_id: 'bot-sales', prompt_key: 'sales_main', name: 'Основной промпт продаж', description: 'Главный промпт для консультирования', system_prompt: 'Ты — Марина, менеджер по продажам AI-секретаря. Помогай выбрать тариф, отвечай на вопросы о продукте.', temperature: 0.7, max_tokens: 2048, enabled: true, order: 1, created: daysAgo(14) },
  { id: 2, bot_id: 'bot-sales', prompt_key: 'objection_handler', name: 'Обработка возражений', description: 'Промпт для работы с возражениями клиентов', system_prompt: 'Ты — опытный менеджер. Клиент высказал возражение. Мягко и аргументированно развей сомнения.', temperature: 0.6, max_tokens: 1024, enabled: true, order: 2, created: daysAgo(14) },
  { id: 3, bot_id: 'bot-sales', prompt_key: 'closer', name: 'Закрытие сделки', description: 'Промпт для завершения продажи', system_prompt: 'Клиент готов к покупке. Помоги оформить заказ, предложи оптимальный тариф.', temperature: 0.5, max_tokens: 1024, enabled: true, order: 3, created: daysAgo(14) },
]

const quizQuestions = [
  { id: 1, bot_id: 'bot-sales', question_key: 'business_type', text: 'Какой у вас бизнес?', order: 1, enabled: true, options: [{ label: 'Услуги', value: 'services', icon: '🛠' }, { label: 'Товары', value: 'goods', icon: '📦' }, { label: 'IT', value: 'it', icon: '💻' }, { label: 'Другое', value: 'other', icon: '🏢' }], created: daysAgo(14) },
  { id: 2, bot_id: 'bot-sales', question_key: 'team_size', text: 'Сколько человек в команде?', order: 2, enabled: true, options: [{ label: '1-5', value: 'small' }, { label: '6-20', value: 'medium' }, { label: '20+', value: 'large' }], created: daysAgo(14) },
  { id: 3, bot_id: 'bot-sales', question_key: 'budget', text: 'Какой бюджет на автоматизацию?', order: 3, enabled: true, options: [{ label: 'до 10к', value: 'low' }, { label: '10-30к', value: 'mid' }, { label: '30к+', value: 'high' }], created: daysAgo(14) },
]

const segments = [
  { id: 1, bot_id: 'bot-sales', segment_key: 'small_service', name: 'Малый бизнес (услуги)', description: 'Небольшие компании в сфере услуг', path: 'services>small>low', match_rules: { business_type: 'services', team_size: 'small' }, priority: 1, agent_prompt_key: 'sales_main', enabled: true, created: daysAgo(14) },
  { id: 2, bot_id: 'bot-sales', segment_key: 'medium_it', name: 'Средний IT бизнес', description: 'IT-компании среднего размера', path: 'it>medium>mid', match_rules: { business_type: 'it', team_size: 'medium' }, priority: 2, agent_prompt_key: 'sales_main', enabled: true, created: daysAgo(14) },
]

const testimonials = [
  { id: 1, bot_id: 'bot-sales', text: 'AI-секретарь сэкономил нам 40 часов в неделю. Клиенты довольны скоростью ответа!', author: 'Анна К., стоматология "Улыбка"', rating: 5, enabled: true, order: 1, created: daysAgo(20) },
  { id: 2, bot_id: 'bot-sales', text: 'Подключили за 2 дня, бот отвечает лучше живого оператора. Рекомендую!', author: 'Дмитрий В., автосервис', rating: 5, enabled: true, order: 2, created: daysAgo(15) },
  { id: 3, bot_id: 'bot-sales', text: 'Клонировали голос нашего менеджера — клиенты не отличают от живого.', author: 'Елена М., риелторское агентство', rating: 4, enabled: true, order: 3, created: daysAgo(10) },
]

const funnelData = {
  start: 245,
  quiz_started: 189,
  quiz_completed: 142,
  offer_shown: 138,
  payment_started: 67,
  payment_completed: 34,
}

export const botSalesRoutes: DemoRoute[] = [
  // Prompts
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/prompts$/,
    handler: () => ({ prompts }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/prompts$/,
    handler: ({ body }) => ({ prompt: { id: Date.now(), ...(body as object), created: daysAgo(0) } }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/prompts\/(\d+)$/,
    handler: ({ body }) => ({ prompt: body }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/prompts\/(\d+)$/,
    handler: () => ({ status: 'ok' }),
  },
  // Quiz
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/quiz$/,
    handler: () => ({ questions: quizQuestions }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/quiz$/,
    handler: ({ body }) => ({ question: { id: Date.now(), ...(body as object), created: daysAgo(0) } }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/quiz\/(\d+)$/,
    handler: ({ body }) => ({ question: body }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/quiz\/(\d+)$/,
    handler: () => ({ status: 'ok' }),
  },
  // Segments
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/segments$/,
    handler: () => ({ segments }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/segments$/,
    handler: ({ body }) => ({ segment: { id: Date.now(), ...(body as object) } }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/segments\/(\d+)$/,
    handler: ({ body }) => ({ segment: body }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/segments\/(\d+)$/,
    handler: () => ({ status: 'ok' }),
  },
  // Followups
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/followups$/,
    handler: () => ({
      rules: [
        { id: 1, bot_id: 'bot-sales', name: 'Напоминание', trigger: 'quiz_completed', delay_hours: 24, message_template: 'Здравствуйте! Вчера вы интересовались AI-секретарём. Есть вопросы?', buttons: [{ text: 'Да, расскажите', callback_data: 'tell_more' }], max_sends: 1, enabled: true, order: 1 },
      ],
    }),
  },
  {
    method: ['POST', 'PUT', 'DELETE'],
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/followups/,
    handler: ({ body }) => ({ status: 'ok', rule: body }),
  },
  // Testimonials
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/testimonials$/,
    handler: () => ({ testimonials }),
  },
  {
    method: ['POST', 'PUT', 'DELETE'],
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/testimonials/,
    handler: ({ body }) => ({ status: 'ok', testimonial: body }),
  },
  // Hardware
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/hardware$/,
    handler: () => ({
      specs: [
        { id: 1, bot_id: 'bot-sales', gpu_name: 'RTX 3060', gpu_vram_gb: 12, gpu_family: 'Ampere', recommended_llm: 'Qwen2.5-7B-AWQ', recommended_tts: 'XTTS v2', recommended_stt: 'Vosk', quality_stars: 4, speed_note: 'Быстрый отклик', enabled: true, order: 1 },
        { id: 2, bot_id: 'bot-sales', gpu_name: 'RTX 4090', gpu_vram_gb: 24, gpu_family: 'Ada Lovelace', recommended_llm: 'Qwen2.5-14B', recommended_tts: 'XTTS v2 + OpenVoice', recommended_stt: 'Whisper Large', quality_stars: 5, speed_note: 'Максимальное качество', enabled: true, order: 2 },
      ],
    }),
  },
  {
    method: ['POST', 'PUT', 'DELETE'],
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/hardware/,
    handler: ({ body }) => ({ status: 'ok', spec: body }),
  },
  // A/B Tests
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/abtests$/,
    handler: () => ({ tests: [] }),
  },
  {
    method: ['POST', 'PUT', 'DELETE'],
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/abtests/,
    handler: ({ body }) => ({ status: 'ok', test: body }),
  },
  // Subscribers
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/subscribers$/,
    handler: () => ({
      subscribers: [
        { id: 1, bot_id: 'bot-sales', user_id: 100001, subscribed: true, subscribed_at: daysAgo(30), username: 'anna_k', first_name: 'Анна' },
        { id: 2, bot_id: 'bot-sales', user_id: 100002, subscribed: true, subscribed_at: daysAgo(25), username: 'dmitriy_v', first_name: 'Дмитрий' },
        { id: 3, bot_id: 'bot-sales', user_id: 100003, subscribed: true, subscribed_at: daysAgo(20), username: null, first_name: 'Елена' },
        { id: 4, bot_id: 'bot-sales', user_id: 100004, subscribed: false, subscribed_at: daysAgo(18), unsubscribed_at: daysAgo(5), username: 'ivan_p', first_name: 'Иван' },
        { id: 5, bot_id: 'bot-sales', user_id: 100005, subscribed: true, subscribed_at: daysAgo(15), username: 'maria_s', first_name: 'Мария' },
        { id: 6, bot_id: 'bot-sales', user_id: 100006, subscribed: true, subscribed_at: daysAgo(10), username: 'alexey_r', first_name: 'Алексей' },
        { id: 7, bot_id: 'bot-sales', user_id: 100007, subscribed: true, subscribed_at: daysAgo(7), username: null, first_name: null },
        { id: 8, bot_id: 'bot-sales', user_id: 100008, subscribed: true, subscribed_at: daysAgo(3), username: 'olga_n', first_name: 'Ольга' },
      ],
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/subscribers\/stats$/,
    handler: () => ({ stats: { total_active: 156 } }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/broadcast$/,
    handler: ({ body }) => {
      const userIds = (body as { user_ids?: number[] })?.user_ids || []
      const count = userIds.length || 156
      return { status: 'ok', sent_count: count, failed_count: 0, errors: [] }
    },
  },
  // GitHub Config
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/github-config$/,
    handler: () => ({ config: null }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/github-config$/,
    handler: ({ body }) => ({ config: body }),
  },
  // Funnel
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/funnel\/daily$/,
    handler: () => ({
      report: {
        funnel: funnelData,
        subscribers: 156,
        segments: { small_service: 89, medium_it: 42, other: 25 },
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/funnel/,
    handler: () => ({ funnel: funnelData }),
  },
  // Users
  {
    method: 'GET',
    pattern: /^\/admin\/telegram\/instances\/([^/]+)\/users/,
    handler: () => ({ users: [] }),
  },
]
