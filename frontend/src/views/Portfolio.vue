<template>
  <div class="portfolio">
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

    <main class="main">
      <header class="header">
        <h1 class="page-title">投资组合</h1>
        <div class="header-actions">
          <button class="action-btn" @click="refreshData">
            <IconRefresh :size="16" :class="{ 'is-loading': refreshing }" />
          </button>
        </div>
      </header>

      <div class="content">
        <!-- Overview Cards -->
        <div class="overview-grid">
          <div class="overview-card">
            <div class="overview-label">总资产</div>
            <div class="overview-value font-mono">{{ formatMoney(totalAssets) }}</div>
            <div class="overview-change" :class="totalReturn >= 0 ? 'text-green' : 'text-red'">
              {{ totalReturn >= 0 ? '+' : '' }}{{ totalReturn.toFixed(2) }}%
            </div>
          </div>
          <div class="overview-card">
            <div class="overview-label">可用资金</div>
            <div class="overview-value font-mono">{{ formatMoney(cash) }}</div>
          </div>
          <div class="overview-card">
            <div class="overview-label">持仓市值</div>
            <div class="overview-value font-mono">{{ formatMoney(positionValue) }}</div>
          </div>
          <div class="overview-card">
            <div class="overview-label">今日盈亏</div>
            <div class="overview-value font-mono" :class="todayPnl >= 0 ? 'text-green' : 'text-red'">
              {{ todayPnl >= 0 ? '+' : '' }}{{ formatMoney(todayPnl) }}
            </div>
          </div>
        </div>

        <!-- Positions Table -->
        <div class="positions-section">
          <div class="section-header">
            <h2>持仓明细</h2>
            <span class="position-count">共 {{ positions.length }} 只</span>
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th class="text-right">持仓</th>
                  <th class="text-right">成本价</th>
                  <th class="text-right">现价</th>
                  <th class="text-right">市值</th>
                  <th class="text-right">盈亏</th>
                  <th class="text-right">盈亏比</th>
                  <th>占比</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="pos in positions" :key="pos.symbol">
                  <td class="font-mono">{{ pos.symbol }}</td>
                  <td>{{ pos.name }}</td>
                  <td class="text-right font-mono">{{ pos.quantity }}</td>
                  <td class="text-right font-mono">{{ pos.cost_price?.toFixed(2) }}</td>
                  <td class="text-right font-mono">{{ pos.current_price?.toFixed(2) }}</td>
                  <td class="text-right font-mono">{{ formatMoney(pos.market_value) }}</td>
                  <td class="text-right font-mono" :class="pos.pnl >= 0 ? 'text-green' : 'text-red'">
                    {{ pos.pnl >= 0 ? '+' : '' }}{{ formatMoney(pos.pnl) }}
                  </td>
                  <td class="text-right">
                    <span class="pct-badge" :class="pos.pnl_pct >= 0 ? 'up' : 'down'">
                      {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct?.toFixed(2) }}%
                    </span>
                  </td>
                  <td>
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: pos.weight + '%' }"></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Allocation Chart -->
        <div class="chart-section">
          <div class="section-header">
            <h2>资产配置</h2>
          </div>
          <div class="chart-grid">
            <div class="chart-card">
              <v-chart class="pie-chart" :option="allocationOption" autoresize />
            </div>
            <div class="chart-card">
              <v-chart class="line-chart" :option="historyOption" autoresize />
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { IconHome, IconBarChart, IconThunderbolt, IconDashboard, IconRefresh } from '@arco-design/web-vue/es/icon'

use([CanvasRenderer, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent])

const refreshing = ref(false)
const totalAssets = ref(1250000)
const cash = ref(350000)
const totalReturn = ref(12.5)
const todayPnl = ref(8500)

const positionValue = computed(() => totalAssets.value - cash.value)

