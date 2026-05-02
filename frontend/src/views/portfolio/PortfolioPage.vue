<template>
  <div class="portfolio-page">
    <div class="page-header">
      <h1 class="page-title">投资组合</h1>
    </div>

    <div class="portfolio-grid">
      <section class="account-panel panel">
        <div class="panel-title">账户概览</div>
        <div class="account-content" v-if="account">
          <div class="account-hero">
            <div class="hero-metric">
              <span class="hero-label">总资产</span>
              <span class="hero-value mono">{{ formatNumber(account.total_assets, 0) }}</span>
            </div>
            <div class="hero-metric">
              <span class="hero-label">总收益</span>
              <span class="hero-value mono" :class="account.total_profit >= 0 ? 'text-rise' : 'text-fall'">
                {{ account.total_profit >= 0 ? '+' : '' }}{{ formatNumber(account.total_profit, 0) }}
              </span>
            </div>
            <div class="hero-metric">
              <span class="hero-label">收益率</span>
              <span class="hero-value mono" :class="account.return_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ account.return_pct >= 0 ? '+' : '' }}{{ account.return_pct.toFixed(2) }}%
              </span>
            </div>
          </div>
          <div class="account-details">
            <div class="detail-item">
              <span class="detail-label">初始资金</span>
              <span class="detail-value mono">{{ formatNumber(account.initial_capital, 0) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">现金</span>
              <span class="detail-value mono">{{ formatNumber(account.cash, 0) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">持仓市值</span>
              <span class="detail-value mono">{{ formatNumber(account.market_value, 0) }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">持仓数量</span>
              <span class="detail-value mono">{{ account.position_count }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="positions-panel panel">
        <div class="panel-title">当前持仓</div>
        <div class="positions-content" v-if="account?.positions?.length">
          <table class="pos-table">
            <thead>
              <tr>
                <th>股票</th>
                <th>数量</th>
                <th>成本</th>
                <th>现价</th>
                <th>盈亏</th>
                <th>盈亏%</th>
                <th>权重</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in account.positions" :key="p.symbol">
                <td>
                  <div class="pos-name">{{ p.name }}</div>
                  <div class="pos-code mono">{{ p.symbol }}</div>
                </td>
                <td class="mono">{{ p.shares }}</td>
                <td class="mono">{{ p.avg_cost.toFixed(2) }}</td>
                <td class="mono">{{ p.current_price.toFixed(2) }}</td>
                <td class="mono" :class="p.profit >= 0 ? 'text-rise' : 'text-fall'">
                  {{ p.profit >= 0 ? '+' : '' }}{{ formatNumber(p.profit, 0) }}
                </td>
                <td class="mono" :class="p.profit_pct >= 0 ? 'text-rise' : 'text-fall'">
                  {{ p.profit_pct >= 0 ? '+' : '' }}{{ p.profit_pct.toFixed(2) }}%
                </td>
                <td class="mono">{{ (p.weight * 100).toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">暂无持仓</div>
      </section>

      <section class="risk-panel panel">
        <div class="panel-title">风险监控</div>
        <div class="risk-content" v-if="account?.risk_report">
          <div class="risk-items">
            <div class="risk-item">
              <span class="risk-label">最大集中度</span>
              <span class="risk-value mono">{{ (account.risk_report.max_concentration * 100).toFixed(0) }}%</span>
            </div>
            <div class="risk-item">
              <span class="risk-label">当日盈亏</span>
              <span class="risk-value mono" :class="account.risk_report.current_daily_pnl >= 0 ? 'text-rise' : 'text-fall'">
                {{ formatNumber(account.risk_report.current_daily_pnl, 0) }}
              </span>
            </div>
            <div class="risk-item">
              <span class="risk-label">日损失限额</span>
              <span class="risk-value mono">{{ formatNumber(account.risk_report.daily_loss_limit, 0) }}</span>
            </div>
            <div class="risk-item">
              <span class="risk-label">熔断状态</span>
              <span class="risk-value" :class="account.risk_report.circuit_breaker_active ? 'text-rise' : 'text-fall'">
                {{ account.risk_report.circuit_breaker_active ? '已触发' : '正常' }}
              </span>
            </div>
            <div class="risk-item">
              <span class="risk-label">VaR</span>
              <span class="risk-value mono">{{ formatNumber(account.risk_report.var, 0) }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="history-panel panel">
        <div class="panel-title">交易记录</div>
        <div class="history-content" v-if="tradeHistory.trades?.length">
          <table class="history-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>股票</th>
                <th>方向</th>
                <th>价格</th>
                <th>数量</th>
                <th>金额</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(t, i) in tradeHistory.trades.slice(0, 20)" :key="i">
                <td class="mono">{{ t.timestamp?.slice(0, 16) || '-' }}</td>
                <td>{{ t.name || t.symbol }}</td>
                <td :class="t.side === 'buy' ? 'text-rise' : 'text-fall'">{{ t.side === 'buy' ? '买入' : '卖出' }}</td>
                <td class="mono">{{ t.price?.toFixed(2) }}</td>
                <td class="mono">{{ t.shares }}</td>
                <td class="mono">{{ formatNumber(t.total || t.price * t.shares, 0) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">暂无交易记录</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { api } from '@/api'
import { formatNumber } from '@/utils/format'
import { storeToRefs } from 'pinia'

const portfolioStore = usePortfolioStore()
const { account } = storeToRefs(portfolioStore)
const tradeHistory = ref<{ trades: unknown[]; total: number }>({ trades: [], total: 0 })

onMounted(async () => {
  await portfolioStore.fetchAccount()
  try {
    tradeHistory.value = await api.trading.history(50)
  } catch {
    // silent
  }
})
</script>

<style scoped>
.portfolio-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--space-4);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: 600;
}

.portfolio-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.panel {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.panel-title {
  padding: var(--space-3) var(--space-4);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}

.account-content {
  padding: var(--space-4);
}

.account-hero {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
  background: var(--bg-gradient-card);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.hero-label {
  display: block;
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.hero-value {
  font-size: var(--text-xl);
  font-weight: 600;
}

.account-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

.detail-item {
  display: flex;
  justify-content: space-between;
}

.detail-label {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
}

.detail-value {
  font-size: var(--text-sm);
}

.positions-content,
.history-content {
  overflow-x: auto;
}

.pos-table,
.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-xs);
}

.pos-table th,
.history-table th {
  padding: var(--space-2) var(--space-3);
  text-align: left;
  font-weight: 500;
  color: var(--text-tertiary);
  font-size: 10px;
  background: var(--bg-elevated);
  white-space: nowrap;
}

.pos-table td,
.history-table td {
  padding: var(--space-2) var(--space-3);
  white-space: nowrap;
}

.pos-table tbody tr:nth-child(even),
.history-table tbody tr:nth-child(even) {
  background: var(--bg-hover);
}

.pos-table tbody tr,
.history-table tbody tr {
  transition: background var(--transition-fast);
}

.pos-name {
  font-size: var(--text-sm);
}

.pos-code {
  font-size: 10px;
  color: var(--text-tertiary);
}

.risk-content {
  padding: var(--space-4);
}

.risk-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.risk-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border);
}

.risk-item:last-child {
  border-bottom: none;
}

.risk-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.risk-label::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  flex-shrink: 0;
}

.risk-value {
  font-size: var(--text-sm);
  font-weight: 500;
}

.empty-state {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}

.account-panel {
  grid-column: 1 / -1;
}
</style>
