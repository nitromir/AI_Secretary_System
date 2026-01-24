<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const props = defineProps<{
  memoryHistory: number[]
  utilizationHistory: number[]
  labels?: string[]
}>()

const chartData = computed(() => ({
  labels: props.labels || props.memoryHistory.map((_, i) => ''),
  datasets: [
    {
      label: 'Memory %',
      data: props.memoryHistory,
      borderColor: '#a855f7',
      backgroundColor: 'rgba(168, 85, 247, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4
    },
    {
      label: 'Utilization %',
      data: props.utilizationHistory,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4
    }
  ]
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'top' as const,
      labels: {
        color: '#9ca3af',
        boxWidth: 12,
        padding: 15,
        font: { size: 11 }
      }
    },
    tooltip: {
      backgroundColor: '#1f2937',
      titleColor: '#fff',
      bodyColor: '#9ca3af',
      borderColor: '#374151',
      borderWidth: 1,
      padding: 10,
      displayColors: true,
      callbacks: {
        label: (ctx: any) => `${ctx.dataset.label}: ${ctx.parsed.y}%`
      }
    }
  },
  scales: {
    x: {
      display: false
    },
    y: {
      min: 0,
      max: 100,
      grid: {
        color: 'rgba(75, 85, 99, 0.3)'
      },
      ticks: {
        color: '#6b7280',
        font: { size: 10 },
        callback: (value: any) => `${value}%`
      }
    }
  },
  interaction: {
    intersect: false,
    mode: 'index' as const
  }
}
</script>

<template>
  <div class="h-48 w-full">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
