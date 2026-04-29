<template>
  <span class="signal-badge" :class="[signalClass, { pulse: isStrong }]">
    <span class="badge-dot"></span>
    {{ label }}
    <span v-if="score" class="badge-score">{{ score.toFixed(2) }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  signal: 'strong_buy' | 'buy' | 'neutral' | 'sell' | 'strong_sell'
  score?: number
}>()

const signalClass = computed(() => props.signal.replace('_', '-'))

const isStrong = computed(() => props.signal === 'strong_buy' || props.signal === 'strong_sell')

const label = computed(() => {
  const map: Record<string, string> = {
    strong_buy: '强烈买入',
    buy: '买入',
    neutral: '中性',
    sell: '卖出',
    strong_sell: '强烈卖出',
  }
  return map[props.signal] || props.signal
})
</script>

<style scoped>
.signal-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;
}
.badge-dot { width: 6px; height: 6px; border-radius: 50%; }
.badge-score { font-family: var(--font-mono); font-size: 11px; opacity: 0.8; }

.strong-buy { background: rgba(244,63,94,0.2); color: var(--accent-red); }
.strong-buy .badge-dot { background: var(--accent-red); }
.buy { background: rgba(244,63,94,0.1); color: var(--accent-red); }
.buy .badge-dot { background: var(--accent-red); }
.neutral { background: rgba(255,255,255,0.06); color: var(--text-secondary); }
.neutral .badge-dot { background: var(--text-tertiary); }
.sell { background: rgba(52,211,153,0.1); color: var(--accent-green); }
.sell .badge-dot { background: var(--accent-green); }
.strong-sell { background: rgba(52,211,153,0.2); color: var(--accent-green); }
.strong-sell .badge-dot { background: var(--accent-green); }

.pulse { animation: badgePulse 2s infinite; }
@keyframes badgePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(244,63,94,0); }
  50% { box-shadow: 0 0 8px rgba(244,63,94,0.3); }
}
.strong-sell.pulse {
  animation: badgePulseGreen 2s infinite;
}
@keyframes badgePulseGreen {
  0%, 100% { box-shadow: 0 0 0 0 rgba(52,211,153,0); }
  50% { box-shadow: 0 0 8px rgba(52,211,153,0.3); }
}
</style>
