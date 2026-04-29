<template>
  <span class="price-tag" :class="[size, direction]">
    <span class="price-value">{{ formattedPrice }}</span>
    <span v-if="changePct !== undefined" class="price-change" :class="changePct >= 0 ? 'up' : 'down'">
      {{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}%
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  price: number
  change?: number
  changePct?: number
  size?: 'sm' | 'md' | 'lg'
}>(), { size: 'md' })

const direction = computed(() => {
  if (props.changePct === undefined) return ''
  return props.changePct >= 0 ? 'up' : 'down'
})

const formattedPrice = computed(() => {
  if (typeof props.price !== 'number') return props.price
  return props.price.toFixed(2)
})
</script>

<style scoped>
.price-tag { display: inline-flex; align-items: baseline; gap: 6px; }
.price-value { font-family: var(--font-mono); font-weight: 600; }
.price-change { font-family: var(--font-mono); font-size: 0.8em; }
.sm .price-value { font-size: 12px; }
.md .price-value { font-size: 14px; }
.lg .price-value { font-size: 20px; }
.up .price-value { color: var(--accent-red); }
.down .price-value { color: var(--accent-green); }
.price-change.up { color: var(--accent-red); }
.price-change.down { color: var(--accent-green); }
</style>
