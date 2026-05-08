<template>
  <div class="bbg-dash">
    <TickerBar :indices="displayIndices.map(idx => ({ name: idx.name, price: idx.price, change: idx.change ?? 0, change_pct: idx.change_pct, sparkline: generateSparkData(idx.change_pct) }))" />

    <div class="bbg-grid">
      <section class="bbg-col bbg-col--left">
        <DataPanel title="SECTOR HEATMAP" :loading="marketStore.loading">
          <template #header-actions>
            <router-link to="/sector" class="bbg-link">VIEW ALL</router-link>
          </template>
          <BaseChart v-if="heatmapOption" :option="heatmapOption" height="280px" />
          <div v-else class="bbg-empty">LOADING...</div>
        </DataPanel>

        <DataPanel title="MARKET OVERVIEW" :loading="marketStore.loading">
          <div class="bbg-metrics">
            <MetricBlock :value="riseCount" label="RISE" direction="rise" />
            <MetricBlock :value="fallCount" label="FALL" direction="fall" />
            <MetricBlock :value="volumeRatioDisplay" label="VOL RATIO" direction="neutral" />
            <MetricBlock :value="northboundDisplay" label="NORTHBOUND" :direction="northboundDirection" />
            <MetricBlock :value="totalAmountDisplay" label="TOTAL AMT" direction="neutral" />
          </div>
        </DataPanel>
      </section>

      <section class="bbg-col bbg-col--mid">
        <DataPanel title="STRATEGY SIGNALS">
          <div v-if="signals.length" class="bbg-sig-list">
            <div
              v-for="sig in signals.slice(0, 8)"
              :key="sig.id"
              class="bbg-sig-row"
              @click="sig.symbol && goToStock(sig.symbol)"
            >
              <div class="bbg-sig-left">
                <SignalBadge :type="(sig.type as 'buy' | 'sell' | 'hold')" />
                <span class="bbg-sig-name">{{ sig.name }}</span>
              </div>
              <span class="bbg-sig-strat">{{ sig.strategy }}</span>
            </div>
          </div>
          <div v-else class="bbg-empty">NO SIGNALS</div>
        </DataPanel>

        <DataPanel title="STRATEGY RANKING">
          <template #header-actions>
            <router-link to="/strategy" class="bbg-link">VIEW ALL</router-link>
          </template>
          <div v-if="strategyRanking?.strategies.length" class="bbg-rank-list">
            <div class="bbg-rank-header">
              <span class="bbg-rank-h-cell bbg-rank-h-cell--name">STRATEGY</span>
              <span class="bbg-rank-h-cell bbg-rank-h-cell--sharpe">SHARPE</span>
              <span class="bbg-rank-h-cell bbg-rank-h-cell--ret">RETURN</span>
            </div>
            <div
              v-for="(s, idx) in strategyRanking.strategies.slice(0, 6)"
              :key="s.strategy"
              class="bbg-rank-row"
            >
              <div class="bbg-rank-left">
                <span class="bbg-rank-num" :class="idx < 3 ? 'bbg-rank-num--top' : ''">{{ idx + 1 }}</span>
                <span class="bbg-rank-name">{{ s.strategy }}</span>
              </div>
              <div class="bbg-rank-right">
                <span class="bbg-num bbg-num--sm" :class="s.sharpe_ratio >= 0 ? 'bbg-rise' : 'bbg-fall'">
                  {{ safeToFixed(s.sharpe_ratio, 2) }}
                </span>
                <span class="bbg-num bbg-num--sm" :class="s.total_return >= 0 ? 'bbg-rise' : 'bbg-fall'">
                  {{ formatPct(s.total_return) }}
                </span>
              </div>
            </div>
          </div>
          <div v-else class="bbg-empty">LOADING...</div>
        </DataPanel>

        <DataPanel title="UNUSUAL ACTIVITY">
          <div v-if="anomalies.length" class="bbg-ano-list">
            <div
              v-for="item in anomalies.slice(0, 8)"
              :key="item.symbol"
              class="bbg-ano-row"
              @click="goToStock(item.symbol)"
            >
              <div class="bbg-ano-left">
                <span class="bbg-ano-name">{{ item.name }}</span>
                <span class="bbg-ano-code">{{ item.symbol }}</span>
              </div>
              <div class="bbg-ano-right">
                <span class="bbg-num bbg-num--sm" :class="item.change_pct >= 0 ? 'bbg-rise' : 'bbg-fall'">
                  {{ formatPct(item.change_pct) }}
                </span>
                <span class="bbg-ano-reason">{{ item.reason }}</span>
              </div>
            </div>
          </div>
          <div v-else class="bbg-empty">NO UNUSUAL ACTIVITY</div>
        </DataPanel>
      </section>

      <section class="bbg-col bbg-col--right">
        <DataPanel title="ACCOUNT SNAPSHOT">
          <template #header-actions>
            <router-link to="/portfolio" class="bbg-link">MANAGE</router-link>
          </template>
          <div v-if="account" class="bbg-acct">
            <div class="bbg-acct-total">
              <span class="bbg-acct-label">TOTAL ASSETS</span>
              <span class="bbg-num bbg-num--xl">{{ formatNumber(account.total_assets, 0) }}</span>
            </div>
            <div class="bbg-acct-row">
              <MetricBlock
                :value="dailyPnl"
                label="DAILY P&L"
                :direction="account.risk_report.current_daily_pnl >= 0 ? 'rise' : 'fall'"
              />
              <MetricBlock
                :value="formatPct(account.return_pct)"
                label="RETURN"
                :direction="account.return_pct >= 0 ? 'rise' : 'fall'"
              />
            </div>
            <div v-if="account.positions.length" class="bbg-acct-hold">
              <div class="bbg-acct-hold-title">HOLDINGS</div>
              <div class="bbg-hold-bar">
                <div
                  v-for="(pos, i) in account.positions.slice(0, 6)"
                  :key="pos.symbol"
                  class="bbg-hold-seg"
                  :style="{
                    width: pos.weight + '%',
                    background: HOLDING_COLORS[i % HOLDING_COLORS.length],
                  }"
                  :title="`${pos.name} ${safeToFixed(pos.weight, 1)}%`"
                />
              </div>
              <div class="bbg-hold-legend">
                <span
                  v-for="(pos, i) in account.positions.slice(0, 4)"
                  :key="pos.symbol"
                  class="bbg-hold-leg"
                >
                  <span
                    class="bbg-hold-dot"
                    :style="{ background: HOLDING_COLORS[i % HOLDING_COLORS.length] }"
                  />
                  <span>{{ pos.name }}</span>
                </span>
              </div>
            </div>
          </div>
          <div v-else class="bbg-empty">LOADING...</div>
        </DataPanel>

        <DataPanel title="WATCHLIST">
          <template #header-actions>
            <router-link to="/watchlist" class="bbg-link">VIEW ALL</router-link>
          </template>
          <div v-if="watchlistQuotes.length" class="bbg-wl-list">
            <div class="bbg-wl-header">
              <span class="bbg-wl-h-cell bbg-wl-h-cell--name">NAME</span>
              <span class="bbg-wl-h-cell bbg-wl-h-cell--price">PRICE</span>
              <span class="bbg-wl-h-cell bbg-wl-h-cell--chg">CHG%</span>
            </div>
            <div
              v-for="q in watchlistQuotes.slice(0, 6)"
              :key="q.symbol"
              class="bbg-wl-row"
              @click="goToStock(q.symbol)"
            >
              <div class="bbg-wl-left">
                <span class="bbg-wl-name">{{ q.name }}</span>
                <span class="bbg-wl-code">{{ q.symbol }}</span>
              </div>
              <div class="bbg-wl-right">
                <span class="bbg-num bbg-num--base">{{ formatPrice(q.price) }}</span>
                <span class="bbg-num bbg-num--sm" :class="q.change_pct >= 0 ? 'bbg-rise' : 'bbg-fall'">
                  {{ formatPct(q.change_pct) }}
                </span>
              </div>
            </div>
          </div>
          <div v-else class="bbg-empty">
            <router-link to="/market">ADD STOCKS TO WATCHLIST</router-link>
          </div>
        </DataPanel>
      </section>
    </div>

    <section class="bbg-features">
      <router-link
        v-for="card in featureCards"
        :key="card.to"
        :to="card.to"
        class="bbg-feature-card"
      >
        <div class="bbg-fc-icon" :style="{ background: card.iconBg, color: card.iconColor }">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-if="card.svg === 'news'"><path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/></svg>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-else-if="card.svg === 'screener'"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-else-if="card.svg === 'moneyflow'"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-else-if="card.svg === 'chip'"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-else-if="card.svg === 'sector'"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/><path d="M2 12h20"/></svg>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" v-else-if="card.svg === 'strategy'"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        </div>
        <div class="bbg-fc-body">
          <span class="bbg-fc-title">{{ card.title }}</span>
          <span class="bbg-fc-desc">{{ card.desc }}</span>
        </div>
        <svg class="bbg-fc-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
      </router-link>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useLoadingState } from '@/composables/useLoadingState'
