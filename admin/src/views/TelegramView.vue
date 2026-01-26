<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import {
  Send,
  Bot,
  Power,
  Play,
  Square,
  RefreshCw,
  Users,
  Shield,
  MessageSquare,
  Settings2,
  Copy,
  Check,
  Plus,
  X,
  Loader2,
  ExternalLink,
  Eye,
  EyeOff,
  Trash2,
  BookOpen
} from 'lucide-vue-next'
import { telegramApi, type TelegramConfig, type TelegramStatus } from '@/api'
import { useToastStore } from '@/stores/toast'

const { t } = useI18n()
const queryClient = useQueryClient()
const toast = useToastStore()

// Form state
const config = ref<TelegramConfig>({
  enabled: false,
  bot_token: '',
  api_url: 'http://localhost:8002',
  allowed_users: [],
  admin_users: [],
  welcome_message: 'Здравствуйте! Я AI-ассистент компании Шаервэй. Чем могу помочь?',
  unauthorized_message: 'Извините, у вас нет доступа к этому боту.',
  error_message: 'Произошла ошибка. Попробуйте позже.',
  typing_enabled: true
})

const newAllowedUser = ref('')
const newAdminUser = ref('')
const showToken = ref(false)
const copied = ref<string | null>(null)
const activeTab = ref<'settings' | 'users' | 'messages' | 'instructions'>('settings')

// Queries
const { data: configData, isLoading: configLoading } = useQuery({
  queryKey: ['telegram-config'],
  queryFn: () => telegramApi.getConfig(),
})

const { data: statusData, refetch: refetchStatus } = useQuery({
  queryKey: ['telegram-status'],
  queryFn: () => telegramApi.getStatus(),
  refetchInterval: 5000, // Poll every 5 seconds
})

const { data: sessionsData, refetch: refetchSessions } = useQuery({
  queryKey: ['telegram-sessions'],
  queryFn: () => telegramApi.getSessions(),
})

// Watch for data load
watch(configData, (data) => {
  if (data?.config) {
    config.value = {
      ...config.value, // Keep defaults
      ...data.config,
      allowed_users: Array.isArray(data.config.allowed_users) ? data.config.allowed_users : [],
      admin_users: Array.isArray(data.config.admin_users) ? data.config.admin_users : [],
      bot_token: '' // Don't show actual token, use masked
    }
  }
}, { immediate: true })

// Computed
const status = computed<TelegramStatus | null>(() => statusData.value?.status ?? null)
const isRunning = computed(() => status.value?.running ?? false)
const hasToken = computed(() => status.value?.has_token ?? false)
const sessionsCount = computed(() => {
  const sessions = sessionsData.value?.sessions
  return sessions && typeof sessions === 'object' ? Object.keys(sessions).length : 0
})

// Mutations
const saveMutation = useMutation({
  mutationFn: () => telegramApi.saveConfig(config.value),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['telegram-config'] })
    queryClient.invalidateQueries({ queryKey: ['telegram-status'] })
    toast.success(t('telegram.saved'))
  },
  onError: () => {
    toast.error(t('telegram.saveFailed'))
  }
})

const startMutation = useMutation({
  mutationFn: () => telegramApi.start(),
  onSuccess: (data) => {
    refetchStatus()
    if (data.status === 'already_running') {
      toast.info(t('telegram.alreadyRunning'))
    } else {
      toast.success(t('telegram.started'))
    }
  },
  onError: (error: any) => {
    toast.error(error?.response?.data?.detail || t('telegram.startFailed'))
  }
})

const stopMutation = useMutation({
  mutationFn: () => telegramApi.stop(),
  onSuccess: () => {
    refetchStatus()
    toast.success(t('telegram.stopped'))
  },
  onError: () => {
    toast.error(t('telegram.stopFailed'))
  }
})

const restartMutation = useMutation({
  mutationFn: () => telegramApi.restart(),
  onSuccess: () => {
    refetchStatus()
    toast.success(t('telegram.restarted'))
  },
  onError: () => {
    toast.error(t('telegram.restartFailed'))
  }
})

const clearSessionsMutation = useMutation({
  mutationFn: () => telegramApi.clearSessions(),
  onSuccess: () => {
    refetchSessions()
    refetchStatus()
    toast.success(t('telegram.sessionsCleared'))
  }
})

// User management
function addAllowedUser() {
  const userId = typeof newAllowedUser.value === 'string'
    ? parseInt(newAllowedUser.value.trim())
    : newAllowedUser.value
  if (userId && !isNaN(userId) && !config.value.allowed_users.includes(userId)) {
    config.value.allowed_users.push(userId)
    newAllowedUser.value = ''
  }
}

function removeAllowedUser(userId: number) {
  config.value.allowed_users = config.value.allowed_users.filter(id => id !== userId)
}

