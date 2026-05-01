<template>
  <div class="dashboard">
    <div v-if="loading" class="dash-skeleton">
      <div class="sk-row"><div class="skeleton" style="height:24px;width:100%;margin-bottom:10px"></div></div>
      <div class="sk-row" style="gap:8px"><div class="skeleton" style="height:72px;flex:1" v-for="i in 4" :key="i"></div></div>
      <div class="sk-row" style="gap:8px;margin-top:10px"><div class="skeleton" style="height:280px;flex:3"></div><div class="skeleton" style="height:280px;flex:2"></div></div>
    </div>
    <template v-else>

    <div class="status-strip">
      <span class="st-time mono">{{ currentTime }}</span>
      <span class="st-dot" :class="isMarketOpen ? 'live' : 'off'"></span>
      <span class="st-market" :class="isMarketOpen ? 'up' : 'muted'">{{ isMarketOpen ? '交易中' : '已休市' }}</span>
      <span class="st-sep"></span>
      <template v-if="northboundData">
        <span class="st-label">北向</span>
        <span class="st-val mono" :class="northboundData.net_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.net_inflow) }}</span>
        <span class="st-sep"></span>
      </template>
      <span class="st-label">温度</span>
      <span class="st-val mono" :class="temperature >= 60 ? 'up' : temperature <= 30 ? 'down' : ''">{{ temperature.toFixed(0) }}</span>
      <span class="st-right">更新 {{ lastUpdate }}</span>
    </div>

    <div v-if="hasIndices" class="indices-strip">
      <div v-for="(item, key, idx) in allIndices" :key="key" class="idx-card" :class="item.change_pct >= 0 ? 'rise' : 'fall'" :style="{animationDelay: idx*50+'ms'}">
        <div class="idx-head">
          <span class="idx-name">{{ item.name }}</span>
          <span class="idx-pct mono" :class="item.change_pct >= 0 ? 'up' : 'down'">{{ item.change_pct >= 0 ? '+' : '' }}{{ (item.change_pct || 0).toFixed(2) }}%</span>
        </div>
        <span class="idx-price mono" :class="item.change_pct >= 0 ? 'up' : 'down'">{{ (item.price || 0).toFixed(2) }}</span>
      </div>
    </div>

    <div v-if="hasHeatmap || hasNorthbound || hasAccount" class="main-grid" :class="{ 'single-col': !hasHeatmap }">
      <div v-if="hasHeatmap" class="heatmap-panel card">
        <div class="panel-head"><h2 class="section-title">板块热力图</h2></div>
        <div ref="heatmapRef" class="chart-area"></div>
      </div>
      <div v-if="hasNorthbound || hasAccount" class="side-col">
        <div v-if="hasNorthbound" class="nb-panel card">
          <div class="panel-head"><h2 class="section-title">北向资金</h2></div>
          <div ref="nbGaugeRef" class="nb-gauge"></div>
          <div class="nb-rows">
            <div class="nb-row"><span class="nb-label">沪股通</span><span class="nb-val mono" :class="northboundData.sh_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.sh_inflow) }}</span></div>
            <div class="nb-row"><span class="nb-label">深股通</span><span class="nb-val mono" :class="northboundData.sz_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.sz_inflow) }}</span></div>
          </div>
        </div>
        <div v-if="hasAccount" class="acct-panel card">
          <div class="panel-head"><h2 class="section-title">账户概览</h2></div>
          <div class="acct-grid">
            <div class="acct-item"><span class="acct-label">总资产</span><span class="acct-val mono">¥{{ fmtNum(account.total_assets || 100000) }}</span></div>
            <div class="acct-item"><span class="acct-label">持仓市值</span><span class="acct-val mono">¥{{ fmtNum(account.market_value || 0) }}</span></div>
            <div class="acct-item"><span class="acct-label">可用资金</span><span class="acct-val mono">¥{{ fmtNum(account.cash || 0) }}</span></div>
            <div class="acct-item" :class="(account.total_profit || 0) >= 0 ? 'up' : 'down'"><span class="acct-label">总盈亏</span><span class="acct-val mono">{{ (account.total_profit || 0) >= 0 ? '+' : '' }}¥{{ fmtNum(account.total_profit || 0) }}</span></div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="hasWatchlist || hasSignals || hasAnomaly" class="bottom-row" :style="bottomGridStyle">
      <div v-if="hasWatchlist" class="watch-panel card">
        <div class="panel-head">
          <h2 class="section-title">自选股</h2>
          <button class="btn-ghost" style="font-size:11px;padding:3px 8px" @click="$router.push('/watchlist')">管理</button>
        </div>
        <div class="wl-list">
          <div v-for="q in watchlistQuotes" :key="q.symbol" class="wl-row" :class="q.change_pct >= 0 ? 'rise' : 'fall'" @click="$router.push(`/stock/${q.symbol}`)">
            <div class="wl-left"><span class="wl-code mono">{{ q.symbol }}</span><span class="wl-name">{{ q.name }}</span></div>
            <div class="wl-right"><span class="wl-price mono">{{ (q.price || 0).toFixed(2) }}</span><span class="wl-pct mono" :class="q.change_pct >= 0 ? 'up' : 'down'">{{ q.change_pct >= 0 ? '+' : '' }}{{ (q.change_pct || 0).toFixed(2) }}%</span></div>
          </div>
        </div>
      </div>

      <div v-if="hasSignals" class="signal-panel card">
        <div class="panel-head"><h2 class="section-title">策略信号</h2></div>
        <div class="sig-list">
          <div v-for="sig in signalFlow" :key="sig.date+sig.strategy+sig.symbol" class="sig-row" @click="sig.symbol && $router.push(`/stock/${sig.symbol}`)">
            <div class="sig-bar" :class="sig.signal === 'buy' ? 'up-bg' : 'down-bg'"></div>
            <div class="sig-body">
              <div class="sig-top"><span class="sig-stock">{{ sig.symbol || '' }} {{ sig.stock_name || '' }}</span><span class="sig-badge badge" :class="sig.signal === 'buy' ? 'badge-up' : 'badge-down'">{{ sig.signal === 'buy' ? '买' : '卖' }}</span></div>
              <div class="sig-meta"><span class="sig-strat">{{ sig.strategy }}</span><span class="sig-conf mono">{{ (sig.confidence * 100).toFixed(0) }}%</span></div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasAnomaly" class="anomaly-panel card">
        <div class="panel-head"><h2 class="section-title">异动监控</h2></div>
        <div class="ano-list">
          <div v-for="a in anomalyData.slice(0,6)" :key="a.symbol" class="ano-row" @click="$router.push(`/stock/${a.symbol}`)">
            <span class="ano-code mono">{{ a.symbol }}</span>
            <span class="ano-name">{{ a.name }}</span>
            <span class="ano-pct mono" :class="a.change_pct >= 0 ? 'up' : 'down'">{{ a.change_pct >= 0 ? '+' : '' }}{{ (a.change_pct || 0).toFixed(2) }}%</span>
            <span class="ano-reason badge badge-warn">{{ a.reason }}</span>
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
import { useToast } from '../composables/useToast'
import echarts from '../lib/echarts'
import { useWebSocketStore } from '../stores/websocket.store'

