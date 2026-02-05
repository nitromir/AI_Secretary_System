<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Users,
  Building2,
  Link2,
  Settings2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Check,
  X as XIcon
} from 'lucide-vue-next'

const { t } = useI18n()

// amoCRM integration state
const isConnected = ref(false)
const isLoading = ref(false)

// Settings form
const settings = ref({
  subdomain: '',
  clientId: '',
  clientSecret: '',
  redirectUri: window.location.origin + '/admin/#/crm/callback',
  syncContacts: true,
  syncLeads: true,
  syncTasks: false,
  autoCreateLead: true,
  leadPipelineId: '',
  leadStatusId: ''
})

// Placeholder for future implementation
const stats = ref({
  contacts: 0,
  leads: 0,
  lastSync: null as string | null
})

async function connectAmoCRM() {
  // TODO: Implement OAuth flow
  isLoading.value = true
  setTimeout(() => {
    isLoading.value = false
  }, 1000)
}

async function disconnectAmoCRM() {
  isConnected.value = false
}

async function testConnection() {
  isLoading.value = true
  setTimeout(() => {
    isLoading.value = false
  }, 1000)
}
</script>

<template>
  <div class="space-y-6">
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
            <div class="text-sm font-medium">{{ stats.lastSync || t('crm.never') }}</div>
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
        </div>

        <!-- Actions -->
        <div class="flex justify-between pt-6 border-t border-border mt-6">
          <button class="btn btn-ghost text-red-400 hover:bg-red-500/10" @click="disconnectAmoCRM">
            <XIcon class="w-4 h-4 mr-2" />
            {{ t('crm.disconnect') }}
          </button>
          <div class="flex gap-2">
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

    <!-- Features Coming Soon -->
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
          <Check class="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.contacts') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.contactsDesc') }}</div>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.leads') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.leadsDesc') }}</div>
          </div>
        </div>
        <div class="flex items-start gap-3 p-3 rounded-lg bg-secondary/30">
          <Check class="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
          <div>
            <div class="font-medium">{{ t('crm.feature.webhook') }}</div>
            <div class="text-sm text-muted-foreground">{{ t('crm.feature.webhookDesc') }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
