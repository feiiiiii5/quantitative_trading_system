<template>
  <div class="sr-root">
    <div class="sr-layout">
      <aside class="sr-sidebar">
        <section class="sr-sb-section">
          <div class="sr-sb-title">STRATEGY</div>
          <div class="sr-strat-list">
            <div
              v-for="(info, name) in store.strategies"
              :key="name"
              class="sr-strat-item"
              :class="{ 'sr-strat-active': strategyType === name }"
              @click="strategyType = name"
            >
              <div class="sr-strat-left">
                <span class="sr-strat-name">{{ strategyDisplayName(name) }}</span>
                <span class="sr-strat-type mono">{{ info.type }}</span>
              </div>
              <span class="sr-strat-diff" :class="diffClass(info.difficulty)">{{ diffLabel(info.difficulty) }}</span>
            </div>
            <div
              class="sr-strat-item"
              :class="{ 'sr-strat-active': strategyType === 'adaptive' }"
              @click="strategyType = 'adaptive'"
            >
              <div class="sr-strat-left">
                <span class="sr-strat-name">自适应量化引擎</span>
                <span class="sr-strat-type mono">adaptive</span>
              </div>
              <span class="sr-strat-diff expert">EXPERT</span>
            </div>
          </div>
        </section>

        <section class="sr-sb-section">
          <div class="sr-sb-title">PARAMETERS</div>
          <div class="sr-form">
            <div class="sr-field">
              <label class="sr-label">STOCK CODE</label>
              <input v-model="symbol" placeholder="e.g. 600519" class="sr-input mono" />
            </div>
            <div class="sr-field">
              <label class="sr-label">START DATE</label>
              <input v-model="startDate" type="date" class="sr-input" />
            </div>
            <div class="sr-field">
              <label class="sr-label">END DATE</label>
              <input v-model="endDate" type="date" class="sr-input" />
            </div>
            <div class="sr-field">
              <label class="sr-label">INITIAL CAPITAL</label>
              <input v-model.number="initialCapital" type="number" class="sr-input mono" />
            </div>
            <button class="sr-run-btn" :disabled="running" @click="runBacktest">
              <span v-if="running" class="sr-run-pulse"></span>
              {{ running ? 'RUNNING...' : '▶ RUN BACKTEST' }}
            </button>
          </div>
        </section>

        <section class="sr-sb-section" v-if="history.length">
          <div class="sr-sb-title sr-sb-title-click" @click="historyOpen = !historyOpen">
            HISTORY
            <span class="sr-sb-toggle">{{ historyOpen ? '−' : '+' }}</span>
          </div>
          <div class="sr-history" v-show="historyOpen">
            <div v-for="(h, i) in history.slice(0, 10)" :key="i" class="sr-hist-item" @click="loadHistory(h)">
              <div class="sr-hist-top">
                <span class="sr-hist-strat">{{ strategyDisplayName(h.strategy_name || h.strategy_type) }}</span>
                <span class="sr-hist-sym mono">{{ h.symbol }}</span>
              </div>
              <div class="sr-hist-bot">
                <span class="mono" :class="(h.total_return ?? 0) >= 0 ? 'text-rise' : 'text-fall'">
                  {{ formatPct(h.total_return ?? 0) }}
                </span>
                <span class="sr-hist-sharpe mono">Sharpe {{ safeToFixed(h.sharpe_ratio, 2) }}</span>
              </div>
            </div>
          </div>
        </section>
      </aside>

      <main class="sr-main">
        <div v-if="runState === 'waiting'" class="sr-waiting">
          <pre class="sr-ascii">┌─────────────────────────────────────────┐
