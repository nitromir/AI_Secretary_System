import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ttsApi, type Voice, type VoiceConfig, type XttsParams } from '@/api'

export const useTtsStore = defineStore('tts', () => {
  const voices = ref<Voice[]>([])
  const currentVoice = ref<VoiceConfig>({ engine: 'xtts', voice: 'anna' })
  const currentPreset = ref<string>('natural')
  const xttsParams = ref<XttsParams>({
    temperature: 0.75,
    repetition_penalty: 4.0,
    top_k: 55,
    top_p: 0.88,
    speed: 0.98,
    gpt_cond_len: 20,
    gpt_cond_chunk_len: 5,
  })
  const isLoading = ref(false)

  async function fetchVoices() {
    try {
      const response = await ttsApi.getVoices()
      voices.value = response.voices
      currentVoice.value = response.current
    } catch (e) {
      console.error('Failed to fetch voices:', e)
    }
  }

  async function fetchXttsParams() {
    try {
      const response = await ttsApi.getXttsParams()
      xttsParams.value = response.current_params
      currentPreset.value = response.default_preset
    } catch (e) {
      console.error('Failed to fetch XTTS params:', e)
    }
  }

  async function setVoice(voice: string) {
    isLoading.value = true
    try {
      const response = await ttsApi.setVoice(voice)
      currentVoice.value = { engine: response.engine, voice: response.voice }
    } finally {
      isLoading.value = false
    }
  }

  async function setPreset(preset: string) {
    isLoading.value = true
    try {
      await ttsApi.setPreset(preset)
      currentPreset.value = preset
      await fetchXttsParams()
    } finally {
      isLoading.value = false
    }
  }

  async function updateXttsParams(params: Partial<XttsParams>) {
    isLoading.value = true
    try {
      await ttsApi.setXttsParams(params)
      Object.assign(xttsParams.value, params)
    } finally {
      isLoading.value = false
    }
  }

  return {
    voices,
    currentVoice,
    currentPreset,
    xttsParams,
    isLoading,
    fetchVoices,
    fetchXttsParams,
    setVoice,
    setPreset,
    updateXttsParams,
  }
})
