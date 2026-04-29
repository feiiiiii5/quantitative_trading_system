<template>
  <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" class="sparkline">
    <polyline :points="points" fill="none" :stroke="color" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  data: number[]
  color?: string
  height?: number
  width?: number
}>(), { height: 30, width: 80 })

const points = computed(() => {
  if (!props.data || props.data.length < 2) return ''
  const min = Math.min(...props.data)
  const max = Math.max(...props.data)
  const range = max - min || 1
  const step = props.width / (props.data.length - 1)
  return props.data.map((v, i) => {
    const x = i * step
    const y = props.height - ((v - min) / range) * (props.height - 4) - 2
    return `${x},${y}`
  }).join(' ')
})

const color = computed(() => {
  if (props.color) return props.color
  if (props.data.length < 2) return 'var(--text-tertiary)'
  const first = props.data[0]
  const last = props.data[props.data.length - 1]
  return last >= first ? 'var(--accent-red)' : 'var(--accent-green)'
})
</script>
