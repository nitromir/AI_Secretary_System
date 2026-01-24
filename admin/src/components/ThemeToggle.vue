<script setup lang="ts">
import { useThemeStore, type Theme } from '@/stores/theme'
import { useI18n } from 'vue-i18n'
import { ref, onMounted, onUnmounted } from 'vue'

const { t } = useI18n()
const themeStore = useThemeStore()
const menuOpen = ref(false)

const icons: Record<Theme, string> = {
  light: 'M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z',
  dark: 'M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z',
  'night-eyes': 'M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
  system: 'M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25'
}

function handleClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.theme-menu')) {
    menuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

function selectTheme(theme: Theme) {
  themeStore.setTheme(theme)
  menuOpen.value = false
}
</script>

<template>
  <div class="relative theme-menu">
    <button
      type="button"
      class="flex items-center gap-2 rounded-lg bg-secondary px-2 md:px-3 py-2 text-sm text-muted-foreground hover:bg-secondary/80 hover:text-foreground transition-colors"
      @click.stop="menuOpen = !menuOpen"
      :title="t(`themes.${themeStore.theme}`)"
    >
      <svg
        class="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke-width="1.5"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          :d="icons[themeStore.theme]"
        />
      </svg>
      <span class="hidden md:inline">{{ t(`themes.${themeStore.theme}`) }}</span>
    </button>

    <!-- Theme Menu -->
    <div
      v-if="menuOpen"
      class="absolute right-0 top-full mt-2 w-40 rounded-lg bg-popover border border-border shadow-lg py-1 z-50"
    >
      <button
        v-for="theme in themeStore.themes"
        :key="theme.value"
        class="flex items-center gap-3 w-full px-3 py-2 text-sm text-left hover:bg-secondary/50 transition-colors"
        :class="{ 'bg-secondary text-foreground': themeStore.theme === theme.value }"
        @click="selectTheme(theme.value)"
      >
        <svg
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            :d="icons[theme.value]"
          />
        </svg>
        {{ t(`themes.${theme.value}`) }}
      </button>
    </div>
  </div>
</template>
