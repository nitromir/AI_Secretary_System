<script setup lang="ts">
import { ref } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { useI18n } from 'vue-i18n'
import {
  Info,
  Github,
  ExternalLink,
  Heart,
  Code2,
  Cpu,
  Database,
  Globe,
  Shield,
  Zap
} from 'lucide-vue-next'
import { api } from '@/api'

const { t } = useI18n()

interface HealthResponse {
  services: Record<string, boolean>
  llm_backend: string
  database: {
    sqlite: { size_mb: number }
    redis: { status: string }
  }
}

// Fetch health info
const { data: health } = useQuery<HealthResponse>({
  queryKey: ['health'],
  queryFn: async (): Promise<HealthResponse> => {
    const response = await api.get('/health')
    return (response as { data: HealthResponse }).data
  },
  refetchInterval: 30000
})

const version = ref('1.0.0')

const features = [
  { icon: Cpu, title: 'Локальный LLM', desc: 'vLLM + Qwen/Llama с LoRA адаптерами' },
  { icon: Globe, title: 'Облачные провайдеры', desc: 'OpenRouter, Gemini, OpenAI, Claude, DeepSeek' },
  { icon: Zap, title: 'Голосовой клон', desc: 'XTTS v2 и OpenVoice для клонирования голоса' },
  { icon: Database, title: 'База знаний', desc: 'FAQ с мгновенными ответами' },
  { icon: Shield, title: 'Безопасность', desc: 'JWT аутентификация, аудит логов' },
  { icon: Code2, title: 'Интеграции', desc: 'Telegram, веб-виджет, GSM телефония' },
]

const links = [
  { label: 'GitHub Repository', url: 'https://github.com/ShaerWare/AI-Secretary-System', icon: Github },
  { label: 'Documentation', url: 'https://github.com/ShaerWare/AI-Secretary-System/wiki', icon: ExternalLink },
]
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-lg bg-indigo-500/20">
          <Info class="w-6 h-6 text-indigo-500" />
        </div>
        <div>
          <h1 class="text-2xl font-bold">{{ t('nav.about') }}</h1>
          <p class="text-muted-foreground">AI Secretary System v{{ version }}</p>
        </div>
      </div>
    </div>

    <!-- Main Card -->
    <div class="card p-6">
      <div class="flex flex-col md:flex-row gap-6">
        <div class="flex-1">
          <h2 class="text-xl font-semibold mb-3">AI Secretary System</h2>
          <p class="text-muted-foreground mb-4">
            Виртуальный секретарь с голосовым клонированием, локальными и облачными LLM,
            интеграцией с Telegram, веб-виджетами и GSM телефонией.
          </p>

          <div class="space-y-2">
            <div class="flex items-center gap-2 text-sm">
              <span class="text-muted-foreground">LLM Backend:</span>
              <span class="font-medium">{{ health?.services?.llm_backend || 'Loading...' }}</span>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <span class="text-muted-foreground">Database:</span>
              <span class="font-medium">
                SQLite {{ health?.database?.sqlite?.size_mb?.toFixed(2) || '?' }} MB
              </span>
            </div>
            <div class="flex items-center gap-2 text-sm">
              <span class="text-muted-foreground">Cache:</span>
              <span
:class="[
                'font-medium',
                health?.database?.redis?.status === 'ok' ? 'text-green-400' : 'text-yellow-400'
              ]">
                Redis {{ health?.database?.redis?.status || 'unknown' }}
              </span>
            </div>
          </div>
        </div>

        <div class="w-px bg-border hidden md:block" />

        <div class="flex flex-col gap-3">
          <a
            v-for="link in links"
            :key="link.url"
            :href="link.url"
            target="_blank"
            rel="noopener"
            class="flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
          >
            <component :is="link.icon" class="w-4 h-4" />
            <span>{{ link.label }}</span>
          </a>
        </div>
      </div>
    </div>

    <!-- Features Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="feature in features"
        :key="feature.title"
        class="card p-4"
      >
        <div class="flex items-start gap-3">
          <div class="p-2 rounded-lg bg-primary/10">
            <component :is="feature.icon" class="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 class="font-medium">{{ feature.title }}</h3>
            <p class="text-sm text-muted-foreground">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Tech Stack -->
    <div class="card p-6">
      <h3 class="font-semibold mb-4">Технологический стек</h3>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <div class="text-muted-foreground mb-1">Backend</div>
          <div>FastAPI, Python 3.11</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">Frontend</div>
          <div>Vue 3, TypeScript, Tailwind</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">LLM</div>
          <div>vLLM, OpenAI API</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">TTS</div>
          <div>XTTS v2, Piper, OpenVoice</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">Database</div>
          <div>SQLite, Redis</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">Deployment</div>
          <div>Docker, NVIDIA CUDA</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">Integrations</div>
          <div>Telegram, amoCRM</div>
        </div>
        <div>
          <div class="text-muted-foreground mb-1">Telephony</div>
          <div>SIM7600E-H GSM</div>
        </div>
      </div>
    </div>

    <!-- Footer -->
    <div class="text-center text-sm text-muted-foreground">
      <p class="flex items-center justify-center gap-1">
        Made with <Heart class="w-4 h-4 text-red-400" /> by ShaerWare
      </p>
    </div>
  </div>
</template>