const overview = ref<any>({ cn_indices: {}, hk_indices: {}, us_indices: {}, temperature: 50 })
const watchlist = ref<any>({ symbols: [], quotes: {} })
const account = ref<any>({})
const heatmapItems = ref<any[]>([])
const signalFlow = ref<any[]>([])
const anomalyData = ref<any[]>([])
const loading = ref(true)
const northboundData = ref<any>(null)
const lastUpdate = ref('')
const currentTime = ref('')
let updateTimer: any = null
let clockTimer: any = null

const wsStore = useWebSocketStore()
const toast = useToast()

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
    }
    if (data.quotes) {
      const existing = watchlist.value.quotes || {}
      watchlist.value.quotes = { ...existing, ...data.quotes }
    }
  } else if (msg.type === 'signal') {
    const s = msg.data || msg
    signalFlow.value.unshift({
      time: new Date().toLocaleTimeString('zh-CN'),
      date: new Date().toISOString().slice(0, 10),
      symbol: s.symbol, stock_name: s.stock_name || '',
      strategy: s.strategy, signal: s.signal_type || s.signal || 'hold',
      confidence: s.score || s.confidence || 0,
    })
    if (signalFlow.value.length > 20) signalFlow.value = signalFlow.value.slice(0, 20)
  }
})

