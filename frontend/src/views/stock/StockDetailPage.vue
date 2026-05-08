<template>
  <div class="bb-page" v-if="quote">
    <header class="bb-ticker">
      <div class="tk-left">
        <span class="tk-name">{{ quote.name }}</span>
        <span class="tk-sym mono">{{ quote.symbol }}</span>
        <span class="tk-mkt">{{ getMarketLabel(quote.market) }}</span>
      </div>
      <div class="tk-price-group">
        <span class="tk-price mono" :class="quote.change_pct >= 0 ? 'c-rise' : 'c-fall'">
          {{ formatPrice(quote.price) }}
        </span>
        <span class="tk-chg mono" :class="quote.change_pct >= 0 ? 'c-rise' : 'c-fall'">
          {{ quote.change_pct >= 0 ? '▲' : '▼' }}
          {{ quote.change_pct >= 0 ? '+' : '' }}{{ safeToFixed(quote.change, 2) }}
          ({{ quote.change_pct >= 0 ? '+' : '' }}{{ safeToFixed(quote.change_pct, 2) }}%)
        </span>
      </div>
      <div class="tk-meta">
        <span class="tk-meta-item"><span class="tk-meta-label">O</span><span class="mono">{{ formatPrice(quote.open) }}</span></span>
        <span class="tk-meta-item"><span class="tk-meta-label">H</span><span class="mono">{{ formatPrice(quote.high) }}</span></span>
        <span class="tk-meta-item"><span class="tk-meta-label">L</span><span class="mono">{{ formatPrice(quote.low) }}</span></span>
        <span class="tk-meta-item"><span class="tk-meta-label">C</span><span class="mono">{{ formatPrice(quote.last_close) }}</span></span>
        <span class="tk-meta-sep" />
        <span class="tk-meta-item"><span class="tk-meta-label">VOL</span><span class="mono">{{ formatVolume(quote.volume) }}</span></span>
        <span class="tk-meta-item"><span class="tk-meta-label">AMT</span><span class="mono">{{ formatNumber(quote.amount) }}</span></span>
        <span class="tk-meta-item"><span class="tk-meta-label">TURN</span><span class="mono">{{ safeToFixed(quote.turnover_rate, 2) }}%</span></span>
      </div>
      <div class="tk-actions">
        <button class="tk-star" :class="{ active: isInWatchlist }" @click="toggleWatchlist">
          {{ isInWatchlist ? '★' : '☆' }}
        </button>
        <button class="tk-buy-btn" @click="showTradeForm = true">BUY</button>
      </div>
    </header>

    <div class="bb-body">
      <div class="bb-chart-col">
        <div class="bb-chart-wrap surface-panel">
          <div class="chart-type-bar">
            <button
              v-for="t in klineTypes"
              :key="t.value"
              class="ct-btn mono"
              :class="{ active: klineType === t.value }"
              @click="klineType = t.value"
            >{{ t.label }}</button>
          </div>
          <CandlestickChart
            :symbol="symbol"
            :period="klinePeriod"
            :kline-type="klineType"
            :show-volume="true"
            :show-signals="true"
            height="100%"
            @update:period="klinePeriod = $event"
          />
        </div>
      </div>

      <aside class="bb-sidebar">
        <section class="sb-panel surface-panel">
          <div class="sb-head">
            <span class="sb-accent" />
            <span class="sb-title">SIGNALS</span>
            <span class="sb-count mono" v-if="signals.length">{{ signals.length }}</span>
          </div>
          <div class="sb-body sig-body" v-if="signals.length">
            <div v-for="s in signals.slice(0, 15)" :key="s.date + (s.signals?.[0]?.strategy || '')" class="sig-row">
              <div class="sig-top">
                <span class="sig-date mono">{{ (s.date || '').slice(5, 10) }}</span>
                <span class="sig-price mono">{{ formatPrice(s.price ?? 0) }}</span>
              </div>
              <div class="sig-badges">
                <span
                  v-for="sig in (s.signals || []).slice(0, 3)"
                  :key="sig.strategy"
                  class="sig-badge"
                  :class="sig.signal === 'buy' ? 'buy' : 'sell'"
                >
                  <span class="sig-marker">{{ sig.signal === 'buy' ? '▲' : '▼' }}</span>
                  <SignalBadge :type="(sig.signal === 'buy' ? 'buy' : 'sell') as 'buy' | 'sell'" />
                  <span class="sig-strat">{{ strategyDisplayName(sig.strategy) }}</span>
                  <span class="sig-conf mono">{{ ((sig.confidence ?? 0) * 100).toFixed(0) }}%</span>
                </span>
              </div>
            </div>
          </div>
          <div v-else class="sb-empty">NO SIGNALS</div>
        </section>

        <section class="sb-panel surface-panel">
          <div class="sb-head">
            <span class="sb-accent" style="background:var(--teal)" />
            <span class="sb-title">DEPTH</span>
          </div>
          <div class="sb-body" v-if="depth">
            <div class="depth-asks">
              <div v-for="(a, i) in depth.asks.slice().reverse()" :key="'a'+i" class="depth-row">
                <span class="depth-price mono c-fall">{{ safeToFixed(a.price, 2) }}</span>
                <span class="depth-qty mono">{{ a.quantity }}</span>
                <div class="depth-bar ask-bar" :style="{ width: (a.quantity / maxQty * 100) + '%' }" />
              </div>
            </div>
            <div class="depth-spread-row">
              <span class="mono">{{ spread }}</span>
            </div>
            <div class="depth-bids">
              <div v-for="(b, i) in depth.bids" :key="'b'+i" class="depth-row">
                <span class="depth-price mono c-rise">{{ safeToFixed(b.price, 2) }}</span>
                <span class="depth-qty mono">{{ b.quantity }}</span>
                <div class="depth-bar bid-bar" :style="{ width: (b.quantity / maxQty * 100) + '%' }" />
              </div>
            </div>
          </div>
          <div v-else class="sb-empty">NO DEPTH</div>
        </section>

        <section class="sb-panel surface-panel">
          <div class="sb-head clickable" @click="tradeFormOpen = !tradeFormOpen">
            <span class="sb-accent" style="background:var(--warn)" />
            <span class="sb-title">TRADE</span>
            <span class="sb-toggle">{{ tradeFormOpen ? '−' : '+' }}</span>
          </div>
          <div class="sb-body trade-body" v-show="tradeFormOpen">
            <div class="trade-field">
              <label>PRICE</label>
              <input v-model.number="tradePrice" type="number" class="trade-input mono" />
            </div>
            <div class="trade-field">
              <label>QTY</label>
              <input v-model.number="tradeShares" type="number" class="trade-input mono" />
            </div>
            <div class="trade-btns">
              <button class="trade-btn buy" @click="doBuy">BUY ▲</button>
              <button class="trade-btn sell" @click="doSell">SELL ▼</button>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <div class="bb-bottom">
      <div class="bb-tab-bar">
        <button
          v-for="t in infoTabs"
          :key="t.key"
          class="bb-tab mono"
          :class="{ active: activeTab === t.key }"
          @click="activeTab = t.key"
        >{{ t.label }}</button>
      </div>

      <div class="bb-tab-content">
        <div v-show="activeTab === 'analysis'" v-if="analysis" class="tab-analysis">
          <div class="analysis-grid">
            <MetricBlock :value="trendLabel" label="趋势方向" :direction="trendDirection" />
            <MetricBlock :value="signalLabel(analysis.signal)" label="综合信号" :direction="signalDirection" />
            <MetricBlock :value="safeToFixed(analysis.composite_score, 1)" label="综合得分" :direction="analysis.composite_score > 0 ? 'rise' : 'fall'" />
            <MetricBlock :value="analysis.momentum.rsi_signal" label="RSI信号" direction="neutral" />
            <MetricBlock :value="analysis.momentum.macd_signal" label="MACD信号" direction="neutral" />
            <MetricBlock :value="analysis.momentum.kdj_signal" label="KDJ信号" direction="neutral" />
            <MetricBlock :value="analysis.volume.trend" label="量能趋势" direction="neutral" />
            <MetricBlock :value="safeToFixed(analysis.volume?.volume_ratio_5d, 2)" label="5日量比" direction="neutral" />
            <MetricBlock :value="safeToFixed(analysis.signal_confidence, 1) + '%'" label="信号置信度" direction="neutral" />
          </div>
          <div class="levels-grid" v-if="analysis.trend.key_levels">
            <DataPanel title="支撑位">
              <div class="level-list">
                <span v-for="(s, i) in analysis.trend.key_levels.support" :key="i" class="level-tag support">{{ formatPrice(s) }}</span>
              </div>
            </DataPanel>
            <DataPanel title="阻力位">
              <div class="level-list">
                <span v-for="(r, i) in analysis.trend.key_levels.resistance" :key="i" class="level-tag resistance">{{ formatPrice(r) }}</span>
              </div>
            </DataPanel>
          </div>
        </div>

        <div v-show="activeTab === 'indicators'" v-if="indicators" class="tab-indicators">
          <div class="ind-grid">
            <div v-for="(val, key) in indicators" :key="key" class="ind-item">
              <span class="ind-key mono">{{ key }}</span>
              <span class="ind-val mono">{{ typeof val === 'number' ? val.toFixed(4) : val }}</span>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'financial'" v-if="fundamentals" class="tab-financial">
          <div class="fund-grid">
            <MetricBlock :value="fundamentals.pe_ttm?.toFixed(1) ?? '-'" label="PE(TTM)" direction="neutral" />
            <MetricBlock :value="fundamentals.pb?.toFixed(2) ?? '-'" label="PB" direction="neutral" />
            <MetricBlock :value="fundamentals.roe != null ? (fundamentals.roe * 100).toFixed(2) + '%' : '-'" label="ROE" :direction="(fundamentals.roe ?? 0) > 0 ? 'rise' : 'fall'" />
            <MetricBlock :value="fundamentals.eps?.toFixed(2) ?? '-'" label="EPS" direction="neutral" />
            <MetricBlock :value="fundamentals.revenue_yoy != null ? (fundamentals.revenue_yoy * 100).toFixed(1) + '%' : '-'" label="营收同比" :direction="(fundamentals.revenue_yoy ?? 0) >= 0 ? 'rise' : 'fall'" />
            <MetricBlock :value="fundamentals.profit_yoy != null ? (fundamentals.profit_yoy * 100).toFixed(1) + '%' : '-'" label="净利同比" :direction="(fundamentals.profit_yoy ?? 0) >= 0 ? 'rise' : 'fall'" />
            <MetricBlock :value="fundamentals.debt_ratio != null ? (fundamentals.debt_ratio * 100).toFixed(1) + '%' : '-'" label="资产负债率" direction="neutral" />
            <MetricBlock :value="fundamentals.market_cap != null ? formatNumber(fundamentals.market_cap) : '-'" label="总市值" direction="neutral" />
          </div>
        </div>

        <div v-show="activeTab === 'backtest'" class="tab-backtest">
          <router-link :to="`/strategy/run?symbol=${symbol}`" class="backtest-link">
            RUN BACKTEST &rarr;
          </router-link>
        </div>

        <div v-show="activeTab === 'related'" v-if="correlation?.related?.length" class="tab-related">
          <DataTable
            :columns="relatedColumns"
            :rows="correlation.related"
            row-key="symbol"
            @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
          />
        </div>
        <div v-show="activeTab === 'related'" v-else-if="activeTab === 'related'" class="tab-empty">NO RELATED DATA</div>

        <div v-show="activeTab === 'ai'" v-if="aiSummary" class="tab-ai">
          <div class="ai-panel surface-panel">
            <div class="sb-head">
              <span class="sb-accent" style="background:var(--purple)" />
              <span class="sb-title">AI SUMMARY</span>
            </div>
            <div class="ai-body">
              <p class="ai-overall">{{ aiSummary.overall }}</p>
              <ul class="ai-points" v-if="aiSummary.points?.length">
                <li v-for="(pt, i) in aiSummary.points" :key="i" class="ai-point">{{ pt }}</li>
              </ul>
              <div class="ai-price-change" v-if="aiSummary.price_change">
                <div class="ai-pc-item">
                  <span class="ai-pc-label mono">5D</span>
                  <span class="ai-pc-val mono" :class="aiSummary.price_change['5d'] >= 0 ? 'c-rise' : 'c-fall'">
                    {{ aiSummary.price_change['5d'] >= 0 ? '+' : '' }}{{ safeToFixed(aiSummary.price_change['5d'], 2) }}%
                  </span>
                </div>
                <div class="ai-pc-item">
                  <span class="ai-pc-label mono">20D</span>
                  <span class="ai-pc-val mono" :class="aiSummary.price_change['20d'] >= 0 ? 'c-rise' : 'c-fall'">
                    {{ aiSummary.price_change['20d'] >= 0 ? '+' : '' }}{{ safeToFixed(aiSummary.price_change['20d'], 2) }}%
                  </span>
                </div>
                <div class="ai-pc-item">
                  <span class="ai-pc-label mono">60D</span>
                  <span class="ai-pc-val mono" :class="aiSummary.price_change['60d'] >= 0 ? 'c-rise' : 'c-fall'">
                    {{ aiSummary.price_change['60d'] >= 0 ? '+' : '' }}{{ safeToFixed(aiSummary.price_change['60d'], 2) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="page-loading">
    <span class="loading-cursor">█</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
const CandlestickChart = defineAsyncComponent(() => import('@/components/chart/CandlestickChart.vue'))
import DataPanel from '@/components/ui/DataPanel.vue'
import MetricBlock from '@/components/ui/MetricBlock.vue'
import SignalBadge from '@/components/common/SignalBadge.vue'
import DataTable from '@/components/ui/DataTable.vue'
import { formatPrice, formatPct, formatNumber, formatVolume, strategyDisplayName, signalLabel, getMarketLabel, safeToFixed } from '@/utils/format'
import { useWatchlistStore } from '@/stores/watchlist'
import { useToast } from '@/composables/useToast'
import type { StockQuote, DeepAnalysis, SignalItem, AiSummary, Fundamentals, OrderDepth, CorrelationData } from '@/types'
import type { ColumnDef } from '@/components/ui/DataTable.vue'

const route = useRoute()
const router = useRouter()
const watchlistStore = useWatchlistStore()
const { toast } = useToast()
const log = createLogger('StockDetail')
const { handleApiError } = useApiError()
const { createSignal, cancelAll } = useRequestCancel()

const symbol = computed(() => (route.params.symbol as string) || '')

const quote = ref<StockQuote | null>(null)
const analysis = ref<DeepAnalysis | null>(null)
const signals = ref<SignalItem[]>([])
const aiSummary = ref<AiSummary | null>(null)
const fundamentals = ref<Fundamentals | null>(null)
const indicators = ref<Record<string, unknown> | null>(null)
const correlation = ref<CorrelationData | null>(null)
const depth = ref<OrderDepth | null>(null)

const klinePeriod = ref('1y')
const klineType = ref('daily')
const activeTab = ref('analysis')
const tradeFormOpen = ref(false)
const tradePrice = ref(0)
const tradeShares = ref(100)
const showTradeForm = ref(false)

const klineTypes = [
  { label: 'D', value: 'daily' },
  { label: 'W', value: 'weekly' },
  { label: 'M', value: 'monthly' },
]

const infoTabs = [
  { key: 'analysis', label: '深度分析' },
  { key: 'indicators', label: '技术指标' },
  { key: 'financial', label: '财务数据' },
  { key: 'ai', label: 'AI 摘要' },
  { key: 'backtest', label: '回测链接' },
  { key: 'related', label: '相关股票' },
]

const isInWatchlist = computed(() => watchlistStore.symbols.includes(symbol.value))

const trendLabel = computed(() => {
  if (!analysis.value) return '-'
  const map: Record<string, string> = { up: '上涨', down: '下跌', sideways: '震荡' }
  return map[analysis.value.trend.direction] || analysis.value.trend.direction
})

const trendDirection = computed<'rise' | 'fall' | 'neutral'>(() => {
  if (!analysis.value) return 'neutral'
  const d = analysis.value.trend.direction
  if (d === 'up') return 'rise'
  if (d === 'down') return 'fall'
  return 'neutral'
})

const signalDirection = computed<'rise' | 'fall' | 'neutral'>(() => {
  if (!analysis.value) return 'neutral'
  if (analysis.value.signal === 'buy' || analysis.value.signal === 'bullish') return 'rise'
  if (analysis.value.signal === 'sell' || analysis.value.signal === 'bearish') return 'fall'
  return 'neutral'
})

const maxQty = computed(() => {
  if (!depth.value) return 1
  const all = [...depth.value.bids, ...depth.value.asks].map(x => x.quantity)
  return Math.max(...all, 1)
})

const spread = computed(() => {
  if (!depth.value?.bids?.length || !depth.value?.asks?.length) return '-'
  return '价差 ' + safeToFixed(depth.value.asks[0].price - depth.value.bids[0].price, 2)
})

const relatedColumns: ColumnDef[] = [
  { key: 'symbol', label: '代码', width: '90px', code: true },
  { key: 'name', label: '名称', width: '120px' },
  { key: 'coefficient', label: '相关系数', width: '100px', align: 'right', format: (v: unknown) => safeToFixed(v, 3) },
]

async function toggleWatchlist(): Promise<void> {
  if (isInWatchlist.value) {
    await watchlistStore.removeSymbol(symbol.value)
  } else {
    await watchlistStore.addSymbol(symbol.value)
  }
}

async function fetchData(): Promise<void> {
  if (!symbol.value) return
  cancelAll()
  const signal = createSignal()

  try {
    const [rt, a, s, ai, f, ind, corr] = await Promise.allSettled([
      api.stock.realtime(symbol.value),
      api.stock.analysis(symbol.value, '1y'),
      api.stock.signals(symbol.value, '1y'),
      api.stock.aiSummary(symbol.value, '1y'),
      api.stock.fundamentals(symbol.value),
      api.stock.indicators(symbol.value, '1y', klineType.value),
      api.stock.correlation(symbol.value),
    ])

    if (rt.status === 'fulfilled') { quote.value = rt.value; tradePrice.value = rt.value.price }
    if (a.status === 'fulfilled') analysis.value = a.value
    if (s.status === 'fulfilled') signals.value = s.value?.signals ?? []
    if (ai.status === 'fulfilled') aiSummary.value = ai.value
    if (f.status === 'fulfilled') fundamentals.value = f.value
    if (ind.status === 'fulfilled') indicators.value = ind.value
    if (corr.status === 'fulfilled') correlation.value = corr.value
  } catch (err) {
    handleApiError(err, '获取股票数据失败')
  }
}

async function doBuy(): Promise<void> {
  if (!tradePrice.value || tradePrice.value <= 0) { toast('error', '请输入有效价格'); return }
  if (!tradeShares.value || tradeShares.value <= 0) { toast('error', '请输入有效数量'); return }
  try {
    await api.trading.buy({
      symbol: symbol.value,
      price: tradePrice.value,
      shares: tradeShares.value,
      name: quote.value?.name,
      market: quote.value?.market,
    })
    toast('success', `买入 ${symbol.value} ${tradeShares.value}股 @ ${tradePrice.value}`)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '买入失败'
    toast('error', msg)
  }
}

async function doSell(): Promise<void> {
  if (!tradePrice.value || tradePrice.value <= 0) { toast('error', '请输入有效价格'); return }
  if (!tradeShares.value || tradeShares.value <= 0) { toast('error', '请输入有效数量'); return }
  try {
    await api.trading.sell({
      symbol: symbol.value,
      price: tradePrice.value,
      shares: tradeShares.value,
    })
    toast('success', `卖出 ${symbol.value} ${tradeShares.value}股 @ ${tradePrice.value}`)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '卖出失败'
    toast('error', msg)
  }
}

function goToStock(sym: string): void {
  router.push(`/stock/${sym}`)
}

watch(symbol, fetchData)
onMounted(() => {
  fetchData()
  watchlistStore.fetchWatchlist()
})
onUnmounted(cancelAll)
</script>

<style scoped>
.bb-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-base);
}