│  ╔═╗╔═╗╔═╗╦═╗╔╦╗ QUANTCORE            │
│  ║  ║ ║╠═╝╠╦╝ ║   BACKTEST ENGINE      │
│  ╚═╝╚═╝╩  ╩╚═ ╩   v3.2.1               │
│─────────────────────────────────────────│
│                                         │
│  STATUS: IDLE                           │
│  SELECT STRATEGY → CONFIGURE → RUN      │
│                                         │
│  > _                                    │
└─────────────────────────────────────────┘</pre>
          <div class="sr-waiting-hint">
            <span class="sr-blink">█</span> Select a strategy and click RUN BACKTEST
          </div>
        </div>

        <div v-else-if="runState === 'running'" class="sr-running">
          <div class="sr-term-bar">
            <div class="sr-term-dots">
              <span class="sr-dot sr-dot-red"></span>
              <span class="sr-dot sr-dot-yel"></span>
              <span class="sr-dot sr-dot-grn"></span>
            </div>
            <span class="sr-term-title mono">quantcore-backtest — {{ strategyType }}</span>
            <span class="sr-term-status mono">RUNNING</span>
          </div>
          <div class="sr-term-body" ref="terminalBody">
            <div v-for="(line, i) in terminalLines" :key="i" class="sr-term-line mono">
              <span class="sr-term-prompt">$</span> {{ line }}
            </div>
            <div class="sr-term-line mono sr-term-active">
              <span class="sr-term-prompt">$</span> <span class="sr-blink">█</span>
            </div>
          </div>
        </div>

        <div v-else-if="runState === 'results' && result" class="sr-results">
          <div class="sr-tabs">
            <button
              v-for="tab in resultTabs"
              :key="tab.key"
              class="sr-tab"
              :class="{ 'sr-tab-active': activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>

          <div v-if="activeTab === 'overview'" class="sr-tab-body">
            <div class="sr-telegram">
              <div class="sr-tg-col">
                <div class="sr-tg-row">
                  <span class="sr-tg-label">TOTAL RETURN</span>
                  <span class="sr-tg-val mono" :class="result.total_return >= 0 ? 'text-rise' : 'text-fall'">
                    {{ formatPct(result.total_return) }}
                  </span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">ANNUAL RETURN</span>
                  <span class="sr-tg-val mono" :class="(result.annual_return ?? 0) >= 0 ? 'text-rise' : 'text-fall'">
                    {{ formatPct(result.annual_return ?? 0) }}
                  </span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">SHARPE RATIO</span>
                  <span class="sr-tg-val mono">{{ safeToFixed(result.sharpe_ratio, 2) }}</span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">MAX DRAWDOWN</span>
                  <span class="sr-tg-val mono text-fall">{{ formatPct(result.max_drawdown ?? 0) }}</span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">WIN RATE</span>
                  <span class="sr-tg-val mono">{{ safeToFixed(result.win_rate, 1) }}%</span>
                </div>
              </div>
              <div class="sr-tg-sep"></div>
              <div class="sr-tg-col">
                <div class="sr-tg-row">
                  <span class="sr-tg-label">TOTAL TRADES</span>
                  <span class="sr-tg-val mono">{{ result.total_trades }}</span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">PROFIT FACTOR</span>
                  <span class="sr-tg-val mono">{{ safeToFixed(result.profit_factor, 2) }}</span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">ALPHA</span>
                  <span class="sr-tg-val mono" :class="(result.alpha ?? 0) >= 0 ? 'text-rise' : 'text-fall'">
                    {{ formatPct(result.alpha ?? 0) }}
                  </span>
                </div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">BETA</span>
                  <span class="sr-tg-val mono">{{ safeToFixed(result.beta, 3) }}</span>
                </div>
                <div class="sr-tg-divider"></div>
                <div class="sr-tg-row">
                  <span class="sr-tg-label">VS BENCHMARK</span>
                  <span class="sr-tg-val mono" :class="(result.benchmark_return ?? 0) >= 0 ? 'text-rise' : 'text-fall'">
                    {{ formatPct(result.benchmark_return ?? 0) }}
                  </span>
                </div>
              </div>
            </div>

            <DataPanel title="EQUITY CURVE">
              <BaseChart v-if="equityOption" :option="equityOption" height="280px" />
            </DataPanel>

            <DataPanel title="DRAWDOWN" style="margin-top: var(--u3)">
              <BaseChart v-if="drawdownOption" :option="drawdownOption" height="180px" />
            </DataPanel>
          </div>

          <div v-if="activeTab === 'trades'" class="sr-tab-body">
            <DataPanel title="TRADE DETAILS" v-if="result.trades?.length">
              <DataTable :columns="tradeColumns" :rows="tradeRows" row-key="idx" toolbar exportable export-filename="trade-details">
                <template #cell-action="{ row }">
                  <span class="sr-action-badge" :class="row.action === 'buy' ? 'buy' : 'sell'">
                    {{ row.action === 'buy' ? 'BUY' : 'SELL' }}
                  </span>
                </template>
                <template #cell-pnl="{ row }">
                  <span class="mono" :class="Number(row.pnl || 0) >= 0 ? 'text-rise' : 'text-fall'">
                    {{ safeToFixed(row.pnl, 2) }}
                  </span>
                </template>
              </DataTable>
            </DataPanel>
          </div>

          <div v-if="activeTab === 'risk'" class="sr-tab-body">
            <DataPanel title="RISK METRICS">
              <div class="sr-risk-grid">
                <MetricBlock :value="safeToFixed(result.var_95, 4)" label="VaR(95%)" direction="neutral" />
                <MetricBlock :value="safeToFixed(result.cvar_95, 4)" label="CVaR(95%)" direction="neutral" />
                <MetricBlock :value="safeToFixed((result.volatility ?? result.annual_volatility ?? 0) * 100, 2) + '%'" label="Volatility" direction="neutral" />
                <MetricBlock :value="safeToFixed(result.downside_deviation, 4)" label="Downside Dev" direction="neutral" />
                <MetricBlock :value="safeToFixed(result.information_ratio, 3)" label="Info Ratio" direction="neutral" />
                <MetricBlock :value="safeToFixed(result.tail_ratio, 3)" label="Tail Ratio" direction="neutral" />
                <MetricBlock v-if="result.sortino_ratio" :value="safeToFixed(result.sortino_ratio, 3)" label="Sortino" direction="neutral" />
                <MetricBlock v-if="result.calmar_ratio" :value="safeToFixed(result.calmar_ratio, 3)" label="Calmar" direction="neutral" />
                <MetricBlock v-if="result.omega_ratio" :value="safeToFixed(result.omega_ratio, 3)" label="Omega" direction="neutral" />
              </div>
            </DataPanel>
          </div>

          <div v-if="activeTab === 'montecarlo'" class="sr-tab-body">
            <DataPanel title="MONTE CARLO SIMULATION">
              <div v-if="mcResult" class="sr-mc-content">
                <div class="sr-mc-summary">
                  <MetricBlock :value="formatPct(mcResult.median_return ?? 0)" label="Median Return" :direction="(mcResult.median_return ?? 0) >= 0 ? 'rise' : 'fall'" />
                  <MetricBlock :value="formatPct(mcResult.p5_return ?? 0)" label="5th Percentile" direction="fall" />
                  <MetricBlock :value="formatPct(mcResult.p95_return ?? 0)" label="95th Percentile" direction="rise" />
                  <MetricBlock :value="safeToFixed((mcResult.ruin_prob ?? 0) * 100, 1) + '%'" label="Ruin Probability" :direction="(mcResult.ruin_prob ?? 0) > 0.05 ? 'fall' : 'neutral'" />
                </div>
                <BaseChart v-if="mcOption" :option="mcOption" height="250px" />
              </div>
              <div v-else class="sr-panel-cta">
                <button class="sr-cta-btn" @click="runMonteCarlo" :disabled="mcRunning">
                  {{ mcRunning ? 'SIMULATING...' : '▶ RUN MONTE CARLO' }}
                </button>
              </div>
            </DataPanel>
          </div>

          <div v-if="activeTab === 'sensitivity'" class="sr-tab-body">
            <DataPanel title="PARAMETER SENSITIVITY">
              <div v-if="sensitivityResult" class="sr-sens-content">
                <div class="sr-sens-grid">
                  <div v-for="item in sensitivityResult" :key="item.param" class="sr-sens-item">
                    <div class="sr-sens-param mono">{{ item.param }}</div>
                    <div class="sr-sens-range mono">{{ item.min ?? '-' }} → {{ item.max ?? '-' }}</div>
                    <div class="sr-sens-impact mono" :class="(item.impact ?? 0) > 0 ? 'text-rise' : 'text-fall'">
                      Impact {{ safeToFixed((item.impact ?? 0) * 100, 1) }}%
                    </div>
                  </div>
                </div>
                <BaseChart v-if="sensChartOption" :option="sensChartOption" height="260px" />
              </div>
              <div v-else class="sr-panel-cta">
                <button class="sr-cta-btn" @click="runSensitivity" :disabled="sensRunning">
                  {{ sensRunning ? 'ANALYZING...' : '▶ RUN SENSITIVITY' }}
                </button>
              </div>
            </DataPanel>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useBacktestStore } from '@/stores/backtest'
