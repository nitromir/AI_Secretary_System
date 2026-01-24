<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { llmApi, type LlmParams } from '@/api'
import {
  Brain,
  User,
  Settings2,
  Trash2,
  Save,
  RotateCw,
  AlertCircle,
  CheckCircle2
} from 'lucide-vue-next'
import { ref, computed, watch } from 'vue'

const queryClient = useQueryClient()

// State
const editingPrompt = ref(false)
const promptText = ref('')
const selectedPersonaForPrompt = ref('gulya')

// Queries
const { data: backendData, isLoading: backendLoading } = useQuery({
  queryKey: ['llm-backend'],
  queryFn: () => llmApi.getBackend(),
})

const { data: personasData } = useQuery({
  queryKey: ['llm-personas'],
  queryFn: () => llmApi.getPersonas(),
})

const { data: currentPersonaData } = useQuery({
  queryKey: ['llm-persona'],
  queryFn: () => llmApi.getCurrentPersona(),
})

const { data: paramsData } = useQuery({
  queryKey: ['llm-params'],
  queryFn: () => llmApi.getParams(),
})

const { data: historyData, refetch: refetchHistory } = useQuery({
  queryKey: ['llm-history'],
  queryFn: () => llmApi.getHistory(),
})

// Local state for params
const localParams = ref<Partial<LlmParams>>({})

watch(paramsData, (data) => {
  if (data?.params) {
    localParams.value = { ...data.params }
  }
}, { immediate: true })

// Mutations
const setBackendMutation = useMutation({
  mutationFn: (backend: 'vllm' | 'gemini') => llmApi.setBackend(backend),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['llm-backend'] }),
})

const setPersonaMutation = useMutation({
  mutationFn: (persona: string) => llmApi.setPersona(persona),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['llm-persona'] })
    queryClient.invalidateQueries({ queryKey: ['llm-history'] })
  },
})

const setParamsMutation = useMutation({
  mutationFn: (params: Partial<LlmParams>) => llmApi.setParams(params),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['llm-params'] }),
})

const clearHistoryMutation = useMutation({
  mutationFn: () => llmApi.clearHistory(),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['llm-history'] }),
})

const savePromptMutation = useMutation({
  mutationFn: ({ persona, prompt }: { persona: string; prompt: string }) =>
    llmApi.setPrompt(persona, prompt),
  onSuccess: () => {
    editingPrompt.value = false
  },
})

// Computed
const personas = computed(() => personasData.value?.personas || {})

const isVllm = computed(() => backendData.value?.backend === 'vllm')

// Methods
async function loadPromptForEdit(personaId: string) {
  selectedPersonaForPrompt.value = personaId
  try {
    const response = await llmApi.getPrompt(personaId)
    promptText.value = response.prompt
    editingPrompt.value = true
  } catch (e) {
    console.error('Failed to load prompt:', e)
  }
}

