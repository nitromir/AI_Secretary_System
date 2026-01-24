import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '@/api/client'

interface User {
  username: string
  role: 'admin' | 'viewer'
}

interface AuthState {
  token: string | null
  user: User | null
  isAuthenticated: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('admin_token'))
  const user = ref<User | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

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
      error.value = 'Connection error'
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
    login,
    logout,
    getAuthHeaders,
    isTokenExpired
  }
})
