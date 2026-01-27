<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { chatApi, ttsApi, llmApi, sttApi, type ChatSession, type ChatMessage, type ChatSessionSummary } from '@/api'
import {
  MessageSquare,
  Plus,
  Send,
  Trash2,
  Edit3,
  RefreshCw,
  Settings2,
  Check,
  X,
  ChevronLeft,
  Loader2,
  Bot,
  User,
  Copy,
  MoreVertical,
  Volume2,
  VolumeX,
  Square,
  RotateCw,
  FileText,
  Sparkles,
  Mic,
  MicOff
} from 'lucide-vue-next'

const queryClient = useQueryClient()

// State
const currentSessionId = ref<string | null>(null)
const inputMessage = ref('')
const isStreaming = ref(false)
const streamingContent = ref('')
const editingMessageId = ref<string | null>(null)
const editingContent = ref('')
const showSettings = ref(false)
const settingsTab = ref<'session' | 'default'>('session')
const customPrompt = ref('')
const editingDefaultPrompt = ref('')
const isEditingDefault = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const showSidebar = ref(true)

// TTS state
const audioRef = ref<HTMLAudioElement | null>(null)
const audioUrl = ref<string | null>(null)
const speakingMessageId = ref<string | null>(null)
const isSpeaking = ref(false)
const ttsLoading = ref<string | null>(null)

// Voice mode - auto-play TTS for assistant responses
const voiceMode = ref(localStorage.getItem('chat-voice-mode') === 'true')
const pendingTtsMessageId = ref<string | null>(null)

// Voice input (STT) state
const isRecording = ref(false)
const isTranscribing = ref(false)
const mediaRecorder = ref<MediaRecorder | null>(null)
const audioChunks = ref<Blob[]>([])

// Save voice mode preference
watch(voiceMode, (val) => {
  localStorage.setItem('chat-voice-mode', val ? 'true' : 'false')
})

// Queries
const { data: sessionsData, refetch: refetchSessions } = useQuery({
  queryKey: ['chat-sessions'],
  queryFn: () => chatApi.listSessions(),
})

const { data: sessionData, refetch: refetchSession } = useQuery({
  queryKey: ['chat-session', currentSessionId],
  queryFn: () => currentSessionId.value ? chatApi.getSession(currentSessionId.value) : null,
  enabled: computed(() => !!currentSessionId.value),
})

const { data: defaultPromptData } = useQuery({
  queryKey: ['default-prompt'],
  queryFn: () => chatApi.getDefaultPrompt(),
})

// Computed
const sessions = computed(() => sessionsData.value?.sessions || [])
const currentSession = computed(() => sessionData.value?.session)
const messages = computed(() => currentSession.value?.messages || [])
const defaultPrompt = computed(() => defaultPromptData.value?.prompt || '')

// Watch for session change to load custom prompt
watch(currentSession, (session) => {
  if (session) {
    customPrompt.value = session.system_prompt || ''
  }
})

// Mutations
const createSessionMutation = useMutation({
  mutationFn: () => chatApi.createSession(),
  onSuccess: (data) => {
    refetchSessions()
    currentSessionId.value = data.session.id
  },
})

const deleteSessionMutation = useMutation({
  mutationFn: (sessionId: string) => chatApi.deleteSession(sessionId),
  onSuccess: () => {
    refetchSessions()
    if (sessions.value.length > 0) {
      currentSessionId.value = sessions.value[0].id
    } else {
      currentSessionId.value = null
    }
  },
})

const updateSessionMutation = useMutation({
  mutationFn: ({ sessionId, data }: { sessionId: string; data: { title?: string; system_prompt?: string } }) =>
    chatApi.updateSession(sessionId, data),
  onSuccess: () => {
    refetchSession()
    refetchSessions()
  },
})

const sendMessageMutation = useMutation({
  mutationFn: ({ sessionId, content }: { sessionId: string; content: string }) =>
    chatApi.sendMessage(sessionId, content),
  onSuccess: () => {
    refetchSession()
    refetchSessions()
    scrollToBottom()
  },
})

const editMessageMutation = useMutation({
  mutationFn: ({ sessionId, messageId, content }: { sessionId: string; messageId: string; content: string }) =>
    chatApi.editMessage(sessionId, messageId, content),
  onSuccess: () => {
    editingMessageId.value = null
    refetchSession()
    scrollToBottom()
  },
})