import { api } from '@/api'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))
import DataPanel from '@/components/ui/DataPanel.vue'
import MetricBlock from '@/components/ui/MetricBlock.vue'
import DataTable from '@/components/ui/DataTable.vue'
import { strategyDisplayName, formatPct, formatNumber, safeToFixed } from '@/utils/format'
import type { BacktestResult, BacktestHistoryItem, MonteCarloResult, SensitivityItem } from '@/types'
import type { ColumnDef } from '@/components/ui/DataTable.vue'

const log = createLogger('Backtest')
const { handleApiError } = useApiError()
const { cancelAll } = useRequestCancel()

const route = useRoute()
const store = useBacktestStore()

const symbol = ref((route.query.symbol as string) || '600519')
const strategyType = ref((route.query.strategy as string) || 'adaptive')
const startDate = ref('2024-01-01')
const endDate = ref('2025-12-31')
const initialCapital = ref(1000000)
const historyOpen = ref(true)

const runState = ref<'waiting' | 'running' | 'results'>('waiting')
const running = ref(false)
const result = ref<BacktestResult | null>(null)
const history = ref<BacktestHistoryItem[]>([])
const activeTab = ref('overview')

const mcResult = ref<MonteCarloResult | null>(null)
const mcRunning = ref(false)
const sensitivityResult = ref<SensitivityItem[] | null>(null)
const sensRunning = ref(false)