const heatmapRef = ref<HTMLElement>()
const nbGaugeRef = ref<HTMLElement>()
let heatmapChart: any = null
let nbGaugeChart: any = null

const allIndices = computed(() => ({ ...(overview.value.cn_indices || {}), ...(overview.value.hk_indices || {}), ...(overview.value.us_indices || {}) }))
const temperature = computed(() => overview.value.temperature || 50)
const isMarketOpen = computed(() => {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  const hm = now.getHours() * 100 + now.getMinutes()
  return (hm >= 915 && hm <= 1130) || (hm >= 1300 && hm <= 1500)
})
const watchlistQuotes = computed(() => {
  const quotes = watchlist.value.quotes || {}
  return Object.entries(quotes).map(([symbol, q]: [string, any]) => ({ symbol, ...q })).slice(0, 6)
})

const hasIndices = computed(() => Object.keys(allIndices.value).length > 0)
const hasHeatmap = computed(() => heatmapItems.value.length > 0)
const hasNorthbound = computed(() => northboundData.value !== null)
const hasAccount = computed(() => Object.keys(account.value).length > 0)
const hasWatchlist = computed(() => watchlistQuotes.value.length > 0)
const hasSignals = computed(() => signalFlow.value.length > 0)
const hasAnomaly = computed(() => anomalyData.value.length > 0)

const bottomGridStyle = computed(() => {
  const count = [hasWatchlist.value, hasSignals.value, hasAnomaly.value].filter(Boolean).length
  return { gridTemplateColumns: `repeat(${count}, 1fr)` }
})

