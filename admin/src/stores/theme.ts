import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type Theme = 'light' | 'dark' | 'system' | 'night-eyes'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>((localStorage.getItem('admin_theme') as Theme) || 'system')
  const resolvedTheme = ref<'light' | 'dark' | 'night-eyes'>('dark')

  // System preference media query
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)')

  // Available themes for UI
  const themes: { value: Theme; label: string; icon: string }[] = [
    { value: 'light', label: 'Light', icon: 'sun' },
    { value: 'dark', label: 'Dark', icon: 'moon' },
    { value: 'night-eyes', label: 'Night Eyes', icon: 'eye' },
    { value: 'system', label: 'System', icon: 'monitor' }
  ]

  function getResolvedTheme(): 'light' | 'dark' | 'night-eyes' {
    if (theme.value === 'system') {
      return systemPrefersDark.matches ? 'dark' : 'light'
    }
    if (theme.value === 'night-eyes') {
      return 'night-eyes'
    }
    return theme.value as 'light' | 'dark'
  }

  function applyTheme() {
    resolvedTheme.value = getResolvedTheme()
    const root = document.documentElement

    // Remove all theme classes
    root.classList.remove('dark', 'light', 'night-eyes')

    // Apply resolved theme
    root.classList.add(resolvedTheme.value)
  }

  function setTheme(newTheme: Theme) {
    theme.value = newTheme
    localStorage.setItem('admin_theme', newTheme)
    applyTheme()
  }

  function toggleTheme() {
    const themeValues: Theme[] = ['light', 'dark', 'night-eyes', 'system']
    const currentIndex = themeValues.indexOf(theme.value)
    const nextIndex = (currentIndex + 1) % themeValues.length
    setTheme(themeValues[nextIndex])
  }

  const isNightEyes = computed(() => resolvedTheme.value === 'night-eyes')

  // Watch for system preference changes
  systemPrefersDark.addEventListener('change', () => {
    if (theme.value === 'system') {
      applyTheme()
    }
  })

  // Apply theme on init
  applyTheme()

  return {
    theme,
    resolvedTheme,
    themes,
    isNightEyes,
    setTheme,
    toggleTheme
  }
})