const terminalLines = ref<string[]>([])
const terminalBody = ref<HTMLElement>()
let terminalTimer: ReturnType<typeof setInterval> | null = null
let resetTimer: ReturnType<typeof setTimeout> | null = null

const MC_DEFAULT_SIMULATIONS = 500
const RESET_DELAY_MS = 2_000

const resultTabs = [
  { key: 'overview', label: '概览' },
  { key: 'trades', label: '交易明细' },
  { key: 'risk', label: '风险分析' },
  { key: 'montecarlo', label: '蒙特卡洛' },
  { key: 'sensitivity', label: '参数优化' },
]

const terminalOutputPool = [
  'Loading historical data...',
  'Parsing OHLCV records...',
  'Initializing strategy engine...',
  'Computing technical indicators...',
  'Running signal detection...',
  'Generating trade signals...',
  'Simulating order execution...',
  'Applying slippage model...',
  'Calculating P&L per trade...',
  'Building equity curve...',
  'Computing risk metrics...',
  'VaR analysis complete.',
  'Sharpe ratio computed.',
  'Max drawdown identified.',
  'Win rate calculated.',
  'Backtest iteration complete.',
  'Aggregating results...',
  'Finalizing report...',
]

const DIFF_MAP: Record<string, { cls: string; label: string }> = {
  beginner: { cls: 'basic', label: 'BASIC' },
  intermediate: { cls: 'pro', label: 'PRO' },
  advanced: { cls: 'expert', label: 'EXPERT' },
  BASIC: { cls: 'basic', label: 'BASIC' },
  PRO: { cls: 'pro', label: 'PRO' },
  EXPERT: { cls: 'expert', label: 'EXPERT' },
}

function diffClass(d?: string): string {
  return DIFF_MAP[d || 'BASIC']?.cls ?? 'basic'
}

function diffLabel(d?: string): string {
  return DIFF_MAP[d || 'BASIC']?.label ?? 'BASIC'
}

const tradeColumns: ColumnDef[] = [
  { key: 'idx', label: '#', width: '40px', align: 'right' },
  { key: 'date', label: 'Date', width: '100px' },
  { key: 'action', label: 'Action', width: '60px' },
  { key: 'price', label: 'Price', width: '80px', align: 'right', format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'shares', label: 'Shares', width: '70px', align: 'right' },
  { key: 'amount', label: 'Amount', width: '90px', align: 'right', format: (v: unknown) => v != null ? formatNumber(v as number, 0) : '-' },
  { key: 'fee', label: 'Fee', width: '70px', align: 'right', format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'pnl', label: 'P&L', width: '90px', align: 'right' },
  { key: 'hold_days', label: 'Hold', width: '50px', align: 'right' },
  { key: 'reason', label: 'Reason' },
]

