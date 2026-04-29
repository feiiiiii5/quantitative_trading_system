<template>
  <div class="dashboard">
    <div v-if="loading" class="skeleton-dashboard">
      <div class="skeleton skeleton-bar" style="height:28px;margin-bottom:12px"></div>
      <div class="skeleton-row">
        <div class="skeleton skeleton-card" style="height:80px;flex:1" v-for="i in 3" :key="i"></div>
      </div>
      <div class="skeleton-row" style="margin-top:12px">
        <div class="skeleton skeleton-block" style="height:260px;flex:2"></div>
        <div class="skeleton skeleton-block" style="height:260px;flex:1"></div>
      </div>
    </div>
    <template v-else>
    <div class="status-bar">
      <span class="status-time">{{ currentTime }}</span>
      <span class="status-divider">|</span>
      <span class="status-market" :class="isMarketOpen ? 'open' : 'closed'">{{ isMarketOpen ? '交易中' : '已休市' }}</span>
      <template v-if="marketStatus && Object.keys(marketStatus).length">
        <span class="status-divider">|</span>
        <span v-for="(ms, key) in marketStatus" :key="key" class="status-market-detail">
          {{ key === 'A' ? 'A股' : key === 'HK' ? '港股' : '美股' }}
          <span :class="ms.is_open ? 'open' : 'closed'">{{ ms.is_open ? '开' : '休' }}</span>
        </span>
      </template>
      <span class="status-divider">|</span>
      <span class="status-nb" v-if="northboundData">
        北向 <span :class="nbNetInflow >= 0 ? 'up' : 'down'">{{ nbNetInflow >= 0 ? '+' : '' }}{{ fmtAmount(nbNetInflow) }}</span>
      </span>
      <span class="status-divider">|</span>
      <span class="status-temp">温度 <span class="temp-num" :class="temperature >= 60 ? 'up' : temperature <= 30 ? 'down' : ''">{{ temperature.toFixed(0) }}</span></span>
      <span class="status-right">最后更新: {{ lastUpdate }}</span>
    </div>

    <div class="indices-row">
      <div
        v-for="(item, key, idx) in allIndices"
        :key="key"
        class="index-card"
        :class="{ up: item.change_pct >= 0, down: item.change_pct < 0 }"
        :style="{ animationDelay: idx * 60 + 'ms' }"
      >
        <div class="index-top">
          <span class="index-name">{{ item.name }}</span>
          <span class="index-pct" :class="item.change_pct >= 0 ? 'up' : 'down'">
            {{ item.change_pct >= 0 ? '+' : '' }}{{ (item.change_pct || 0).toFixed(2) }}%
          </span>
        </div>
        <span class="index-price" :class="item.change_pct >= 0 ? 'up' : 'down'">
          {{ (item.price || 0).toFixed(2) }}
        </span>
        <div class="index-spark" :ref="el => setSparkRef(key, el)"></div>
        <div class="index-hover-info">
          <span v-if="item.high">高 {{ item.high.toFixed(2) }}</span>
          <span v-if="item.low">低 {{ item.low.toFixed(2) }}</span>
        </div>
      </div>
    </div>

    <div class="main-grid">
      <div class="heatmap-section">
        <div class="section-header">
          <h2 class="section-title">板块热力图</h2>
        </div>
        <div ref="heatmapChartRef" class="heatmap-chart"></div>
      </div>

      <div class="right-col">
        <div class="northbound-gauge-card">
          <h2 class="section-title">北向资金</h2>
          <div ref="nbGaugeRef" class="nb-gauge"></div>
          <div class="nb-detail" v-if="northboundData">
            <div class="nb-row">
              <span class="nb-label">沪股通</span>
              <span class="nb-val" :class="northboundData.sh_inflow >= 0 ? 'up' : 'down'">
                {{ northboundData.sh_inflow >= 0 ? '+' : '' }}{{ fmtAmount(northboundData.sh_inflow) }}
              </span>
            </div>
            <div class="nb-row">
              <span class="nb-label">深股通</span>
              <span class="nb-val" :class="northboundData.sz_inflow >= 0 ? 'up' : 'down'">
                {{ northboundData.sz_inflow >= 0 ? '+' : '' }}{{ fmtAmount(northboundData.sz_inflow) }}
              </span>
            </div>
          </div>
        </div>

        <div class="account-card">
          <h2 class="section-title">账户概览</h2>
          <div class="account-grid">
            <div class="metric">
              <span class="metric-label">总资产</span>
              <span class="metric-value">¥{{ fmtNum(account.total_assets || 100000) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">持仓市值</span>
              <span class="metric-value">¥{{ fmtNum(account.position_value || 0) }}</span>
            </div>
            <div class="metric">
              <span class="metric-label">可用资金</span>
              <span class="metric-value">¥{{ fmtNum(account.available_cash || 0) }}</span>
            </div>
            <div class="metric" :class="{ up: account.total_pnl >= 0, down: account.total_pnl < 0 }">
              <span class="metric-label">总盈亏</span>
              <span class="metric-value">{{ account.total_pnl >= 0 ? '+' : '' }}¥{{ fmtNum(account.total_pnl || 0) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="bottom-grid">
      <div class="watchlist-section">
        <h2 class="section-title">自选股快速面板</h2>
        <div v-if="watchlistQuotes.length" class="quotes-list">
          <div
            v-for="quote in watchlistQuotes"
            :key="quote.symbol"
            class="quote-row"
            :class="{ up: quote.change_pct >= 0, down: quote.change_pct < 0 }"
            @click="$router.push(`/stock/${quote.symbol}`)"
          >
            <div class="quote-left">
              <span class="quote-code">{{ quote.symbol }}</span>
              <span class="quote-name">{{ quote.name }}</span>
            </div>
            <div class="quote-right">
              <span class="quote-price">{{ (quote.price || 0).toFixed(2) }}</span>
              <span class="quote-pct">{{ quote.change_pct >= 0 ? '+' : '' }}{{ (quote.change_pct || 0).toFixed(2) }}%</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-small">
          <span>暂无自选股</span>
          <button class="btn-link" @click="$router.push('/watchlist')">添加</button>
        </div>
      </div>

      <div class="signal-section">
        <h2 class="section-title">今日信号</h2>
        <div v-if="signalFlow.length" class="signal-list">
          <div
            v-for="sig in signalFlow"
            :key="sig.date + sig.strategy + sig.symbol"
            class="signal-item"
            :class="sig.signal"
            @click="sig.symbol && $router.push(`/stock/${sig.symbol}`)"
          >
            <div class="signal-bar" :class="sig.signal"></div>
            <div class="signal-content">
              <div class="signal-top">
                <span class="signal-time">{{ (sig.date || '').slice(5) }}</span>
                <span class="signal-stock">{{ sig.symbol || '' }} {{ sig.stock_name || '' }}</span>
              </div>
              <div class="signal-bottom">
                <span class="signal-badge" :class="sig.signal">{{ sig.signal === 'buy' ? '买入' : '卖出' }}</span>
                <span class="signal-strategy">{{ sig.strategy }}</span>
                <span class="signal-conf">{{ (sig.confidence * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state-small">暂无信号</div>
      </div>

      <div class="dragon-section">
        <h2 class="section-title">龙虎榜/涨停板</h2>
        <div v-if="limitUpData.length" class="mini-table">
          <div v-for="s in limitUpData.slice(0, 5)" :key="s.code" class="mini-row" @click="$router.push(`/stock/${s.code}`)">
            <span class="mini-code">{{ s.code }}</span>
            <span class="mini-name">{{ s.name }}</span>
            <span class="mini-tag hot">{{ s.continuous || s.chain_count || 1 }}板</span>
          </div>
        </div>
        <div v-else-if="dragonData.length" class="mini-table">
          <div v-for="s in dragonData.slice(0, 5)" :key="s.code || s.symbol" class="mini-row" @click="$router.push(`/stock/${s.code || s.symbol}`)">
            <span class="mini-code">{{ s.code || s.symbol }}</span>
            <span class="mini-name">{{ s.name }}</span>
            <span class="mini-reason">{{ s.reason || '-' }}</span>
          </div>
        </div>
        <div v-else class="empty-state-small">暂无数据</div>
      </div>
    </div>

    <div class="extra-grid" v-if="systemMetrics || weeklyReport">
      <div class="metrics-section" v-if="systemMetrics">
        <h2 class="section-title">系统状态</h2>
        <div class="sys-metrics">
          <div class="sys-item" v-if="systemMetrics.uptime_seconds">
            <span class="sys-label">运行时间</span>
            <span class="sys-value">{{ fmtUptime(systemMetrics.uptime_seconds) }}</span>
          </div>
          <div class="sys-item" v-if="systemMetrics.api_requests_total">
            <span class="sys-label">API请求</span>
            <span class="sys-value">{{ systemMetrics.api_requests_total }}</span>
          </div>
          <div class="sys-item" v-if="systemMetrics.avg_response_time">
            <span class="sys-label">平均响应</span>
            <span class="sys-value">{{ systemMetrics.avg_response_time.toFixed(1) }}ms</span>
          </div>
        </div>
      </div>

      <div class="report-section" v-if="weeklyReport">
        <h2 class="section-title">市场周报 ({{ weeklyReport.report_date || '' }})</h2>
        <div class="report-summary" v-if="weeklyReport.market_summary">
          <div v-for="(info, name) in weeklyReport.market_summary" :key="name" class="report-index">
            <span class="report-name">{{ name }}</span>
            <span class="report-pct" :class="(info.change_pct || 0) >= 0 ? 'up' : 'down'">{{ (info.change_pct || 0).toFixed(2) }}%</span>
          </div>
        </div>
        <div class="report-sectors" v-if="weeklyReport.sector_performance">
          <div v-if="weeklyReport.sector_performance.top_gainers?.length" class="sector-group">
            <span class="sector-group-label up">领涨板块</span>
            <span v-for="s in weeklyReport.sector_performance.top_gainers.slice(0, 3)" :key="s.name" class="sector-tag up">{{ s.name }} +{{ s.change_pct.toFixed(2) }}%</span>
          </div>
          <div v-if="weeklyReport.sector_performance.top_losers?.length" class="sector-group">
            <span class="sector-group-label down">领跌板块</span>
            <span v-for="s in weeklyReport.sector_performance.top_losers.slice(0, 3)" :key="s.name" class="sector-tag down">{{ s.name }} {{ s.change_pct.toFixed(2) }}%</span>
          </div>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { api } from '../api'
import echarts from '../lib/echarts'
import { useWebSocketStore } from '../stores/websocket.store'

const overview = ref<any>({ cn_indices: {}, hk_indices: {}, us_indices: {}, temperature: 50 })
const watchlist = ref<any>({ symbols: [], quotes: {} })
const account = ref<any>({})
const heatmapItems = ref<any[]>([])
const signalFlow = ref<any[]>([])
const loading = ref(true)
const northboundData = ref<any>(null)
const limitUpData = ref<any[]>([])
const dragonData = ref<any[]>([])
const marketStatus = ref<any>({})
const systemMetrics = ref<any>(null)
const weeklyReport = ref<any>(null)
const lastUpdate = ref('')
const currentTime = ref('')
let updateTimer: any = null
let clockTimer: any = null

const wsStore = useWebSocketStore()

watch(() => wsStore.lastMessage, (msg: any) => {
  if (!msg) return
  if (msg.type === 'quote_update') {
    const data = msg.data || {}
    if (data.indices) {
      const idx = data.indices
      if (idx.sh000001) overview.value.cn_indices = { ...overview.value.cn_indices, sh000001: idx.sh000001 }
      if (idx.sz399001) overview.value.cn_indices = { ...overview.value.cn_indices, sz399001: idx.sz399001 }
      if (idx.sz399006) overview.value.cn_indices = { ...overview.value.cn_indices, sz399006: idx.sz399006 }
      lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
      nextTick(() => renderSparklines())
    }
    if (data.quotes) {
      const q = data.quotes
      const existing = watchlist.value.quotes || {}
      watchlist.value.quotes = { ...existing, ...q }
    }
  } else if (msg.type === 'signal') {
    const s = msg.data || msg
    signalFlow.value.unshift({
      time: new Date().toLocaleTimeString('zh-CN'),
      symbol: s.symbol,
      strategy: s.strategy,
      signal_type: s.signal_type,
      score: s.score,
    })
    if (signalFlow.value.length > 20) signalFlow.value = signalFlow.value.slice(0, 20)
  } else if (msg.type === 'market_event') {
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
  }
})

const sparkRefs: Record<string, any> = {}
const sparkCharts: Record<string, any> = {}
const heatmapChartRef = ref<HTMLElement>()
const nbGaugeRef = ref<HTMLElement>()
let heatmapChart: any = null
let nbGaugeChart: any = null

function setSparkRef(key: string, el: any) {
  if (el) sparkRefs[key] = el
}

const allIndices = computed(() => {
  const cn = overview.value.cn_indices || {}
  const hk = overview.value.hk_indices || {}
  const us = overview.value.us_indices || {}
  return { ...cn, ...hk, ...us }
})

const temperature = computed(() => overview.value.temperature || 50)

const isMarketOpen = computed(() => {
  const ms = marketStatus.value
  if (!ms || !Object.keys(ms).length) {
    const now = new Date()
    const h = now.getHours()
    const m = now.getMinutes()
    const hm = h * 100 + m
    const day = now.getDay()
    if (day === 0 || day === 6) return false
    return (hm >= 915 && hm <= 1130) || (hm >= 1300 && hm <= 1500)
  }
  return Object.values(ms).some((s: any) => s?.is_open)
})

const nbNetInflow = computed(() => northboundData.value?.net_inflow || 0)

function fmtNum(n: number): string {
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtAmount(v: number): string {
  if (!v) return '0'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

function fmtUptime(seconds: number): string {
  if (!seconds) return '-'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 24) return Math.floor(h / 24) + '天' + (h % 24) + '时'
  return h + '时' + m + '分'
}

const watchlistQuotes = computed(() => Object.values(watchlist.value.quotes || {}).slice(0, 8))

function renderSparklines() {
  Object.entries(sparkRefs).forEach(([key, el]) => {
    if (!el || sparkCharts[key]) return
    const item = allIndices.value[key]
    if (!item) return
    const chart = echarts.init(el, undefined, { renderer: 'canvas' })
    const isUp = (item.change_pct || 0) >= 0
    const color = isUp ? '#f43f5e' : '#34d399'
    const data = item.sparkline || generateFakeSparkline(item.price || 0, item.change_pct || 0)
    chart.setOption({
      animation: false,
      grid: { left: 0, right: 0, top: 2, bottom: 2 },
      xAxis: { type: 'category', show: false, boundaryGap: false },
      yAxis: { type: 'value', show: false, scale: true },
      series: [{
        type: 'line', data, smooth: true, showSymbol: false,
        lineStyle: { width: 1.5, color },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: color + '30' }, { offset: 1, color: color + '00' }] } },
      }],
    })
    sparkCharts[key] = chart
  })
}

function generateFakeSparkline(price: number, pct: number): number[] {
  const pts: number[] = []
  const base = price / (1 + pct / 100)
  for (let i = 0; i < 30; i++) {
    const t = i / 29
    const noise = (Math.random() - 0.5) * base * 0.005
    pts.push(+(base + (price - base) * t + noise).toFixed(2))
  }
  return pts
}

function renderHeatmap() {
  if (!heatmapChartRef.value) return
  if (!heatmapChart) {
    heatmapChart = echarts.init(heatmapChartRef.value, undefined, { renderer: 'canvas' })
  }
  if (!heatmapItems.value.length) return
  const data = heatmapItems.value.map(item => ({
    name: item.name,
    value: Math.max(item.value || 1, 1),
    change_pct: item.change_pct || 0,
    leader: item.leader || '',
  }))
  heatmapChart.setOption({
    animation: false,
    tooltip: {
      formatter: (info: any) => {
        const d = info.data
        return `<b>${d.name}</b><br/>涨跌幅: <span style="color:${d.change_pct >= 0 ? '#f43f5e' : '#34d399'}">${d.change_pct >= 0 ? '+' : ''}${d.change_pct.toFixed(2)}%</span>${d.leader ? '<br/>领涨: ' + d.leader : ''}`
      },
    },
    series: [{
      type: 'treemap',
      data: data.map(d => ({
        name: d.name,
        value: d.value,
        itemStyle: {
          color: d.change_pct >= 3 ? '#f43f5e' : d.change_pct >= 1 ? '#f43f5e99' : d.change_pct >= 0 ? '#f43f5e44' : d.change_pct >= -1 ? '#34d39944' : d.change_pct >= -3 ? '#34d39999' : '#34d399',
          borderColor: 'rgba(0,0,0,0.3)',
          borderWidth: 1,
          gapWidth: 2,
        },
        change_pct: d.change_pct,
        leader: d.leader,
      })),
      roam: false,
      nodeClick: false,
      breadcrumb: { show: false },
      label: {
        show: true,
        formatter: (info: any) => {
          const d = info.data
          return `${d.name}\n${d.change_pct >= 0 ? '+' : ''}${d.change_pct.toFixed(2)}%`
        },
        fontSize: 11,
        color: '#e8eaed',
      },
      upperLabel: { show: false },
      itemStyle: { borderColor: 'rgba(0,0,0,0.3)', borderWidth: 1, gapWidth: 2 },
      levels: [{ itemStyle: { borderColor: 'rgba(0,0,0,0.3)', borderWidth: 1, gapWidth: 2 } }],
    }],
  }, true)
}

function renderNbGauge() {
  if (!nbGaugeRef.value) return
  if (!nbGaugeChart) {
    nbGaugeChart = echarts.init(nbGaugeRef.value, undefined, { renderer: 'canvas' })
  }
  const net = northboundData.value?.net_inflow || 0
  const maxVal = 200
  const val = Math.max(-maxVal, Math.min(maxVal, net / 1e8))
  nbGaugeChart.setOption({
    animation: false,
    series: [{
      type: 'gauge',
      startAngle: 200,
      endAngle: -20,
      min: -maxVal,
      max: maxVal,
      splitNumber: 4,
      radius: '90%',
      center: ['50%', '55%'],
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.35, '#34d399'],
            [0.5, '#666'],
            [0.65, '#f43f5e'],
            [1, '#f43f5e'],
          ],
        },
      },
      pointer: {
        itemStyle: { color: 'auto' },
        width: 4,
        length: '60%',
      },
      axisTick: { show: false },
      splitLine: { length: 8, lineStyle: { width: 2, color: '#999' } },
      axisLabel: {
        distance: 16,
        color: '#888',
        fontSize: 10,
        formatter: (v: number) => v.toFixed(0) + '亿',
      },
      detail: {
        valueAnimation: true,
        formatter: (v: number) => {
          const actual = northboundData.value?.net_inflow || 0
          return (actual >= 0 ? '+' : '') + fmtAmount(actual)
        },
        color: net >= 0 ? '#f43f5e' : '#34d399',
        fontSize: 16,
        fontWeight: 700,
        fontFamily: 'var(--font-mono)',
        offsetCenter: [0, '70%'],
      },
      title: { show: false },
      data: [{ value: val }],
    }],
  }, true)
}