const regenerateMutation = useMutation({
  mutationFn: ({ sessionId, messageId }: { sessionId: string; messageId: string }) =>
    chatApi.regenerateResponse(sessionId, messageId),
  onSuccess: () => {
    refetchSession()
    scrollToBottom()
  },
})

const deleteMessageMutation = useMutation({
  mutationFn: ({ sessionId, messageId }: { sessionId: string; messageId: string }) =>
    chatApi.deleteMessage(sessionId, messageId),
  onSuccess: () => {
    refetchSession()
  },
})

const saveDefaultPromptMutation = useMutation({
  mutationFn: ({ persona, prompt }: { persona: string; prompt: string }) =>
    llmApi.setPrompt(persona, prompt),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['default-prompt'] })
    isEditingDefault.value = false
  },
})

const resetDefaultPromptMutation = useMutation({
  mutationFn: (persona: string) => llmApi.resetPrompt(persona),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['default-prompt'] })
    isEditingDefault.value = false
  },
})

// Methods
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function selectSession(sessionId: string) {
  currentSessionId.value = sessionId
  showSidebar.value = false
}

function createNewChat() {
  createSessionMutation.mutate()
}

function deleteCurrentSession() {
  if (currentSessionId.value && confirm('Delete this chat?')) {
    deleteSessionMutation.mutate(currentSessionId.value)
  }
}

function sendMessage() {
  if (!inputMessage.value.trim() || !currentSessionId.value || isStreaming.value) return

  const content = inputMessage.value.trim()
  inputMessage.value = ''

  // Use streaming
  isStreaming.value = true
  streamingContent.value = ''

  let fullContent = ''
  const stream = chatApi.streamMessage(currentSessionId.value, content, (data) => {
    if (data.type === 'chunk' && data.content) {
      streamingContent.value += data.content
      fullContent += data.content
      scrollToBottom()
    } else if (data.type === 'done' || data.type === 'assistant_message') {
      isStreaming.value = false
      const responseText = fullContent || streamingContent.value
      streamingContent.value = ''
      refetchSession()
      refetchSessions()
      scrollToBottom()

      // Voice mode: auto-play TTS for the response
      const messageId = data.message?.id
      if (voiceMode.value && responseText && messageId) {
        // Small delay to ensure session is refetched
        setTimeout(() => {
          speakMessage(messageId, responseText)
        }, 100)
      }
    } else if (data.type === 'error') {
      isStreaming.value = false
      streamingContent.value = ''
      console.error('Stream error:', data.content)
    }
  })
}

function startEditing(message: ChatMessage) {
  editingMessageId.value = message.id
  editingContent.value = message.content
}

function cancelEditing() {
  editingMessageId.value = null
  editingContent.value = ''
}

function saveEdit() {
  if (!currentSessionId.value || !editingMessageId.value) return
  editMessageMutation.mutate({
    sessionId: currentSessionId.value,
    messageId: editingMessageId.value,
    content: editingContent.value,
  })
}

function regenerateResponse(messageId: string) {
  if (!currentSessionId.value) return
  regenerateMutation.mutate({
    sessionId: currentSessionId.value,
    messageId,
  })
}

function deleteMessage(messageId: string) {
  if (!currentSessionId.value) return
  if (confirm('Delete this message and all following?')) {
    deleteMessageMutation.mutate({
      sessionId: currentSessionId.value,
      messageId,
    })
  }
}

function saveSettings() {
  if (!currentSessionId.value) return
  updateSessionMutation.mutate({
    sessionId: currentSessionId.value,
    data: { system_prompt: customPrompt.value || undefined },
  })
  showSettings.value = false
}

function startEditingDefault() {
  editingDefaultPrompt.value = defaultPrompt.value
  isEditingDefault.value = true
}

function cancelEditingDefault() {
  isEditingDefault.value = false
  editingDefaultPrompt.value = ''
}

function saveDefaultPrompt() {
  const persona = defaultPromptData.value?.persona
  if (!persona) return
  saveDefaultPromptMutation.mutate({
    persona,
    prompt: editingDefaultPrompt.value,
  })
}

function resetDefaultPrompt() {
  const persona = defaultPromptData.value?.persona
  if (!persona) return
  if (confirm('Reset to original prompt? This cannot be undone.')) {
    resetDefaultPromptMutation.mutate(persona)
  }
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
}

