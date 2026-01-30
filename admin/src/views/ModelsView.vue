<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { modelsApi, type ModelInfo, type HuggingFaceModel } from '@/api'
import {
  Search,
  Download,
  Trash2,
  RefreshCw,
  HardDrive,
  Cloud,
  FolderSearch,
  X,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Database,
  MessageSquare,
  Mic,
  AudioWaveform,
  Box,
  Filter,
  ChevronDown,
  ChevronUp
} from 'lucide-vue-next'
import { ref, computed, watch, onUnmounted } from 'vue'

const queryClient = useQueryClient()

// State
const searchQuery = ref('')
const hfSearchQuery = ref('')
const selectedType = ref<string>('all')
const selectedSource = ref<string>('all')
const expandedModel = ref<string | null>(null)
const showDeleteConfirm = ref<string | null>(null)
const selectedHfModel = ref<HuggingFaceModel | null>(null)

// Queries
const { data: modelsData, refetch: refetchModels } = useQuery({
  queryKey: ['local-models'],
  queryFn: () => modelsApi.listModels(),
})

const { data: scanStatusData, refetch: refetchScanStatus } = useQuery({
  queryKey: ['scan-status'],
  queryFn: () => modelsApi.getScanStatus(),
  refetchInterval: (query) => query.state.data?.status?.is_active ? 500 : false,
})

const { data: downloadStatusData, refetch: refetchDownloadStatus } = useQuery({
  queryKey: ['download-status'],
  queryFn: () => modelsApi.getDownloadStatus(),
  refetchInterval: (query) => query.state.data?.status?.is_active ? 1000 : false,
})

const { data: hfSearchData, refetch: searchHuggingFace } = useQuery({
  queryKey: ['hf-search', hfSearchQuery],
  queryFn: () => modelsApi.searchHuggingFace(hfSearchQuery.value, 20),
  enabled: false,
})

// Mutations
const scanMutation = useMutation({
  mutationFn: (includeSystem: boolean) => modelsApi.scanModels(includeSystem),
  onSuccess: () => refetchScanStatus(),
})

const cancelScanMutation = useMutation({
  mutationFn: () => modelsApi.cancelScan(),
})

const downloadMutation = useMutation({
  mutationFn: (repoId: string) => modelsApi.downloadModel(repoId),
  onSuccess: () => {
    refetchDownloadStatus()
    selectedHfModel.value = null
  },
})

const cancelDownloadMutation = useMutation({
  mutationFn: () => modelsApi.cancelDownload(),
})

const deleteMutation = useMutation({
  mutationFn: (path: string) => modelsApi.deleteModel(path),
  onSuccess: () => {
    refetchModels()
    showDeleteConfirm.value = null
  },
})

// Computed
const models = computed(() => modelsData.value?.models || [])
const scanStatus = computed(() => scanStatusData.value?.status)
const downloadStatus = computed(() => downloadStatusData.value?.status)
const hfResults = computed(() => hfSearchData.value?.results || [])

const filteredModels = computed(() => {
  let result = models.value

  // Filter by search query
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(m =>
      m.name.toLowerCase().includes(q) ||
      m.path.toLowerCase().includes(q) ||
      (m.repo_id && m.repo_id.toLowerCase().includes(q))
    )
  }

  // Filter by type
  if (selectedType.value !== 'all') {
    result = result.filter(m => m.type === selectedType.value)
  }

  // Filter by source
  if (selectedSource.value !== 'all') {
    result = result.filter(m => m.source === selectedSource.value)
  }

  return result
})

const modelTypes = computed(() => {
  const types = new Set(models.value.map(m => m.type))
  return ['all', ...Array.from(types)]
})

const modelSources = computed(() => {
  const sources = new Set(models.value.map(m => m.source))
  return ['all', ...Array.from(sources)]
})

const totalSize = computed(() => {
  return models.value.reduce((sum, m) => sum + m.size_gb, 0).toFixed(1)
})

const downloadProgressPercent = computed(() => {
  if (!downloadStatus.value?.total_bytes) return 0
  return Math.round((downloadStatus.value.downloaded_bytes / downloadStatus.value.total_bytes) * 100)
})

