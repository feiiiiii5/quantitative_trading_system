<template>
  <div class="strategy-page">
    <div class="page-header">
      <h1 class="page-title">策略中心</h1>
      <button class="btn-primary" @click="showNewStrategy = true">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
        新建策略
      </button>
    </div>

    <div v-if="showNewStrategy" class="modal-overlay" @click.self="showNewStrategy = false">
      <div class="modal-card">
        <h2 class="modal-title">新建策略</h2>
        <div class="form-row">
          <label>策略名称</label>
          <input v-model="newStrategy.name" placeholder="输入策略名称" class="form-input" />
        </div>
        <div class="form-row">
          <label>策略类型</label>
          <select v-model="newStrategy.type" class="form-input">
            <optgroup label="趋势跟踪">
              <option value="dual_ma">双均线</option>
              <option value="supertrend">SuperTrend</option>
              <option value="adaptive_trend">自适应趋势</option>
              <option value="turtle_trading">海龟交易</option>
              <option value="donchian_channel">唐奇安通道</option>
            </optgroup>
            <optgroup label="动量/突破">
              <option value="macd">MACD</option>
              <option value="momentum">动量</option>
              <option value="dual_thrust">Dual Thrust</option>
              <option value="atr_channel_breakout">ATR通道突破</option>
              <option value="bollinger_breakout">布林突破</option>
              <option value="volatility_squeeze">波动率收缩突破</option>
            </optgroup>
            <optgroup label="均值回归">
              <option value="mean_reversion_pro">均值回归增强</option>
              <option value="rsi_mean_reversion">RSI均值回归</option>
              <option value="kdj">KDJ</option>
              <option value="vwap_deviation">VWAP偏离</option>
            </optgroup>
            <optgroup label="高级策略">
              <option value="multi_factor">多因子共振</option>
              <option value="ichimoku">一目均衡</option>
              <option value="fractal_breakout">分形突破</option>
              <option value="wyckoff">威科夫积累</option>
              <option value="elliott_wave">艾略特波浪</option>
              <option value="regime_switching">机制转换</option>
              <option value="chande_kroll">Chande-Kroll止损</option>
              <option value="vw_macd">量价MACD</option>
              <option value="order_flow_imbalance">订单流失衡</option>
              <option value="market_microstructure">市场微观结构</option>
              <option value="copula_correlation">Copula相关性</option>
              <option value="quantile_regression">分位数回归</option>
            </optgroup>
            <optgroup label="综合引擎">
              <option value="adaptive">自适应量化引擎</option>
            </optgroup>
          </select>
        </div>
        <div class="form-row">
          <label>股票代码</label>
          <div class="search-row">
            <input v-model="newStrategy.symbol" placeholder="如 600519 或 贵州茅台" class="form-input" @input="onSymbolSearch" />
            <div v-if="searchResults.length" class="search-dropdown">
              <div v-for="r in searchResults" :key="r.code" class="search-item" @click="selectSymbol(r)">
                <span class="search-code mono">{{ r.code }}</span>
                <span class="search-name">{{ r.name }}</span>
                <span class="search-market">{{ r.market }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="form-row">
          <label>初始资金</label>
          <input v-model.number="newStrategy.capital" type="number" placeholder="1000000" class="form-input" />
        </div>
        <div class="form-row">
          <label>回测区间</label>
          <div class="date-row">
            <input v-model="newStrategy.start_date" type="date" class="form-input" />
            <span class="date-sep">至</span>
            <input v-model="newStrategy.end_date" type="date" class="form-input" />
          </div>
        </div>
        <div class="modal-btns">
          <button class="btn-save" @click="createStrategy" :disabled="creating">{{ creating ? '创建中...' : '创建并回测' }}</button>
          <button class="btn-cancel" @click="showNewStrategy = false">取消</button>
        </div>
      </div>
    </div>

    <div v-if="strategies.length" class="strategy-list">
      <div v-for="s in strategies" :key="s.id" class="strategy-card card" @click="selectStrategy(s)">
        <div class="card-header">
          <div class="card-title-row">
            <span class="strategy-name">{{ s.name }}</span>
            <span class="strategy-type badge">{{ typeLabel(s.type) }}</span>
          </div>
          <div class="card-meta">
            <span class="meta-item mono">{{ s.symbol }}</span>
            <span class="meta-item">{{ s.start_date }} ~ {{ s.end_date }}</span>
          </div>
        </div>
        <div v-if="s.result && !s.result.error" class="card-metrics">
          <div class="metric">
            <span class="metric-label">总收益</span>
            <span class="metric-value mono" :class="s.result.total_return >= 0 ? 'up' : 'down'">{{ pct(s.result.total_return) }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">最大回撤</span>
            <span class="metric-value mono down">{{ pct(s.result.max_drawdown) }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">夏普比率</span>
            <span class="metric-value mono">{{ (s.result.sharpe_ratio || 0).toFixed(2) }}</span>
          </div>
          <div class="metric">
            <span class="metric-label">胜率</span>
            <span class="metric-value mono">{{ pct(s.result.win_rate) }}</span>
          </div>
        </div>
        <div v-else-if="s.result && s.result.error" class="card-metrics">
          <span class="metric-error">{{ s.result.error }}</span>
        </div>
        <div v-else class="card-metrics">
          <span class="metric-pending">回测中...</span>
        </div>
        <div class="card-actions">
          <button class="action-btn" @click.stop="rerunBacktest(s)">重新回测</button>
          <button class="action-btn danger" @click.stop="deleteStrategy(s.id)">删除</button>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      <span>暂无策略</span>
      <button class="btn-primary" @click="showNewStrategy = true">创建第一个策略</button>
    </div>

    <div v-if="selectedStrategy" class="detail-panel card">
      <div class="detail-header">
        <h2 class="detail-title">{{ selectedStrategy.name }}</h2>
        <button class="close-btn" @click="selectedStrategy = null">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <div v-if="selectedStrategy.result && !selectedStrategy.result.error" class="detail-content">
        <div class="detail-metrics">
          <MetricCard label="总收益" :value="pct(selectedStrategy.result.total_return)" :positive="selectedStrategy.result.total_return >= 0 ? 'up' : 'down'" />
          <MetricCard label="年化收益" :value="pct(selectedStrategy.result.annual_return)" :positive="selectedStrategy.result.annual_return >= 0 ? 'up' : 'down'" />
          <MetricCard label="最大回撤" :value="pct(selectedStrategy.result.max_drawdown)" positive="down" />
          <MetricCard label="夏普比率" :value="(selectedStrategy.result.sharpe_ratio || 0).toFixed(2)" positive="neutral" />
          <MetricCard label="胜率" :value="pct(selectedStrategy.result.win_rate)" positive="neutral" />
          <MetricCard label="盈亏比" :value="(selectedStrategy.result.profit_factor || 0).toFixed(2)" positive="neutral" />
        </div>

        <div v-if="selectedStrategy.result.strategy_allocation && selectedStrategy.result.strategy_allocation.length" class="regime-section">
          <h3 class="section-title">市场状态与策略分配</h3>
          <div class="regime-list">
            <div v-for="ra in selectedStrategy.result.strategy_allocation" :key="ra.regime" class="regime-item">
              <div class="regime-name">{{ ra.name }}</div>
              <div class="regime-strats">
                <span v-for="s in ra.strategies" :key="s.name" class="strat-chip">
                  {{ s.name }} <span class="strat-w">{{ (s.weight * 100).toFixed(0) }}%</span>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="selectedStrategy.result.equity_curve && selectedStrategy.result.equity_curve.length" class="detail-chart">
          <BaseChart :option="equityOption" height="260px" />
        </div>

        <div v-if="selectedStrategy.result.trades && selectedStrategy.result.trades.length" class="detail-trades">
          <h3 class="section-title">交易记录 ({{ selectedStrategy.result.total_trades }}笔)</h3>
          <div class="trades-table">
            <div class="trade-row trade-header">
              <span>日期</span><span>方向</span><span>价格</span><span>数量</span><span>盈亏</span><span>原因</span>
            </div>
            <div v-for="(t, idx) in selectedStrategy.result.trades.filter((x: any) => x.action === 'sell').slice(0, 30)" :key="idx" class="trade-row" :class="{ 'trade-buy': t.action === 'buy', 'trade-sell': t.action === 'sell' }">
              <span class="mono">{{ (t.date || '').slice(0, 10) }}</span>
              <span :class="t.action === 'buy' ? 'up' : 'down'">{{ t.action === 'buy' ? '买入' : '卖出' }}</span>
              <span class="mono">{{ (t.price || 0).toFixed(2) }}</span>
              <span class="mono">{{ t.shares || 0 }}</span>
              <span class="mono" :class="t.pnl >= 0 ? 'up' : 'down'">{{ t.pnl >= 0 ? '+' : '' }}{{ (t.pnl || 0).toFixed(0) }}</span>
              <span class="trade-reason">{{ (t.reason || '').slice(0, 20) }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="selectedStrategy.result && selectedStrategy.result.error" class="detail-content">
        <div class="error-box">{{ selectedStrategy.result.error }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useToast } from '../composables/useToast'
import { MetricCard, BaseChart } from '../components'

const toast = useToast()
const strategies = ref<any[]>([])
const selectedStrategy = ref<any>(null)
const showNewStrategy = ref(false)
const creating = ref(false)
const searchResults = ref<any[]>([])
let searchTimer: any = null

const newStrategy = ref({
  name: '',
  type: 'adaptive',
  symbol: '',
  capital: 1000000,
  start_date: new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10),
  end_date: new Date().toISOString().slice(0, 10),
})

const TYPE_LABELS: Record<string, string> = {
  dual_ma: '双均线', macd: 'MACD', bollinger_breakout: '布林突破',
  ichimoku: '一目均衡', adaptive: '自适应引擎', supertrend: 'SuperTrend',
  adaptive_trend: '自适应趋势', turtle_trading: '海龟交易',
  donchian_channel: '唐奇安通道', momentum: '动量', dual_thrust: 'Dual Thrust',
  atr_channel_breakout: 'ATR通道突破', volatility_squeeze: '波动率收缩突破',
  mean_reversion_pro: '均值回归增强', rsi_mean_reversion: 'RSI均值回归',
  kdj: 'KDJ', vwap_deviation: 'VWAP偏离', multi_factor: '多因子共振',
  fractal_breakout: '分形突破', wyckoff: '威科夫积累',
  elliott_wave: '艾略特波浪', regime_switching: '机制转换',
  chande_kroll: 'Chande-Kroll', vw_macd: '量价MACD',
  order_flow_imbalance: '订单流失衡', market_microstructure: '市场微观结构',
  copula_correlation: 'Copula相关性', quantile_regression: '分位数回归',
}

function typeLabel(type: string): string {
  return TYPE_LABELS[type] || type
}

function pct(v: number): string {
  if (v === undefined || v === null) return '0.00%'
  return (v >= 0 ? '+' : '') + (v * 100).toFixed(2) + '%'
}

function onSymbolSearch() {
  if (searchTimer) clearTimeout(searchTimer)
  const q = newStrategy.value.symbol.trim()
  if (!q) { searchResults.value = []; return }
  searchTimer = setTimeout(async () => {
    try {
      const data = await api.search(q, 6)
      searchResults.value = Array.isArray(data) ? data : []
    } catch { searchResults.value = [] }
  }, 300)
}

function selectSymbol(r: any) {
  newStrategy.value.symbol = r.code || r.symbol
  searchResults.value = []
}

async function loadStrategies() {
  try {
    const data = await api.getStrategies()
    strategies.value = Array.isArray(data) ? data : []
  } catch {
    strategies.value = []
  }
}

async function createStrategy() {
  if (!newStrategy.value.name || !newStrategy.value.symbol) {
    toast.warning('请填写策略名称和股票代码')
    return
  }
  creating.value = true
  try {
    const data = await api.runBacktest(
      newStrategy.value.symbol, newStrategy.value.type,
      newStrategy.value.start_date, newStrategy.value.end_date,
      newStrategy.value.capital,
    )
    if (data) {
      strategies.value.unshift({
        id: Date.now().toString(),
        name: newStrategy.value.name,
        type: newStrategy.value.type,
        symbol: newStrategy.value.symbol,
        start_date: newStrategy.value.start_date,
        end_date: newStrategy.value.end_date,
        result: data,
      })
      showNewStrategy.value = false
      newStrategy.value = { name: '', type: 'adaptive', symbol: '', capital: 1000000, start_date: newStrategy.value.start_date, end_date: newStrategy.value.end_date }
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '创建策略失败')
  } finally {
    creating.value = false
  }
}

function selectStrategy(s: any) {
  selectedStrategy.value = s
}

async function rerunBacktest(s: any) {
  try {
    const data = await api.runBacktest(s.symbol, s.type, s.start_date, s.end_date, 1000000)
    if (data) {
      s.result = data
      if (selectedStrategy.value?.id === s.id) selectedStrategy.value = { ...s }
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '回测失败')
  }
}

async function deleteStrategy(id: string) {
  strategies.value = strategies.value.filter(s => s.id !== id)
  if (selectedStrategy.value?.id === id) selectedStrategy.value = null
}

const equityOption = computed(() => {
  if (!selectedStrategy.value?.result?.equity_curve) return {}
  const eq = selectedStrategy.value.result.equity_curve
  const dates = eq.map((d: any) => (d.date || '').slice(0, 10))
  const values = eq.map((d: any) => d.value)
  const bc = selectedStrategy.value.result.benchmark_curve || []
  const benchValues = bc.map((d: any) => d.value)

  const series: any[] = [{
    type: 'line', name: '策略权益', data: values, showSymbol: false,
    lineStyle: { width: 1.5, color: '#38bdf8' },
    areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(56,189,248,0.12)' }, { offset: 1, color: 'rgba(56,189,248,0)' }] } },
  }]
  if (benchValues.length) {
    series.push({
      type: 'line', name: '基准', data: benchValues, showSymbol: false,
      lineStyle: { width: 1, color: '#6b7280', type: 'dashed' },
    })
  }

  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    legend: { show: benchValues.length > 0, top: 0, textStyle: { color: '#9ca3af', fontSize: 10 } },
    grid: { left: 55, right: 12, top: 24, bottom: 28 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#4a5068', fontSize: 9 } },
    yAxis: { type: 'value', scale: true, axisLabel: { color: '#4a5068', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.03)' } } },
    series,
  }
})

onMounted(loadStrategies)
</script>

<style scoped>
.strategy-page { padding: 14px 16px; max-width: 1200px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.page-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }

.btn-primary {
  display: flex; align-items: center; gap: 4px;
  padding: 6px 14px; background: linear-gradient(135deg, var(--accent-blue), var(--accent-violet));
  color: white; border: none; border-radius: var(--radius-sm);
  font-size: 11px; font-weight: 600; cursor: pointer;
}

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 100;
  display: flex; align-items: center; justify-content: center;
}
.modal-card {
  width: 480px; max-width: 90vw; max-height: 85vh; overflow-y: auto;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color); border-radius: var(--radius-lg);
  padding: 20px; box-shadow: var(--shadow-lg);
}
.modal-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin-bottom: 14px; }
.form-row { margin-bottom: 10px; position: relative; }
.form-row label { display: block; font-size: 10px; color: var(--text-secondary); margin-bottom: 3px; }
.form-input {
  width: 100%; padding: 6px 10px; background: var(--bg-secondary);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);
  color: var(--text-primary); font-size: 12px;
}
.form-input:focus { outline: none; border-color: var(--accent-cyan); box-shadow: 0 0 0 2px var(--accent-cyan-dim); }
select.form-input { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b7280'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 8px center; padding-right: 24px; }
.date-row { display: flex; gap: 6px; align-items: center; }
.date-sep { font-size: 10px; color: var(--text-tertiary); }
.modal-btns { display: flex; gap: 8px; margin-top: 14px; }
.btn-save {
  flex: 1; padding: 7px; background: linear-gradient(135deg, var(--accent-blue), var(--accent-violet));
  color: white; border: none; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; cursor: pointer;
}
.btn-save:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-cancel {
  flex: 1; padding: 7px; background: transparent; border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 12px; cursor: pointer;
}

.search-row { position: relative; }
.search-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 10;
  background: var(--bg-elevated); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); max-height: 200px; overflow-y: auto;
  box-shadow: var(--shadow-lg);
}
.search-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 10px;
  cursor: pointer; font-size: 11px; transition: background 0.15s;
}
.search-item:hover { background: var(--bg-hover); }
.search-code { color: var(--accent-cyan); font-size: 11px; width: 60px; }
.search-name { color: var(--text-primary); flex: 1; }
.search-market { color: var(--text-tertiary); font-size: 9px; }

