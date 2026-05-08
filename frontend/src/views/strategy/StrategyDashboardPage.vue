<template>
  <div class="sd-root">
    <header class="sd-header">
      <div class="sd-header-row">
        <div class="sd-header-left">
          <h1 class="sd-title">STRATEGY DASHBOARD</h1>
          <span class="sd-subtitle">Performance overview across all strategies for a selected stock</span>
        </div>
        <router-link to="/strategy/run" class="sd-nav-btn">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5,3 19,12 5,21"/></svg>
          RUN BACKTEST
        </router-link>
      </div>
    </header>

    <div class="sd-controls surface-panel">
      <div class="sd-ctrl-field">
        <label class="sd-ctrl-label">STOCK CODE</label>
        <input v-model="symbol" class="sd-ctrl-input mono" placeholder="e.g. 600519" @keydown.enter="fetchData" />
      </div>
      <div class="sd-ctrl-field">
        <label class="sd-ctrl-label">PERIOD</label>
        <select v-model="period" class="sd-ctrl-input" @change="fetchData">
          <option value="3m">3M</option>
          <option value="6m">6M</option>
          <option value="1y">1Y</option>
          <option value="2y">2Y</option>
          <option value="3y">3Y</option>
        </select>
      </div>
      <button class="sd-ctrl-btn" :disabled="loading" @click="fetchData">
        {{ loading ? 'ANALYZING...' : '▶ ANALYZE' }}
      </button>
    </div>

    <div v-if="loading" class="sd-loading">
      <div class="sd-spinner"></div>
      <span class="mono">Running all strategy backtests...</span>
    </div>

    <div v-else-if="error" class="sd-error">
      <span class="mono">{{ error }}</span>
    </div>

    <div v-else-if="data" class="sd-content">
      <div class="sd-summary">
        <div class="sd-best surface-panel">
          <div class="sd-best-badge">★ BEST STRATEGY</div>
          <div class="sd-best-name mono">{{ strategyDisplayName(data.best_strategy?.strategy ?? '-') }}</div>
          <div class="sd-best-metrics">
            <div class="sd-best-metric">
              <span class="sd-best-label">RETURN</span>
              <span class="sd-best-val mono" :class="(data.best_strategy?.total_return ?? 0) >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatPct(data.best_strategy?.total_return ?? 0) }}
              </span>
            </div>
            <div class="sd-best-metric">
              <span class="sd-best-label">SHARPE</span>
              <span class="sd-best-val mono">{{ safeToFixed(data.best_strategy?.sharpe_ratio, 2) || '-' }}</span>
            </div>
            <div class="sd-best-metric">
              <span class="sd-best-label">MAX DD</span>
              <span class="sd-best-val mono text-fall">{{ formatPct(data.best_strategy?.max_drawdown ?? 0) }}</span>
            </div>
          </div>
        </div>

        <div class="sd-stats">
          <MetricBlock :value="String(data.strategy_count)" label="Strategies Tested" direction="neutral" />
          <MetricBlock :value="formatPct(data.average_return)" label="Average Return" :direction="data.average_return >= 0 ? 'rise' : 'fall'" />
          <MetricBlock :value="safeToFixed(data.average_sharpe, 2)" label="Average Sharpe" direction="neutral" />
          <MetricBlock :value="formatPct(data.benchmark.total_return)" label="Benchmark Return" :direction="data.benchmark.total_return >= 0 ? 'rise' : 'fall'" />
        </div>
      </div>

      <DataPanel title="STRATEGY COMPARISON">
        <template #header-actions>
          <button class="sd-export-btn" :disabled="!compareRows.length" @click="exportComparison">
            ⤓ EXPORT CSV
          </button>
        </template>
        <DataTable :columns="compareColumns" :rows="compareRows" row-key="strategy" toolbar exportable export-filename="strategy-compare">
          <template #cell-strategy="{ row }">
            <span class="mono sd-strat-link">{{ strategyDisplayName(row.strategy as string) }}</span>
          </template>
          <template #cell-total_return="{ row }">
            <span class="mono" :class="(row.total_return as number) >= 0 ? 'text-rise' : 'text-fall'">
              {{ formatPct(row.total_return as number) }}
            </span>
          </template>
          <template #cell-annual_return="{ row }">
            <span class="mono" :class="(row.annual_return as number) >= 0 ? 'text-rise' : 'text-fall'">
              {{ formatPct(row.annual_return as number) }}
            </span>
          </template>
          <template #cell-max_drawdown="{ row }">
            <span class="mono text-fall">{{ formatPct(row.max_drawdown as number) }}</span>
          </template>
        </DataTable>
      </DataPanel>

      <DataPanel title="RETURN COMPARISON" style="margin-top: var(--u4)">
        <BaseChart v-if="barChartOption" :option="barChartOption" height="320px" />
      </DataPanel>

      <DataPanel title="DEEP COMPARISON" style="margin-top: var(--u4)">
        <template #header-actions>
          <button class="sd-export-btn" :disabled="compareLoading || selectedStrategies.length < 2" @click="runDeepCompare">
            {{ compareLoading ? 'COMPARING...' : '⇄ COMPARE SELECTED' }}
          </button>
        </template>
        <div v-if="data?.strategies.length" class="sd-deep-select">
          <label class="sd-deep-label">SELECT STRATEGIES (2-5)</label>
          <div class="sd-deep-chips">
            <button
              v-for="s in data.strategies.slice(0, 12)"
              :key="s.strategy"
              class="sd-deep-chip"
              :class="{ 'sd-deep-chip-on': selectedStrategies.includes(s.strategy) }"
              @click="toggleStrategy(s.strategy)"
            >
              {{ strategyDisplayName(s.strategy) }}
            </button>
          </div>
        </div>
        <div v-if="compareResult" class="sd-deep-result">
          <div class="sd-deep-equity">
            <BaseChart v-if="equityChartOption" :option="equityChartOption" height="280px" />
          </div>
          <div v-if="compareResult.significance_tests?.length" class="sd-deep-sig">
            <div class="sd-deep-sig-title">SIGNIFICANCE TESTS</div>
            <DataTable :columns="sigColumns" :rows="sigRows" row-key="pair" :page-size="10" />
          </div>
        </div>
        <div v-else-if="!compareLoading" class="sd-empty">Select 2+ strategies above to compare</div>
      </DataPanel>

      <DataPanel title="HISTORICAL BACKTEST RECORDS" style="margin-top: var(--u4)" v-if="historyRows.length">
        <DataTable :columns="historyColumns" :rows="historyRows" row-key="id" />
      </DataPanel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import DataTable from '@/components/ui/DataTable.vue'
