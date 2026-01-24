<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { finetuneApi, type TrainingConfig, type TrainingStatus, type Adapter } from '@/api'
import {
  Sparkles,
  Upload,
  PlayCircle,
  StopCircle,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Database,
  Settings2,
  Loader2,
  FileJson
} from 'lucide-vue-next'
import { ref, computed, watch, onUnmounted } from 'vue'

const queryClient = useQueryClient()

// State
const uploadingFile = ref<File | null>(null)
const uploadProgress = ref(0)
const trainingLog = ref<string[]>([])
const localConfig = ref<Partial<TrainingConfig>>({})
let logEventSource: { close: () => void } | null = null

// Queries
const { data: statsData, refetch: refetchStats } = useQuery({
  queryKey: ['finetune-dataset-stats'],
  queryFn: () => finetuneApi.getDatasetStats(),
})

const { data: configData } = useQuery({
  queryKey: ['finetune-config'],
  queryFn: () => finetuneApi.getConfig(),
})

const { data: statusData, refetch: refetchStatus } = useQuery({
  queryKey: ['finetune-status'],
  queryFn: () => finetuneApi.getTrainingStatus(),
  refetchInterval: (data) => data?.status?.is_running ? 2000 : false,
})

const { data: adaptersData, refetch: refetchAdapters } = useQuery({
  queryKey: ['finetune-adapters'],
  queryFn: () => finetuneApi.listAdapters(),
})

// Watch config data
watch(configData, (data) => {
  if (data?.config) {
    localConfig.value = { ...data.config }
  }
}, { immediate: true })

// Mutations
const uploadMutation = useMutation({
  mutationFn: (file: File) => finetuneApi.uploadDataset(file),
  onSuccess: () => {
    refetchStats()
    uploadingFile.value = null
    uploadProgress.value = 0
  },
})

const processMutation = useMutation({
  mutationFn: () => finetuneApi.processDataset(),
  onSuccess: () => refetchStats(),
})

const augmentMutation = useMutation({
  mutationFn: () => finetuneApi.augmentDataset(),
  onSuccess: () => refetchStats(),
})

const saveConfigMutation = useMutation({
  mutationFn: (config: Partial<TrainingConfig>) => finetuneApi.setConfig(config),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['finetune-config'] }),
})

const startTrainingMutation = useMutation({
  mutationFn: () => finetuneApi.startTraining(),
  onSuccess: () => {
    refetchStatus()
    startLogStream()
  },
})

const stopTrainingMutation = useMutation({
  mutationFn: () => finetuneApi.stopTraining(),
  onSuccess: () => {
    refetchStatus()
    stopLogStream()
  },
})

const activateAdapterMutation = useMutation({
  mutationFn: (adapter: string) => finetuneApi.activateAdapter(adapter),
  onSuccess: () => refetchAdapters(),
})

const deleteAdapterMutation = useMutation({
  mutationFn: (name: string) => finetuneApi.deleteAdapter(name),
  onSuccess: () => refetchAdapters(),
})

// Computed
const stats = computed(() => statsData.value?.stats)
const config = computed(() => configData.value?.config)
const presets = computed(() => configData.value?.presets || {})
const status = computed(() => statusData.value?.status)
const adapters = computed(() => adaptersData.value?.adapters || [])
const activeAdapter = computed(() => adaptersData.value?.active)

const progressPercent = computed(() => {
  if (!status.value?.total_steps) return 0
  return Math.round((status.value.current_step / status.value.total_steps) * 100)
})

const formattedEta = computed(() => {
  if (!status.value?.eta_seconds) return 'N/A'
  const minutes = Math.floor(status.value.eta_seconds / 60)
  const seconds = Math.floor(status.value.eta_seconds % 60)
  return `${minutes}m ${seconds}s`
})

// Methods
function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    uploadingFile.value = file
  }
}

function uploadFile() {
  if (uploadingFile.value) {
    uploadMutation.mutate(uploadingFile.value)
  }
}

function applyPreset(presetName: string) {
  const preset = presets.value[presetName]
  if (preset) {
    localConfig.value = { ...localConfig.value, ...preset }
  }
}

function saveConfig() {
  saveConfigMutation.mutate(localConfig.value)
}

