<template>
  <div class="metric-block" :class="directionClass">
    <div class="mb-stripe" :style="stripeStyle" />
    <template v-if="loading">
      <Skeleton width="60%" height="24px" class="mb-skel-value" />
      <Skeleton width="80%" height="12px" />
    </template>
    <template v-else>
      <div class="mb-value">{{ value }}</div>
      <div class="mb-label">{{ label }}</div>
      <div v-if="change != null || changePct != null" class="mb-change">
        <span v-if="change != null" class="mb-change-val">{{ change }}</span>
        <span v-if="changePct != null" class="mb-change-pct">{{ changePct }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Skeleton from '@/components/ui/Skeleton.vue'

const props = withDefaults(defineProps<{
  value: string | number
  label: string
  change?: string | number
  changePct?: string | number
  direction?: 'rise' | 'fall' | 'neutral'
  loading?: boolean
}>(), {
  loading: false,
})

const directionClass = computed(() => {
  if (props.direction) return `dir-${props.direction}`
  const v = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  if (v > 0) return 'dir-rise'
  if (v < 0) return 'dir-fall'
  return 'dir-neutral'
})

const stripeStyle = computed(() => {
  const dir = directionClass.value
  if (dir === 'dir-rise') return { background: 'var(--rise)' }
  if (dir === 'dir-fall') return { background: 'var(--fall)' }
  return { background: 'var(--warn)' }
})
</script>

<style scoped>
.metric-block {
  background: var(--bg-plate);
  border: none;
  border-radius: var(--r-md);
  padding: var(--u4);
  display: flex;
  flex-direction: column;
  gap: var(--u1);
  position: relative;
  overflow: hidden;
  padding-left: calc(var(--u4) + 8px);
}

.mb-stripe {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 8px;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.mb-skel-value {
  margin-top: var(--u2);
}

.mb-value {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  line-height: var(--lh-tight);
}

.dir-rise .mb-value { color: var(--rise); }
.dir-fall .mb-value { color: var(--fall); }

.mb-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.mb-change {
  display: flex;
  align-items: baseline;
  gap: var(--u2);
  margin-top: var(--u1);
}

.mb-change-val,
.mb-change-pct {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.dir-rise .mb-change-val,
.dir-rise .mb-change-pct { color: var(--rise); }
.dir-fall .mb-change-val,
.dir-fall .mb-change-pct { color: var(--fall); }
.dir-neutral .mb-change-val,
.dir-neutral .mb-change-pct { color: var(--text-tertiary); }
</style>
