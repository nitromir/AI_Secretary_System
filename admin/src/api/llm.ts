import { api } from './client'

export interface LlmBackend {
  backend: string
  model: string
  api_url?: string | null
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

// LLM API
export const llmApi = {
  getBackend: () =>
    api.get<LlmBackend>('/admin/llm/backend'),

  setBackend: (backend: 'vllm' | 'gemini') =>
    api.post<{ status: string; backend: string; message?: string }>('/admin/llm/backend', { backend }),

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
}
