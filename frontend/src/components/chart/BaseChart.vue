<template>
  <div ref="el" :style="{ height, width: '100%' }" class="chart-wrap" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import echarts from '@/lib/echarts'

const props = withDefaults(defineProps<{
  option: Record<string, unknown>
  height?: string
}>(), {
  height: '300px',
})

const el = ref<HTMLElement>()
let chart: ReturnType<typeof echarts.init> | null = null
let ro: ResizeObserver | null = null

function init() {
  if (!el.value) return
  chart = echarts.init(el.value)
  chart.setOption(props.option)
  ro = new ResizeObserver(() => chart?.resize())
  ro.observe(el.value)
}

watch(() => props.option, (opt) => {
  if (chart && opt) chart.setOption(opt, { notMerge: false })
}, { deep: true })

onMounted(init)

onUnmounted(() => {
  ro?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.chart-wrap {
  min-height: 200px;
}
</style>