function fmtNum(n: number) { return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmtAmt(v: number) {
  if (!v) return '0'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return v.toFixed(2)
}

function renderHeatmap() {
  if (!heatmapRef.value || !heatmapItems.value.length) return
  if (!heatmapChart) heatmapChart = echarts.init(heatmapRef.value, undefined, { renderer: 'canvas' })
  heatmapChart.setOption({
    animation: false,
    tooltip: { formatter: (i: any) => { const d = i.data; return `<b>${d.name}</b><br/><span style="color:${d.cp >= 0 ? '#ef4444' : '#22c55e'}">${d.cp >= 0 ? '+' : ''}${d.cp.toFixed(2)}%</span>` } },
    series: [{
      type: 'treemap', data: heatmapItems.value.map(d => ({
        name: d.name, value: Math.max(d.value || 1, 1), cp: d.change_pct || 0,
        itemStyle: { color: d.change_pct >= 3 ? '#ef4444' : d.change_pct >= 1 ? 'rgba(239,68,68,0.6)' : d.change_pct >= 0 ? 'rgba(239,68,68,0.25)' : d.change_pct >= -1 ? 'rgba(34,197,94,0.25)' : d.change_pct >= -3 ? 'rgba(34,197,94,0.6)' : '#22c55e', borderColor: 'rgba(0,0,0,0.4)', borderWidth: 1, gapWidth: 2 },
      })),
      roam: false, nodeClick: false, breadcrumb: { show: false },
      label: { show: true, formatter: (i: any) => `${i.data.name}\n${i.data.cp >= 0 ? '+' : ''}${i.data.cp.toFixed(2)}%`, fontSize: 10, color: '#e4e7ec', fontFamily: 'DM Mono, monospace' },
    }],
  }, true)
}

function renderNbGauge() {
  if (!nbGaugeRef.value || !northboundData.value) return
  if (!nbGaugeChart) nbGaugeChart = echarts.init(nbGaugeRef.value, undefined, { renderer: 'canvas' })
  const net = northboundData.value.net_inflow || 0
  const maxVal = 200
  const val = Math.max(-maxVal, Math.min(maxVal, net / 1e8))
  nbGaugeChart.setOption({
    animation: false,
    series: [{
      type: 'gauge', startAngle: 200, endAngle: -20, min: -maxVal, max: maxVal, splitNumber: 4, radius: '88%', center: ['50%', '55%'],
      axisLine: { lineStyle: { width: 10, color: [[0.35, '#22c55e'], [0.5, '#4a5068'], [0.65, '#ef4444'], [1, '#ef4444']] } },
      pointer: { itemStyle: { color: 'auto' }, width: 3, length: '55%' },
      axisTick: { show: false }, splitLine: { length: 6, lineStyle: { width: 1.5, color: '#4a5068' } },
      axisLabel: { distance: 14, color: '#4a5068', fontSize: 9, fontFamily: 'DM Mono', formatter: (v: number) => v.toFixed(0) + '亿' },
      detail: { valueAnimation: true, formatter: () => (net >= 0 ? '+' : '') + fmtAmt(net), color: net >= 0 ? '#ef4444' : '#22c55e', fontSize: 14, fontWeight: 700, fontFamily: 'DM Mono', offsetCenter: [0, '72%'] },
      title: { show: false }, data: [{ value: val }],
    }],
  }, true)
}

async function loadData() {
  try {
    const [ov, wl, acc, hm, nb, anomaly] = await Promise.allSettled([
      api.getMarketOverview(), api.getWatchlist(), api.getAccount(),
      api.getMarketHeatmap(), api.getNorthboundDetail(), api.getAnomalyList(),
    ])
    if (ov.status === 'fulfilled' && ov.value) overview.value = ov.value
    if (wl.status === 'fulfilled' && wl.value) watchlist.value = wl.value
    if (acc.status === 'fulfilled' && acc.value) account.value = acc.value
    if (hm.status === 'fulfilled' && hm.value) {
      const items = hm.value.items || hm.value || []
      heatmapItems.value = Array.isArray(items) ? items.slice(0, 30) : []
    }
    if (nb.status === 'fulfilled' && nb.value) {
      const nbVal = nb.value
      if (nbVal && (nbVal.net_inflow !== undefined || nbVal.sh_inflow !== undefined)) northboundData.value = nbVal
      else northboundData.value = null
    } else {
      northboundData.value = null
    }
    if (anomaly.status === 'fulfilled' && anomaly.value) {
      const arr = Array.isArray(anomaly.value) ? anomaly.value : []
      anomalyData.value = arr.length > 0 ? arr : []
    } else {
      anomalyData.value = []
    }
    lastUpdate.value = new Date().toLocaleTimeString('zh-CN')
    await nextTick()
    renderHeatmap()
    renderNbGauge()
    loading.value = false
  } catch (e) {
    loading.value = false
    toast.error(e instanceof Error ? e.message : '数据加载失败')
  }
}

function updateClock() { currentTime.value = new Date().toLocaleString('zh-CN', { hour12: false }) }
function handleResize() { heatmapChart?.resize(); nbGaugeChart?.resize() }

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadData().then(() => {
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
  heatmapChart?.dispose(); nbGaugeChart?.dispose()
  wsStore.disconnect()
})
</script>

<style scoped>
.dashboard { padding: 14px 16px; max-width: 1440px; margin: 0 auto; }

.dash-skeleton { padding: 14px 16px; }
.sk-row { display: flex; gap: 8px; }

.status-strip {
  display: flex; align-items: center; gap: 8px; padding: 5px 12px;
  background: var(--bg-secondary); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); margin-bottom: 10px; font-size: 11px;
}
.st-time { color: var(--text-secondary); font-size: 11px; }
.st-dot { width: 6px; height: 6px; border-radius: 50%; }
.st-dot.live { background: var(--accent-green); box-shadow: var(--glow-green); animation: pulse 2s infinite; }
.st-dot.off { background: var(--text-tertiary); }
.st-market { font-weight: 600; font-size: 11px; }
.st-market.up { color: var(--accent-red); }
.st-market.muted { color: var(--text-tertiary); }
.st-sep { width: 1px; height: 12px; background: var(--border-color); }
.st-label { color: var(--text-tertiary); font-size: 10px; }
.st-val { font-size: 11px; font-weight: 600; }
.st-right { margin-left: auto; color: var(--text-tertiary); font-size: 10px; font-family: var(--font-mono); }