function startLogStream() {
  trainingLog.value = []
  logEventSource = finetuneApi.streamTrainingLog((data) => {
    if (data.type === 'log' && data.line) {
      trainingLog.value.push(data.line)
      // Keep last 1000 lines
      if (trainingLog.value.length > 1000) {
        trainingLog.value = trainingLog.value.slice(-500)
      }
    }
  })
}

function stopLogStream() {
  if (logEventSource) {
    logEventSource.close()
    logEventSource = null
  }
}

onUnmounted(() => {
  stopLogStream()
})
</script>

<template>
  <div class="space-y-6">
    <!-- Dataset Section -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <Database class="w-5 h-5" />
          Dataset
        </h2>
      </div>

      <div class="p-4 space-y-4">
        <!-- Upload -->
        <div class="border-2 border-dashed border-border rounded-lg p-6 text-center">
          <Upload class="w-8 h-8 mx-auto text-muted-foreground mb-2" />
          <p class="text-sm text-muted-foreground mb-4">
            Upload Telegram export (result.json)
          </p>
          <input
            type="file"
            accept=".json"
            class="hidden"
            id="file-upload"
            @change="handleFileSelect"
          />
          <label
            for="file-upload"
            class="inline-block px-4 py-2 bg-secondary rounded-lg cursor-pointer hover:bg-secondary/80 transition-colors"
          >
            Select File
          </label>

          <div v-if="uploadingFile" class="mt-4">
            <p class="text-sm">{{ uploadingFile.name }} ({{ (uploadingFile.size / 1024 / 1024).toFixed(2) }} MB)</p>
            <button
              @click="uploadFile"
              :disabled="uploadMutation.isPending.value"
              class="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Loader2 v-if="uploadMutation.isPending.value" class="w-4 h-4 animate-spin inline mr-2" />
              Upload
            </button>
          </div>
        </div>

        <!-- Stats -->
        <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="p-4 bg-secondary rounded-lg">
            <p class="text-sm text-muted-foreground">Sessions</p>
            <p class="text-2xl font-bold">{{ stats.total_sessions }}</p>
          </div>
          <div class="p-4 bg-secondary rounded-lg">
            <p class="text-sm text-muted-foreground">Messages</p>
            <p class="text-2xl font-bold">{{ stats.total_messages }}</p>
          </div>
          <div class="p-4 bg-secondary rounded-lg">
            <p class="text-sm text-muted-foreground">Tokens</p>
            <p class="text-2xl font-bold">{{ stats.total_tokens?.toLocaleString() }}</p>
          </div>
          <div class="p-4 bg-secondary rounded-lg">
            <p class="text-sm text-muted-foreground">File Size</p>
            <p class="text-2xl font-bold">{{ stats.file_size_mb }} MB</p>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-2">
          <button
            @click="processMutation.mutate()"
            :disabled="processMutation.isPending.value"
            class="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
          >
            <FileJson class="w-4 h-4" />
            Process Dataset
          </button>
          <button
            @click="augmentMutation.mutate()"
            :disabled="augmentMutation.isPending.value"
            class="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
          >
            <Sparkles class="w-4 h-4" />
            Augment
          </button>
        </div>
      </div>
    </div>

    <!-- Training Config -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <Settings2 class="w-5 h-5" />
          Training Configuration
        </h2>
        <button
          @click="saveConfig"
          :disabled="saveConfigMutation.isPending.value"
          class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          Save Config
        </button>
      </div>

      <div class="p-4">
        <!-- Presets -->
        <div class="mb-6">
          <h3 class="text-sm font-medium mb-2">Presets</h3>
          <div class="flex gap-2">
            <button
              v-for="(preset, name) in presets"
              :key="name"
              @click="applyPreset(name as string)"
              class="px-3 py-1.5 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors text-sm"
            >
              {{ name }}
            </button>
          </div>
        </div>

        <!-- Config Form -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm mb-1">LoRA Rank</label>
            <input
              v-model.number="localConfig.lora_rank"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">LoRA Alpha</label>
            <input
              v-model.number="localConfig.lora_alpha"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">Batch Size</label>
            <input
              v-model.number="localConfig.batch_size"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">Grad Accum Steps</label>
            <input
              v-model.number="localConfig.gradient_accumulation_steps"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">Learning Rate</label>
            <input
              v-model.number="localConfig.learning_rate"
              type="number"
              step="0.00001"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">Epochs</label>
            <input
              v-model.number="localConfig.num_epochs"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div>
            <label class="block text-sm mb-1">Max Seq Length</label>
            <input
              v-model.number="localConfig.max_seq_length"
              type="number"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
          <div class="col-span-2">
            <label class="block text-sm mb-1">Output Directory</label>
            <input
              v-model="localConfig.output_dir"
              type="text"
              class="w-full px-3 py-2 bg-secondary rounded-lg"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Training Status -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <PlayCircle class="w-5 h-5" />
          Training
        </h2>
        <div class="flex gap-2">
          <button
            v-if="!status?.is_running"
            @click="startTrainingMutation.mutate()"
            :disabled="startTrainingMutation.isPending.value"
            class="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <PlayCircle class="w-4 h-4" />
            Start
          </button>
          <button
            v-else
            @click="stopTrainingMutation.mutate()"
            :disabled="stopTrainingMutation.isPending.value"
            class="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
          >
            <StopCircle class="w-4 h-4" />
            Stop
          </button>
        </div>
      </div>

      <div class="p-4">
        <!-- Progress -->
        <div v-if="status?.is_running" class="space-y-4">
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span>Progress</span>
              <span>{{ status.current_step }} / {{ status.total_steps }} ({{ progressPercent }}%)</span>
            </div>
            <div class="h-2 bg-secondary rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all"
                :style="{ width: `${progressPercent}%` }"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p class="text-sm text-muted-foreground">Epoch</p>
              <p class="font-medium">{{ status.current_epoch }} / {{ status.total_epochs }}</p>
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Loss</p>
              <p class="font-medium">{{ status.loss?.toFixed(4) }}</p>
            </div>
            <div>
              <p class="text-sm text-muted-foreground">Learning Rate</p>
              <p class="font-medium">{{ status.learning_rate?.toExponential(2) }}</p>
            </div>
            <div>
              <p class="text-sm text-muted-foreground">ETA</p>
              <p class="font-medium">{{ formattedEta }}</p>
            </div>
          </div>
        </div>

        <div v-else-if="status?.error" class="flex items-center gap-2 text-red-500">
          <AlertCircle class="w-5 h-5" />
          {{ status.error }}
        </div>

        <div v-else class="text-muted-foreground text-center py-4">
          Training not running
        </div>

        <!-- Training Log -->
        <div v-if="trainingLog.length" class="mt-4">
          <h3 class="text-sm font-medium mb-2">Training Log</h3>
          <div class="h-48 overflow-auto bg-background rounded-lg p-3 font-mono text-xs">
            <div v-for="(line, i) in trainingLog.slice(-100)" :key="i" class="text-muted-foreground">
              {{ line }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Adapters -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold">LoRA Adapters</h2>
        <button
          @click="refetchAdapters"
          class="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
        >
          <RefreshCw class="w-4 h-4" />
        </button>
      </div>

      <div v-if="!adapters.length" class="p-8 text-center text-muted-foreground">
        No adapters found
      </div>

      <div v-else class="divide-y divide-border">
        <div
          v-for="adapter in adapters"
          :key="adapter.name"
          class="flex items-center justify-between p-4"
        >
          <div class="flex items-center gap-3">
            <CheckCircle2
              v-if="adapter.active"
              class="w-5 h-5 text-green-500"
            />
            <div v-else class="w-5 h-5 rounded-full border-2 border-border" />
            <div>
              <p class="font-medium">{{ adapter.name }}</p>
              <p class="text-sm text-muted-foreground">
                {{ adapter.size_mb }} MB | {{ new Date(adapter.modified).toLocaleDateString() }}
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="!adapter.active"
              @click="activateAdapterMutation.mutate(adapter.name)"
              :disabled="activateAdapterMutation.isPending.value"
              class="px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm"
            >
              Activate
            </button>
            <button
              v-if="!adapter.active"
              @click="deleteAdapterMutation.mutate(adapter.name)"
              :disabled="deleteAdapterMutation.isPending.value"
              class="p-2 text-red-500 hover:bg-red-500/20 rounded-lg transition-colors"
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