const tradeRows = computed(() => {
  if (!result.value?.trades) return []
  return result.value.trades.map((t, i) => ({
    idx: i + 1,
    date: (t.date || t.entry_date || '').slice(0, 10),
    action: t.action || (t.direction === 'long' ? 'buy' : 'sell'),
    price: t.price || t.entry_price || 0,
    shares: t.shares || '-',
    amount: t.amount,
    fee: t.fee,
    pnl: t.pnl,
    hold_days: t.hold_days ?? '-',
    reason: t.reason || '-',
  }))
})

const equityOption = computed(() => {
  if (!result.value?.equity_curve?.length) return null
  const curve = result.value.equity_curve
  const benchmarkCurve = result.value.benchmark_curve
  const series: Record<string, unknown>[] = [
    {
      type: 'line',
      name: 'Strategy',
      data: curve.map((p: { value: number }) => p.value),
      smooth: true,
      lineStyle: { color: '#2979ff', width: 1.5 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(41, 121, 255, 0.15)' },
            { offset: 1, color: 'rgba(41, 121, 255, 0)' },
          ],
        },
      },
      itemStyle: { opacity: 0 },
    },
  ]
  const legendData = ['Strategy']
  if (benchmarkCurve?.length) {
    series.push({
      type: 'line',
      name: 'Benchmark',
      data: benchmarkCurve.map((p: { value: number }) => p.value),
      smooth: true,
      lineStyle: { color: '#555568', width: 1, type: 'dashed' },
      itemStyle: { opacity: 0 },
    })
    legendData.push('Benchmark')
  }
  return {
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { data: legendData, top: 0, textStyle: { color: '#9898b0', fontSize: 10 } },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: curve.map((p: { date?: string }) => p.date?.slice(0, 10)), axisLabel: { fontSize: 10, color: '#555568' } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } }, axisLabel: { fontSize: 10, color: '#555568' } },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series,
  }
})

const drawdownOption = computed(() => {
  if (!result.value?.equity_curve?.length) return null
  const curve = result.value.equity_curve
  const values = curve.map((p: { value: number }) => p.value)
  const peak = values.reduce((acc: number[], v: number) => {
    acc.push(Math.max(acc.length ? acc[acc.length - 1] : v, v))
    return acc
  }, [] as number[])
  const dd = values.map((v: number, i: number) => ((v - peak[i]) / peak[i] * 100))
  return {
    animation: false,
    tooltip: { trigger: 'axis', formatter: (p: { axisValue: string; value: number }[]) => `${p[0].axisValue}<br/>Drawdown: ${safeToFixed(p[0].value, 2)}%` },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: curve.map((p: { date?: string }) => p.date?.slice(0, 10)), axisLabel: { fontSize: 10, color: '#555568' } },
    yAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#555568', formatter: '{value}%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } } },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [{
      type: 'line', data: dd, lineStyle: { color: '#ff3b3b', width: 1 },
      areaStyle: { color: 'rgba(255, 59, 59, 0.1)' }, itemStyle: { opacity: 0 },
    }],
  }
})

const mcOption = computed(() => {
  if (!mcResult.value?.paths?.length) return null
  const paths = mcResult.value.paths.slice(0, 50)
  return {
    animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: paths[0]?.map((_: number, i: number) => i) || [], axisLabel: { show: false } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } }, axisLabel: { fontSize: 10, color: '#555568' } },
    series: paths.map((path: number[]) => ({
      type: 'line', data: path, smooth: true, showSymbol: false,
      lineStyle: { width: 0.5, color: 'rgba(41, 121, 255, 0.2)' }, itemStyle: { opacity: 0 },
    })),
  }
})

