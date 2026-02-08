<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import {
  Users,
  Building2,
  Link2,
  Settings2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Check,
  X as XIcon,
  Save,
  ArrowDownUp,
  Clock
} from 'lucide-vue-next'
import { amocrmApi } from '@/api/amocrm'
import type { AmoCRMSyncLogEntry } from '@/api/amocrm'

const { t } = useI18n()
const route = useRoute()

// amoCRM integration state
const isConnected = ref(false)
const isLoading = ref(false)
const isSyncing = ref(false)
const isSaving = ref(false)
const toast = ref<{ message: string; type: 'success' | 'error' } | null>(null)

// Settings form
const settings = ref({
  subdomain: '',
  clientId: '',
  clientSecret: '',
  redirectUri: window.location.origin + '/admin/crm/oauth-redirect',
  syncContacts: true,
  syncLeads: true,
  syncTasks: false,
  autoCreateLead: true,
  leadPipelineId: '',
  leadStatusId: ''
})

// Stats
const stats = ref({
  contacts: 0,
  leads: 0,
  lastSync: null as string | null
})

// Account info
const accountInfo = ref<Record<string, unknown>>({})

// Sync log
const syncLogs = ref<AmoCRMSyncLogEntry[]>([])
const showSyncLog = ref(false)

function showToast(message: string, type: 'success' | 'error' = 'success') {
  toast.value = { message, type }
  setTimeout(() => { toast.value = null }, 3000)
}

async function loadConfig() {
  try {
    const resp = await amocrmApi.getConfig()
    const config = resp.config
    if (config && config.subdomain) {
      settings.value.subdomain = config.subdomain || ''
      settings.value.clientId = config.client_id || ''
      settings.value.redirectUri = config.redirect_uri || window.location.origin + '/admin/crm/oauth-redirect'
      settings.value.syncContacts = config.sync_contacts ?? true
      settings.value.syncLeads = config.sync_leads ?? true
      settings.value.syncTasks = config.sync_tasks ?? false
      settings.value.autoCreateLead = config.auto_create_lead ?? true
      settings.value.leadPipelineId = config.lead_pipeline_id ? String(config.lead_pipeline_id) : ''
      settings.value.leadStatusId = config.lead_status_id ? String(config.lead_status_id) : ''
      isConnected.value = config.is_connected || false
      stats.value.contacts = config.contacts_count || 0
      stats.value.leads = config.leads_count || 0
      stats.value.lastSync = config.last_sync_at || null
      accountInfo.value = config.account_info || {}
    }
  } catch {
    // Config not yet created — expected on first load
  }
}

async function connectAmoCRM() {
  isLoading.value = true
  try {
    // Save credentials first
    await amocrmApi.saveConfig({
      subdomain: settings.value.subdomain,
      client_id: settings.value.clientId,
      client_secret: settings.value.clientSecret,
      redirect_uri: settings.value.redirectUri,
      sync_contacts: settings.value.syncContacts,
      sync_leads: settings.value.syncLeads,
      sync_tasks: settings.value.syncTasks,
      auto_create_lead: settings.value.autoCreateLead,
    })

    // Get OAuth URL and redirect
    const resp = await amocrmApi.getAuthUrl()
    window.location.href = resp.auth_url
  } catch {
    showToast(t('crm.connectionFail'), 'error')
    isLoading.value = false
  }
}

async function disconnectAmoCRM() {
  try {
    await amocrmApi.disconnect()
    isConnected.value = false
    stats.value = { contacts: 0, leads: 0, lastSync: null }
    accountInfo.value = {}
  } catch {
    showToast(t('crm.connectionFail'), 'error')
  }
}

async function testConnection() {
  isLoading.value = true
  try {
    const resp = await amocrmApi.testConnection()
    if (resp.account) {
      accountInfo.value = resp.account
    }
    showToast(t('crm.connectionOk'))
  } catch {
    showToast(t('crm.connectionFail'), 'error')
  } finally {
    isLoading.value = false
  }
}

async function saveSettings() {
  isSaving.value = true
  try {
    await amocrmApi.saveConfig({
      sync_contacts: settings.value.syncContacts,
      sync_leads: settings.value.syncLeads,
      sync_tasks: settings.value.syncTasks,
      auto_create_lead: settings.value.autoCreateLead,
      lead_pipeline_id: settings.value.leadPipelineId ? Number(settings.value.leadPipelineId) : null,
      lead_status_id: settings.value.leadStatusId ? Number(settings.value.leadStatusId) : null,
    })
    showToast(t('crm.settingsSaved'))
  } catch {
    showToast(t('crm.connectionFail'), 'error')
  } finally {
    isSaving.value = false
  }
}

