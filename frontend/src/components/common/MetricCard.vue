<template>
  <div class="metric-card">
    <div class="mc-label">{{ label }}</div>
    <div class="mc-value mono" :class="valueClass">{{ formatted }}</div>
    <div v-if="sub" class="mc-sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: number | string
  sub?: string
  direction?: 'rise' | 'fall' | 'neutral'
  suffix?: string
}>(), { direction: 'neutral' })

const valueClass = computed(() => {
  if (props.direction === 'rise') return 'text-rise'
  if (props.direction === 'fall') return 'text-fall'
  return ''
})

const formatted = computed(() => {
  if (typeof props.value === 'string') return props.value
  const v = props.value
  if (props.suffix) return v.toFixed(2) + props.suffix
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(2)
})
</script>

<style scoped>
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.mc-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.mc-value {
  font-size: var(--text-lg);
  font-weight: 600;
}

.mc-sub {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}
</style>
