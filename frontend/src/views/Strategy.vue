<template>
  <div class="strategy-page fade-in">
    <header class="page-header">
      <div>
        <h1 class="page-title">策略回测</h1>
        <p class="page-subtitle">量化策略回测与参数优化</p>
      </div>
    </header>

    <div class="strategy-grid">
      <div class="config-panel card">
        <h2 class="section-title">回测配置</h2>
        <div class="form-group">
          <label>股票代码</label>
          <input v-model="config.symbol" placeholder="如 600519" />
        </div>
        <div class="form-group">
          <label>策略选择</label>
          <select v-model="config.strategy">
            <option v-for="s in strategies" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>开始日期</label>
          <input type="date" v-model="config.start_date" />
        </div>
        <div class="form-group">
          <label>结束日期</label>
          <input type="date" v-model="config.end_date" />
        </div>
        <div class="form-group">
          <label>初始资金</label>
          <input type="number" v-model.number="config.initial_capital" step="100000" />
        </div>
        <button class="btn btn-primary run-btn" @click="runBacktest" :disabled="running">
          {{ running ? '回测中...' : '开始回测' }}
        </button>
      </div>

      <div class="results-panel">
        <div v-if="!result && !running" class="empty-state card">
          <div class="empty-icon">📊</div>
          <div class="empty-text">选择策略并运行回测查看结果</div>
        </div>

        <div v-if="running" class="loading-state card">
          <div class="spinner"></div>
          <span>正在运行回测...</span>
        </div>

        <template v-if="result && !running">
          <div class="metrics-grid">
            <div class="metric-card card">
              <div class="metric-label">总收益率</div>
              <div class="metric-value font-mono" :class="result.total_return >= 0 ? 'text-up' : 'text-down'">
                {{ (result.total_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="metric-card card">
              <div class="metric-label">年化收益</div>
              <div class="metric-value font-mono" :class="result.annual_return >= 0 ? 'text-up' : 'text-down'">
                {{ (result.annual_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="metric-card card">
              <div class="metric-label">最大回撤</div>
              <div class="metric-value font-mono text-down">
                -{{ (result.max_drawdown * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="metric-card card">
              <div class="metric-label">夏普比率</div>
              <div class="metric-value font-mono">{{ result.sharpe_ratio?.toFixed(2) || '-' }}</div>
            </div>
            <div class="metric-card card">
              <div class="metric-label">胜率</div>
              <div class="metric-value font-mono">{{ (result.win_rate * 100).toFixed(1) }}%</div>
            </div>
            <div class="metric-card card">
              <div class="metric-label">交易次数</div>
              <div class="metric-value font-mono">{{ result.total_trades || 0 }}</div>
            </div>
          </div>

          <div class="card chart-card">
            <h3 class="section-title">净值曲线</h3>
            <div class="equity-chart" ref="equityChartRef"></div>
          </div>

          <div class="card" v-if="result.trades && result.trades.length">
            <h3 class="section-title">交易记录</h3>
            <div class="trades-table">
              <div class="table-header">
                <span>时间</span><span>方向</span><span>价格</span><span>数量</span><span>盈亏</span>
              </div>
              <div v-for="(t, i) in result.trades.slice(0, 30)" :key="i" class="table-row">
                <span class="font-mono">{{ t.trade_time?.slice(0, 10) }}</span>
                <span :class="t.direction === 'BUY' ? 'text-up' : 'text-down'">{{ t.direction === 'BUY' ? '买入' : '卖出' }}</span>
                <span class="font-mono">{{ t.price?.toFixed(2) }}</span>
                <span class="font-mono">{{ t.quantity }}</span>
                <span class="font-mono" :class="t.pnl >= 0 ? 'text-up' : 'text-down'">{{ t.pnl?.toFixed(2) || '-' }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import api from '../api'
import * as echarts from 'echarts'

const strategies = ref<any[]>([])
const running = ref(false)
const result = ref<any>(null)
const equityChartRef = ref<HTMLElement>()
let equityChart: echarts.ECharts | null = null

const config = ref({
  symbol: '600519',
  strategy: 'ma_cross',
  start_date: '2024-01-01',
  end_date: '2025-12-31',
  initial_capital: 1000000,
  params: {},
})

async function loadStrategies() {
  try {
    strategies.value = await api.getStrategyList()
    if (strategies.value.length && !config.value.strategy) {
      config.value.strategy = strategies.value[0].name
    }
  } catch {}
}

async function runBacktest() {
  running.value = true
  result.value = null
  try {
    result.value = await api.runBacktest(config.value)
    await nextTick()
    renderEquityChart()
  } catch (e: any) {
    alert(`回测失败: ${e.message}`)
  } finally {
    running.value = false
  }
}

function renderEquityChart() {
  if (!equityChartRef.value || !result.value?.equity_curve) return
  if (!equityChart) {
    equityChart = echarts.init(equityChartRef.value, 'dark')
  }
  const curve = result.value.equity_curve
  const dates = curve.map((p: any) => p.date?.slice(0, 10) || '')
  const values = curve.map((p: any) => p.value || p.equity || 0)

  equityChart.setOption({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(28,28,30,0.95)', borderColor: 'rgba(255,255,255,0.1)', textStyle: { color: '#f5f5f7', fontSize: 12, fontFamily: 'SF Mono, Menlo, monospace' } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#6e6e73', fontSize: 10 } },
    yAxis: { type: 'value', scale: true, splitLine: { lineStyle: { color: '#1a1a1a' } }, axisLabel: { color: '#6e6e73', fontSize: 10, fontFamily: 'SF Mono, Menlo, monospace' } },
    series: [{ type: 'line', data: values, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#2997ff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(41,151,255,0.3)' }, { offset: 1, color: 'rgba(41,151,255,0)' }] } } }],
    dataZoom: [{ type: 'inside' }],
  })
}

onMounted(loadStrategies)
onUnmounted(() => { equityChart?.dispose() })
</script>

<style scoped>
.strategy-page { padding: 24px 28px; }

.page-header { margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.strategy-grid {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 16px;
}

.config-panel { height: fit-content; position: sticky; top: 24px; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 12px; color: var(--text-tertiary); margin-bottom: 4px; }
.form-group input, .form-group select { width: 100%; }

.run-btn { width: 100%; margin-top: 8px; padding: 10px; }

.results-panel { min-width: 0; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card { padding: 16px; }
.metric-label { font-size: 11px; color: var(--text-tertiary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-value { font-size: 22px; font-weight: 700; }

.chart-card { margin-bottom: 16px; }
.equity-chart { height: 300px; }

.trades-table { width: 100%; }
.table-header {
  display: grid;
  grid-template-columns: 100px 60px 80px 60px 80px;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-row {
  display: grid;
  grid-template-columns: 100px 60px 80px 60px 80px;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
}

.empty-state, .loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
}

.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; color: var(--text-tertiary); }

.spinner {
  width: 24px; height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
