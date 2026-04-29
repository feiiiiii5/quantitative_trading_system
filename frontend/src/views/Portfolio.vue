<template>
  <div class="portfolio-page">
    <div v-if="loading" class="skeleton-portfolio">
      <div class="skeleton-row">
        <div class="skeleton" style="height:60px;flex:1;border-radius:8px" v-for="i in 4" :key="i"></div>
      </div>
      <div class="skeleton-row" style="margin-top:12px">
        <div class="skeleton" style="height:300px;flex:2;border-radius:8px"></div>
        <div class="skeleton" style="height:300px;flex:1;border-radius:8px;margin-left:12px"></div>
      </div>
    </div>
    <template v-else>
    <div class="page-header">
      <h1 class="page-title">投资组合</h1>
      <div class="header-actions">
        <button class="action-btn" @click="loadData">刷新</button>
      </div>
    </div>

    <div class="summary-row">
      <div class="summary-card total">
        <span class="summary-label">总资产</span>
        <span class="summary-value">¥{{ fmtNum(account.total_assets || 0) }}</span>
      </div>
      <div class="summary-card" :class="account.total_pnl >= 0 ? 'up' : 'down'">
        <span class="summary-label">总盈亏</span>
        <span class="summary-value">{{ account.total_pnl >= 0 ? '+' : '' }}¥{{ fmtNum(account.total_pnl || 0) }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">持仓市值</span>
        <span class="summary-value">¥{{ fmtNum(account.position_value || 0) }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">可用资金</span>
        <span class="summary-value">¥{{ fmtNum(account.available_cash || 0) }}</span>
      </div>
      <div class="summary-card">
        <span class="summary-label">持仓数</span>
        <span class="summary-value">{{ positions.length }}</span>
      </div>
    </div>

    <div class="main-grid">
      <div class="positions-section">
        <h2 class="section-title">持仓列表</h2>
        <DataTable v-if="positions.length" :columns="positionColumns" :data="positions" :striped="true" row-key="symbol" :row-click="(r: any) => $router.push(`/stock/${r.symbol}`)" />
        <div v-else class="empty-state-small">暂无持仓</div>
      </div>

      <div class="right-col">
        <div class="risk-section">
          <h2 class="section-title">风险指标</h2>
          <div v-if="riskMetrics" class="risk-grid">
            <div class="risk-item"><span class="risk-label">夏普比率</span><span class="risk-value">{{ (riskMetrics.sharpe || 0).toFixed(2) }}</span></div>
            <div class="risk-item"><span class="risk-label">最大回撤</span><span class="risk-value down">{{ ((riskMetrics.max_drawdown || 0) * 100).toFixed(2) }}%</span></div>
            <div class="risk-item"><span class="risk-label">波动率</span><span class="risk-value">{{ ((riskMetrics.volatility || 0) * 100).toFixed(2) }}%</span></div>
            <div class="risk-item"><span class="risk-label">Beta</span><span class="risk-value">{{ (riskMetrics.beta || 1).toFixed(2) }}</span></div>
            <div class="risk-item"><span class="risk-label">集中度</span><span class="risk-value">{{ ((riskMetrics.concentration || 0) * 100).toFixed(1) }}%</span></div>
            <div class="risk-item"><span class="risk-label">CVaR(95%)</span><span class="risk-value down">{{ ((riskMetrics.cvar_95 || 0) * 100).toFixed(2) }}%</span></div>
          </div>
          <div v-else class="empty-state-small">加载中...</div>
        </div>

        <div class="attribution-section">
          <h2 class="section-title">收益归因</h2>
          <div v-if="attribution" ref="attributionChartRef" class="attribution-chart"></div>
          <div v-else class="empty-state-small">加载中...</div>
        </div>
      </div>
    </div>

    <div class="equity-section" v-if="equityCurve.length">
      <h2 class="section-title">组合净值曲线</h2>
      <BaseChart :option="equityOption" height="250px" />
    </div>

    <div class="trades-section">
      <h2 class="section-title">交易记录</h2>
      <DataTable v-if="tradeHistory.length" :columns="tradeColumns" :data="tradeHistory" :striped="true" row-key="id" />
      <div v-else class="empty-state-small">暂无交易记录</div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { api } from '../api'
import echarts from '../lib/echarts'
import { DataTable, BaseChart } from '../components'

const account = ref<any>({})
const positions = ref<any[]>([])
const riskMetrics = ref<any>(null)
const attribution = ref<any>(null)
const loading = ref(true)
const equityCurve = ref<any[]>([])
const tradeHistory = ref<any[]>([])
const attributionChartRef = ref<HTMLElement | null>(null)
let attrChart: any = null

const positionColumns = [
  { key: 'symbol', label: '代码', width: '70px' },
  { key: 'name', label: '名称', width: '80px' },
  { key: 'shares', label: '持仓', align: 'right' as const },
  { key: 'avg_cost', label: '成本', align: 'right' as const, format: (v: number) => v?.toFixed(2) },
  { key: 'current_price', label: '现价', align: 'right' as const, format: (v: number) => v?.toFixed(2) },
  { key: 'market_value', label: '市值', align: 'right' as const, format: (v: number) => '¥' + (v || 0).toLocaleString() },
  { key: 'pnl', label: '盈亏', align: 'right' as const, format: (v: number) => v ? (v >= 0 ? '+' : '') + '¥' + v.toLocaleString() : '-' },
  { key: 'pnl_pct', label: '盈亏%', align: 'right' as const, format: (v: number) => v ? (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%' : '-' },
  { key: 'weight', label: '占比', align: 'right' as const, format: (v: number) => (v * 100).toFixed(1) + '%' },
]

const tradeColumns = [
  { key: 'time', label: '时间', width: '130px' },
  { key: 'symbol', label: '代码', width: '70px' },
  { key: 'name', label: '名称', width: '80px' },
  { key: 'side', label: '方向', width: '50px' },
  { key: 'price', label: '价格', align: 'right' as const, format: (v: number) => v?.toFixed(2) },
  { key: 'shares', label: '数量', align: 'right' as const },
  { key: 'amount', label: '金额', align: 'right' as const, format: (v: number) => '¥' + (v || 0).toLocaleString() },
  { key: 'pnl', label: '盈亏', align: 'right' as const, format: (v: number) => v ? (v >= 0 ? '+' : '') + '¥' + v.toLocaleString() : '-' },
]

function fmtNum(n: number): string {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const equityOption = computed(() => {
  if (!equityCurve.value.length) return {}
  const dates = equityCurve.value.map(d => (d.date || '').slice(0, 10))
  const values = equityCurve.value.map(d => d.value || d.equity)
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    series: [{ type: 'line', data: values, showSymbol: false, lineStyle: { width: 1.5, color: '#4d9fff' }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(77,159,255,0.12)' }, { offset: 1, color: 'rgba(77,159,255,0)' }] } } }],
  }
})

function renderAttributionChart() {
  if (!attributionChartRef.value || !attribution.value) return
  if (!attrChart) {
    attrChart = echarts.init(attributionChartRef.value, undefined, { renderer: 'canvas' })
  }
  const attr = attribution.value
  const items = Object.entries(attr).filter(([_, v]) => typeof v === 'number').map(([k, v]) => ({ name: k, value: v as number }))
  attrChart.setOption({
    animation: false,
    tooltip: { trigger: 'item', formatter: '{b}: {c}%' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '50%'],
      data: items.map(d => ({
        name: d.name, value: Math.abs(d.value).toFixed(1),
        itemStyle: { color: d.value >= 0 ? '#4d9fff' : '#f43f5e' },
      })),
      label: { color: '#888', fontSize: 10 },
    }],
  }, true)
}

async function loadData() {
  try {
    const acc = await api.getAccount()
    if (acc) {
      account.value = acc
      positions.value = acc.positions || []
    }
    const syms = positions.value.map((p: any) => p.symbol).join(',')
    const [risk, attr, eq, trades] = await Promise.allSettled([
      syms ? api.getPortfolioRiskAnalysis(syms) : Promise.resolve(null),
      syms ? api.getPortfolioAttribution(syms) : Promise.resolve(null),
      syms ? api.getPortfolioEquity(syms) : Promise.resolve(null),
      api.getTradeHistory(),
    ])
    if (risk.status === 'fulfilled' && risk.value) riskMetrics.value = risk.value
    if (attr.status === 'fulfilled' && attr.value) {
      attribution.value = attr.value
      nextTick(() => renderAttributionChart())
    }
    if (eq.status === 'fulfilled' && eq.value) equityCurve.value = eq.value.equity_curve || eq.value || []
    if (trades.status === 'fulfilled' && trades.value) tradeHistory.value = trades.value.trades || trades.value || []
  } catch (e) {
    console.error('Load portfolio error:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => loadData())
</script>

<style scoped>
.skeleton-portfolio { padding: 20px; }
.skeleton-row { display: flex; gap: 12px; }
.skeleton { border-radius: 8px; background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary, #1a1a24) 50%, var(--bg-secondary) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.portfolio-page { padding: 20px; max-width: 1440px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.action-btn { padding: 6px 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 12px; cursor: pointer; }
.action-btn:hover { color: var(--text-primary); }

.summary-row { display: flex; gap: 10px; margin-bottom: 16px; overflow-x: auto; }
.summary-card { flex: 1; min-width: 120px; padding: 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); }
.summary-card.total { border-left: 3px solid var(--accent-cyan); }
.summary-card.up { border-left: 3px solid var(--accent-red); }
.summary-card.down { border-left: 3px solid var(--accent-green); }
.summary-label { display: block; font-size: 10px; color: var(--text-tertiary); margin-bottom: 4px; }
.summary-value { font-size: 16px; font-weight: 700; font-family: var(--font-mono); color: var(--text-primary); }
.summary-card.up .summary-value { color: var(--accent-red); }
.summary-card.down .summary-value { color: var(--accent-green); }

.main-grid { display: grid; grid-template-columns: 1fr 320px; gap: 14px; margin-bottom: 14px; }
.right-col { display: flex; flex-direction: column; gap: 14px; }

.positions-section, .risk-section, .attribution-section, .equity-section, .trades-section {
  background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px;
}

.section-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }

.risk-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.risk-item { display: flex; justify-content: space-between; padding: 6px 8px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); }
.risk-label { font-size: 11px; color: var(--text-secondary); }
.risk-value { font-size: 11px; font-family: var(--font-mono); color: var(--text-primary); font-weight: 600; }
.risk-value.down { color: var(--accent-green); }

.attribution-chart { width: 100%; height: 200px; }
.empty-state-small { text-align: center; padding: 30px; color: var(--text-tertiary); font-size: 13px; }

@media (max-width: 1024px) {
  .main-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .portfolio-page { padding: 10px; }
  .summary-row { flex-wrap: wrap; }
  .summary-card { min-width: 100px; }
}
</style>
