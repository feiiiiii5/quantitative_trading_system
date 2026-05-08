<template>
  <div ref="chartRef" :style="{ width: '100%', height: height }" role="img" :aria-label="ariaLabel" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import echarts from '@/lib/echarts'

const props = withDefaults(defineProps<{
  option: Record<string, unknown>
  height?: string
  theme?: string
  ariaLabel?: string
}>(), {
  height: '300px',
  theme: 'quantcore',
  ariaLabel: 'Chart',
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null
let _updateTimer: ReturnType<typeof requestAnimationFrame> | null = null
let _lastOptionJson = ''

function initChart() {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value, props.theme)
  chart.setOption(props.option)
  _lastOptionJson = JSON.stringify(props.option)
  resizeObserver = new ResizeObserver(() => {
    if (_updateTimer) cancelAnimationFrame(_updateTimer)
    _updateTimer = requestAnimationFrame(() => {
      chart?.resize()
      _updateTimer = null
    })
  })
  resizeObserver.observe(chartRef.value)
}

watch(() => props.option, (newOpt) => {
  if (!chart) return
  const json = JSON.stringify(newOpt)
  if (json === _lastOptionJson) return
  _lastOptionJson = json
  if (_updateTimer) cancelAnimationFrame(_updateTimer)
  _updateTimer = requestAnimationFrame(() => {
    chart?.setOption(newOpt, { notMerge: false })
    _updateTimer = null
  })
}, { deep: false })

onMounted(() => {
  nextTick(initChart)
})

onUnmounted(() => {
  if (_updateTimer) {
    cancelAnimationFrame(_updateTimer)
    _updateTimer = null
  }
  if (resizeObserver && chartRef.value) {
    resizeObserver.unobserve(chartRef.value)
    resizeObserver.disconnect()
  }
  chart?.dispose()
  chart = null
  resizeObserver = null
})
</script>
