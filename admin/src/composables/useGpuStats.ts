import { ref, onMounted, onUnmounted } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { monitorApi, type GpuInfo } from '@/api'

export function useGpuStats(interval = 5000) {
  const stats = ref<GpuInfo | null>(null)
  const history = ref<{ time: Date; allocated: number }[]>([])

  const { data, refetch, isLoading, error } = useQuery({
    queryKey: ['gpu-stats'],
    queryFn: () => monitorApi.getGpuStats(),
    refetchInterval: interval,
  })

  // Watch for changes
  let unwatch: (() => void) | null = null

  onMounted(() => {
    unwatch = watchEffect(() => {
      if (data.value?.gpus?.[0]) {
        stats.value = data.value.gpus[0]

        // Add to history
        history.value.push({
          time: new Date(),
          allocated: data.value.gpus[0].allocated_gb,
        })

        // Keep last 60 entries
        if (history.value.length > 60) {
          history.value = history.value.slice(-60)
        }
      }
    })
  })

  onUnmounted(() => {
    if (unwatch) unwatch()
  })

  return {
    stats,
    history,
    isLoading,
    error,
    refetch,
  }
}

// Simple watchEffect implementation since we're not importing from vue
function watchEffect(fn: () => void) {
  fn()
  return () => {}
}
