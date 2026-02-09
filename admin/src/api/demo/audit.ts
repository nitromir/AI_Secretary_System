import type { DemoRoute } from './types'
import { getStore, daysAgo, minutesAgo } from './store'
import type { AuditLogData } from './store'

const defaultAuditLogs: AuditLogData[] = [
  { id: 1, timestamp: daysAgo(3), action: 'login', resource: 'auth', resource_id: null, user_id: 'admin', user_ip: '192.168.1.100', details: 'Successful login' },
  { id: 2, timestamp: daysAgo(3), action: 'update', resource: 'llm', resource_id: 'backend', user_id: 'admin', user_ip: '192.168.1.100', details: 'Backend changed to vllm' },
  { id: 3, timestamp: daysAgo(2), action: 'create', resource: 'faq', resource_id: 'привет', user_id: 'admin', user_ip: '192.168.1.100', details: 'FAQ entry created' },
  { id: 4, timestamp: daysAgo(2), action: 'start', resource: 'telegram', resource_id: 'bot-support', user_id: 'admin', user_ip: '192.168.1.100', details: 'Bot started' },
  { id: 5, timestamp: daysAgo(2), action: 'start', resource: 'telegram', resource_id: 'bot-sales', user_id: 'admin', user_ip: '192.168.1.100', details: 'Bot started' },
  { id: 6, timestamp: daysAgo(1), action: 'update', resource: 'tts', resource_id: 'voice', user_id: 'admin', user_ip: '192.168.1.100', details: 'Voice changed to gulya' },
  { id: 7, timestamp: daysAgo(1), action: 'create', resource: 'chat', resource_id: 'session-admin-1', user_id: 'admin', user_ip: '192.168.1.100', details: 'Chat session created' },
  { id: 8, timestamp: daysAgo(1), action: 'update', resource: 'llm', resource_id: 'params', user_id: 'admin', user_ip: '192.168.1.100', details: 'Temperature set to 0.7' },
  { id: 9, timestamp: minutesAgo(300), action: 'login', resource: 'auth', resource_id: null, user_id: 'admin', user_ip: '192.168.1.100', details: 'Successful login' },
  { id: 10, timestamp: minutesAgo(240), action: 'create', resource: 'provider', resource_id: 'gemini-flash-1', user_id: 'admin', user_ip: '192.168.1.100', details: 'Cloud provider created' },
  { id: 11, timestamp: minutesAgo(180), action: 'test', resource: 'provider', resource_id: 'gemini-flash-1', user_id: 'admin', user_ip: '192.168.1.100', details: 'Provider test passed' },
  { id: 12, timestamp: minutesAgo(120), action: 'update', resource: 'widget', resource_id: 'widget-main', user_id: 'admin', user_ip: '192.168.1.100', details: 'Widget config updated' },
  { id: 13, timestamp: minutesAgo(60), action: 'delete', resource: 'chat', resource_id: 'old-session', user_id: 'admin', user_ip: '192.168.1.100', details: 'Chat session deleted' },
  { id: 14, timestamp: minutesAgo(30), action: 'restart', resource: 'services', resource_id: 'vllm', user_id: 'admin', user_ip: '192.168.1.100', details: 'vLLM service restarted' },
  { id: 15, timestamp: minutesAgo(5), action: 'login', resource: 'auth', resource_id: null, user_id: 'admin', user_ip: '192.168.1.100', details: 'Successful login (demo)' },
]

export function initAuditData() {
  const store = getStore()
  if (store.auditLogs.length === 0) {
    store.auditLogs = [...defaultAuditLogs]
  }
}

export const auditRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/audit\/logs/,
    handler: ({ searchParams }) => {
      initAuditData()
      let logs = [...getStore().auditLogs]
      const action = searchParams.get('action')
      const resource = searchParams.get('resource')
      if (action) logs = logs.filter(l => l.action === action)
      if (resource) logs = logs.filter(l => l.resource === resource)
      const limit = parseInt(searchParams.get('limit') || '100')
      const offset = parseInt(searchParams.get('offset') || '0')
      return { logs: logs.slice(offset, offset + limit), count: logs.length }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/audit\/stats$/,
    handler: () => {
      initAuditData()
      const logs = getStore().auditLogs
      const byAction: Record<string, number> = {}
      const byResource: Record<string, number> = {}
      for (const l of logs) {
        byAction[l.action] = (byAction[l.action] || 0) + 1
        byResource[l.resource] = (byResource[l.resource] || 0) + 1
      }
      return {
        stats: {
          total: logs.length,
          last_24h: logs.filter(l => new Date(l.timestamp) > new Date(Date.now() - 86400000)).length,
          by_action: byAction,
          by_resource: byResource,
        },
      }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/audit\/export/,
    handler: () => {
      initAuditData()
      return { logs: getStore().auditLogs, count: getStore().auditLogs.length }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/audit\/cleanup/,
    handler: () => ({ status: 'ok', deleted: 0, retention_days: 90 }),
  },
]
