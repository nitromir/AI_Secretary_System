import { createRouter, createWebHashHistory } from 'vue-router'
import DashboardView from './views/DashboardView.vue'
import ServicesView from './views/ServicesView.vue'
import LlmView from './views/LlmView.vue'
import TtsView from './views/TtsView.vue'
import FaqView from './views/FaqView.vue'
import FinetuneView from './views/FinetuneView.vue'
import MonitoringView from './views/MonitoringView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: 'Dashboard', icon: 'LayoutDashboard' }
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
    }
  ]
})

export default router
