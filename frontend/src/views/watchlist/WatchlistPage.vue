<template>
  <div class="watchlist-page">
    <div class="page-header">
      <h1 class="page-title">自选股</h1>
      <div class="add-stock">
        <input v-model="addSymbol" placeholder="输入股票代码添加" class="add-input mono" @keyup.enter="addStock" />
        <button class="add-btn" @click="addStock">添加</button>
      </div>
    </div>

    <div class="watchlist-content" v-if="quotes.length">
      <table class="wl-table">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>最新价</th>
            <th>涨跌</th>
            <th>涨跌幅</th>
            <th>成交量</th>
            <th>成交额</th>
            <th>换手率</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="q in quotes" :key="q.symbol" class="wl-row" @click="goToStock(q.symbol)">
            <td class="mono code">{{ q.symbol }}</td>
            <td class="name">{{ q.name }}</td>
            <td class="mono">{{ formatPrice(q.price) }}</td>
            <td class="mono" :class="q.change >= 0 ? 'text-rise' : 'text-fall'">
              {{ q.change >= 0 ? '+' : '' }}{{ q.change.toFixed(2) }}
            </td>
            <td class="mono" :class="q.change_pct >= 0 ? 'text-rise' : 'text-fall'">
              {{ q.change_pct >= 0 ? '+' : '' }}{{ q.change_pct.toFixed(2) }}%
            </td>
            <td class="mono">{{ formatVolume(q.volume) }}</td>
            <td class="mono">{{ formatAmount(q.amount) }}</td>
            <td class="mono">{{ q.turnover_rate?.toFixed(2) }}%</td>
            <td>
              <button class="remove-btn" @click.stop="removeStock(q.symbol)">移除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="empty-state">
      <p>暂无自选股</p>
      <p class="hint">在行情页面点击 ☆ 添加自选股，或在此输入代码添加</p>
    </div>

    <section class="alerts-section" v-if="alerts.length">
      <div class="section-title">价格预警</div>
      <div class="alerts-list">
        <div v-for="a in alerts" :key="a.id" class="alert-item">
          <span class="alert-symbol mono">{{ a.symbol }}</span>
          <span class="alert-type">{{ a.alert_type }}</span>
          <span class="alert-value mono">{{ a.value }}</span>
          <span class="alert-status" :class="{ triggered: a.triggered }">
            {{ a.triggered ? '已触发' : '监控中' }}
          </span>
          <button class="remove-btn" @click="removeAlert(a.id)">删除</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWatchlistStore } from '@/stores/watchlist'
import { formatPrice, formatVolume, formatAmount } from '@/utils/format'
import type { StockQuote, PriceAlert } from '@/types'

const router = useRouter()
const watchlistStore = useWatchlistStore()

const addSymbol = ref('')
const alerts = ref<PriceAlert[]>([])

const quotes = computed<StockQuote[]>(() => {
  return Object.values(watchlistStore.quotes) as StockQuote[]
})

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
    alerts.value = alerts.value.filter(a => a.id !== alertId)
  } catch {
    // silent
  }
}

onMounted(async () => {
  await watchlistStore.fetchWatchlist()
  try {
    alerts.value = await watchlistStore.fetchAlerts()
  } catch {
    // silent
  }
})
</script>

<style scoped>
.watchlist-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
}

.add-stock {
  display: flex;
  gap: var(--space-2);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 3px;
}

.add-input {
  padding: var(--space-2) var(--space-3);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: var(--text-sm);
  outline: none;
  width: 200px;
}

.add-input:focus {
  background: var(--bg-elevated);
}

.add-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--bg-gradient-accent);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: box-shadow var(--transition-fast);
}

.add-btn:hover {
  box-shadow: var(--glow-accent);
}

.wl-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.wl-table th {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  background: var(--bg-elevated);
  white-space: nowrap;
}

.wl-row {
  cursor: pointer;
  transition: background var(--duration-fast);
}

.wl-row:hover {
  background: var(--bg-hover);
}

.wl-row td {
  padding: var(--space-2) var(--space-3);
  white-space: nowrap;
}

.wl-row:nth-child(even) {
  background: var(--bg-hover);
}

.code { color: var(--accent); }
.name { color: var(--text-primary); }

.remove-btn {
  background: none;
  border: 1px solid var(--border);
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  cursor: pointer;
  font-family: var(--font-sans);
}

.remove-btn:hover {
  border-color: var(--rise);
  color: var(--rise);
}

.empty-state {
  padding: var(--space-10);
  text-align: center;
  color: var(--text-tertiary);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.hint {
  font-size: var(--text-xs);
  margin-top: var(--space-2);
}

.alerts-section {
  margin-top: var(--space-6);
}

.section-title {
  font-size: var(--text-md);
  font-weight: 500;
  margin-bottom: var(--space-3);
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.alert-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}

.alert-symbol {
  color: var(--accent);
}

.alert-type {
  color: var(--text-secondary);
}

.alert-value {
  color: var(--text-primary);
}

.alert-status {
  color: var(--text-tertiary);
}

.alert-status.triggered {
  color: var(--rise);
}
</style>