import { useMarketStore } from '@/stores/market'
import { usePortfolioStore } from '@/stores/portfolio'
import { useWatchlistStore } from '@/stores/watchlist'
import { api } from '@/api'
import { formatNumber, formatPrice, formatPct, safeToFixed } from '@/utils/format'
import DataPanel from '@/components/ui/DataPanel.vue'
import MetricBlock from '@/components/ui/MetricBlock.vue'
const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))
import SignalBadge from '@/components/common/SignalBadge.vue'
import TickerBar from '@/components/layout/TickerBar.vue'
import type { StockQuote, SignalItem, MarketEvent, PerformanceOverview } from '@/types'

const log = createLogger('Dashboard')

const HOLDING_COLORS = [
  '#2979ff', '#00e676', '#ff3b3b', '#ffd600', '#e040fb', '#1de9b6', '#ff9100', '#00b0ff',
]

const TREEMAP_COLOR_RANGE = [
  { pct: -7, rgb: [0, 77, 46] },
  { pct: -3, rgb: [0, 230, 118] },
  { pct: 0, rgb: [51, 51, 69] },
  { pct: 3, rgb: [239, 68, 68] },
  { pct: 7, rgb: [74, 0, 0] },
]

const featureCards = [
  {
    to: '/news',
    title: '资讯中心',
    desc: '实时财经新闻与市场情绪',
    iconBg: 'rgba(41, 121, 255, 0.12)',
    iconColor: '#2979ff',
    svg: 'news',
  },
  {
    to: '/screener',
    title: '智能选股',
    desc: '多维度条件筛选投资机会',
    iconBg: 'rgba(224, 64, 251, 0.12)',
    iconColor: '#e040fb',
    svg: 'screener',
  },
  {
    to: '/moneyflow',
    title: '资金流向',
    desc: '追踪主力资金动向',
    iconBg: 'rgba(255, 214, 0, 0.12)',
    iconColor: '#ffd600',
    svg: 'moneyflow',
  },
  {
    to: '/chip',
    title: '筹码分布',
    desc: '分析持仓成本与支撑阻力',
    iconBg: 'rgba(0, 230, 118, 0.12)',
    iconColor: '#00e676',
    svg: 'chip',
  },
  {
    to: '/sector',
    title: '板块轮动',
    desc: '追踪板块资金轮动节奏',
    iconBg: 'rgba(255, 59, 59, 0.12)',
    iconColor: '#ff3b3b',
    svg: 'sector',
  },
  {
    to: '/strategy',
    title: '策略回测',
    desc: '量化策略验证与优化',
    iconBg: 'rgba(29, 233, 182, 0.12)',
    iconColor: '#1de9b6',
    svg: 'strategy',
  },
]

