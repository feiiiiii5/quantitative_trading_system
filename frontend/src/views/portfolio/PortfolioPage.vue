<template>
  <div class="portfolio-page">
    <section class="metrics-strip">
      <div class="surface-panel metric-block">
        <span class="mb-label">TOTAL ASSETS</span>
        <span class="mb-value">{{ account ? formatNumber(account.total_assets, 0) : '—' }}</span>
      </div>
      <div class="surface-panel metric-block">
        <span class="mb-label">DAILY P&L</span>
        <span class="mb-value" :class="account && account.risk_report?.current_daily_pnl >= 0 ? 'val-rise' : 'val-fall'">
          {{ account ? formatPct(account.risk_report?.current_daily_pnl ?? 0) : '—' }}
        </span>
      </div>
      <div class="surface-panel metric-block">
        <span class="mb-label">AVAILABLE CASH</span>
        <span class="mb-value">{{ account ? formatNumber(account.cash, 0) : '—' }}</span>
      </div>
      <div class="surface-panel metric-block">
        <span class="mb-label">POSITIONS</span>
        <span class="mb-value">{{ account ? String(account.position_count) : '0' }}</span>
      </div>
    </section>

    <div class="surface-panel">
      <div class="panel-header">
        <span class="panel-title">CURRENT HOLDINGS</span>
        <router-link to="/market" class="term-link">+ ADD POSITION</router-link>
      </div>
      <DataTable
        v-if="account?.positions?.length"
        :columns="positionColumns"
        :rows="account.positions as unknown as Record<string, unknown>[]"
        row-key="symbol"
        @row-click="(row: Record<string, unknown>) => goToStock(row.symbol as string)"
      >
        <template #cell-symbol="{ value }">
          <span class="code-text">{{ value }}</span>
        </template>
        <template #cell-name="{ row }">
          <span class="name-text">{{ row.name }}</span>
        </template>
        <template #cell-profit_pct="{ value }">
          <span class="mono" :class="(value as number) >= 0 ? 'val-rise' : 'val-fall'">
            {{ formatPct(value as number) }}
          </span>
        </template>
        <template #cell-weight="{ value }">
          <div class="weight-cell">
            <div class="weight-track">
              <div class="weight-fill" :style="{ width: safeToFixed((value as number ?? 0) * 100, 1) + '%' }" />
            </div>
            <span class="mono weight-val">{{ safeToFixed((value as number ?? 0) * 100, 1) }}%</span>
          </div>
        </template>
      </DataTable>
      <div v-else class="panel-empty">NO POSITIONS</div>
    </div>

    <div class="surface-panel">
      <div class="panel-header"><span class="panel-title">RISK MONITORING</span></div>
      <div v-if="account?.risk_report" class="risk-grid">
        <div class="risk-cell">
          <span class="rc-label">CONCENTRATION</span>
          <span class="rc-value mono">{{ safeToFixed((account.risk_report?.max_concentration ?? 0) * 100, 0) }}%</span>
        </div>
        <div class="risk-cell">
          <span class="rc-label">DAILY P&L</span>
          <span class="rc-value mono" :class="account.risk_report.current_daily_pnl >= 0 ? 'val-rise' : 'val-fall'">
            {{ formatNumber(account.risk_report.current_daily_pnl, 0) }}
          </span>
        </div>
        <div class="risk-cell">
          <span class="rc-label">LOSS LIMIT</span>
          <span class="rc-value mono">{{ formatNumber(account.risk_report.daily_loss_limit, 0) }}</span>
        </div>
        <div class="risk-cell">
          <span class="rc-label">CIRCUIT BREAKER</span>
          <span class="rc-status" :class="account.risk_report.circuit_breaker_active ? 'status-triggered' : 'status-ok'">
            {{ account.risk_report.circuit_breaker_active ? 'TRIGGERED' : 'NORMAL' }}
          </span>
        </div>
        <div class="risk-cell">
          <span class="rc-label">VaR</span>
          <span class="rc-value mono">{{ formatNumber(account.risk_report.var, 0) }}</span>
        </div>
      </div>
      <div v-else class="panel-empty">NO RISK DATA</div>
    </div>

    <div class="surface-panel">
      <div class="panel-header"><span class="panel-title">CORRELATION HEATMAP</span></div>
      <div v-if="correlationData && correlationData.symbols.length > 1" class="heatmap-wrap">
        <BaseChart :option="heatmapOption" :height="Math.max(300, correlationData.symbols.length * 40 + 80) + 'px'" />
      </div>
      <div v-else class="panel-empty">NEED 2+ POSITIONS FOR CORRELATION</div>
    </div>

    <div class="surface-panel">
      <div class="panel-header">
        <span class="panel-title">TRADE HISTORY</span>
        <span class="record-count mono" v-if="tradeHistory.trades?.length">{{ tradeHistory.trades.length }} RECORDS</span>
      </div>
      <DataTable
        v-if="tradeHistory.trades?.length"
        :columns="tradeColumns"
        :rows="tradeHistory.trades.slice(0, 30) as unknown as Record<string, unknown>[]"
        row-key="date"
      >
        <template #cell-direction="{ value }">
          <span class="dir-badge" :class="value === 'buy' ? 'dir-buy' : 'dir-sell'">
            {{ value === 'buy' ? 'BUY' : 'SELL' }}
          </span>
        </template>
        <template #cell-price="{ value }">
          <span class="mono">{{ ((value as number) ?? 0).toFixed(2) }}</span>
        </template>
        <template #cell-amount="{ value }">
          <span class="mono">{{ formatNumber((value as number) ?? 0, 0) }}</span>
        </template>
      </DataTable>
      <div v-else class="panel-empty">NO TRADE HISTORY</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import { createLogger } from '@/composables/useLogger'