.indices-strip {
  display: flex; gap: 6px; margin-bottom: 10px; overflow-x: auto;
  padding-bottom: 4px; scrollbar-width: none;
}
.indices-strip::-webkit-scrollbar { display: none; }
.idx-card {
  flex-shrink: 0; min-width: 140px; padding: 10px 14px;
  background: var(--bg-secondary); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); animation: slideUp 0.4s ease-out both;
  transition: border-color var(--transition);
}
.idx-card:hover { border-color: var(--border-color); }
.idx-card.rise { border-left: 2px solid var(--accent-red); }
.idx-card.fall { border-left: 2px solid var(--accent-green); }
.idx-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
.idx-name { font-size: 10px; color: var(--text-tertiary); }
.idx-pct { font-size: 10px; font-weight: 600; }
.idx-price { font-size: 18px; font-weight: 700; }

.main-grid { display: grid; grid-template-columns: 1fr 280px; gap: 8px; margin-bottom: 8px; }
.main-grid.single-col { grid-template-columns: 1fr; }
.side-col { display: flex; flex-direction: column; gap: 8px; }

.panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.chart-area { width: 100%; height: 260px; }

.nb-gauge { width: 100%; height: 120px; }
.nb-rows { display: flex; flex-direction: column; gap: 4px; }
.nb-row { display: flex; justify-content: space-between; align-items: center; padding: 5px 8px; background: var(--bg-hover); border-radius: var(--radius-sm); }
.nb-label { font-size: 11px; color: var(--text-secondary); }
.nb-val { font-size: 12px; font-weight: 600; }

.acct-panel { flex: 1; }
.acct-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.acct-item { padding: 8px; background: var(--bg-hover); border-radius: var(--radius-sm); }
.acct-label { display: block; font-size: 10px; color: var(--text-tertiary); margin-bottom: 2px; }
.acct-val { font-size: 12px; font-weight: 600; color: var(--text-primary); }
.acct-item.up .acct-val { color: var(--accent-red); }
.acct-item.down .acct-val { color: var(--accent-green); }

.bottom-row { display: grid; gap: 8px; }

.wl-list { display: flex; flex-direction: column; gap: 2px; }
.wl-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 5px 8px; border-radius: var(--radius-sm); cursor: pointer;
  transition: background var(--transition-fast);
}
.wl-row:hover { background: var(--bg-hover); }
.wl-left { display: flex; gap: 8px; align-items: center; }
.wl-code { font-size: 11px; color: var(--accent-cyan); }
.wl-name { font-size: 11px; color: var(--text-primary); }
.wl-right { display: flex; gap: 8px; align-items: center; }
.wl-price { font-size: 11px; font-weight: 600; color: var(--text-primary); }
.wl-pct { font-size: 11px; font-weight: 600; }

.sig-list { display: flex; flex-direction: column; gap: 3px; max-height: 240px; overflow-y: auto; }
.sig-row {
  display: flex; align-items: stretch; border-radius: var(--radius-sm);
  background: var(--bg-hover); cursor: pointer; overflow: hidden;
  transition: background var(--transition-fast);
}
.sig-row:hover { background: rgba(255,255,255,0.04); }
.sig-bar { width: 3px; flex-shrink: 0; }
.sig-body { padding: 5px 8px; flex: 1; min-width: 0; }
.sig-top { display: flex; gap: 6px; align-items: center; margin-bottom: 2px; }
.sig-stock { font-size: 11px; color: var(--text-primary); font-weight: 500; }
.sig-meta { display: flex; gap: 6px; align-items: center; }
.sig-strat { font-size: 10px; color: var(--text-secondary); }
.sig-conf { font-size: 10px; color: var(--accent-cyan); }

.ano-list { display: flex; flex-direction: column; gap: 3px; }
.ano-row {
  display: flex; align-items: center; gap: 6px; padding: 5px 8px;
  border-radius: var(--radius-sm); cursor: pointer; transition: background var(--transition-fast);
}
.ano-row:hover { background: var(--bg-hover); }
.ano-code { font-size: 11px; color: var(--accent-cyan); width: 50px; }
.ano-name { font-size: 11px; color: var(--text-primary); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ano-pct { font-size: 11px; font-weight: 600; width: 60px; text-align: right; }
.ano-reason { font-size: 9px; }

@media (max-width: 1024px) {
  .main-grid { grid-template-columns: 1fr; }
  .bottom-row { grid-template-columns: 1fr !important; }
}
@media (max-width: 768px) {
  .dashboard { padding: 10px; }
  .idx-card { min-width: 110px; padding: 8px 10px; }
  .idx-price { font-size: 15px; }
}
</style>
