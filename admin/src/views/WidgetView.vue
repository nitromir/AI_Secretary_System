<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  Code2,
  Globe,
  Palette,
  MessageSquare,
  Copy,
  Check,
  Plus,
  X,
  Power,
  ExternalLink,
  Terminal,
  BookOpen,
  RefreshCw,
  Loader2,
  Eye,
  EyeOff
} from 'lucide-vue-next'
import { widgetApi, type WidgetConfig } from '@/api'
import { useToastStore } from '@/stores/toast'

const { t } = useI18n()
const queryClient = useQueryClient()
const toast = useToastStore()

// Form state
const config = ref<WidgetConfig>({
  enabled: false,
  title: 'AI Ассистент',
  greeting: 'Здравствуйте! Компания Шаервэй Ди-Иджитал, чем могу помочь?',
  placeholder: 'Введите сообщение...',
  primary_color: '#6366f1',
  position: 'right',
  allowed_domains: [],
  tunnel_url: ''
})

const newDomain = ref('')
const copied = ref<string | null>(null)
const activeTab = ref<'settings' | 'code' | 'instructions'>('settings')
const showPreview = ref(false)

// Queries
const { data: configData, isLoading } = useQuery({
  queryKey: ['widget-config'],
  queryFn: () => widgetApi.getConfig(),
})

// Watch for data load
watch(configData, (data) => {
  if (data?.config) {
    config.value = { ...data.config }
  }
}, { immediate: true })

// Mutations
const saveMutation = useMutation({
  mutationFn: () => widgetApi.saveConfig(config.value),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['widget-config'] })
    toast.success(t('widget.saved'))
  },
  onError: () => {
    toast.error(t('widget.saveFailed'))
  }
})

// Domain management
function addDomain() {
  const domain = newDomain.value.trim().toLowerCase()
  if (domain && !config.value.allowed_domains.includes(domain)) {
    config.value.allowed_domains.push(domain)
    newDomain.value = ''
  }
}

function removeDomain(domain: string) {
  config.value.allowed_domains = config.value.allowed_domains.filter(d => d !== domain)
}

// Copy to clipboard
async function copyToClipboard(text: string, key: string) {
  await navigator.clipboard.writeText(text)
  copied.value = key
  setTimeout(() => { copied.value = null }, 2000)
  toast.success(t('common.copied'))
}

// Generated code snippets
const apiUrl = computed(() => {
  if (config.value.tunnel_url) {
    return config.value.tunnel_url
  }
  return window.location.origin
})

const scriptTag = computed(() => {
  return `<script src="${apiUrl.value}/widget.js"><\/script>`
})

const fullSnippet = computed(() => {
  return `<!-- AI Chat Widget -->
<script src="${apiUrl.value}/widget.js"><\/script>`
})

const manualSnippet = computed(() => {
  return `<!-- AI Chat Widget (manual config) -->
<script>
  window.aiChatSettings = {
    apiUrl: '${apiUrl.value}',
    title: '${config.value.title}',
    greeting: '${config.value.greeting.replace(/'/g, "\\'")}',
    placeholder: '${config.value.placeholder.replace(/'/g, "\\'")}',
    primaryColor: '${config.value.primary_color}',
    position: '${config.value.position}'
  };
<\/script>
<script src="${apiUrl.value}/widget.js"><\/script>`
})

