<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
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
  BookOpen,
  Edit3,
  ChevronRight,
  Cpu,
  Volume2,
  MoreVertical,
  FileText
} from 'lucide-vue-next'
import { botInstancesApi, type BotInstance, type BotInstanceSession } from '@/api'
import { useToastStore } from '@/stores/toast'

const { t } = useI18n()
const queryClient = useQueryClient()
const toast = useToastStore()

// State
const selectedInstanceId = ref<string | null>(null)
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showLogsDialog = ref(false)
const activeTab = ref<'settings' | 'users' | 'messages' | 'ai' | 'sessions'>('settings')

// Form state for create/edit
const formData = ref<Partial<BotInstance>>({
  name: '',
  description: '',
  enabled: true,
  bot_token: '',
  allowed_users: [],
  admin_users: [],
  welcome_message: 'Здравствуйте! Я AI-ассистент. Чем могу помочь?',
  unauthorized_message: 'Извините, у вас нет доступа к этому боту.',
  error_message: 'Произошла ошибка. Попробуйте позже.',
  typing_enabled: true,
  llm_backend: 'vllm',
  llm_persona: 'gulya',
  system_prompt: '',
  tts_engine: 'xtts',
  tts_voice: 'gulya',
  tts_preset: '',
})

const newAllowedUser = ref('')
const newAdminUser = ref('')
const showToken = ref(false)

// Queries
const { data: instancesData, isLoading: instancesLoading, refetch: refetchInstances } = useQuery({
  queryKey: ['bot-instances'],
  queryFn: () => botInstancesApi.list(),
  refetchInterval: 5000,
})

const instances = computed(() => instancesData.value?.instances || [])

const selectedInstance = computed(() =>
  instances.value.find(i => i.id === selectedInstanceId.value)
)

// Sessions query for selected instance
const { data: sessionsData, refetch: refetchSessions } = useQuery({
  queryKey: ['bot-instance-sessions', selectedInstanceId],
  queryFn: () => selectedInstanceId.value ? botInstancesApi.getSessions(selectedInstanceId.value) : Promise.resolve({ sessions: [] }),
  enabled: computed(() => !!selectedInstanceId.value),
})

const sessions = computed<BotInstanceSession[]>(() => sessionsData.value?.sessions || [])

// Logs query
const { data: logsData, refetch: refetchLogs } = useQuery({
  queryKey: ['bot-instance-logs', selectedInstanceId],
  queryFn: () => selectedInstanceId.value ? botInstancesApi.getLogs(selectedInstanceId.value, 200) : Promise.resolve({ logs: '' }),
  enabled: computed(() => showLogsDialog.value && !!selectedInstanceId.value),
})

// Mutations
const createMutation = useMutation({
  mutationFn: (data: Partial<BotInstance>) => botInstancesApi.create(data),
  onSuccess: (data) => {
    queryClient.invalidateQueries({ queryKey: ['bot-instances'] })
    toast.success(t('telegram.instanceCreated'))
    showCreateDialog.value = false
    selectedInstanceId.value = data.instance.id
  },
  onError: () => toast.error(t('telegram.createFailed')),
})

const updateMutation = useMutation({
  mutationFn: ({ id, data }: { id: string; data: Partial<BotInstance> }) =>
    botInstancesApi.update(id, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['bot-instances'] })
    toast.success(t('telegram.saved'))
    showEditDialog.value = false
  },
  onError: () => toast.error(t('telegram.saveFailed')),
})

const deleteMutation = useMutation({
  mutationFn: (id: string) => botInstancesApi.delete(id),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['bot-instances'] })
    toast.success(t('telegram.instanceDeleted'))
    if (selectedInstanceId.value === deleteMutation.variables.value) {
      selectedInstanceId.value = null
    }
  },
  onError: () => toast.error(t('telegram.deleteFailed')),
})

