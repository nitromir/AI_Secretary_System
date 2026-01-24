import { api, createSSE } from './client'

export interface GpuInfo {
  id: number
  name: string
  total_memory_gb: number
  allocated_gb: number
  reserved_gb: number
  free_gb: number
  utilization_percent: number | null
  temperature_c: number | null
  compute_capability: string
}

export interface HealthComponent {
  status: 'healthy' | 'unhealthy' | 'unavailable' | 'stopped'
  backend?: string
  pid?: number
  error?: string
  uptime?: string
}

export interface SystemMetrics {
  cpu_percent: number
  memory_percent: number
  memory_used_gb: number
  memory_total_gb: number
}

export interface Metrics {
  timestamp: string
  system: SystemMetrics
  streaming_tts: {
    cache_size: number
    active_sessions: number
    max_cache_size: number
  } | null
  llm?: {
    history_length: number
    faq_count: number
  }
}

// Monitor API
export const monitorApi = {
  getGpuStats: () =>
    api.get<{ available: boolean; gpus: GpuInfo[] }>('/admin/monitor/gpu'),

  streamGpuStats: (onMessage: (data: { gpus?: GpuInfo[]; available?: boolean; timestamp?: string }) => void) =>
    createSSE('/admin/monitor/gpu/stream', onMessage),

  getHealth: () =>
    api.get<{
      timestamp: string
      overall: 'healthy' | 'degraded'
      components: Record<string, HealthComponent>
    }>('/admin/monitor/health'),

  getMetrics: () =>
    api.get<Metrics>('/admin/monitor/metrics'),

  getErrors: () =>
    api.get<{ errors: Record<string, string>; timestamp: string }>('/admin/monitor/errors'),

  resetMetrics: () =>
    api.post<{ status: string; message: string }>('/admin/monitor/metrics/reset'),
}
