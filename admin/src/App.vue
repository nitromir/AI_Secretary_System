<script setup lang="ts">
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import {
  LayoutDashboard,
  MessageCircle,
  Server,
  Brain,
  Mic,
  MessageSquare,
  Sparkles,
  Activity,
  HardDrive,
  Code2,
  Send,
  Settings,
  Menu,
  X,
  Search,
  LogOut,
  User,
  Languages
} from 'lucide-vue-next'
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from './stores/auth'
import { useSearchStore } from './stores/search'
import { useThemeStore } from './stores/theme'
import { setLocale, getLocale } from './plugins/i18n'
import ToastContainer from './components/ToastContainer.vue'
import ConfirmDialog from './components/ConfirmDialog.vue'
import SearchPalette from './components/SearchPalette.vue'
import ThemeToggle from './components/ThemeToggle.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const searchStore = useSearchStore()
const themeStore = useThemeStore()

const sidebarOpen = ref(true)
const mobileMenuOpen = ref(false)
const isMobile = ref(false)

// Check if mobile
function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    sidebarOpen.value = false
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

// Close mobile menu on route change
watch(() => route.path, () => {
  mobileMenuOpen.value = false
})

const navItems = [
  { path: '/', nameKey: 'nav.dashboard', icon: LayoutDashboard },
  { path: '/chat', nameKey: 'nav.chat', icon: MessageCircle },
  { path: '/services', nameKey: 'nav.services', icon: Server },
  { path: '/llm', nameKey: 'nav.llm', icon: Brain },
  { path: '/tts', nameKey: 'nav.tts', icon: Mic },
  { path: '/faq', nameKey: 'nav.faq', icon: MessageSquare },
  { path: '/finetune', nameKey: 'nav.finetune', icon: Sparkles },
  { path: '/monitoring', nameKey: 'nav.monitoring', icon: Activity },
  { path: '/models', nameKey: 'nav.models', icon: HardDrive },
  { path: '/widget', nameKey: 'nav.widget', icon: Code2 },
  { path: '/telegram', nameKey: 'nav.telegram', icon: Send },
  { path: '/settings', nameKey: 'common.settings', icon: Settings },
]

const currentTitle = computed(() => {
  const item = navItems.find(i => i.path === route.path)
  return item ? t(item.nameKey) : 'Admin'
})

const isLoginPage = computed(() => route.name === 'login')

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function toggleLocale() {
  const newLocale = getLocale() === 'ru' ? 'en' : 'ru'
  setLocale(newLocale)
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
        <!-- Mobile Overlay -->
        <div
          v-if="mobileMenuOpen && isMobile"
          class="fixed inset-0 bg-black/50 z-40 md:hidden"
          @click="mobileMenuOpen = false"
        />

        <!-- Sidebar -->
        <aside
          :class="[
            'flex flex-col bg-card border-r border-border transition-all duration-300 z-50',
            isMobile ? 'fixed inset-y-0 left-0' : '',
            isMobile && !mobileMenuOpen ? '-translate-x-full' : 'translate-x-0',
            sidebarOpen || isMobile ? 'w-64' : 'w-16'
          ]"
        >
          <!-- Logo -->
          <div class="flex items-center justify-between h-16 px-4 border-b border-border">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                <Settings class="w-5 h-5 text-primary" />
              </div>
              <span v-if="sidebarOpen || isMobile" class="font-semibold text-lg">AI Secretary</span>
            </div>
            <button
              v-if="isMobile"
              @click="mobileMenuOpen = false"
              class="p-1 rounded-lg hover:bg-secondary/50 text-muted-foreground"
            >
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Search button -->
          <div v-if="sidebarOpen || isMobile" class="p-2">
            <button
              @click="searchStore.open"
              class="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground rounded-lg bg-secondary/50 hover:bg-secondary transition-colors"
            >
              <Search class="w-4 h-4" />
              <span class="flex-1 text-left">{{ t('nav.search') }}</span>
              <kbd class="text-xs bg-background px-1.5 py-0.5 rounded hidden sm:inline">⌘K</kbd>
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
              <span v-if="sidebarOpen || isMobile" class="truncate">{{ t(item.nameKey) }}</span>
            </RouterLink>
          </nav>

          <!-- User & Toggle -->
          <div class="p-2 border-t border-border space-y-1">
            <!-- User info -->
            <div
              v-if="(sidebarOpen || isMobile) && authStore.user"
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
                sidebarOpen || isMobile ? 'gap-3' : 'justify-center'
              ]"
            >
              <LogOut class="w-5 h-5" />
              <span v-if="sidebarOpen || isMobile">{{ t('nav.logout') }}</span>
            </button>

            <!-- Toggle Button (desktop only) -->
            <button
              v-if="!isMobile"
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
          <header class="flex items-center justify-between h-16 px-4 md:px-6 border-b border-border bg-card">
            <div class="flex items-center gap-3">
              <!-- Mobile Menu Button -->
              <button
                v-if="isMobile"
                @click="mobileMenuOpen = true"
                class="p-2 -ml-2 rounded-lg hover:bg-secondary/50 text-muted-foreground"
              >
                <Menu class="w-5 h-5" />
              </button>
              <h1 class="text-lg md:text-xl font-semibold truncate">{{ currentTitle }}</h1>
            </div>
            <div class="flex items-center gap-2 md:gap-4">
              <!-- Language Toggle -->
              <button
                @click="toggleLocale"
                class="p-2 rounded-lg hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-colors"
                :title="getLocale() === 'ru' ? 'Switch to English' : 'Переключить на русский'"
              >
                <Languages class="w-5 h-5" />
              </button>

              <!-- Theme Toggle -->
              <ThemeToggle />

              <!-- Search shortcut hint (desktop only) -->
              <button
                @click="searchStore.open"
                class="hidden lg:flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Search class="w-4 h-4" />
                <span>{{ t('nav.search') }}</span>
                <kbd class="text-xs bg-secondary px-1.5 py-0.5 rounded">⌘K</kbd>
              </button>
            </div>
          </header>

          <!-- Content -->
          <div class="flex-1 overflow-auto p-4 md:p-6">
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
/* Page transition animations */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Fade transition for modals */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Slide transition for sidebar */
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}

/* Scale transition for cards */
.scale-enter-active,
.scale-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* Smooth hover effects */
.hover-lift {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hover-lift:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* Focus visible styles */
*:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: 2px;
}

/* Responsive text sizing */
@media (max-width: 640px) {
  .text-responsive-sm { font-size: 0.75rem; }
  .text-responsive-base { font-size: 0.875rem; }
  .text-responsive-lg { font-size: 1rem; }
  .text-responsive-xl { font-size: 1.125rem; }
}
</style>
