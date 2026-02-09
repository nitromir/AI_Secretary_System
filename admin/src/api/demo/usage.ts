import type { DemoRoute } from './types'
import { getStore, generateId, nowISO, daysAgo } from './store'
import type { UsageLimitData } from './store'

const defaultLimits: UsageLimitData[] = [
  { id: 1, service_type: 'llm', limit_type: 'daily', limit_value: 1000, warning_threshold: 80, hard_limit: false, enabled: true, created: daysAgo(30) },
  { id: 2, service_type: 'tts', limit_type: 'daily', limit_value: 500, warning_threshold: 80, hard_limit: false, enabled: true, created: daysAgo(30) },
  { id: 3, service_type: 'llm', limit_type: 'monthly', limit_value: 20000, warning_threshold: 80, hard_limit: true, enabled: true, created: daysAgo(30) },
]

function generateDailyData() {
  const daily = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    daily.push({
      date: d.toISOString().split('T')[0],
      units: Math.floor(50 + Math.random() * 200),
      requests: Math.floor(20 + Math.random() * 80),
      cost_usd: +(Math.random() * 2).toFixed(3),
    })
  }
  return daily
}

export function initUsageData() {
  const store = getStore()
  if (store.usageLimits.length === 0) {
    store.usageLimits = [...defaultLimits]
  }
}

export const usageRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/logs/,
    handler: () => {
      const logs = []
      for (let i = 0; i < 20; i++) {
        logs.push({
          id: i + 1,
          timestamp: daysAgo(Math.floor(Math.random() * 7)),
          service_type: ['llm', 'tts', 'stt'][Math.floor(Math.random() * 3)],
          action: ['chat', 'synthesis', 'transcribe'][Math.floor(Math.random() * 3)],
          source: ['admin', 'telegram', 'widget'][Math.floor(Math.random() * 3)],
          units_consumed: Math.floor(10 + Math.random() * 500),
          cost_usd: +(Math.random() * 0.5).toFixed(4),
        })
      }
      return { logs, count: 20 }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/stats/,
    handler: () => ({
      stats: {
        period_days: 30,
        from_date: daysAgo(30),
        by_service: {
          llm: { units: 15420, requests: 892, cost_usd: 12.34 },
          tts: { units: 8730, requests: 456, cost_usd: 4.56 },
          stt: { units: 2340, requests: 123, cost_usd: 1.23 },
        },
        by_source: {
          admin: { units: 3200, requests: 180 },
          telegram: { units: 18500, requests: 1050 },
          widget: { units: 4790, requests: 241 },
        },
        daily: generateDailyData(),
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/summary$/,
    handler: () => ({
      summary: {
        llm: {
          daily: { used: 342, limit: 1000, percent: 34.2 },
          monthly: { used: 8920, limit: 20000, percent: 44.6 },
        },
        tts: {
          daily: { used: 156, limit: 500, percent: 31.2 },
          monthly: { used: 4230, limit: null, percent: 0 },
        },
        stt: {
          daily: { used: 45, limit: null, percent: 0 },
          monthly: { used: 1120, limit: null, percent: 0 },
        },
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/limits$/,
    handler: () => {
      initUsageData()
      return { limits: getStore().usageLimits }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/limits\/([^/]+)\/([^/]+)$/,
    handler: ({ matches }) => {
      initUsageData()
      const limit = getStore().usageLimits.find(
        l => l.service_type === matches[1] && l.limit_type === matches[2]
      )
      return { limit: limit || defaultLimits[0] }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/usage\/limits$/,
    handler: ({ body }) => {
      initUsageData()
      const data = body as Record<string, unknown>
      const limit: UsageLimitData = {
        id: Date.now(),
        service_type: data.service_type as string,
        limit_type: data.limit_type as string,
        limit_value: data.limit_value as number,
        warning_threshold: (data.warning_threshold as number) ?? 80,
        hard_limit: (data.hard_limit as boolean) ?? false,
        enabled: true,
        created: nowISO(),
      }
      getStore().usageLimits.push(limit)
      return { limit }
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/usage\/limits\/([^/]+)\/([^/]+)$/,
    handler: ({ matches }) => {
      const store = getStore()
      store.usageLimits = store.usageLimits.filter(
        l => !(l.service_type === matches[1] && l.limit_type === matches[2])
      )
      return { status: 'ok' }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/usage\/check\//,
    handler: () => ({
      service_type: 'llm',
      limit_type: 'daily',
      current_usage: 342,
      within_limits: true,
      warnings: [],
      blocked: false,
      limits: [{ limit_type: 'daily', limit_value: 1000, current_usage: 342, usage_percent: 34.2, hard_limit: false }],
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/usage\/cleanup/,
    handler: () => ({ status: 'ok', deleted: 0, retention_days: 90 }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/usage\/log$/,
    handler: ({ body }) => ({
      log: { id: Date.now(), timestamp: nowISO(), ...(body as object) },
    }),
  },
]