const POLL_INTERVAL_MS = 30_000

const router = useRouter()
const marketStore = useMarketStore()
const portfolioStore = usePortfolioStore()
const watchlistStore = useWatchlistStore()

const signals = ref<SignalItem[]>([])
const marketEvents = ref<MarketEvent[]>([])
const strategyRanking = ref<PerformanceOverview | null>(null)
const regimeData = ref<{
  current_regime: string
  recommendation: string
  regime_history: { regime: string; index: number }[]
} | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null
const { cancelAll } = useRequestCancel()
const dashLoader = useLoadingState()

const cnIndices = computed(() => marketStore.cnIndices)
const heatmap = computed(() => marketStore.heatmap)
const anomalies = computed(() => marketStore.anomalies)
const northbound = computed(() => marketStore.northbound)
const account = computed(() => portfolioStore.account)

const displayIndices = computed(() => cnIndices.value.slice(0, 6))

const watchlistQuotes = computed<StockQuote[]>(() => {
  return Object.values(watchlistStore.quotes) as StockQuote[]
})

const dailyPnl = computed(() => {
  if (!account.value) return '0'
  const pnl = account.value.risk_report.current_daily_pnl
  return formatPct(pnl)
})

const riseCount = computed(() => {
  return String(heatmap.value.filter(h => h.change_pct >= 0).length)
})

