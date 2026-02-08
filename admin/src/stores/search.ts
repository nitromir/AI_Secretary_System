import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { faqApi } from '@/api/faq'
import { servicesApi } from '@/api/services'

export interface SearchResult {
  id: string
  type: 'faq' | 'log' | 'preset' | 'persona' | 'service' | 'adapter'
  title: string
  subtitle?: string
  icon: string
  route?: string
  action?: () => void
}

export const useSearchStore = defineStore('search', () => {
  const isOpen = ref(false)
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const isSearching = ref(false)
  const selectedIndex = ref(0)

  // Static data for quick search
  const staticItems: SearchResult[] = [
    // Personas
    { id: 'persona-anna', type: 'persona', title: 'Анна', subtitle: 'Персона секретаря', icon: 'user', route: '/llm' },
    { id: 'persona-marina', type: 'persona', title: 'Марина', subtitle: 'Персона секретаря', icon: 'user', route: '/llm' },
    // Services
    { id: 'service-vllm', type: 'service', title: 'vLLM Server', subtitle: 'Qwen2.5-7B + LoRA', icon: 'server', route: '/services' },
    { id: 'service-xtts-anna', type: 'service', title: 'XTTS Anna', subtitle: 'Голос Анна', icon: 'volume-2', route: '/services' },
    { id: 'service-xtts-marina', type: 'service', title: 'XTTS Marina', subtitle: 'Голос Марина', icon: 'volume-2', route: '/services' },
    { id: 'service-piper', type: 'service', title: 'Piper TTS', subtitle: 'CPU голоса', icon: 'cpu', route: '/services' },
    { id: 'service-openvoice', type: 'service', title: 'OpenVoice', subtitle: 'Клонирование голоса', icon: 'mic', route: '/services' },
    // Built-in presets
    { id: 'preset-neutral', type: 'preset', title: 'Neutral', subtitle: 'TTS пресет', icon: 'sliders', route: '/tts' },
    { id: 'preset-expressive', type: 'preset', title: 'Expressive', subtitle: 'TTS пресет', icon: 'sliders', route: '/tts' },
    { id: 'preset-calm', type: 'preset', title: 'Calm', subtitle: 'TTS пресет', icon: 'sliders', route: '/tts' },
    { id: 'preset-fast', type: 'preset', title: 'Fast', subtitle: 'TTS пресет', icon: 'sliders', route: '/tts' },
    { id: 'preset-slow', type: 'preset', title: 'Slow', subtitle: 'TTS пресет', icon: 'sliders', route: '/tts' },
    // Navigation
    { id: 'nav-dashboard', type: 'service', title: 'Dashboard', subtitle: 'Обзор системы', icon: 'layout-dashboard', route: '/' },
    { id: 'nav-services', type: 'service', title: 'Services', subtitle: 'Управление сервисами', icon: 'server', route: '/services' },
    { id: 'nav-llm', type: 'service', title: 'LLM', subtitle: 'Настройки LLM', icon: 'brain', route: '/llm' },
    { id: 'nav-tts', type: 'service', title: 'TTS', subtitle: 'Настройки голоса', icon: 'volume-2', route: '/tts' },
    { id: 'nav-faq', type: 'faq', title: 'FAQ', subtitle: 'Типичные ответы', icon: 'message-circle', route: '/faq' },
    { id: 'nav-finetune', type: 'adapter', title: 'Finetune', subtitle: 'Обучение модели', icon: 'graduation-cap', route: '/finetune' },
    { id: 'nav-monitoring', type: 'service', title: 'Monitoring', subtitle: 'Мониторинг', icon: 'activity', route: '/monitoring' },
  ]

  async function search(q: string) {
    query.value = q
    selectedIndex.value = 0

    if (!q.trim()) {
      results.value = []
      return
    }

    isSearching.value = true
    const searchResults: SearchResult[] = []
    const lowerQuery = q.toLowerCase()

    // Search static items
    for (const item of staticItems) {
      if (
        item.title.toLowerCase().includes(lowerQuery) ||
        item.subtitle?.toLowerCase().includes(lowerQuery)
      ) {
        searchResults.push(item)
      }
    }

    // Search FAQ (async)
    try {
      const faqData = await faqApi.getAll()
      for (const [trigger, response] of Object.entries(faqData.faq || {})) {
        if (
          trigger.toLowerCase().includes(lowerQuery) ||
          (response as string).toLowerCase().includes(lowerQuery)
        ) {
          searchResults.push({
            id: `faq-${trigger}`,
            type: 'faq',
            title: trigger,
            subtitle: (response as string).substring(0, 50) + '...',
            icon: 'message-circle',
            route: '/faq'
          })
        }
      }
    } catch {
      // Ignore errors, just don't include FAQ results
    }

    results.value = searchResults.slice(0, 20) // Limit to 20 results
    isSearching.value = false
  }

  function open() {
    isOpen.value = true
    query.value = ''
    results.value = []
    selectedIndex.value = 0
  }

  function close() {
    isOpen.value = false
  }

  function selectNext() {
    if (results.value.length > 0) {
      selectedIndex.value = (selectedIndex.value + 1) % results.value.length
    }
  }

  function selectPrev() {
    if (results.value.length > 0) {
      selectedIndex.value = (selectedIndex.value - 1 + results.value.length) % results.value.length
    }
  }

  function getSelected(): SearchResult | null {
    return results.value[selectedIndex.value] || null
  }

  return {
    isOpen,
    query,
    results,
    isSearching,
    selectedIndex,
    search,
    open,
    close,
    selectNext,
    selectPrev,
    getSelected
  }
})