const sensChartOption = computed(() => {
  if (!sensitivityResult.value?.length) return null
  const items = sensitivityResult.value
  const params = items.map(i => i.param)
  const sharpes = items.map(i => i.sharpe_ratio)
  const returns = items.map(i => (i.total_return ?? 0) * 100)
  const impacts = items.map(i => (i.impact ?? 0) * 100)
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13, 13, 26, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#f0f0f8', fontSize: 12 },
    },
    legend: { data: ['Sharpe', 'Return%', 'Impact%'], top: 0, textStyle: { color: '#9898b0', fontSize: 10 } },
    grid: { left: 50, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: params, axisLabel: { fontSize: 10, color: '#555568' } },
    yAxis: [
      { type: 'value', name: 'Sharpe', axisLabel: { fontSize: 10, color: '#555568' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } } },
      { type: 'value', name: '%', axisLabel: { fontSize: 10, color: '#555568' }, splitLine: { show: false } },
    ],
    series: [
      { name: 'Sharpe', type: 'bar', data: sharpes, itemStyle: { color: '#2979ff' }, barMaxWidth: 30 },
      { name: 'Return%', type: 'bar', data: returns, yAxisIndex: 1, itemStyle: { color: '#00e676' }, barMaxWidth: 30 },
      { name: 'Impact%', type: 'line', data: impacts, yAxisIndex: 1, smooth: true, lineStyle: { color: '#ffd600', width: 2 }, itemStyle: { color: '#ffd600' }, symbol: 'circle', symbolSize: 6 },
    ],
  }
})

async function runBacktest() {
  if (!symbol.value) return
  running.value = true
  runState.value = 'running'
  result.value = null
  mcResult.value = null
  sensitivityResult.value = null
  activeTab.value = 'overview'
  terminalLines.value = []

  let lineIdx = 0
  terminalTimer = setInterval(() => {
    if (lineIdx < terminalOutputPool.length) {
      const now = new Date()
      const ts = [now.getHours(), now.getMinutes(), now.getSeconds()].map(n => String(n).padStart(2, '0')).join(':')
      terminalLines.value.push(`[${ts}] ${terminalOutputPool[lineIdx]}`)
      lineIdx++
      nextTick(() => {
        if (terminalBody.value) {
          terminalBody.value.scrollTop = terminalBody.value.scrollHeight
        }
      })
    }
  }, 100)

  try {
    const res = await api.backtest.run({
      symbol: symbol.value,
      strategy_type: strategyType.value,
      start_date: startDate.value,
      end_date: endDate.value,
      initial_capital: initialCapital.value,
    })

    if (terminalTimer) { clearInterval(terminalTimer); terminalTimer = null }

    const now = new Date()
    const ts = [now.getHours(), now.getMinutes(), now.getSeconds()].map(n => String(n).padStart(2, '0')).join(':')
    terminalLines.value.push(`[${ts}] ${res.total_trades} trades found. Computing metrics...`)
    await new Promise(r => setTimeout(r, 300))

    result.value = res
    runState.value = 'results'

    if (res) {
      history.value.unshift({
        symbol: symbol.value,
        strategy_type: strategyType.value,
        strategy_name: strategyType.value,
        total_return: res.total_return,
        sharpe_ratio: res.sharpe_ratio,
        result: res,
      })
      if (history.value.length > 20) history.value = history.value.slice(0, 20)
    }
  } catch (e: unknown) {
    if (terminalTimer) { clearInterval(terminalTimer); terminalTimer = null }
    terminalLines.value.push('ERROR: ' + (e instanceof Error ? e.message : String(e)))
    terminalLines.value.push('Backtest failed. Check parameters and retry.')
    if (resetTimer) clearTimeout(resetTimer)
    resetTimer = setTimeout(() => { runState.value = 'waiting' }, RESET_DELAY_MS)
  } finally {
    running.value = false
  }
}

async function runMonteCarlo() {
  if (!result.value) return
  mcRunning.value = true
  try {
    const res = await api.backtest.advanced({
      symbol: symbol.value,
      strategy_type: strategyType.value,
      start_date: startDate.value,
      end_date: endDate.value,
      initial_capital: initialCapital.value,
      monte_carlo: true,
      n_simulations: MC_DEFAULT_SIMULATIONS,
    })
    mcResult.value = (res?.monte_carlo as unknown as MonteCarloResult) || null
  } catch (err) {
    log.warn('Monte Carlo simulation failed', err)
    mcResult.value = null
  } finally {
    mcRunning.value = false
  }
}

async function runSensitivity() {
  if (!result.value) return
  sensRunning.value = true
  try {
    const res = await api.backtest.advanced({
      symbol: symbol.value,
      strategy_type: strategyType.value,
      start_date: startDate.value,
      end_date: endDate.value,
      initial_capital: initialCapital.value,
      sensitivity: true,
    })
    sensitivityResult.value = (res?.sensitivity as SensitivityItem[]) || null
  } catch (err) {
    log.warn('Sensitivity analysis failed', err)
    sensitivityResult.value = null
  } finally {
    sensRunning.value = false
  }
}