import DataPanel from '@/components/ui/DataPanel.vue'
import MetricBlock from '@/components/ui/MetricBlock.vue'
const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))
import { strategyDisplayName, formatPct, formatNumber, safeToFixed } from '@/utils/format'
import { exportToCsv } from '@/composables/useExport'
import type { PerformanceOverview, BacktestHistoryItem } from '@/types'
import type { ColumnDef } from '@/components/ui/DataTable.vue'

const log = createLogger('StrategyDashboard')
const { handleApiError } = useApiError()
const { cancelAll } = useRequestCancel()

const symbol = ref('600000')
const period = ref('1y')
const loading = ref(false)
const error = ref('')
const data = ref<PerformanceOverview | null>(null)
const historyRecords = ref<BacktestHistoryItem[]>([])
const selectedStrategies = ref<string[]>([])
const compareResult = ref<{
  symbol: string
  period: string
  strategies: { strategy_name: string; equity_curve: { date: string; value: number }[]; sharpe_ratio: number; total_return: number; max_drawdown: number; win_rate: number }[]
  significance_tests: { strategy_a: string; strategy_b: string; t_statistic: number; p_value: number; significant_5pct: boolean; mean_diff_annualized: number }[]
  best_by_sharpe: string | null
} | null>(null)
const compareLoading = ref(false)

