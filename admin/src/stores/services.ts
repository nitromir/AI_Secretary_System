import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { servicesApi, type ServiceStatus } from '@/api'

export const useServicesStore = defineStore('services', () => {
  const services = ref<Record<string, ServiceStatus>>({})
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const lastUpdated = ref<Date | null>(null)

  const servicesList = computed(() => Object.values(services.value))
  const runningCount = computed(() => servicesList.value.filter(s => s.is_running).length)
  const totalCount = computed(() => servicesList.value.length)

  async function fetchStatus() {
    isLoading.value = true
    error.value = null
    try {
      const response = await servicesApi.getStatus()
      services.value = response.services
      lastUpdated.value = new Date()
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch status'
    } finally {
      isLoading.value = false
    }
  }

  async function startService(name: string) {
    try {
      await servicesApi.startService(name)
      await fetchStatus()
    } catch (e) {
      throw e
    }
  }

  async function stopService(name: string) {
    try {
      await servicesApi.stopService(name)
      await fetchStatus()
    } catch (e) {
      throw e
    }
  }

  async function restartService(name: string) {
    try {
      await servicesApi.restartService(name)
      await fetchStatus()
    } catch (e) {
      throw e
    }
  }

  return {
    services,
    servicesList,
    runningCount,
    totalCount,
    isLoading,
    error,
    lastUpdated,
    fetchStatus,
    startService,
    stopService,
    restartService,
  }
})