const startMutation = useMutation({
  mutationFn: (id: string) => botInstancesApi.start(id),
  onSuccess: (data) => {
    refetchInstances()
    if (data.status === 'already_running') {
      toast.info(t('telegram.alreadyRunning'))
    } else {
      toast.success(t('telegram.started'))
    }
  },
  onError: (error: any) => toast.error(error?.response?.data?.detail || t('telegram.startFailed')),
})

const stopMutation = useMutation({
  mutationFn: (id: string) => botInstancesApi.stop(id),
  onSuccess: () => {
    refetchInstances()
    toast.success(t('telegram.stopped'))
  },
  onError: () => toast.error(t('telegram.stopFailed')),
})

const restartMutation = useMutation({
  mutationFn: (id: string) => botInstancesApi.restart(id),
  onSuccess: () => {
    refetchInstances()
    toast.success(t('telegram.restarted'))
  },
  onError: () => toast.error(t('telegram.restartFailed')),
})

const clearSessionsMutation = useMutation({
  mutationFn: (id: string) => botInstancesApi.clearSessions(id),
  onSuccess: () => {
    refetchSessions()
    toast.success(t('telegram.sessionsCleared'))
  },
})

// Functions
function openCreateDialog() {
  formData.value = {
    name: '',
    description: '',
    enabled: true,
    bot_token: '',
    allowed_users: [],
    admin_users: [],
    welcome_message: 'Здравствуйте! Я AI-ассистент. Чем могу помочь?',
    unauthorized_message: 'Извините, у вас нет доступа к этому боту.',
    error_message: 'Произошла ошибка. Попробуйте позже.',
    typing_enabled: true,
    llm_backend: 'vllm',
    llm_persona: 'gulya',
    system_prompt: '',
    tts_engine: 'xtts',
    tts_voice: 'gulya',
    tts_preset: '',
  }
  showCreateDialog.value = true
}

function openEditDialog(instance: BotInstance) {
  formData.value = { ...instance }
  showEditDialog.value = true
}

function saveInstance() {
  if (showCreateDialog.value) {
    createMutation.mutate(formData.value)
  } else if (showEditDialog.value && selectedInstanceId.value) {
    updateMutation.mutate({ id: selectedInstanceId.value, data: formData.value })
  }
}

function confirmDelete(instance: BotInstance) {
  if (confirm(t('telegram.confirmDelete', { name: instance.name }))) {
    deleteMutation.mutate(instance.id)
  }
}

function addAllowedUser() {
  const userId = parseInt(newAllowedUser.value.trim())
  if (userId && !isNaN(userId) && !formData.value.allowed_users?.includes(userId)) {
    formData.value.allowed_users = [...(formData.value.allowed_users || []), userId]
    newAllowedUser.value = ''
  }
}

function removeAllowedUser(userId: number) {
  formData.value.allowed_users = formData.value.allowed_users?.filter(id => id !== userId) || []
}

function addAdminUser() {
  const userId = parseInt(newAdminUser.value.trim())
  if (userId && !isNaN(userId) && !formData.value.admin_users?.includes(userId)) {
    formData.value.admin_users = [...(formData.value.admin_users || []), userId]
    newAdminUser.value = ''
  }
}

function removeAdminUser(userId: number) {
  formData.value.admin_users = formData.value.admin_users?.filter(id => id !== userId) || []
}

function openLogs() {
  showLogsDialog.value = true
  refetchLogs()
}

// Auto-select first instance
watch(instances, (newInstances) => {
  if (!selectedInstanceId.value && newInstances.length > 0) {
    selectedInstanceId.value = newInstances[0].id
  }
}, { immediate: true })
</script>

