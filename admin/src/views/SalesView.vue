<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ShoppingCart,
  Target,
  Users,
  TrendingUp,
  MessageSquare,
  Gift,
  Settings2,
  BarChart3,
  Clock,
  Star
} from 'lucide-vue-next'

const { t } = useI18n()

// Placeholder data
const stats = ref({
  totalLeads: 0,
  convertedLeads: 0,
  conversionRate: 0,
  avgResponseTime: 0
})

const activeTab = ref<'funnel' | 'segments' | 'quiz' | 'testimonials'>('funnel')
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 rounded-lg bg-green-500/20">
          <ShoppingCart class="w-6 h-6 text-green-500" />
        </div>
        <div>
          <h1 class="text-2xl font-bold">{{ t('nav.sales') }}</h1>
          <p class="text-muted-foreground">Управление воронкой продаж и сегментацией</p>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="card p-4">
        <div class="flex items-center gap-3">
          <Target class="w-8 h-8 text-blue-400" />
          <div>
            <div class="text-2xl font-bold">{{ stats.totalLeads }}</div>
            <div class="text-sm text-muted-foreground">Лидов всего</div>
          </div>
        </div>
      </div>
      <div class="card p-4">
        <div class="flex items-center gap-3">
          <Users class="w-8 h-8 text-green-400" />
          <div>
            <div class="text-2xl font-bold">{{ stats.convertedLeads }}</div>
            <div class="text-sm text-muted-foreground">Конвертировано</div>
          </div>
        </div>
      </div>
      <div class="card p-4">
        <div class="flex items-center gap-3">
          <TrendingUp class="w-8 h-8 text-yellow-400" />
          <div>
            <div class="text-2xl font-bold">{{ stats.conversionRate }}%</div>
            <div class="text-sm text-muted-foreground">Конверсия</div>
          </div>
        </div>
      </div>
      <div class="card p-4">
        <div class="flex items-center gap-3">
          <Clock class="w-8 h-8 text-purple-400" />
          <div>
            <div class="text-2xl font-bold">{{ stats.avgResponseTime }}с</div>
            <div class="text-sm text-muted-foreground">Время ответа</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="card">
      <div class="border-b border-border">
        <div class="flex gap-1 p-1">
          <button
            v-for="tab in ['funnel', 'segments', 'quiz', 'testimonials'] as const"
            :key="tab"
            :class="[
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              activeTab === tab
                ? 'bg-secondary text-foreground'
                : 'text-muted-foreground hover:bg-secondary/50'
            ]"
            @click="activeTab = tab"
          >
            <BarChart3 v-if="tab === 'funnel'" class="w-4 h-4" />
            <Users v-if="tab === 'segments'" class="w-4 h-4" />
            <MessageSquare v-if="tab === 'quiz'" class="w-4 h-4" />
            <Star v-if="tab === 'testimonials'" class="w-4 h-4" />
            <span>
              {{ tab === 'funnel' ? 'Воронка' :
                 tab === 'segments' ? 'Сегменты' :
                 tab === 'quiz' ? 'Квиз' : 'Отзывы' }}
            </span>
          </button>
        </div>
      </div>

      <div class="p-6">
        <!-- Funnel Tab -->
        <div v-if="activeTab === 'funnel'" class="text-center py-12">
          <BarChart3 class="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
          <h3 class="text-lg font-medium mb-2">Воронка продаж</h3>
          <p class="text-muted-foreground max-w-md mx-auto">
            Визуализация этапов воронки и конверсии между ними.
            Настройте в разделе Telegram → Воронка для конкретного бота.
          </p>
        </div>

        <!-- Segments Tab -->
        <div v-if="activeTab === 'segments'" class="text-center py-12">
          <Users class="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
          <h3 class="text-lg font-medium mb-2">Сегменты аудитории</h3>
          <p class="text-muted-foreground max-w-md mx-auto">
            Автоматическая сегментация пользователей по ответам на квиз.
            Настройте в разделе Telegram → Воронка для конкретного бота.
          </p>
        </div>

        <!-- Quiz Tab -->
        <div v-if="activeTab === 'quiz'" class="text-center py-12">
          <MessageSquare class="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
          <h3 class="text-lg font-medium mb-2">Квиз-вопросы</h3>
          <p class="text-muted-foreground max-w-md mx-auto">
            Вопросы для квалификации лидов и определения их потребностей.
            Настройте в разделе Telegram → Воронка для конкретного бота.
          </p>
        </div>

        <!-- Testimonials Tab -->
        <div v-if="activeTab === 'testimonials'" class="text-center py-12">
          <Star class="w-16 h-16 mx-auto text-muted-foreground/50 mb-4" />
          <h3 class="text-lg font-medium mb-2">Отзывы клиентов</h3>
          <p class="text-muted-foreground max-w-md mx-auto">
            Social proof для приветственных сообщений бота.
            Настройте в разделе Telegram → Воронка для конкретного бота.
          </p>
        </div>
      </div>
    </div>

    <!-- Info Card -->
    <div class="card p-6">
      <div class="flex gap-4">
        <Settings2 class="w-6 h-6 text-muted-foreground shrink-0" />
        <div>
          <h3 class="font-semibold mb-2">Где настроить Sales Bot?</h3>
          <p class="text-muted-foreground text-sm">
            Настройки воронки продаж привязаны к конкретному Telegram боту.
            Перейдите в раздел <strong>Telegram</strong>, выберите бота и откройте вкладку <strong>Воронка</strong>
            для настройки квиза, сегментов, follow-up сообщений и отзывов.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
