<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h1 class="page-title">投资组合</h1>
      <div class="header-summary">
        <div class="summary-item">
          <span class="summary-label">总资产</span>
          <span class="summary-value mono">{{ fmtMoney(portfolio.total_value) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">总收益</span>
          <span class="summary-value mono" :class="portfolio.total_pnl >= 0 ? 'up' : 'down'">{{ portfolio.total_pnl >= 0 ? '+' : '' }}{{ fmtMoney(portfolio.total_pnl) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">收益率</span>
          <span class="summary-value mono" :class="portfolio.total_return >= 0 ? 'up' : 'down'">{{ (portfolio.total_return || 0) >= 0 ? '+' : '' }}{{ ((portfolio.total_return || 0) * 100).toFixed(2) }}%</span>
        </div>
      </div>
    </div>

    <div class="main-layout">
      <div class="positions-section card">
        <div class="section-header">
          <h2 class="section-title">持仓</h2>
          <span class="pos-count mono">{{ positions.length }} 只</span>
        </div>
        <div v-if="positions.length" class="position-list">
          <div v-for="p in positions" :key="p.symbol" class="position-row" @click="$router.push(`/stock/${p.symbol}`)">
            <div class="pos-main">
              <span class="pos-code mono">{{ p.symbol }}</span>
              <span class="pos-name">{{ p.name }}</span>
            </div>
            <div class="pos-detail">
              <div class="pos-col"><span class="pos-label">持仓</span><span class="pos-val mono">{{ p.shares }}股</span></div>
              <div class="pos-col"><span class="pos-label">成本</span><span class="pos-val mono">{{ (p.avg_cost || 0).toFixed(2) }}</span></div>
              <div class="pos-col"><span class="pos-label">现价</span><span class="pos-val mono">{{ (p.current_price || 0).toFixed(2) }}</span></div>
              <div class="pos-col"><span class="pos-label">市值</span><span class="pos-val mono">{{ fmtMoney(p.market_value) }}</span></div>
              <div class="pos-col"><span class="pos-label">盈亏</span><span class="pos-val mono" :class="p.pnl >= 0 ? 'up' : 'down'">{{ p.pnl >= 0 ? '+' : '' }}{{ fmtMoney(p.pnl) }}</span></div>
              <div class="pos-col"><span class="pos-label">收益率</span><span class="pos-val mono" :class="p.pnl_pct >= 0 ? 'up' : 'down'">{{ (p.pnl_pct || 0) >= 0 ? '+' : '' }}{{ ((p.pnl_pct || 0) * 100).toFixed(2) }}%</span></div>
            </div>
          </div>
        </div>
        <div v-else class="empty-hint">暂无持仓</div>
      </div>

      <div class="side-panel">
        <div class="account-card card">
          <h2 class="section-title">账户信息</h2>
          <div class="account-grid">
            <div class="acct-item"><span class="acct-label">可用资金</span><span class="acct-value mono">{{ fmtMoney(portfolio.cash) }}</span></div>
            <div class="acct-item"><span class="acct-label">冻结资金</span><span class="acct-value mono">{{ fmtMoney(portfolio.frozen_cash) }}</span></div>
            <div class="acct-item"><span class="acct-label">持仓市值</span><span class="acct-value mono">{{ fmtMoney(portfolio.market_value) }}</span></div>
            <div class="acct-item"><span class="acct-label">总资产</span><span class="acct-value mono highlight">{{ fmtMoney(portfolio.total_value) }}</span></div>
          </div>
        </div>

        <div class="allocation-card card">
          <h2 class="section-title">资产配置</h2>
          <div v-if="positions.length" ref="pieChartRef" class="pie-chart"></div>
          <div v-else class="empty-hint">暂无数据</div>
        </div>

        <div class="trades-card card">
          <div class="section-header">
            <h2 class="section-title">最近交易</h2>
          </div>
          <div v-if="recentTrades.length" class="trade-list">
            <div v-for="(t, idx) in recentTrades.slice(0, 10)" :key="idx" class="trade-item" :class="{ buy: t.action === 'buy', sell: t.action === 'sell' }">
              <div class="trade-main">
                <span class="trade-action">{{ t.action === 'buy' ? '买入' : '卖出' }}</span>
                <span class="trade-symbol mono">{{ t.symbol }}</span>
              </div>
              <div class="trade-detail">
                <span class="mono">{{ (t.price || 0).toFixed(2) }}</span>
                <span class="mono">{{ t.shares }}股</span>
                <span class="trade-time">{{ (t.date || '').slice(5, 10) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-hint">暂无交易记录</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from '../api'
import { useToast } from '../composables/useToast'
import echarts from '../lib/echarts'

const toast = useToast()
const portfolio = ref<any>({})
const positions = ref<any[]>([])
const recentTrades = ref<any[]>([])
const pieChartRef = ref<HTMLElement | null>(null)
let pieChart: any = null

function fmtMoney(v: number): string {
  if (!v) return '0.00'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

async function loadPortfolio() {
  try {
    const data = await api.getPortfolio()
    if (data) {
      portfolio.value = data
      positions.value = data.positions || []
    }
  } catch (e) {
    toast.warning(e instanceof Error ? e.message : '组合数据加载失败')
  }
}

async function loadTrades() {
  try {
    const data = await api.getRecentTrades()
    recentTrades.value = Array.isArray(data) ? data : []
  } catch (e) {
    recentTrades.value = []
  }
}

function renderPie() {
  if (!pieChartRef.value || !positions.value.length) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value, undefined, { renderer: 'canvas' })
  }
  const data = positions.value.map(p => ({
    name: p.name || p.symbol,
    value: p.market_value || 0,
  }))
  if (portfolio.value.cash > 0) {
    data.push({ name: '现金', value: portfolio.value.cash })
  }
  pieChart.setOption({
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '50%'],
      data,
      label: { show: true, color: '#8b92a5', fontSize: 9, formatter: '{b}\n{d}%' },
      labelLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      itemStyle: { borderColor: 'var(--bg-elevated)', borderWidth: 2 },
      color: ['#3b82f6', '#8b5cf6', '#f59e0b', '#22c55e', '#ef4444', '#38bdf8', '#fb923c', '#a78bfa', '#f43f5e'],
    }],
  }, true)
}

function handleResize() { pieChart?.resize() }

onMounted(async () => {
  await loadPortfolio()
  loadTrades()
  await nextTick()
  renderPie()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (pieChart) { pieChart.dispose(); pieChart = null }
})

watch(positions, () => { nextTick(renderPie) })
</script>

<style scoped>
.portfolio-page { padding: 14px 16px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.header-summary { display: flex; gap: 16px; }
.summary-item { display: flex; flex-direction: column; gap: 1px; }
.summary-label { font-size: 9px; color: var(--text-tertiary); }
.summary-value { font-size: 14px; font-weight: 700; }
.summary-value.up { color: var(--accent-red); }
.summary-value.down { color: var(--accent-green); }

.main-layout { display: grid; grid-template-columns: 1fr 280px; gap: 10px; }

.positions-section { padding: 12px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 0; }
.pos-count { font-size: 10px; color: var(--text-tertiary); }
.position-list { display: flex; flex-direction: column; gap: 4px; }
.position-row {
  padding: 8px 10px; background: var(--bg-hover); border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--transition-fast);
  border-left: 2px solid transparent;
}
.position-row:hover { background: rgba(255,255,255,0.04); }
.pos-main { display: flex; gap: 8px; align-items: center; margin-bottom: 4px; }
.pos-code { font-size: 11px; color: var(--accent-cyan); }
.pos-name { font-size: 11px; color: var(--text-primary); font-weight: 500; }
.pos-detail { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px 12px; }
.pos-col { display: flex; justify-content: space-between; }
.pos-label { font-size: 9px; color: var(--text-tertiary); }
.pos-val { font-size: 9px; color: var(--text-primary); }
.pos-val.up { color: var(--accent-red); }
.pos-val.down { color: var(--accent-green); }

.side-panel { display: flex; flex-direction: column; gap: 8px; }
.account-card, .allocation-card, .trades-card { padding: 12px; }
.account-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.acct-item { display: flex; flex-direction: column; gap: 1px; padding: 4px 6px; background: var(--bg-hover); border-radius: 3px; }
.acct-label { font-size: 9px; color: var(--text-tertiary); }
.acct-value { font-size: 11px; color: var(--text-primary); }
.acct-value.highlight { color: var(--accent-cyan); font-weight: 600; }
.pie-chart { width: 100%; height: 180px; }

.trade-list { display: flex; flex-direction: column; gap: 2px; }
.trade-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 4px 6px; border-radius: 2px; font-size: 10px;
}
.trade-item.buy { border-left: 2px solid var(--accent-red); }
.trade-item.sell { border-left: 2px solid var(--accent-green); }
.trade-main { display: flex; gap: 6px; }
.trade-action { font-weight: 600; }
.trade-item.buy .trade-action { color: var(--accent-red); }
.trade-item.sell .trade-action { color: var(--accent-green); }
.trade-symbol { color: var(--accent-cyan); }
.trade-detail { display: flex; gap: 6px; color: var(--text-tertiary); }
.trade-time { color: var(--text-tertiary); }

.empty-hint { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 11px; }

@media (max-width: 768px) {
  .portfolio-page { padding: 10px; }
  .main-layout { grid-template-columns: 1fr; }
  .header-summary { gap: 10px; }
  .pos-detail { grid-template-columns: repeat(2, 1fr); }
}
</style>
