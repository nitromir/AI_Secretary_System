<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { auditApi, type AuditLog, type AuditQueryParams } from '@/api'
import {
  FileText,
  Search,
  Download,
  Trash2,
  RefreshCw,
  Filter,
  Calendar,
  User,
  Activity,
  Database,
  ChevronLeft,
  ChevronRight,
  X,
  Info
} from 'lucide-vue-next'
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const queryClient = useQueryClient()

// Filters state
const filters = ref<AuditQueryParams>({
  action: undefined,
  resource: undefined,
  user_id: undefined,
  from_date: undefined,
  to_date: undefined,
  limit: 50,
  offset: 0,
})

const showFilters = ref(false)
const selectedLog = ref<AuditLog | null>(null)

// Queries
const { data: logsData, isLoading, refetch } = useQuery({
  queryKey: ['audit-logs', filters],
  queryFn: () => auditApi.getLogs(filters.value),
})

const { data: statsData, isLoading: statsLoading } = useQuery({
  queryKey: ['audit-stats'],
  queryFn: () => auditApi.getStats(),
})

// Mutations
const cleanupMutation = useMutation({
  mutationFn: (days: number) => auditApi.cleanup(days),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['audit-logs'] })
    queryClient.invalidateQueries({ queryKey: ['audit-stats'] })
  },
})

// Computed
const logs = computed(() => logsData.value?.logs || [])
const stats = computed(() => statsData.value?.stats)

const currentPage = computed(() => Math.floor((filters.value.offset || 0) / (filters.value.limit || 50)) + 1)
const hasMore = computed(() => logs.value.length >= (filters.value.limit || 50))

const uniqueActions = computed(() => {
  if (!stats.value?.by_action) return []
  return Object.keys(stats.value.by_action).sort()
})

const uniqueResources = computed(() => {
  if (!stats.value?.by_resource) return []
  return Object.keys(stats.value.by_resource).sort()
})

// Methods
function applyFilters() {
  filters.value.offset = 0
  refetch()
}

function clearFilters() {
  filters.value = {
    action: undefined,
    resource: undefined,
    user_id: undefined,
    from_date: undefined,
    to_date: undefined,
    limit: 50,
    offset: 0,
  }
  refetch()
}

function nextPage() {
  filters.value.offset = (filters.value.offset || 0) + (filters.value.limit || 50)
  refetch()
}

function prevPage() {
  const newOffset = (filters.value.offset || 0) - (filters.value.limit || 50)
  filters.value.offset = Math.max(0, newOffset)
  refetch()
}

async function exportLogs(format: 'json' | 'csv') {
  try {
    if (format === 'csv') {
      // For CSV, we need to fetch as blob
      const response = await fetch(`/admin/audit/export?format=csv${filters.value.from_date ? '&from_date=' + filters.value.from_date : ''}${filters.value.to_date ? '&to_date=' + filters.value.to_date : ''}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('admin_token')}`
        }
      })
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`
      a.click()
      window.URL.revokeObjectURL(url)
    } else {
      const data = await auditApi.exportLogs({
        from_date: filters.value.from_date,
        to_date: filters.value.to_date,
        format: 'json'
      })
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit_logs_${new Date().toISOString().split('T')[0]}.json`
      a.click()
      window.URL.revokeObjectURL(url)
    }
  } catch (error) {
    console.error('Export failed:', error)
  }
}

function formatDate(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleString()
}

function getActionColor(action: string) {
  switch (action) {
    case 'create': return 'bg-green-500/20 text-green-400'
    case 'update': return 'bg-blue-500/20 text-blue-400'
    case 'delete': return 'bg-red-500/20 text-red-400'
    case 'login': return 'bg-purple-500/20 text-purple-400'
    case 'logout': return 'bg-gray-500/20 text-gray-400'
    default: return 'bg-primary/20 text-primary'
  }
}

