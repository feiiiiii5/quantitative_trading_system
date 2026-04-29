<template>
  <div ref="chartRef" :style="{ height: height, width: '100%' }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import echarts from '../lib/echarts'

const props = withDefaults(defineProps<{
  option: Record<string, any>
  height?: string
  loading?: boolean
}>(), { height: '300px', loading: false })

const chartRef = ref<HTMLElement>()
let chart: any = null
let resizeObserver: ResizeObserver | null = null

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  chart.setOption(props.option)
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartRef.value)
}

watch(() => props.option, (newOption) => {
  if (chart && newOption) {
    chart.setOption(newOption, { notMerge: false })
  }
}, { deep: true })

onMounted(() => initChart())

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.dispose()
  chart = null
})
</script>