const compareColumns: ColumnDef[] = [
  { key: 'strategy', label: 'Strategy', width: '180px', sortable: true },
  { key: 'total_return', label: 'Total Return', width: '100px', align: 'right', sortable: true },
  { key: 'annual_return', label: 'Annual Return', width: '100px', align: 'right', sortable: true },
  { key: 'sharpe_ratio', label: 'Sharpe', width: '80px', align: 'right', sortable: true, format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'max_drawdown', label: 'Max DD', width: '90px', align: 'right', sortable: true },
  { key: 'win_rate', label: 'Win Rate', width: '80px', align: 'right', sortable: true, format: (v: unknown) => safeToFixed((v as number) * 100, 1) + '%' },
  { key: 'profit_factor', label: 'P/F', width: '70px', align: 'right', sortable: true, format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'trade_count', label: 'Trades', width: '70px', align: 'right', sortable: true },
]

const compareRows = computed(() => {
  if (!data.value) return []
  return data.value.strategies.map(s => ({
    strategy: s.strategy,
    total_return: s.total_return,
    annual_return: s.annual_return,
    sharpe_ratio: s.sharpe_ratio,
    max_drawdown: s.max_drawdown,
    win_rate: s.win_rate,
    profit_factor: s.profit_factor,
    trade_count: s.trade_count,
  }))
})

const historyColumns: ColumnDef[] = [
  { key: 'strategy_name', label: 'Strategy', width: '160px', format: (v: unknown) => strategyDisplayName(v as string) },
  { key: 'symbol', label: 'Symbol', width: '80px', code: true },
  { key: 'total_return', label: 'Return', width: '90px', align: 'right', format: (v: unknown) => formatPct(v as number) },
  { key: 'sharpe_ratio', label: 'Sharpe', width: '80px', align: 'right', format: (v: unknown) => safeToFixed(v, 2) || '-' },
  { key: 'created_at', label: 'Date', width: '100px', format: (v: unknown) => v ? String(v).slice(0, 10) : '-' },
]

const historyRows = computed(() =>
  historyRecords.value.map((h, i) => ({
    id: h.id ?? i,
    strategy_name: h.strategy_name || h.strategy_type,
    symbol: h.symbol,
    total_return: h.total_return ?? 0,
    sharpe_ratio: h.sharpe_ratio ?? 0,
    created_at: h.created_at ?? '',
  }))
)

const barChartOption = computed(() => {
  if (!data.value?.strategies?.length) return null
  const strategies = data.value.strategies.slice(0, 12)
  const names = strategies.map(s => strategyDisplayName(s.strategy))
  const returns = strategies.map(s => (s.total_return * 100))
  const benchmarkLine = strategies.map(() => data.value!.benchmark.total_return * 100)
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13, 13, 26, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#f0f0f8', fontSize: 12 },
    },
    legend: { data: ['Return%', 'Benchmark%'], top: 0, textStyle: { color: '#9898b0', fontSize: 10 } },
    grid: { left: 60, right: 20, top: 30, bottom: 60 },
    xAxis: {
      type: 'category',
      data: names,
      axisLabel: { fontSize: 10, color: '#555568', rotate: 30, interval: 0 },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, color: '#555568', formatter: '{value}%' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
    },
    series: [
      {
        name: 'Return%',
        type: 'bar',
        data: returns.map(v => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#00e676' : '#ff3b3b' },
        })),
        barMaxWidth: 24,
      },
      {
        name: 'Benchmark%',
        type: 'line',
        data: benchmarkLine,
        lineStyle: { color: '#ffd600', width: 1.5, type: 'dashed' },
        itemStyle: { color: '#ffd600' },
        symbol: 'none',
      },
    ],
  }
})

const DEEP_COMPARE_COLORS = ['#2979ff', '#00e676', '#ff3b3b', '#ffd600', '#e040fb']

function toggleStrategy(name: string) {
  const idx = selectedStrategies.value.indexOf(name)
  if (idx >= 0) {
    selectedStrategies.value.splice(idx, 1)
  } else if (selectedStrategies.value.length < 5) {
    selectedStrategies.value.push(name)
  }
  compareResult.value = null
}

