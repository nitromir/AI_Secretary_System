import { defineStore } from 'pinia'
import { ref } from 'vue'
import { llmApi, type LlmParams } from '@/api'

export const useLlmStore = defineStore('llm', () => {
  const backend = ref<'vllm' | 'gemini'>('vllm')
  const model = ref<string>('')
  const persona = ref<string>('gulya')
  const params = ref<LlmParams>({
    temperature: 0.7,
    max_tokens: 512,
    top_p: 0.9,
    repetition_penalty: 1.1,
  })
  const isLoading = ref(false)

  async function fetchBackend() {
    try {
      const response = await llmApi.getBackend()
      backend.value = response.backend as 'vllm' | 'gemini'
      model.value = response.model
    } catch (e) {
      console.error('Failed to fetch backend:', e)
    }
  }

  async function fetchParams() {
    try {
      const response = await llmApi.getParams()
      params.value = response.params
    } catch (e) {
      console.error('Failed to fetch params:', e)
    }
  }

  async function fetchPersona() {
    try {
      const response = await llmApi.getCurrentPersona()
      persona.value = response.id
    } catch (e) {
      console.error('Failed to fetch persona:', e)
    }
  }

  async function switchBackend(newBackend: 'vllm' | 'gemini') {
    isLoading.value = true
    try {
      await llmApi.setBackend(newBackend)
      backend.value = newBackend
    } finally {
      isLoading.value = false
    }
  }

  async function switchPersona(newPersona: string) {
    isLoading.value = true
    try {
      await llmApi.setPersona(newPersona)
      persona.value = newPersona
    } finally {
      isLoading.value = false
    }
  }

  async function updateParams(newParams: Partial<LlmParams>) {
    isLoading.value = true
    try {
      const response = await llmApi.setParams(newParams)
      params.value = response.params
    } finally {
      isLoading.value = false
    }
  }

  return {
    backend,
    model,
    persona,
    params,
    isLoading,
    fetchBackend,
    fetchParams,
    fetchPersona,
    switchBackend,
    switchPersona,
    updateParams,
  }
})
