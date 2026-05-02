<template>
  <div class="dashboard">
    <div class="dash-grid">
      <section class="section indices-section">
        <div class="section-title">市场指数</div>
        <div class="indices-grid">
          <div v-for="idx in cnIndices" :key="idx.code" class="index-card" :class="idx.change_pct >= 0 ? 'rise' : 'fall'">
            <div class="index-name">{{ idx.name }}</div>
            <div class="index-price mono">{{ formatPrice(idx.price) }}</div>
            <div class="index-change mono">
              {{ idx.change_pct >= 0 ? '+' : '' }}{{ idx.change_pct?.toFixed(2) }}%
            </div>
          </div>
        </div>
      </section>

      <section class="section heatmap-section">
        <div class="section-header">
          <span class="section-title">板块热力图</span>
        </div>
        <div class="heatmap-wrap" v-if="heatmap.length">
          <div class="heatmap-grid">
            <div
              v-for="item in heatmap.slice(0, 24)"
              :key="item.name"
              class="heatmap-cell"
              :class="item.change_pct >= 0 ? 'rise' : 'fall'"
              :style="{ flex: Math.max(item.value, 1e9), fontSize: item.name.length > 4 ? '10px' : '11px' }"
              :title="`${item.name} ${item.change_pct >= 0 ? '+' : ''}${item.change_pct.toFixed(2)}%`"
            >
              <span class="hm-name">{{ item.name }}</span>
              <span class="hm-pct mono">{{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无数据</div>
      </section>

      <section class="section signal-section">
        <div class="section-header">
          <span class="section-title">策略信号流</span>
          <span class="signal-count">{{ signals.length }}条</span>
        </div>
        <div class="signal-list" v-if="signals.length">
          <div v-for="sig in signals.slice(0, 10)" :key="sig.id" class="signal-item" @click="goToStock(sig.symbol)">
            <div class="signal-left">
              <span class="signal-badge" :class="sig.type === 'buy' ? 'badge-buy' : 'badge-sell'">
                {{ sig.type === 'buy' ? '买' : '卖' }}
              </span>
              <span class="signal-name">{{ sig.name || sig.symbol }}</span>
            </div>
            <div class="signal-right">
              <span class="signal-strategy">{{ sig.strategy }}</span>
              <span class="signal-time mono">{{ sig.time }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无信号</div>
      </section>

      <section class="section northbound-section">
        <div class="section-title">北向资金</div>
        <div class="northbound-content" v-if="northbound">
          <div class="nb-main">
            <div class="nb-label">今日净流入</div>
            <div class="nb-value mono" :class="northbound.net_inflow >= 0 ? 'text-rise' : 'text-fall'">
              {{ northbound.net_inflow >= 0 ? '+' : '' }}{{ formatNumber(northbound.net_inflow) }}亿
            </div>
          </div>
          <div class="nb-detail">
            <div class="nb-item">
              <span class="nb-item-label">沪股通</span>
              <span class="mono" :class="northbound.sh_inflow >= 0 ? 'text-rise' : 'text-fall'">
                {{ northbound.sh_inflow >= 0 ? '+' : '' }}{{ formatNumber(northbound.sh_inflow) }}亿
              </span>
            </div>
            <div class="nb-item">
              <span class="nb-item-label">深股通</span>
              <span class="mono" :class="northbound.sz_inflow >= 0 ? 'text-rise' : 'text-fall'">
                {{ northbound.sz_inflow >= 0 ? '+' : '' }}{{ formatNumber(northbound.sz_inflow) }}亿
              </span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无数据</div>
      </section>

      <section class="section limitup-section">
        <div class="section-header">
          <span class="section-title">涨停板</span>
          <span class="section-count">{{ limitUpStocks.length }}只</span>
        </div>
        <div class="limitup-list" v-if="limitUpStocks.length">
          <div v-for="item in limitUpStocks.slice(0, 8)" :key="item.code" class="limitup-item" @click="goToStock(item.code)">
            <div class="limitup-left">
              <span class="limitup-name">{{ item.name }}</span>
              <span class="limitup-code mono">{{ item.code }}</span>
            </div>
            <div class="limitup-right">
              <span class="limitup-chain" v-if="item.chain_count > 1">{{ item.chain_count }}连板</span>
              <span class="limitup-time mono">{{ item.time }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无涨停</div>
      </section>

      <section class="section dragon-section">
        <div class="section-header">
          <span class="section-title">龙虎榜</span>
          <span class="section-count">{{ dragonTiger.length }}只</span>
        </div>
        <div class="dragon-list" v-if="dragonTiger.length">
          <div v-for="item in dragonTiger.slice(0, 8)" :key="item.code" class="dragon-item" @click="goToStock(item.code)">
            <div class="dragon-left">
              <span class="dragon-name">{{ item.name }}</span>
              <span class="dragon-code mono">{{ item.code }}</span>
            </div>
            <div class="dragon-right">
              <span class="dragon-buy mono">买{{ formatAmount(item.buy_amount) }}</span>
              <span class="dragon-sell mono">卖{{ formatAmount(item.sell_amount) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无数据</div>
      </section>

      <section class="section anomaly-section">
        <div class="section-header">
          <span class="section-title">异动行情</span>
          <span class="section-count">{{ anomalies.length }}只</span>
        </div>
        <div class="anomaly-list" v-if="anomalies.length">
          <div v-for="item in anomalies.slice(0, 12)" :key="item.symbol" class="anomaly-item" @click="goToStock(item.symbol)">
            <div class="anomaly-left">
              <span class="anomaly-name">{{ item.name }}</span>
              <span class="anomaly-code mono">{{ item.symbol }}</span>
            </div>
            <div class="anomaly-right">
              <span class="anomaly-pct mono" :class="item.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
              </span>
              <span class="anomaly-reason">{{ item.reason }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">暂无异常行情</div>
      </section>

      <section class="section account-section">
        <div class="section-title">模拟账户</div>
        <div class="account-content" v-if="account">
          <div class="account-main">
            <div class="account-metric">
              <span class="metric-label">总资产</span>
              <span class="metric-value mono">{{ formatNumber(account.total_assets, 0) }}</span>
            </div>
            <div class="account-metric">
              <span class="metric-label">总收益</span>
              <span class="metric-value mono" :class="account.total_profit >= 0 ? 'text-rise' : 'text-fall'">
                {{ account.total_profit >= 0 ? '+' : '' }}{{ formatNumber(account.total_profit, 0) }}
              </span>
            </div>
            <div class="account-metric">
              <span class="metric-label">收益率</span>
              <span class="metric-value mono" :class="account.return_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ account.return_pct >= 0 ? '+' : '' }}{{ account.return_pct.toFixed(2) }}%
              </span>
            </div>
          </div>
          <div class="account-sub">
            <div class="account-metric small">
              <span class="metric-label">现金</span>
              <span class="metric-value mono">{{ formatNumber(account.cash, 0) }}</span>
            </div>
            <div class="account-metric small">
              <span class="metric-label">持仓市值</span>
              <span class="metric-value mono">{{ formatNumber(account.market_value, 0) }}</span>
            </div>
            <div class="account-metric small">
              <span class="metric-label">持仓数</span>
              <span class="metric-value mono">{{ account.position_count }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">加载中...</div>
      </section>

      <section class="section watchlist-section">
        <div class="section-header">
          <span class="section-title">自选股</span>
          <router-link to="/watchlist" class="section-link">查看全部 →</router-link>
        </div>
        <div class="watchlist-mini" v-if="watchlistQuotes.length">
          <div v-for="q in watchlistQuotes.slice(0, 6)" :key="q.symbol" class="wl-item" @click="goToStock(q.symbol)">
            <div class="wl-left">
              <span class="wl-name">{{ q.name }}</span>
              <span class="wl-code mono">{{ q.symbol }}</span>
            </div>
            <div class="wl-right">
              <span class="wl-price mono">{{ formatPrice(q.price) }}</span>
              <span class="wl-pct mono" :class="q.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ q.change_pct >= 0 ? '+' : '' }}{{ q.change_pct.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <router-link to="/market">去行情页添加自选股 →</router-link>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useMarketStore } from '@/stores/market'
import { usePortfolioStore } from '@/stores/portfolio'
import { useWatchlistStore } from '@/stores/watchlist'
import { formatNumber, formatPrice } from '@/utils/format'
import { api } from '@/api'
import type { StockQuote } from '@/types'

const router = useRouter()
const marketStore = useMarketStore()
const portfolioStore = usePortfolioStore()
const watchlistStore = useWatchlistStore()

const cnIndices = computed(() => marketStore.cnIndices)
const heatmap = computed(() => marketStore.heatmap)
const anomalies = computed(() => marketStore.anomalies)
const northbound = computed(() => marketStore.northbound)
const account = computed(() => portfolioStore.account)

const signals = ref<any[]>([])
const limitUpStocks = ref<any[]>([])
const dragonTiger = ref<any[]>([])

const watchlistQuotes = computed(() => {
  return Object.values(watchlistStore.quotes) as StockQuote[]
})

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

function formatAmount(val: number): string {
  if (!val || val === 0) return '0'
  if (Math.abs(val) >= 1e8) return (val / 1e8).toFixed(1) + '亿'
  if (Math.abs(val) >= 1e4) return (val / 1e4).toFixed(0) + '万'
  return val.toFixed(0)
}

async function fetchSignals() {
  try {
    const res = await api.stock.signals('sh000300')
    if (res?.signals) {
      signals.value = res.signals.slice(0, 10).map((s: any, i: number) => ({
        id: i,
        symbol: s.symbol || 'sh000300',
        name: s.name || '沪深300',
        type: s.signal_type || 'buy',
        strategy: s.strategy || '综合策略',
        time: s.date || '',
      }))
    }
  } catch {}
}

async function fetchLimitUp() {
  try {
    const res = await api.market.limitUp()
    if (res) {
      limitUpStocks.value = Array.isArray(res) ? res : []
    }
  } catch {}
}

async function fetchDragonTiger() {
  try {
    const res = await api.market.dragonTiger()
    if (res) {
      dragonTiger.value = Array.isArray(res) ? res : []
    }
  } catch {}
}

onMounted(async () => {
  await Promise.allSettled([
    marketStore.fetchDashboardData(),
    portfolioStore.fetchAccount(),
    watchlistStore.fetchWatchlist(),
    fetchSignals(),
    fetchLimitUp(),
    fetchDragonTiger(),
  ])
})
</script>

<style scoped>
.dashboard {
  max-width: 1400px;
  margin: 0 auto;
}

.dash-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--space-4);
}

.section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  animation: fadeIn 0.3s ease;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.section-title {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  border-left: 3px solid var(--accent);
}

.section-header .section-title {
  padding: 0;
  border-bottom: none;
}

.section-count {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.section-link {
  font-size: var(--text-xs);
  color: var(--accent);
}

.indices-section {
  grid-column: 1 / -1;
}

.indices-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1px;
  background: var(--border);
}

.index-card {
  padding: var(--space-3) var(--space-4);
  background: var(--bg-surface);
  cursor: default;
  transition: background var(--transition-fast);
}

.index-card:hover {
  background: var(--bg-hover);
}

.index-card.rise {
  background: var(--bg-gradient-card-rise);
}

.index-card.fall {
  background: var(--bg-gradient-card-fall);
}

.index-name {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.index-price {
  font-size: var(--text-lg);
  font-weight: 600;
  margin-bottom: 2px;
}

.index-change {
  font-size: var(--text-xs);
}

.index-card.rise .index-price,
.index-card.rise .index-change {
  color: var(--rise);
}

.index-card.fall .index-price,
.index-card.fall .index-change {
  color: var(--fall);
}

.heatmap-section {
  grid-column: 1 / 3;
}

.heatmap-wrap {
  padding: var(--space-3);
}

.heatmap-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  height: 240px;
}

.heatmap-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  min-width: 40px;
  min-height: 40px;
  padding: 2px;
  cursor: default;
  transition: opacity var(--transition-normal), transform var(--transition-fast);
}

.heatmap-cell:hover {
  opacity: 0.85;
  transform: scale(1.05);
}

.heatmap-cell.rise {
  background: rgba(239, 68, 68, 0.15);
  color: var(--rise);
}

.heatmap-cell.fall {
  background: rgba(34, 197, 94, 0.15);
  color: var(--fall);
}

.hm-name {
  font-size: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.hm-pct {
  font-size: 10px;
  font-weight: 500;
}

.signal-section {
  grid-column: 3 / 4;
}

.signal-count {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.signal-list {
  max-height: 280px;
  overflow-y: auto;
}

.signal-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.signal-item:hover {
  background: var(--bg-hover);
}

.signal-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.signal-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1.4;
}

.badge-buy {
  background: rgba(239, 68, 68, 0.15);
  color: var(--rise);
}

.badge-sell {
  background: rgba(34, 197, 94, 0.15);
  color: var(--fall);
}

.signal-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.signal-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.signal-strategy {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: 1px 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
}

.signal-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.northbound-content {
  padding: var(--space-4);
}

.nb-main {
  margin-bottom: var(--space-3);
}

.nb-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.nb-value {
  font-size: var(--text-2xl);
  font-weight: 600;
}

.nb-detail {
  display: flex;
  gap: var(--space-6);
}

.nb-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nb-item-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.limitup-section {
  grid-column: 1 / 2;
}

.limitup-list {
  max-height: 280px;
  overflow-y: auto;
}

.limitup-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.limitup-item:hover {
  background: var(--bg-hover);
}

.limitup-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.limitup-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.limitup-code {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.limitup-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.limitup-chain {
  font-size: var(--text-xs);
  color: var(--rise);
  font-weight: 500;
}

.limitup-time {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.dragon-section {
  grid-column: 2 / 3;
}

.dragon-list {
  max-height: 280px;
  overflow-y: auto;
}

.dragon-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.dragon-item:hover {
  background: var(--bg-hover);
}

.dragon-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.dragon-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.dragon-code {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.dragon-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.dragon-buy {
  font-size: var(--text-xs);
  color: var(--rise);
}

.dragon-sell {
  font-size: var(--text-xs);
  color: var(--fall);
}

.anomaly-section {
  grid-column: 1 / 2;
}

.anomaly-list {
  max-height: 280px;
  overflow-y: auto;
}

.anomaly-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.anomaly-item:hover {
  background: var(--bg-hover);
}

.anomaly-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.anomaly-name {
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.anomaly-code {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.anomaly-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.anomaly-pct {
  font-size: var(--text-sm);
  font-weight: 500;
}

.anomaly-reason {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: 1px 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
}

.account-section {
  grid-column: 2 / 3;
}

.account-content {
  padding: var(--space-4);
}

.account-main {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.account-metric {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.metric-value {
  font-size: var(--text-md);
  font-weight: 500;
}

.account-metric.small .metric-value {
  font-size: var(--text-sm);
}

.account-sub {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.watchlist-section {
  grid-column: 3 / 4;
}

.watchlist-mini {
  max-height: 280px;
  overflow-y: auto;
}

.wl-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.wl-item:hover {
  background: var(--bg-hover);
}

.wl-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.wl-name {
  font-size: var(--text-sm);
}

.wl-code {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.wl-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.wl-price {
  font-size: var(--text-sm);
}

.wl-pct {
  font-size: var(--text-xs);
  font-weight: 500;
  min-width: 56px;
  text-align: right;
}

.empty-state {
  padding: var(--space-8) var(--space-6);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  background: var(--bg-gradient-card);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1200px) {
  .dash-grid {
    grid-template-columns: 1fr 1fr;
  }
  .indices-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .heatmap-section {
    grid-column: 1 / -1;
  }
  .signal-section,
  .limitup-section,
  .dragon-section,
  .anomaly-section,
  .account-section,
  .watchlist-section {
    grid-column: auto;
  }
}
</style>