async function runDeepCompare() {
  if (selectedStrategies.value.length < 2) return
  compareLoading.value = true
  compareResult.value = null
  try {
    compareResult.value = await api.backtest.advanced({
      symbol: symbol.value.trim(),
      strategies: selectedStrategies.value,
      start_date: '2024-01-01',
      end_date: '2025-12-31',
      action: 'strategy_compare',
    }) as unknown as typeof compareResult.value
  } catch {
    try {
      const res = await api.backtest.compare(symbol.value.trim())
      compareResult.value = {
        symbol: symbol.value.trim(),
        period: '1y',
        strategies: (res as unknown as { strategy_name: string; sharpe_ratio: number; total_return: number; max_drawdown: number; win_rate: number }[]).map((s, i) => ({
          strategy_name: s.strategy_name || selectedStrategies.value[i] || `Strategy ${i + 1}`,
          equity_curve: [],
          sharpe_ratio: s.sharpe_ratio ?? 0,
          total_return: s.total_return ?? 0,
          max_drawdown: s.max_drawdown ?? 0,
          win_rate: s.win_rate ?? 0,
        })),
        significance_tests: [],
        best_by_sharpe: null,
      }
    } catch (err) {
      handleApiError(err, '策略对比失败')
    }
  } finally {
    compareLoading.value = false
  }
}

const equityChartOption = computed(() => {
  if (!compareResult.value?.strategies?.length) return null
  const strategies = compareResult.value.strategies.filter(s => s.equity_curve?.length > 0)
  if (strategies.length === 0) return null

  const dateSet = new Set<string>()
  for (const s of strategies) {
    for (const pt of s.equity_curve) {
      dateSet.add(pt.date)
    }
  }
  const dates = [...dateSet].sort()

  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(13, 13, 26, 0.95)',
      borderColor: 'rgba(255,255,255,0.08)',
      textStyle: { color: '#f0f0f8', fontSize: 12 },
    },
    legend: {
      data: strategies.map(s => strategyDisplayName(s.strategy_name)),
      top: 0,
      textStyle: { color: '#9898b0', fontSize: 10 },
    },
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: dates.map(d => d.slice(5)),
      axisLabel: { fontSize: 10, color: '#555568' },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 10, color: '#555568' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } },
    },
    series: strategies.map((s, i) => ({
      name: strategyDisplayName(s.strategy_name),
      type: 'line',
      data: dates.map(d => {
        const pt = s.equity_curve.find(p => p.date === d)
        return pt ? pt.value : null
      }),
      lineStyle: { width: 1.5, color: DEEP_COMPARE_COLORS[i % DEEP_COMPARE_COLORS.length] },
      itemStyle: { color: DEEP_COMPARE_COLORS[i % DEEP_COMPARE_COLORS.length] },
      symbol: 'none',
      connectNulls: true,
    })),
  }
})

const sigColumns: ColumnDef[] = [
  { key: 'pair', label: 'Pair', width: '200px' },
  { key: 't_statistic', label: 'T-Stat', width: '80px', align: 'right', format: (v: unknown) => safeToFixed(v, 3) },
  { key: 'p_value', label: 'P-Value', width: '80px', align: 'right', format: (v: unknown) => safeToFixed(v, 4) },
  { key: 'significant_5pct', label: 'Significant', width: '90px', align: 'center' },
  { key: 'mean_diff_annualized', label: 'Ann. Diff%', width: '100px', align: 'right', format: (v: unknown) => safeToFixed(v, 2) + '%' },
]

const sigRows = computed(() => {
  if (!compareResult.value?.significance_tests?.length) return []
  return compareResult.value.significance_tests.map(t => ({
    pair: `${strategyDisplayName(t.strategy_a)} vs ${strategyDisplayName(t.strategy_b)}`,
    t_statistic: t.t_statistic,
    p_value: t.p_value,
    significant_5pct: t.significant_5pct,
    mean_diff_annualized: t.mean_diff_annualized,
  }))
})

function exportComparison() {
  if (!compareRows.value.length) return
  const exportCols = compareColumns.map(c => ({ key: c.key, label: c.label, format: c.format }))
  const ts = new Date().toISOString().slice(0, 10)
  exportToCsv(`strategy_comparison_${symbol.value}_${ts}.csv`, exportCols, compareRows.value)
}

