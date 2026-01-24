import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type UserRole = 'admin' | 'operator' | 'viewer'

export interface User {
  username: string
  role: UserRole
}

// Role permissions
export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  admin: ['*'], // All permissions
  operator: [
    'services.view', 'services.start', 'services.stop', 'services.restart',
    'llm.view', 'llm.edit',
    'tts.view', 'tts.edit', 'tts.test',
    'faq.view', 'faq.edit',
    'monitoring.view',
    'logs.view'
  ],
  viewer: [
    'services.view',
    'llm.view',
    'tts.view',
    'faq.view',
    'monitoring.view',
    'logs.view'
  ]
}

// Check if we're in dev mode (Vite sets this)
const isDev = import.meta.env.DEV

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isOperator = computed(() => user.value?.role === 'operator' || isAdmin.value)
  const isViewer = computed(() => !!user.value)

  // Check if user has specific permission
  function hasPermission(permission: string): boolean {
    if (!user.value) return false
    const permissions = ROLE_PERMISSIONS[user.value.role]
    return permissions.includes('*') || permissions.includes(permission)
  }

  // Check if user can perform action on resource
  function can(action: string, resource: string): boolean {
    return hasPermission(`${resource}.${action}`)
  }

  // Initialize from localStorage
  if (token.value) {
    try {
      const payload = JSON.parse(atob(token.value.split('.')[1]))
      user.value = { username: payload.sub, role: payload.role }
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
      role: 'admin',
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
      user.value = { username: payload.sub, role: payload.role }

      return true
    } catch (e) {
      // In dev mode, allow login without backend
      if (isDev && username === 'admin' && password === 'admin') {
        console.warn('⚠️ Dev mode: Backend unavailable, using mock authentication')
        const devToken = createDevToken(username)
        token.value = devToken
        localStorage.setItem('admin_token', devToken)
        user.value = { username, role: 'admin' }
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
    isLoading,
    error,
    isAuthenticated,
    isAdmin,
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
