<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { servicesApi, monitorApi } from '@/api'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
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
import { useRealtimeMetrics } from '@/composables/useRealtimeMetrics'
import SparklineChart from '@/components/charts/SparklineChart.vue'
import GpuChart from '@/components/charts/GpuChart.vue'

const { t } = useI18n()
const router = useRouter()

// Real-time GPU metrics with SSE/polling
const {
  gpuMetrics,
  memorySparkline,
  utilizationSparkline,
  isConnected: metricsConnected
} = useRealtimeMetrics(5000)

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

// Extract first GPU from response
const gpu = computed(() => {
  const data = gpuData.value
  if (!data) return null
  // Handle both direct GpuInfo and wrapped response
  if ('gpus' in data && Array.isArray(data.gpus)) {
    return data.gpus[0] || null
  }
  return data as any
})

const gpuMemoryPercent = computed(() => {
  // Prefer real-time metrics if available
  if (gpuMetrics.value?.memoryPercent) return gpuMetrics.value.memoryPercent
  if (!gpu.value) return 0
  const g = gpu.value as any
  const used = g.allocated_gb || g.memory_used || 0
  const total = g.total_memory_gb || g.memory_total || 1
  return Math.round((used / total) * 100)
})

const gpuUtilization = computed(() => {
  // Prefer real-time metrics if available
  if (gpuMetrics.value?.utilization) return gpuMetrics.value.utilization
  if (!gpu.value) return 0
  const g = gpu.value as any
  return g.utilization_percent || g.utilization || 0
})

const gpuTemperature = computed(() => {
  if (gpuMetrics.value?.temperature) return gpuMetrics.value.temperature
  if (!gpu.value) return null
  const g = gpu.value as any
  return g.temperature_c || null
})

// GPU memory values for template
const gpuUsedGb = computed(() => {
  if (!gpu.value) return 0
  const g = gpu.value as any
  return g.allocated_gb || g.memory_used || 0
})

const gpuTotalGb = computed(() => {
  if (!gpu.value) return 0
  const g = gpu.value as any
  return g.total_memory_gb || g.memory_total || 0
})

const gpuName = computed(() => {
  if (gpuMetrics.value?.name) return gpuMetrics.value.name
  if (!gpu.value) return 'GPU'
  const g = gpu.value as any
  return g.name || 'GPU'
})

function refreshAll() {
  refetchServices()
  refetchHealth()
  refetchGpu()
}

function navigateTo(path: string) {
  router.push(path)
}

const statusConfig = computed(() => ({
  healthy: {
    gradient: 'from-green-900/50 to-green-950/50',
    bg: 'bg-green-500',
    ring: 'ring-green-500/30',
    text: 'text-green-400',
    label: t('dashboard.allOperational')
  },
  warning: {
    gradient: 'from-yellow-900/50 to-yellow-950/50',
    bg: 'bg-yellow-500',
    ring: 'ring-yellow-500/30',
    text: 'text-yellow-400',
    label: t('dashboard.someServicesStopped')
  },
  error: {
    gradient: 'from-red-900/50 to-red-950/50',
    bg: 'bg-red-500',
    ring: 'ring-red-500/30',
    text: 'text-red-400',
    label: t('dashboard.systemError')
  },
  unknown: {
    gradient: 'from-gray-900/50 to-gray-950/50',
    bg: 'bg-gray-500',
    ring: 'ring-gray-500/30',
    text: 'text-gray-400',
    label: t('dashboard.statusUnknown')
  }
}))