async function loadData() {
  try {
    const [ov, wl, acc, hm, nb, lu, dt, ms, sm, wr] = await Promise.allSettled([
      api.getMarketOverview(),
      api.getWatchlist(),
      api.getAccount(),
      api.getMarketHeatmap(),
      api.getNorthboundDetail(),
      api.getLimitUpPool(),
      api.getDragonTiger(),
      api.getMarketStatus(),
      api.getSystemMetrics(),
      api.getWeeklyReport(),
    ])
    if (ov.status === 'fulfilled' && ov.value) overview.value = ov.value
    if (wl.status === 'fulfilled' && wl.value) watchlist.value = wl.value
    if (acc.status === 'fulfilled' && acc.value) account.value = acc.value
    if (hm.status === 'fulfilled' && hm.value) heatmapItems.value = (hm.value.items || []).slice(0, 30)
    if (nb.status === 'fulfilled' && nb.value) {
      const nbVal = nb.value
      if (Array.isArray(nbVal) && nbVal.length > 0) {
        northboundData.value = nbVal[nbVal.length - 1]
      } else if (nbVal && (nbVal.net_inflow !== undefined || nbVal.sh_inflow !== undefined)) {
        northboundData.value = nbVal
      }
    }
    if (lu.status === 'fulfilled' && lu.value) {
      limitUpData.value = Array.isArray(lu.value) ? lu.value : (lu.value.items || [])
    }
    if (dt.status === 'fulfilled' && dt.value) {
      dragonData.value = Array.isArray(dt.value) ? dt.value : (dt.value.items || [])
    }
    if (ms.status === 'fulfilled' && ms.value) marketStatus.value = ms.value
    if (sm.status === 'fulfilled' && sm.value) systemMetrics.value = sm.value
    if (wr.status === 'fulfilled' && wr.value) weeklyReport.value = wr.value
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
    await nextTick()
    renderSparklines()
    renderHeatmap()
    renderNbGauge()
    loading.value = false
  } catch (e) {
    console.error('Load data error:', e)
  }
}

