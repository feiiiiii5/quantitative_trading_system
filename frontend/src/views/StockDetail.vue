<template>
  <div class="trading-layout">
    <!-- Left: Watchlist + Market -->
    <aside class="left-panel">
      <div class="search-box">
        <a-input-search v-model="searchQuery" placeholder="搜索代码/名称/拼音" size="small" @search="doSearch" />
      </div>
      <div class="watchlist-header">
        <span class="section-title">自选股</span>
      </div>
      <div class="watchlist">
        <div v-for="item in watchlist" :key="item.symbol" class="watchlist-item"
             :class="{ active: item.symbol === symbol }" @click="goStock(item.symbol)">
          <div class="wl-left">
            <span class="wl-symbol font-mono">{{ item.symbol }}</span>
            <span class="wl-name">{{ item.name }}</span>
          </div>
          <div class="wl-right" :class="item.change_pct >= 0 ? 'text-up' : 'text-down'">
            <span class="wl-price font-mono">{{ item.price?.toFixed(2) }}</span>
            <span class="wl-pct font-mono">{{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct?.toFixed(2) }}%</span>
          </div>
        </div>
      </div>
      <div class="market-section">
        <div class="section-title">市场指数</div>
        <div v-for="idx in marketIndices" :key="idx.name" class="market-item">
          <span class="mi-name">{{ idx.name }}</span>
          <span class="mi-price font-mono" :class="idx.change >= 0 ? 'text-up' : 'text-down'">
            {{ idx.price?.toFixed(2) }}
          </span>
        </div>
      </div>
    </aside>

    <!-- Center: K-line Chart -->
    <main class="center-panel">
      <!-- Top bar -->
      <header class="chart-topbar">
        <div class="stock-identity">
          <span class="si-symbol font-mono">{{ symbol }}</span>
          <span class="si-name">{{ stockInfo.name || '--' }}</span>
          <span class="si-market">{{ stockInfo.market || '' }}</span>
        </div>
        <div class="price-display" :class="rt.pct >= 0 ? 'text-up' : 'text-down'">
          <span class="pd-price font-mono">{{ rt.price?.toFixed(2) || '--' }}</span>
          <span class="pd-change font-mono">{{ rt.pct >= 0 ? '+' : '' }}{{ rt.change?.toFixed(2) }}</span>
          <span class="pd-pct font-mono">({{ rt.pct >= 0 ? '+' : '' }}{{ rt.pct?.toFixed(2) }}%)</span>
        </div>
        <div class="period-tabs">
          <button v-for="p in periods" :key="p.value" class="period-btn"
                  :class="{ active: period === p.value }" @click="switchPeriod(p.value)">{{ p.label }}</button>
        </div>
        <div class="adjust-tabs">
          <button v-for="a in adjustModes" :key="a.value" class="adjust-btn"
                  :class="{ active: adjust === a.value }" @click="adjust = a.value; loadData()">{{ a.label }}</button>
        </div>
      </header>

      <!-- Chart -->
      <div class="chart-area">
        <v-chart class="main-chart" :option="chartOption" autoresize :manual-update="false" />
      </div>

      <!-- Bottom Tabs -->
      <div class="bottom-panel">
        <a-tabs v-model:active-key="bottomTab" size="mini" :lazy-render="true">
          <a-tab-pane key="position" title="持仓">
            <div class="tab-content">
              <table class="data-table">
                <thead><tr><th>标的</th><th>方向</th><th>数量</th><th>成本</th><th>现价</th><th>盈亏</th></tr></thead>
                <tbody>
                  <tr v-for="p in positions" :key="p.symbol">
                    <td class="font-mono">{{ p.symbol }}</td>
                    <td :class="p.quantity > 0 ? 'text-up' : 'text-down'">{{ p.quantity > 0 ? '多' : '空' }}</td>
                    <td class="font-mono">{{ Math.abs(p.quantity) }}</td>
                    <td class="font-mono">{{ p.avg_cost?.toFixed(2) }}</td>
                    <td class="font-mono">{{ p.current_price?.toFixed(2) }}</td>
                    <td class="font-mono" :class="p.unrealized_pnl >= 0 ? 'text-up' : 'text-down'">
                      {{ p.unrealized_pnl >= 0 ? '+' : '' }}{{ p.unrealized_pnl?.toFixed(2) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </a-tab-pane>
          <a-tab-pane key="orders" title="委托">
            <div class="tab-content">
              <table class="data-table">
                <thead><tr><th>时间</th><th>标的</th><th>方向</th><th>类型</th><th>数量</th><th>价格</th><th>状态</th></tr></thead>
                <tbody>
                  <tr v-for="o in orders" :key="o.id">
                    <td class="font-mono">{{ o.timestamp?.slice(11, 19) }}</td>
                    <td class="font-mono">{{ o.symbol }}</td>
                    <td :class="o.side === 'buy' ? 'text-up' : 'text-down'">{{ o.side === 'buy' ? '买入' : '卖出' }}</td>
                    <td>{{ o.type }}</td>
                    <td class="font-mono">{{ o.quantity }}</td>
                    <td class="font-mono">{{ o.price?.toFixed(2) }}</td>
                    <td>{{ o.status }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </a-tab-pane>
          <a-tab-pane key="fills" title="成交">
            <div class="tab-content">
              <table class="data-table">
                <thead><tr><th>时间</th><th>标的</th><th>方向</th><th>数量</th><th>成交价</th><th>手续费</th></tr></thead>
                <tbody>
                  <tr v-for="f in fills" :key="f.order_id">
                    <td class="font-mono">{{ f.timestamp?.slice(11, 19) }}</td>
                    <td class="font-mono">{{ f.symbol }}</td>
                    <td :class="f.side === 'buy' ? 'text-up' : 'text-down'">{{ f.side === 'buy' ? '买入' : '卖出' }}</td>
                    <td class="font-mono">{{ f.quantity }}</td>
                    <td class="font-mono">{{ f.price?.toFixed(2) }}</td>
                    <td class="font-mono">{{ f.commission?.toFixed(2) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </a-tab-pane>
          <a-tab-pane key="strategy" title="策略监控">
            <div class="tab-content strategy-grid">
              <div v-for="s in strategyStatus" :key="s.name" class="strategy-card">
                <div class="sc-name">{{ s.name }}</div>
                <div class="sc-score font-mono" :class="s.score > 0 ? 'text-up' : 'text-down'">{{ s.score?.toFixed(1) }}</div>
                <div class="sc-status">{{ s.running ? '运行中' : '已停止' }}</div>
              </div>
            </div>
          </a-tab-pane>
        </a-tabs>
      </div>
    </main>

    <!-- Right: Trading Panel -->
    <aside class="right-panel">
      <div class="rp-section">
        <div class="section-title">实时行情</div>
        <div class="rt-grid">
          <div class="rt-item"><span class="rt-label">今开</span><span class="rt-val font-mono">{{ rt.open?.toFixed(2) || '--' }}</span></div>
          <div class="rt-item"><span class="rt-label">昨收</span><span class="rt-val font-mono">{{ rt.prev_close?.toFixed(2) || '--' }}</span></div>
          <div class="rt-item"><span class="rt-label">最高</span><span class="rt-val font-mono text-up">{{ rt.high?.toFixed(2) || '--' }}</span></div>
          <div class="rt-item"><span class="rt-label">最低</span><span class="rt-val font-mono text-down">{{ rt.low?.toFixed(2) || '--' }}</span></div>
          <div class="rt-item"><span class="rt-label">成交量</span><span class="rt-val font-mono">{{ fmtVol(rt.volume) }}</span></div>
          <div class="rt-item"><span class="rt-label">成交额</span><span class="rt-val font-mono">{{ fmtVol(rt.amount) }}</span></div>
          <div class="rt-item"><span class="rt-label">换手率</span><span class="rt-val font-mono">{{ rt.turnover?.toFixed(2) || '--' }}%</span></div>
          <div class="rt-item"><span class="rt-label">振幅</span><span class="rt-val font-mono">{{ rt.amplitude?.toFixed(2) || '--' }}%</span></div>
        </div>
      </div>

      <div class="rp-section">
        <div class="section-title">下单</div>
        <a-radio-group v-model="orderSide" type="button" size="small">
          <a-radio value="buy">买入</a-radio>
          <a-radio value="sell">卖出</a-radio>
        </a-radio-group>
        <div class="order-form">
          <div class="of-row">
            <span class="of-label">标的</span>
            <a-input v-model="orderSymbol" size="small" class="of-input font-mono" />
          </div>
          <div class="of-row">
            <span class="of-label">价格</span>
            <a-input-number v-model="orderPrice" :precision="2" size="small" class="of-input" />
          </div>
          <div class="of-row">
            <span class="of-label">数量</span>
            <a-input-number v-model="orderQty" :min="100" :step="100" size="small" class="of-input" />
          </div>
          <a-button :type="orderSide === 'buy' ? 'primary' : 'outline'" :status="orderSide === 'buy' ? 'danger' : 'success'"
                    size="small" long @click="submitOrder" :class="orderSide === 'buy' ? 'btn-buy' : 'btn-sell'">
            {{ orderSide === 'buy' ? '买入' : '卖出' }}
          </a-button>
        </div>
      </div>

      <div class="rp-section">
        <div class="section-title">账户</div>
        <div class="acct-info">
          <div class="ai-row"><span>总资产</span><span class="font-mono">{{ fmtMoney(account.total_value) }}</span></div>
          <div class="ai-row"><span>可用资金</span><span class="font-mono">{{ fmtMoney(account.cash) }}</span></div>
          <div class="ai-row"><span>持仓市值</span><span class="font-mono">{{ fmtMoney(account.position_value) }}</span></div>
          <div class="ai-row">
            <span>今日盈亏</span>
            <span class="font-mono" :class="account.today_pnl >= 0 ? 'text-up' : 'text-down'">
              {{ account.today_pnl >= 0 ? '+' : '' }}{{ fmtMoney(account.today_pnl) }}
            </span>
          </div>
        </div>
      </div>

      <div class="rp-section">
        <div class="section-title">技术指标</div>
        <div class="ind-list">
          <div v-for="ind in indicators" :key="ind.name" class="ind-item">
            <span class="ind-name">{{ ind.name }}</span>
            <span class="ind-val font-mono">{{ ind.value }}</span>
            <span class="ind-signal" :class="ind.signal === '买入' ? 'text-up' : 'text-down'">{{ ind.signal }}</span>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiGet, apiPost } from '../api'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, MarkLineComponent, VisualMapComponent
} from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, CandlestickChart, LineChart, BarChart, GridComponent,
  TooltipComponent, LegendComponent, DataZoomComponent, MarkLineComponent, VisualMapComponent])

const route = useRoute()
const router = useRouter()
const symbol = computed(() => (route.params.symbol as string) || '600519')
const period = ref('daily')
const adjust = ref('qfq')
const bottomTab = ref('position')
const orderSide = ref('buy')
const orderSymbol = ref('')
const orderPrice = ref(0)
const orderQty = ref(100)

const klineData = ref<any[]>([])
const rt = ref<any>({})
const stockInfo = ref<any>({})
const indicators = ref<any[]>([])
const watchlist = ref<any[]>([
  { symbol: '600519', name: '贵州茅台', price: 0, change_pct: 0 },
  { symbol: '000858', name: '五粮液', price: 0, change_pct: 0 },
  { symbol: '601318', name: '中国平安', price: 0, change_pct: 0 },
  { symbol: '000001', name: '平安银行', price: 0, change_pct: 0 },
])
const marketIndices = ref<any[]>([
  { name: '上证指数', price: 0, change: 0 },
  { name: '深证成指', price: 0, change: 0 },
  { name: '创业板指', price: 0, change: 0 },
])
const positions = ref<any[]>([])
const orders = ref<any[]>([])
const fills = ref<any[]>([])
const strategyStatus = ref<any[]>([])
const account = ref<any>({ total_value: 0, cash: 0, position_value: 0, today_pnl: 0 })
const searchQuery = ref('')

const periods = [
  { label: '1分', value: '1' }, { label: '5分', value: '5' },
  { label: '15分', value: '15' }, { label: '30分', value: '30' },
  { label: '60分', value: '60' }, { label: '日K', value: 'daily' },
  { label: '周K', value: 'weekly' }, { label: '月K', value: 'monthly' },
]
const adjustModes = [
  { label: '前复权', value: 'qfq' }, { label: '后复权', value: 'hfq' }, { label: '不复权', value: '' },
]

const chartOption = computed(() => {
  const raw = klineData.value
  if (!raw.length) return {}

  const data = raw.map((d: any) => ({
    ...d,
    date: d.date || d.time,
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
    volume: d.volume || 0,
  }))

  const dates = data.map((d: any) => typeof d.date === 'string' ? d.date.slice(0, 10) : String(d.date))
  const klines = data.map((d: any) => [d.open, d.close, d.low, d.high])
  const volumes = data.map((d: any, i: number) => ({
    value: d.volume,
    itemStyle: { color: d.close >= d.open ? 'rgba(248,81,73,0.7)' : 'rgba(63,185,80,0.7)' }
  }))
  const closes = data.map((d: any) => d.close)

  const ma5 = calcMA(closes, 5)
  const ma10 = calcMA(closes, 10)
  const ma20 = calcMA(closes, 20)
  const ma60 = calcMA(closes, 60)

  // MACD
  const macdData = calcMACD(closes, 12, 26, 9)
  const macdHist = macdData.hist.map((v: number, i: number) => ({
    value: v,
    itemStyle: { color: v >= 0 ? 'rgba(248,81,73,0.7)' : 'rgba(63,185,80,0.7)' }
  }))

  // RSI
  const rsiData = calcRSI(closes, 14)

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', crossStyle: { color: '#6e7681' } },
      backgroundColor: 'rgba(13,17,23,0.95)',
      borderColor: '#30363d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'JetBrains Mono' },
      formatter: (params: any) => {
        if (!params || !params.length) return ''
        const k = params.find((p: any) => p.seriesName === 'K线')
        if (!k) return ''
        const d = k.data
        const idx = k.dataIndex
        const isUp = d[1] >= d[0]
        const c = isUp ? '#f85149' : '#3fb950'
        return `<div style="font-family:JetBrains Mono;font-size:12px">
          <div style="color:#8b949e;margin-bottom:4px">${dates[idx]}</div>
          <div>开 <span style="color:${c}">${d[0]?.toFixed(2)}</span></div>
          <div>高 <span style="color:${c}">${d[3]?.toFixed(2)}</span></div>
          <div>低 <span style="color:${c}">${d[2]?.toFixed(2)}</span></div>
          <div>收 <span style="color:${c}">${d[1]?.toFixed(2)}</span></div>
          <div>量 <span style="color:#8b949e">${fmtVol(data[idx]?.volume)}</span></div>
          ${ma5[idx] != null ? `<div>MA5 <span style="color:#d29922">${ma5[idx]?.toFixed(2)}</span></div>` : ''}
          ${ma10[idx] != null ? `<div>MA10 <span style="color:#a371f7">${ma10[idx]?.toFixed(2)}</span></div>` : ''}
          ${ma20[idx] != null ? `<div>MA20 <span style="color:#58a6ff">${ma20[idx]?.toFixed(2)}</span></div>` : ''}
        </div>`
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'],
      textStyle: { color: '#8b949e', fontSize: 11 },
      top: 4, right: 60, itemGap: 12, itemWidth: 14, itemHeight: 2,
    },
    grid: [
      { left: 60, right: 16, top: 36, height: '48%' },
      { left: 60, right: 16, top: '62%', height: '10%' },
      { left: 60, right: 16, top: '74%', height: '10%' },
      { left: 60, right: 16, top: '86%', height: '10%' },
    ],
    xAxis: [
      { type: 'category', data: dates, axisLine: { lineStyle: { color: '#30363d' } }, axisLabel: { color: '#6e7681', fontSize: 10 }, axisTick: { show: false }, gridIndex: 0 },
      { type: 'category', data: dates, gridIndex: 1, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
      { type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
      { type: 'category', data: dates, gridIndex: 3, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false } },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, axisLine: { show: false }, axisLabel: { color: '#6e7681', fontSize: 10, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } } },
      { scale: true, gridIndex: 1, axisLine: { show: false }, axisLabel: { show: false }, splitLine: { show: false } },
      { scale: true, gridIndex: 2, axisLine: { show: false }, axisLabel: { show: false }, splitLine: { show: false } },
      { scale: true, gridIndex: 3, axisLine: { show: false }, axisLabel: { show: false }, splitLine: { show: false } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: 60, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1, 2, 3], bottom: 2, height: 12, borderColor: '#30363d', fillerColor: 'rgba(88,166,255,0.15)', handleStyle: { color: '#58a6ff' }, textStyle: { color: '#6e7681', fontSize: 10 } },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: klines, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: '#f85149', color0: '#3fb950', borderColor: '#f85149', borderColor0: '#3fb950', borderWidth: 1 },
      },
      { name: 'MA5', type: 'line', data: ma5, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { color: '#d29922', width: 1 }, },
      { name: 'MA10', type: 'line', data: ma10, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { color: '#a371f7', width: 1 }, },
      { name: 'MA20', type: 'line', data: ma20, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { color: '#58a6ff', width: 1 }, },
      { name: 'MA60', type: 'line', data: ma60, xAxisIndex: 0, yAxisIndex: 0, showSymbol: false, lineStyle: { color: '#3fb950', width: 1 }, },
      { name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1, },
      { name: 'MACD', type: 'bar', data: macdHist, xAxisIndex: 2, yAxisIndex: 2, },
      { name: 'DIF', type: 'line', data: macdData.dif, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { color: '#d29922', width: 1 }, },
      { name: 'DEA', type: 'line', data: macdData.dea, xAxisIndex: 2, yAxisIndex: 2, showSymbol: false, lineStyle: { color: '#58a6ff', width: 1 }, },
      { name: 'RSI', type: 'line', data: rsiData, xAxisIndex: 3, yAxisIndex: 3, showSymbol: false, lineStyle: { color: '#a371f7', width: 1 },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: '#30363d', type: 'dashed' }, data: [{ yAxis: 70 }, { yAxis: 30 }] }
      },
    ],
  }
})

