<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { monitorApi, type GpuInfo } from '@/api'
import {
  Activity,
  Cpu,
  HardDrive,
  Thermometer,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Trash2
} from 'lucide-vue-next'
import { computed, onMounted, onUnmounted, ref } from 'vue'

const queryClient = useQueryClient()

// State
const gpuHistory = ref<{ time: string; allocated: number }[]>([])
let gpuStreamHandle: { close: () => void } | null = null

// Queries
const { data: gpuData, isLoading: gpuLoading, refetch: refetchGpu } = useQuery({
  queryKey: ['gpu-stats'],
  queryFn: () => monitorApi.getGpuStats(),
  refetchInterval: 5000,
})

const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
  queryKey: ['health'],
  queryFn: () => monitorApi.getHealth(),
  refetchInterval: 10000,
})

const { data: metricsData, refetch: refetchMetrics } = useQuery({
  queryKey: ['metrics'],
  queryFn: () => monitorApi.getMetrics(),
  refetchInterval: 5000,
})

const { data: errorsData, refetch: refetchErrors } = useQuery({
  queryKey: ['errors'],
  queryFn: () => monitorApi.getErrors(),
})

// Mutations
const resetMetricsMutation = useMutation({
  mutationFn: () => monitorApi.resetMetrics(),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['metrics'] })
  },
})

// Computed
const gpu = computed(() => gpuData.value?.gpus?.[0])

const gpuMemoryPercent = computed(() => {
  if (!gpu.value) return 0
  return Math.round((gpu.value.allocated_gb / gpu.value.total_memory_gb) * 100)
})

const systemMemoryPercent = computed(() => metricsData.value?.system?.memory_percent || 0)

const cpuPercent = computed(() => metricsData.value?.system?.cpu_percent || 0)

const healthComponents = computed(() => healthData.value?.components || {})

const errors = computed(() => {
  if (!errorsData.value?.errors) return []
  return Object.entries(errorsData.value.errors).map(([service, error]) => ({
    service,
    error,
  }))
})

// GPU streaming
function startGpuStream() {
  gpuStreamHandle = monitorApi.streamGpuStats((data) => {
    if (data.gpus?.[0]) {
      const now = new Date().toLocaleTimeString()
      gpuHistory.value.push({
        time: now,
        allocated: data.gpus[0].allocated_gb,
      })
      // Keep last 60 entries (5 minutes at 5s interval)
      if (gpuHistory.value.length > 60) {
        gpuHistory.value = gpuHistory.value.slice(-60)
      }
    }
  })
}

function stopGpuStream() {
  if (gpuStreamHandle) {
    gpuStreamHandle.close()
    gpuStreamHandle = null
  }
}

function refreshAll() {
  refetchGpu()
  refetchHealth()
  refetchMetrics()
  refetchErrors()
}

function getStatusColor(status: string) {
  switch (status) {
    case 'healthy':
      return 'text-green-500'
    case 'unhealthy':
      return 'text-red-500'
    case 'unavailable':
    case 'stopped':
      return 'text-yellow-500'
    default:
      return 'text-muted-foreground'
  }
}

function getStatusIcon(status: string) {
  switch (status) {
    case 'healthy':
      return CheckCircle2
    case 'unhealthy':
      return XCircle
    default:
      return AlertTriangle
  }
}

onMounted(() => {
  startGpuStream()
})