async function loadSignals() {
  try {
    const wl = watchlist.value.symbols || []
    if (wl.length === 0) return
    const tasks = wl.slice(0, 3).map(sym => api.getSignals(sym, '1m'))
    const results = await Promise.allSettled(tasks)
    const allSignals: any[] = []
    results.forEach((r, i) => {
      if (r.status !== 'fulfilled' || !r.value?.signals) return
      const sym = wl[i]
      r.value.signals.slice(-5).forEach((s: any) => {
        ;(s.signals || []).forEach((sig: any) => {
          allSignals.push({
            date: s.date,
            symbol: sym,
            stock_name: sig.stock_name || '',
            strategy: sig.strategy,
            signal: sig.signal,
            confidence: sig.confidence || sig.score || 0,
          })
        })
      })
    })
    signalFlow.value = allSignals.sort((a, b) => b.date?.localeCompare(a.date) || 0).slice(0, 20)
  } catch (e) {}
}

function updateClock() {
  currentTime.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

function handleResize() {
  Object.values(sparkCharts).forEach(c => c?.resize())
  heatmapChart?.resize()
  nbGaugeChart?.resize()
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadData().then(() => {
    loadSignals()
    const syms = (watchlist.value.symbols || []).slice(0, 10)
    if (syms.length) wsStore.subscribe(syms)
  })
  updateTimer = setInterval(loadData, 30000)
  wsStore.connect()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
  if (clockTimer) clearInterval(clockTimer)
  window.removeEventListener('resize', handleResize)
  Object.values(sparkCharts).forEach(c => c?.dispose())
  heatmapChart?.dispose()
  nbGaugeChart?.dispose()
  wsStore.disconnect()
})
</script>