function loadHistory(h: { result: BacktestResult }) {
  result.value = h.result
  runState.value = 'results'
  activeTab.value = 'overview'
}

onMounted(async () => {
  if (!Object.keys(store.strategies).length) {
    await store.fetchStrategies()
  }
  try {
    history.value = await api.backtest.history(symbol.value, 20)
  } catch (err) {
    handleApiError(err, '获取回测历史失败')
    history.value = []
  }
})

onUnmounted(() => {
  cancelAll()
  if (terminalTimer) { clearInterval(terminalTimer); terminalTimer = null }
  if (resetTimer) { clearTimeout(resetTimer); resetTimer = null }
})
</script>

<style scoped>
.sr-root {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.sr-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.sr-sidebar {
  width: 280px;
  flex-shrink: 0;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-hair);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.sr-sb-section {
  border-bottom: 1px solid var(--border-hair);
}

.sr-sb-title {
  padding: var(--u3) var(--u4);
  font-size: var(--fs-xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  border-bottom: 1px solid var(--border-hair);
}

.sr-sb-title-click {
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sr-sb-toggle {
  font-size: var(--fs-md);
  color: var(--text-tertiary);
}

.sr-strat-list {
  max-height: 320px;
  overflow-y: auto;
}

.sr-strat-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u2) var(--u4);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
  border-left: 3px solid transparent;
}

.sr-strat-item:hover {
  background: var(--bg-raised);
}

.sr-strat-active {
  background: var(--accent-muted);
  border-left-color: var(--accent);
}

.sr-strat-left {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.sr-strat-name {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sr-strat-active .sr-strat-name {
  color: var(--accent);
}

.sr-strat-type {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.sr-strat-diff {
  font-size: 9px;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 1px 5px;
  border-radius: var(--r-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.sr-strat-diff.basic {
  background: var(--fall-bg);
  color: var(--fall);
}

.sr-strat-diff.pro {
  background: var(--warn-bg);
  color: var(--warn);
}

.sr-strat-diff.expert {
  background: var(--rise-bg);
  color: var(--rise);
}

.sr-form {
  padding: var(--u4);
}

.sr-field {
  margin-bottom: var(--u3);
}

.sr-label {
  display: block;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-bottom: var(--u1);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sr-input {
  width: 100%;
  padding: var(--u2) var(--u3);
  background: var(--bg-void);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  outline: none;
  font-family: inherit;
  font-variant-numeric: tabular-nums;
}

.sr-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-muted);
}

.sr-run-btn {
  width: 100%;
  height: 48px;
  background: var(--accent);
  color: #ffffff;
  border: none;
  border-radius: var(--r-md);
  font-size: var(--fs-sm);
  font-weight: 600;
  cursor: pointer;
  font-family: var(--font-mono);
  letter-spacing: 0.08em;
  transition: opacity var(--dur-fast) var(--ease-mechanical);
  margin-top: var(--u2);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--u2);
}

.sr-run-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}

.sr-run-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sr-run-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  animation: sr-pulse 800ms ease-in-out infinite;
}

@keyframes sr-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.7); }
}

.sr-history {
  max-height: 300px;
  overflow-y: auto;
}

.sr-hist-item {
  padding: var(--u2) var(--u4);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical);
  border-bottom: 1px solid var(--border-hair);
}

.sr-hist-item:hover {
  background: var(--bg-raised);
}

.sr-hist-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 2px;
}

.sr-hist-strat {
  font-size: var(--fs-sm);
  color: var(--text-primary);
}

.sr-hist-sym {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
}

.sr-hist-bot {
  display: flex;
  justify-content: space-between;
  font-size: var(--fs-xs);
}

.sr-hist-sharpe {
  color: var(--text-tertiary);
}

.sr-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: var(--bg-base);
}

.sr-waiting {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--u8);
}

.sr-ascii {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  color: var(--text-muted);
  line-height: 1.5;
  text-align: center;
  white-space: pre;
  text-shadow: 0 0 8px rgba(41, 121, 255, 0.15);
}