function parseDetails(details: string | null): Record<string, unknown> | null {
  if (!details) return null
  try {
    return JSON.parse(details)
  } catch {
    return null
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
            <FileText class="w-5 h-5 text-primary" />
          </div>
          <div>
            <div class="text-2xl font-bold">{{ stats?.total || 0 }}</div>
            <div class="text-sm text-muted-foreground">{{ t('audit.totalLogs') }}</div>
          </div>
        </div>
      </div>

      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Activity class="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <div class="text-2xl font-bold">{{ stats?.last_24h || 0 }}</div>
            <div class="text-sm text-muted-foreground">{{ t('audit.last24h') }}</div>
          </div>
        </div>
      </div>

      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
            <Database class="w-5 h-5 text-green-400" />
          </div>
          <div>
            <div class="text-2xl font-bold">{{ Object.keys(stats?.by_resource || {}).length }}</div>
            <div class="text-sm text-muted-foreground">{{ t('audit.resources') }}</div>
          </div>
        </div>
      </div>

      <div class="bg-card border border-border rounded-xl p-4">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <User class="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <div class="text-2xl font-bold">{{ Object.keys(stats?.by_action || {}).length }}</div>
            <div class="text-sm text-muted-foreground">{{ t('audit.actions') }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Toolbar -->
    <div class="flex items-center gap-4 flex-wrap">
      <button
        @click="showFilters = !showFilters"
        :class="[
          'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
          showFilters ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
        ]"
      >
        <Filter class="w-4 h-4" />
        {{ t('audit.filters') }}
      </button>

      <button
        @click="refetch()"
        :disabled="isLoading"
        class="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors disabled:opacity-50"
      >
        <RefreshCw :class="['w-4 h-4', isLoading && 'animate-spin']" />
        {{ t('common.refresh') }}
      </button>

      <div class="flex-1" />

      <div class="flex items-center gap-2">
        <button
          @click="exportLogs('json')"
          class="flex items-center gap-2 px-3 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
        >
          <Download class="w-4 h-4" />
          JSON
        </button>
        <button
          @click="exportLogs('csv')"
          class="flex items-center gap-2 px-3 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
        >
          <Download class="w-4 h-4" />
          CSV
        </button>
      </div>

      <button
        @click="cleanupMutation.mutate(90)"
        :disabled="cleanupMutation.isPending.value"
        class="flex items-center gap-2 px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors disabled:opacity-50"
        :title="t('audit.cleanupTitle')"
      >
        <Trash2 class="w-4 h-4" />
        {{ t('audit.cleanup') }}
      </button>
    </div>

    <!-- Filters Panel -->
    <div v-if="showFilters" class="bg-card border border-border rounded-xl p-4 space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">{{ t('audit.action') }}</label>
          <select
            v-model="filters.action"
            class="w-full px-3 py-2 bg-secondary rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option :value="undefined">{{ t('audit.allActions') }}</option>
            <option v-for="action in uniqueActions" :key="action" :value="action">
              {{ action }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('audit.resource') }}</label>
          <select
            v-model="filters.resource"
            class="w-full px-3 py-2 bg-secondary rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option :value="undefined">{{ t('audit.allResources') }}</option>
            <option v-for="resource in uniqueResources" :key="resource" :value="resource">
              {{ resource }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('audit.fromDate') }}</label>
          <input
            v-model="filters.from_date"
            type="datetime-local"
            class="w-full px-3 py-2 bg-secondary rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">{{ t('audit.toDate') }}</label>
          <input
            v-model="filters.to_date"
            type="datetime-local"
            class="w-full px-3 py-2 bg-secondary rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div class="flex items-end gap-2">
          <button
            @click="applyFilters"
            class="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            {{ t('audit.apply') }}
          </button>
          <button
            @click="clearFilters"
            class="px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
          >
            <X class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Logs Table -->
    <div class="bg-card border border-border rounded-xl overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-secondary/50">
            <tr>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.timestamp') }}</th>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.action') }}</th>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.resource') }}</th>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.user') }}</th>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.ip') }}</th>
              <th class="px-4 py-3 text-left text-sm font-medium">{{ t('audit.details') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <tr
              v-for="log in logs"
              :key="log.id"
              class="hover:bg-secondary/30 transition-colors cursor-pointer"
              @click="selectedLog = log"
            >
              <td class="px-4 py-3 text-sm whitespace-nowrap">
                {{ formatDate(log.timestamp) }}
              </td>
              <td class="px-4 py-3">
                <span :class="['px-2 py-1 text-xs font-medium rounded-full', getActionColor(log.action)]">
                  {{ log.action }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm">
                {{ log.resource }}
                <span v-if="log.resource_id" class="text-muted-foreground">
                  #{{ log.resource_id }}
                </span>
              </td>
              <td class="px-4 py-3 text-sm">
                {{ log.user_id || '-' }}
              </td>
              <td class="px-4 py-3 text-sm text-muted-foreground">
                {{ log.user_ip || '-' }}
              </td>
              <td class="px-4 py-3">
                <button
                  v-if="log.details"
                  class="text-primary hover:text-primary/80"
                  @click.stop="selectedLog = log"
                >
                  <Info class="w-4 h-4" />
                </button>
                <span v-else class="text-muted-foreground">-</span>
              </td>
            </tr>
            <tr v-if="logs.length === 0 && !isLoading">
              <td colspan="6" class="px-4 py-8 text-center text-muted-foreground">
                {{ t('audit.noLogs') }}
              </td>
            </tr>
            <tr v-if="isLoading">
              <td colspan="6" class="px-4 py-8 text-center text-muted-foreground">
                {{ t('common.loading') }}...
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between px-4 py-3 border-t border-border">
        <div class="text-sm text-muted-foreground">
          {{ t('audit.showing') }} {{ logs.length }} {{ t('audit.records') }}
        </div>
        <div class="flex items-center gap-2">
          <button
            @click="prevPage"
            :disabled="currentPage === 1"
            class="p-2 rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft class="w-4 h-4" />
          </button>
          <span class="text-sm">{{ t('audit.page') }} {{ currentPage }}</span>
          <button
            @click="nextPage"
            :disabled="!hasMore"
            class="p-2 rounded-lg hover:bg-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronRight class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Details Modal -->
    <div
      v-if="selectedLog"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="selectedLog = null"
    >
      <div class="bg-card border border-border rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-auto">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">{{ t('audit.logDetails') }}</h3>
          <button
            @click="selectedLog = null"
            class="p-1 hover:bg-secondary rounded-lg transition-colors"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <div class="text-sm text-muted-foreground">{{ t('audit.timestamp') }}</div>
              <div class="font-medium">{{ formatDate(selectedLog.timestamp) }}</div>
            </div>
            <div>
              <div class="text-sm text-muted-foreground">{{ t('audit.action') }}</div>
              <span :class="['px-2 py-1 text-xs font-medium rounded-full', getActionColor(selectedLog.action)]">
                {{ selectedLog.action }}
              </span>
            </div>
            <div>
              <div class="text-sm text-muted-foreground">{{ t('audit.resource') }}</div>
              <div class="font-medium">
                {{ selectedLog.resource }}
                <span v-if="selectedLog.resource_id" class="text-muted-foreground">
                  #{{ selectedLog.resource_id }}
                </span>
              </div>
            </div>
            <div>
              <div class="text-sm text-muted-foreground">{{ t('audit.user') }}</div>
              <div class="font-medium">{{ selectedLog.user_id || '-' }}</div>
            </div>
            <div>
              <div class="text-sm text-muted-foreground">{{ t('audit.ip') }}</div>
              <div class="font-medium">{{ selectedLog.user_ip || '-' }}</div>
            </div>
          </div>

          <div v-if="selectedLog.details">
            <div class="text-sm text-muted-foreground mb-2">{{ t('audit.details') }}</div>
            <pre class="bg-secondary/50 p-4 rounded-lg text-sm overflow-auto max-h-64">{{ JSON.stringify(parseDetails(selectedLog.details), null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