const fallCount = computed(() => {
  return String(heatmap.value.filter(h => h.change_pct < 0).length)
})

const volumeRatioDisplay = computed(() => {
  if (!heatmap.value.length) return 'N/A'
  const riseAmount = heatmap.value
    .filter(h => h.change_pct >= 0)
    .reduce((s, h) => s + h.amount, 0)
  const fallAmount = heatmap.value
    .filter(h => h.change_pct < 0)
    .reduce((s, h) => s + h.amount, 0)
  if (fallAmount === 0) return riseAmount > 0 ? '∞' : 'N/A'
  return safeToFixed(riseAmount / fallAmount, 2) + 'x'
})

const northboundDisplay = computed(() => {
  if (!northbound.value) return 'N/A'
  return formatNumber(northbound.value.net_inflow, 0)
})

const northboundDirection = computed<'rise' | 'fall' | 'neutral'>(() => {
  if (!northbound.value) return 'neutral'
  return northbound.value.net_inflow >= 0 ? 'rise' : 'fall'
})

const totalAmountDisplay = computed(() => {
  if (!heatmap.value.length) return 'N/A'
  const total = heatmap.value.reduce((s, h) => s + h.amount, 0)
  return formatNumber(total, 0)
})

function generateSparkData(changePct: number): number[] {
  const base = 100
  const amp = Math.min(Math.abs(changePct) * 1.5, 8)
  const dir = changePct >= 0 ? 1 : -1
  return Array.from({ length: 9 }, (_, i) => {
    const noise = Math.sin(i * 1.2 + changePct) * amp * 0.25
    const trend = (i / 8) * amp * dir
    return base + trend + noise
  })
}

function heatmapColor(changePct: number): string {
  const clamped = Math.max(-7, Math.min(7, changePct))
  let lower = TREEMAP_COLOR_RANGE[0]
  let upper = TREEMAP_COLOR_RANGE[TREEMAP_COLOR_RANGE.length - 1]

  for (let i = 0; i < TREEMAP_COLOR_RANGE.length - 1; i++) {
    if (clamped >= TREEMAP_COLOR_RANGE[i].pct && clamped <= TREEMAP_COLOR_RANGE[i + 1].pct) {
      lower = TREEMAP_COLOR_RANGE[i]
      upper = TREEMAP_COLOR_RANGE[i + 1]
      break
    }
  }

  const range = upper.pct - lower.pct
  const t = range === 0 ? 0 : (clamped - lower.pct) / range
  const r = Math.round(lower.rgb[0] + t * (upper.rgb[0] - lower.rgb[0]))
  const g = Math.round(lower.rgb[1] + t * (upper.rgb[1] - lower.rgb[1]))
  const b = Math.round(lower.rgb[2] + t * (upper.rgb[2] - lower.rgb[2]))

  return `rgb(${r},${g},${b})`
}

const heatmapOption = computed(() => {
  if (!heatmap.value.length) return null
  return {
    tooltip: {
      formatter: (info: { data: { name: string; changePct: number; leader: string } }) => {
        const d = info.data
        return `${d.name}<br/>涨跌: ${formatPct(d.changePct)}<br/>领涨: ${d.leader || '-'}`
      },
    },
    series: [
      {
        type: 'treemap',
        width: '100%',
        height: '100%',
        data: heatmap.value.map((item) => ({
          name: item.name,
          value: Math.max(item.value, 1e9),
          changePct: item.change_pct,
          leader: item.leader,
          itemStyle: {
            color: heatmapColor(item.change_pct),
          },
        })),
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          formatter: '{b}',
          fontSize: 10,
          color: '#f0f0f8',
        },
        upperLabel: { show: false },
        itemStyle: {
          borderColor: 'rgba(5,5,7,0.8)',
          borderWidth: 1,
          gapWidth: 2,
        },
        levels: [
          {
            itemStyle: {
              borderColor: 'rgba(5,5,7,0.8)',
              borderWidth: 1,
              gapWidth: 2,
            },
          },
        ],
      },
    ],
  }
})

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

async function fetchSignals() {
  const res = await dashLoader.wrap(() => api.stock.signals('sh000300'), '获取信号失败') as { symbol: string; signals: SignalItem[] } | null
  if (res?.signals) {
    signals.value = res.signals.slice(0, 10).map(
      (
        s: {
          symbol?: string
          signal?: string
          price?: number
          date?: string
          name?: string
          signal_type?: string
          strategy?: string
        },
        i: number,
      ) => ({
        id: i,
        symbol: s.symbol || 'sh000300',
        name: s.name || '沪深300',
        type: s.signal_type || 'buy',
        strategy: s.strategy || '综合策略',
        time: s.date || '',
      }),
    )
  }
}