<style scoped>
.skeleton-dashboard { padding: 16px 20px; }
.skeleton-row { display: flex; gap: 12px; }
.skeleton { border-radius: 8px; background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary, #1a1a24) 50%, var(--bg-secondary) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.dashboard {
  padding: 16px 20px;
  max-width: 1440px;
  margin: 0 auto;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 40px 40px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  font-size: 11px;
  color: var(--text-secondary);
}
.status-divider { color: var(--text-tertiary); opacity: 0.3; }
.status-market.open { color: var(--accent-red); }
.status-market.closed { color: var(--text-tertiary); }
.status-right { margin-left: auto; color: var(--text-tertiary); font-size: 10px; }
.up { color: var(--accent-red); }
.down { color: var(--accent-green); }

.indices-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
  margin-bottom: 14px;
  scrollbar-width: thin;
}
.index-card {
  flex-shrink: 0;
  min-width: 150px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 2px;
  position: relative;
  animation: cardIn 0.4s ease-out both;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.index-card:hover {
  border-color: rgba(255,255,255,0.1);
}
.index-card.up {
  border-left: 3px solid var(--accent-red);
  box-shadow: inset 0 0 20px rgba(244,63,94,0.05);
}
.index-card.down {
  border-left: 3px solid var(--accent-green);
  box-shadow: inset 0 0 20px rgba(52,211,153,0.05);
}
.index-card:hover .index-hover-info { opacity: 1; }
@keyframes cardIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.index-top { display: flex; justify-content: space-between; align-items: center; }
.index-name { font-size: 11px; color: var(--text-secondary); }
.index-pct { font-size: 11px; font-family: var(--font-mono); font-weight: 600; }
.index-pct.up { color: var(--accent-red); }
.index-pct.down { color: var(--accent-green); }
.index-price { font-size: 20px; font-weight: 700; font-family: var(--font-mono); }
.index-price.up { color: var(--accent-red); }
.index-price.down { color: var(--accent-green); }
.index-spark { width: 100%; height: 28px; }
.index-hover-info {
  display: flex; gap: 8px; font-size: 10px; color: var(--text-tertiary);
  opacity: 0; transition: opacity 0.2s; margin-top: 2px;
}

.main-grid { display: grid; grid-template-columns: 1fr 300px; gap: 14px; margin-bottom: 14px; }
.right-col { display: flex; flex-direction: column; gap: 14px; }

.section-title {
  font-size: 11px; font-weight: 600; color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;
}

.heatmap-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px;
  min-height: 300px;
}
.heatmap-chart { width: 100%; height: 280px; }