import { useRequestCancel } from '@/composables/useRequestCancel'
import { useApiError } from '@/composables/useApiError'
import { api } from '@/api'
import { formatNumber, formatPct, safeToFixed } from '@/utils/format'
import DataTable from '@/components/ui/DataTable.vue'
const BaseChart = defineAsyncComponent(() => import('@/components/chart/BaseChart.vue'))
import type { ColumnDef } from '@/components/ui/DataTable.vue'
import type { TradeRecord } from '@/types'

const log = createLogger('Portfolio')
const { handleApiError } = useApiError()
const { cancelAll } = useRequestCancel()

const router = useRouter()
const portfolioStore = usePortfolioStore()
const { account } = storeToRefs(portfolioStore)

const tradeHistory = ref<{ trades: TradeRecord[]; total: number }>({ trades: [], total: 0 })
const correlationData = ref<{ symbols: string[]; matrix: number[][] } | null>(null)

const heatmapOption = computed(() => {
  if (!correlationData.value || correlationData.value.symbols.length < 2) return {}
  const { symbols, matrix } = correlationData.value
  const data: [number, number, number][] = []
  for (let i = 0; i < symbols.length; i++) {
    for (let j = 0; j < symbols.length; j++) {
      data.push([j, i, matrix[i][j]])
    }
  }
  return {
    tooltip: {
      formatter: (p: { data: number[] }) => {
        const [x, y, val] = p.data
        return `${symbols[y]} vs ${symbols[x]}: ${safeToFixed(val, 2)}`
      },
    },
    grid: { top: 10, right: 60, bottom: 40, left: 80 },
    xAxis: {
      type: 'category',
      data: symbols,
      splitArea: { show: true },
      axisLabel: { fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
    },
    yAxis: {
      type: 'category',
      data: symbols,
      splitArea: { show: true },
      axisLabel: { fontSize: 10, fontFamily: 'JetBrains Mono, monospace' },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      inRange: {
        color: ['#ff3b3b', '#ff8a80', '#fff9c4', '#69f0ae', '#00e676'],
      },
      textStyle: { fontSize: 10 },
    },
    series: [{
      type: 'heatmap',
      data,
      label: {
        show: symbols.length <= 8,
        fontSize: 9,
        fontFamily: 'JetBrains Mono, monospace',
        formatter: (p: { data: number[] }) => safeToFixed(p.data?.[2], 2),
      },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' } },
    }],
  }
})

const positionColumns: ColumnDef[] = [
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'name', label: 'NAME', width: '100px' },
  { key: 'shares', label: 'SHARES', align: 'right', width: '70px' },
  { key: 'avg_cost', label: 'COST', align: 'right', width: '80px', format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'current_price', label: 'PRICE', align: 'right', width: '80px', format: (v: unknown) => safeToFixed(v, 2) },
  { key: 'profit_pct', label: 'P&L%', align: 'right', width: '80px' },
  { key: 'weight', label: 'WEIGHT', align: 'right', width: '140px' },
]