// TTS functions
async function speakMessage(messageId: string, text: string) {
  // If already speaking this message, stop
  if (speakingMessageId.value === messageId && isSpeaking.value) {
    stopSpeaking()
    return
  }

  // Stop any current playback
  stopSpeaking()

  ttsLoading.value = messageId
  try {
    const blob = await ttsApi.testSynthesize(text)

    // Cleanup previous URL
    if (audioUrl.value) {
      URL.revokeObjectURL(audioUrl.value)
    }

    audioUrl.value = URL.createObjectURL(blob)
    speakingMessageId.value = messageId

    // Play audio
    nextTick(() => {
      if (audioRef.value) {
        audioRef.value.play()
        isSpeaking.value = true
      }
    })
  } catch (e) {
    console.error('TTS failed:', e)
  } finally {
    ttsLoading.value = null
  }
}

function stopSpeaking() {
  if (audioRef.value) {
    audioRef.value.pause()
    audioRef.value.currentTime = 0
  }
  isSpeaking.value = false
  speakingMessageId.value = null
}

function onAudioEnded() {
  isSpeaking.value = false
  speakingMessageId.value = null
}

// Voice input (STT) functions
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

    mediaRecorder.value = new MediaRecorder(stream, {
      mimeType: MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4'
    })
    audioChunks.value = []

    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.value.push(event.data)
      }
    }

    mediaRecorder.value.onstop = async () => {
      // Stop all tracks
      stream.getTracks().forEach(track => track.stop())

      if (audioChunks.value.length === 0) return

      const audioBlob = new Blob(audioChunks.value, { type: mediaRecorder.value?.mimeType || 'audio/webm' })

      // Transcribe
      isTranscribing.value = true
      try {
        const result = await sttApi.transcribe(audioBlob)
        if (result.text) {
          // Append to input or replace
          inputMessage.value = inputMessage.value
            ? inputMessage.value + ' ' + result.text
            : result.text
        }
      } catch (e) {
        console.error('Transcription failed:', e)
      } finally {
        isTranscribing.value = false
      }
    }

    mediaRecorder.value.start()
    isRecording.value = true
  } catch (e) {
    console.error('Failed to start recording:', e)
    alert('Could not access microphone. Please check permissions.')
  }
}

function stopRecording() {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop()
    isRecording.value = false
  }
}

function toggleRecording() {
  if (isRecording.value) {
    stopRecording()
  } else {
    startRecording()
  }
}

// Cleanup on unmount
onUnmounted(() => {
  stopSpeaking()
  stopRecording()
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
  }
})

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Initialize: select first session or create new
onMounted(() => {
  if (sessions.value.length > 0) {
    currentSessionId.value = sessions.value[0].id
  }
})

watch(sessions, (newSessions) => {
  if (!currentSessionId.value && newSessions.length > 0) {
    currentSessionId.value = newSessions[0].id
  }
})
</script>

