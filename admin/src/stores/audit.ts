import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

export interface AuditEntry {
  id: number
  timestamp: Date
  user: string
  action: 'create' | 'update' | 'delete' | 'start' | 'stop' | 'login' | 'logout' | 'export' | 'import'
  resource: string
  resourceId?: string
  details?: string
  oldValue?: any
  newValue?: any
}

let auditId = Date.now()

export const useAuditStore = defineStore('audit', () => {
  const entries = ref<AuditEntry[]>([])
  const maxEntries = 500

  // Load from localStorage
  const stored = localStorage.getItem('admin_audit_log')
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      entries.value = parsed.map((e: any) => ({
        ...e,
        timestamp: new Date(e.timestamp)
      }))
    } catch {
      entries.value = []
    }
  }

  const recentEntries = computed(() => entries.value.slice(0, 50))

  function log(
    action: AuditEntry['action'],
    resource: string,
    details?: string,
    options?: {
      resourceId?: string
      oldValue?: any
      newValue?: any
    }
  ) {
    const authStore = useAuthStore()
    const entry: AuditEntry = {
      id: ++auditId,
      timestamp: new Date(),
      user: authStore.user?.username || 'anonymous',
      action,
      resource,
      resourceId: options?.resourceId,
      details,
      oldValue: options?.oldValue,
      newValue: options?.newValue
    }

    entries.value.unshift(entry)

    // Keep only maxEntries
    if (entries.value.length > maxEntries) {
      entries.value = entries.value.slice(0, maxEntries)
    }

    // Persist to localStorage
    save()
  }

  function save() {
    localStorage.setItem('admin_audit_log', JSON.stringify(entries.value))
  }

  function clear() {
    entries.value = []
    localStorage.removeItem('admin_audit_log')
  }

  function getByResource(resource: string) {
    return entries.value.filter(e => e.resource === resource)
  }

  function getByUser(user: string) {
    return entries.value.filter(e => e.user === user)
  }

  function getByAction(action: AuditEntry['action']) {
    return entries.value.filter(e => e.action === action)
  }

  function exportLog(): string {
    return JSON.stringify(entries.value, null, 2)
  }

  // Convenience methods
  function logCreate(resource: string, resourceId: string, details?: string) {
    log('create', resource, details, { resourceId })
  }

  function logUpdate(resource: string, resourceId: string, oldValue: any, newValue: any, details?: string) {
    log('update', resource, details, { resourceId, oldValue, newValue })
  }

  function logDelete(resource: string, resourceId: string, details?: string) {
    log('delete', resource, details, { resourceId })
  }

  function logServiceStart(serviceName: string) {
    log('start', 'service', `Started ${serviceName}`, { resourceId: serviceName })
  }

  function logServiceStop(serviceName: string) {
    log('stop', 'service', `Stopped ${serviceName}`, { resourceId: serviceName })
  }

  return {
    entries,
    recentEntries,
    log,
    clear,
    getByResource,
    getByUser,
    getByAction,
    exportLog,
    logCreate,
    logUpdate,
    logDelete,
    logServiceStart,
    logServiceStop
  }
})