function calcMA(data: number[], p: number) {
  const r: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < p - 1) { r.push(null); continue }
    let s = 0; for (let j = 0; j < p; j++) s += data[i - j]
    r.push(s / p)
  }
  return r
}

function calcMACD(closes: number[], fast: number, slow: number, signal: number) {
  const ema = (arr: number[], span: number) => {
    const a = 2 / (span + 1); const r = [arr[0]]
    for (let i = 1; i < arr.length; i++) r.push(a * arr[i] + (1 - a) * r[i - 1])
    return r
  }
  const ef = ema(closes, fast); const es = ema(closes, slow)
  const dif = ef.map((v, i) => v - es[i])
  const dea = ema(dif, signal)
  const hist = dif.map((v, i) => (v - dea[i]) * 2)
  return { dif, dea, hist }
}

function calcRSI(closes: number[], period: number) {
  const r: (number | null)[] = []
  let avgGain = 0, avgLoss = 0
  for (let i = 0; i < closes.length; i++) {
    if (i === 0) { r.push(null); continue }
    const diff = closes[i] - closes[i - 1]
    if (i <= period) {
      avgGain += Math.max(diff, 0); avgLoss += Math.max(-diff, 0)
      if (i === period) { avgGain /= period; avgLoss /= period; r.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)) }
      else r.push(null)
    } else {
      avgGain = (avgGain * (period - 1) + Math.max(diff, 0)) / period
      avgLoss = (avgLoss * (period - 1) + Math.max(-diff, 0)) / period
      r.push(avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss))
    }
  }
  return r
}

