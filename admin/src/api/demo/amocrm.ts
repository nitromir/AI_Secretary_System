import type { DemoRoute } from './types'
import { daysAgo, minutesAgo, nowISO } from './store'

let connected = true

const accountInfo = {
  id: 31234567,
  name: 'AI Секретарь Demo',
  subdomain: 'ai-sekretar-demo',
  currency: 'RUB',
  created_at: 1690000000,
}

const mockConfig = () => ({
  id: 1,
  subdomain: 'ai-sekretar-demo',
  client_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  client_secret_masked: '••••••••••••',
  redirect_uri: window.location.origin + '/admin/crm/oauth-redirect',
  is_connected: connected,
  sync_contacts: true,
  sync_leads: true,
  sync_tasks: false,
  auto_create_lead: true,
  lead_pipeline_id: 7001,
  lead_status_id: 42000001,
  webhook_url: window.location.origin + '/webhooks/amocrm',
  last_sync_at: connected ? minutesAgo(35) : null,
  contacts_count: connected ? 5 : 0,
  leads_count: connected ? 5 : 0,
  account_info: connected ? accountInfo : {},
  created: daysAgo(14),
  updated: minutesAgo(35),
})

const contacts = [
  { id: 50001, name: 'Иванов Алексей', custom_fields_values: [{ field_id: 1, values: [{ value: '+79991234501' }] }] },
  { id: 50002, name: 'Петрова Мария', custom_fields_values: [{ field_id: 1, values: [{ value: '+79991234502' }] }] },
  { id: 50003, name: 'Сидоров Дмитрий', custom_fields_values: [{ field_id: 1, values: [{ value: '+79991234503' }] }] },
  { id: 50004, name: 'Козлова Анна', custom_fields_values: [{ field_id: 1, values: [{ value: '+79991234504' }] }] },
  { id: 50005, name: 'Новиков Сергей', custom_fields_values: [{ field_id: 1, values: [{ value: '+79991234505' }] }] },
]

const leads = [
  { id: 60001, name: 'Подключение VoIP', price: 15000, pipeline_id: 7001, status_id: 42000001 },
  { id: 60002, name: 'Настройка секретаря', price: 25000, pipeline_id: 7001, status_id: 42000002 },
  { id: 60003, name: 'Интеграция CRM', price: 35000, pipeline_id: 7001, status_id: 42000003 },
  { id: 60004, name: 'Обучение персонала', price: 10000, pipeline_id: 7002, status_id: 42000011 },
  { id: 60005, name: 'Поддержка 6 мес', price: 60000, pipeline_id: 7002, status_id: 42000012 },
]

const pipelines = [
  {
    id: 7001,
    name: 'Продажи',
    sort: 1,
    is_main: true,
    _embedded: {
      statuses: [
        { id: 42000001, name: 'Новая заявка', sort: 1, color: '#99ccff' },
        { id: 42000002, name: 'В работе', sort: 2, color: '#ffff99' },
        { id: 42000003, name: 'Согласование', sort: 3, color: '#ffcc66' },
        { id: 42000004, name: 'Успешно', sort: 4, color: '#ccff66' },
      ],
    },
  },
  {
    id: 7002,
    name: 'Сервис',
    sort: 2,
    is_main: false,
    _embedded: {
      statuses: [
        { id: 42000011, name: 'Обращение', sort: 1, color: '#99ccff' },
        { id: 42000012, name: 'Выполняется', sort: 2, color: '#ffff99' },
        { id: 42000013, name: 'Закрыто', sort: 3, color: '#ccff66' },
      ],
    },
  },
]