.bb-ticker {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  gap: var(--u5);
  padding: 0 var(--u5);
  height: 52px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-hair);
  flex-shrink: 0;
}

.bb-ticker::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent), transparent);
  opacity: 0.3;
}

.tk-left {
  display: flex;
  align-items: baseline;
  gap: var(--u2);
  min-width: 160px;
}

.tk-name {
  font-size: var(--fs-md);
  font-weight: 600;
  color: var(--text-primary);
}

.tk-sym {
  font-size: var(--fs-sm);
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}

.tk-mkt {
  font-size: var(--fs-2xs);
  color: var(--text-tertiary);
  padding: 1px 5px;
  background: var(--bg-plate);
  border-radius: var(--r-xs);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: var(--font-mono);
}

.tk-price-group {
  display: flex;
  align-items: baseline;
  gap: var(--u3);
}

.tk-price {
  font-size: var(--fs-2xl);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.tk-chg {
  font-size: var(--fs-sm);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.c-rise { color: var(--rise); }
.c-fall { color: var(--fall); }

.tk-meta {
  display: flex;
  align-items: center;
  gap: var(--u3);
  flex: 1;
  justify-content: center;
}

.tk-meta-item {
  display: flex;
  align-items: baseline;
  gap: 3px;
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.tk-meta-label {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  letter-spacing: 0.06em;
}

.tk-meta-sep {
  width: 1px;
  height: 14px;
  background: var(--border-mid);
}

.tk-actions {
  display: flex;
  align-items: center;
  gap: var(--u2);
  margin-left: auto;
}

.tk-star {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: var(--text-muted);
  padding: 4px;
  line-height: 1;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.tk-star:hover { color: var(--warn); }
.tk-star.active { color: var(--warn); }

.tk-buy-btn {
  padding: var(--u1) var(--u4);
  background: var(--rise);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.tk-buy-btn:hover { opacity: 0.85; }

.bb-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.bb-chart-col {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.bb-chart-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  border-radius: 0;
  border-left: none;
  border-top: none;
  border-right: none;
  border-bottom: 1px solid var(--border-hair);
}

.chart-type-bar {
  position: absolute;
  top: 6px;
  left: 60px;
  z-index: 10;
  display: flex;
  gap: 2px;
  background: rgba(13, 13, 26, 0.85);
  border-radius: var(--r-xs);
  padding: 2px;
  border: 1px solid var(--border-hair);
}

.ct-btn {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: var(--fs-2xs);
  padding: 2px 8px;
  cursor: pointer;
  border-radius: var(--r-xs);
  transition: all var(--dur-fast) var(--ease-mechanical);
  letter-spacing: 0.06em;
  font-weight: 500;
}

.ct-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-plate);
}

.ct-btn.active {
  color: var(--accent);
  background: var(--accent-muted);
}

.bb-sidebar {
  flex-shrink: 0;
  border-left: 1px solid var(--border-hair);
  background: var(--bg-surface);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sb-panel {
  border-radius: 0;
  border-left: none;
  border-right: none;
  border-top: none;
}

.sb-panel + .sb-panel {
  border-top: 1px solid var(--border-hair);
}

.sb-head {
  display: flex;
  align-items: center;
  gap: var(--u2);
  padding: var(--u2) var(--u3);
  border-bottom: 1px solid var(--border-hair);
  position: relative;
}

.sb-head.clickable {
  cursor: pointer;
}

.sb-accent {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 16px;
  background: var(--accent);
  border-radius: 0 1px 1px 0;
}

.sb-title {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-tertiary);
}

.sb-count {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  margin-left: auto;
}

.sb-toggle {
  margin-left: auto;
  font-size: var(--fs-md);
  color: var(--text-muted);
  font-family: var(--font-mono);
}

.sb-body {
  padding: var(--u2) var(--u3);
}

.sb-empty {
  padding: var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sig-body {
  max-height: 240px;
  overflow-y: auto;
}

.sig-row {
  padding: var(--u1) 0;
  border-bottom: 1px solid var(--border-hair);
}

.sig-row:last-child {
  border-bottom: none;
}

.sig-top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 2px;
}

.sig-date {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.sig-price {
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
}

.sig-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.sig-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: var(--fs-2xs);
  padding: 1px 5px;
  border-radius: var(--r-xs);
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
}

.sig-badge.buy {
  background: var(--rise-bg);
  color: var(--rise);
}

.sig-badge.sell {
  background: var(--fall-bg);
  color: var(--fall);
}

.sig-marker {
  font-size: 8px;
  line-height: 1;
}

.sig-strat {
  font-size: var(--fs-2xs);
}

.sig-conf {
  font-size: var(--fs-2xs);
  opacity: 0.7;
}

.depth-asks,
.depth-bids {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.depth-row {
  display: flex;
  align-items: center;
  gap: var(--u2);
  padding: 1px 0;
  position: relative;
}

.depth-price {
  width: 56px;
  font-size: var(--fs-2xs);
  font-variant-numeric: tabular-nums;
}

.depth-qty {
  width: 44px;
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.depth-bar {
  position: absolute;
  right: 0;
  height: 14px;
  opacity: 0.12;
  border-radius: 1px;
}

.ask-bar { background: var(--fall); }
.bid-bar { background: var(--rise); }

.depth-spread-row {
  text-align: center;
  padding: 2px 0;
  border-top: 1px solid var(--border-hair);
  border-bottom: 1px solid var(--border-hair);
  margin: 2px 0;
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.trade-body {
  padding: var(--u3);
}

.trade-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--u2);
}

.trade-field label {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.trade-input {
  width: 100px;
  padding: var(--u1) var(--u2);
  background: var(--bg-void);
  border: 1px solid var(--border-mid);
  border-radius: var(--r-sm);
  color: var(--text-primary);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  outline: none;
  transition: border-color var(--dur-fast) var(--ease-mechanical);
}

.trade-input:focus {
  border-color: var(--accent);
}

.trade-btns {
  display: flex;
  gap: var(--u2);
  margin-top: var(--u2);
}

.trade-btn {
  flex: 1;
  padding: var(--u2);
  border: none;
  border-radius: var(--r-sm);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.trade-btn.buy {
  background: var(--rise);
  color: var(--text-inverse);
}

.trade-btn.sell {
  background: var(--fall);
  color: var(--text-inverse);
}

.trade-btn:hover {
  opacity: 0.85;
}

.bb-bottom {
  background: var(--bg-surface);
  border-top: 1px solid var(--border-hair);
  flex-shrink: 0;
}

.bb-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-hair);
  padding: 0 var(--u4);
}

.bb-tab {
  padding: var(--u2) var(--u4);
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  border-bottom: 2px solid transparent;
  transition: all var(--dur-fast) var(--ease-mechanical);
  cursor: pointer;
  background: none;
  border-top: none;
  border-left: none;
  border-right: none;
}

.bb-tab:hover {
  color: var(--text-secondary);
}

.bb-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.bb-tab-content {
  padding: var(--u4);
  min-height: 180px;
}

.tab-empty {
  text-align: center;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  padding: var(--u8) 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--u3);
}

.levels-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--u3);
  margin-top: var(--u4);
}

.level-list {
  display: flex;
  gap: var(--u2);
  flex-wrap: wrap;
}

.level-tag {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  padding: var(--u1) var(--u2);
  border-radius: var(--r-xs);
}

.level-tag.support {
  background: var(--fall-bg);
  color: var(--fall);
}

.level-tag.resistance {
  background: var(--rise-bg);
  color: var(--rise);
}

.fund-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--u3);
}