<template>
  <!-- Hidden audio element for TTS playback -->
  <audio ref="audioRef" :src="audioUrl || undefined" @ended="onAudioEnded" class="hidden" />

  <div class="flex h-[calc(100vh-6rem)] md:h-[calc(100vh-7rem)] -m-4 md:-m-6">
    <!-- Sidebar: Chat List -->
    <div
      :class="[
        'w-72 border-r border-border bg-card flex flex-col transition-all',
        showSidebar ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
        'fixed md:relative inset-y-0 left-0 z-40 md:z-0'
      ]"
    >
      <!-- Header -->
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="font-semibold flex items-center gap-2">
          <MessageSquare class="w-5 h-5" />
          Chats
        </h2>
        <button
          @click="createNewChat"
          :disabled="createSessionMutation.isPending.value"
          class="p-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          <Plus class="w-4 h-4" />
        </button>
      </div>

      <!-- Sessions List -->
      <div class="flex-1 overflow-y-auto">
        <div
          v-for="session in sessions"
          :key="session.id"
          @click="selectSession(session.id)"
          :class="[
            'p-3 cursor-pointer border-b border-border transition-colors',
            currentSessionId === session.id
              ? 'bg-primary/10 border-l-2 border-l-primary'
              : 'hover:bg-secondary/50'
          ]"
        >
          <p class="font-medium text-sm truncate">{{ session.title }}</p>
          <p class="text-xs text-muted-foreground truncate mt-1">
            {{ session.last_message || 'No messages' }}
          </p>
          <p class="text-xs text-muted-foreground mt-1">
            {{ session.message_count }} messages
          </p>
        </div>

        <div v-if="!sessions.length" class="p-4 text-center text-muted-foreground">
          <p>No chats yet</p>
          <button
            @click="createNewChat"
            class="mt-2 text-primary hover:underline"
          >
            Create first chat
          </button>
        </div>
      </div>
    </div>

    <!-- Mobile sidebar toggle -->
    <button
      @click="showSidebar = !showSidebar"
      class="md:hidden fixed left-4 bottom-24 z-50 p-3 bg-primary text-primary-foreground rounded-full shadow-lg"
    >
      <ChevronLeft :class="['w-5 h-5 transition-transform', showSidebar ? '' : 'rotate-180']" />
    </button>

    <!-- Main Chat Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Chat Header -->
      <div v-if="currentSession" class="p-4 border-b border-border flex items-center justify-between bg-card">
        <div class="flex-1 min-w-0">
          <h2 class="font-semibold truncate">{{ currentSession.title }}</h2>
          <p class="text-xs text-muted-foreground">
            {{ messages.length }} messages
            <span v-if="currentSession.system_prompt" class="ml-2 text-primary">
              (custom prompt)
            </span>
          </p>
        </div>
        <div class="flex items-center gap-2">
          <!-- Voice mode toggle -->
          <button
            @click="voiceMode = !voiceMode"
            :class="[
              'p-2 rounded-lg transition-colors',
              voiceMode ? 'bg-primary text-primary-foreground' : 'hover:bg-secondary'
            ]"
            :title="voiceMode ? 'Voice mode ON (click to disable)' : 'Voice mode OFF (click to enable)'"
          >
            <Volume2 v-if="voiceMode" class="w-4 h-4" />
            <VolumeX v-else class="w-4 h-4" />
          </button>
          <button
            @click="showSettings = true"
            class="p-2 rounded-lg hover:bg-secondary transition-colors"
            title="Chat settings"
          >
            <Settings2 class="w-4 h-4" />
          </button>
          <button
            @click="deleteCurrentSession"
            class="p-2 rounded-lg text-red-500 hover:bg-red-500/20 transition-colors"
            title="Delete chat"
          >
            <Trash2 class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div
        ref="messagesContainer"
        class="flex-1 overflow-y-auto p-4 space-y-4"
      >
        <div v-if="!currentSession" class="h-full flex items-center justify-center text-muted-foreground">
          <div class="text-center">
            <MessageSquare class="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>Select a chat or create a new one</p>
          </div>
        </div>

        <template v-else>
          <!-- Messages -->
          <div
            v-for="message in messages"
            :key="message.id"
            :class="[
              'flex gap-3',
              message.role === 'user' ? 'justify-end' : 'justify-start'
            ]"
          >
            <!-- Avatar -->
            <div
              v-if="message.role === 'assistant'"
              class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0"
            >
              <Bot class="w-4 h-4 text-primary" />
            </div>

            <!-- Message Content -->
            <div
              :class="[
                'max-w-[80%] rounded-lg p-3 group relative',
                message.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary'
              ]"
            >
              <!-- Editing mode -->
              <div v-if="editingMessageId === message.id" class="space-y-2">
                <textarea
                  v-model="editingContent"
                  class="w-full min-h-[80px] p-2 bg-background text-foreground rounded resize-none"
                  @keydown.escape="cancelEditing"
                />
                <div class="flex gap-2">
                  <button
                    @click="saveEdit"
                    :disabled="editMessageMutation.isPending.value"
                    class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                  >
                    <Check class="w-3 h-3 inline mr-1" />
                    Save
                  </button>
                  <button
                    @click="cancelEditing"
                    class="px-3 py-1 bg-secondary text-foreground rounded text-sm hover:bg-secondary/80"
                  >
                    <X class="w-3 h-3 inline mr-1" />
                    Cancel
                  </button>
                </div>
              </div>

              <!-- Normal mode -->
              <template v-else>
                <p class="whitespace-pre-wrap break-words">{{ message.content }}</p>
                <div class="flex items-center gap-2 mt-2 text-xs opacity-60">
                  <span>{{ formatTime(message.timestamp) }}</span>
                  <span v-if="message.edited" class="italic">(edited)</span>
                </div>

                <!-- Actions -->
                <div
                  :class="[
                    'absolute top-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1',
                    message.role === 'user' ? 'left-1' : 'right-1'
                  ]"
                >
                  <!-- TTS button for assistant messages -->
                  <button
                    v-if="message.role === 'assistant'"
                    @click="speakMessage(message.id, message.content)"
                    :disabled="ttsLoading === message.id"
                    class="p-1 rounded bg-background/80 hover:bg-background text-foreground"
                    :title="speakingMessageId === message.id && isSpeaking ? 'Stop' : 'Listen'"
                  >
                    <Loader2 v-if="ttsLoading === message.id" class="w-3 h-3 animate-spin" />
                    <Square v-else-if="speakingMessageId === message.id && isSpeaking" class="w-3 h-3 text-primary" />
                    <Volume2 v-else class="w-3 h-3" />
                  </button>
                  <button
                    @click="copyToClipboard(message.content)"
                    class="p-1 rounded bg-background/80 hover:bg-background text-foreground"
                    title="Copy"
                  >
                    <Copy class="w-3 h-3" />
                  </button>
                  <button
                    v-if="message.role === 'user'"
                    @click="startEditing(message)"
                    class="p-1 rounded bg-background/80 hover:bg-background text-foreground"
                    title="Edit"
                  >
                    <Edit3 class="w-3 h-3" />
                  </button>
                  <button
                    v-if="message.role === 'user'"
                    @click="regenerateResponse(message.id)"
                    :disabled="regenerateMutation.isPending.value"
                    class="p-1 rounded bg-background/80 hover:bg-background text-foreground"
                    title="Regenerate response"
                  >
                    <RefreshCw class="w-3 h-3" />
                  </button>
                  <button
                    @click="deleteMessage(message.id)"
                    class="p-1 rounded bg-background/80 hover:bg-background text-red-500"
                    title="Delete"
                  >
                    <Trash2 class="w-3 h-3" />
                  </button>
                </div>
              </template>
            </div>

            <!-- User Avatar -->
            <div
              v-if="message.role === 'user'"
              class="w-8 h-8 rounded-full bg-primary flex items-center justify-center flex-shrink-0"
            >
              <User class="w-4 h-4 text-primary-foreground" />
            </div>
          </div>

          <!-- Streaming response -->
          <div v-if="isStreaming && streamingContent" class="flex gap-3 justify-start">
            <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Bot class="w-4 h-4 text-primary" />
            </div>
            <div class="max-w-[80%] rounded-lg p-3 bg-secondary">
              <p class="whitespace-pre-wrap break-words">{{ streamingContent }}</p>
              <Loader2 class="w-4 h-4 animate-spin mt-2 text-muted-foreground" />
            </div>
          </div>

          <!-- Loading indicator -->
          <div v-if="isStreaming && !streamingContent" class="flex gap-3 justify-start">
            <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
              <Bot class="w-4 h-4 text-primary" />
            </div>
            <div class="rounded-lg p-3 bg-secondary">
              <Loader2 class="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          </div>
        </template>
      </div>

      <!-- Input Area -->
      <div v-if="currentSession" class="p-4 border-t border-border bg-card">
        <div class="flex gap-3 items-end">
          <textarea
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendMessage"
            placeholder="Type a message..."
            rows="1"
            class="flex-1 p-3 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            :disabled="isStreaming || isRecording"
          />
          <!-- Microphone button -->
          <button
            @click="toggleRecording"
            :disabled="isStreaming || isTranscribing"
            :class="[
              'p-3 rounded-lg transition-colors',
              isRecording
                ? 'bg-red-500 text-white animate-pulse'
                : 'bg-secondary hover:bg-secondary/80'
            ]"
            :title="isRecording ? 'Stop recording' : (isTranscribing ? 'Transcribing...' : 'Start voice input')"
          >
            <Loader2 v-if="isTranscribing" class="w-5 h-5 animate-spin" />
            <MicOff v-else-if="isRecording" class="w-5 h-5" />
            <Mic v-else class="w-5 h-5" />
          </button>
          <!-- Send button -->
          <button
            @click="sendMessage"
            :disabled="!inputMessage.trim() || isStreaming || isRecording"
            class="p-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send v-if="!isStreaming" class="w-5 h-5" />
            <Loader2 v-else class="w-5 h-5 animate-spin" />
          </button>
        </div>
        <!-- Recording indicator -->
        <div v-if="isRecording" class="mt-2 flex items-center gap-2 text-sm text-red-500">
          <span class="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          Recording... Click mic to stop
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <div
      v-if="showSettings"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="showSettings = false"
    >
      <div class="bg-card border border-border rounded-lg w-full max-w-2xl p-6 m-4 max-h-[90vh] overflow-y-auto">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <Settings2 class="w-5 h-5" />
          Chat Settings
        </h3>

        <!-- Tabs -->
        <div class="flex gap-2 mb-4 border-b border-border">
          <button
            @click="settingsTab = 'session'"
            :class="[
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              settingsTab === 'session'
                ? 'border-primary text-primary'
                : 'border-transparent hover:text-foreground text-muted-foreground'
            ]"
          >
            <FileText class="w-4 h-4 inline mr-2" />
            Session Prompt
          </button>
          <button
            @click="settingsTab = 'default'"
            :class="[
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              settingsTab === 'default'
                ? 'border-primary text-primary'
                : 'border-transparent hover:text-foreground text-muted-foreground'
            ]"
          >
            <Sparkles class="w-4 h-4 inline mr-2" />
            Default Prompt
          </button>
        </div>

        <!-- Session Prompt Tab -->
        <div v-if="settingsTab === 'session'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Custom System Prompt for This Chat</label>
            <p class="text-xs text-muted-foreground mb-2">
              Leave empty to use the default persona prompt
            </p>
            <textarea
              v-model="customPrompt"
              rows="8"
              class="w-full p-3 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
              placeholder="Enter custom system prompt..."
            />
          </div>

          <div class="p-3 bg-secondary/50 rounded-lg">
            <p class="text-xs font-medium mb-1">Current default ({{ defaultPromptData?.persona }}):</p>
            <p class="text-xs text-muted-foreground whitespace-pre-wrap max-h-24 overflow-y-auto">
              {{ defaultPrompt || 'Loading...' }}
            </p>
          </div>

          <div class="flex justify-end gap-2">
            <button
              @click="showSettings = false"
              class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              Cancel
            </button>
            <button
              @click="saveSettings"
              :disabled="updateSessionMutation.isPending.value"
              class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              Save Session Prompt
            </button>
          </div>
        </div>

        <!-- Default Prompt Tab -->
        <div v-if="settingsTab === 'default'" class="space-y-4">
          <div>
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium">
                Default Persona Prompt ({{ defaultPromptData?.persona }})
              </label>
              <div class="flex gap-2">
                <button
                  v-if="!isEditingDefault"
                  @click="startEditingDefault"
                  class="px-3 py-1 text-xs bg-secondary rounded hover:bg-secondary/80 transition-colors"
                >
                  <Edit3 class="w-3 h-3 inline mr-1" />
                  Edit
                </button>
                <button
                  v-if="!isEditingDefault"
                  @click="resetDefaultPrompt"
                  :disabled="resetDefaultPromptMutation.isPending.value"
                  class="px-3 py-1 text-xs bg-secondary rounded hover:bg-secondary/80 transition-colors text-orange-500"
                >
                  <RotateCw class="w-3 h-3 inline mr-1" />
                  Reset
                </button>
              </div>
            </div>
            <p class="text-xs text-muted-foreground mb-2">
              This prompt is used for all chats that don't have a custom prompt
            </p>

            <!-- View mode -->
            <div v-if="!isEditingDefault" class="p-3 bg-secondary rounded-lg">
              <p class="text-sm whitespace-pre-wrap max-h-64 overflow-y-auto">
                {{ defaultPrompt || 'Loading...' }}
              </p>
            </div>

            <!-- Edit mode -->
            <div v-else class="space-y-3">
              <textarea
                v-model="editingDefaultPrompt"
                rows="12"
                class="w-full p-3 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono text-sm"
                placeholder="Enter default system prompt..."
              />
              <div class="flex justify-end gap-2">
                <button
                  @click="cancelEditingDefault"
                  class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
                >
                  Cancel
                </button>
                <button
                  @click="saveDefaultPrompt"
                  :disabled="saveDefaultPromptMutation.isPending.value"
                  class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  <Loader2 v-if="saveDefaultPromptMutation.isPending.value" class="w-4 h-4 inline mr-1 animate-spin" />
                  Save Default Prompt
                </button>
              </div>
            </div>
          </div>

          <div v-if="!isEditingDefault" class="flex justify-end">
            <button
              @click="showSettings = false"
              class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
