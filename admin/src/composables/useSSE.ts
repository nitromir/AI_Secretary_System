import { ref, onUnmounted } from 'vue'

export function useSSE<T = unknown>(url: string) {
  const data = ref<T[]>([])
  const lastData = ref<T | null>(null)
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
        data.value.push(parsed)
        lastData.value = parsed

        // Keep last 1000 items
        if (data.value.length > 1000) {
          data.value = data.value.slice(-500)
        }
      } catch {
        // If not JSON, store as string
        data.value.push(event.data as T)
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
