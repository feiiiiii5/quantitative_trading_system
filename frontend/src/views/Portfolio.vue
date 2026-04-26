<template>
  <div class="portfolio-page fade-in">
    <header class="page-header">
      <div>
        <h1 class="page-title">组合管理</h1>
        <p class="page-subtitle">模拟交易组合与风控监控</p>
      </div>
      <button class="btn btn-ghost" @click="resetPortfolio">重置账户</button>
    </header>

    <div class="summary-grid" v-if="summary">
      <div class="metric-card card">
        <div class="metric-label">总资产</div>
        <div class="metric-value font-mono">{{ fmtMoney(summary.total_assets) }}</div>
      </div>
      <div class="metric-card card">
        <div class="metric-label">可用资金</div>
        <div class="metric-value font-mono">{{ fmtMoney(summary.cash) }}</div>
      </div>
      <div class="metric-card card">
        <div class="metric-label">持仓市值</div>
        <div class="metric-value font-mono">{{ fmtMoney(summary.market_value) }}</div>
      </div>
      <div class="metric-card card">
        <div class="metric-label">总盈亏</div>
        <div class="metric-value font-mono" :class="summary.total_pnl >= 0 ? 'text-up' : 'text-down'">
          {{ summary.total_pnl >= 0 ? '+' : '' }}{{ fmtMoney(summary.total_pnl) }}
        </div>
      </div>
      <div class="metric-card card">
        <div class="metric-label">收益率</div>
        <div class="metric-value font-mono" :class="summary.return_pct >= 0 ? 'text-up' : 'text-down'">
          {{ summary.return_pct >= 0 ? '+' : '' }}{{ (summary.return_pct * 100).toFixed(2) }}%
        </div>
      </div>
      <div class="metric-card card">
        <div class="metric-label">持仓数</div>
        <div class="metric-value font-mono">{{ positions.length }}</div>
      </div>
    </div>

    <div class="grid-2">
      <section class="card">
        <h2 class="section-title">当前持仓</h2>
        <div v-if="positions.length === 0" class="empty-text">暂无持仓</div>
        <div class="positions-table" v-else>
          <div class="table-header">
            <span>代码</span><span>名称</span><span class="r">持仓</span><span class="r">成本</span><span class="r">现价</span><span class="r">盈亏</span><span class="r">盈亏%</span>
          </div>
          <div v-for="p in positions" :key="p.symbol" class="table-row" @click="goStock(p.symbol)">
            <span class="font-mono code">{{ p.symbol }}</span>
            <span>{{ p.name }}</span>
            <span class="r font-mono">{{ p.quantity }}</span>
            <span class="r font-mono">{{ p.avg_cost?.toFixed(2) }}</span>
            <span class="r font-mono">{{ p.current_price?.toFixed(2) || '-' }}</span>
            <span class="r font-mono" :class="p.pnl >= 0 ? 'text-up' : 'text-down'">{{ p.pnl >= 0 ? '+' : '' }}{{ p.pnl?.toFixed(2) }}</span>
            <span class="r font-mono" :class="p.pnl_pct >= 0 ? 'text-up' : 'text-down'">{{ p.pnl_pct >= 0 ? '+' : '' }}{{ (p.pnl_pct * 100).toFixed(2) }}%</span>
          </div>
        </div>
      </section>

      <section class="card">
        <h2 class="section-title">交易记录</h2>
        <div v-if="trades.length === 0" class="empty-text">暂无交易记录</div>
        <div class="trades-table" v-else>
          <div class="table-header">
            <span>时间</span><span>代码</span><span>方向</span><span class="r">价格</span><span class="r">数量</span>
          </div>
          <div v-for="t in trades" :key="t.id" class="table-row">
            <span class="font-mono">{{ t.trade_time?.slice(5, 16) }}</span>
            <span class="font-mono code">{{ t.symbol }}</span>
            <span :class="t.direction === 'BUY' ? 'text-up' : 'text-down'">{{ t.direction === 'BUY' ? '买入' : '卖出' }}</span>
            <span class="r font-mono">{{ t.price?.toFixed(2) }}</span>
            <span class="r font-mono">{{ t.quantity }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const summary = ref<any>({})
const positions = ref<any[]>([])
const trades = ref<any[]>([])

function fmtMoney(v: number) {
  if (v == null) return '-'
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function goStock(code: string) { router.push(`/stock/${code}`) }

async function loadData() {
  try { summary.value = await api.getPortfolioSummary() } catch {}
  try { positions.value = await api.getPortfolioPositions() } catch {}
  try { trades.value = await api.getPortfolioTrades() } catch {}
}

async function resetPortfolio() {
  if (!confirm('确定要重置账户？所有持仓和交易记录将被清除。')) return
  try {
    await api.resetPortfolio()
    await loadData()
  } catch (e: any) {
    alert(`重置失败: ${e.message}`)
  }
}

onMounted(loadData)
</script>

<style scoped>
.portfolio-page { padding: 24px 28px; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.metric-card { padding: 16px; }
.metric-label { font-size: 11px; color: var(--text-tertiary); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.metric-value { font-size: 18px; font-weight: 700; }

.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.empty-text { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 13px; }

.positions-table .table-header,
.trades-table .table-header {
  display: grid;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.positions-table .table-header { grid-template-columns: 70px 1fr 50px 60px 60px 70px 60px; }
.trades-table .table-header { grid-template-columns: 80px 70px 40px 60px 50px; }

.positions-table .table-row,
.trades-table .table-row {
  display: grid;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background var(--transition);
}

.positions-table .table-row { grid-template-columns: 70px 1fr 50px 60px 60px 70px 60px; }
.trades-table .table-row { grid-template-columns: 80px 70px 40px 60px 50px; cursor: default; }

.table-row:hover { background: rgba(255,255,255,0.02); }
.r { text-align: right; }
.code { color: var(--accent-cyan); }
</style>
