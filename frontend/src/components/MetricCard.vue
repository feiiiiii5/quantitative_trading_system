<template>
  <div class="metric-card" :class="{ loading }">
    <div v-if="loading" class="skeleton" style="height:60px;border-radius:8px"></div>
    <template v-else>
      <div class="metric-label">
        {{ label }}
        <span v-if="tooltip" class="tooltip-icon" :title="tooltip">?</span>
      </div>
      <div class="metric-value" :class="valueClass">
        {{ formattedValue }}
        <span v-if="unit" class="metric-unit">{{ unit }}</span>
      </div>
      <div v-if="change !== undefined" class="metric-change" :class="changeClass">
        {{ change >= 0 ? '+' : '' }}{{ change.toFixed(2) }}%
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  label: string
  value: number | string
  unit?: string
  change?: number
  positive?: 'up' | 'down' | 'neutral'
  tooltip?: string
  loading?: boolean
  format?: 'number' | 'percent' | 'currency' | 'raw'
}>(), { positive: 'up', format: 'raw' })

const formattedValue = computed(() => {
  if (typeof props.value !== 'number') return props.value
  switch (props.format) {
    case 'number': return props.value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    case 'percent': return `${props.value.toFixed(2)}%`
    case 'currency': return `¥${props.value.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
    default: return String(props.value)
  }
})

const valueClass = computed(() => {
  if (typeof props.value !== 'number' || props.positive === 'neutral') return ''
  if (props.positive === 'up') return props.value >= 0 ? 'text-up' : 'text-down'
  return props.value >= 0 ? 'text-down' : 'text-up'
})

const changeClass = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? 'text-up' : 'text-down'
})
</script>

<style scoped>
.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 16px;
  transition: all var(--transition);
}
.metric-card:hover { border-color: rgba(255,255,255,0.1); }
.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.tooltip-icon {
  width: 14px; height: 14px; border-radius: 50%;
  background: rgba(255,255,255,0.06); display: inline-flex;
  align-items: center; justify-content: center;
  font-size: 9px; color: var(--text-tertiary); cursor: help;
}
.metric-value {
  font-size: 22px; font-family: var(--font-mono); font-weight: 700;
  color: var(--text-primary); line-height: 1.2;
}
.metric-unit { font-size: 13px; font-weight: 400; color: var(--text-secondary); margin-left: 2px; }
.metric-change { font-size: 12px; font-family: var(--font-mono); margin-top: 4px; }
.text-up { color: var(--accent-red) !important; }
.text-down { color: var(--accent-green) !important; }
</style>
