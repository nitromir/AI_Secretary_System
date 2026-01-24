import { api, createSSE } from './client'

export interface ServiceStatus {
  name: string
  display_name: string
  is_running: boolean
  pid: number | null
  memory_mb: number | null
  port: number | null
  internal: boolean
  gpu_required: boolean
  cpu_only: boolean
  log_file: string | null
  last_error: string | null
  uptime_seconds?: number
}

export interface ServicesStatusResponse {
  services: Record<string, ServiceStatus>
  timestamp: string
}

export interface LogFile {
  name: string
  file: string
  display_name: string
  size_kb: number
  modified: string
}

export interface LogReadResponse {
  lines: string[]
  total_lines: number
  file: string
  start_line?: number
  end_line?: number
  error?: string
}

// Services API
export const servicesApi = {
  getStatus: () =>
    api.get<ServicesStatusResponse>('/admin/services/status'),

  startService: (name: string) =>
    api.post<{ status: string; message: string; pid?: number }>(`/admin/services/${name}/start`),

  stopService: (name: string) =>
    api.post<{ status: string; message: string }>(`/admin/services/${name}/stop`),

  restartService: (name: string) =>
    api.post<{ status: string; message: string }>(`/admin/services/${name}/restart`),

  startAll: () =>
    api.post<{ status: string; results: Record<string, unknown> }>('/admin/services/start-all'),

  stopAll: () =>
    api.post<{ status: string; results: Record<string, unknown> }>('/admin/services/stop-all'),
}

// Logs API
export const logsApi = {
  list: () =>
    api.get<{ logs: LogFile[] }>('/admin/logs'),

  read: (logfile: string, lines = 100, offset = 0, search?: string) => {
    let url = `/admin/logs/${logfile}?lines=${lines}&offset=${offset}`
    if (search) url += `&search=${encodeURIComponent(search)}`
    return api.get<LogReadResponse>(url)
  },

  stream: (logfile: string, onMessage: (data: { line?: string; error?: string }) => void) =>
    createSSE(`/admin/logs/stream/${logfile}`, onMessage),
}
