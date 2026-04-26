<template>
  <div class="stock-detail fade-in">
    <header class="detail-header">
      <div class="stock-identity">
        <button class="btn btn-ghost back-btn" @click="$router.back()">← 返回</button>
        <div class="stock-name">{{ stockInfo.name || symbol }}</div>
        <div class="stock-code font-mono">{{ symbol }}</div>
        <span v-if="stockInfo.market" class="market-tag">{{ stockInfo.market }}</span>
        <button class="btn btn-ghost star-btn" @click="toggleWatchlist">
          {{ inWatchlist ? '★' : '☆' }}
        </button>
      </div>
      <div class="price-section" v-if="realtime.price">
        <div class="current-price font-mono" :class="realtime.pct >= 0 ? 'text-up' : 'text-down'">
          {{ realtime.price?.toFixed(2) }}
        </div>
        <div class="price-change font-mono">
          <span :class="realtime.change >= 0 ? 'text-up' : 'text-down'">
            {{ realtime.change >= 0 ? '+' : '' }}{{ realtime.change?.toFixed(2) }}
          </span>
          <span :class="realtime.pct >= 0 ? 'text-up' : 'text-down'">
            {{ realtime.pct >= 0 ? '+' : '' }}{{ realtime.pct?.toFixed(2) }}%
          </span>
        </div>
      </div>
    </header>

    <div class="main-grid">
      <div class="chart-section">
        <div class="chart-toolbar">
          <div class="period-tabs">
            <button v-for="p in periods" :key="p.value" class="period-tab" :class="{ active: currentPeriod === p.value }" @click="switchPeriod(p.value)">{{ p.label }}</button>
          </div>
          <div class="indicator-toggles">
            <label v-for="ind in indicatorToggles" :key="ind.key" class="toggle-label">
              <input type="checkbox" v-model="ind.visible" @change="updateChart" />
              {{ ind.label }}
            </label>
          </div>
        </div>
        <div class="chart-container" ref="chartRef"></div>
      </div>

      <div class="side-panel">
        <div class="panel-card">
          <h3 class="panel-title">交易面板</h3>
          <div class="trade-form">
            <div class="trade-type-tabs">
              <button class="trade-type" :class="{ active: tradeType === 'buy', buy: tradeType === 'buy' }" @click="tradeType = 'buy'">买入</button>
              <button class="trade-type" :class="{ active: tradeType === 'sell', sell: tradeType === 'sell' }" @click="tradeType = 'sell'">卖出</button>
            </div>
            <div class="form-group">
              <label>价格</label>
              <input type="number" v-model.number="tradePrice" class="font-mono" step="0.01" />
            </div>
            <div class="form-group">
              <label>数量(手)</label>
              <input type="number" v-model.number="tradeQty" min="1" step="1" />
            </div>
            <div class="trade-summary">
              <div class="summary-row">
                <span>金额</span>
                <span class="font-mono">{{ tradeAmount.toLocaleString() }}</span>
              </div>
            </div>
            <button class="btn trade-btn" :class="tradeType === 'buy' ? 'btn-success' : 'btn-danger'" @click="executeTrade" :disabled="trading">
              {{ tradeType === 'buy' ? '买入' : '卖出' }}
            </button>
          </div>
        </div>

        <div class="panel-card">
          <h3 class="panel-title">实时行情</h3>
          <div class="quote-grid" v-if="realtime.price">
            <div class="quote-item"><span class="ql">开盘</span><span class="qv font-mono">{{ realtime.open?.toFixed(2) }}</span></div>
            <div class="quote-item"><span class="ql">最高</span><span class="qv font-mono text-up">{{ realtime.high?.toFixed(2) }}</span></div>
            <div class="quote-item"><span class="ql">最低</span><span class="qv font-mono text-down">{{ realtime.low?.toFixed(2) }}</span></div>
            <div class="quote-item"><span class="ql">昨收</span><span class="qv font-mono">{{ realtime.prev_close?.toFixed(2) }}</span></div>
            <div class="quote-item"><span class="ql">成交量</span><span class="qv font-mono">{{ fmtVol(realtime.volume) }}</span></div>
            <div class="quote-item"><span class="ql">成交额</span><span class="qv font-mono">{{ fmtAmt(realtime.turnover) }}</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import * as echarts from 'echarts'