.northbound-gauge-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px;
}
.nb-gauge { width: 100%; height: 140px; }
.nb-detail { display: flex; flex-direction: column; gap: 6px; margin-top: 4px; }
.nb-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 8px; background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); }
.nb-label { font-size: 11px; color: var(--text-secondary); }
.nb-val { font-size: 13px; font-weight: 600; font-family: var(--font-mono); }

.account-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px;
  flex: 1;
}
.account-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.metric { padding: 8px 10px; background: rgba(255,255,255,0.03); border-radius: var(--radius-sm); }
.metric-label { font-size: 10px; color: var(--text-tertiary); display: block; margin-bottom: 2px; }
.metric-value { font-size: 13px; font-weight: 600; font-family: var(--font-mono); color: var(--text-primary); }
.metric.up .metric-value { color: var(--accent-red); }
.metric.down .metric-value { color: var(--accent-green); }

.bottom-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }

.watchlist-section, .signal-section, .dragon-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px;
}

.quotes-list { display: flex; flex-direction: column; gap: 3px; }
.quote-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer;
  transition: background 0.15s;
}
.quote-row:hover { background: rgba(255,255,255,0.05); }
.quote-left { display: flex; gap: 8px; align-items: center; }
.quote-code { font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); }
.quote-name { font-size: 11px; color: var(--text-primary); }
.quote-right { display: flex; gap: 8px; align-items: center; }
.quote-price { font-family: var(--font-mono); font-size: 11px; font-weight: 600; color: var(--text-primary); }
.quote-pct { font-family: var(--font-mono); font-size: 11px; }
.quote-row.up .quote-pct { color: var(--accent-red); }
.quote-row.down .quote-pct { color: var(--accent-green); }

