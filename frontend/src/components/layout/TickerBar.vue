<template>
  <div class="ticker-bar" v-if="indices.length">
    <div class="ticker-grid">
      <div
        v-for="(item, i) in indices"
        :key="'idx-' + i"
        class="ticker-cell"
      >
        <span class="ticker-name">{{ item.name }}</span>
        <span class="ticker-price" :class="item.change_pct >= 0 ? 'rise' : 'fall'">
          {{ formatPrice(item.price) }}
        </span>
        <span class="ticker-pct" :class="item.change_pct >= 0 ? 'rise' : 'fall'">
          {{ item.change_pct >= 0 ? '▲' : '▼' }}{{ item.change_pct >= 0 ? '+' : '' }}{{ safeToFixed(item.change_pct, 2) }}%
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { safeToFixed } from '@/utils/format'
import { useMarketStore } from '@/stores/market'

const marketStore = useMarketStore()

export interface IndexItem {
  name: string
  price: number
  change: number
  change_pct: number
}

const props = withDefaults(defineProps<{
  indices?: IndexItem[]
}>(), {
  indices: () => [],
})

const internalIndices = computed<IndexItem[]>(() => {
  const overview = marketStore.overview
  if (!overview) return []
  const all: IndexItem[] = []
  for (const [, d] of Object.entries(overview.cn_indices).slice(0, 3)) {
    all.push({ name: d.name, price: d.price, change: d.change, change_pct: d.change_pct })
  }
  for (const [, d] of Object.entries(overview.hk_indices).slice(0, 1)) {
    all.push({ name: d.name, price: d.price, change: d.change, change_pct: d.change_pct })
  }
  for (const [, d] of Object.entries(overview.us_indices).slice(0, 2)) {
    all.push({ name: d.name, price: d.price, change: d.change, change_pct: d.change_pct })
  }
  return all.slice(0, 6)
})

const indices = computed(() =>
  props.indices.length > 0 ? props.indices : internalIndices.value
)

function formatPrice(p: number): string {
  if (p == null || isNaN(p)) return '-'
  return safeToFixed(p, 2)
}
</script>

<style scoped>
.ticker-bar {
  width: 100%;
  height: var(--ticker-height);
  background: var(--bg-void);
  border-bottom: 1px solid var(--border-hair);
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
  z-index: 80;
  box-shadow: inset 0 1px 0 rgba(41, 121, 255, 0.08);
}

.ticker-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  height: var(--ticker-height);
}

.ticker-cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: var(--u1) var(--u3);
  gap: 0;
  position: relative;
}

.ticker-cell:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 20%;
  height: 60%;
  width: 1px;
  background: var(--border-hair);
}

.ticker-name {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-tertiary);
  font-variant: all-small-caps;
  letter-spacing: 0.08em;
  line-height: 1.3;
}

.ticker-price {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.ticker-price.rise {
  color: var(--rise);
}

.ticker-price.fall {
  color: var(--fall);
}

.ticker-pct {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-variant-numeric: tabular-nums;
  letter-spacing: 0;
  line-height: 1.3;
}

.ticker-pct.rise {
  color: var(--rise);
}

.ticker-pct.fall {
  color: var(--fall);
}

@media (max-width: 768px) {
  .ticker-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