const route = useRoute()
const router = useRouter()
const symbol = computed(() => route.params.symbol as string)

const stockInfo = ref<any>({})
const realtime = ref<any>({})
const klineData = ref<any[]>([])
const currentPeriod = ref('daily')
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

const periods = [
  { value: 'daily', label: '日K' },
  { value: 'weekly', label: '周K' },
  { value: 'monthly', label: '月K' },
]

const indicatorToggles = ref([
  { key: 'ma', label: '均线', visible: true },
  { key: 'vol', label: '成交量', visible: true },
  { key: 'macd', label: 'MACD', visible: true },
])

const tradeType = ref('buy')
const tradePrice = ref(0)
const tradeQty = ref(1)
const trading = ref(false)
const inWatchlist = ref(false)

const tradeAmount = computed(() => tradePrice.value * tradeQty.value * 100)

function fmtVol(v: number) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toString()
}

function fmtAmt(v: number) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}

function calcMA(data: number[], n: number) {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < n - 1) { result.push(null); continue }
    let sum = 0
    for (let j = 0; j < n; j++) sum += data[i - j]
    result.push(sum / n)
  }
  return result
}

function calcMACD(closes: number[], short = 12, long = 26, signal = 9) {
  const emaShort: number[] = [closes[0]]
  const emaLong: number[] = [closes[0]]
  const dif: number[] = []
  const dea: number[] = [0]
  const hist: number[] = [0]

  for (let i = 1; i < closes.length; i++) {
    emaShort.push(emaShort[i - 1] * (short - 1) / (short + 1) + closes[i] * 2 / (short + 1))
    emaLong.push(emaLong[i - 1] * (long - 1) / (long + 1) + closes[i] * 2 / (long + 1))
    dif.push(emaShort[i] - emaLong[i])
  }
  dif.unshift(0)

  for (let i = 1; i < dif.length; i++) {
    dea.push(dea[i - 1] * (signal - 1) / (signal + 1) + dif[i] * 2 / (signal + 1))
    hist.push(2 * (dif[i] - dea[i]))
  }

  return { dif, dea, hist }
}

