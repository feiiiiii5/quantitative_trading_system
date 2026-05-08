<template>
  <div class="watchlist-page">
    <div class="surface-panel">
      <div class="panel-header">
        <span class="panel-title">WATCHLIST</span>
        <div class="add-bar">
          <input
            v-model="addSymbol"
            placeholder="CODE"
            class="term-input"
            @keyup.enter="addStock"
          />
          <button class="term-btn" @click="addStock" :disabled="!addSymbol.trim()">ADD</button>
        </div>
      </div>
      <DataTable
        v-if="quotes.length"
        :columns="watchlistColumns"
        :rows="quotes as unknown as Record<string, unknown>[]"
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
          <span class="mono">{{ formatPrice(value as number) }}</span>
        </template>
        <template #cell-change="{ value }">
          <span class="mono" :class="(value as number) >= 0 ? 'val-rise' : 'val-fall'">
            {{ (value as number) >= 0 ? '+' : '' }}{{ ((value as number) ?? 0).toFixed(2) }}
          </span>
        </template>
        <template #cell-change_pct="{ value }">
          <span class="mono" :class="(value as number) >= 0 ? 'val-rise' : 'val-fall'">
            {{ formatPct(value as number) }}
          </span>
        </template>
        <template #cell-volume="{ value }">
          <span class="mono">{{ formatVolume(value as number) }}</span>
        </template>
        <template #cell-amount="{ value }">
          <span class="mono">{{ formatAmount(value as number) }}</span>
        </template>
        <template #cell-turnover_rate="{ value }">
          <span class="mono">{{ ((value as number) ?? 0).toFixed(2) }}%</span>
        </template>
        <template #actions="{ row }">
          <button class="del-btn" @click.stop="removeStock(row.symbol as string)">DEL</button>
        </template>
      </DataTable>
      <div v-else class="panel-empty">NO WATCHLIST — ADD STOCKS ABOVE</div>
    </div>

    <div class="surface-panel">
      <div class="panel-header">
        <span class="panel-title">PRICE ALERTS</span>
        <span class="alert-count mono" v-if="alerts.length">{{ alerts.length }} ACTIVE</span>
      </div>
      <div v-if="alerts.length" class="alert-list">
        <div v-for="a in alerts" :key="String(a.id)" class="alert-row">
          <div class="alert-left">
            <span class="code-text">{{ a.symbol }}</span>
            <span class="alert-type">{{ a.alert_type }}</span>
            <span class="alert-value mono">{{ a.value }}</span>
          </div>
          <div class="alert-right">
            <span class="alert-status" :class="a.triggered ? 'status-fired' : 'status-watch'">
              {{ a.triggered ? 'FIRED' : 'WATCH' }}
            </span>
            <button class="del-btn" @click="removeAlert(String(a.id))">DEL</button>
          </div>
        </div>
      </div>
      <div v-else class="panel-empty">NO ALERTS</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { useWatchlistStore } from '@/stores/watchlist'
import { formatPrice, formatPct, formatVolume, formatAmount } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { StockQuote, PriceAlert } from '@/types'

const log = createLogger('Watchlist')
const { cancelAll } = useRequestCancel()
const { handleApiError } = useApiError()

const router = useRouter()
const watchlistStore = useWatchlistStore()

const addSymbol = ref('')
const alerts = ref<PriceAlert[]>([])

const quotes = computed<StockQuote[]>(() => {
  return Object.values(watchlistStore.quotes) as StockQuote[]
})

const watchlistColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '100px' },
  { key: 'price', label: 'PRICE', align: 'right', width: '80px' },
  { key: 'change', label: 'CHG', align: 'right', width: '70px' },
  { key: 'change_pct', label: 'CHG%', align: 'right', width: '70px' },
  { key: 'volume', label: 'VOL', align: 'right', width: '80px' },
  { key: 'amount', label: 'AMT', align: 'right', width: '90px' },
  { key: 'turnover_rate', label: 'T/O', align: 'right', width: '60px' },
]

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

async function addStock() {
  const s = addSymbol.value.trim()
  if (!s) return
  await watchlistStore.addSymbol(s)
  addSymbol.value = ''
}

async function removeStock(symbol: string) {
  await watchlistStore.removeSymbol(symbol)
}

async function removeAlert(alertId: string) {
  try {
    const { api } = await import('@/api')
    await api.watchlist.removeAlert(alertId)
    alerts.value = alerts.value.filter(a => String(a.id) !== alertId)
  } catch (err) {
    handleApiError(err, '删除提醒失败')
  }
}

onMounted(async () => {
  await watchlistStore.fetchWatchlist()
  try {
    alerts.value = await watchlistStore.fetchAlerts()
  } catch (err) {
    handleApiError(err, '获取提醒失败')
  }
})

onUnmounted(cancelAll)
</script>

<style scoped>
.watchlist-page {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
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

.add-bar {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.term-input {
  width: 100px;
  padding: 3px 8px;
  background: var(--bg-plate);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.term-input:focus { border-color: var(--accent); }

.term-btn {
  padding: 3px 10px;
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

.code-text {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: var(--fs-xs);
}

.name-text { color: var(--text-primary); }

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

.del-btn {
  font-size: var(--fs-3xs);
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--r-md);
  border: 1px solid var(--border-dim);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.del-btn:hover { border-color: var(--rise); color: var(--rise); }

.alert-list { display: grid; }

.alert-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u2) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.alert-row:last-child { border-bottom: none; }

.alert-left {
  display: flex;
  align-items: center;
  gap: var(--u3);
}

.alert-type {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.alert-value {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.alert-right {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.alert-status {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.status-fired { background: var(--rise-bg); color: var(--rise); }
.status-watch { background: var(--accent-muted); color: var(--accent); }

.alert-count {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

@media (max-width: 768px) {
  .term-input { width: 80px; }
}
</style>