async function fetchMarketEvents() {
  const result = await dashLoader.wrap(() => api.market.events(15), '获取市场事件失败') as MarketEvent[] | null
  if (result) marketEvents.value = result
}

async function fetchRegime() {
  const result = await dashLoader.wrap(() => api.stock.regime('sh000300'), '获取市场状态失败') as typeof regimeData.value | null
  if (result?.current_regime) regimeData.value = result as typeof regimeData.value
}

async function fetchStrategyRanking() {
  const result = await dashLoader.wrap(() => api.backtest.performanceOverview('600000', '1y'), '获取策略排名失败') as PerformanceOverview | null
  if (result) strategyRanking.value = result
}

onMounted(async () => {
  await Promise.allSettled([
    marketStore.fetchDashboardData(),
    portfolioStore.fetchAccount(),
    watchlistStore.fetchWatchlist(),
    fetchSignals(),
    fetchMarketEvents(),
    fetchRegime(),
    fetchStrategyRanking(),
  ])

  pollTimer = setInterval(() => {
    marketStore.fetchOverview()
    fetchMarketEvents()
    fetchRegime()
  }, POLL_INTERVAL_MS)
})

onUnmounted(() => {
  cancelAll()
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.bbg-dash {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
  background: var(--bg-base);
  min-height: 100%;
}

.bbg-dash > :deep(.ticker-bar) {
  border-radius: 0;
}

.bbg-grid {
  display: grid;
  grid-template-columns: 2fr 1.2fr 1fr;
  gap: var(--u3);
}

.bbg-col {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
}

.bbg-link {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 500;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.bbg-link:hover {
  color: var(--text-primary);
  text-decoration: none;
}

.bbg-empty {
  padding: var(--u6) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.bbg-num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.bbg-num--xl {
  font-size: var(--fs-2xl);
  font-weight: 700;
  color: var(--text-primary);
}

.bbg-num--base {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-primary);
}

.bbg-num--sm {
  font-size: var(--fs-xs);
  font-weight: 500;
}

.bbg-rise {
  color: var(--rise);
}

.bbg-fall {
  color: var(--fall);
}

.bbg-metrics {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--u2);
}

.bbg-sig-list {
  display: flex;
  flex-direction: column;
  max-height: 280px;
  overflow-y: auto;
}

.bbg-sig-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u1) 0;
  border-bottom: 1px solid var(--border-hair);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.bbg-sig-row:last-child {
  border-bottom: none;
}

.bbg-sig-row:hover {
  background: var(--accent-muted);
}

.bbg-sig-left {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.bbg-sig-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
}

.bbg-sig-strat {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  padding: 1px 4px;
  background: var(--bg-plate);
  border-radius: 0;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.bbg-rank-list {
  display: flex;
  flex-direction: column;
}

.bbg-rank-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: var(--u2);
  border-bottom: 1px solid var(--border-mid);
  margin-bottom: var(--u1);
}

.bbg-rank-h-cell {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 500;
}

.bbg-rank-h-cell--name {
  flex: 1;
}

.bbg-rank-h-cell--sharpe {
  width: 52px;
  text-align: right;
}

.bbg-rank-h-cell--ret {
  width: 56px;
  text-align: right;
}

.bbg-rank-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u1) 0;
  border-bottom: 1px solid var(--border-hair);
}

.bbg-rank-row:last-child {
  border-bottom: none;
}

.bbg-rank-left {
  display: flex;
  align-items: center;
  gap: var(--u2);
  min-width: 0;
  flex: 1;
}

.bbg-rank-num {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  background: var(--bg-plate);
  border-radius: 0;
  flex-shrink: 0;
}

.bbg-rank-num--top {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.bbg-rank-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bbg-rank-right {
  display: flex;
  align-items: center;
  gap: var(--u3);
  flex-shrink: 0;
}

.bbg-rank-right .bbg-num--sm:first-child {
  min-width: 40px;
  text-align: right;
}

.bbg-rank-right .bbg-num--sm:last-child {
  min-width: 52px;
  text-align: right;
}

.bbg-ano-list {
  display: flex;
  flex-direction: column;
  max-height: 240px;
  overflow-y: auto;
}

.bbg-ano-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u1) 0;
  border-bottom: 1px solid var(--border-hair);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.bbg-ano-row:last-child {
  border-bottom: none;
}

