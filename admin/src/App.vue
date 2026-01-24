<script setup lang="ts">
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  Server,
  Brain,
  Mic,
  MessageSquare,
  Sparkles,
  Activity,
  Settings,
  Menu,
  X,
  Search,
  LogOut,
  User
} from 'lucide-vue-next'
import { ref, computed, watch } from 'vue'
import { useAuthStore } from './stores/auth'
import { useSearchStore } from './stores/search'
import { useThemeStore } from './stores/theme'
import ToastContainer from './components/ToastContainer.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import SearchPalette from './components/SearchPalette.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const searchStore = useSearchStore()
const themeStore = useThemeStore()

const sidebarOpen = ref(true)

const navItems = [
  { path: '/', name: 'Dashboard', icon: LayoutDashboard },
  { path: '/services', name: 'Services', icon: Server },
  { path: '/llm', name: 'LLM', icon: Brain },
  { path: '/tts', name: 'TTS', icon: Mic },
  { path: '/faq', name: 'FAQ', icon: MessageSquare },
  { path: '/finetune', name: 'Fine-tune', icon: Sparkles },
  { path: '/monitoring', name: 'Monitoring', icon: Activity },
]

const currentTitle = computed(() => {
  const item = navItems.find(i => i.path === route.path)
  return item?.name || 'Admin'
})

const isLoginPage = computed(() => route.name === 'login')

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <ErrorBoundary>
    <!-- Login Page (no sidebar) -->
    <template v-if="isLoginPage">
      <RouterView />
    </template>

    <!-- Main App Layout -->
    <template v-else>
      <div class="flex h-screen overflow-hidden bg-background">
        <!-- Sidebar -->
        <aside
          :class="[
            'flex flex-col bg-card border-r border-border transition-all duration-300',
            sidebarOpen ? 'w-64' : 'w-16'
          ]"
        >
          <!-- Logo -->
          <div class="flex items-center h-16 px-4 border-b border-border">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                <Settings class="w-5 h-5 text-primary" />
              </div>
              <span v-if="sidebarOpen" class="font-semibold text-lg">AI Secretary</span>
            </div>
          </div>

          <!-- Search button -->
          <div v-if="sidebarOpen" class="p-2">
            <button
              @click="searchStore.open"
              class="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
            >
              <Search class="w-4 h-4" />
              <span class="flex-1 text-left">Search...</span>
              <kbd class="text-xs bg-background px-1.5 py-0.5 rounded">⌘K</kbd>
            </button>
          </div>
          <div v-else class="p-2">
            <button
              @click="searchStore.open"
              class="flex items-center justify-center w-full p-2 text-muted-foreground rounded-lg hover:bg-secondary/50 transition-colors"
            >
              <Search class="w-5 h-5" />
            </button>
          </div>

          <!-- Navigation -->
          <nav class="flex-1 p-2 space-y-1 overflow-y-auto">
            <RouterLink
              v-for="item in navItems"
              :key="item.path"
              :to="item.path"
              :class="[
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                route.path === item.path
                  ? 'bg-secondary text-foreground'
                  : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground'
              ]"
            >
              <component :is="item.icon" class="w-5 h-5 shrink-0" />
              <span v-if="sidebarOpen" class="truncate">{{ item.name }}</span>
            </RouterLink>
          </nav>

          <!-- User & Toggle -->
          <div class="p-2 border-t border-border space-y-1">
            <!-- User info -->
            <div
              v-if="sidebarOpen && authStore.user"
              class="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground"
            >
              <User class="w-4 h-4" />
              <span class="truncate">{{ authStore.user.username }}</span>
            </div>

            <!-- Logout -->
            <button
              @click="handleLogout"
              :class="[
                'flex items-center w-full px-3 py-2 rounded-lg text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-colors',
                sidebarOpen ? 'gap-3' : 'justify-center'
              ]"
            >
              <LogOut class="w-5 h-5" />
              <span v-if="sidebarOpen">Logout</span>
            </button>

            <!-- Toggle Button -->
            <button
              @click="sidebarOpen = !sidebarOpen"
              class="flex items-center justify-center w-full p-2 rounded-lg text-muted-foreground hover:bg-secondary/50 hover:text-foreground transition-colors"
            >
              <Menu v-if="!sidebarOpen" class="w-5 h-5" />
              <X v-else class="w-5 h-5" />
            </button>
          </div>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 flex flex-col overflow-hidden">
          <!-- Header -->
          <header class="flex items-center justify-between h-16 px-6 border-b border-border bg-card">
            <h1 class="text-xl font-semibold">{{ currentTitle }}</h1>
            <div class="flex items-center gap-4">
              <!-- Theme Toggle -->
              <ThemeToggle />

              <!-- Search shortcut hint -->
              <button
                @click="searchStore.open"
                class="hidden sm:flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Search class="w-4 h-4" />
                <span>Search</span>
                <kbd class="text-xs bg-secondary px-1.5 py-0.5 rounded">⌘K</kbd>
              </button>
            </div>
          </header>

          <!-- Content -->
          <div class="flex-1 overflow-auto p-6">
            <RouterView />
          </div>
        </main>
      </div>
    </template>

    <!-- Global Components -->
    <ToastContainer />
    <ConfirmDialog />
    <SearchPalette />
  </ErrorBoundary>
</template>

<style>
/* Light theme support */
.light {
  --background: 255 255 255;
  --foreground: 9 9 11;
  --card: 250 250 250;
  --card-foreground: 9 9 11;
  --popover: 255 255 255;
  --popover-foreground: 9 9 11;
  --primary: 99 102 241;
  --primary-foreground: 255 255 255;
  --secondary: 244 244 245;
  --secondary-foreground: 9 9 11;
  --muted: 244 244 245;
  --muted-foreground: 113 113 122;
  --accent: 244 244 245;
  --accent-foreground: 9 9 11;
  --destructive: 239 68 68;
  --destructive-foreground: 255 255 255;
  --border: 228 228 231;
  --input: 228 228 231;
  --ring: 99 102 241;
}

.light .bg-zinc-900 { background-color: rgb(250 250 250); }
.light .bg-zinc-800 { background-color: rgb(244 244 245); }
.light .bg-zinc-950 { background-color: rgb(255 255 255); }
.light .text-white { color: rgb(9 9 11); }
.light .text-gray-300 { color: rgb(63 63 70); }
.light .text-gray-400 { color: rgb(113 113 122); }
.light .text-gray-500 { color: rgb(161 161 170); }
.light .ring-zinc-700 { --tw-ring-color: rgb(228 228 231); }
.light .ring-zinc-800 { --tw-ring-color: rgb(228 228 231); }
.light .border-zinc-700 { border-color: rgb(228 228 231); }
.light .border-zinc-800 { border-color: rgb(228 228 231); }
</style>
