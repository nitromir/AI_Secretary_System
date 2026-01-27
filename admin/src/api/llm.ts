import { api } from './client'

export interface LlmBackend {
  backend: string
  model: string
  api_url?: string | null
  provider_type?: string | null
}

// Cloud LLM Provider types
export interface CloudProvider {
  id: string
  name: string
  provider_type: string
  api_key_masked?: string
  api_key?: string
  base_url?: string | null
  model_name: string
  enabled: boolean
  is_default: boolean
  config?: Record<string, unknown>
  description?: string | null
  created?: string
  updated?: string
}

export interface ProviderType {
  name: string
  default_base_url: string | null
  default_models: string[]
  requires_base_url: boolean
}

export interface Persona {
  name: string
  full_name: string
}

export interface LlmParams {
  temperature: number
  max_tokens: number
  top_p: number
  repetition_penalty: number
}

export interface LlmModelInfo {
  id: string
  name: string
  full_name?: string
  description?: string
  size?: string
  features?: string[]
  start_flag?: string
  lora_support?: boolean
  vllm_model_name?: string
  lora?: string
  available?: boolean
}

export interface LlmModelsResponse {
  available_models: Record<string, LlmModelInfo>
  current_model: LlmModelInfo | null
  loaded_models: string[]
  backend: string
}

// LLM API
export const llmApi = {
  getBackend: () =>
    api.get<LlmBackend>('/admin/llm/backend'),

  setBackend: (backend: string, stopUnused: boolean = false) =>
    api.post<{
      status: string
      backend: string
      model?: string
      message?: string
      provider_id?: string
      provider_type?: string
    }>('/admin/llm/backend', { backend, stop_unused: stopUnused }),

  getModels: () =>
    api.get<LlmModelsResponse>('/admin/llm/models'),

  getPersonas: () =>
    api.get<{ personas: Record<string, Persona> }>('/admin/llm/personas'),

  getCurrentPersona: () =>
    api.get<{ id: string; name: string }>('/admin/llm/persona'),

  setPersona: (persona: string) =>
    api.post<{ status: string; persona: string }>('/admin/llm/persona', { persona }),

  getParams: () =>
    api.get<{ params: LlmParams }>('/admin/llm/params'),

  setParams: (params: Partial<LlmParams>) =>
    api.post<{ status: string; params: LlmParams }>('/admin/llm/params', params),

  getPrompt: (persona: string) =>
    api.get<{ persona: string; prompt: string }>(`/admin/llm/prompt/${persona}`),

  setPrompt: (persona: string, prompt: string) =>
    api.post<{ status: string; persona: string }>(`/admin/llm/prompt/${persona}`, { prompt }),

  resetPrompt: (persona: string) =>
    api.post<{ status: string }>(`/admin/llm/prompt/${persona}/reset`),

  getHistory: () =>
    api.get<{ history: Array<{ role: string; content: string }>; count: number }>('/admin/llm/history'),

  clearHistory: () =>
    api.delete<{ status: string; cleared_messages: number }>('/admin/llm/history'),

  // Cloud LLM Providers API
  getProviders: (enabledOnly = false) =>
    api.get<{ providers: CloudProvider[]; provider_types: Record<string, ProviderType> }>(
      `/admin/llm/providers?enabled_only=${enabledOnly}`
    ),

  getProvider: (providerId: string, includeKey = false) =>
    api.get<{ provider: CloudProvider }>(
      `/admin/llm/providers/${providerId}?include_key=${includeKey}`
    ),

  createProvider: (data: Partial<CloudProvider>) =>
    api.post<{ status: string; provider: CloudProvider }>('/admin/llm/providers', data),

  updateProvider: (providerId: string, data: Partial<CloudProvider>) =>
    api.put<{ status: string; provider: CloudProvider }>(
      `/admin/llm/providers/${providerId}`,
      data
    ),

  deleteProvider: (providerId: string) =>
    api.delete<{ status: string; message: string }>(`/admin/llm/providers/${providerId}`),

  testProvider: (providerId: string) =>
    api.post<{ status: string; available: boolean; test_response?: string; message?: string }>(
      `/admin/llm/providers/${providerId}/test`
    ),

  setDefaultProvider: (providerId: string) =>
    api.post<{ status: string; message: string }>(
      `/admin/llm/providers/${providerId}/set-default`
    ),
}
