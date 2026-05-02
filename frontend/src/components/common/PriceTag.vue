<template>
  <span class="price-tag" :class="direction">
    <span class="price-value mono">{{ formatted }}</span>
    <span v-if="showChange && change !== undefined" class="price-change mono">
      {{ change >= 0 ? '+' : '' }}{{ change.toFixed(2) }}%
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  value: number
  change?: number
  showChange?: boolean
}>(), { showChange: false })

const direction = computed(() => {
  if (props.change === undefined) return ''
  return props.change >= 0 ? 'rise' : 'fall'
})

const formatted = computed(() => {
  if (props.value === undefined || props.value === null) return '-'
  return props.value.toFixed(2)
})
</script>

<style scoped>
.price-tag {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.price-value {
  font-weight: 500;
}

.price-change {
  font-size: var(--text-xs);
}

.rise .price-value,
.rise .price-change {
  color: var(--rise);
}

.fall .price-value,
.fall .price-change {
  color: var(--fall);
}
</style>