function getChartOption() {
  const raw = klineData.value
  if (!raw.length) return {}

  const dates = raw.map((d: any) => String(d.date).slice(0, 10))
  const klines = raw.map((d: any) => [d.open, d.close, d.low, d.high])
  const volumes = raw.map((d: any) => ({
    value: d.volume,
    itemStyle: { color: d.close >= d.open ? 'rgba(255,69,58,0.5)' : 'rgba(48,209,88,0.5)' }
  }))
  const closes = raw.map((d: any) => d.close)
  const ma5 = calcMA(closes, 5)
  const ma10 = calcMA(closes, 10)
  const ma20 = calcMA(closes, 20)
  const ma60 = calcMA(closes, 60)
  const macdData = calcMACD(closes)
  const showMA = indicatorToggles.value.find(i => i.key === 'ma')?.visible
  const showVol = indicatorToggles.value.find(i => i.key === 'vol')?.visible
  const showMACD = indicatorToggles.value.find(i => i.key === 'macd')?.visible

  const grids: any[] = [{ left: 60, right: 20, top: 30, height: '50%' }]
  const xAxes: any[] = [{ type: 'category', data: dates, gridIndex: 0, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { show: false }, axisTick: { show: false } }]
  const yAxes: any[] = [{ type: 'value', gridIndex: 0, scale: true, splitLine: { lineStyle: { color: '#1a1a1a' } }, axisLabel: { color: '#6e6e73', fontSize: 10, fontFamily: 'SF Mono, Menlo, monospace' } }]
  const series: any[] = [
    { name: 'K线', type: 'candlestick', data: klines, xAxisIndex: 0, yAxisIndex: 0, itemStyle: { color: '#ff453a', color0: '#30d158', borderColor: '#ff453a', borderColor0: '#30d158' } },
  ]

  if (showMA) {
    series.push(
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#ff9f0a' } },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#bf5af2' } },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#5ac8fa' } },
      { name: 'MA60', type: 'line', data: ma60, xAxisIndex: 0, yAxisIndex: 0, smooth: true, symbol: 'none', lineStyle: { width: 1, color: '#30d158' } },
    )
  }

  let gridBottom = '8%'
  let volIndex = 0

  if (showVol) {
    volIndex = grids.length
    grids.push({ left: 60, right: 20, top: '68%', height: '12%' })
    xAxes.push({ type: 'category', data: dates, gridIndex: volIndex, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { lineStyle: { color: '#333' } } })
    yAxes.push({ type: 'value', gridIndex: volIndex, scale: true, splitLine: { show: false }, axisLabel: { show: false } })
    series.push({ name: '成交量', type: 'bar', data: volumes, xAxisIndex: volIndex, yAxisIndex: volIndex })
    gridBottom = '20%'
  }

  if (showMACD) {
    const macdIndex = grids.length
    grids.push({ left: 60, right: 20, top: '82%', height: '12%' })
    xAxes.push({ type: 'category', data: dates, gridIndex: macdIndex, axisLine: { lineStyle: { color: '#333' } }, axisLabel: { color: '#6e6e73', fontSize: 9, fontFamily: 'SF Mono, Menlo, monospace' } })
    yAxes.push({ type: 'value', gridIndex: macdIndex, scale: true, splitLine: { show: false }, axisLabel: { show: false } })
    const macdHist = macdData.hist.map((v: number) => ({
      value: v,
      itemStyle: { color: v >= 0 ? 'rgba(255,69,58,0.5)' : 'rgba(48,209,88,0.5)' }
    }))
    series.push(
      { name: 'MACD', type: 'bar', data: macdHist, xAxisIndex: macdIndex, yAxisIndex: macdIndex },
      { name: 'DIF', type: 'line', data: macdData.dif, xAxisIndex: macdIndex, yAxisIndex: macdIndex, symbol: 'none', lineStyle: { width: 1, color: '#ff9f0a' } },
      { name: 'DEA', type: 'line', data: macdData.dea, xAxisIndex: macdIndex, yAxisIndex: macdIndex, symbol: 'none', lineStyle: { width: 1, color: '#5ac8fa' } },
    )
    gridBottom = '34%'
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#6e6e73' } },
      backgroundColor: 'rgba(28,28,30,0.95)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#f5f5f7', fontSize: 12, fontFamily: 'SF Mono, Menlo, monospace' },
    },
    grid: grids,
    xAxis: xAxes,
    yAxis: yAxes,
    dataZoom: [
      { type: 'inside', xAxisIndex: xAxes.map((_, i) => i), start: 60, end: 100 },
      { type: 'slider', xAxisIndex: xAxes.map((_, i) => i), start: 60, end: 100, height: 16, bottom: 4, borderColor: '#333', fillerColor: 'rgba(41,151,255,0.15)', handleStyle: { color: '#2997ff' } },
    ],
    series,
  }
}

function updateChart() {
  if (!chart) return
  const option = getChartOption()
  if (Object.keys(option).length) chart.setOption(option, true)
}

async function loadData() {
  try { stockInfo.value = await api.getStockInfo(symbol.value) } catch {}
  try {
    realtime.value = await api.getRealtime(symbol.value)
    tradePrice.value = realtime.value.price || 0
  } catch {}
  try {
    klineData.value = await api.getKline(symbol.value, currentPeriod.value, 500)
    await nextTick()
    updateChart()
  } catch {}
}