.bbg-ano-row:hover {
  background: var(--warn-bg);
}

.bbg-ano-left {
  display: flex;
  align-items: center;
  gap: var(--u2);
  min-width: 0;
}

.bbg-ano-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bbg-ano-code {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.bbg-ano-right {
  display: flex;
  align-items: center;
  gap: var(--u2);
  flex-shrink: 0;
}

.bbg-ano-reason {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  padding: 1px 4px;
  background: var(--bg-plate);
  border-radius: 0;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.bbg-acct {
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

.bbg-acct-total {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bbg-acct-label {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.bbg-acct-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--u2);
}

.bbg-acct-hold {
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.bbg-acct-hold-title {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.bbg-hold-bar {
  display: flex;
  height: 4px;
  border-radius: 0;
  overflow: hidden;
  background: var(--bg-plate);
}

.bbg-hold-seg {
  height: 100%;
  transition: width var(--dur-normal) var(--ease-mechanical);
}

.bbg-hold-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--u2);
}

.bbg-hold-leg {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
}

.bbg-hold-dot {
  width: 4px;
  height: 4px;
  border-radius: 0;
  flex-shrink: 0;
}

.bbg-wl-list {
  display: flex;
  flex-direction: column;
}

.bbg-wl-header {
  display: flex;
  align-items: center;
  padding-bottom: var(--u2);
  border-bottom: 1px solid var(--border-mid);
  margin-bottom: var(--u1);
}

.bbg-wl-h-cell {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 500;
}

.bbg-wl-h-cell--name {
  flex: 1;
}

.bbg-wl-h-cell--price {
  width: 64px;
  text-align: right;
}

.bbg-wl-h-cell--chg {
  width: 52px;
  text-align: right;
}

.bbg-wl-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u1) 0;
  border-bottom: 1px solid var(--border-hair);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
}

.bbg-wl-row:last-child {
  border-bottom: none;
}

.bbg-wl-row:hover {
  background: var(--accent-muted);
}

.bbg-wl-left {
  display: flex;
  align-items: center;
  gap: var(--u2);
  min-width: 0;
  flex: 1;
}

.bbg-wl-name {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bbg-wl-code {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.bbg-wl-right {
  display: flex;
  align-items: center;
  gap: var(--u3);
  flex-shrink: 0;
}

.bbg-wl-right .bbg-num--base {
  min-width: 64px;
  text-align: right;
}

.bbg-wl-right .bbg-num--sm {
  min-width: 52px;
  text-align: right;
}

.bbg-features {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: var(--u2);
}

.bbg-feature-card {
  display: flex;
  align-items: center;
  gap: var(--u3);
  padding: var(--u3) var(--u4);
  background: var(--bg-surface);
  border: 1px solid var(--border-hair);
  border-radius: 0;
  text-decoration: none;
  color: inherit;
  position: relative;
  overflow: hidden;
  transition: border-color var(--dur-fast) var(--ease-mechanical),
              background var(--dur-fast) var(--ease-mechanical);
}

.bbg-feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 2px;
  background: var(--accent);
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.bbg-feature-card:hover {
  border-color: var(--accent);
  color: inherit;
  text-decoration: none;
}

.bbg-feature-card:hover::before {
  opacity: 1;
}

.bbg-fc-icon {
  width: 36px;
  height: 36px;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.bbg-fc-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.bbg-fc-title {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.bbg-fc-desc {
  font-family: var(--font-sans);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bbg-fc-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: color var(--dur-fast) var(--ease-mechanical),
              transform var(--dur-fast) var(--ease-mechanical);
}

.bbg-feature-card:hover .bbg-fc-arrow {
  color: var(--accent);
  transform: translateX(2px);
}

@keyframes scanline {
  0% { transform: translateY(-100%); }
  100% { transform: translateY(100%); }
}

@media (max-width: 1200px) {
  .bbg-grid {
    grid-template-columns: 1fr 1fr;
  }

  .bbg-col--left {
    grid-column: 1 / -1;
  }

  .bbg-metrics {
    grid-template-columns: repeat(3, 1fr);
  }

  .bbg-features {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .bbg-grid {
    grid-template-columns: 1fr;
  }

  .bbg-metrics {
    grid-template-columns: repeat(2, 1fr);
  }

  .bbg-features {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