const positions = ref([
  { symbol: '000001', name: '平安银行', quantity: 5000, cost_price: 12.50, current_price: 14.20, market_value: 71000, pnl: 8500, pnl_pct: 13.6, weight: 7.9 },
  { symbol: '600519', name: '贵州茅台', quantity: 100, cost_price: 1680.00, current_price: 1750.00, market_value: 175000, pnl: 7000, pnl_pct: 4.17, weight: 19.4 },
  { symbol: '000858', name: '五粮液', quantity: 800, cost_price: 145.00, current_price: 152.00, market_value: 121600, pnl: 5600, pnl_pct: 4.83, weight: 13.5 },
  { symbol: '601318', name: '中国平安', quantity: 2000, cost_price: 48.00, current_price: 52.00, market_value: 104000, pnl: 8000, pnl_pct: 8.33, weight: 11.6 },
  { symbol: '600036', name: '招商银行', quantity: 3000, cost_price: 35.00, current_price: 38.50, market_value: 115500, pnl: 10500, pnl_pct: 10.0, weight: 12.8 },
])

const allocationOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(17, 24, 39, 0.95)',
    borderColor: '#334155',
    textStyle: { color: '#e0e0e0' },
  },
  legend: {
    orient: 'vertical',
    right: 16,
    top: 'center',
    textStyle: { color: '#94a3b8' },
  },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    center: ['35%', '50%'],
    avoidLabelOverlap: false,
    itemStyle: { borderRadius: 8, borderColor: '#111827', borderWidth: 2 },
    label: { show: false },
    data: positions.value.map(p => ({ value: p.market_value, name: p.name })).concat([{ value: cash.value, name: '现金' }]),
    color: ['#00d4aa', '#0ea5e9', '#f59e0b', '#ef4444', '#a855f7', '#64748b'],
  }]
}))

const historyOption = computed(() => ({
  backgroundColor: 'transparent',
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(17, 24, 39, 0.95)',
    borderColor: '#334155',
    textStyle: { color: '#e0e0e0' },
  },
  grid: { left: 48, right: 16, top: 16, bottom: 32 },
  xAxis: {
    type: 'category',
    data: ['1月', '2月', '3月', '4月', '5月', '6月'],
    axisLine: { lineStyle: { color: '#334155' } },
    axisLabel: { color: '#64748b' },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisLabel: { color: '#64748b', fontFamily: 'JetBrains Mono' },
    splitLine: { lineStyle: { color: '#1e293b', type: 'dashed' } },
  },
  series: [{
    type: 'line',
    data: [100, 102, 105, 103, 108, 112.5],
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
}))

function formatMoney(v: number) {
  if (!v) return '¥0.00'
  return '¥' + v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function refreshData() {
  refreshing.value = true
  setTimeout(() => refreshing.value = false, 1000)
}

const navItems = [
  { path: '/dashboard', icon: 'IconHome', label: '首页' },
  { path: '/backtest', icon: 'IconBarChart', label: '回测' },
  { path: '/strategy', icon: 'IconThunderbolt', label: '策略' },
  { path: '/portfolio', icon: 'IconDashboard', label: '组合' },
]

const iconMap: Record<string, any> = { IconHome, IconBarChart, IconThunderbolt, IconDashboard }
</script>

<style scoped>
.portfolio {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

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
  justify-content: space-between;
  padding: 0 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

/* Overview */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.overview-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.overview-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.overview-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.overview-change {
  font-size: 14px;
  font-weight: 600;
}

/* Positions */
.positions-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.section-header h2 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.position-count {
  font-size: 13px;
  color: var(--text-muted);
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table th {
  text-align: left;
  padding: 14px 20px;
  font-weight: 500;
  color: var(--text-muted);
  font-size: 13px;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.data-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.pct-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.pct-badge.up {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.pct-badge.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.progress-bar {
  width: 80px;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* Charts */
.chart-section {
  margin-bottom: 24px;
}

.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.pie-chart, .line-chart {
  width: 100%;
  height: 300px;
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

.font-mono {
  font-family: 'JetBrains Mono', monospace;
}

@media (max-width: 1200px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .chart-grid {
    grid-template-columns: 1fr;
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
  .overview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
