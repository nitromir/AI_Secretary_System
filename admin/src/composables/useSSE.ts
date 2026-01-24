import { ref, onUnmounted, type Ref, shallowRef } from 'vue'

export function useSSE<T = unknown>(url: string) {
  const data: Ref<T[]> = shallowRef([])
  const lastData: Ref<T | null> = shallowRef(null)
  const isConnected = ref(false)
  const error = ref<string | null>(null)
  let eventSource: EventSource | null = null

  function connect() {
    if (eventSource) {
      return
    }

    eventSource = new EventSource(url)

    eventSource.onopen = () => {
      isConnected.value = true
      error.value = null
    }

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as T
        const newData = [...data.value, parsed]
        // Keep last 1000 items
        data.value = newData.length > 1000 ? newData.slice(-500) : newData
        lastData.value = parsed
      } catch {
        // If not JSON, store as string
        const newData = [...data.value, event.data as T]
        data.value = newData.length > 1000 ? newData.slice(-500) : newData
        lastData.value = event.data as T
      }
    }

    eventSource.onerror = () => {
      isConnected.value = false
      error.value = 'Connection lost'
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
      isConnected.value = false
    }
  }

  function clear() {
    data.value = []
    lastData.value = null
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    data,
    lastData,
    isConnected,
    error,
    connect,
    disconnect,
    clear,
  }
}