// Color presets
const colorPresets = [
  { name: 'Indigo', value: '#6366f1' },
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Green', value: '#22c55e' },
  { name: 'Purple', value: '#a855f7' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Orange', value: '#f97316' },
]
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6 animate-fade-in">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ t('widget.title') }}</h1>
        <p class="text-muted-foreground mt-1">{{ t('widget.description') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Enable/Disable Toggle -->
        <button
          @click="config.enabled = !config.enabled"
          :class="[
            'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
            config.enabled
              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
              : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
          ]"
        >
          <Power class="w-4 h-4" />
          {{ config.enabled ? t('widget.enabled') : t('widget.disabled') }}
        </button>

        <!-- Save Button -->
        <button
          @click="saveMutation.mutate()"
          :disabled="saveMutation.isPending.value"
          class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          <Loader2 v-if="saveMutation.isPending.value" class="w-4 h-4 animate-spin" />
          <Check v-else class="w-4 h-4" />
          {{ t('common.save') }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center p-12">
      <Loader2 class="w-8 h-8 animate-spin text-primary" />
    </div>

    <template v-else>
      <!-- Tabs -->
      <div class="flex gap-1 bg-secondary/50 p-1 rounded-lg w-fit">
        <button
          v-for="tab in ['settings', 'code', 'instructions'] as const"
          :key="tab"
          @click="activeTab = tab"
          :class="[
            'px-4 py-2 text-sm rounded-md transition-colors',
            activeTab === tab
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground'
          ]"
        >
          <span class="flex items-center gap-2">
            <Palette v-if="tab === 'settings'" class="w-4 h-4" />
            <Code2 v-else-if="tab === 'code'" class="w-4 h-4" />
            <BookOpen v-else class="w-4 h-4" />
            {{ t(`widget.tabs.${tab}`) }}
          </span>
        </button>
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="space-y-4">
        <!-- Tunnel URL -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center shrink-0">
              <Globe class="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('widget.tunnelUrl') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('widget.tunnelUrlDesc') }}</p>
            </div>
          </div>
          <input
            v-model="config.tunnel_url"
            type="url"
            :placeholder="t('widget.tunnelUrlPlaceholder')"
            class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('widget.tunnelUrlHint') }}
          </p>
        </div>

        <!-- Appearance -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
              <Palette class="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('widget.appearance') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('widget.appearanceDesc') }}</p>
            </div>
          </div>

          <div class="space-y-4">
            <!-- Title -->
            <div>
              <label class="block text-sm font-medium mb-2">{{ t('widget.widgetTitle') }}</label>
              <input
                v-model="config.title"
                type="text"
                class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <!-- Greeting -->
            <div>
              <label class="block text-sm font-medium mb-2">{{ t('widget.greeting') }}</label>
              <textarea
                v-model="config.greeting"
                rows="2"
                class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>

            <!-- Placeholder -->
            <div>
              <label class="block text-sm font-medium mb-2">{{ t('widget.placeholder') }}</label>
              <input
                v-model="config.placeholder"
                type="text"
                class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>

            <!-- Color -->
            <div>
              <label class="block text-sm font-medium mb-2">{{ t('widget.primaryColor') }}</label>
              <div class="flex items-center gap-3">
                <div class="flex gap-2">
                  <button
                    v-for="preset in colorPresets"
                    :key="preset.value"
                    @click="config.primary_color = preset.value"
                    :class="[
                      'w-8 h-8 rounded-full border-2 transition-all',
                      config.primary_color === preset.value
                        ? 'border-foreground scale-110'
                        : 'border-transparent hover:scale-105'
                    ]"
                    :style="{ backgroundColor: preset.value }"
                    :title="preset.name"
                  />
                </div>
                <input
                  v-model="config.primary_color"
                  type="color"
                  class="w-10 h-10 rounded cursor-pointer"
                />
                <input
                  v-model="config.primary_color"
                  type="text"
                  class="w-28 px-3 py-2 bg-secondary rounded-lg text-sm font-mono"
                />
              </div>
            </div>

            <!-- Position -->
            <div>
              <label class="block text-sm font-medium mb-2">{{ t('widget.position') }}</label>
              <div class="flex gap-2">
                <button
                  v-for="pos in ['left', 'right'] as const"
                  :key="pos"
                  @click="config.position = pos"
                  :class="[
                    'px-4 py-2 rounded-lg transition-colors capitalize',
                    config.position === pos
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary hover:bg-secondary/80'
                  ]"
                >
                  {{ t(`widget.positions.${pos}`) }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Allowed Domains -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
              <Globe class="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('widget.allowedDomains') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('widget.allowedDomainsDesc') }}</p>
            </div>
          </div>

          <!-- Add domain -->
          <div class="flex gap-2 mb-3">
            <input
              v-model="newDomain"
              type="text"
              :placeholder="t('widget.domainPlaceholder')"
              class="flex-1 px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              @keydown.enter="addDomain"
            />
            <button
              @click="addDomain"
              :disabled="!newDomain.trim()"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Plus class="w-4 h-4" />
            </button>
          </div>

          <!-- Domain list -->
          <div class="flex flex-wrap gap-2">
            <div
              v-for="domain in config.allowed_domains"
              :key="domain"
              class="flex items-center gap-2 px-3 py-1.5 bg-secondary rounded-full text-sm"
            >
              <Globe class="w-3 h-3 text-muted-foreground" />
              {{ domain }}
              <button
                @click="removeDomain(domain)"
                class="text-muted-foreground hover:text-red-400 transition-colors"
              >
                <X class="w-3 h-3" />
              </button>
            </div>
            <div v-if="config.allowed_domains.length === 0" class="text-sm text-muted-foreground">
              {{ t('widget.noDomains') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Code Tab -->
      <div v-if="activeTab === 'code'" class="space-y-4">
        <!-- Simple snippet -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-medium flex items-center gap-2">
              <Code2 class="w-5 h-5 text-green-400" />
              {{ t('widget.simpleCode') }}
            </h3>
            <button
              @click="copyToClipboard(fullSnippet, 'simple')"
              class="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              <Check v-if="copied === 'simple'" class="w-4 h-4 text-green-400" />
              <Copy v-else class="w-4 h-4" />
              {{ t('common.copy') }}
            </button>
          </div>
          <pre class="bg-secondary/50 p-4 rounded-lg text-sm overflow-x-auto font-mono">{{ fullSnippet }}</pre>
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('widget.simpleCodeDesc') }}
          </p>
        </div>

        <!-- Manual config snippet -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-medium flex items-center gap-2">
              <Code2 class="w-5 h-5 text-purple-400" />
              {{ t('widget.manualCode') }}
            </h3>
            <button
              @click="copyToClipboard(manualSnippet, 'manual')"
              class="flex items-center gap-2 px-3 py-1.5 text-sm bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              <Check v-if="copied === 'manual'" class="w-4 h-4 text-green-400" />
              <Copy v-else class="w-4 h-4" />
              {{ t('common.copy') }}
            </button>
          </div>
          <pre class="bg-secondary/50 p-4 rounded-lg text-sm overflow-x-auto font-mono whitespace-pre-wrap">{{ manualSnippet }}</pre>
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('widget.manualCodeDesc') }}
          </p>
        </div>

        <!-- Test URL -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-medium flex items-center gap-2 mb-3">
            <ExternalLink class="w-5 h-5 text-blue-400" />
            {{ t('widget.testWidget') }}
          </h3>
          <div class="flex items-center gap-2">
            <code class="flex-1 px-4 py-2 bg-secondary rounded-lg text-sm font-mono truncate">
              {{ apiUrl }}/widget.js
            </code>
            <a
              :href="`${apiUrl}/widget.js`"
              target="_blank"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <ExternalLink class="w-4 h-4" />
            </a>
          </div>
        </div>
      </div>

      <!-- Instructions Tab -->
      <div v-if="activeTab === 'instructions'" class="space-y-4">
        <!-- Step 1: Tunnel -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">1</span>
            {{ t('widget.step1Title') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('widget.step1Desc') }}</p>
          <div class="bg-secondary/50 p-4 rounded-lg space-y-2 font-mono text-sm">
            <p class="text-muted-foreground"># Cloudflare Tunnel ({{ t('widget.recommended') }})</p>
            <p>cloudflared tunnel --url http://localhost:8002</p>
            <p class="text-muted-foreground mt-3"># {{ t('widget.or') }} ngrok</p>
            <p>ngrok http 8002</p>
          </div>
        </div>

        <!-- Step 2: Configure -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">2</span>
            {{ t('widget.step2Title') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('widget.step2Desc') }}</p>
          <ul class="list-disc list-inside space-y-1 text-sm text-muted-foreground">
            <li>{{ t('widget.step2Item1') }}</li>
            <li>{{ t('widget.step2Item2') }}</li>
            <li>{{ t('widget.step2Item3') }}</li>
          </ul>
        </div>

        <!-- Step 3: Add to site -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">3</span>
            {{ t('widget.step3Title') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('widget.step3Desc') }}</p>
          <pre class="bg-secondary/50 p-4 rounded-lg text-sm overflow-x-auto font-mono">{{ fullSnippet }}</pre>
        </div>

        <!-- Step 4: Enable -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">4</span>
            {{ t('widget.step4Title') }}
          </h3>
          <p class="text-muted-foreground">{{ t('widget.step4Desc') }}</p>
        </div>

        <!-- Helper script -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <Terminal class="w-5 h-5 text-green-400" />
            {{ t('widget.helperScript') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('widget.helperScriptDesc') }}</p>
          <div class="bg-secondary/50 p-4 rounded-lg font-mono text-sm">
            <p>./start_with_tunnel.sh cloudflare</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
