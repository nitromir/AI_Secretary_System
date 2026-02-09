import type { DemoRoute } from './types'

function jitter(base: number, range: number): number {
  return +(base + (Math.random() - 0.5) * range).toFixed(1)
}

function gpuData() {
  return {
    available: true,
    gpus: [{
      id: 0,
      name: 'NVIDIA GeForce RTX 3060',
      total_memory_gb: 12.0,
      allocated_gb: jitter(8.6, 0.4),
      reserved_gb: jitter(9.2, 0.3),
      free_gb: jitter(2.8, 0.4),
      utilization_percent: jitter(45, 15),
      temperature_c: jitter(61, 5),
      compute_capability: '8.6',
    }],
    timestamp: new Date().toISOString(),
  }
}

export const monitorRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/gpu$/,
    handler: () => gpuData(),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/gpu\/stream$/,
    handler: () => gpuData(),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/health$/,
    handler: () => ({
      timestamp: new Date().toISOString(),
      overall: 'healthy',
      components: {
        vllm: { status: 'healthy', backend: 'vllm', pid: 1234, uptime: '24h 0m' },
        tts: { status: 'healthy', pid: 1235, uptime: '24h 0m' },
        stt: { status: 'healthy', pid: 1237, uptime: '24h 0m' },
        telegram: { status: 'healthy', pid: 1238, uptime: '23h 45m' },
        redis: { status: 'unavailable', error: 'Connection refused' },
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/metrics$/,
    handler: () => ({
      timestamp: new Date().toISOString(),
      system: {
        cpu_percent: jitter(23, 8),
        memory_percent: jitter(26.3, 3),
        memory_used_gb: jitter(8.4, 0.5),
        memory_total_gb: 32.0,
      },
      streaming_tts: {
        cache_size: 47,
        active_sessions: 2,
        max_cache_size: 100,
      },
      llm: {
        history_length: 24,
        faq_count: 12,
      },
      avg_response_time: jitter(42, 10),
      total_requests: 1247,
      successful_requests: 1239,
      failed_requests: 8,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/errors$/,
    handler: () => ({
      errors: {},
      timestamp: new Date().toISOString(),
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/monitor\/metrics\/reset$/,
    handler: () => ({ status: 'ok', message: 'Metrics reset' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/monitor\/system$/,
    handler: () => ({
      system: {
        hostname: 'ai-secretary-demo',
        os: 'Ubuntu 22.04.3 LTS',
        kernel: '5.15.0-91-generic',
        uptime: '15 days, 6:42:30',
        boot_time: '2024-01-01T03:17:30',
      },
      gpus: [{
        index: 0,
        name: 'NVIDIA GeForce RTX 3060',
        driver_version: '545.29.06',
        memory_total_mb: 12288,
        memory_used_mb: Math.round(jitter(8806, 400)),
        memory_free_mb: Math.round(jitter(3482, 400)),
        utilization_percent: Math.round(jitter(45, 15)),
        temperature_c: Math.round(jitter(61, 5)),
        power_draw_w: jitter(120, 20),
        power_limit_w: 170,
        fan_speed_percent: Math.round(jitter(55, 10)),
        compute_capability: '8.6',
        pcie_gen: 4,
        pcie_width: 16,
      }],
      cpu: {
        model: 'AMD Ryzen 7 5800X 8-Core Processor',
        cores_physical: 8,
        cores_logical: 16,
        frequency_mhz: 3800,
        frequency_max_mhz: 4850,
        usage_percent: jitter(23, 8),
        usage_per_core: Array.from({ length: 16 }, () => jitter(20, 15)),
        temperature_c: jitter(52, 5),
        load_avg_1m: jitter(1.2, 0.5),
        load_avg_5m: jitter(1.5, 0.3),
        load_avg_15m: jitter(1.3, 0.2),
      },
      memory: {
        total_gb: 32.0,
        used_gb: jitter(8.4, 0.5),
        free_gb: jitter(18.2, 1),
        available_gb: jitter(23.6, 1),
        percent_used: jitter(26.3, 3),
        swap_total_gb: 8.0,
        swap_used_gb: 0.3,
        swap_percent: 3.8,
      },
      disks: [
        { device: '/dev/nvme0n1p2', mountpoint: '/', fstype: 'ext4', total_gb: 465.8, used_gb: 124.3, free_gb: 317.8, percent_used: 26.7 },
        { device: '/dev/sda1', mountpoint: '/data', fstype: 'ext4', total_gb: 931.5, used_gb: 256.7, free_gb: 674.8, percent_used: 27.6 },
      ],
      docker: [
        { id: 'abc123', name: 'vllm-qwen', image: 'vllm/vllm-openai:latest', status: 'Up 24 hours', state: 'running', ports: '11434:8000', cpu_percent: 12.3, memory_mb: 6144, memory_limit_mb: 8192, memory_percent: 75.0, created: '2024-01-14T10:00:00', uptime: '24h' },
      ],
      network: [
        { interface: 'eth0', ip_address: '155.212.231.7', mac_address: 'aa:bb:cc:dd:ee:ff', bytes_sent_mb: 1245, bytes_recv_mb: 3456, packets_sent: 892456, packets_recv: 1245678, is_up: true },
      ],
      processes: [
        { pid: 1000, name: 'python', cpu_percent: 5.2, memory_percent: 1.2, memory_mb: 384, status: 'running', cmdline: 'python orchestrator.py' },
        { pid: 1234, name: 'python', cpu_percent: 15.8, memory_percent: 19.2, memory_mb: 6144, status: 'running', cmdline: 'vllm serve Qwen2.5-7B-AWQ' },
        { pid: 1235, name: 'python', cpu_percent: 3.4, memory_percent: 16.0, memory_mb: 5120, status: 'running', cmdline: 'xtts_server' },
      ],
      timestamp: new Date().toISOString(),
    }),
  },
  {
    method: 'GET',
    pattern: /^\/health$/,
    handler: () => ({
      status: 'healthy',
      version: '1.0.0',
      uptime: '15 days, 6:42:30',
    }),
  },
]
