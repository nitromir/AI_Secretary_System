<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Filler
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler)

const props = defineProps<{
  data: number[]
  color?: string
  height?: number
  showArea?: boolean
}>()

const chartData = computed(() => ({
  labels: props.data.map((_, i) => i.toString()),
  datasets: [
    {
      data: props.data,
      borderColor: props.color || '#6366f1',
      backgroundColor: props.showArea ? `${props.color || '#6366f1'}20` : 'transparent',
      borderWidth: 2,
      fill: props.showArea,
      tension: 0.4,
      pointRadius: 0,
      pointHoverRadius: 0
    }
  ]
}))

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false }
  },
  scales: {
    x: { display: false },
    y: { display: false }
  },
  interaction: {
    intersect: false
  },
  elements: {
    line: {
      borderCapStyle: 'round' as const,
      borderJoinStyle: 'round' as const
    }
  }
}))
</script>

<template>
  <div :style="{ height: `${height || 40}px` }" class="w-full">
    <Line :data="chartData" :options="chartOptions" />
  </div>
</template>
