<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
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
  X
} from 'lucide-vue-next'
import { ref, computed } from 'vue'

const route = useRoute()
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
</script>

<template>
  <div class="flex h-screen overflow-hidden">
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

      <!-- Toggle Button -->
      <div class="p-2 border-t border-border">
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
          <span class="text-sm text-muted-foreground">AI Secretary Admin Panel</span>
        </div>
      </header>

      <!-- Content -->
      <div class="flex-1 overflow-auto p-6">
        <RouterView />
      </div>
    </main>
  </div>
</template>
