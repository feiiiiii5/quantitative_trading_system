<template>
  <span class="signal-badge" :class="type">
    <span class="sb-line" />
    <span class="sb-text">{{ type.toUpperCase() }}</span>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  type: 'buy' | 'sell' | 'hold'
}>()
</script>

<style scoped>
.signal-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border-radius: 0;
  border: none;
  background: none;
}

.sb-line {
  display: block;
  width: 2px;
  height: 10px;
  background: var(--text-tertiary);
}

.sb-text {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-tertiary);
}

.buy .sb-line { background: var(--rise); }
.buy .sb-text { color: var(--rise); }

.sell .sb-line { background: var(--fall); }
.sell .sb-text { color: var(--fall); }

.hold .sb-line { background: var(--text-tertiary); }
.hold .sb-text { color: var(--text-tertiary); }
</style>
