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
  // Request statistics (optional, may be returned by backend)
  avg_response_time?: number
  total_requests?: number
  successful_requests?: number
  failed_requests?: number
}

// Comprehensive system monitoring types
export interface GpuFullInfo {
  index: number
  name: string
  driver_version: string
  memory_total_mb: number
  memory_used_mb: number
  memory_free_mb: number
  utilization_percent: number
  temperature_c: number
  power_draw_w: number
  power_limit_w: number
  fan_speed_percent: number
  compute_capability: string
  pcie_gen: number
  pcie_width: number
}

export interface CpuInfo {
  model: string
  cores_physical: number
  cores_logical: number
  frequency_mhz: number
  frequency_max_mhz: number
  usage_percent: number
  usage_per_core: number[] | null
  temperature_c: number
  load_avg_1m: number
  load_avg_5m: number
  load_avg_15m: number
}

export interface MemoryInfo {
  total_gb: number
  used_gb: number
  free_gb: number
  available_gb: number
  percent_used: number
  swap_total_gb: number
  swap_used_gb: number
  swap_percent: number
}

export interface DiskInfo {
  device: string
  mountpoint: string
  fstype: string
  total_gb: number
  used_gb: number
  free_gb: number
  percent_used: number
}

export interface DockerContainer {
  id: string
  name: string
  image: string
  status: string
  state: string
  ports: string
  cpu_percent: number
  memory_mb: number
  memory_limit_mb: number
  memory_percent: number
  created: string
  uptime: string
}

export interface NetworkInfo {
  interface: string
  ip_address: string
  mac_address: string
  bytes_sent_mb: number
  bytes_recv_mb: number
  packets_sent: number
  packets_recv: number
  is_up: boolean
}

export interface ProcessInfo {
  pid: number
  name: string
  cpu_percent: number
  memory_percent: number
  memory_mb: number
  status: string
  cmdline: string
}

export interface SystemInfo {
  hostname: string
  os: string
  kernel: string
  uptime: string
  boot_time: string
}

export interface FullSystemStatus {
  system: SystemInfo
  gpus: GpuFullInfo[]
  cpu: CpuInfo
  memory: MemoryInfo
  disks: DiskInfo[]
  docker: DockerContainer[]
  network: NetworkInfo[]
  processes: ProcessInfo[]
  timestamp: string
}

// Monitor API
export const monitorApi = {
  getGpuStats: () =>
    api.get<{ available: boolean; gpus: GpuInfo[] }>('/admin/monitor/gpu'),

  streamGpuStats: (onMessage: (data: { gpus?: GpuInfo[]; available?: boolean; timestamp?: string }) => void) =>
    createSSE<{ gpus?: GpuInfo[]; available?: boolean; timestamp?: string }>('/admin/monitor/gpu/stream', onMessage),

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

  getSystemStatus: () =>
    api.get<FullSystemStatus>('/admin/monitor/system'),
}
