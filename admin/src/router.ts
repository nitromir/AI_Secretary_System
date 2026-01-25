import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'
import DashboardView from './views/DashboardView.vue'
import ChatView from './views/ChatView.vue'
import ServicesView from './views/ServicesView.vue'
import LlmView from './views/LlmView.vue'
import TtsView from './views/TtsView.vue'
import FaqView from './views/FaqView.vue'
import FinetuneView from './views/FinetuneView.vue'
import MonitoringView from './views/MonitoringView.vue'
import SettingsView from './views/SettingsView.vue'
import LoginView from './views/LoginView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { title: 'Login', public: true }
    },
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: 'Dashboard', icon: 'LayoutDashboard' }
    },
    {
      path: '/chat',
      name: 'chat',
      component: ChatView,
      meta: { title: 'Chat', icon: 'MessageCircle' }
    },
    {
      path: '/services',
      name: 'services',
      component: ServicesView,
      meta: { title: 'Services', icon: 'Server' }
    },
    {
      path: '/llm',
      name: 'llm',
      component: LlmView,
      meta: { title: 'LLM', icon: 'Brain' }
    },
    {
      path: '/tts',
      name: 'tts',
      component: TtsView,
      meta: { title: 'TTS', icon: 'Mic' }
    },
    {
      path: '/faq',
      name: 'faq',
      component: FaqView,
      meta: { title: 'FAQ', icon: 'MessageSquare' }
    },
    {
      path: '/finetune',
      name: 'finetune',
      component: FinetuneView,
      meta: { title: 'Fine-tune', icon: 'Sparkles' }
    },
    {
      path: '/monitoring',
      name: 'monitoring',
      component: MonitoringView,
      meta: { title: 'Monitoring', icon: 'Activity' }
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
      meta: { title: 'Settings', icon: 'Settings' }
    }
  ]
})

// Navigation guard for authentication
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // Check if route requires auth
  const isPublicRoute = to.meta.public === true

  if (!isPublicRoute && !authStore.isAuthenticated) {
    // Check if token is in localStorage but store not initialized
    const token = localStorage.getItem('admin_token')
    if (token && !authStore.isTokenExpired()) {
      // Token exists and valid, allow navigation
      next()
    } else {
      // Redirect to login
      next({ name: 'login', query: { redirect: to.fullPath } })
    }
  } else if (to.name === 'login' && authStore.isAuthenticated) {
    // Already logged in, redirect to dashboard
    next({ name: 'dashboard' })
  } else {
    next()
  }
})

export default router
