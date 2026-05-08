<template>
  <div class="data-panel">
    <div v-if="title || $slots['header-actions']" class="dp-header">
      <span class="dp-accent" :style="accentStyle" />
      <span v-if="title" class="dp-title">{{ title }}</span>
      <slot name="header-actions" />
    </div>
    <div class="dp-body">
      <template v-if="loading">
        <Skeleton width="80%" height="14px" />
        <Skeleton width="60%" height="14px" />
        <Skeleton width="40%" height="14px" />
      </template>
      <slot v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const props = withDefaults(defineProps<{
  title?: string
  accent?: string
  loading?: boolean
}>(), {
  loading: false,
})

const accentStyle = computed(() => ({
  background: props.accent || 'var(--accent)',
}))
</script>

<style scoped>
.data-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-hair);
  border-radius: var(--r-md);
  position: relative;
  overflow: hidden;
}

.data-panel::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
}

.dp-header {
  display: flex;
  align-items: center;
  gap: var(--u3);
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
  position: relative;
}

.dp-accent {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 20px;
  background: var(--accent);
  border-radius: 0 1px 1px 0;
}

.dp-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.dp-body {
  padding: var(--u4);
}
</style>
