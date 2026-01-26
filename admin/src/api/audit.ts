import { api } from './client'

export interface AuditLog {
  id: number
  timestamp: string
  action: string
  resource: string
  resource_id: string | null
  user_id: string | null
  user_ip: string | null
  details: string | null
}

export interface AuditStats {
  total: number
  last_24h: number
  by_action: Record<string, number>
  by_resource: Record<string, number>
}

export interface AuditQueryParams {
  action?: string
  resource?: string
  user_id?: string
  from_date?: string
  to_date?: string
  limit?: number
  offset?: number
}

// Audit API
export const auditApi = {
  getLogs: (params?: AuditQueryParams) => {
    const query = new URLSearchParams()
    if (params?.action) query.set('action', params.action)
    if (params?.resource) query.set('resource', params.resource)
    if (params?.user_id) query.set('user_id', params.user_id)
    if (params?.from_date) query.set('from_date', params.from_date)
    if (params?.to_date) query.set('to_date', params.to_date)
    if (params?.limit) query.set('limit', params.limit.toString())
    if (params?.offset) query.set('offset', params.offset.toString())

    const queryStr = query.toString()
    return api.get<{ logs: AuditLog[]; count: number }>(
      `/admin/audit/logs${queryStr ? '?' + queryStr : ''}`
    )
  },

  getStats: () =>
    api.get<{ stats: AuditStats }>('/admin/audit/stats'),

  exportLogs: (params?: { from_date?: string; to_date?: string; format?: 'json' | 'csv' }) => {
    const query = new URLSearchParams()
    if (params?.from_date) query.set('from_date', params.from_date)
    if (params?.to_date) query.set('to_date', params.to_date)
    if (params?.format) query.set('format', params.format)

    const queryStr = query.toString()
    return api.get<{ logs: AuditLog[]; count: number } | Blob>(
      `/admin/audit/export${queryStr ? '?' + queryStr : ''}`
    )
  },

  cleanup: (days: number = 90) =>
    api.post<{ status: string; deleted: number; retention_days: number }>(
      `/admin/audit/cleanup?days=${days}`
    ),
}