async function syncNow() {
  isSyncing.value = true
  try {
    const resp = await amocrmApi.sync()
    stats.value.contacts = resp.contacts_count
    stats.value.leads = resp.leads_count
    stats.value.lastSync = resp.synced_at
    showToast(t('crm.syncSuccess'))
  } catch {
    showToast(t('crm.connectionFail'), 'error')
  } finally {
    isSyncing.value = false
  }
}

async function loadSyncLog() {
  showSyncLog.value = !showSyncLog.value
  if (showSyncLog.value) {
    try {
      const resp = await amocrmApi.getSyncLog()
      syncLogs.value = resp.logs
    } catch {
      syncLogs.value = []
    }
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

onMounted(async () => {
  await loadConfig()

  // Check for OAuth redirect result
  const query = route.query
  if (query.connected === 'true') {
    showToast(t('crm.connectedSuccess'))
    await loadConfig()
  } else if (query.error) {
    showToast(String(query.error), 'error')
  }
})
</script>

<template>
  <div class="space-y-6">
    <!-- Toast -->
    <Transition name="fade">
      <div
        v-if="toast"
        :class="[
          'fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium',
          toast.type === 'success' ? 'bg-green-500/90 text-white' : 'bg-red-500/90 text-white'
        ]"
      >
        {{ toast.message }}
      </div>
    </Transition>

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-lg bg-blue-500/20">
          <Users class="w-6 h-6 text-blue-500" />
        </div>
        <div>
          <h1 class="text-2xl font-bold">{{ t('crm.title') }}</h1>
          <p class="text-muted-foreground">{{ t('crm.description') }}</p>
        </div>
      </div>
    </div>

    <!-- Connection Status Card -->
    <div class="card p-6">
      <div class="flex items-center justify-between mb-6">
        <div class="flex items-center gap-3">
          <Building2 class="w-8 h-8 text-blue-500" />
          <div>
            <h2 class="text-lg font-semibold">amoCRM</h2>
            <p class="text-sm text-muted-foreground">{{ t('crm.amoDescription') }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span
            :class="[
              'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
              isConnected
                ? 'bg-green-500/20 text-green-400'
                : 'bg-yellow-500/20 text-yellow-400'
            ]"
          >
            <span :class="['w-2 h-2 rounded-full', isConnected ? 'bg-green-400' : 'bg-yellow-400']" />
            {{ isConnected ? t('crm.connected') : t('crm.notConnected') }}
          </span>
        </div>
      </div>

      <!-- Not Connected State -->
      <template v-if="!isConnected">
        <div class="p-4 rounded-lg bg-secondary/50 border border-border mb-6">
          <div class="flex gap-3">
            <AlertCircle class="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
            <div>
              <p class="text-sm font-medium">{{ t('crm.setupRequired') }}</p>
              <p class="text-sm text-muted-foreground mt-1">{{ t('crm.setupDescription') }}</p>
            </div>
          </div>
        </div>

        <!-- Settings Form -->
        <div class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1.5">{{ t('crm.subdomain') }}</label>
              <div class="flex">
                <input
                  v-model="settings.subdomain"
                  type="text"
                  placeholder="your-company"
                  class="input rounded-r-none flex-1"
                />
                <span class="inline-flex items-center px-3 bg-secondary border border-l-0 border-border rounded-r-lg text-sm text-muted-foreground">
                  .amocrm.ru
                </span>
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium mb-1.5">{{ t('crm.clientId') }}</label>
              <input
                v-model="settings.clientId"
                type="text"
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                class="input w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1.5">{{ t('crm.clientSecret') }}</label>
              <input
                v-model="settings.clientSecret"
                type="password"
                placeholder="..."
                class="input w-full"
              />
            </div>

            <div>
              <label class="block text-sm font-medium mb-1.5">{{ t('crm.redirectUri') }}</label>
              <input
                v-model="settings.redirectUri"
                type="text"
                readonly
                class="input w-full bg-secondary/50 cursor-not-allowed"
              />
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-4">
            <button
              :disabled="!settings.subdomain || !settings.clientId || !settings.clientSecret || isLoading"
              class="btn btn-primary"
              @click="connectAmoCRM"
            >
              <Link2 v-if="!isLoading" class="w-4 h-4 mr-2" />
              <RefreshCw v-else class="w-4 h-4 mr-2 animate-spin" />
              {{ t('crm.connect') }}
            </button>
          </div>
        </div>
      </template>

      <!-- Connected State -->
      <template v-else>
        <!-- Account Info -->
        <div v-if="accountInfo.name" class="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 mb-4">
          <div class="text-sm">
            <span class="text-muted-foreground">{{ t('crm.accountName') }}:</span>
            <span class="ml-2 font-medium">{{ accountInfo.name }}</span>
          </div>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-3 gap-4 mb-6">
          <div class="p-4 rounded-lg bg-secondary/50">
            <div class="text-2xl font-bold">{{ stats.contacts }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.contacts') }}</div>
          </div>
          <div class="p-4 rounded-lg bg-secondary/50">
            <div class="text-2xl font-bold">{{ stats.leads }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.leads') }}</div>
          </div>
          <div class="p-4 rounded-lg bg-secondary/50">
            <div class="text-sm text-muted-foreground">{{ t('crm.lastSync') }}</div>
            <div class="text-sm font-medium">{{ stats.lastSync ? formatDate(stats.lastSync) : t('crm.never') }}</div>
          </div>
        </div>

        <!-- Sync Settings -->
        <div class="space-y-4">
          <h3 class="font-medium flex items-center gap-2">
            <Settings2 class="w-4 h-4" />
            {{ t('crm.syncSettings') }}
          </h3>

          <div class="space-y-3">
            <label class="flex items-center gap-3">
              <input v-model="settings.syncContacts" type="checkbox" class="checkbox" />
              <span>{{ t('crm.syncContactsLabel') }}</span>
            </label>
            <label class="flex items-center gap-3">
              <input v-model="settings.syncLeads" type="checkbox" class="checkbox" />
              <span>{{ t('crm.syncLeadsLabel') }}</span>
            </label>
            <label class="flex items-center gap-3">
              <input v-model="settings.autoCreateLead" type="checkbox" class="checkbox" />
              <span>{{ t('crm.autoCreateLeadLabel') }}</span>
            </label>
          </div>

          <div class="flex justify-end pt-2">
            <button :disabled="isSaving" class="btn btn-secondary" @click="saveSettings">
              <Save v-if="!isSaving" class="w-4 h-4 mr-2" />
              <RefreshCw v-else class="w-4 h-4 mr-2 animate-spin" />
              {{ t('crm.saveSettings') }}
            </button>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-between pt-6 border-t border-border mt-6">
          <button class="btn btn-ghost text-red-400 hover:bg-red-500/10" @click="disconnectAmoCRM">
            <XIcon class="w-4 h-4 mr-2" />
            {{ t('crm.disconnect') }}
          </button>
          <div class="flex gap-2">
            <button :disabled="isSyncing" class="btn btn-secondary" @click="syncNow">
              <ArrowDownUp :class="['w-4 h-4 mr-2', isSyncing && 'animate-spin']" />
              {{ isSyncing ? t('crm.syncing') : t('crm.syncNow') }}
            </button>
            <button :disabled="isLoading" class="btn btn-secondary" @click="testConnection">
              <RefreshCw :class="['w-4 h-4 mr-2', isLoading && 'animate-spin']" />
              {{ t('crm.testConnection') }}
            </button>
            <a
              :href="`https://${settings.subdomain}.amocrm.ru`"
              target="_blank"
              class="btn btn-primary"
            >
              <ExternalLink class="w-4 h-4 mr-2" />
              {{ t('crm.openAmoCRM') }}
            </a>
          </div>
        </div>
      </template>
    </div>

    <!-- Sync Log -->
    <div class="card p-6">
      <button class="flex items-center gap-2 font-semibold w-full text-left" @click="loadSyncLog">
        <Clock class="w-5 h-5" />
        {{ t('crm.syncLog') }}
        <span class="text-muted-foreground text-sm ml-auto">{{ showSyncLog ? '▲' : '▼' }}</span>
      </button>

      <div v-if="showSyncLog" class="mt-4">
        <div v-if="syncLogs.length === 0" class="text-sm text-muted-foreground py-4 text-center">
          {{ t('crm.never') }}
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-border text-left">
                <th class="pb-2 pr-4">{{ t('crm.status') }}</th>
                <th class="pb-2 pr-4">Direction</th>
                <th class="pb-2 pr-4">Type</th>
                <th class="pb-2 pr-4">Action</th>
                <th class="pb-2">Date</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in syncLogs" :key="log.id" class="border-b border-border/50">
                <td class="py-2 pr-4">
                  <span
:class="[
                    'inline-block w-2 h-2 rounded-full',
                    log.status === 'success' ? 'bg-green-400' : 'bg-red-400'
                  ]" />
                </td>
                <td class="py-2 pr-4 text-muted-foreground">{{ log.direction }}</td>
                <td class="py-2 pr-4">{{ log.entity_type }}</td>
                <td class="py-2 pr-4">{{ log.action }}</td>
                <td class="py-2 text-muted-foreground">{{ formatDate(log.created) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Features -->
    <div class="card p-6">
      <h3 class="font-semibold mb-4">{{ t('crm.plannedFeatures') }}</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.oauth') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.oauthDesc') }}</div>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.contacts') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.contactsDesc') }}</div>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.leads') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.leadsDesc') }}</div>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.webhook') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.webhookDesc') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
