<template>
  <div class="backtest">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M4 24L12 12L20 20L28 4" stroke="url(#logo-gradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="logo-gradient" x1="4" y1="24" x2="28" y2="4">
              <stop stop-color="#00d4aa"/>
              <stop offset="1" stop-color="#0ea5e9"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="logo-text">Quant</span>
      </div>
      
      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <component :is="iconMap[item.icon]" :size="20" />
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>
    </aside>

    <!-- Main Content -->
    <main class="main">
      <header class="header">
        <h1 class="page-title">策略回测</h1>
      </header>

      <div class="content">
        <div class="backtest-layout">
          <!-- Config Panel -->
          <div class="config-panel">
            <div class="panel-header">
              <h3>回测配置</h3>
            </div>
            
            <div class="form-group">
              <label>标的代码</label>
              <input v-model="config.symbol" type="text" placeholder="如: 000001" class="form-input" />
            </div>

            <div class="form-group">
              <label>策略类型</label>
              <div class="strategy-options">
                <button
                  v-for="s in strategies"
                  :key="s.value"
                  class="strategy-btn"
                  :class="{ active: config.strategy_type === s.value }"
                  @click="config.strategy_type = s.value"
                >
                  {{ s.label }}
                </button>
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>开始日期</label>
                <input v-model="config.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label>结束日期</label>
                <input v-model="config.end_date" type="date" class="form-input" />
              </div>
            </div>

            <div class="form-group">
              <label>初始资金</label>
              <div class="input-with-suffix">
                <input v-model="config.initial_capital" type="number" class="form-input" />
                <span class="suffix">元</span>
              </div>
            </div>

            <div class="form-group">
              <label>回测模式</label>
              <div class="mode-options">
                <button
                  class="mode-btn"
                  :class="{ active: config.mode === 'vectorized' }"
                  @click="config.mode = 'vectorized'"
                >
                  向量化
                </button>
                <button
                  class="mode-btn"
                  :class="{ active: config.mode === 'event_driven' }"
                  @click="config.mode = 'event_driven'"
                >
                  事件驱动
                </button>
              </div>
            </div>

            <button class="run-btn" @click="runBacktest" :disabled="loading">
              <IconLoading v-if="loading" :size="16" spin />
              <span>{{ loading ? '运行中...' : '运行回测' }}</span>
            </button>
          </div>

          <!-- Results Panel -->
          <div class="results-panel">
            <div v-if="!result" class="empty-state">
              <div class="empty-icon">
                <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
                  <path d="M8 48L24 32L36 44L56 16" stroke="#334155" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="56" cy="16" r="4" stroke="#334155" stroke-width="2"/>
                </svg>
              </div>
              <p>配置参数并运行回测以查看结果</p>
            </div>

            <template v-else>
              <!-- Metrics Grid -->
              <div class="metrics-grid">
                <div class="metric-card">
                  <div class="metric-label">总收益率</div>
                  <div class="metric-value" :class="result.total_return >= 0 ? 'text-green' : 'text-red'">
                    {{ result.total_return >= 0 ? '+' : '' }}{{ result.total_return?.toFixed(2) }}%
                  </div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">年化收益率</div>
                  <div class="metric-value" :class="result.annual_return >= 0 ? 'text-green' : 'text-red'">
                    {{ result.annual_return >= 0 ? '+' : '' }}{{ result.annual_return?.toFixed(2) }}%
                  </div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">最大回撤</div>
                  <div class="metric-value text-red">{{ result.max_drawdown?.toFixed(2) }}%</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">夏普比率</div>
                  <div class="metric-value">{{ result.sharpe_ratio?.toFixed(2) }}</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">胜率</div>
                  <div class="metric-value">{{ (result.win_rate * 100)?.toFixed(1) }}%</div>
                </div>
                <div class="metric-card">
                  <div class="metric-label">交易次数</div>
                  <div class="metric-value">{{ result.total_trades }}</div>
                </div>
              </div>

              <!-- Equity Chart -->
              <div class="chart-card">
                <div class="card-header">
                  <h3>权益曲线</h3>
                </div>
                <div class="chart-container">
                  <v-chart class="equity-chart" :option="equityChartOption" autoresize />
                </div>
              </div>

              <!-- Trade List -->
              <div class="trades-card" v-if="result.trades?.length">
                <div class="card-header">
                  <h3>交易记录</h3>
                  <span class="trade-count">共 {{ result.trades.length }} 笔</span>
                </div>
                <div class="trades-table-wrapper">
                  <table class="trades-table">
                    <thead>
                      <tr>
                        <th>日期</th>
                        <th>类型</th>
                        <th class="text-right">价格</th>
                        <th class="text-right">数量</th>
                        <th class="text-right">盈亏</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="trade in result.trades" :key="trade.date + trade.type">
                        <td>{{ trade.date }}</td>
                        <td>
                          <span class="trade-type" :class="trade.type">{{ trade.type === 'buy' ? '买入' : '卖出' }}</span>
                        </td>
                        <td class="text-right font-mono">{{ trade.price?.toFixed(2) }}</td>
                        <td class="text-right font-mono">{{ trade.quantity }}</td>
                        <td class="text-right font-mono" :class="trade.pnl >= 0 ? 'text-green' : 'text-red'">
                          {{ trade.pnl >= 0 ? '+' : '' }}{{ trade.pnl?.toFixed(2) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { apiPost } from '../api'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { IconHome, IconBarChart, IconThunderbolt, IconDashboard, IconLoading } from '@arco-design/web-vue/es/icon'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const iconMap: Record<string, any> = { IconHome, IconBarChart, IconThunderbolt, IconDashboard }

const config = ref({
  symbol: '000001',
  strategy_type: 'momentum',
  start_date: '2023-01-01',
  end_date: '2024-01-01',
  initial_capital: 100000,
  mode: 'vectorized',
})

const strategies = [
  { label: '动量策略', value: 'momentum' },
  { label: '均值回归', value: 'mean_reversion' },
  { label: '趋势跟踪', value: 'trend_following' },
]

const navItems = [
  { path: '/dashboard', icon: 'IconHome', label: '首页' },
  { path: '/backtest', icon: 'IconBarChart', label: '回测' },
  { path: '/strategy', icon: 'IconThunderbolt', label: '策略' },
  { path: '/portfolio', icon: 'IconDashboard', label: '组合' },
]

const loading = ref(false)
const result = ref<any>(null)

const equityChartOption = computed(() => {
  if (!result.value?.equity_curve?.length) return {}
  const data = result.value.equity_curve
  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(17, 24, 39, 0.95)',
      borderColor: '#334155',
      textStyle: { color: '#e0e0e0', fontSize: 12 },
    },
    grid: { left: 48, right: 16, top: 16, bottom: 32 },
    xAxis: {
      type: 'category',
      data: data.map((d: any) => d.date),
      axisLine: { lineStyle: { color: '#334155' } },
      axisLabel: { color: '#64748b', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: { color: '#64748b', fontSize: 11, fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } },
    },
    series: [{
      type: 'line',
      data: data.map((d: any) => d.equity),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#00d4aa', width: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(0, 212, 170, 0.2)' },
            { offset: 1, color: 'rgba(0, 212, 170, 0)' },
          ]
        }
      }
    }]
  }
})