// Watch for scan completion
watch(scanStatus, (status, oldStatus) => {
  if (oldStatus?.is_active && !status?.is_active) {
    refetchModels()
  }
})

// Watch for download completion
watch(downloadStatus, (status, oldStatus) => {
  if (oldStatus?.is_active && !status?.is_active && status?.completed) {
    refetchModels()
  }
})

// Methods
function getTypeIcon(type: string) {
  switch (type) {
    case 'llm': return MessageSquare
    case 'tts': return AudioWaveform
    case 'stt': return Mic
    case 'embedding': return Database
    default: return Box
  }
}

function getTypeColor(type: string) {
  switch (type) {
    case 'llm': return 'text-blue-500 bg-blue-500/20'
    case 'tts': return 'text-green-500 bg-green-500/20'
    case 'stt': return 'text-purple-500 bg-purple-500/20'
    case 'embedding': return 'text-orange-500 bg-orange-500/20'
    default: return 'text-gray-500 bg-gray-500/20'
  }
}

function getSourceIcon(source: string) {
  switch (source) {
    case 'huggingface': return Cloud
    case 'ollama': return Box
    default: return HardDrive
  }
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatSpeed(mbps: number): string {
  if (mbps >= 1) return `${mbps.toFixed(1)} MB/s`
  return `${(mbps * 1024).toFixed(0)} KB/s`
}

async function handleHfSearch() {
  if (hfSearchQuery.value.length < 2) return
  await searchHuggingFace()
}

function startDownload(repoId: string) {
  downloadMutation.mutate(repoId)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Header with stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-blue-500/20">
            <Database class="w-5 h-5 text-blue-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Total Models</p>
            <p class="text-2xl font-bold">{{ models.length }}</p>
          </div>
        </div>
      </div>

      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-purple-500/20">
            <HardDrive class="w-5 h-5 text-purple-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">Total Size</p>
            <p class="text-2xl font-bold">{{ totalSize }} GB</p>
          </div>
        </div>
      </div>

      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-green-500/20">
            <MessageSquare class="w-5 h-5 text-green-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">LLM Models</p>
            <p class="text-2xl font-bold">{{ models.filter(m => m.type === 'llm').length }}</p>
          </div>
        </div>
      </div>

      <div class="bg-card rounded-lg border border-border p-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-orange-500/20">
            <AudioWaveform class="w-5 h-5 text-orange-500" />
          </div>
          <div>
            <p class="text-sm text-muted-foreground">TTS/STT Models</p>
            <p class="text-2xl font-bold">{{ models.filter(m => m.type === 'tts' || m.type === 'stt').length }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Scan Section -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between flex-wrap gap-4">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <FolderSearch class="w-5 h-5" />
          Local Models
        </h2>
        <div class="flex gap-2">
          <button
            v-if="!scanStatus?.is_active"
            :disabled="scanMutation.isPending.value"
            class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            @click="scanMutation.mutate(false)"
          >
            <FolderSearch class="w-4 h-4" />
            Scan Models
          </button>
          <button
            v-else
            class="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            @click="cancelScanMutation.mutate()"
          >
            <X class="w-4 h-4" />
            Cancel
          </button>
          <button
            class="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
            @click="() => refetchModels()"
          >
            <RefreshCw class="w-4 h-4" />
          </button>
        </div>
      </div>

      <!-- Scan Progress -->
      <div v-if="scanStatus?.is_active" class="p-4 bg-primary/5 border-b border-border">
        <div class="flex items-center gap-3 mb-2">
          <Loader2 class="w-4 h-4 animate-spin text-primary" />
          <span class="text-sm font-medium">Scanning...</span>
          <span class="text-sm text-muted-foreground">{{ scanStatus.models_found }} models found</span>
        </div>
        <p class="text-xs text-muted-foreground truncate">{{ scanStatus.current_path }}</p>
        <div class="h-1 bg-secondary rounded-full mt-2 overflow-hidden">
          <div class="h-full bg-primary animate-pulse" style="width: 100%" />
        </div>
      </div>

      <!-- Filters -->
      <div class="p-4 border-b border-border flex flex-wrap gap-4">
        <div class="flex-1 min-w-[200px]">
          <div class="relative">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search models..."
              class="w-full pl-10 pr-4 py-2 bg-secondary rounded-lg text-sm"
            />
          </div>
        </div>
        <div class="flex gap-2">
          <select v-model="selectedType" class="px-3 py-2 bg-secondary rounded-lg text-sm">
            <option v-for="type in modelTypes" :key="type" :value="type">
              {{ type === 'all' ? 'All Types' : type.toUpperCase() }}
            </option>
          </select>
          <select v-model="selectedSource" class="px-3 py-2 bg-secondary rounded-lg text-sm">
            <option v-for="source in modelSources" :key="source" :value="source">
              {{ source === 'all' ? 'All Sources' : source }}
            </option>
          </select>
        </div>
      </div>

      <!-- Models List -->
      <div v-if="!filteredModels.length" class="p-8 text-center text-muted-foreground">
        <Database class="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p>No models found</p>
        <p class="text-sm mt-2">Click "Scan Models" to search your system</p>
      </div>

      <div v-else class="divide-y divide-border max-h-[500px] overflow-auto">
        <div
          v-for="model in filteredModels"
          :key="model.path"
          class="p-4 hover:bg-secondary/30 transition-colors"
        >
          <div class="flex items-start gap-4">
            <!-- Type Icon -->
            <div :class="['p-2 rounded-lg', getTypeColor(model.type)]">
              <component :is="getTypeIcon(model.type)" class="w-5 h-5" />
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <h3 class="font-medium">{{ model.name }}</h3>
                <span class="px-2 py-0.5 rounded text-xs bg-secondary">{{ model.format }}</span>
                <span class="px-2 py-0.5 rounded text-xs bg-secondary flex items-center gap-1">
                  <component :is="getSourceIcon(model.source)" class="w-3 h-3" />
                  {{ model.source }}
                </span>
              </div>
              <p class="text-sm text-muted-foreground truncate mt-1">{{ model.path }}</p>
              <div class="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                <span>{{ model.size_gb }} GB</span>
                <span v-if="model.repo_id" class="flex items-center gap-1">
                  <Cloud class="w-3 h-3" />
                  {{ model.repo_id }}
                </span>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-2">
              <button
                class="p-2 text-red-500 hover:bg-red-500/20 rounded-lg transition-colors"
                title="Delete"
                @click="showDeleteConfirm = model.path"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>

          <!-- Delete Confirmation -->
          <div v-if="showDeleteConfirm === model.path" class="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p class="text-sm text-red-500 mb-3">Delete "{{ model.name }}" ({{ model.size_gb }} GB)?</p>
            <div class="flex gap-2">
              <button
                :disabled="deleteMutation.isPending.value"
                class="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 text-sm"
                @click="deleteMutation.mutate(model.path)"
              >
                <Loader2 v-if="deleteMutation.isPending.value" class="w-4 h-4 animate-spin inline mr-1" />
                Delete
              </button>
              <button
                class="px-3 py-1.5 bg-secondary rounded-lg hover:bg-secondary/80 text-sm"
                @click="showDeleteConfirm = null"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Download Section -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <Cloud class="w-5 h-5" />
          Download from HuggingFace
        </h2>
      </div>

      <!-- Download Progress -->
      <div v-if="downloadStatus?.is_active" class="p-4 bg-blue-500/5 border-b border-border">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <Loader2 class="w-4 h-4 animate-spin text-blue-500" />
            <span class="font-medium">Downloading {{ downloadStatus.repo_id }}</span>
          </div>
          <button
            class="p-1 hover:bg-secondary rounded"
            @click="cancelDownloadMutation.mutate()"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
        <p class="text-sm text-muted-foreground mb-2">{{ downloadStatus.filename }}</p>
        <div class="flex items-center gap-4 text-sm mb-2">
          <span>{{ formatBytes(downloadStatus.downloaded_bytes) }} / {{ formatBytes(downloadStatus.total_bytes) }}</span>
          <span v-if="downloadStatus.speed_mbps">{{ formatSpeed(downloadStatus.speed_mbps) }}</span>
          <span>{{ downloadProgressPercent }}%</span>
        </div>
        <div class="h-2 bg-secondary rounded-full overflow-hidden">
          <div
            class="h-full bg-blue-500 transition-all duration-300"
            :style="{ width: `${downloadProgressPercent}%` }"
          />
        </div>
      </div>

      <!-- Download Complete -->
      <div v-else-if="downloadStatus?.completed && !downloadStatus?.error" class="p-4 bg-green-500/5 border-b border-border">
        <div class="flex items-center gap-2 text-green-500">
          <CheckCircle2 class="w-5 h-5" />
          <span>Download complete!</span>
        </div>
      </div>

      <!-- Download Error -->
      <div v-else-if="downloadStatus?.error" class="p-4 bg-red-500/5 border-b border-border">
        <div class="flex items-center gap-2 text-red-500">
          <AlertCircle class="w-5 h-5" />
          <span>{{ downloadStatus.error }}</span>
        </div>
      </div>

      <div class="p-4">
        <!-- Search -->
        <div class="flex gap-2 mb-4">
          <div class="relative flex-1">
            <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              v-model="hfSearchQuery"
              type="text"
              placeholder="Search HuggingFace models..."
              class="w-full pl-10 pr-4 py-2 bg-secondary rounded-lg"
              @keyup.enter="handleHfSearch"
            />
          </div>
          <button
            :disabled="hfSearchQuery.length < 2"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
            @click="handleHfSearch"
          >
            <Search class="w-4 h-4" />
          </button>
        </div>

        <!-- Search Results -->
        <div v-if="hfResults.length" class="space-y-3 max-h-[400px] overflow-auto">
          <div
            v-for="result in hfResults"
            :key="result.repo_id"
            class="p-4 bg-secondary/50 rounded-lg hover:bg-secondary/70 transition-colors"
          >
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <h3 class="font-medium">{{ result.repo_id }}</h3>
                  <span v-if="result.pipeline_tag" class="px-2 py-0.5 rounded text-xs bg-primary/20 text-primary">
                    {{ result.pipeline_tag }}
                  </span>
                </div>
                <div class="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                  <span class="flex items-center gap-1">
                    <Download class="w-3 h-3" />
                    {{ result.downloads?.toLocaleString() }}
                  </span>
                  <span>by {{ result.author }}</span>
                </div>
                <div v-if="result.tags?.length" class="flex flex-wrap gap-1 mt-2">
                  <span
                    v-for="tag in result.tags.slice(0, 5)"
                    :key="tag"
                    class="px-2 py-0.5 rounded text-xs bg-secondary"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-2">
                <a
                  :href="`https://huggingface.co/${result.repo_id}`"
                  target="_blank"
                  class="p-2 hover:bg-secondary rounded-lg transition-colors"
                  title="View on HuggingFace"
                >
                  <ExternalLink class="w-4 h-4" />
                </a>
                <button
                  :disabled="downloadStatus?.is_active"
                  class="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm"
                  @click="startDownload(result.repo_id)"
                >
                  <Download class="w-4 h-4" />
                  Download
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Download -->
        <div v-else class="text-center text-muted-foreground py-8">
          <Cloud class="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>Search for models on HuggingFace</p>
          <p class="text-sm mt-2">Or enter a repo ID directly (e.g., "Qwen/Qwen2.5-7B-Instruct")</p>
          <div class="flex items-center justify-center gap-2 mt-4">
            <input
              v-model="hfSearchQuery"
              type="text"
              placeholder="owner/model-name"
              class="px-4 py-2 bg-secondary rounded-lg text-sm w-64"
            />
            <button
              :disabled="!hfSearchQuery || downloadStatus?.is_active"
              class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm"
              @click="startDownload(hfSearchQuery)"
            >
              <Download class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
