<template>
  <span class="signal-badge" :class="type">{{ label }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  type: 'buy' | 'sell' | 'hold'
}>()

const label = computed(() => {
  const map = { buy: '买', sell: '卖', hold: '持' }
  return map[props.type] || props.type
})
</script>

<style scoped>
.signal-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1.4;
}

.signal-badge.buy {
  background: rgba(239, 68, 68, 0.15);
  color: var(--rise);
}

.signal-badge.sell {
  background: rgba(34, 197, 94, 0.15);
  color: var(--fall);
}

.signal-badge.hold {
  background: var(--bg-elevated);
  color: var(--text-tertiary);
}
</style>