onUnmounted(() => {
  stopGpuStream()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Toolbar -->
    <div class="flex items-center gap-4">
      <button
        @click="refreshAll"
        class="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
      >
        <RefreshCw class="w-4 h-4" />
        Refresh All
      </button>
      <button
        @click="resetMetricsMutation.mutate()"
        :disabled="resetMetricsMutation.isPending.value"
        class="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
      >
        <Trash2 class="w-4 h-4" />
        Reset Metrics
      </button>
    </div>

    <!-- System Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- CPU -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2 rounded-lg bg-blue-500/20">
            <Cpu class="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">CPU Usage</p>
            <p class="text-2xl font-bold">{{ cpuPercent.toFixed(1) }}%</p>
          </div>
        </div>
        <div class="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 transition-all"
            :style="{ width: `${cpuPercent}%` }"
          />
        </div>
      </div>

      <!-- System Memory -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2 rounded-lg bg-orange-500/20">
            <HardDrive class="w-5 h-5 text-orange-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">System Memory</p>
            <p class="text-2xl font-bold">{{ systemMemoryPercent.toFixed(1) }}%</p>
          </div>
        </div>
        <div class="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-orange-500 transition-all"
            :style="{ width: `${systemMemoryPercent}%` }"
          />
        </div>
        <p class="text-xs text-muted-foreground mt-2">
          {{ metricsData?.system?.memory_used_gb?.toFixed(1) }} / {{ metricsData?.system?.memory_total_gb?.toFixed(1) }} GB
        </p>
      </div>

      <!-- GPU Memory -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3 mb-3">
          <div class="p-2 rounded-lg bg-purple-500/20">
            <Activity class="w-5 h-5 text-purple-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">GPU Memory</p>
            <p class="text-2xl font-bold">{{ gpuMemoryPercent }}%</p>
          </div>
        </div>
        <div class="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-purple-500 transition-all"
            :style="{ width: `${gpuMemoryPercent}%` }"
          />
        </div>
        <p v-if="gpu" class="text-xs text-muted-foreground mt-2">
          {{ gpu.allocated_gb?.toFixed(1) }} / {{ gpu.total_memory_gb?.toFixed(1) }} GB
        </p>
      </div>
    </div>

    <!-- GPU Details -->
    <div v-if="gpu" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold">GPU Details</h2>
      </div>
      <div class="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p class="text-sm text-muted-foreground">Name</p>
          <p class="font-medium">{{ gpu.name }}</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Compute Capability</p>
          <p class="font-medium">{{ gpu.compute_capability }}</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Utilization</p>
          <p class="font-medium">{{ gpu.utilization_percent ?? 'N/A' }}%</p>
        </div>
        <div class="flex items-center gap-2">
          <Thermometer class="w-4 h-4 text-muted-foreground" />
          <div>
            <p class="text-sm text-muted-foreground">Temperature</p>
            <p :class="[
              'font-medium',
              (gpu.temperature_c ?? 0) > 80 ? 'text-red-500' :
              (gpu.temperature_c ?? 0) > 60 ? 'text-yellow-500' : ''
            ]">
              {{ gpu.temperature_c ?? 'N/A' }}°C
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Health Status -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold">Health Status</h2>
        <span :class="[
          'px-3 py-1 rounded-full text-sm font-medium',
          healthData?.overall === 'healthy' ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-500'
        ]">
          {{ healthData?.overall || 'unknown' }}
        </span>
      </div>

      <div v-if="healthLoading" class="p-8 text-center text-muted-foreground">
        Loading...
      </div>

      <div v-else class="divide-y divide-border">
        <div
          v-for="(component, name) in healthComponents"
          :key="name"
          class="flex items-center justify-between p-4"
        >
          <div class="flex items-center gap-3">
            <component
              :is="getStatusIcon(component.status)"
              :class="['w-5 h-5', getStatusColor(component.status)]"
            />
            <div>
              <p class="font-medium capitalize">{{ (name as string).replace(/_/g, ' ') }}</p>
              <p v-if="component.backend" class="text-sm text-muted-foreground">
                Backend: {{ component.backend }}
              </p>
              <p v-if="component.pid" class="text-sm text-muted-foreground">
                PID: {{ component.pid }}
              </p>
            </div>
          </div>
          <span :class="[
            'text-sm px-2 py-1 rounded capitalize',
            component.status === 'healthy' ? 'bg-green-500/20 text-green-500' :
            component.status === 'unhealthy' ? 'bg-red-500/20 text-red-500' :
            'bg-yellow-500/20 text-yellow-500'
          ]">
            {{ component.status }}
          </span>
        </div>
      </div>
    </div>

    <!-- TTS Cache Stats -->
    <div v-if="metricsData?.streaming_tts" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold">TTS Streaming Cache</h2>
      </div>
      <div class="p-4 grid grid-cols-3 gap-4">
        <div>
          <p class="text-sm text-muted-foreground">Cache Size</p>
          <p class="text-xl font-bold">{{ metricsData.streaming_tts.cache_size }}</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Max Size</p>
          <p class="text-xl font-bold">{{ metricsData.streaming_tts.max_cache_size }}</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Active Sessions</p>
          <p class="text-xl font-bold">{{ metricsData.streaming_tts.active_sessions }}</p>
        </div>
      </div>
    </div>

    <!-- LLM Stats -->
    <div v-if="metricsData?.llm" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold">LLM Stats</h2>
      </div>
      <div class="p-4 grid grid-cols-2 gap-4">
        <div>
          <p class="text-sm text-muted-foreground">History Length</p>
          <p class="text-xl font-bold">{{ metricsData.llm.history_length }} messages</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">FAQ Entries</p>
          <p class="text-xl font-bold">{{ metricsData.llm.faq_count }}</p>
        </div>
      </div>
    </div>

    <!-- Errors -->
    <div v-if="errors.length" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold text-red-500">Recent Errors</h2>
      </div>
      <div class="divide-y divide-border">
        <div
          v-for="error in errors"
          :key="error.service"
          class="p-4"
        >
          <p class="font-medium text-red-400">{{ error.service }}</p>
          <p class="text-sm text-muted-foreground mt-1">{{ error.error }}</p>
        </div>
      </div>
    </div>

    <!-- GPU Memory History Chart Placeholder -->
    <div v-if="gpuHistory.length > 5" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold">GPU Memory History</h2>
      </div>
      <div class="p-4">
        <div class="h-32 flex items-end gap-1">
          <div
            v-for="(entry, i) in gpuHistory.slice(-30)"
            :key="i"
            class="flex-1 bg-purple-500 rounded-t transition-all"
            :style="{
              height: `${(entry.allocated / (gpu?.total_memory_gb || 12)) * 100}%`,
              minHeight: '4px'
            }"
            :title="`${entry.time}: ${entry.allocated.toFixed(2)} GB`"
          />
        </div>
        <div class="flex justify-between text-xs text-muted-foreground mt-2">
          <span>{{ gpuHistory[0]?.time }}</span>
          <span>{{ gpuHistory[gpuHistory.length - 1]?.time }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
