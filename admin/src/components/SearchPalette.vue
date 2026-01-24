<script setup lang="ts">
import { useSearchStore, type SearchResult } from '@/stores/search'
import { useRouter } from 'vue-router'
import { watch, ref, onMounted, onUnmounted } from 'vue'

const searchStore = useSearchStore()
const router = useRouter()
const inputRef = ref<HTMLInputElement | null>(null)

// Focus input when palette opens
watch(() => searchStore.isOpen, (isOpen) => {
  if (isOpen) {
    setTimeout(() => inputRef.value?.focus(), 50)
  }
})

// Global keyboard shortcut
function handleGlobalKeydown(e: KeyboardEvent) {
  // Cmd/Ctrl + K to open
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    searchStore.open()
  }
  // Escape to close
  if (e.key === 'Escape' && searchStore.isOpen) {
    searchStore.close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown)
})

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    searchStore.selectNext()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    searchStore.selectPrev()
  } else if (e.key === 'Enter') {
    e.preventDefault()
    selectResult(searchStore.getSelected())
  }
}

function selectResult(result: SearchResult | null) {
  if (!result) return

  if (result.action) {
    result.action()
  } else if (result.route) {
    router.push(result.route)
  }

  searchStore.close()
}

function onInput(e: Event) {
  const value = (e.target as HTMLInputElement).value
  searchStore.search(value)
}

const iconPaths: Record<string, string> = {
  'user': 'M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z',
  'server': 'M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03l-2.268-9.64a3.375 3.375 0 00-3.285-2.602H7.923a3.375 3.375 0 00-3.285 2.602l-2.268 9.64a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z',
  'volume-2': 'M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z',
  'cpu': 'M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z',
  'mic': 'M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z',
  'sliders': 'M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75',
  'message-circle': 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z',
  'layout-dashboard': 'M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z',
  'brain': 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z',
  'activity': 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
  'graduation-cap': 'M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5'
}

function getIconPath(icon: string): string {
  return iconPaths[icon] || iconPaths['server']
}

const typeLabels: Record<string, string> = {
  faq: 'FAQ',
  log: 'Log',
  preset: 'Preset',
  persona: 'Persona',
  service: 'Service',
  adapter: 'Adapter'
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="searchStore.isOpen"
        class="fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-20"
      >
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-black/70 transition-opacity"
          @click="searchStore.close"
        />

        <!-- Search panel -->
        <Transition
          enter-active-class="ease-out duration-200"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="ease-in duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="searchStore.isOpen"
            class="mx-auto max-w-xl transform divide-y divide-zinc-700 overflow-hidden rounded-xl bg-zinc-900 shadow-2xl ring-1 ring-zinc-700 transition-all"
          >
            <!-- Search input -->
            <div class="relative">
              <svg
                class="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-gray-400"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fill-rule="evenodd"
                  d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
                  clip-rule="evenodd"
                />
              </svg>
              <input
                ref="inputRef"
                type="text"
                class="h-12 w-full border-0 bg-transparent pl-11 pr-4 text-white placeholder:text-gray-400 focus:ring-0 sm:text-sm"
                placeholder="Search services, FAQ, presets..."
                :value="searchStore.query"
                @input="onInput"
                @keydown="handleKeydown"
              />
              <div class="absolute right-4 top-3.5 text-xs text-gray-500">
                <kbd class="rounded bg-zinc-800 px-1.5 py-0.5 text-gray-400">⌘K</kbd>
              </div>
            </div>

            <!-- Results -->
            <ul
              v-if="searchStore.results.length > 0"
              class="max-h-80 scroll-py-2 overflow-y-auto py-2"
            >
              <li
                v-for="(result, index) in searchStore.results"
                :key="result.id"
                :class="[
                  'cursor-pointer select-none px-4 py-2',
                  index === searchStore.selectedIndex
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-300'
                ]"
                @click="selectResult(result)"
                @mouseenter="searchStore.selectedIndex = index"
              >
                <div class="flex items-center">
                  <svg
                    :class="[
                      'h-5 w-5 flex-shrink-0',
                      index === searchStore.selectedIndex ? 'text-white' : 'text-gray-400'
                    ]"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      :d="getIconPath(result.icon)"
                    />
                  </svg>
                  <div class="ml-3 flex-auto">
                    <p class="text-sm font-medium">{{ result.title }}</p>
                    <p
                      v-if="result.subtitle"
                      :class="[
                        'text-xs',
                        index === searchStore.selectedIndex ? 'text-indigo-200' : 'text-gray-500'
                      ]"
                    >
                      {{ result.subtitle }}
                    </p>
                  </div>
                  <span
                    :class="[
                      'ml-3 flex-none text-xs',
                      index === searchStore.selectedIndex ? 'text-indigo-200' : 'text-gray-500'
                    ]"
                  >
                    {{ typeLabels[result.type] || result.type }}
                  </span>
                </div>
              </li>
            </ul>

            <!-- Empty state -->
            <div
              v-else-if="searchStore.query && !searchStore.isSearching"
              class="px-6 py-14 text-center sm:px-14"
            >
              <svg
                class="mx-auto h-6 w-6 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z"
                />
              </svg>
              <p class="mt-4 text-sm text-gray-400">
                No results found for "{{ searchStore.query }}"
              </p>
            </div>

            <!-- Loading -->
            <div
              v-else-if="searchStore.isSearching"
              class="px-6 py-14 text-center"
            >
              <svg
                class="mx-auto h-6 w-6 animate-spin text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <p class="mt-4 text-sm text-gray-400">Searching...</p>
            </div>

            <!-- Hint -->
            <div
              v-else
              class="px-6 py-14 text-center sm:px-14"
            >
              <svg
                class="mx-auto h-6 w-6 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke-width="1.5"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
                />
              </svg>
              <p class="mt-4 text-sm text-gray-400">
                Search for services, FAQ entries, presets, and more...
              </p>
            </div>

            <!-- Footer -->
            <div class="flex flex-wrap items-center bg-zinc-800/50 px-4 py-2.5 text-xs text-gray-400">
              <span class="mr-4">
                <kbd class="rounded bg-zinc-700 px-1.5 py-0.5">↑↓</kbd> navigate
              </span>
              <span class="mr-4">
                <kbd class="rounded bg-zinc-700 px-1.5 py-0.5">↵</kbd> select
              </span>
              <span>
                <kbd class="rounded bg-zinc-700 px-1.5 py-0.5">esc</kbd> close
              </span>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
