<template>
  <svg
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    class="mini-sparkline"
  >
    <polyline
      :points="points"
      fill="none"
      :stroke="resolvedColor"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <circle
      :cx="lastX"
      :cy="lastY"
      r="1.5"
      :fill="resolvedColor"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  width?: number
  height?: number
  color?: string
}>(), {
  width: 60,
  height: 20,
})

const resolvedColor = computed(() => {
  if (props.color) return props.color
  if (props.data.length < 2) return 'var(--text-muted)'
  return props.data[props.data.length - 1] >= props.data[0] ? 'var(--rise)' : 'var(--fall)'
})

const points = computed(() => {
  const { data, width, height } = props
  if (data.length < 2) return ''
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const padY = 2
  const usableH = height - padY * 2
  const stepX = width / (data.length - 1)

  return data.map((v, i) => {
    const x = i * stepX
    const y = padY + usableH - ((v - min) / range) * usableH
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

const lastX = computed(() => {
  if (props.data.length < 2) return 0
  return ((props.data.length - 1) * props.width) / (props.data.length - 1)
})

const lastY = computed(() => {
  if (props.data.length < 2) return props.height / 2
  const min = Math.min(...props.data)
  const max = Math.max(...props.data)
  const range = max - min || 1
  const padY = 2
  const usableH = props.height - padY * 2
  const lastVal = props.data[props.data.length - 1]
  return padY + usableH - ((lastVal - min) / range) * usableH
})
</script>

<style scoped>
.mini-sparkline {
  display: block;
  overflow: visible;
}
</style>
