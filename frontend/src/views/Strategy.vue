<template>
  <div class="strategy-page">
    <div v-if="loading" class="skeleton-strategy">
      <div class="skeleton-row">
        <div class="skeleton" style="height:500px;width:300px;border-radius:8px"></div>
        <div class="skeleton" style="height:500px;flex:1;border-radius:8px;margin-left:12px"></div>
      </div>
    </div>
    <template v-else>
    <div class="page-header">
      <h1 class="page-title">策略回测</h1>
    </div>

    <div class="strategy-layout">
      <div class="left-col">
        <div class="config-panel">
          <div class="form-group">
            <label>股票代码</label>
            <input v-model="config.symbol" type="text" placeholder="如 000001" class="form-input" />
          </div>

          <div class="form-group">
            <label>策略选择</label>
            <div class="strategy-groups">
              <div v-for="group in strategyGroups" :key="group.label" class="strategy-group">
                <div class="group-label">{{ group.label }}</div>
                <div class="group-items">
                  <button
                    v-for="s in group.items"
                    :key="s.value"
                    class="strategy-chip"
                    :class="{ active: config.strategy === s.value }"
                    @click="config.strategy = s.value"
                  >{{ s.label }}</button>
                </div>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label>时间范围</label>
            <div class="quick-range-btns">
              <button v-for="q in quickRanges" :key="q.value" class="range-btn" :class="{ active: config.period === q.value }" @click="config.period = q.value">{{ q.label }}</button>
            </div>
            <div class="date-row">
              <input v-model="config.startDate" type="date" class="form-input date-input" />
              <span class="date-sep">至</span>
              <input v-model="config.endDate" type="date" class="form-input date-input" />
            </div>
          </div>

          <div class="form-group">
            <label>初始资金</label>
            <input v-model.number="config.capital" type="number" class="form-input" />
          </div>

          <div class="advanced-toggle" @click="showAdvanced = !showAdvanced">
            <span>高级参数</span>
            <span>{{ showAdvanced ? '▲' : '▼' }}</span>
          </div>
          <div v-if="showAdvanced" class="advanced-params">
            <div class="form-group">
              <label class="checkbox-label"><input v-model="config.monteCarlo" type="checkbox" /> 蒙特卡洛模拟</label>
            </div>
            <div v-if="config.monteCarlo" class="form-group">
              <label>模拟次数</label>
              <input v-model.number="config.nSimulations" type="number" min="100" max="2000" class="form-input" />
            </div>
            <div class="form-group">
              <label class="checkbox-label"><input v-model="config.sensitivity" type="checkbox" /> 敏感性分析</label>
            </div>
            <div class="form-group">
              <label class="checkbox-label"><input v-model="config.walkForward" type="checkbox" /> 滚动前进分析</label>
            </div>
          </div>

          <button class="btn-run" @click="runBacktest" :disabled="running">
            {{ running ? '运行中...' : '开始回测' }}
          </button>
          <button class="btn-optimize" @click="runOptimize" :disabled="optimizing" v-if="config.strategy !== 'adaptive'">
            {{ optimizing ? '优化中...' : '参数优化' }}
          </button>
        </div>
      </div>

      <div class="center-col">
        <div v-if="result" class="result-panel">
          <div class="result-tabs">
            <button class="rtab" :class="{ active: resultTab === 'overview' }" @click="resultTab = 'overview'">概览</button>
            <button class="rtab" :class="{ active: resultTab === 'risk' }" @click="resultTab = 'risk'">风险分析</button>
            <button class="rtab" :class="{ active: resultTab === 'montecarlo' }" @click="resultTab = 'montecarlo'" v-if="result.monte_carlo">蒙特卡洛</button>
            <button class="rtab" :class="{ active: resultTab === 'optimization' }" @click="resultTab = 'optimization'" v-if="optimizationResult">参数优化</button>
            <button class="rtab" :class="{ active: resultTab === 'heatmap' }" @click="resultTab = 'heatmap'">收益热力图</button>
            <button class="rtab" :class="{ active: resultTab === 'trades' }" @click="resultTab = 'trades'">交易记录</button>
          </div>

          <div v-if="resultTab === 'overview'" class="tab-body">
            <div class="metrics-grid">
              <MetricCard label="总收益" :value="fmtPct(result.total_return)" :positive="result.total_return >= 0 ? 'up' : 'down'" />
              <MetricCard label="年化收益" :value="fmtPct(result.annual_return)" :positive="result.annual_return >= 0 ? 'up' : 'down'" />
              <MetricCard label="最大回撤" :value="fmtPct(result.max_drawdown)" positive="down" />
              <MetricCard label="夏普比率" :value="(result.sharpe_ratio || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="胜率" :value="fmtPct(result.win_rate)" positive="neutral" />
              <MetricCard label="盈亏比" :value="(result.profit_factor || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="Omega" :value="(result.omega_ratio || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="Calmar" :value="(result.calmar_ratio || 0).toFixed(2)" positive="neutral" />
            </div>
            <div class="chart-section">
              <h3 class="section-title">权益曲线</h3>
              <BaseChart :option="equityOption" height="280px" />
            </div>
            <div class="chart-section">
              <h3 class="section-title">回撤曲线</h3>
              <BaseChart :option="drawdownOption" height="160px" />
            </div>
          </div>

          <div v-if="resultTab === 'risk'" class="tab-body">
            <div class="metrics-grid">
              <MetricCard label="波动率(年)" :value="fmtPct(result.volatility || result.annual_volatility)" positive="neutral" />
              <MetricCard label="下行偏差" :value="fmtPct(result.downside_deviation)" positive="down" />
              <MetricCard label="CVaR(95%)" :value="fmtPct(result.cvar_95)" positive="down" />
              <MetricCard label="Tail Ratio" :value="(result.tail_ratio || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="信息比率" :value="(result.information_ratio || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="恢复天数" :value="String(result.recovery_days || '-')" positive="neutral" />
            </div>
            <div class="chart-section">
              <h3 class="section-title">月度收益分布</h3>
              <BaseChart :option="monthlyReturnOption" height="200px" />
            </div>
          </div>

          <div v-if="resultTab === 'montecarlo' && result.monte_carlo" class="tab-body">
            <div class="metrics-grid">
              <MetricCard label="鲁棒性评分" :value="(result.monte_carlo.robustness_score || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="P5最终资金" :value="fmtMoney(result.monte_carlo.final_p5)" positive="down" />
              <MetricCard label="P50最终资金" :value="fmtMoney(result.monte_carlo.final_p50)" positive="neutral" />
              <MetricCard label="P95最终资金" :value="fmtMoney(result.monte_carlo.final_p95)" positive="up" />
            </div>
            <div class="chart-section">
              <h3 class="section-title">蒙特卡洛资金分布</h3>
              <BaseChart :option="monteCarloOption" height="300px" />
            </div>
          </div>

          <div v-if="resultTab === 'optimization' && optimizationResult" class="tab-body">
            <div class="metrics-grid">
              <MetricCard label="最优夏普" :value="(optimizationResult.top?.[0]?.sharpe_ratio || 0).toFixed(2)" positive="neutral" />
              <MetricCard label="最优收益" :value="fmtPct(optimizationResult.top?.[0]?.total_return)" :positive="(optimizationResult.top?.[0]?.total_return || 0) >= 0 ? 'up' : 'down'" />
              <MetricCard label="最优回撤" :value="fmtPct(optimizationResult.top?.[0]?.max_drawdown)" positive="down" />
              <MetricCard label="优化指标" :value="optimizationResult.metric || 'sharpe_ratio'" positive="neutral" />
            </div>
            <div class="opt-table-wrap">
              <DataTable :columns="optColumns" :data="optimizationResult.top || []" :striped="true" row-key="params" />
            </div>
          </div>

          <div v-if="resultTab === 'heatmap'" class="tab-body">
            <div ref="yearlyHeatmapRef" class="heatmap-chart"></div>
          </div>

          <div v-if="resultTab === 'trades'" class="tab-body">
            <DataTable :columns="tradeColumns" :data="result.trades || []" :striped="true" row-key="date" />
          </div>
        </div>
        <div v-else class="empty-state">
          <div class="empty-icon">📊</div>
          <p>选择策略和参数后开始回测</p>
        </div>
      </div>

      <div class="right-col">
        <div class="history-panel">
          <h3 class="section-title">回测历史</h3>
          <div v-if="historyList.length" class="history-list">
            <div v-for="(h, idx) in historyList" :key="idx" class="history-item" @click="loadHistory(idx)">
              <div class="hist-top">
                <span class="hist-symbol">{{ h.symbol }}</span>
                <span class="hist-strategy">{{ h.strategy }}</span>
              </div>
              <div class="hist-bottom">
                <span class="hist-return" :class="h.total_return >= 0 ? 'up' : 'down'">{{ fmtPct(h.total_return) }}</span>
                <span class="hist-date">{{ h.run_time }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-state-small">暂无历史</div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { api } from '../api'
import echarts from '../lib/echarts'
import { MetricCard, BaseChart, DataTable } from '../components'

const config = ref({
  symbol: '000001',
  strategy: 'adaptive',
  period: '1y',
  startDate: '2024-04-29',
  endDate: '2025-04-29',
  capital: 1000000,
  monteCarlo: false,
  nSimulations: 500,
  sensitivity: false,
  walkForward: false,
})
const loading = ref(true)
const running = ref(false)
const optimizing = ref(false)
const optimizationResult = ref<any>(null)
const result = ref<any>(null)
const resultTab = ref('overview')
const showAdvanced = ref(false)
const historyList = ref<any[]>([])

const yearlyHeatmapRef = ref<HTMLElement | null>(null)
let yearlyHeatmapChart: any = null

const strategyGroups = [
  {
    label: '趋势跟踪',
    items: [
      { value: 'dual_ma', label: '双均线' },
      { value: 'macd', label: 'MACD' },
      { value: 'supertrend', label: 'SuperTrend' },
      { value: 'ichimoku', label: '一目均衡' },
      { value: 'donchian', label: '唐奇安通道' },
    ],
  },
  {
    label: '均值回归',
    items: [
      { value: 'bollinger_breakout', label: '布林突破' },
      { value: 'rsi_reversal', label: 'RSI反转' },
      { value: 'mean_reversion', label: '均值回归' },
    ],
  },
  {
    label: '多因子',
    items: [
      { value: 'composite', label: '复合策略' },
      { value: 'factor_model', label: '因子模型' },
    ],
  },
  {
    label: '自适应',
    items: [
      { value: 'adaptive', label: '自适应引擎' },
      { value: 'regime_switching', label: '状态切换' },
    ],
  },
]

const quickRanges = [
  { value: '3m', label: '3月' },
  { value: '6m', label: '6月' },
  { value: '1y', label: '1年' },
  { value: '3y', label: '3年' },
  { value: '5y', label: '5年' },
]

const tradeColumns = [
  { key: 'date', label: '日期', width: '90px' },
  { key: 'type', label: '方向', width: '50px', cellClass: 'center' },
  { key: 'price', label: '价格', width: '70px', align: 'right' as const, format: (v: number) => v?.toFixed(2) },
  { key: 'shares', label: '数量', width: '60px', align: 'right' as const },
  { key: 'pnl', label: '盈亏', width: '70px', align: 'right' as const, format: (v: number) => v ? (v >= 0 ? '+' : '') + v.toFixed(0) : '-' },
  { key: 'strategy', label: '策略', width: '80px' },
]

const optColumns = [
  { key: 'params', label: '参数', format: (v: any) => JSON.stringify(v) },
  { key: 'total_return', label: '总收益', align: 'right' as const, format: (v: number) => fmtPct(v) },
  { key: 'sharpe_ratio', label: '夏普', align: 'right' as const, format: (v: number) => v?.toFixed(2) },
  { key: 'max_drawdown', label: '最大回撤', align: 'right' as const, format: (v: number) => fmtPct(v) },
]

function fmtPct(v: number): string {
  if (v === undefined || v === null) return '-'
  return (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%'
}

function fmtMoney(v: number): string {
  if (!v) return '-'
  return '¥' + v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

async function runBacktest() {
  running.value = true
  try {
    const data = await api.runBacktest(
      config.value.symbol,
      config.value.strategy,
      config.value.startDate,
      config.value.endDate,
      config.value.capital,
      {
        monte_carlo: config.value.monteCarlo,
        n_simulations: config.value.nSimulations,
        sensitivity: config.value.sensitivity,
        walk_forward: config.value.walkForward,
      }
    )
    if (data) {
      result.value = data
      resultTab.value = 'overview'
      historyList.value.unshift({
        symbol: config.value.symbol,
        strategy: config.value.strategy,
        total_return: data.total_return,
        run_time: new Date().toLocaleTimeString('zh-CN'),
        data,
      })
      if (historyList.value.length > 20) historyList.value = historyList.value.slice(0, 20)
    }
  } catch (e) {
    console.error('Backtest error:', e)
  } finally {
    running.value = false
  }
}

async function runOptimize() {
  optimizing.value = true
  try {
    const data = await api.optimizeStrategy(
      config.value.symbol,
      config.value.strategy,
      config.value.startDate,
      config.value.endDate,
      'sharpe_ratio',
      100
    )
    if (data) {
      optimizationResult.value = data
      resultTab.value = 'optimization'
    }
  } catch (e) {
    console.error('Optimize error:', e)
  } finally {
    optimizing.value = false
  }
}

async function loadServerHistory() {
  try {
    const data = await api.getBacktestHistory()
    if (data && Array.isArray(data) && data.length) {
      const serverHistory = data.slice(0, 10).map((h: any) => ({
        symbol: h.symbol || '',
        strategy: h.strategy_name || h.strategy || '',
        total_return: h.total_return || 0,
        run_time: h.created_at || h.run_time || '',
        data: h,
      }))
      const existingKeys = new Set(historyList.value.map(h => `${h.symbol}_${h.strategy}_${h.run_time}`))
      for (const sh of serverHistory) {
        const key = `${sh.symbol}_${sh.strategy}_${sh.run_time}`
        if (!existingKeys.has(key)) {
          historyList.value.push(sh)
        }
      }
    }
  } catch (e) {}
}

function loadHistory(idx: number) {
  const h = historyList.value[idx]
  if (h?.data) {
    result.value = h.data
    resultTab.value = 'overview'
  }
}

const equityOption = computed(() => {
  if (!result.value?.equity_curve) return {}
  const eq = result.value.equity_curve
  const dates = eq.map((d: any) => (d.date || '').slice(0, 10))
  const values = eq.map((d: any) => d.value || d.equity)
  const benchmark = eq.map((d: any) => d.benchmark || d.bm_value)
  const hasBm = benchmark.some((v: any) => v !== undefined && v !== null)
  const series: any[] = [
    { name: '策略', type: 'line', data: values, showSymbol: false, lineStyle: { width: 1.5, color: '#4d9fff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(77,159,255,0.12)' }, { offset: 1, color: 'rgba(77,159,255,0)' }] } } },
  ]
  if (hasBm) {
    series.push({ name: '基准', type: 'line', data: benchmark, showSymbol: false, lineStyle: { width: 1, color: '#666', type: 'dashed' } })
  }
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    legend: { data: hasBm ? ['策略', '基准'] : ['策略'], top: 0, textStyle: { color: '#888', fontSize: 10 } },
    grid: { left: 60, right: 20, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series,
  }
})

const drawdownOption = computed(() => {
  if (!result.value?.drawdown_curve && !result.value?.equity_curve) return {}
  const eq = result.value.equity_curve
  const dates = eq.map((d: any) => (d.date || '').slice(0, 10))
  let dd: number[]
  if (result.value.drawdown_curve) {
    dd = result.value.drawdown_curve.map((v: any) => typeof v === 'number' ? v * 100 : v)
  } else {
    const values = eq.map((d: any) => d.value || d.equity)
    let peak = values[0]
    dd = values.map((v: number) => {
      peak = Math.max(peak, v)
      return ((v - peak) / peak) * 100
    })
  }
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis', formatter: (p: any) => p[0] ? `${p[0].axisValue}<br/>回撤: ${p[0].value.toFixed(2)}%` : '' },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: { type: 'value', axisLabel: { color: '#888', fontSize: 9, formatter: (v: number) => v.toFixed(0) + '%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ type: 'line', data: dd, showSymbol: false, lineStyle: { width: 1, color: '#f43f5e' }, areaStyle: { color: 'rgba(244,63,94,0.15)' } }],
  }
})

const monthlyReturnOption = computed(() => {
  if (!result.value?.monthly_returns) return {}
  const mr = result.value.monthly_returns
  const months = mr.map((d: any) => d.month || d.date)
  const values = mr.map((d: any) => ((d.return || d.value) * 100))
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis', formatter: (p: any) => p[0] ? `${p[0].axisValue}<br/>${p[0].value.toFixed(2)}%` : '' },
    grid: { left: 50, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: months, axisLabel: { color: '#888', fontSize: 9, rotate: 45 } },
    yAxis: { type: 'value', axisLabel: { color: '#888', fontSize: 9, formatter: (v: number) => v.toFixed(0) + '%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ type: 'bar', data: values.map((v: number) => ({ value: v, itemStyle: { color: v >= 0 ? '#f43f5e' : '#34d399' } })) }],
  }
})

const monteCarloOption = computed(() => {
  if (!result.value?.monte_carlo?.paths) return {}
  const mc = result.value.monte_carlo
  const paths = mc.paths.slice(0, 30)
  const series = paths.map((path: number[], idx: number) => ({
    type: 'line', data: path, showSymbol: false, smooth: true,
    lineStyle: { width: 0.5, color: idx === 0 ? '#4d9fff' : 'rgba(77,159,255,0.2)' },
  }))
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', axisLabel: { show: false } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series,
  }
})

watch(resultTab, (tab) => {
  if (tab === 'heatmap') {
    nextTick(() => renderYearlyHeatmap())
  }
})

function renderYearlyHeatmap() {
  if (!yearlyHeatmapRef.value || !result.value) return
  if (!yearlyHeatmapChart) {
    yearlyHeatmapChart = echarts.init(yearlyHeatmapRef.value, undefined, { renderer: 'canvas' })
  }
  const trades = result.value.trades || []
  const yearMonthMap: Record<string, number> = {}
  trades.forEach((t: any) => {
    const date = t.date || t.exit_date || ''
    if (!date) return
    const ym = date.slice(0, 7)
    if (!yearMonthMap[ym]) yearMonthMap[ym] = 0
    yearMonthMap[ym] += (t.pnl || 0)
  })
  const years = [...new Set(Object.keys(yearMonthMap).map(k => k.slice(0, 4)))].sort()
  const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
  const data: any[] = []
  years.forEach((year, yi) => {
    months.forEach((month, mi) => {
      const key = year + '-' + month
      const val = yearMonthMap[key]
      if (val !== undefined) {
        data.push([mi, yi, val])
      }
    })
  })
  yearlyHeatmapChart.setOption({
    animation: false,
    tooltip: {
      formatter: (info: any) => {
        const d = info.data
        return `${years[d[1]]}-${months[d[0]]}<br/>收益: ${d[2] >= 0 ? '+' : ''}${(d[2] / config.value.capital * 100).toFixed(2)}%`
      },
    },
    grid: { left: 50, right: 20, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: months.map(m => m + '月'), axisLabel: { color: '#888', fontSize: 10 }, splitLine: { show: false } },
    yAxis: { type: 'category', data: years, axisLabel: { color: '#888', fontSize: 10 }, splitLine: { show: false } },
    visualMap: { min: -50000, max: 50000, calculable: true, orient: 'horizontal', left: 'center', bottom: 0, inRange: { color: ['#34d399', '#1a1a2e', '#f43f5e'] }, textStyle: { color: '#888', fontSize: 9 }, show: false },
    series: [{
      type: 'heatmap', data,
      label: { show: true, formatter: (p: any) => p.data[2] >= 0 ? '+' : '', fontSize: 9, color: '#e8eaed' },
      itemStyle: { borderColor: 'var(--bg-primary)', borderWidth: 2 },
    }],
  }, true)
}

onMounted(() => {
  const saved = localStorage.getItem('backtest_history')
  if (saved) {
    try { historyList.value = JSON.parse(saved) } catch (e) {}
  }
  loadServerHistory()
  loading.value = false
})

watch(historyList, (v) => {
  localStorage.setItem('backtest_history', JSON.stringify(v.slice(0, 20)))
}, { deep: true })
</script>

<style scoped>
.skeleton-strategy { padding: 20px; }
.skeleton-row { display: flex; gap: 12px; }
.skeleton { border-radius: 8px; background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary, #1a1a24) 50%, var(--bg-secondary) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.strategy-page { padding: 20px; max-width: 1440px; margin: 0 auto; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }

.strategy-layout { display: grid; grid-template-columns: 260px 1fr 220px; gap: 16px; }

.config-panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 16px; }
.form-group { margin-bottom: 12px; }
.form-group > label { display: block; font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; font-weight: 500; }
.form-input { width: 100%; padding: 7px 10px; background: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-primary); font-size: 12px; font-family: var(--font-mono); }
.form-input:focus { outline: none; border-color: var(--accent-cyan); }