const tradeColumns: ColumnDef[] = [
  { key: 'date', label: 'TIME', width: '140px', format: (v: unknown) => String(v ?? '-').slice(0, 16) },
  { key: 'direction', label: 'DIR', width: '60px', align: 'center' },
  { key: 'symbol', label: 'CODE', width: '90px', code: true },
  { key: 'price', label: 'PRICE', align: 'right', width: '90px' },
  { key: 'shares', label: 'QTY', align: 'right', width: '70px' },
  { key: 'amount', label: 'AMOUNT', align: 'right', width: '100px' },
]

function goToStock(symbol: string) {
  router.push(`/stock/${symbol}`)
}

onMounted(async () => {
  await portfolioStore.fetchAccount()
  try {
    const res = await api.trading.history(50)
    tradeHistory.value = { trades: res?.trades ?? [], total: res?.total ?? 0 }
  } catch (err) {
    handleApiError(err, '获取交易记录失败')
  }
  try {
    const symbols = account.value?.positions?.map(p => p.symbol) ?? []
    if (symbols.length >= 2) {
      const corr = await api.portfolio.correlation(symbols)
      if (corr?.symbols && corr?.matrix) {
        correlationData.value = corr as { symbols: string[]; matrix: number[][] }
      }
    }
  } catch (err) {
    handleApiError(err, '获取相关性数据失败')
  }
})

onUnmounted(cancelAll)
</script>

<style scoped>
.portfolio-page {
  max-width: 1440px;
  margin: 0 auto;
  display: grid;
  gap: var(--u4);
}

.metrics-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.metric-block {
  padding: var(--u4) var(--u5);
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.mb-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.mb-value {
  font-size: var(--fs-xl);
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--u3) var(--u4);
  border-bottom: 1px solid var(--border-hair);
}

.panel-title {
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
}

.term-link {
  font-size: var(--fs-xs);
  color: var(--accent);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 500;
}

.term-link:hover { opacity: 0.8; }

.panel-empty {
  padding: var(--u8) var(--u4);
  text-align: center;
  color: var(--text-muted);
  font-size: var(--fs-xs);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.code-text {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--accent);
  font-size: var(--fs-xs);
}

.name-text { color: var(--text-primary); }

.val-rise { color: var(--rise); }
.val-fall { color: var(--fall); }

.weight-cell {
  display: flex;
  align-items: center;
  gap: var(--u2);
}

.weight-track {
  flex: 1;
  height: 3px;
  background: var(--bg-plate);
  border-radius: 2px;
  overflow: hidden;
}

.weight-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width var(--dur-normal) var(--ease-mechanical);
}

.weight-val {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  min-width: 40px;
  text-align: right;
}

.risk-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 1px;
  background: var(--border-hair);
}

.risk-cell {
  padding: var(--u4);
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  gap: var(--u2);
}

.rc-label {
  font-size: var(--fs-3xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.rc-value {
  font-size: var(--fs-lg);
  font-weight: 600;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}

.rc-status {
  font-size: var(--fs-sm);
  font-weight: 700;
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.status-triggered { color: var(--rise); }
.status-ok { color: var(--teal); }

.dir-badge {
  font-size: var(--fs-3xs);
  font-weight: 700;
  padding: 1px 6px;
  border-radius: var(--r-md);
  font-family: var(--font-mono);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.dir-buy { background: var(--rise-bg); color: var(--rise); }
.dir-sell { background: var(--fall-bg); color: var(--fall); }

.record-count {
  font-size: var(--fs-xs);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.heatmap-wrap {
  width: 100%;
  min-height: 300px;
}

@media (max-width: 1024px) {
  .metrics-strip { grid-template-columns: repeat(2, 1fr); }
  .risk-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 640px) {
  .metrics-strip { grid-template-columns: 1fr; }
  .risk-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