.strategy-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
.strategy-card { padding: 12px; cursor: pointer; transition: border-color var(--transition-fast); }
.strategy-card:hover { border-color: rgba(56,189,248,0.2); }
.card-header { margin-bottom: 8px; }
.card-title-row { display: flex; justify-content: space-between; align-items: center; }
.strategy-name { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.badge {
  font-size: 9px; padding: 1px 6px; border-radius: 3px;
  background: var(--accent-cyan-dim); color: var(--accent-cyan); font-weight: 500;
}
.card-meta { display: flex; gap: 8px; margin-top: 3px; }
.meta-item { font-size: 10px; color: var(--text-tertiary); }
.card-metrics { display: flex; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.metric { display: flex; flex-direction: column; gap: 1px; }
.metric-label { font-size: 9px; color: var(--text-tertiary); }
.metric-value { font-size: 12px; font-weight: 600; }
.metric-value.up { color: var(--accent-red); }
.metric-value.down { color: var(--accent-green); }
.metric-pending { font-size: 10px; color: var(--accent-amber); }
.metric-error { font-size: 10px; color: var(--accent-red); }
.card-actions { display: flex; gap: 6px; }
.action-btn {
  padding: 3px 8px; background: transparent; border: 1px solid var(--border-subtle);
  border-radius: 3px; color: var(--text-secondary); font-size: 9px; cursor: pointer;
}
.action-btn:hover { color: var(--accent-cyan); border-color: rgba(56,189,248,0.3); }
.action-btn.danger:hover { color: var(--accent-red); border-color: rgba(239,68,68,0.3); }

.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 50px 20px; color: var(--text-tertiary); font-size: 12px;
}

.detail-panel { padding: 14px; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.detail-title { font-size: 15px; font-weight: 700; color: var(--text-primary); }
.close-btn {
  display: flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; border-radius: var(--radius-sm);
  background: transparent; border: 1px solid var(--border-subtle);
  color: var(--text-tertiary); cursor: pointer;
}
.close-btn:hover { color: var(--text-primary); background: var(--bg-hover); }
.detail-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin-bottom: 12px; }
.detail-chart { margin-bottom: 12px; }
.section-title { font-size: 12px; font-weight: 600; color: var(--accent-cyan); margin-bottom: 6px; }

.regime-section { margin-bottom: 12px; }
.regime-list { display: flex; flex-direction: column; gap: 6px; }
.regime-item { padding: 8px 10px; background: var(--bg-hover); border-radius: var(--radius-sm); }
.regime-name { font-size: 11px; font-weight: 600; color: var(--text-primary); margin-bottom: 4px; }
.regime-strats { display: flex; flex-wrap: wrap; gap: 4px; }
.strat-chip {
  font-size: 9px; padding: 2px 6px; border-radius: 3px;
  background: var(--accent-cyan-dim); color: var(--accent-cyan);
}
.strat-w { color: var(--text-secondary); }

.trades-table { display: flex; flex-direction: column; gap: 1px; }
.trade-row {
  display: grid; grid-template-columns: 80px 40px 60px 50px 60px 1fr; gap: 4px;
  padding: 4px 6px; font-size: 10px; border-radius: 2px;
}
.trade-header { color: var(--text-tertiary); font-weight: 600; background: var(--bg-hover); }
.trade-buy { border-left: 2px solid var(--accent-red); }
.trade-sell { border-left: 2px solid var(--accent-green); }
.trade-reason { color: var(--text-tertiary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up { color: var(--accent-red); }
.down { color: var(--accent-green); }

.error-box {
  padding: 12px 16px; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2);
  border-radius: var(--radius-sm); color: var(--accent-red); font-size: 12px;
}

@media (max-width: 768px) {
  .strategy-page { padding: 10px; }
  .strategy-list { grid-template-columns: 1fr; }
  .detail-metrics { grid-template-columns: repeat(2, 1fr); }
}
</style>