const syncLogEntries = [
  { id: 1, direction: 'incoming', entity_type: 'contact', entity_id: 50001, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(35) },
  { id: 2, direction: 'incoming', entity_type: 'contact', entity_id: 50002, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(34) },
  { id: 3, direction: 'incoming', entity_type: 'lead', entity_id: 60001, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(33) },
  { id: 4, direction: 'incoming', entity_type: 'lead', entity_id: 60002, action: 'updated', details: { old_status: 42000001, new_status: 42000002 }, status: 'success', error_message: null, created: minutesAgo(32) },
  { id: 5, direction: 'outgoing', entity_type: 'contact', entity_id: 50003, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(31) },
  { id: 6, direction: 'incoming', entity_type: 'lead', entity_id: 60003, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(30) },
  { id: 7, direction: 'outgoing', entity_type: 'lead', entity_id: 60004, action: 'updated', details: null, status: 'error', error_message: 'Timeout connecting to amoCRM API', created: minutesAgo(29) },
  { id: 8, direction: 'incoming', entity_type: 'contact', entity_id: 50004, action: 'updated', details: null, status: 'success', error_message: null, created: minutesAgo(28) },
  { id: 9, direction: 'incoming', entity_type: 'lead', entity_id: 60005, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(27) },
  { id: 10, direction: 'outgoing', entity_type: 'contact', entity_id: 50005, action: 'created', details: null, status: 'success', error_message: null, created: minutesAgo(26) },
]

export const amocrmRoutes: DemoRoute[] = [
  // GET /admin/crm/config
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/config$/,
    handler: () => ({ config: mockConfig() }),
  },
  // POST /admin/crm/config
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/config$/,
    handler: ({ body }) => {
      const b = body as Record<string, unknown>
      if (b.subdomain !== undefined) Object.assign(accountInfo, { subdomain: b.subdomain })
      return { status: 'ok', config: mockConfig() }
    },
  },
  // GET /admin/crm/status
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/status$/,
    handler: () => ({
      connected,
      has_credentials: true,
      subdomain: 'ai-sekretar-demo',
      account_info: connected ? accountInfo : undefined,
      contacts_count: connected ? contacts.length : 0,
      leads_count: connected ? leads.length : 0,
      last_sync: connected ? minutesAgo(35) : null,
    }),
  },
  // GET /admin/crm/auth-url
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/auth-url$/,
    handler: () => ({
      auth_url: '#demo-oauth',
      redirect_uri: window.location.origin + '/admin/crm/oauth-redirect',
    }),
  },
  // POST /admin/crm/disconnect
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/disconnect$/,
    handler: () => {
      connected = false
      return { status: 'ok' }
    },
  },
  // POST /admin/crm/test
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/test$/,
    handler: () => ({
      status: 'ok',
      account: accountInfo,
    }),
  },
  // POST /admin/crm/refresh-token
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/refresh-token$/,
    handler: () => ({
      status: 'ok',
      expires_at: new Date(Date.now() + 86400000).toISOString(),
    }),
  },
  // GET /admin/crm/contacts
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/contacts$/,
    handler: () => ({ _embedded: { contacts } }),
  },
  // POST /admin/crm/contacts
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/contacts$/,
    handler: ({ body }) => {
      const b = body as { name: string; custom_fields?: { field_id: number; values: { value: string }[] }[] }
      const newContact = { id: 50000 + contacts.length + 1, name: b.name, custom_fields_values: b.custom_fields || [] }
      contacts.push(newContact)
      return newContact
    },
  },
  // GET /admin/crm/leads
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/leads$/,
    handler: () => ({ _embedded: { leads } }),
  },
  // POST /admin/crm/leads
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/leads$/,
    handler: ({ body }) => {
      const b = body as { name: string; pipeline_id?: number; status_id?: number }
      const newLead = {
        id: 60000 + leads.length + 1,
        name: b.name,
        price: 0,
        pipeline_id: b.pipeline_id || 7001,
        status_id: b.status_id || 42000001,
      }
      leads.push(newLead)
      return newLead
    },
  },
  // POST /admin/crm/leads/:id/notes
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/leads\/([^/]+)\/notes$/,
    handler: ({ body }) => {
      const b = body as { text: string }
      return { id: Date.now(), text: b.text, created_at: nowISO() }
    },
  },
  // GET /admin/crm/pipelines
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/pipelines$/,
    handler: () => ({ _embedded: { pipelines } }),
  },
  // POST /admin/crm/sync
  {
    method: 'POST',
    pattern: /^\/admin\/crm\/sync$/,
    handler: () => ({
      status: 'ok',
      contacts_count: contacts.length,
      leads_count: leads.length,
      synced_at: nowISO(),
    }),
  },
  // GET /admin/crm/sync-log
  {
    method: 'GET',
    pattern: /^\/admin\/crm\/sync-log$/,
    handler: () => ({ logs: syncLogEntries }),
  },
]
