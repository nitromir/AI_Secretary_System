import type { DemoRoute } from './types'
import { getStore, generateId, nowISO } from './store'

const providerTypes: Record<string, { name: string; default_base_url: string | null; default_models: string[]; requires_base_url: boolean }> = {
  gemini: { name: 'Google Gemini', default_base_url: null, default_models: ['gemini-2.0-flash', 'gemini-2.5-pro'], requires_base_url: false },
  openai: { name: 'OpenAI', default_base_url: 'https://api.openai.com/v1', default_models: ['gpt-4o', 'gpt-4o-mini'], requires_base_url: false },
  anthropic: { name: 'Anthropic', default_base_url: 'https://api.anthropic.com', default_models: ['claude-sonnet-4', 'claude-opus-4'], requires_base_url: false },
  deepseek: { name: 'DeepSeek', default_base_url: 'https://api.deepseek.com/v1', default_models: ['deepseek-chat', 'deepseek-coder'], requires_base_url: false },
  kimi: { name: 'Kimi / Moonshot', default_base_url: 'https://api.moonshot.cn/v1', default_models: ['kimi-k2', 'moonshot-v1-128k'], requires_base_url: false },
  openrouter: { name: 'OpenRouter', default_base_url: 'https://openrouter.ai/api/v1', default_models: ['google/gemini-2.0-flash-exp:free', 'meta-llama/llama-3.1-8b-instruct:free'], requires_base_url: false },
  claude_bridge: { name: 'Claude Bridge (Local CLI)', default_base_url: 'http://localhost:8787/v1', default_models: ['sonnet', 'opus', 'haiku'], requires_base_url: false },
}

const defaultProviders = [
  {
    id: 'gemini-flash-1',
    name: 'Gemini 2.0 Flash',
    provider_type: 'gemini',
    api_key_masked: 'AIza****...Xk9Q',
    model_name: 'gemini-2.0-flash',
    enabled: true,
    is_default: true,
    config: { temperature: 0.7 },
    description: 'Google Gemini Flash - fast & free',
    created: '2024-01-10T12:00:00',
    updated: '2024-01-10T12:00:00',
  },
  {
    id: 'openrouter-free-1',
    name: 'OpenRouter Free',
    provider_type: 'openrouter',
    api_key_masked: 'sk-or****...abc',
    model_name: 'google/gemini-2.0-flash-exp:free',
    enabled: true,
    is_default: false,
    config: { temperature: 0.7 },
    description: 'OpenRouter with free models',
    created: '2024-01-11T14:00:00',
    updated: '2024-01-11T14:00:00',
  },
  {
    id: 'claude-bridge-1',
    name: 'Claude Bridge',
    provider_type: 'claude_bridge',
    api_key_masked: '',
    base_url: 'http://localhost:8787/v1',
    model_name: 'sonnet',
    enabled: true,
    is_default: false,
    config: { bridge_port: 8787, permission_level: 'chat' },
    description: 'Local Claude CLI via bridge',
    created: '2024-01-12T10:00:00',
    updated: '2024-01-12T10:00:00',
  },
]

const defaultPresets = [
  {
    id: 'preset-balanced',
    name: 'Сбалансированный',
    description: 'Оптимальный баланс качества и скорости',
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 0.9,
    repetition_penalty: 1.1,
    is_default: true,
    enabled: true,
    created: '2024-01-10T12:00:00',
    updated: '2024-01-10T12:00:00',
  },
  {
    id: 'preset-creative',
    name: 'Креативный',
    description: 'Более творческие и разнообразные ответы',
    temperature: 0.9,
    max_tokens: 4096,
    top_p: 0.95,
    repetition_penalty: 1.0,
    is_default: false,
    enabled: true,
    created: '2024-01-10T12:00:00',
    updated: '2024-01-10T12:00:00',
  },
]

export function initLlmData() {
  const store = getStore()
  if (store.cloudProviders.length === 0) {
    store.cloudProviders = [...defaultProviders]
  }
  if (store.llmPresets.length === 0) {
    store.llmPresets = [...defaultPresets]
  }
}