.strategy-groups { display: flex; flex-direction: column; gap: 8px; }
.strategy-group { }
.group-label { font-size: 10px; color: var(--text-tertiary); margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }
.group-items { display: flex; flex-wrap: wrap; gap: 3px; }
.strategy-chip { padding: 3px 8px; border: 1px solid var(--border-color); border-radius: 3px; background: transparent; color: var(--text-secondary); font-size: 11px; cursor: pointer; transition: all 0.15s; }
.strategy-chip:hover { border-color: rgba(77,159,255,0.3); color: var(--text-primary); }
.strategy-chip.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); border-color: rgba(77,159,255,0.4); }

.quick-range-btns { display: flex; gap: 3px; margin-bottom: 6px; }
.range-btn { flex: 1; padding: 4px 0; border: 1px solid var(--border-color); border-radius: 3px; background: transparent; color: var(--text-secondary); font-size: 10px; cursor: pointer; }
.range-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); border-color: rgba(77,159,255,0.3); }
.date-row { display: flex; align-items: center; gap: 6px; }
.date-input { flex: 1; }
.date-sep { font-size: 11px; color: var(--text-tertiary); }

.advanced-toggle { display: flex; justify-content: space-between; padding: 8px 0; border-top: 1px solid var(--border-color); margin-top: 8px; cursor: pointer; font-size: 11px; color: var(--text-secondary); }
.advanced-params { margin-top: 8px; }
.checkbox-label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-primary); cursor: pointer; }
.checkbox-label input { accent-color: var(--accent-cyan); }

