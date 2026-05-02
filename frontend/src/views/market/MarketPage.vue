<template>
  <div class="market-page">
    <div class="page-header">
      <h1 class="page-title">市场行情</h1>
      <div class="market-tabs">
        <button v-for="tab in tabs" :key="tab.value" class="tab-btn" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value">
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="market-content">
      <div v-show="activeTab !== 'sector' && activeTab !== 'anomaly'" class="stock-table-wrap">
        <table class="stock-table">
          <thead>
            <tr>
              <th class="col-code">代码</th>
              <th class="col-name">名称</th>
              <th class="col-price">最新价</th>
              <th class="col-change">涨跌幅</th>
              <th class="col-amount">成交额</th>
              <th class="col-volume">成交量</th>
              <th class="col-turnover">换手率</th>
              <th class="col-action"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in stocks" :key="s.symbol" class="stock-row" @click="goToStock(s.symbol)">
              <td class="col-code mono">{{ s.symbol }}</td>
              <td class="col-name">{{ s.name }}</td>
              <td class="col-price mono">{{ formatPrice(s.price) }}</td>
              <td class="col-change mono" :class="s.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ s.change_pct >= 0 ? '+' : '' }}{{ s.change_pct?.toFixed(2) }}%
              </td>
              <td class="col-amount mono">{{ formatAmount(s.amount) }}</td>
              <td class="col-volume mono">{{ formatVolume(s.volume) }}</td>
              <td class="col-turnover mono">{{ s.turnover_rate?.toFixed(2) }}%</td>
              <td class="col-action">
                <button class="watchlist-btn" :class="{ added: isInWatchlist(s.symbol) }" @click.stop="toggleWatchlist(s.symbol)">
                  {{ isInWatchlist(s.symbol) ? '★' : '☆' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="!stocks.length" class="empty-state">暂无数据</div>
      </div>

      <div v-show="activeTab === 'sector'" class="sector-grid" v-if="sectors.length">
        <div v-for="sec in sectors" :key="sec.name" class="sector-card" :class="sec.change_pct >= 0 ? 'rise' : 'fall'" @click="goToStock(sec.code || '')">
          <div class="sec-name">{{ sec.name }}</div>
          <div class="sec-pct mono">{{ sec.change_pct >= 0 ? '+' : '' }}{{ sec.change_pct?.toFixed(2) }}%</div>
          <div class="sec-detail">
            <span>领涨: {{ sec.top_stock || '-' }}</span>
          </div>
        </div>
      </div>
      <div v-show="activeTab === 'sector' && !sectors.length" class="empty-state">暂无板块数据</div>

      <div v-show="activeTab === 'anomaly'" class="anomaly-grid" v-if="anomalies.length">
        <div v-for="a in anomalies" :key="a.symbol" class="anomaly-card" @click="goToStock(a.symbol)">
          <div class="anom-header">
            <span class="anom-name">{{ a.name }}</span>
            <span class="anom-code mono">{{ a.symbol }}</span>
          </div>
          <div class="anom-pct mono" :class="a.change_pct >= 0 ? 'text-rise' : 'text-fall'">
            {{ a.change_pct >= 0 ? '+' : '' }}{{ a.change_pct?.toFixed(2) }}%
          </div>
          <div class="anom-reason">{{ a.reason }}</div>
        </div>
      </div>
      <div v-show="activeTab === 'anomaly' && !anomalies.length" class="empty-state">暂无异常行情</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'
import { useMarketStore } from '@/stores/market'
import { useWatchlistStore } from '@/stores/watchlist'
import { formatPrice, formatAmount, formatVolume } from '@/utils/format'
import type { MarketStock } from '@/types'

const router = useRouter()
const marketStore = useMarketStore()
const watchlistStore = useWatchlistStore()

const tabs = [
  { label: '全部', value: 'A' },
  { label: '沪市', value: 'sh' },
  { label: '深市', value: 'sz' },
  { label: '创业板', value: 'cy' },
  { label: '科创板', value: 'kc' },
  { label: '板块行业', value: 'sector' },
  { label: '量价异动', value: 'anomaly' },
]

const activeTab = ref('A')
const stocks = ref<MarketStock[]>([])
const sectors = ref<any[]>([])
const anomalies = computed(() => marketStore.anomalies)

function goToStock(symbol: string) {
  if (symbol) router.push(`/stock/${symbol}`)
}

function isInWatchlist(symbol: string) {
  return watchlistStore.symbols.includes(symbol)
}

async function toggleWatchlist(symbol: string) {
  if (isInWatchlist(symbol)) {
    await watchlistStore.removeSymbol(symbol)
  } else {
    await watchlistStore.addSymbol(symbol)
  }
}

async function fetchStocks() {
  if (activeTab.value === 'sector' || activeTab.value === 'anomaly') return
  try {
    stocks.value = await api.market.stocks(activeTab.value, 200)
  } catch {
    stocks.value = []
  }
}

async function fetchSectors() {
  try {
    const data = await api.market.heatmap()
    sectors.value = data?.items || []
  } catch {
    sectors.value = []
  }
}

watch(activeTab, (val) => {
  if (val === 'sector') fetchSectors()
  else if (val === 'anomaly') marketStore.fetchDashboardData()
  else fetchStocks()
})

onMounted(() => {
  fetchStocks()
  watchlistStore.fetchWatchlist()
})
</script>

<style scoped>
.market-page {
  max-width: 1400px;
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

.market-tabs {
  display: flex;
  gap: 2px;
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: 2px;
  flex-wrap: wrap;
}

.tab-btn {
  padding: var(--space-1) var(--space-3);
  border: none;
  background: none;
  color: var(--text-secondary);
  font-size: var(--text-sm);
  cursor: pointer;
  border-radius: var(--radius-xs);
  transition: all var(--duration-fast);
  font-family: var(--font-sans);
}

.tab-btn.active {
  background: var(--accent);
  color: white;
}

.tab-btn:hover:not(.active) {
  color: var(--text-primary);
}

.stock-table-wrap {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: auto;
  max-height: calc(100vh - 160px);
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.stock-table th {
  position: sticky;
  top: 0;
  background: var(--bg-elevated);
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  white-space: nowrap;
  z-index: 1;
}

.stock-row {
  cursor: pointer;
  transition: background var(--duration-fast);
}

.stock-row:hover {
  background: var(--bg-hover);
}

.stock-row td {
  padding: var(--space-2) var(--space-3);
  white-space: nowrap;
}

.col-code { color: var(--accent); }
.col-name { color: var(--text-primary); }
.col-price { color: var(--text-primary); }
.col-change { font-weight: 500; }
.col-amount, .col-volume, .col-turnover { color: var(--text-secondary); }

.watchlist-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: var(--text-md);
  color: var(--text-tertiary);
  padding: 2px;
  transition: color var(--duration-fast);
}

.watchlist-btn.added { color: var(--warn); }
.watchlist-btn:hover { color: var(--warn); }

.sector-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
}

.sector-card {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-gradient-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  animation: fadeIn 0.2s ease;
}

.sector-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.sector-card.rise {
  border-left: 3px solid var(--rise);
  background: var(--bg-gradient-card-rise);
}
.sector-card.fall {
  border-left: 3px solid var(--fall);
  background: var(--bg-gradient-card-fall);
}

.sec-name {
  font-size: var(--text-sm);
  font-weight: 500;
  margin-bottom: 4px;
}

.sec-pct {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 4px;
}

.sector-card.rise .sec-pct { color: var(--rise); }
.sector-card.fall .sec-pct { color: var(--fall); }

.sec-detail {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.anomaly-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

.anomaly-card {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-gradient-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  animation: fadeIn 0.2s ease;
}

.anomaly-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.anomaly-card:has(.text-rise) {
  border-left: 3px solid var(--rise);
}

.anomaly-card:has(.text-fall) {
  border-left: 3px solid var(--fall);
}

.anom-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 4px;
}

.anom-name {
  font-size: var(--text-sm);
  font-weight: 500;
}

.anom-code {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.anom-pct {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 4px;
}

.anom-reason {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  display: inline-block;
}

.empty-state {
  padding: var(--space-10);
  text-align: center;
  color: var(--text-tertiary);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .sector-grid { grid-template-columns: repeat(2, 1fr); }
  .anomaly-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
