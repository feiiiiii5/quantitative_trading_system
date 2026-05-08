<template>
  <div class="screener-page">
    <div class="screener-body">
      <div class="preset-col">
        <div class="surface-panel">
          <div class="panel-header"><span class="panel-title">SCREENER STRATEGIES</span></div>
          <div class="preset-list">
            <div
              v-for="p in presets"
              :key="p.id"
              class="preset-card"
              :class="{ active: selectedPreset === p.id }"
              @click="selectPreset(p.id)"
            >
              <div class="pc-name">{{ p.name }}</div>
              <div class="pc-desc">{{ p.description }}</div>
              <div class="pc-tags">
                <span class="cat-badge" :class="categoryClass(p.category)">{{ categoryLabel(p.category) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="result-col">
        <div class="surface-panel">
          <div class="panel-header">
            <span class="panel-title">SCREENER RESULTS</span>
            <div class="result-actions">
              <span v-if="results" class="result-count mono">{{ results.total }} STOCKS</span>
              <button class="term-btn" @click="runScreener" :disabled="!selectedPreset || running">
                {{ running ? 'RUNNING...' : 'RUN SCREENER' }}
              </button>
            </div>
          </div>
          <div v-if="running" class="panel-empty">SCREENING<span class="blink-cursor">_</span></div>
          <DataTable
            v-else-if="results && results.stocks.length"
            :columns="resultColumns"
            :rows="results.stocks as unknown as Record<string, unknown>[]"
            row-key="symbol"
            @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
          >
            <template #cell-symbol="{ value }">
              <span class="code-text">{{ value }}</span>
            </template>
            <template #cell-name="{ value }">
              <span class="name-text">{{ value }}</span>
            </template>
            <template #cell-price="{ value }">
              <span class="mono">{{ ((value as number) ?? 0).toFixed(2) }}</span>
            </template>
            <template #cell-change_pct="{ value }">
              <span class="mono" :class="((value as number) ?? 0) >= 0 ? 'val-rise' : 'val-fall'">
                {{ formatPct((value as number) ?? 0) }}
              </span>
            </template>
            <template #cell-amount="{ value }">
              <span class="mono">{{ formatAmount((value as number) ?? 0) }}</span>
            </template>
            <template #cell-turnover_rate="{ value }">
              <span class="mono">{{ ((value as number) ?? 0).toFixed(2) }}%</span>
            </template>
            <template #cell-pe="{ value }">
              <span class="mono">{{ value ? (value as number).toFixed(1) : '—' }}</span>
            </template>
          </DataTable>
          <div v-else-if="results && !results.stocks.length" class="panel-empty">NO MATCHING STOCKS</div>
          <div v-else class="panel-empty">SELECT A STRATEGY AND RUN</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { formatPct, formatAmount } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { ScreenerPreset, ScreenerResult } from '@/types'

const router = useRouter()
const presets = ref<ScreenerPreset[]>([])
const selectedPreset = ref('')
const results = ref<ScreenerResult | null>(null)
const running = ref(false)
const { cancelAll } = useRequestCancel()

function categoryLabel(cat: string): string {
  const map: Record<string, string> = {
    technical: 'TECHNICAL',
    fundamental: 'FUNDAMENTAL',
    market_activity: 'ACTIVITY',
  }
  return map[cat] || cat.toUpperCase()
}

function categoryClass(cat: string): string {
  const map: Record<string, string> = {
    technical: 'cat-tech',
    fundamental: 'cat-fund',
    market_activity: 'cat-activity',
  }
  return map[cat] || 'cat-tech'
}

const resultColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '100px' },
  { key: 'price', label: 'PRICE', align: 'right', width: '80px' },
  { key: 'change_pct', label: 'CHG%', align: 'right', width: '70px' },
  { key: 'amount', label: 'AMT', align: 'right', width: '90px' },
  { key: 'turnover_rate', label: 'T/O', align: 'right', width: '60px' },
  { key: 'pe', label: 'PE', align: 'right', width: '60px' },
]

function selectPreset(id: string) {
  selectedPreset.value = selectedPreset.value === id ? '' : id
}

async function fetchPresets() {
  try {
    presets.value = await api.screener.presets()
  } catch {
    presets.value = []
  }
}

async function runScreener() {
  if (!selectedPreset.value) return
  running.value = true
  try {
    results.value = await api.screener.run(selectedPreset.value)
  } catch {
    results.value = null
  } finally {
    running.value = false
  }
}

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

onMounted(fetchPresets)

onUnmounted(cancelAll)
</script>

<style scoped>
.screener-page {
  max-width: 1440px;
  margin: 0 auto;
  height: 100%;
}

.screener-body {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: var(--u4);
  min-height: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.preset-list { display: grid; gap: 1px; background: var(--border-hair); }

.preset-card {
  padding: var(--u3) var(--u4);
  background: var(--bg-surface);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
  border-left: 2px solid transparent;
}

.preset-card:hover { background: var(--bg-overlay); }

.preset-card.active {
  background: var(--accent-muted);
  border-left-color: var(--accent);
}

.pc-name {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--u1);
}

.pc-desc {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  line-height: 1.4;
  margin-bottom: var(--u2);
}

.pc-tags { display: flex; gap: var(--u1); }

.cat-badge {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.cat-tech { background: var(--accent-muted); color: var(--accent); }
.cat-fund { background: var(--fall-bg); color: var(--fall); }
.cat-activity { background: var(--warn-bg); color: var(--warn); }

.result-col { min-width: 0; }

.result-actions {
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.result-count {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.term-btn {
  padding: 3px 12px;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--r-md);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-weight: 600;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.term-btn:hover { opacity: 0.85; }
.term-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.panel-empty {
  padding: var(--u8) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.blink-cursor { animation: blink 1s step-end infinite; }

.code-text {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: var(--fs-xs);
}

.name-text { color: var(--text-primary); }

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

@media (max-width: 900px) {
  .screener-body { grid-template-columns: 1fr; }
}
</style>