.signal-list { display: flex; flex-direction: column; gap: 4px; max-height: 260px; overflow-y: auto; }
.signal-item {
  display: flex; align-items: stretch; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.02); cursor: pointer; transition: background 0.15s;
  overflow: hidden;
}
.signal-item:hover { background: rgba(255,255,255,0.05); }
.signal-bar { width: 3px; flex-shrink: 0; }
.signal-bar.buy { background: var(--accent-red); }
.signal-bar.sell { background: var(--accent-green); }
.signal-content { padding: 6px 10px; flex: 1; min-width: 0; }
.signal-top { display: flex; gap: 8px; align-items: center; margin-bottom: 2px; }
.signal-time { font-size: 10px; color: var(--text-tertiary); font-family: var(--font-mono); }
.signal-stock { font-size: 11px; color: var(--text-primary); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.signal-bottom { display: flex; gap: 6px; align-items: center; }
.signal-badge {
  padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600;
}
.signal-badge.buy { background: rgba(244,63,94,0.2); color: var(--accent-red); }
.signal-badge.sell { background: rgba(52,211,153,0.2); color: var(--accent-green); }
.signal-strategy { font-size: 10px; color: var(--text-secondary); }
.signal-conf { font-size: 10px; font-family: var(--font-mono); color: var(--accent-cyan); }

.mini-table { display: flex; flex-direction: column; gap: 3px; }
.mini-row {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: var(--radius-sm); cursor: pointer;
  transition: background 0.15s;
}
.mini-row:hover { background: rgba(255,255,255,0.05); }
.mini-code { font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); width: 60px; }
.mini-name { font-size: 11px; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.mini-tag.hot { background: rgba(244,63,94,0.2); color: var(--accent-red); }
.mini-reason { font-size: 10px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.empty-state-small { text-align: center; padding: 20px; color: var(--text-tertiary); font-size: 12px; }
.btn-link { background: none; border: none; color: var(--accent-cyan); cursor: pointer; font-size: 12px; text-decoration: underline; margin-left: 8px; }

.extra-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 14px; }
.metrics-section, .report-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.sys-metrics { display: flex; gap: 16px; flex-wrap: wrap; }
.sys-item { display: flex; flex-direction: column; gap: 2px; padding: 8px 12px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); }
.sys-label { font-size: 10px; color: var(--text-tertiary); }
.sys-value { font-size: 13px; font-family: var(--font-mono); font-weight: 600; color: var(--text-primary); }
.report-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.report-index { display: flex; gap: 6px; align-items: center; padding: 4px 10px; background: rgba(255,255,255,0.02); border-radius: var(--radius-sm); }
.report-name { font-size: 11px; color: var(--text-secondary); }
.report-pct { font-size: 11px; font-family: var(--font-mono); font-weight: 600; }
.report-pct.up { color: var(--accent-red); }
.report-pct.down { color: var(--accent-green); }
.report-sectors { display: flex; flex-direction: column; gap: 6px; }
.sector-group { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sector-group-label { font-size: 11px; font-weight: 600; }
.sector-group-label.up { color: var(--accent-red); }
.sector-group-label.down { color: var(--accent-green); }
.sector-tag { font-size: 10px; padding: 2px 8px; border-radius: 3px; }
.sector-tag.up { background: rgba(244,63,94,0.1); color: var(--accent-red); }
.sector-tag.down { background: rgba(52,211,153,0.1); color: var(--accent-green); }
.status-market-detail { font-size: 11px; color: var(--text-secondary); }
.status-market-detail .open { color: var(--accent-red); font-weight: 600; }
.status-market-detail .closed { color: var(--text-tertiary); }

.temp-num.up { color: var(--accent-red); }
.temp-num.down { color: var(--accent-green); }

@media (max-width: 1024px) {
  .main-grid { grid-template-columns: 1fr; }
  .bottom-grid { grid-template-columns: 1fr; }
  .status-bar { flex-wrap: wrap; }
}
@media (max-width: 768px) {
  .dashboard { padding: 10px; }
  .indices-row { gap: 6px; }
  .index-card { min-width: 120px; padding: 8px 10px; }
  .index-price { font-size: 16px; }
  .index-spark { display: none; }
}
</style>