function switchPeriod(p: string) {
  currentPeriod.value = p
  loadData()
}

async function toggleWatchlist() {
  try {
    if (inWatchlist.value) {
      await api.removeFromWatchlist(symbol.value)
      inWatchlist.value = false
    } else {
      await api.addToWatchlist(symbol.value)
      inWatchlist.value = true
    }
  } catch {}
}

async function executeTrade() {
  if (trading.value) return
  trading.value = true
  try {
    if (tradeType.value === 'buy') {
      await api.buyStock(symbol.value, tradeQty.value * 100, tradePrice.value)
    } else {
      await api.sellStock(symbol.value, tradeQty.value * 100, tradePrice.value)
    }
    alert(`${tradeType.value === 'buy' ? '买入' : '卖出'}成功!`)
  } catch (e: any) {
    alert(`交易失败: ${e.message}`)
  } finally {
    trading.value = false
  }
}

let refreshTimer: any = null

onMounted(async () => {
  await loadData()
  try {
    const wl = await api.getWatchlist()
    inWatchlist.value = wl.some((s: any) => s.code === symbol.value)
  } catch {}

  if (chartRef.value) {
    chart = echarts.init(chartRef.value, 'dark')
    updateChart()
    window.addEventListener('resize', () => chart?.resize())
  }

  refreshTimer = setInterval(async () => {
    try { realtime.value = await api.getRealtime(symbol.value) } catch {}
  }, 10000)
})

onUnmounted(() => {
  chart?.dispose()
  clearInterval(refreshTimer)
})

watch(symbol, () => { loadData() })
</script>

<style scoped>
.stock-detail { padding: 20px 24px; height: 100vh; display: flex; flex-direction: column; overflow: hidden; }

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.stock-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn { padding: 4px 10px; font-size: 12px; }

.stock-name { font-size: 20px; font-weight: 700; }
.stock-code { font-size: 13px; color: var(--text-tertiary); }

.market-tag {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(41,151,255,0.15);
  color: var(--accent-blue);
}

.star-btn { padding: 4px 8px; font-size: 16px; }

.price-section { text-align: right; }
.current-price { font-size: 28px; font-weight: 700; }
.price-change { font-size: 14px; display: flex; gap: 12px; justify-content: flex-end; }

.main-grid {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.chart-section {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.chart-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.period-tabs { display: flex; gap: 2px; }

.period-tab {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  background: transparent;
  color: var(--text-secondary);
  border: none;
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-sans);
}

.period-tab.active { background: rgba(41,151,255,0.12); color: var(--accent-blue); }

.indicator-toggles { display: flex; gap: 12px; }

.toggle-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--text-tertiary);
  cursor: pointer;
}

.toggle-label input { width: 12px; height: 12px; }

.chart-container { flex: 1; min-height: 400px; }

.side-panel { display: flex; flex-direction: column; gap: 12px; overflow-y: auto; }

.panel-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.trade-type-tabs { display: flex; gap: 4px; margin-bottom: 12px; }

.trade-type {
  flex: 1;
  padding: 6px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  background: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-sans);
}

.trade-type.active.buy { background: rgba(255,69,58,0.15); color: var(--accent-red); border-color: var(--accent-red); }
.trade-type.active.sell { background: rgba(48,209,88,0.15); color: var(--accent-green); border-color: var(--accent-green); }

.form-group { margin-bottom: 10px; }
.form-group label { display: block; font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; }
.form-group input { width: 100%; }

.trade-summary {
  padding: 8px 0;
  border-top: 1px solid var(--border-light);
  margin-bottom: 10px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.trade-btn { width: 100%; padding: 10px; }

.quote-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.quote-item {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.ql { color: var(--text-tertiary); }
.qv { color: var(--text-primary); }
</style>