.btn-run { width: 100%; padding: 10px; margin-top: 12px; border: none; border-radius: var(--radius-sm); background: linear-gradient(135deg, #4d9fff, #a78bfa); color: white; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.btn-run:hover { opacity: 0.9; }
.btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-optimize { width: 100%; padding: 10px; margin-top: 6px; border: 1px solid rgba(77,159,255,0.4); border-radius: var(--radius-sm); background: transparent; color: var(--accent-cyan); font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.btn-optimize:hover { background: rgba(77,159,255,0.1); }
.btn-optimize:disabled { opacity: 0.5; cursor: not-allowed; }

.result-panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 16px; min-height: 400px; }
.result-tabs { display: flex; gap: 2px; margin-bottom: 14px; overflow-x: auto; }
.rtab { padding: 6px 12px; border: none; background: transparent; color: var(--text-secondary); font-size: 12px; border-radius: var(--radius-sm); cursor: pointer; white-space: nowrap; transition: all 0.15s; }
.rtab.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); }

.tab-body { }
.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
.chart-section { margin-bottom: 14px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; }

.opt-table-wrap { max-height: 400px; overflow-y: auto; }

.heatmap-chart { width: 100%; height: 300px; }

.empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 80px 20px; color: var(--text-tertiary); }
.empty-icon { font-size: 40px; margin-bottom: 12px; }

.right-col { }
.history-panel { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.history-list { display: flex; flex-direction: column; gap: 4px; max-height: 500px; overflow-y: auto; }
.history-item { padding: 8px 10px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); cursor: pointer; transition: background 0.15s; }
.history-item:hover { background: rgba(255,255,255,0.05); }
.hist-top { display: flex; justify-content: space-between; margin-bottom: 2px; }
.hist-symbol { font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); }
.hist-strategy { font-size: 10px; color: var(--text-secondary); }
.hist-bottom { display: flex; justify-content: space-between; }
.hist-return { font-family: var(--font-mono); font-size: 11px; font-weight: 600; }
.hist-return.up { color: var(--accent-red); }
.hist-return.down { color: var(--accent-green); }
.hist-date { font-size: 10px; color: var(--text-tertiary); }
.empty-state-small { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 12px; }

@media (max-width: 1024px) {
  .strategy-layout { grid-template-columns: 1fr; }
  .right-col { display: none; }
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .strategy-page { padding: 10px; }
  .metrics-grid { grid-template-columns: 1fr 1fr; }
}
</style>