<template>
  <div class="flex h-full gap-6 animate-fade-in">
    <!-- Sidebar: Instance List -->
    <div class="w-80 flex-shrink-0 flex flex-col bg-card rounded-xl border border-border overflow-hidden">
      <!-- Header -->
      <div class="p-4 border-b border-border">
        <div class="flex items-center justify-between mb-2">
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <Send class="w-5 h-5 text-[#0088cc]" />
            {{ t('telegram.bots') }}
          </h2>
          <button
            @click="openCreateDialog"
            class="p-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            :title="t('telegram.createBot')"
          >
            <Plus class="w-4 h-4" />
          </button>
        </div>
        <p class="text-xs text-muted-foreground">{{ t('telegram.instancesDesc') }}</p>
      </div>

      <!-- Instance List -->
      <div class="flex-1 overflow-y-auto p-2">
        <div v-if="instancesLoading" class="flex items-center justify-center p-8">
          <Loader2 class="w-6 h-6 animate-spin text-primary" />
        </div>

        <div v-else-if="instances.length === 0" class="text-center p-8 text-muted-foreground">
          <Bot class="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>{{ t('telegram.noInstances') }}</p>
        </div>

        <div v-else class="space-y-1">
          <button
            v-for="instance in instances"
            :key="instance.id"
            @click="selectedInstanceId = instance.id"
            :class="[
              'w-full p-3 rounded-lg text-left transition-colors',
              selectedInstanceId === instance.id
                ? 'bg-primary/10 border border-primary/30'
                : 'hover:bg-secondary'
            ]"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span :class="[
                  'w-2 h-2 rounded-full',
                  instance.running ? 'bg-green-400 animate-pulse' : 'bg-gray-400'
                ]" />
                <span class="font-medium truncate">{{ instance.name }}</span>
              </div>
              <ChevronRight class="w-4 h-4 text-muted-foreground" />
            </div>
            <p v-if="instance.description" class="text-xs text-muted-foreground mt-1 truncate">
              {{ instance.description }}
            </p>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- No selection -->
      <div v-if="!selectedInstance" class="flex-1 flex items-center justify-center">
        <div class="text-center">
          <Bot class="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
          <p class="text-muted-foreground">{{ t('telegram.selectInstance') }}</p>
        </div>
      </div>

      <!-- Instance Detail -->
      <template v-else>
        <!-- Instance Header -->
        <div class="flex items-center justify-between mb-6">
          <div>
            <h1 class="text-2xl font-bold flex items-center gap-2">
              {{ selectedInstance.name }}
              <span :class="[
                'px-2 py-0.5 text-xs rounded-full',
                selectedInstance.running
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-500/20 text-gray-400'
              ]">
                {{ selectedInstance.running ? t('telegram.running') : t('telegram.stopped') }}
              </span>
            </h1>
            <p v-if="selectedInstance.description" class="text-muted-foreground mt-1">
              {{ selectedInstance.description }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <!-- Control buttons -->
            <button
              v-if="!selectedInstance.running"
              @click="startMutation.mutate(selectedInstance.id)"
              :disabled="startMutation.isPending.value || !selectedInstance.bot_token_masked || !selectedInstance.enabled"
              class="flex items-center gap-2 px-3 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 disabled:opacity-50 transition-colors"
            >
              <Loader2 v-if="startMutation.isPending.value" class="w-4 h-4 animate-spin" />
              <Play v-else class="w-4 h-4" />
              {{ t('telegram.start') }}
            </button>
            <button
              v-else
              @click="stopMutation.mutate(selectedInstance.id)"
              :disabled="stopMutation.isPending.value"
              class="flex items-center gap-2 px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 transition-colors"
            >
              <Loader2 v-if="stopMutation.isPending.value" class="w-4 h-4 animate-spin" />
              <Square v-else class="w-4 h-4" />
              {{ t('telegram.stop') }}
            </button>
            <button
              @click="restartMutation.mutate(selectedInstance.id)"
              :disabled="restartMutation.isPending.value || !selectedInstance.running"
              class="p-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
              :title="t('telegram.restart')"
            >
              <Loader2 v-if="restartMutation.isPending.value" class="w-4 h-4 animate-spin" />
              <RefreshCw v-else class="w-4 h-4" />
            </button>
            <button
              @click="openLogs"
              class="p-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
              :title="t('telegram.viewLogs')"
            >
              <FileText class="w-4 h-4" />
            </button>
            <button
              @click="openEditDialog(selectedInstance)"
              class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              <Edit3 class="w-4 h-4" />
              {{ t('common.edit') }}
            </button>
            <button
              @click="confirmDelete(selectedInstance)"
              class="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
              :title="t('common.delete')"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>

        <!-- Status Cards -->
        <div class="grid grid-cols-4 gap-4 mb-6">
          <div class="bg-card rounded-xl border border-border p-4">
            <div class="flex items-center gap-2 text-muted-foreground mb-1">
              <Bot class="w-4 h-4" />
              <span class="text-sm">{{ t('telegram.status') }}</span>
            </div>
            <p :class="['text-lg font-semibold', selectedInstance.running ? 'text-green-400' : 'text-gray-400']">
              {{ selectedInstance.running ? t('telegram.online') : t('telegram.offline') }}
            </p>
          </div>
          <div class="bg-card rounded-xl border border-border p-4">
            <div class="flex items-center gap-2 text-muted-foreground mb-1">
              <MessageSquare class="w-4 h-4" />
              <span class="text-sm">{{ t('telegram.sessions') }}</span>
            </div>
            <p class="text-lg font-semibold">{{ sessions.length }}</p>
          </div>
          <div class="bg-card rounded-xl border border-border p-4">
            <div class="flex items-center gap-2 text-muted-foreground mb-1">
              <Users class="w-4 h-4" />
              <span class="text-sm">{{ t('telegram.allowedUsers') }}</span>
            </div>
            <p class="text-lg font-semibold">
              {{ selectedInstance.allowed_users?.length || t('telegram.allUsers') }}
            </p>
          </div>
          <div class="bg-card rounded-xl border border-border p-4">
            <div class="flex items-center gap-2 text-muted-foreground mb-1">
              <Cpu class="w-4 h-4" />
              <span class="text-sm">{{ t('telegram.aiBackend') }}</span>
            </div>
            <p class="text-lg font-semibold">{{ selectedInstance.llm_backend }}</p>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex gap-1 bg-secondary/50 p-1 rounded-lg w-fit mb-6">
          <button
            v-for="tab in ['settings', 'users', 'messages', 'ai', 'sessions'] as const"
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
              <Cpu v-else-if="tab === 'ai'" class="w-4 h-4" />
              <BookOpen v-else class="w-4 h-4" />
              {{ t(`telegram.tabs.${tab}`) }}
            </span>
          </button>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-y-auto space-y-4">
          <!-- Settings Tab -->
          <template v-if="activeTab === 'settings'">
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.botToken') }}</h3>
              <p class="text-sm text-muted-foreground mb-2">{{ t('telegram.botTokenDesc') }}</p>
              <code class="block px-3 py-2 bg-secondary rounded-lg font-mono text-sm">
                {{ selectedInstance.bot_token_masked || t('telegram.noToken') }}
              </code>
            </div>
            <div class="bg-card rounded-xl border border-border p-4">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="font-medium">{{ t('telegram.typingIndicator') }}</h3>
                  <p class="text-sm text-muted-foreground">{{ t('telegram.typingIndicatorDesc') }}</p>
                </div>
                <span :class="['px-2 py-1 rounded-full text-sm', selectedInstance.typing_enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400']">
                  {{ selectedInstance.typing_enabled ? t('common.enabled') : t('common.disabled') }}
                </span>
              </div>
            </div>
          </template>

          <!-- Users Tab -->
          <template v-if="activeTab === 'users'">
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.allowedUsersList') }}</h3>
              <p class="text-sm text-muted-foreground mb-3">{{ t('telegram.allowedUsersDesc') }}</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="userId in selectedInstance.allowed_users"
                  :key="userId"
                  class="px-3 py-1.5 bg-secondary rounded-full text-sm font-mono"
                >
                  {{ userId }}
                </span>
                <span v-if="!selectedInstance.allowed_users?.length" class="text-sm text-muted-foreground">
                  {{ t('telegram.allUsersAllowed') }}
                </span>
              </div>
            </div>
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.adminUsersList') }}</h3>
              <p class="text-sm text-muted-foreground mb-3">{{ t('telegram.adminUsersDesc') }}</p>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="userId in selectedInstance.admin_users"
                  :key="userId"
                  class="flex items-center gap-1 px-3 py-1.5 bg-orange-500/20 text-orange-400 rounded-full text-sm font-mono"
                >
                  <Shield class="w-3 h-3" />
                  {{ userId }}
                </span>
                <span v-if="!selectedInstance.admin_users?.length" class="text-sm text-muted-foreground">
                  {{ t('telegram.noAdmins') }}
                </span>
              </div>
            </div>
          </template>

          <!-- Messages Tab -->
          <template v-if="activeTab === 'messages'">
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.welcomeMessage') }}</h3>
              <p class="text-sm bg-secondary rounded-lg p-3">{{ selectedInstance.welcome_message }}</p>
            </div>
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.unauthorizedMessage') }}</h3>
              <p class="text-sm bg-secondary rounded-lg p-3">{{ selectedInstance.unauthorized_message }}</p>
            </div>
            <div class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.errorMessage') }}</h3>
              <p class="text-sm bg-secondary rounded-lg p-3">{{ selectedInstance.error_message }}</p>
            </div>
          </template>

          <!-- AI Tab -->
          <template v-if="activeTab === 'ai'">
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-card rounded-xl border border-border p-4">
                <h3 class="font-medium mb-2">{{ t('telegram.llmBackend') }}</h3>
                <p class="text-lg font-semibold">{{ selectedInstance.llm_backend }}</p>
              </div>
              <div class="bg-card rounded-xl border border-border p-4">
                <h3 class="font-medium mb-2">{{ t('telegram.llmPersona') }}</h3>
                <p class="text-lg font-semibold">{{ selectedInstance.llm_persona }}</p>
              </div>
              <div class="bg-card rounded-xl border border-border p-4">
                <h3 class="font-medium mb-2">{{ t('telegram.ttsEngine') }}</h3>
                <p class="text-lg font-semibold">{{ selectedInstance.tts_engine }}</p>
              </div>
              <div class="bg-card rounded-xl border border-border p-4">
                <h3 class="font-medium mb-2">{{ t('telegram.ttsVoice') }}</h3>
                <p class="text-lg font-semibold">{{ selectedInstance.tts_voice }}</p>
              </div>
            </div>
            <div v-if="selectedInstance.system_prompt" class="bg-card rounded-xl border border-border p-4">
              <h3 class="font-medium mb-2">{{ t('telegram.systemPrompt') }}</h3>
              <p class="text-sm bg-secondary rounded-lg p-3 whitespace-pre-wrap">{{ selectedInstance.system_prompt }}</p>
            </div>
          </template>

          <!-- Sessions Tab -->
          <template v-if="activeTab === 'sessions'">
            <div class="bg-card rounded-xl border border-border p-4">
              <div class="flex items-center justify-between mb-4">
                <h3 class="font-medium">{{ t('telegram.activeSessions') }} ({{ sessions.length }})</h3>
                <button
                  @click="clearSessionsMutation.mutate(selectedInstance.id)"
                  :disabled="clearSessionsMutation.isPending.value || sessions.length === 0"
                  class="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 disabled:opacity-50 transition-colors"
                >
                  <Trash2 class="w-4 h-4" />
                  {{ t('telegram.clearSessions') }}
                </button>
              </div>
              <div v-if="sessions.length === 0" class="text-center py-8 text-muted-foreground">
                {{ t('telegram.noSessions') }}
              </div>
              <div v-else class="space-y-2">
                <div
                  v-for="session in sessions"
                  :key="session.user_id"
                  class="flex items-center justify-between p-3 bg-secondary rounded-lg"
                >
                  <div>
                    <p class="font-medium">
                      {{ session.first_name || session.username || `User ${session.user_id}` }}
                    </p>
                    <p class="text-sm text-muted-foreground">
                      ID: {{ session.user_id }}
                      <span v-if="session.username">• @{{ session.username }}</span>
                    </p>
                  </div>
                  <p class="text-xs text-muted-foreground">{{ session.chat_session_id }}</p>
                </div>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>

    <!-- Create/Edit Dialog -->
    <Teleport to="body">
      <div
        v-if="showCreateDialog || showEditDialog"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        @click.self="showCreateDialog = false; showEditDialog = false"
      >
        <div class="bg-card rounded-xl border border-border w-full max-w-2xl max-h-[90vh] overflow-hidden">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h2 class="text-lg font-semibold">
              {{ showCreateDialog ? t('telegram.createBot') : t('telegram.editBot') }}
            </h2>
            <button
              @click="showCreateDialog = false; showEditDialog = false"
              class="p-1 hover:bg-secondary rounded"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <div class="p-4 overflow-y-auto max-h-[calc(90vh-120px)] space-y-4">
            <!-- Basic Info -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.botName') }} *</label>
                <input
                  v-model="formData.name"
                  type="text"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  :placeholder="t('telegram.botNamePlaceholder')"
                />
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.botDescription') }}</label>
                <input
                  v-model="formData.description"
                  type="text"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <!-- Token -->
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('telegram.botToken') }}</label>
              <div class="relative">
                <input
                  v-model="formData.bot_token"
                  :type="showToken ? 'text' : 'password'"
                  class="w-full px-3 py-2 pr-10 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary font-mono text-sm"
                  :placeholder="t('telegram.tokenPlaceholder')"
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

            <!-- Enabled -->
            <div class="flex items-center justify-between p-3 bg-secondary rounded-lg">
              <div>
                <h4 class="font-medium">{{ t('telegram.enableBot') }}</h4>
                <p class="text-sm text-muted-foreground">{{ t('telegram.enableBotDesc') }}</p>
              </div>
              <button
                @click="formData.enabled = !formData.enabled"
                :class="[
                  'relative w-11 h-6 rounded-full transition-colors',
                  formData.enabled ? 'bg-green-500' : 'bg-gray-500'
                ]"
              >
                <span :class="[
                  'absolute top-1 left-1 w-4 h-4 rounded-full bg-white transition-transform',
                  formData.enabled ? 'translate-x-5' : 'translate-x-0'
                ]" />
              </button>
            </div>

            <!-- Allowed Users -->
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('telegram.allowedUsersList') }}</label>
              <div class="flex gap-2 mb-2">
                <input
                  v-model="newAllowedUser"
                  type="number"
                  class="flex-1 px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  :placeholder="t('telegram.userIdPlaceholder')"
                  @keydown.enter="addAllowedUser"
                />
                <button
                  @click="addAllowedUser"
                  class="px-3 py-2 bg-primary text-primary-foreground rounded-lg"
                >
                  <Plus class="w-4 h-4" />
                </button>
              </div>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="userId in formData.allowed_users"
                  :key="userId"
                  class="flex items-center gap-1 px-2 py-1 bg-secondary rounded text-sm font-mono"
                >
                  {{ userId }}
                  <button @click="removeAllowedUser(userId)" class="text-muted-foreground hover:text-red-400">
                    <X class="w-3 h-3" />
                  </button>
                </span>
                <span v-if="!formData.allowed_users?.length" class="text-sm text-muted-foreground">
                  {{ t('telegram.allUsersAllowed') }}
                </span>
              </div>
            </div>

            <!-- Admin Users -->
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('telegram.adminUsersList') }}</label>
              <div class="flex gap-2 mb-2">
                <input
                  v-model="newAdminUser"
                  type="number"
                  class="flex-1 px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  :placeholder="t('telegram.userIdPlaceholder')"
                  @keydown.enter="addAdminUser"
                />
                <button
                  @click="addAdminUser"
                  class="px-3 py-2 bg-primary text-primary-foreground rounded-lg"
                >
                  <Plus class="w-4 h-4" />
                </button>
              </div>
              <div class="flex flex-wrap gap-1">
                <span
                  v-for="userId in formData.admin_users"
                  :key="userId"
                  class="flex items-center gap-1 px-2 py-1 bg-orange-500/20 text-orange-400 rounded text-sm font-mono"
                >
                  {{ userId }}
                  <button @click="removeAdminUser(userId)" class="hover:text-red-400">
                    <X class="w-3 h-3" />
                  </button>
                </span>
              </div>
            </div>

            <!-- Messages -->
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('telegram.welcomeMessage') }}</label>
              <textarea
                v-model="formData.welcome_message"
                rows="2"
                class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              />
            </div>

            <!-- AI Config -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.llmBackend') }}</label>
                <select
                  v-model="formData.llm_backend"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="vllm">vLLM</option>
                  <option value="gemini">Gemini</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.llmPersona') }}</label>
                <select
                  v-model="formData.llm_persona"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="gulya">Гуля</option>
                  <option value="lidia">Лидия</option>
                </select>
              </div>
            </div>

            <!-- TTS Config -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.ttsEngine') }}</label>
                <select
                  v-model="formData.tts_engine"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="xtts">XTTS v2</option>
                  <option value="piper">Piper</option>
                  <option value="openvoice">OpenVoice</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">{{ t('telegram.ttsVoice') }}</label>
                <select
                  v-model="formData.tts_voice"
                  class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="gulya">Гуля</option>
                  <option value="lidia">Лидия</option>
                </select>
              </div>
            </div>

            <!-- System Prompt -->
            <div>
              <label class="block text-sm font-medium mb-1">{{ t('telegram.systemPrompt') }}</label>
              <textarea
                v-model="formData.system_prompt"
                rows="3"
                class="w-full px-3 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
                :placeholder="t('telegram.systemPromptPlaceholder')"
              />
            </div>
          </div>

          <div class="p-4 border-t border-border flex justify-end gap-2">
            <button
              @click="showCreateDialog = false; showEditDialog = false"
              class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              {{ t('common.cancel') }}
            </button>
            <button
              @click="saveInstance"
              :disabled="createMutation.isPending.value || updateMutation.isPending.value || !formData.name"
              class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Loader2 v-if="createMutation.isPending.value || updateMutation.isPending.value" class="w-4 h-4 animate-spin" />
              <Check v-else class="w-4 h-4" />
              {{ t('common.save') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Logs Dialog -->
    <Teleport to="body">
      <div
        v-if="showLogsDialog"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
        @click.self="showLogsDialog = false"
      >
        <div class="bg-card rounded-xl border border-border w-full max-w-4xl max-h-[90vh] overflow-hidden">
          <div class="p-4 border-b border-border flex items-center justify-between">
            <h2 class="text-lg font-semibold">{{ t('telegram.logs') }} - {{ selectedInstance?.name }}</h2>
            <div class="flex items-center gap-2">
              <button
                @click="() => refetchLogs()"
                class="p-2 hover:bg-secondary rounded-lg transition-colors"
              >
                <RefreshCw class="w-4 h-4" />
              </button>
              <button @click="showLogsDialog = false" class="p-1 hover:bg-secondary rounded">
                <X class="w-5 h-5" />
              </button>
            </div>
          </div>
          <div class="p-4 max-h-[calc(90vh-80px)] overflow-y-auto">
            <pre class="bg-secondary rounded-lg p-4 text-sm font-mono whitespace-pre-wrap overflow-x-auto">{{ logsData?.logs || t('telegram.noLogs') }}</pre>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