async function fetchData() {
  if (!symbol.value.trim()) return
  loading.value = true
  error.value = ''
  try {
    data.value = await api.backtest.performanceOverview(symbol.value.trim(), period.value)
    historyRecords.value = await api.backtest.history(symbol.value.trim(), 20)
  } catch (err) {
    handleApiError(err, '获取策略数据失败')
    error.value = (err instanceof Error ? err.message : String(err)) || 'Load failed'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
})

onUnmounted(cancelAll)
</script>

<style scoped>
.sd-root {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.sd-header {
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.sd-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--u4);
}

.sd-header-left {
  display: flex;
  align-items: baseline;
  gap: var(--u4);
}

.sd-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sd-subtitle {
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  letter-spacing: 0.02em;
}

.sd-nav-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--u2);
  padding: var(--u2) var(--u4);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--r-md);
  color: #fff;
  text-decoration: none;
  transition: filter var(--dur-fast) var(--ease-mechanical);
}

.sd-nav-btn:hover {
  filter: brightness(1.15);
  text-decoration: none;
}

.sd-controls {
  display: flex;
  gap: var(--u4);
  align-items: flex-end;
  padding: var(--u4);
}

.sd-ctrl-field {
  display: flex;
  flex-direction: column;
  gap: var(--u1);
}

.sd-ctrl-label {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sd-ctrl-input {
  padding: var(--u2) var(--u3);
  background: var(--bg-void);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  color: var(--text-primary);
  font-size: var(--fs-sm);
  outline: none;
  font-family: inherit;
  font-variant-numeric: tabular-nums;
  min-width: 140px;
}

.sd-ctrl-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-muted);
}

.sd-ctrl-btn {
  padding: var(--u2) var(--u6);
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: var(--r-md);
  color: #fff;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: filter var(--dur-fast) var(--ease-mechanical);
}

.sd-ctrl-btn:hover:not(:disabled) {
  filter: brightness(1.1);
}

.sd-ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sd-loading,
.sd-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--u3);
  padding: var(--u8);
  color: var(--text-secondary);
  font-size: var(--fs-sm);
}

.sd-error {
  color: var(--rise);
}

.sd-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-dim);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: sd-spin 350ms linear infinite;
}

@keyframes sd-spin {
  to { transform: rotate(360deg); }
}

.sd-content {
  display: grid;
  gap: var(--u4);
}

.sd-summary {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: var(--u4);
}

.sd-best {
  padding: var(--u5);
  display: flex;
  flex-direction: column;
  gap: var(--u3);
  position: relative;
  overflow: hidden;
}

.sd-best::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent), var(--teal));
}

.sd-best-badge {
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
}

.sd-best-name {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sd-best-metrics {
  display: flex;
  gap: var(--u5);
}

.sd-best-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sd-best-label {
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
}

.sd-best-val {
  font-size: var(--fs-md);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.sd-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--u4);
}

.sd-strat-link {
  color: var(--accent);
  font-size: var(--fs-sm);
}

.sd-export-btn {
  padding: var(--u1) var(--u3);
  background: var(--bg-raised);
  border: 1px solid var(--border-mid);
  border-radius: var(--r-md);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--fs-2xs);
  font-weight: 500;
  letter-spacing: 0.06em;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.sd-export-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.sd-export-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.sd-deep-select {
  margin-bottom: var(--u4);
}

.sd-deep-label {
  display: block;
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--u2);
}

.sd-deep-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--u2);
}

.sd-deep-chip {
  padding: 3px 10px;
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  color: var(--text-secondary);
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.sd-deep-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.sd-deep-chip-on {
  background: var(--accent-muted);
  border-color: var(--accent);
  color: var(--accent);
}

.sd-deep-result {
  display: flex;
  flex-direction: column;
  gap: var(--u4);
}

.sd-deep-equity {
  border-bottom: 1px solid var(--border-hair);
  padding-bottom: var(--u4);
}

.sd-deep-sig-title {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--u2);
}

.sd-empty {
  padding: var(--u6) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.text-rise { color: var(--rise); }
.text-fall { color: var(--fall); }
.mono { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

@media (max-width: 768px) {
  .sd-summary {
    grid-template-columns: 1fr;
  }

  .sd-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .sd-stats {
    grid-template-columns: 1fr;
  }

  .sd-header-left {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--u2);
  }
}
</style>
