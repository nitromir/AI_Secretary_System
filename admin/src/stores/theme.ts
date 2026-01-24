import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type Theme = 'light' | 'dark' | 'system'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>((localStorage.getItem('admin_theme') as Theme) || 'system')
  const resolvedTheme = ref<'light' | 'dark'>('dark')

  // System preference media query
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)')

  function getResolvedTheme(): 'light' | 'dark' {
    if (theme.value === 'system') {
      return systemPrefersDark.matches ? 'dark' : 'light'
    }
    return theme.value
  }

  function applyTheme() {
    resolvedTheme.value = getResolvedTheme()
    const root = document.documentElement

    if (resolvedTheme.value === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.add('light')
      root.classList.remove('dark')
    }
  }

  function setTheme(newTheme: Theme) {
    theme.value = newTheme
    localStorage.setItem('admin_theme', newTheme)
    applyTheme()
  }

  function toggleTheme() {
    const themes: Theme[] = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme.value)
    const nextIndex = (currentIndex + 1) % themes.length
    setTheme(themes[nextIndex])
  }

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
    setTheme,
    toggleTheme
  }
})
