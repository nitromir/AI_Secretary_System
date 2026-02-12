import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type UserRole = 'admin' | 'user' | 'web' | 'guest'

export interface User {
  id: number
  username: string
  role: UserRole
}

// Role permissions
export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin: ['*'], // All permissions
  user: [
    'chat.*',
    'llm.view', 'llm.cloud.*',
    'tts.view', 'tts.test',
    'faq.*',
    'telegram.*',
    'widget.*',
    'monitoring.view',
    'services.view',
    'audit.view',
    'settings.profile',
    'sales.*',
    'crm.view',
    'usage.view',
  ],
  web: [
    'chat.*',
    'llm.view', 'llm.cloud.*',
    'faq.*',
    'telegram.*',
    'widget.*',
    'monitoring.view',
    'audit.view',
    'settings.profile',
    'sales.*',
    'crm.view',
    'usage.view',
  ],
  guest: [
    'chat.demo',
    'dashboard.view',
    'faq.view',
  ]
}

// Check if we're in dev mode (Vite sets this)
const isDev = import.meta.env.DEV
const isDemo = import.meta.env.VITE_DEMO_MODE === 'true'

export type DeploymentMode = 'full' | 'cloud' | 'local'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  const user = ref<User | null>(null)
  const deploymentMode = ref<DeploymentMode>('full')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isUser = computed(() => user.value?.role === 'user' || user.value?.role === 'web' || isAdmin.value)
  const isWeb = computed(() => user.value?.role === 'web')
  const isGuest = computed(() => user.value?.role === 'guest')
  const isCloudMode = computed(() => deploymentMode.value === 'cloud')

  // Legacy compat aliases
  const isOperator = isUser
  const isViewer = computed(() => !!user.value)

  // Check if user has specific permission
  function hasPermission(permission: string): boolean {
    if (!user.value) return false
    const permissions = ROLE_PERMISSIONS[user.value.role]
    if (permissions.includes('*')) return true
    // Check exact match or wildcard match (e.g. 'chat.*' matches 'chat.view')
    return permissions.some(p => {
      if (p === permission) return true
      if (p.endsWith('.*')) {
        const prefix = p.slice(0, -2)
        return permission.startsWith(prefix + '.')
      }
      return false
    })
  }

  // Check if user can perform action on resource
  function can(action: string, resource: string): boolean {
    return hasPermission(`${resource}.${action}`)
  }

  // Fetch deployment mode from backend
  async function fetchDeploymentMode() {
    try {
      const response = await fetch('/admin/deployment-mode')
      if (response.ok) {
        const data = await response.json()
        deploymentMode.value = data.mode || 'full'
      }
    } catch {
      // Default to full if backend unreachable
    }
  }

  // Initialize from localStorage
  if (token.value) {
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      user.value = {
        id: payload.user_id || 0,
        username: payload.sub,
        role: payload.role
      }
      // Fetch deployment mode on init
      fetchDeploymentMode()
    } catch {
      token.value = null
      localStorage.removeItem('admin_token')
    }
  }

  // Create a mock JWT for dev mode when backend is unavailable
  function createDevToken(username: string): string {
    const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
    const payload = btoa(JSON.stringify({
      sub: username,
      user_id: 0,
      role: import.meta.env.VITE_DEMO_ROLE || 'admin',
      exp: Math.floor(Date.now() / 1000) + 86400, // 24 hours
      iat: Math.floor(Date.now() / 1000),
      dev: true
    }))
    const signature = btoa('dev-signature')
    return `${header}.${payload}.${signature}`
  }

  async function login(username: string, password: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch('/admin/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      if (!response.ok) {
        const data = await response.json()
        error.value = data.detail || 'Invalid credentials'
        return false
      }

      const data = await response.json()
      token.value = data.access_token
      localStorage.setItem('admin_token', data.access_token)

      // Decode JWT payload
      const payload = JSON.parse(atob(data.access_token.split('.')[1]))
      user.value = {
        id: payload.user_id || 0,
        username: payload.sub,
        role: payload.role
      }

      // Fetch deployment mode from backend
      await fetchDeploymentMode()

      return true
    } catch (e) {
      // In dev mode, allow login without backend
      if ((isDev || isDemo) && ((username === 'admin' && password === 'admin') || (username === 'demo' && password === 'demo'))) {
        console.warn('⚠️ Dev/Demo mode: Backend unavailable, using mock authentication')
        const devToken = createDevToken(username)
        token.value = devToken
        localStorage.setItem('admin_token', devToken)
        user.value = { id: 0, username, role: (import.meta.env.VITE_DEMO_ROLE || 'admin') as UserRole }
        error.value = null
        return true
      }

      error.value = 'Connection error - Backend not running'
      return false
    } finally {
      isLoading.value = false
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('admin_token')
  }

  function getAuthHeaders(): Record<string, string> {
    if (token.value) {
      return { 'Authorization': `Bearer ${token.value}` }
    }
    return {}
  }

  // Check if token is expired
  function isTokenExpired(): boolean {
    if (!token.value) return true
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      return payload.exp * 1000 < Date.now()
    } catch {
      return true
    }
  }

  return {
    token,
    user,
    deploymentMode,
    isLoading,
    error,
    isAuthenticated,
    isAdmin,
    isUser,
    isWeb,
    isGuest,
    isCloudMode,
    isOperator,
    isViewer,
    hasPermission,
    can,
    login,
    logout,
    getAuthHeaders,
    isTokenExpired
  }
})