function addAdminUser() {
  const userId = typeof newAdminUser.value === 'string'
    ? parseInt(newAdminUser.value.trim())
    : newAdminUser.value
  if (userId && !isNaN(userId) && !config.value.admin_users.includes(userId)) {
    config.value.admin_users.push(userId)
    newAdminUser.value = ''
  }
}

function removeAdminUser(userId: number) {
  config.value.admin_users = config.value.admin_users.filter(id => id !== userId)
}

// Copy to clipboard
async function copyToClipboard(text: string, key: string) {
  await navigator.clipboard.writeText(text)
  copied.value = key
  setTimeout(() => { copied.value = null }, 2000)
  toast.success(t('common.copied'))
}

// Bot father link
const botFatherUrl = 'https://t.me/BotFather'
</script>

<template>
  <div class="max-w-4xl mx-auto space-y-6 animate-fade-in">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold flex items-center gap-2">
          <Send class="w-7 h-7 text-[#0088cc]" />
          {{ t('telegram.title') }}
        </h1>
        <p class="text-muted-foreground mt-1">{{ t('telegram.description') }}</p>
      </div>
      <div class="flex items-center gap-3">
        <!-- Status indicator -->
        <div
          :class="[
            'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
            isRunning
              ? 'bg-green-500/20 text-green-400'
              : 'bg-gray-500/20 text-gray-400'
          ]"
        >
          <span :class="['w-2 h-2 rounded-full', isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-400']" />
          {{ isRunning ? t('telegram.running') : t('telegram.stopped') }}
        </div>

        <!-- Control buttons -->
        <div class="flex gap-2">
          <button
            v-if="!isRunning"
            @click="startMutation.mutate()"
            :disabled="startMutation.isPending.value || !hasToken || !config.enabled"
            class="flex items-center gap-2 px-3 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 disabled:opacity-50 transition-colors"
            :title="!hasToken ? t('telegram.noToken') : !config.enabled ? t('telegram.notEnabled') : ''"
          >
            <Loader2 v-if="startMutation.isPending.value" class="w-4 h-4 animate-spin" />
            <Play v-else class="w-4 h-4" />
            {{ t('telegram.start') }}
          </button>
          <button
            v-else
            @click="stopMutation.mutate()"
            :disabled="stopMutation.isPending.value"
            class="flex items-center gap-2 px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 transition-colors"
          >
            <Loader2 v-if="stopMutation.isPending.value" class="w-4 h-4 animate-spin" />
            <Square v-else class="w-4 h-4" />
            {{ t('telegram.stop') }}
          </button>
          <button
            @click="restartMutation.mutate()"
            :disabled="restartMutation.isPending.value || !isRunning"
            class="flex items-center gap-2 px-3 py-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
          >
            <Loader2 v-if="restartMutation.isPending.value" class="w-4 h-4 animate-spin" />
            <RefreshCw v-else class="w-4 h-4" />
          </button>
        </div>

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
    <div v-if="configLoading" class="flex items-center justify-center p-12">
      <Loader2 class="w-8 h-8 animate-spin text-primary" />
    </div>

    <template v-else>
      <!-- Status Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center gap-2 text-muted-foreground mb-1">
            <Bot class="w-4 h-4" />
            <span class="text-sm">{{ t('telegram.status') }}</span>
          </div>
          <p :class="['text-lg font-semibold', isRunning ? 'text-green-400' : 'text-gray-400']">
            {{ isRunning ? t('telegram.online') : t('telegram.offline') }}
          </p>
        </div>

        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center gap-2 text-muted-foreground mb-1">
            <MessageSquare class="w-4 h-4" />
            <span class="text-sm">{{ t('telegram.sessions') }}</span>
          </div>
          <p class="text-lg font-semibold">{{ sessionsCount }}</p>
        </div>

        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center gap-2 text-muted-foreground mb-1">
            <Users class="w-4 h-4" />
            <span class="text-sm">{{ t('telegram.allowedUsers') }}</span>
          </div>
          <p class="text-lg font-semibold">
            {{ config.allowed_users.length || t('telegram.allUsers') }}
          </p>
        </div>

        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center gap-2 text-muted-foreground mb-1">
            <Shield class="w-4 h-4" />
            <span class="text-sm">{{ t('telegram.admins') }}</span>
          </div>
          <p class="text-lg font-semibold">{{ config.admin_users.length }}</p>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex gap-1 bg-secondary/50 p-1 rounded-lg w-fit">
        <button
          v-for="tab in ['settings', 'users', 'messages', 'instructions'] as const"
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
            <Settings2 v-if="tab === 'settings'" class="w-4 h-4" />
            <Users v-else-if="tab === 'users'" class="w-4 h-4" />
            <MessageSquare v-else-if="tab === 'messages'" class="w-4 h-4" />
            <BookOpen v-else class="w-4 h-4" />
            {{ t(`telegram.tabs.${tab}`) }}
          </span>
        </button>
      </div>

      <!-- Settings Tab -->
      <div v-if="activeTab === 'settings'" class="space-y-4">
        <!-- Enable/Disable -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                <Power class="w-5 h-5 text-green-400" />
              </div>
              <div>
                <h3 class="font-medium">{{ t('telegram.enableBot') }}</h3>
                <p class="text-sm text-muted-foreground">{{ t('telegram.enableBotDesc') }}</p>
              </div>
            </div>
            <button
              @click="config.enabled = !config.enabled"
              :class="[
                'relative w-11 h-6 rounded-full transition-colors shrink-0',
                config.enabled ? 'bg-green-500' : 'bg-gray-500'
              ]"
            >
              <span
                :class="[
                  'absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform',
                  config.enabled ? 'translate-x-5' : 'translate-x-0'
                ]"
              />
            </button>
          </div>
        </div>

        <!-- Bot Token -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-[#0088cc]/20 flex items-center justify-center shrink-0">
              <Bot class="w-5 h-5 text-[#0088cc]" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('telegram.botToken') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('telegram.botTokenDesc') }}</p>
            </div>
          </div>
          <div class="flex gap-2">
            <div class="relative flex-1">
              <input
                v-model="config.bot_token"
                :type="showToken ? 'text' : 'password'"
                :placeholder="configData?.config?.bot_token_masked || t('telegram.tokenPlaceholder')"
                class="w-full px-4 py-2 pr-10 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
              />
              <button
                @click="showToken = !showToken"
                class="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground"
              >
                <EyeOff v-if="showToken" class="w-4 h-4" />
                <Eye v-else class="w-4 h-4" />
              </button>
            </div>
          </div>
          <p class="text-xs text-muted-foreground mt-2">
            {{ t('telegram.getTokenFrom') }}
            <a :href="botFatherUrl" target="_blank" class="text-[#0088cc] hover:underline">
              @BotFather
              <ExternalLink class="w-3 h-3 inline" />
            </a>
          </p>
        </div>

        <!-- API URL -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
              <Settings2 class="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('telegram.apiUrl') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('telegram.apiUrlDesc') }}</p>
            </div>
          </div>
          <input
            v-model="config.api_url"
            type="url"
            class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <!-- Typing indicator -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                <MessageSquare class="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <h3 class="font-medium">{{ t('telegram.typingIndicator') }}</h3>
                <p class="text-sm text-muted-foreground">{{ t('telegram.typingIndicatorDesc') }}</p>
              </div>
            </div>
            <button
              @click="config.typing_enabled = !config.typing_enabled"
              :class="[
                'relative w-11 h-6 rounded-full transition-colors shrink-0',
                config.typing_enabled ? 'bg-blue-500' : 'bg-gray-500'
              ]"
            >
              <span
                :class="[
                  'absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform',
                  config.typing_enabled ? 'translate-x-5' : 'translate-x-0'
                ]"
              />
            </button>
          </div>
        </div>
      </div>

      <!-- Users Tab -->
      <div v-if="activeTab === 'users'" class="space-y-4">
        <!-- Allowed Users -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
              <Users class="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('telegram.allowedUsersList') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('telegram.allowedUsersDesc') }}</p>
            </div>
          </div>

          <div class="flex gap-2 mb-3">
            <input
              v-model="newAllowedUser"
              type="number"
              :placeholder="t('telegram.userIdPlaceholder')"
              class="flex-1 px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              @keydown.enter="addAllowedUser"
            />
            <button
              @click="addAllowedUser"
              :disabled="!newAllowedUser"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Plus class="w-4 h-4" />
            </button>
          </div>

          <div class="flex flex-wrap gap-2">
            <div
              v-for="userId in config.allowed_users"
              :key="userId"
              class="flex items-center gap-2 px-3 py-1.5 bg-secondary rounded-full text-sm font-mono"
            >
              {{ userId }}
              <button
                @click="removeAllowedUser(userId)"
                class="text-muted-foreground hover:text-red-400 transition-colors"
              >
                <X class="w-3 h-3" />
              </button>
            </div>
            <div v-if="config.allowed_users.length === 0" class="text-sm text-muted-foreground">
              {{ t('telegram.allUsersAllowed') }}
            </div>
          </div>
        </div>

        <!-- Admin Users -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center shrink-0">
              <Shield class="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <h3 class="font-medium">{{ t('telegram.adminUsersList') }}</h3>
              <p class="text-sm text-muted-foreground">{{ t('telegram.adminUsersDesc') }}</p>
            </div>
          </div>

          <div class="flex gap-2 mb-3">
            <input
              v-model="newAdminUser"
              type="number"
              :placeholder="t('telegram.userIdPlaceholder')"
              class="flex-1 px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
              @keydown.enter="addAdminUser"
            />
            <button
              @click="addAdminUser"
              :disabled="!newAdminUser"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Plus class="w-4 h-4" />
            </button>
          </div>

          <div class="flex flex-wrap gap-2">
            <div
              v-for="userId in config.admin_users"
              :key="userId"
              class="flex items-center gap-2 px-3 py-1.5 bg-orange-500/20 text-orange-400 rounded-full text-sm font-mono"
            >
              <Shield class="w-3 h-3" />
              {{ userId }}
              <button
                @click="removeAdminUser(userId)"
                class="hover:text-red-400 transition-colors"
              >
                <X class="w-3 h-3" />
              </button>
            </div>
            <div v-if="config.admin_users.length === 0" class="text-sm text-muted-foreground">
              {{ t('telegram.noAdmins') }}
            </div>
          </div>
        </div>

        <!-- Sessions -->
        <div class="bg-card rounded-xl border border-border p-4">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center shrink-0">
                <MessageSquare class="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 class="font-medium">{{ t('telegram.activeSessions') }}</h3>
                <p class="text-sm text-muted-foreground">{{ sessionsCount }} {{ t('telegram.sessionsCount') }}</p>
              </div>
            </div>
            <button
              @click="clearSessionsMutation.mutate()"
              :disabled="clearSessionsMutation.isPending.value || sessionsCount === 0"
              class="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 transition-colors"
            >
              <Trash2 class="w-4 h-4" />
              {{ t('telegram.clearSessions') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Messages Tab -->
      <div v-if="activeTab === 'messages'" class="space-y-4">
        <!-- Welcome Message -->
        <div class="bg-card rounded-xl border border-border p-4">
          <label class="block text-sm font-medium mb-2">{{ t('telegram.welcomeMessage') }}</label>
          <textarea
            v-model="config.welcome_message"
            rows="3"
            class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>

        <!-- Unauthorized Message -->
        <div class="bg-card rounded-xl border border-border p-4">
          <label class="block text-sm font-medium mb-2">{{ t('telegram.unauthorizedMessage') }}</label>
          <textarea
            v-model="config.unauthorized_message"
            rows="2"
            class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>

        <!-- Error Message -->
        <div class="bg-card rounded-xl border border-border p-4">
          <label class="block text-sm font-medium mb-2">{{ t('telegram.errorMessage') }}</label>
          <textarea
            v-model="config.error_message"
            rows="2"
            class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
          />
        </div>
      </div>

      <!-- Instructions Tab -->
      <div v-if="activeTab === 'instructions'" class="space-y-4">
        <!-- Step 1 -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">1</span>
            {{ t('telegram.step1Title') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('telegram.step1Desc') }}</p>
          <ol class="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
            <li>{{ t('telegram.step1Item1') }}</li>
            <li>{{ t('telegram.step1Item2') }}</li>
            <li>{{ t('telegram.step1Item3') }}</li>
          </ol>
          <a
            :href="botFatherUrl"
            target="_blank"
            class="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-[#0088cc] text-white rounded-lg hover:bg-[#0088cc]/90 transition-colors"
          >
            <Send class="w-4 h-4" />
            {{ t('telegram.openBotFather') }}
            <ExternalLink class="w-4 h-4" />
          </a>
        </div>

        <!-- Step 2 -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">2</span>
            {{ t('telegram.step2Title') }}
          </h3>
          <p class="text-muted-foreground">{{ t('telegram.step2Desc') }}</p>
        </div>

        <!-- Step 3 -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">3</span>
            {{ t('telegram.step3Title') }}
          </h3>
          <p class="text-muted-foreground">{{ t('telegram.step3Desc') }}</p>
        </div>

        <!-- Step 4 -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <span class="w-6 h-6 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-sm">4</span>
            {{ t('telegram.step4Title') }}
          </h3>
          <p class="text-muted-foreground">{{ t('telegram.step4Desc') }}</p>
        </div>

        <!-- Get User ID -->
        <div class="bg-card rounded-xl border border-border p-4">
          <h3 class="font-semibold flex items-center gap-2 mb-3">
            <Users class="w-5 h-5 text-blue-400" />
            {{ t('telegram.howToGetUserId') }}
          </h3>
          <p class="text-muted-foreground mb-3">{{ t('telegram.getUserIdDesc') }}</p>
          <a
            href="https://t.me/userinfobot"
            target="_blank"
            class="text-[#0088cc] hover:underline"
          >
            @userinfobot
            <ExternalLink class="w-3 h-3 inline" />
          </a>
        </div>
      </div>
    </template>
  </div>
</template>
