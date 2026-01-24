<script setup lang="ts">
import { computed } from 'vue'
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
  data: number[]
  label: string
  color: string
  unit?: string
}>()

const chartData = computed(() => ({
  labels: props.data.map((_, i) => ''),
  datasets: [
    {
      label: props.label,
      data: props.data,
      borderColor: props.color,
      backgroundColor: `${props.color}20`,
      fill: true,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2
    }
  ]
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#1f2937',
      titleColor: '#fff',
      bodyColor: '#9ca3af',
      borderColor: '#374151',
      borderWidth: 1,
      padding: 10,
      callbacks: {
        label: (ctx: any) => `${ctx.parsed.y}${props.unit || ''}`
      }
    }
  },
  scales: {
    x: { display: false },
    y: {
      display: false,
      beginAtZero: true
    }
  },
  interaction: {
    intersect: false,
    mode: 'index' as const
  }
}))
</script>

<template>
  <div class="h-16 w-full">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