async function runBacktest() {
  loading.value = true
  try {
    const data = await apiPost<any>('/backtest/run?' + new URLSearchParams(config.value as any).toString())
    if (data) {
      result.value = data
    }
  } catch (e) {
    console.error('回测失败', e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.backtest {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

/* Sidebar */
.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 30px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(14, 165, 233, 0.15));
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 170, 0.2);
}

/* Main */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 64px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  padding: 0 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.backtest-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  height: 100%;
}

/* Config Panel */
.config-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 24px;
  height: fit-content;
}

.panel-header {
  margin-bottom: 24px;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 40px;
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  padding: 0 12px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent-primary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.input-with-suffix {
  position: relative;
}

.input-with-suffix .form-input {
  padding-right: 40px;
}

.suffix {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  color: var(--text-muted);
}

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strategy-btn {
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  font-size: 14px;
}

.strategy-btn:hover {
  border-color: var(--bg-hover);
  color: var(--text-primary);
}

.strategy-btn.active {
  border-color: var(--accent-primary);
  background: rgba(0, 212, 170, 0.1);
  color: var(--accent-primary);
}

.mode-options {
  display: flex;
  gap: 8px;
}

.mode-btn {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.mode-btn.active {
  border-color: var(--accent-primary);
  background: rgba(0, 212, 170, 0.1);
  color: var(--accent-primary);
}

.run-btn {
  width: 100%;
  height: 44px;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.run-btn:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Results Panel */
.results-panel {
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  gap: 16px;
}

.empty-icon {
  opacity: 0.5;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.metric-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
}

.chart-card, .trades-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.card-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.trade-count {
  font-size: 13px;
  color: var(--text-muted);
}

.chart-container {
  padding: 16px;
}

.equity-chart {
  width: 100%;
  height: 300px;
}

.trades-table-wrapper {
  max-height: 400px;
  overflow-y: auto;
}

.trades-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.trades-table th {
  text-align: left;
  padding: 12px 20px;
  font-weight: 500;
  color: var(--text-muted);
  font-size: 13px;
  border-bottom: 1px solid var(--border-color);
}

.trades-table td {
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.trades-table tr:last-child td {
  border-bottom: none;
}

.trade-type {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.trade-type.buy {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.trade-type.sell {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.text-right {
  text-align: right;
}

.text-green {
  color: var(--accent-primary);
}

.text-red {
  color: var(--accent-danger);
}

/* Responsive */
@media (max-width: 1200px) {
  .backtest-layout {
    grid-template-columns: 1fr;
  }
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }
  .logo-text, .nav-label {
    display: none;
  }
  .nav-item {
    justify-content: center;
    padding: 12px;
  }
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
