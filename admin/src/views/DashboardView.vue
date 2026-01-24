<script setup lang="ts">
import { useQuery } from '@tanstack/vue-query'
import { servicesApi, monitorApi } from '@/api'
import {
  Server,
  Cpu,
  HardDrive,
  Activity,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw
} from 'lucide-vue-next'
import { computed } from 'vue'

// Queries
const { data: servicesData, isLoading: servicesLoading, refetch: refetchServices } = useQuery({
  queryKey: ['services-status'],
  queryFn: () => servicesApi.getStatus(),
  refetchInterval: 10000,
})

const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
  queryKey: ['health'],
  queryFn: () => monitorApi.getHealth(),
  refetchInterval: 10000,
})

const { data: gpuData, isLoading: gpuLoading, refetch: refetchGpu } = useQuery({
  queryKey: ['gpu-stats'],
  queryFn: () => monitorApi.getGpuStats(),
  refetchInterval: 5000,
})

const { data: metricsData } = useQuery({
  queryKey: ['metrics'],
  queryFn: () => monitorApi.getMetrics(),
  refetchInterval: 5000,
})

// Computed
const services = computed(() => {
  if (!servicesData.value) return []
  return Object.entries(servicesData.value.services).map(([key, value]) => ({
    id: key,
    ...value,
  }))
})

const runningCount = computed(() =>
  services.value.filter(s => s.is_running).length
)

const overallHealth = computed(() => healthData.value?.overall || 'unknown')

const gpu = computed(() => gpuData.value?.gpus?.[0])

const gpuMemoryPercent = computed(() => {
  if (!gpu.value) return 0
  return Math.round((gpu.value.allocated_gb / gpu.value.total_memory_gb) * 100)
})

function refreshAll() {
  refetchServices()
  refetchHealth()
  refetchGpu()
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header Stats -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- Services -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-blue-500/20">
            <Server class="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Services</p>
            <p class="text-2xl font-bold">{{ runningCount }}/{{ services.length }}</p>
          </div>
        </div>
      </div>

      <!-- Health -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div :class="[
            'p-2 rounded-lg',
            overallHealth === 'healthy' ? 'bg-green-500/20' : 'bg-yellow-500/20'
          ]">
            <Activity :class="[
              'w-5 h-5',
              overallHealth === 'healthy' ? 'text-green-500' : 'text-yellow-500'
            ]" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Health</p>
            <p class="text-2xl font-bold capitalize">{{ overallHealth }}</p>
          </div>
        </div>
      </div>

      <!-- GPU Memory -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-purple-500/20">
            <Cpu class="w-5 h-5 text-purple-500" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-muted-foreground">GPU Memory</p>
            <p class="text-2xl font-bold">{{ gpuMemoryPercent }}%</p>
          </div>
        </div>
        <div class="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-purple-500 transition-all"
            :style="{ width: `${gpuMemoryPercent}%` }"
          />
        </div>
      </div>

      <!-- System Memory -->
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-orange-500/20">
            <HardDrive class="w-5 h-5 text-orange-500" />
          </div>
          <div class="flex-1">
            <p class="text-sm text-muted-foreground">System Memory</p>
            <p class="text-2xl font-bold">{{ metricsData?.system?.memory_percent || 0 }}%</p>
          </div>
        </div>
        <div class="mt-2 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-orange-500 transition-all"
            :style="{ width: `${metricsData?.system?.memory_percent || 0}%` }"
          />
        </div>
      </div>
    </div>

    <!-- Services Grid -->
    <div class="bg-card rounded-lg border border-border">
      <div class="flex items-center justify-between p-4 border-b border-border">
        <h2 class="text-lg font-semibold">Services Status</h2>
        <button
          @click="refreshAll"
          class="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
        >
          <RefreshCw class="w-4 h-4" />
          Refresh
        </button>
      </div>

      <div v-if="servicesLoading" class="p-8 text-center text-muted-foreground">
        Loading services...
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
        <div
          v-for="service in services"
          :key="service.id"
          class="flex items-center gap-3 p-4 rounded-lg border border-border bg-background"
        >
          <div :class="[
            'p-2 rounded-lg',
            service.is_running ? 'bg-green-500/20' : 'bg-red-500/20'
          ]">
            <CheckCircle2 v-if="service.is_running" class="w-5 h-5 text-green-500" />
            <XCircle v-else class="w-5 h-5 text-red-500" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-medium truncate">{{ service.display_name }}</p>
            <p class="text-sm text-muted-foreground">
              <template v-if="service.is_running">
                PID: {{ service.pid }}
                <span v-if="service.memory_mb"> | {{ service.memory_mb?.toFixed(0) }} MB</span>
              </template>
              <template v-else>
                Stopped
              </template>
            </p>
          </div>
          <div v-if="service.port" class="text-xs text-muted-foreground">
            :{{ service.port }}
          </div>
        </div>
      </div>
    </div>

    <!-- GPU Info -->
    <div v-if="gpu" class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold">GPU Information</h2>
      </div>
      <div class="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <p class="text-sm text-muted-foreground">Name</p>
          <p class="font-medium">{{ gpu.name }}</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Memory</p>
          <p class="font-medium">{{ gpu.allocated_gb?.toFixed(1) }} / {{ gpu.total_memory_gb?.toFixed(1) }} GB</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Utilization</p>
          <p class="font-medium">{{ gpu.utilization_percent ?? 'N/A' }}%</p>
        </div>
        <div>
          <p class="text-sm text-muted-foreground">Temperature</p>
          <p class="font-medium">{{ gpu.temperature_c ?? 'N/A' }}°C</p>
        </div>
      </div>
    </div>

    <!-- Health Components -->
    <div v-if="healthData" class="bg-card rounded-lg border border-border">
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
            <CheckCircle2 v-if="component.status === 'healthy'" class="w-5 h-5 text-green-500" />
            <AlertCircle v-else-if="component.status === 'unavailable'" class="w-5 h-5 text-yellow-500" />
            <XCircle v-else class="w-5 h-5 text-red-500" />
            <span class="font-medium capitalize">{{ name.replace(/_/g, ' ') }}</span>
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
  </div>
</template>