function fmtVol(v: number) {
  if (!v) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(0)
}

function fmtMoney(v: number) {
  if (!v) return '0.00'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

function switchPeriod(p: string) {
  period.value = p
  loadData()
}

function goStock(sym: string) {
  router.push(`/stock/${sym}`)
}

async function doSearch(q: string) {
  if (!q) return
  try {
    const results = await apiGet<any[]>(`/search?q=${q}`)
    if (results && results.length > 0) {
      router.push(`/stock/${results[0].code}`)
    }
  } catch {}
}

async function submitOrder() {
  try {
    const endpoint = orderSide.value === 'buy' ? '/sim/buy' : '/sim/sell'
    await apiPost(endpoint, {
      symbol: orderSymbol.value || symbol.value,
      shares: orderQty.value,
      price: orderPrice.value,
    })
    loadAccount()
  } catch {}
}

async function loadData() {
  try {
    const [histData, rtData] = await Promise.all([
      apiGet<any[]>(`/history?symbol=${symbol.value}&period=${period.value}&adjust=${adjust.value}`),
      apiGet<any>(`/realtime?symbol=${symbol.value}`)
    ])
    if (histData && typeof histData === 'object' && 'data' in histData && Array.isArray(histData.data)) {
      klineData.value = histData.data
    } else if (Array.isArray(histData)) {
      klineData.value = histData
    } else {
      klineData.value = []
    }
    rt.value = rtData && typeof rtData === 'object' ? rtData : {}
    if (rt.value.name) stockInfo.value = { name: rt.value.name, market: rt.value.market || '' }
    orderSymbol.value = symbol.value
    orderPrice.value = rt.value.price || 0

    const closes = klineData.value.map((d: any) => d.close)
    if (closes.length >= 20) {
      const m5 = closes.slice(-5).reduce((a: number, b: number) => a + b, 0) / 5
      const m10 = closes.slice(-10).reduce((a: number, b: number) => a + b, 0) / 10
      const m20 = closes.slice(-20).reduce((a: number, b: number) => a + b, 0) / 20
      const latest = closes[closes.length - 1]
      indicators.value = [
        { name: 'MA5', value: m5.toFixed(2), signal: latest > m5 ? '买入' : '卖出' },
        { name: 'MA10', value: m10.toFixed(2), signal: latest > m10 ? '买入' : '卖出' },
        { name: 'MA20', value: m20.toFixed(2), signal: latest > m20 ? '买入' : '卖出' },
        { name: 'MA交叉', value: m5 > m10 ? '金叉' : '死叉', signal: m5 > m10 ? '买入' : '卖出' },
      ]
    }
  } catch {}
}

async function loadAccount() {
  try {
    const [acct, pos, ord, fill] = await Promise.all([
      apiGet<any>('/sim/account'),
      apiGet<any[]>('/sim/positions'),
      apiGet<any[]>('/sim/orders'),
      apiGet<any[]>('/sim/trades'),
    ])
    if (acct) account.value = acct
    if (Array.isArray(pos)) positions.value = pos
    if (Array.isArray(ord)) orders.value = ord
    if (Array.isArray(fill)) fills.value = fill
  } catch {}
}

watch(symbol, () => { loadData(); loadAccount() })

onMounted(() => { loadData(); loadAccount() })
</script>

<style scoped>
.trading-layout {
  display: flex; height: 100vh; background: var(--bg-primary); overflow: hidden;
}

/* Left Panel */
.left-panel {
  width: 220px; background: var(--bg-secondary); border-right: 1px solid var(--border-color);
  display: flex; flex-direction: column; overflow: hidden;
}
.search-box { padding: 12px; border-bottom: 1px solid var(--border-color); }
.watchlist-header { padding: 8px 12px; }
.section-title { font-size: 12px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.watchlist { flex: 1; overflow-y: auto; }
.watchlist-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; cursor: pointer; transition: background 0.15s;
}
.watchlist-item:hover { background: var(--bg-tertiary); }
.watchlist-item.active { background: var(--bg-hover); border-left: 2px solid var(--color-up); }
.wl-left { display: flex; flex-direction: column; gap: 2px; }
.wl-symbol { font-size: 13px; color: var(--text-primary); }
.wl-name { font-size: 11px; color: var(--text-muted); }
.wl-right { text-align: right; }
.wl-price { font-size: 13px; display: block; }
.wl-pct { font-size: 11px; }
.market-section { padding: 8px 12px; border-top: 1px solid var(--border-color); }
.market-item { display: flex; justify-content: space-between; padding: 4px 0; }
.mi-name { font-size: 12px; color: var(--text-secondary); }
.mi-price { font-size: 12px; }

/* Center Panel */
.center-panel {
  flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0;
}
.chart-topbar {
  display: flex; align-items: center; gap: 16px; padding: 8px 16px;
  background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);
}
.stock-identity { display: flex; align-items: center; gap: 8px; }
.si-symbol { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.si-name { font-size: 13px; color: var(--text-secondary); }
.si-market { font-size: 11px; color: var(--text-muted); background: var(--bg-tertiary); padding: 1px 6px; border-radius: 3px; }
.price-display { display: flex; align-items: baseline; gap: 8px; }
.pd-price { font-size: 22px; font-weight: 700; }
.pd-change { font-size: 13px; }
.pd-pct { font-size: 13px; }
.period-tabs, .adjust-tabs { display: flex; gap: 2px; }
.period-btn, .adjust-btn {
  padding: 4px 10px; border: none; background: transparent; color: var(--text-secondary);
  font-size: 12px; cursor: pointer; border-radius: 3px; transition: all 0.15s;
}
.period-btn:hover, .adjust-btn:hover { color: var(--text-primary); background: var(--bg-tertiary); }
.period-btn.active, .adjust-btn.active { color: var(--color-up); background: var(--bg-tertiary); }

.chart-area { flex: 1; min-height: 0; }
.main-chart { width: 100%; height: 100%; }

/* Bottom Panel */
.bottom-panel {
  height: 180px; background: var(--bg-secondary); border-top: 1px solid var(--border-color);
  overflow: hidden;
}
.tab-content { padding: 0 12px; overflow-y: auto; max-height: 140px; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.data-table th { color: var(--text-muted); font-weight: 500; text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-color); }
.data-table th:first-child { text-align: left; }
.data-table td { padding: 5px 8px; text-align: right; color: var(--text-secondary); border-bottom: 1px solid var(--border-light); }
.data-table td:first-child { text-align: left; }
.strategy-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.strategy-card { background: var(--bg-tertiary); border-radius: 4px; padding: 8px 12px; }
.sc-name { font-size: 12px; color: var(--text-secondary); }
.sc-score { font-size: 18px; font-weight: 700; }
.sc-status { font-size: 11px; color: var(--text-muted); }

/* Right Panel */
.right-panel {
  width: 240px; background: var(--bg-secondary); border-left: 1px solid var(--border-color);
  display: flex; flex-direction: column; overflow-y: auto;
}
.rp-section { padding: 12px; border-bottom: 1px solid var(--border-color); }
.rt-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.rt-item { display: flex; justify-content: space-between; }
.rt-label { font-size: 11px; color: var(--text-muted); }
.rt-val { font-size: 12px; color: var(--text-primary); }
.order-form { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
.of-row { display: flex; align-items: center; gap: 8px; }
.of-label { font-size: 12px; color: var(--text-muted); min-width: 32px; }
.of-input { flex: 1; }
.btn-buy { background: var(--color-up) !important; border-color: var(--color-up) !important; }
.btn-sell { background: var(--color-down) !important; border-color: var(--color-down) !important; color: #fff !important; }
.acct-info { display: flex; flex-direction: column; gap: 6px; }
.ai-row { display: flex; justify-content: space-between; font-size: 12px; }
.ai-row span:first-child { color: var(--text-muted); }
.ai-row span:last-child { color: var(--text-primary); }
.ind-list { display: flex; flex-direction: column; gap: 6px; }
.ind-item { display: flex; justify-content: space-between; align-items: center; }
.ind-name { font-size: 12px; color: var(--text-muted); }
.ind-val { font-size: 13px; color: var(--text-primary); }
.ind-signal { font-size: 11px; font-weight: 600; }

@media (max-width: 1280px) {
  .left-panel { width: 180px; }
  .right-panel { width: 200px; }
}
</style>