.ind-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--u3);
}

.ind-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--u2) var(--u3);
  background: var(--bg-plate);
  border-radius: var(--r-md);
}

.ind-key {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ind-val {
  font-size: var(--fs-sm);
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}

.tab-backtest {
  padding: var(--u8) var(--u4);
  text-align: center;
}

.backtest-link {
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.ai-panel {
  border-radius: var(--r-md);
}

.ai-body {
  padding: var(--u4);
}

.ai-overall {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  line-height: var(--lh-relaxed);
  margin-bottom: var(--u4);
}

.ai-points {
  list-style: none;
  padding: 0;
  margin: 0 0 var(--u4);
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.ai-point {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  padding-left: var(--u3);
  position: relative;
  line-height: var(--lh-normal);
}

.ai-point::before {
  content: '›';
  position: absolute;
  left: 0;
  color: var(--accent);
  font-family: var(--font-mono);
  font-weight: 700;
}

.ai-price-change {
  display: flex;
  gap: var(--u6);
  padding: var(--u3);
  background: var(--bg-plate);
  border-radius: var(--r-md);
}

.ai-pc-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.ai-pc-label {
  font-size: var(--fs-2xs);
  color: var(--text-muted);
  letter-spacing: 0.08em;
}

.ai-pc-val {
  font-size: var(--fs-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.page-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--bg-base);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.loading-cursor {
  animation: blink 1s step-end infinite;
  color: var(--accent);
  font-size: var(--fs-xl);
}

.mono {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1024px) {
  .tk-meta {
    display: none;
  }

  .bb-body {
    grid-template-columns: 1fr 240px;
  }
}

@media (max-width: 768px) {
  .bb-body {
    grid-template-columns: 1fr;
  }

  .bb-sidebar {
    display: none;
  }

  .tk-name {
    font-size: var(--fs-sm);
  }

  .tk-price {
    font-size: var(--fs-xl);
  }

  .analysis-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .fund-grid,
  .ind-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
