<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { servicesApi, monitorApi } from '@/api'
import { useRouter } from 'vue-router'
import {
  Server,
  Cpu,
  HardDrive,
  Activity,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Zap,
  Clock,
  TrendingUp,
  Brain,
  Mic,
  MessageSquare,
  Sparkles
} from 'lucide-vue-next'
import { computed } from 'vue'

const router = useRouter()

// Queries
const { data: servicesData, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
  queryKey: ['services-status'],
  queryFn: () => servicesApi.getStatus(),
  refetchInterval: 5000,
})

const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
  queryKey: ['health'],
  queryFn: () => monitorApi.getHealth(),
  refetchInterval: 5000,
})

const { data: gpuData, isLoading: gpuLoading, refetch: refetchGpu } = useQuery({
  queryKey: ['gpu-stats'],
  queryFn: () => monitorApi.getGpuStats(),
  refetchInterval: 3000,
})

const { data: metricsData } = useQuery({
  queryKey: ['metrics'],
  queryFn: () => monitorApi.getMetrics(),
  refetchInterval: 5000,
})

// Computed
const services = computed(() => {
  if (!servicesData.value) return []
  return Object.entries(servicesData.value.services || servicesData.value).map(([key, value]: [string, any]) => ({
    id: key,
    name: value.display_name || value.name || key,
    ...value,
  }))
})

const serviceStats = computed(() => {
  const running = services.value.filter(s => s.is_running || s.status === 'running').length
  const stopped = services.value.filter(s => !s.is_running && s.status !== 'running' && s.status !== 'error').length
  const error = services.value.filter(s => s.status === 'error').length
  return { total: services.value.length, running, stopped, error }
})

const overallStatus = computed(() => {
  if (serviceStats.value.error > 0) return 'error'
  if (serviceStats.value.stopped > 0 && serviceStats.value.running < serviceStats.value.total) return 'warning'
  if (serviceStats.value.running === serviceStats.value.total && serviceStats.value.total > 0) return 'healthy'
  return 'unknown'
})

const gpu = computed(() => gpuData.value?.gpus?.[0] || gpuData.value)

const gpuMemoryPercent = computed(() => {
  if (!gpu.value) return 0
  const used = gpu.value.allocated_gb || gpu.value.memory_used || 0
  const total = gpu.value.total_memory_gb || gpu.value.memory_total || 1
  return Math.round((used / total) * 100)
})

const gpuUtilization = computed(() => gpu.value?.utilization_percent || gpu.value?.utilization || 0)

function refreshAll() {
  refetchServices()
  refetchHealth()
  refetchGpu()
}

function navigateTo(path: string) {
  router.push(path)
}

const statusConfig = {
  healthy: {
    gradient: 'from-green-900/50 to-green-950/50',
    bg: 'bg-green-500',
    ring: 'ring-green-500/30',
    text: 'text-green-400',
    label: 'All Systems Operational'
  },
  warning: {
    gradient: 'from-yellow-900/50 to-yellow-950/50',
    bg: 'bg-yellow-500',
    ring: 'ring-yellow-500/30',
    text: 'text-yellow-400',
    label: 'Some Services Stopped'
  },
  error: {
    gradient: 'from-red-900/50 to-red-950/50',
    bg: 'bg-red-500',
    ring: 'ring-red-500/30',
    text: 'text-red-400',
    label: 'System Error'
  },
  unknown: {
    gradient: 'from-gray-900/50 to-gray-950/50',
    bg: 'bg-gray-500',
    ring: 'ring-gray-500/30',
    text: 'text-gray-400',
    label: 'Status Unknown'
  }
}