function saveParams() {
  setParamsMutation.mutate(localParams.value)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Backend Selection -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <Brain class="w-5 h-5" />
          LLM Backend
        </h2>
      </div>

      <div class="p-4">
        <div v-if="backendLoading" class="text-muted-foreground">Loading...</div>
        <div v-else class="space-y-4">
          <div class="flex items-center gap-4">
            <div class="grid grid-cols-2 gap-2 p-1 bg-secondary rounded-lg">
              <button
                @click="setBackendMutation.mutate('vllm')"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors',
                  isVllm ? 'bg-primary text-primary-foreground' : 'hover:bg-secondary/80'
                ]"
              >
                vLLM (Local)
              </button>
              <button
                @click="setBackendMutation.mutate('gemini')"
                :class="[
                  'px-4 py-2 rounded-lg transition-colors',
                  !isVllm ? 'bg-primary text-primary-foreground' : 'hover:bg-secondary/80'
                ]"
              >
                Gemini (Cloud)
              </button>
            </div>
          </div>

          <div class="flex items-center gap-2 text-sm">
            <CheckCircle2 class="w-4 h-4 text-green-500" />
            <span>Current: <strong>{{ backendData?.backend }}</strong></span>
            <span v-if="backendData?.model" class="text-muted-foreground">
              ({{ backendData.model }})
            </span>
          </div>

          <div v-if="setBackendMutation.data?.value?.message" class="flex items-center gap-2 text-sm text-yellow-500">
            <AlertCircle class="w-4 h-4" />
            {{ setBackendMutation.data?.value?.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- Persona Selection -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <User class="w-5 h-5" />
          Secretary Persona
        </h2>
      </div>

      <div class="p-4">
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="(persona, id) in personas"
            :key="id"
            @click="setPersonaMutation.mutate(id as string)"
            :class="[
              'p-4 rounded-lg border cursor-pointer transition-all',
              currentPersonaData?.id === id
                ? 'border-primary bg-primary/10'
                : 'border-border hover:border-primary/50'
            ]"
          >
            <div class="font-medium">{{ persona.name }}</div>
            <div class="text-sm text-muted-foreground">{{ persona.full_name }}</div>
            <button
              @click.stop="loadPromptForEdit(id as string)"
              class="mt-2 text-xs text-primary hover:underline"
            >
              Edit Prompt
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Generation Parameters -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <Settings2 class="w-5 h-5" />
          Generation Parameters
        </h2>
        <button
          @click="saveParams"
          :disabled="setParamsMutation.isPending.value"
          class="flex items-center gap-2 px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          <Save class="w-4 h-4" />
          Save
        </button>
      </div>

      <div class="p-4 grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Temperature -->
        <div>
          <label class="flex items-center justify-between text-sm mb-2">
            <span>Temperature</span>
            <span class="text-muted-foreground">{{ localParams.temperature?.toFixed(2) }}</span>
          </label>
          <input
            v-model.number="localParams.temperature"
            type="range"
            min="0"
            max="2"
            step="0.05"
            class="w-full"
          />
          <p class="text-xs text-muted-foreground mt-1">Higher = more creative, lower = more focused</p>
        </div>

        <!-- Max Tokens -->
        <div>
          <label class="flex items-center justify-between text-sm mb-2">
            <span>Max Tokens</span>
            <span class="text-muted-foreground">{{ localParams.max_tokens }}</span>
          </label>
          <input
            v-model.number="localParams.max_tokens"
            type="range"
            min="64"
            max="2048"
            step="64"
            class="w-full"
          />
          <p class="text-xs text-muted-foreground mt-1">Maximum response length</p>
        </div>

        <!-- Top P -->
        <div>
          <label class="flex items-center justify-between text-sm mb-2">
            <span>Top P</span>
            <span class="text-muted-foreground">{{ localParams.top_p?.toFixed(2) }}</span>
          </label>
          <input
            v-model.number="localParams.top_p"
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            class="w-full"
          />
          <p class="text-xs text-muted-foreground mt-1">Nucleus sampling threshold</p>
        </div>

        <!-- Repetition Penalty -->
        <div>
          <label class="flex items-center justify-between text-sm mb-2">
            <span>Repetition Penalty</span>
            <span class="text-muted-foreground">{{ localParams.repetition_penalty?.toFixed(2) }}</span>
          </label>
          <input
            v-model.number="localParams.repetition_penalty"
            type="range"
            min="1"
            max="2"
            step="0.05"
            class="w-full"
          />
          <p class="text-xs text-muted-foreground mt-1">Higher = less repetition</p>
        </div>
      </div>
    </div>

    <!-- Conversation History -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold">
          Conversation History
          <span v-if="historyData?.count" class="text-sm font-normal text-muted-foreground">
            ({{ historyData.count }} messages)
          </span>
        </h2>
        <div class="flex items-center gap-2">
          <button
            @click="refetchHistory"
            class="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
          >
            <RotateCw class="w-4 h-4" />
          </button>
          <button
            @click="clearHistoryMutation.mutate()"
            :disabled="clearHistoryMutation.isPending.value || !historyData?.count"
            class="flex items-center gap-2 px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            <Trash2 class="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>

      <div class="max-h-64 overflow-auto p-4">
        <div v-if="!historyData?.history?.length" class="text-muted-foreground text-center py-4">
          No conversation history
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="(msg, i) in historyData.history"
            :key="i"
            :class="[
              'p-3 rounded-lg',
              msg.role === 'user' ? 'bg-secondary' : 'bg-primary/10 ml-4'
            ]"
          >
            <div class="text-xs text-muted-foreground mb-1 capitalize">{{ msg.role }}</div>
            <div class="text-sm">{{ msg.content }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Prompt Editor Modal -->
    <div
      v-if="editingPrompt"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="editingPrompt = false"
    >
      <div class="bg-card border border-border rounded-lg w-full max-w-2xl p-6">
        <h3 class="text-lg font-semibold mb-4">
          Edit System Prompt: {{ personas[selectedPersonaForPrompt]?.name }}
        </h3>

        <textarea
          v-model="promptText"
          rows="15"
          class="w-full p-3 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none font-mono text-sm"
        />

        <div class="flex justify-end gap-2 mt-4">
          <button
            @click="editingPrompt = false"
            class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="savePromptMutation.mutate({ persona: selectedPersonaForPrompt, prompt: promptText })"
            :disabled="savePromptMutation.isPending.value"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            Save Prompt
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