export const llmRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/backend$/,
    handler: () => ({
      backend: 'vllm',
      model: 'Qwen2.5-7B-Instruct-AWQ',
      api_url: 'http://localhost:11434',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/backend$/,
    handler: ({ body }) => {
      const { backend } = body as { backend: string }
      return {
        status: 'ok',
        backend,
        model: backend === 'vllm' ? 'Qwen2.5-7B-Instruct-AWQ' : 'unknown',
        message: `Backend switched to ${backend}`,
      }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/models$/,
    handler: () => ({
      available_models: {
        'qwen2_5_7b_instruct_awq': {
          id: 'qwen2_5_7b_instruct_awq',
          name: 'Qwen2.5-7B-Instruct-AWQ',
          full_name: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
          description: 'Qwen2.5 7B quantized with AWQ for efficient inference',
          size: '4.1 GB',
          features: ['chat', 'instruct', 'russian'],
          lora_support: true,
          vllm_model_name: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
          available: true,
        },
      },
      current_model: {
        id: 'qwen2_5_7b_instruct_awq',
        name: 'Qwen2.5-7B-Instruct-AWQ',
        available: true,
      },
      loaded_models: ['Qwen/Qwen2.5-7B-Instruct-AWQ'],
      backend: 'vllm',
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/vllm-model$/,
    handler: () => ({
      model: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
      source: 'config',
      env_model: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/vllm-model$/,
    handler: ({ body }) => ({
      status: 'ok',
      model: (body as { model: string }).model,
      message: 'Model switched',
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/personas$/,
    handler: () => ({
      personas: {
        anna: { name: 'anna', full_name: 'Анна — дружелюбный AI-секретарь' },
        marina: { name: 'marina', full_name: 'Марина — строгий бизнес-ассистент' },
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/persona$/,
    handler: () => ({ id: 'anna', name: 'Анна' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/persona$/,
    handler: ({ body }) => ({
      status: 'ok',
      persona: (body as { persona: string }).persona,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/params$/,
    handler: () => ({
      params: {
        temperature: 0.7,
        max_tokens: 2048,
        top_p: 0.9,
        repetition_penalty: 1.1,
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/params$/,
    handler: ({ body }) => ({
      status: 'ok',
      params: { temperature: 0.7, max_tokens: 2048, top_p: 0.9, repetition_penalty: 1.1, ...(body as object) },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/prompt\/([^/]+)$/,
    handler: ({ matches }) => ({
      persona: matches[1],
      prompt: `Ты — ${matches[1] === 'anna' ? 'Анна' : 'Марина'}, виртуальный AI-секретарь компании. Отвечай вежливо, кратко и по делу. Помогай клиентам с вопросами о услугах, ценах и записи.`,
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/prompt\/([^/]+)$/,
    handler: ({ matches }) => ({
      status: 'ok',
      persona: matches[1],
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/prompt\/([^/]+)\/reset$/,
    handler: () => ({ status: 'ok' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/history$/,
    handler: () => ({
      history: [
        { role: 'user', content: 'Привет!' },
        { role: 'assistant', content: 'Здравствуйте! Чем могу помочь?' },
      ],
      count: 2,
    }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/llm\/history$/,
    handler: () => ({ status: 'ok', cleared_messages: 2 }),
  },
  // Cloud Providers
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/providers/,
    handler: ({ url }) => {
      initLlmData()
      const store = getStore()
      // Check if this is a specific provider request
      const singleMatch = /\/admin\/llm\/providers\/([^/?]+)/.exec(url)
      if (singleMatch && !url.includes('test') && !url.includes('set-default')) {
        const provider = store.cloudProviders.find(p => p.id === singleMatch[1])
        if (provider) return { provider }
        return { provider: store.cloudProviders[0] }
      }
      return {
        providers: store.cloudProviders,
        provider_types: providerTypes,
      }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/providers\/([^/]+)\/test$/,
    handler: () => ({
      status: 'ok',
      available: true,
      test_response: 'Привет! Я работаю корректно.',
      message: 'Provider is available',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/providers\/([^/]+)\/set-default$/,
    handler: ({ matches }) => {
      const store = getStore()
      store.cloudProviders.forEach(p => { p.is_default = p.id === matches[1] })
      return { status: 'ok', message: 'Default provider updated' }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/providers$/,
    handler: ({ body }) => {
      const store = getStore()
      const data = body as Record<string, unknown>
      const newProvider = {
        id: generateId(),
        name: data.name as string || 'New Provider',
        provider_type: data.provider_type as string || 'openai',
        api_key_masked: '****',
        model_name: data.model_name as string || 'gpt-4o',
        enabled: true,
        is_default: false,
        config: data.config as Record<string, unknown> || {},
        description: data.description as string || null,
        created: nowISO(),
        updated: nowISO(),
      }
      store.cloudProviders.push(newProvider)
      return { status: 'ok', provider: newProvider }
    },
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/llm\/providers\/([^/]+)$/,
    handler: ({ matches, body }) => {
      const store = getStore()
      const idx = store.cloudProviders.findIndex(p => p.id === matches[1])
      if (idx >= 0) {
        Object.assign(store.cloudProviders[idx], body, { updated: nowISO() })
        return { status: 'ok', provider: store.cloudProviders[idx] }
      }
      return { status: 'ok', provider: body }
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/llm\/providers\/([^/]+)$/,
    handler: ({ matches }) => {
      const store = getStore()
      store.cloudProviders = store.cloudProviders.filter(p => p.id !== matches[1])
      return { status: 'ok', message: 'Provider deleted' }
    },
  },
  // Proxy
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/proxy\/status$/,
    handler: () => ({
      status: 'ok',
      proxy: {
        xray_available: false,
        is_running: false,
        configured: false,
        total_proxies: 0,
        enabled_proxies: 0,
        proxies: [],
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/proxy\//,
    handler: () => ({ status: 'ok', message: 'Proxy operation completed' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/proxy\/validate/,
    handler: () => ({ valid: true, config: { server: 'example.com', security: 'reality', transport: 'tcp', remark: 'demo' } }),
  },
  // Bridge
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/bridge\/status$/,
    handler: () => ({
      is_running: false,
      pid: null,
      port: 8787,
      url: 'http://localhost:8787',
      uptime: null,
      permission_level: 'chat',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/bridge\/(start|stop)$/,
    handler: ({ matches }) => ({
      status: 'ok',
      message: `Bridge ${matches[1]}ed`,
    }),
  },
  // LLM Presets
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/presets\/current$/,
    handler: () => {
      initLlmData()
      const store = getStore()
      return { current: store.llmPresets.find(p => p.is_default) || null }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/presets\/([^/]+)$/,
    handler: ({ matches }) => {
      initLlmData()
      const store = getStore()
      return store.llmPresets.find(p => p.id === matches[1]) || store.llmPresets[0]
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/presets$/,
    handler: () => {
      initLlmData()
      return { presets: getStore().llmPresets }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/presets\/([^/]+)\/activate$/,
    handler: ({ matches }) => {
      const store = getStore()
      store.llmPresets.forEach(p => { p.is_default = p.id === matches[1] })
      const preset = store.llmPresets.find(p => p.id === matches[1])
      return { status: 'ok', preset, message: 'Preset activated' }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/llm\/presets$/,
    handler: ({ body }) => {
      const store = getStore()
      const data = body as Record<string, unknown>
      const preset = {
        id: generateId(),
        name: data.name as string || 'New Preset',
        description: data.description as string || null,
        system_prompt: data.system_prompt as string || null,
        temperature: (data.temperature as number) ?? 0.7,
        max_tokens: (data.max_tokens as number) ?? 2048,
        top_p: (data.top_p as number) ?? 0.9,
        repetition_penalty: (data.repetition_penalty as number) ?? 1.1,
        is_default: false,
        enabled: true,
        created: nowISO(),
        updated: nowISO(),
      }
      store.llmPresets.push(preset)
      return preset
    },
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/llm\/presets\/([^/]+)$/,
    handler: ({ matches, body }) => {
      const store = getStore()
      const idx = store.llmPresets.findIndex(p => p.id === matches[1])
      if (idx >= 0) {
        Object.assign(store.llmPresets[idx], body, { updated: nowISO() })
        return store.llmPresets[idx]
      }
      return body
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/llm\/presets\/([^/]+)$/,
    handler: ({ matches }) => {
      const store = getStore()
      store.llmPresets = store.llmPresets.filter(p => p.id !== matches[1])
      return { status: 'ok', deleted: matches[1] }
    },
  },
  // Prompt (default system prompt for chat)
  {
    method: 'GET',
    pattern: /^\/admin\/llm\/prompt$/,
    handler: () => ({
      prompt: 'Ты — Анна, виртуальный AI-секретарь. Отвечай вежливо и помогай клиентам.',
      persona: 'anna',
    }),
  },
]