const currentStatus = computed(() => statusConfig[overallStatus.value])
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <div v-if="servicesLoading && !servicesData" class="flex items-center justify-center h-64">
      <div class="flex items-center gap-3 text-muted-foreground">
        <svg class="animate-spin h-6 w-6" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Loading dashboard...</span>
      </div>
    </div>

    <template v-else>
      <!-- Large Status Indicator -->
      <div
        :class="[
          'relative overflow-hidden rounded-2xl p-8 cursor-pointer transition-all hover:scale-[1.01]',
          'bg-gradient-to-br',
          currentStatus.gradient
        ]"
        @click="navigateTo('/services')"
      >
        <!-- Animated Background Pulse -->
        <div
          :class="['absolute inset-0 opacity-20 animate-pulse', currentStatus.bg]"
          style="animation-duration: 3s;"
        />

        <div class="relative flex items-center justify-between flex-wrap gap-6">
          <div class="flex items-center gap-6">
            <!-- Large Status Dot with Ring -->
            <div class="relative">
              <div
                :class="[
                  'w-20 h-20 rounded-full flex items-center justify-center ring-8',
                  currentStatus.bg,
                  currentStatus.ring
                ]"
              >
                <CheckCircle v-if="overallStatus === 'healthy'" class="w-10 h-10 text-white" />
                <AlertTriangle v-else-if="overallStatus === 'warning'" class="w-10 h-10 text-white" />
                <XCircle v-else-if="overallStatus === 'error'" class="w-10 h-10 text-white" />
                <Activity v-else class="w-10 h-10 text-white" />
              </div>
              <!-- Ping animation for healthy status -->
              <div
                v-if="overallStatus === 'healthy'"
                :class="['absolute inset-0 rounded-full animate-ping opacity-30', currentStatus.bg]"
                style="animation-duration: 2s;"
              />
            </div>

            <div>
              <h2 class="text-3xl font-bold text-white">
                {{ currentStatus.label }}
              </h2>
              <p class="mt-1 text-lg text-gray-400">
                {{ serviceStats.running }} of {{ serviceStats.total }} services running
              </p>
            </div>
          </div>

          <!-- Service Count Badges -->
          <div class="flex gap-4">
            <div class="text-center px-6 py-3 rounded-xl bg-black/20">
              <div class="text-4xl font-bold text-green-400">{{ serviceStats.running }}</div>
              <div class="text-sm text-gray-400 mt-1">Running</div>
            </div>
            <div class="text-center px-6 py-3 rounded-xl bg-black/20">
              <div class="text-4xl font-bold text-yellow-400">{{ serviceStats.stopped }}</div>
              <div class="text-sm text-gray-400 mt-1">Stopped</div>
            </div>
            <div class="text-center px-6 py-3 rounded-xl bg-black/20">
              <div class="text-4xl font-bold text-red-400">{{ serviceStats.error }}</div>
              <div class="text-sm text-gray-400 mt-1">Errors</div>
            </div>
          </div>
        </div>
      </div>

      <!-- GPU & System Stats Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- GPU Memory -->
        <div
          class="bg-card rounded-xl p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-colors"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <HardDrive class="w-5 h-5 text-purple-400" />
              </div>
              <span class="text-sm text-muted-foreground">GPU Memory</span>
            </div>
            <span
              :class="[
                'text-2xl font-bold',
                gpuMemoryPercent > 90 ? 'text-red-400' :
                gpuMemoryPercent > 70 ? 'text-yellow-400' : 'text-green-400'
              ]"
            >
              {{ gpuMemoryPercent }}%
            </span>
          </div>
          <div class="h-3 bg-secondary rounded-full overflow-hidden">
            <div
              :class="[
                'h-full rounded-full transition-all duration-500',
                gpuMemoryPercent > 90 ? 'bg-red-500' :
                gpuMemoryPercent > 70 ? 'bg-yellow-500' : 'bg-green-500'
              ]"
              :style="{ width: `${gpuMemoryPercent}%` }"
            />
          </div>
          <p class="mt-2 text-xs text-muted-foreground">
            {{ (gpu?.allocated_gb || gpu?.memory_used || 0).toFixed(1) }} / {{ (gpu?.total_memory_gb || gpu?.memory_total || 0).toFixed(1) }} GB
          </p>
        </div>

        <!-- GPU Utilization -->
        <div
          class="bg-card rounded-xl p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-colors"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Cpu class="w-5 h-5 text-blue-400" />
              </div>
              <span class="text-sm text-muted-foreground">GPU Load</span>
            </div>
            <span
              :class="[
                'text-2xl font-bold',
                gpuUtilization > 90 ? 'text-red-400' :
                gpuUtilization > 70 ? 'text-yellow-400' : 'text-green-400'
              ]"
            >
              {{ gpuUtilization }}%
            </span>
          </div>
          <div class="h-3 bg-secondary rounded-full overflow-hidden">
            <div
              :class="[
                'h-full rounded-full transition-all duration-500',
                gpuUtilization > 90 ? 'bg-red-500' :
                gpuUtilization > 70 ? 'bg-yellow-500' : 'bg-blue-500'
              ]"
              :style="{ width: `${gpuUtilization}%` }"
            />
          </div>
          <p class="mt-2 text-xs text-muted-foreground">
            {{ gpu?.name || 'GPU' }}
          </p>
        </div>

        <!-- Response Time -->
        <div
          class="bg-card rounded-xl p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-colors"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Clock class="w-5 h-5 text-orange-400" />
              </div>
              <span class="text-sm text-muted-foreground">Avg Response</span>
            </div>
            <span class="text-2xl font-bold text-orange-400">
              {{ metricsData?.avg_response_time?.toFixed(0) || '-' }}ms
            </span>
          </div>
          <div class="flex items-center gap-2 text-xs text-muted-foreground">
            <TrendingUp class="w-4 h-4" />
            <span>Last 100 requests</span>
          </div>
        </div>

        <!-- Requests -->
        <div
          class="bg-card rounded-xl p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-colors"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                <Zap class="w-5 h-5 text-indigo-400" />
              </div>
              <span class="text-sm text-muted-foreground">Total Requests</span>
            </div>
            <span class="text-2xl font-bold text-indigo-400">
              {{ metricsData?.total_requests || 0 }}
            </span>
          </div>
          <div class="flex items-center gap-2 text-xs text-muted-foreground">
            <span class="text-green-400">{{ metricsData?.successful_requests || 0 }} success</span>
            <span>/</span>
            <span class="text-red-400">{{ metricsData?.failed_requests || 0 }} failed</span>
          </div>
        </div>
      </div>

      <!-- Services Grid -->
      <div class="bg-card rounded-xl border border-border">
        <div class="flex items-center justify-between p-4 border-b border-border">
          <h2 class="text-lg font-semibold">Services</h2>
          <button
            @click="refreshAll"
            class="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
          >
            <RefreshCw class="w-4 h-4" />
            Refresh
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
          <div
            v-for="service in services"
            :key="service.id"
            :class="[
              'flex items-center gap-3 p-4 rounded-lg border cursor-pointer transition-all hover:scale-[1.02]',
              (service.is_running || service.status === 'running')
                ? 'bg-green-500/5 border-green-500/30 hover:border-green-500/50'
                : service.status === 'error'
                ? 'bg-red-500/5 border-red-500/30 hover:border-red-500/50'
                : 'bg-background border-border hover:border-border/80'
            ]"
            @click="navigateTo('/services')"
          >
            <div :class="[
              'w-10 h-10 rounded-lg flex items-center justify-center',
              (service.is_running || service.status === 'running') ? 'bg-green-500/20' :
              service.status === 'error' ? 'bg-red-500/20' : 'bg-gray-500/20'
            ]">
              <Server :class="[
                'w-5 h-5',
                (service.is_running || service.status === 'running') ? 'text-green-400' :
                service.status === 'error' ? 'text-red-400' : 'text-gray-400'
              ]" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="font-medium truncate">{{ service.name }}</p>
              <p class="text-sm text-muted-foreground">
                <template v-if="service.is_running || service.status === 'running'">
                  PID: {{ service.pid }}
                  <span v-if="service.memory_mb"> | {{ service.memory_mb?.toFixed(0) }} MB</span>
                </template>
                <template v-else>
                  {{ service.status || 'Stopped' }}
                </template>
              </p>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="service.port" class="text-xs text-muted-foreground">:{{ service.port }}</span>
              <div
                :class="[
                  'w-3 h-3 rounded-full',
                  (service.is_running || service.status === 'running') ? 'bg-green-500 animate-pulse' :
                  service.status === 'error' ? 'bg-red-500' : 'bg-gray-500'
                ]"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <button
          @click="navigateTo('/llm')"
          class="flex items-center gap-3 p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-colors"
        >
          <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
            <Brain class="w-5 h-5 text-primary" />
          </div>
          <div class="text-left">
            <p class="font-medium">LLM Settings</p>
            <p class="text-xs text-muted-foreground">Configure model</p>
          </div>
        </button>

        <button
          @click="navigateTo('/tts')"
          class="flex items-center gap-3 p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-colors"
        >
          <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <Mic class="w-5 h-5 text-purple-400" />
          </div>
          <div class="text-left">
            <p class="font-medium">Voice Settings</p>
            <p class="text-xs text-muted-foreground">Change voice</p>
          </div>
        </button>

        <button
          @click="navigateTo('/faq')"
          class="flex items-center gap-3 p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-colors"
        >
          <div class="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
            <MessageSquare class="w-5 h-5 text-green-400" />
          </div>
          <div class="text-left">
            <p class="font-medium">FAQ Editor</p>
            <p class="text-xs text-muted-foreground">Edit responses</p>
          </div>
        </button>

        <button
          @click="navigateTo('/finetune')"
          class="flex items-center gap-3 p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-colors"
        >
          <div class="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
            <Sparkles class="w-5 h-5 text-orange-400" />
          </div>
          <div class="text-left">
            <p class="font-medium">Fine-tuning</p>
            <p class="text-xs text-muted-foreground">Train model</p>
          </div>
        </button>
      </div>

      <!-- Health Components -->
      <div v-if="healthData" class="bg-card rounded-xl border border-border">
        <div class="p-4 border-b border-border">
          <h2 class="text-lg font-semibold">Components Health</h2>
        </div>
        <div class="divide-y divide-border">
          <div
            v-for="(component, name) in healthData.components"
            :key="name"
            class="flex items-center justify-between p-4"
          >
            <div class="flex items-center gap-3">
              <CheckCircle v-if="component.status === 'healthy'" class="w-5 h-5 text-green-500" />
              <AlertTriangle v-else-if="component.status === 'unavailable'" class="w-5 h-5 text-yellow-500" />
              <XCircle v-else class="w-5 h-5 text-red-500" />
              <span class="font-medium capitalize">{{ String(name).replace(/_/g, ' ') }}</span>
            </div>
            <span :class="[
              'text-sm px-2 py-0.5 rounded',
              component.status === 'healthy' ? 'bg-green-500/20 text-green-500' :
              component.status === 'unavailable' ? 'bg-yellow-500/20 text-yellow-500' :
              'bg-red-500/20 text-red-500'
            ]">
              {{ component.status }}
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