.sr-waiting-hint {
  margin-top: var(--u6);
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
}

.sr-blink {
  animation: sr-blink 350ms step-end infinite;
}

@keyframes sr-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.sr-running {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sr-term-bar {
  display: flex;
  align-items: center;
  gap: var(--u2);
  padding: var(--u2) var(--u4);
  background: var(--bg-plate);
  border-bottom: 1px solid var(--border-hair);
}

.sr-term-dots {
  display: flex;
  gap: 6px;
}

.sr-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.sr-dot-red { background: var(--rise); }
.sr-dot-yel { background: var(--warn); }
.sr-dot-grn { background: var(--teal); }

.sr-term-title {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  flex: 1;
}

.sr-term-status {
  font-size: var(--fs-2xs);
  color: var(--teal);
  letter-spacing: 0.08em;
  animation: sr-blink 1.5s ease-in-out infinite;
}

.sr-term-body {
  flex: 1;
  padding: var(--u4);
  overflow-y: auto;
  background: var(--bg-void);
  font-size: var(--fs-sm);
}

.sr-term-line {
  padding: 1px 0;
  color: var(--text-secondary);
}

.sr-term-prompt {
  color: var(--accent);
  margin-right: var(--u2);
}

.sr-term-active {
  color: var(--text-primary);
}

.sr-results {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sr-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border-hair);
  position: relative;
  overflow-x: auto;
  white-space: nowrap;
  flex-shrink: 0;
}

.sr-tab {
  padding: var(--u2) var(--u6);
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: var(--fs-sm);
  font-weight: 500;
  font-family: var(--font-mono);
  cursor: pointer;
  position: relative;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.sr-tab::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--accent);
  transform: scaleX(0);
  will-change: transform;
  transition: transform var(--dur-fast) var(--ease-mechanical);
}

.sr-tab:hover {
  color: var(--text-primary);
}

.sr-tab-active {
  color: var(--accent);
}

.sr-tab-active::after {
  transform: scaleX(1);
}

.sr-tab-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--u4);
}

.sr-telegram {
  display: flex;
  background: var(--bg-surface);
  border: 1px solid var(--border-hair);
  border-radius: var(--r-md);
  overflow: hidden;
  margin-bottom: var(--u4);
}

.sr-tg-col {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.sr-tg-sep {
  width: 1px;
  background: var(--accent);
  opacity: 0.2;
}

.sr-tg-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.sr-tg-row:last-child {
  border-bottom: none;
}

.sr-tg-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sr-tg-val {
  font-size: var(--fs-md);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sr-tg-divider {
  height: 1px;
  background: var(--accent);
  opacity: 0.3;
  margin: 0 var(--u4);
}

.sr-risk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--u4);
}

.sr-mc-content {
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

.sr-mc-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--u4);
}

.sr-sens-content {
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

.sr-sens-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--u4);
}

.sr-sens-item {
  padding: var(--u3);
  background: var(--bg-plate);
  border-radius: var(--r-md);
  border-left: 2px solid var(--accent);
}

.sr-sens-param {
  font-size: var(--fs-sm);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--u1);
}

.sr-sens-range {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  margin-bottom: 2px;
}

.sr-sens-impact {
  font-size: var(--fs-xs);
}

.sr-panel-cta {
  display: flex;
  justify-content: center;
  padding: var(--u6) 0;
}

.sr-cta-btn {
  padding: var(--u2) var(--u6);
  background: var(--bg-raised);
  border: 1px solid var(--accent);
  border-radius: var(--r-md);
  color: var(--accent);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.sr-cta-btn:hover:not(:disabled) {
  background: var(--accent-muted);
}

.sr-cta-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sr-action-badge {
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 1px 6px;
  border-radius: var(--r-xs);
}

.sr-action-badge.buy {
  background: var(--rise-bg);
  color: var(--rise);
}

.sr-action-badge.sell {
  background: var(--fall-bg);
  color: var(--fall);
}

.text-rise { color: var(--rise); }
.text-fall { color: var(--fall); }
.mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

@media (max-width: 1024px) {
  .sr-root { flex-direction: column; }
  .sr-sidebar { width: 100%; max-height: 300px; border-right: none; border-bottom: 1px solid var(--border-hair); }
}
</style>