const currentStatus = computed(() => statusConfig.value[overallStatus.value])
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
          <div class="flex gap-2 md:gap-4">
            <div class="text-center px-3 py-2 md:px-6 md:py-3 rounded-xl bg-black/20">
              <div class="text-2xl md:text-4xl font-bold text-green-400">{{ serviceStats.running }}</div>
              <div class="text-xs md:text-sm text-gray-400 mt-1">{{ t('dashboard.running') }}</div>
            </div>
            <div class="text-center px-3 py-2 md:px-6 md:py-3 rounded-xl bg-black/20">
              <div class="text-2xl md:text-4xl font-bold text-yellow-400">{{ serviceStats.stopped }}</div>
              <div class="text-xs md:text-sm text-gray-400 mt-1">{{ t('dashboard.stopped') }}</div>
            </div>
            <div class="text-center px-3 py-2 md:px-6 md:py-3 rounded-xl bg-black/20">
              <div class="text-2xl md:text-4xl font-bold text-red-400">{{ serviceStats.error }}</div>
              <div class="text-xs md:text-sm text-gray-400 mt-1">{{ t('dashboard.errors') }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- GPU & System Stats Row -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- GPU Memory -->
        <div
          class="bg-card rounded-xl p-4 md:p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-all hover:scale-[1.02]"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2 md:gap-3">
              <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                <HardDrive class="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
              </div>
              <span class="text-xs md:text-sm text-muted-foreground">{{ t('dashboard.gpuMemory') }}</span>
            </div>
            <span
              :class="[
                'text-xl md:text-2xl font-bold',
                gpuMemoryPercent > 90 ? 'text-red-400' :
                gpuMemoryPercent > 70 ? 'text-yellow-400' : 'text-green-400'
              ]"
            >
              {{ gpuMemoryPercent }}%
            </span>
          </div>
          <!-- Sparkline Chart -->
          <div v-if="memorySparkline.length > 2" class="mb-3">
            <SparklineChart :data="memorySparkline" color="#a855f7" :show-area="true" :height="32" />
          </div>
          <div class="h-2 md:h-3 bg-secondary rounded-full overflow-hidden">
            <div
              :class="[
                'h-full rounded-full transition-all duration-500',
                gpuMemoryPercent > 90 ? 'bg-red-500' :
                gpuMemoryPercent > 70 ? 'bg-yellow-500' : 'bg-purple-500'
              ]"
              :style="{ width: `${gpuMemoryPercent}%` }"
            />
          </div>
          <p class="mt-2 text-xs text-muted-foreground">
            {{ gpuUsedGb.toFixed(1) }} / {{ gpuTotalGb.toFixed(1) }} GB
          </p>
        </div>

        <!-- GPU Utilization -->
        <div
          class="bg-card rounded-xl p-4 md:p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-all hover:scale-[1.02]"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2 md:gap-3">
              <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <Cpu class="w-4 h-4 md:w-5 md:h-5 text-blue-400" />
              </div>
              <span class="text-xs md:text-sm text-muted-foreground">{{ t('dashboard.gpuLoad') }}</span>
            </div>
            <span
              :class="[
                'text-xl md:text-2xl font-bold',
                gpuUtilization > 90 ? 'text-red-400' :
                gpuUtilization > 70 ? 'text-yellow-400' : 'text-green-400'
              ]"
            >
              {{ gpuUtilization }}%
            </span>
          </div>
          <!-- Sparkline Chart -->
          <div v-if="utilizationSparkline.length > 2" class="mb-3">
            <SparklineChart :data="utilizationSparkline" color="#3b82f6" :show-area="true" :height="32" />
          </div>
          <div class="h-2 md:h-3 bg-secondary rounded-full overflow-hidden">
            <div
              :class="[
                'h-full rounded-full transition-all duration-500',
                gpuUtilization > 90 ? 'bg-red-500' :
                gpuUtilization > 70 ? 'bg-yellow-500' : 'bg-blue-500'
              ]"
              :style="{ width: `${gpuUtilization}%` }"
            />
          </div>
          <div class="flex items-center justify-between mt-2">
            <p class="text-xs text-muted-foreground truncate">
              {{ gpuName }}
            </p>
            <p v-if="gpuTemperature" class="text-xs text-orange-400">
              {{ gpuTemperature }}°C
            </p>
          </div>
        </div>

        <!-- Response Time -->
        <div
          class="bg-card rounded-xl p-4 md:p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-all hover:scale-[1.02]"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2 md:gap-3">
              <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-orange-500/20 flex items-center justify-center">
                <Clock class="w-4 h-4 md:w-5 md:h-5 text-orange-400" />
              </div>
              <span class="text-xs md:text-sm text-muted-foreground">{{ t('dashboard.avgResponse') }}</span>
            </div>
            <span class="text-xl md:text-2xl font-bold text-orange-400">
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
          class="bg-card rounded-xl p-4 md:p-6 border border-border cursor-pointer hover:bg-secondary/30 transition-all hover:scale-[1.02]"
          @click="navigateTo('/monitoring')"
        >
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2 md:gap-3">
              <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
                <Zap class="w-4 h-4 md:w-5 md:h-5 text-indigo-400" />
              </div>
              <span class="text-xs md:text-sm text-muted-foreground">{{ t('dashboard.totalRequests') }}</span>
            </div>
            <span class="text-xl md:text-2xl font-bold text-indigo-400">
              {{ metricsData?.total_requests || 0 }}
            </span>
          </div>
          <div class="flex flex-wrap items-center gap-1 md:gap-2 text-xs text-muted-foreground">
            <span class="text-green-400">{{ metricsData?.successful_requests || 0 }} success</span>
            <span>/</span>
            <span class="text-red-400">{{ metricsData?.failed_requests || 0 }} failed</span>
          </div>
        </div>
      </div>

      <!-- Services Grid -->
      <div class="bg-card rounded-xl border border-border">
        <div class="flex items-center justify-between p-4 border-b border-border">
          <h2 class="text-lg font-semibold">{{ t('dashboard.services') }}</h2>
          <button
            @click="refreshAll"
            class="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
          >
            <RefreshCw class="w-4 h-4" />
            {{ t('dashboard.refresh') }}
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
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <button
          @click="navigateTo('/llm')"
          class="flex items-center gap-2 md:gap-3 p-3 md:p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-all hover:scale-[1.02]"
        >
          <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-primary/20 flex items-center justify-center shrink-0">
            <Brain class="w-4 h-4 md:w-5 md:h-5 text-primary" />
          </div>
          <div class="text-left min-w-0">
            <p class="font-medium text-sm md:text-base truncate">{{ t('dashboard.llmSettings') }}</p>
            <p class="text-xs text-muted-foreground truncate hidden sm:block">{{ t('dashboard.configureModel') }}</p>
          </div>
        </button>

        <button
          @click="navigateTo('/tts')"
          class="flex items-center gap-2 md:gap-3 p-3 md:p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-all hover:scale-[1.02]"
        >
          <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
            <Mic class="w-4 h-4 md:w-5 md:h-5 text-purple-400" />
          </div>
          <div class="text-left min-w-0">
            <p class="font-medium text-sm md:text-base truncate">{{ t('dashboard.voiceSettings') }}</p>
            <p class="text-xs text-muted-foreground truncate hidden sm:block">{{ t('dashboard.changeVoice') }}</p>
          </div>
        </button>

        <button
          @click="navigateTo('/faq')"
          class="flex items-center gap-2 md:gap-3 p-3 md:p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-all hover:scale-[1.02]"
        >
          <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-green-500/20 flex items-center justify-center shrink-0">
            <MessageSquare class="w-4 h-4 md:w-5 md:h-5 text-green-400" />
          </div>
          <div class="text-left min-w-0">
            <p class="font-medium text-sm md:text-base truncate">{{ t('dashboard.faqEditor') }}</p>
            <p class="text-xs text-muted-foreground truncate hidden sm:block">{{ t('dashboard.editResponses') }}</p>
          </div>
        </button>

        <button
          @click="navigateTo('/finetune')"
          class="flex items-center gap-2 md:gap-3 p-3 md:p-4 bg-card rounded-xl border border-border hover:bg-secondary/30 transition-all hover:scale-[1.02]"
        >
          <div class="w-8 h-8 md:w-10 md:h-10 rounded-lg bg-orange-500/20 flex items-center justify-center shrink-0">
            <Sparkles class="w-4 h-4 md:w-5 md:h-5 text-orange-400" />
          </div>
          <div class="text-left min-w-0">
            <p class="font-medium text-sm md:text-base truncate">{{ t('dashboard.fineTuning') }}</p>
            <p class="text-xs text-muted-foreground truncate hidden sm:block">{{ t('dashboard.trainModel') }}</p>
          </div>
        </button>
      </div>

      <!-- Health Components -->
      <div v-if="healthData" class="bg-card rounded-xl border border-border">
        <div class="p-4 border-b border-border">
          <h2 class="text-lg font-semibold">{{ t('dashboard.health') }}</h2>
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
