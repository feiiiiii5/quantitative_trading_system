<template>
  <div class="market-page">
    <div v-if="loading" class="skeleton-market">
      <div class="skeleton" style="height:32px;width:200px;border-radius:8px;margin-bottom:12px"></div>
      <div class="skeleton-row">
        <div class="skeleton" style="height:400px;flex:1;border-radius:8px"></div>
      </div>
    </div>
    <template v-else>
    <div class="page-header">
      <h1 class="page-title">市场浏览</h1>
      <div class="header-actions">
        <div class="search-filter">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input v-model="filterText" placeholder="搜索代码/名称" class="filter-input" @input="onSearchInput" />
          <div v-if="searchResults.length" class="search-dropdown">
            <div v-for="r in searchResults" :key="r.symbol" class="search-item" @click="goToSearchResult(r.symbol)">
              <span class="search-code">{{ r.symbol }}</span>
              <span class="search-name">{{ r.name }}</span>
              <span class="search-market">{{ r.market || '' }}</span>
            </div>
          </div>
        </div>
        <button class="refresh-btn" @click="refreshAll" :class="{ spinning: refreshing }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg>
        </button>
      </div>
    </div>

    <div class="market-tabs">
      <button v-for="tab in tabs" :key="tab.key" class="tab-btn" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">
        {{ tab.label }}
      </button>
    </div>

    <div v-if="activeTab === 'list'" class="stock-list-section">
      <div class="list-toolbar">
        <div class="market-filter-btns">
          <button v-for="m in marketFilters" :key="m.value" class="mkt-btn" :class="{ active: marketFilter === m.value }" @click="marketFilter = m.value">{{ m.label }}</button>
        </div>
        <span class="list-count">共 {{ filteredStocks.length }} 只</span>
      </div>
      <div class="virtual-table" ref="virtualTableRef" @scroll="handleScroll">
        <div class="vt-header">
          <span class="vt-col code-col" @click="sortBy('symbol')">代码 {{ sortIcon('symbol') }}</span>
          <span class="vt-col name-col">名称</span>
          <span class="vt-col price-col" @click="sortBy('price')">最新价 {{ sortIcon('price') }}</span>
          <span class="vt-col pct-col" @click="sortBy('change_pct')">涨跌幅 {{ sortIcon('change_pct') }}</span>
          <span class="vt-col vol-col" @click="sortBy('volume')">成交量 {{ sortIcon('volume') }}</span>
          <span class="vt-col amt-col">成交额</span>
          <span class="vt-col tr-col">换手率</span>
          <span class="vt-col star-col">★</span>
        </div>
        <div class="vt-body" :style="{ height: totalHeight + 'px' }">
          <div class="vt-rows" :style="{ transform: `translateY(${offsetY}px)` }">
            <div
              v-for="stock in visibleStocks"
              :key="stock.symbol"
              class="vt-row"
              :class="{ up: stock.change_pct >= 0, down: stock.change_pct < 0 }"
              @click="$router.push(`/stock/${stock.symbol}`)"
            >
              <span class="vt-col code-col">{{ stock.symbol }}</span>
              <span class="vt-col name-col">{{ stock.name }}</span>
              <span class="vt-col price-col">{{ (stock.price || 0).toFixed(2) }}</span>
              <span class="vt-col pct-col">{{ stock.change_pct >= 0 ? '+' : '' }}{{ (stock.change_pct || 0).toFixed(2) }}%</span>
              <span class="vt-col vol-col">{{ fmtVol(stock.volume) }}</span>
              <span class="vt-col amt-col">{{ fmtVol(stock.amount || 0) }}</span>
              <span class="vt-col tr-col">{{ (stock.turnover_rate || 0).toFixed(2) }}%</span>
              <span class="vt-col star-col" @click.stop="toggleStar(stock.symbol)">
                <svg width="12" height="12" viewBox="0 0 24 24" :fill="isStarred(stock.symbol) ? 'var(--accent-yellow)' : 'none'" :stroke="isStarred(stock.symbol) ? 'var(--accent-yellow)' : 'var(--text-tertiary)'" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'heatmap'" class="heatmap-section">
      <div ref="heatmapRef" class="heatmap-chart"></div>
    </div>

    <div v-if="activeTab === 'sector'" class="sector-section">
      <div class="sector-grid">
        <div class="sector-chart-card">
          <h3 class="section-title">行业涨跌幅排名</h3>
          <div ref="sectorChartRef" class="sector-chart"></div>
        </div>
        <div class="sector-detail-card">
          <h3 class="section-title">行业详情</h3>
          <div class="sector-list">
            <div v-for="s in sectorData" :key="s.name" class="sector-row" :class="{ up: s.change_pct >= 0, down: s.change_pct < 0 }">
              <span class="sector-name">{{ s.name }}</span>
              <div class="sector-bar-wrap">
                <div class="sector-bar" :style="{ width: Math.min(Math.abs(s.change_pct) * 30, 100) + '%', background: s.change_pct >= 0 ? 'var(--accent-red)' : 'var(--accent-green)' }"></div>
              </div>
              <span class="sector-pct">{{ s.change_pct >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%</span>
              <span class="sector-leader" v-if="s.leader">{{ s.leader }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'limitup'" class="limitup-section">
      <div v-if="limitUpData.length" class="card-grid">
        <div v-for="s in limitUpData" :key="s.code" class="stock-card up" @click="$router.push(`/stock/${s.code}`)">
          <div class="card-top"><span class="card-code">{{ s.code }}</span><span class="card-tag hot">{{ s.continuous || s.chain_count || 1 }}板</span></div>
          <div class="card-name">{{ s.name }}</div>
          <div class="card-pct">+{{ (s.change_pct || 10).toFixed(2) }}%</div>
          <div class="card-detail">封单: {{ fmtVol(s.seal_amount || 0) }}</div>
        </div>
      </div>
      <div v-else class="empty-state-small">暂无涨停数据</div>
    </div>

    <div v-if="activeTab === 'dragon'" class="dragon-section">
      <DataTable v-if="dragonData.length" :columns="dragonColumns" :data="dragonData" :striped="true" row-key="code" :row-click="(r: any) => $router.push(`/stock/${r.code || r.symbol}`)" />
      <div v-else class="empty-state-small">暂无龙虎榜数据</div>
    </div>

    <div v-if="activeTab === 'northbound'" class="northbound-section">
      <div v-if="northboundHistory.length" class="nb-chart-wrap">
        <BaseChart :option="northboundChartOption" height="280px" />
      </div>
      <div v-if="northboundData" class="nb-summary">
        <div class="nb-card"><span class="nb-label">今日净流入</span><span class="nb-val" :class="northboundData.net_inflow >= 0 ? 'up' : 'down'">{{ fmtAmount(northboundData.net_inflow) }}</span></div>
        <div class="nb-card"><span class="nb-label">沪股通</span><span class="nb-val" :class="northboundData.sh_inflow >= 0 ? 'up' : 'down'">{{ fmtAmount(northboundData.sh_inflow) }}</span></div>
        <div class="nb-card"><span class="nb-label">深股通</span><span class="nb-val" :class="northboundData.sz_inflow >= 0 ? 'up' : 'down'">{{ fmtAmount(northboundData.sz_inflow) }}</span></div>
      </div>
      <div v-else class="empty-state-small">暂无北向资金数据</div>
    </div>

    <div v-if="activeTab === 'anomaly'" class="anomaly-section">
      <div v-if="anomalyData.length" class="card-grid">
        <div v-for="s in anomalyData" :key="s.symbol" class="stock-card" :class="s.change_pct >= 0 ? 'up' : 'down'" @click="$router.push(`/stock/${s.symbol}`)">
          <div class="card-top"><span class="card-code">{{ s.symbol }}</span><span class="card-tag warn">{{ s.reason || '异动' }}</span></div>
          <div class="card-name">{{ s.name }}</div>
          <div class="card-pct">{{ s.change_pct >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%</div>
        </div>
      </div>
      <div v-else class="empty-state-small">暂无异动数据</div>
    </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import echarts from '../lib/echarts'
import { DataTable, BaseChart } from '../components'
import { useWebSocketStore } from '../stores/websocket.store'

const activeTab = ref('list')
const filterText = ref('')
const refreshing = ref(false)
const loading = ref(true)
const marketFilter = ref('all')
const sortKey = ref('change_pct')
const sortOrder = ref(-1)
const stockList = ref<any[]>([])
const heatmapItems = ref<any[]>([])
const sectorData = ref<any[]>([])
const limitUpData = ref<any[]>([])
const dragonData = ref<any[]>([])
const northboundData = ref<any>(null)
const northboundHistory = ref<any[]>([])
const anomalyData = ref<any[]>([])
const starredSymbols = ref<Set<string>>(new Set())
const searchResults = ref<any[]>([])
let searchTimer: any = null

const wsStore = useWebSocketStore()
const router = useRouter()

watch(() => wsStore.lastMessage, (msg: any) => {
  if (!msg || msg.type !== 'quote_update') return
  const data = msg.data || {}
  if (data.quotes) {
    const updates = data.quotes
    stockList.value = stockList.value.map(s => {
      const u = updates[s.symbol]
      if (u) return { ...s, price: u.price ?? s.price, change_pct: u.change_pct ?? s.change_pct, volume: u.volume ?? s.volume, amount: u.amount ?? s.amount }
      return s
    })
  }
})

const virtualTableRef = ref<HTMLElement | null>(null)
const heatmapRef = ref<HTMLElement | null>(null)
const sectorChartRef = ref<HTMLElement | null>(null)
let heatmapChart: any = null
let sectorChart: any = null

const ROW_HEIGHT = 36
const BUFFER = 10
const scrollTop = ref(0)
const tableHeight = ref(600)

const tabs = [
  { key: 'list', label: '股票列表' },
  { key: 'heatmap', label: '板块热力图' },
  { key: 'sector', label: '行业排名' },
  { key: 'limitup', label: '涨停板' },
  { key: 'dragon', label: '龙虎榜' },
  { key: 'northbound', label: '北向资金' },
  { key: 'anomaly', label: '异动检测' },
]

const marketFilters = [
  { value: 'all', label: '全部' },
  { value: 'sh', label: '沪市' },
  { value: 'sz', label: '深市' },
  { value: 'cy', label: '创业板' },
  { value: 'kc', label: '科创板' },
]

const dragonColumns = [
  { key: 'code', label: '代码', width: '70px' },
  { key: 'name', label: '名称', width: '80px' },
  { key: 'reason', label: '上榜原因' },
  { key: 'buy_amount', label: '买入额', align: 'right' as const, format: (v: number) => fmtVol(v) },
  { key: 'sell_amount', label: '卖出额', align: 'right' as const, format: (v: number) => fmtVol(v) },
  { key: 'net_amount', label: '净额', align: 'right' as const, format: (v: number) => fmtVol(v) },
]

const filteredStocks = computed(() => {
  let list = stockList.value
  if (marketFilter.value === 'sh') list = list.filter(s => s.symbol.startsWith('6'))
  else if (marketFilter.value === 'sz') list = list.filter(s => s.symbol.startsWith('0'))
  else if (marketFilter.value === 'cy') list = list.filter(s => s.symbol.startsWith('3'))
  else if (marketFilter.value === 'kc') list = list.filter(s => s.symbol.startsWith('688'))
  if (filterText.value) {
    const q = filterText.value.toLowerCase()
    list = list.filter(s => s.symbol?.toLowerCase().includes(q) || s.name?.includes(q))
  }
  if (sortKey.value) {
    const key = sortKey.value
    const order = sortOrder.value
    list = [...list].sort((a, b) => {
      const va = a[key], vb = b[key]
      if (va == null && vb == null) return 0
      if (va == null) return order
      if (vb == null) return -order
      if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * order
      return String(va).localeCompare(String(vb)) * order
    })
  }
  return list
})

const totalHeight = computed(() => filteredStocks.value.length * ROW_HEIGHT)
const startIndex = computed(() => Math.max(0, Math.floor(scrollTop.value / ROW_HEIGHT) - BUFFER))
const endIndex = computed(() => Math.min(filteredStocks.value.length, Math.ceil((scrollTop.value + tableHeight.value) / ROW_HEIGHT) + BUFFER))
const offsetY = computed(() => startIndex.value * ROW_HEIGHT)
const visibleStocks = computed(() => filteredStocks.value.slice(startIndex.value, endIndex.value))

function handleScroll() {
  if (virtualTableRef.value) {
    scrollTop.value = virtualTableRef.value.scrollTop
  }
}

function sortBy(key: string) {
  if (sortKey.value === key) {
    sortOrder.value = sortOrder.value === 1 ? -1 : 1
  } else {
    sortKey.value = key
    sortOrder.value = -1
  }
}

function sortIcon(key: string): string {
  if (sortKey.value !== key) return ''
  return sortOrder.value === 1 ? '↑' : '↓'
}

function isStarred(symbol: string): boolean {
  return starredSymbols.value.has(symbol)
}

async function toggleStar(symbol: string) {
  if (starredSymbols.value.has(symbol)) {
    starredSymbols.value.delete(symbol)
    await api.removeFromWatchlist(symbol)
  } else {
    starredSymbols.value.add(symbol)
    await api.addToWatchlist(symbol)
  }
}

function fmtVol(v: number): string {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return String(Math.round(v))
}

function fmtAmount(v: number): string {
  if (!v) return '0'
  if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toFixed(2)
}

function switchTab(key: string) {
  activeTab.value = key
  nextTick(() => {
    if (key === 'heatmap') renderHeatmap()
    if (key === 'sector') renderSectorChart()
  })
}

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  const q = filterText.value.trim()
  if (!q) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    try {
      const data = await api.search(q, 8)
      if (data) searchResults.value = Array.isArray(data) ? data : (data.results || [])
    } catch (e) {
      searchResults.value = []
    }
  }, 300)
}

function goToSearchResult(symbol: string) {
  searchResults.value = []
  filterText.value = ''
  router.push(`/stock/${symbol}`)
}

function renderHeatmap() {
  if (!heatmapRef.value) return
  if (!heatmapChart) {
    heatmapChart = echarts.init(heatmapRef.value, undefined, { renderer: 'canvas' })
  }
  if (!heatmapItems.value.length) return
  const data = heatmapItems.value
  heatmapChart.setOption({
    animation: false,
    tooltip: { formatter: (info: any) => { const d = info.data; return `<b>${d.name}</b><br/>${d.change_pct >= 0 ? '+' : ''}${(d.change_pct || 0).toFixed(2)}%` } },
    series: [{
      type: 'treemap', data: data.map(d => ({
        name: d.name, value: Math.max(d.value || 1, 1),
        itemStyle: { color: d.change_pct >= 3 ? '#f43f5e' : d.change_pct >= 0 ? '#f43f5e66' : d.change_pct >= -3 ? '#34d39966' : '#34d399' },
        change_pct: d.change_pct,
      })),
      roam: false, nodeClick: false, breadcrumb: { show: false },
      label: { show: true, formatter: (info: any) => `${info.data.name}\n${info.data.change_pct >= 0 ? '+' : ''}${info.data.change_pct.toFixed(2)}%`, fontSize: 11, color: '#e8eaed' },
    }],
  }, true)
}

function renderSectorChart() {
  if (!sectorChartRef.value) return
  if (!sectorChart) {
    sectorChart = echarts.init(sectorChartRef.value, undefined, { renderer: 'canvas' })
  }
  const data = sectorData.value.slice(0, 20)
  sectorChart.setOption({
    animation: false,
    grid: { left: 80, right: 30, top: 10, bottom: 10 },
    xAxis: { type: 'value', axisLabel: { color: '#888', fontSize: 9, formatter: (v: number) => v.toFixed(1) + '%' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
    yAxis: { type: 'category', data: data.map(d => d.name), axisLabel: { color: '#888', fontSize: 10 }, axisLine: { show: false } },
    series: [{ type: 'bar', data: data.map(d => ({ value: d.change_pct, itemStyle: { color: d.change_pct >= 0 ? '#f43f5e' : '#34d399', borderRadius: d.change_pct >= 0 ? [0, 3, 3, 0] : [3, 0, 0, 3] } })) }],
  }, true)
}

const northboundChartOption = computed(() => {
  if (!northboundHistory.value.length) return {}
  const hist = northboundHistory.value
  const dates = hist.map((d: any) => (d.date || '').slice(5))
  const values = hist.map((d: any) => (d.net_inflow || 0) / 1e8)
  const cumValues: number[] = []
  let cum = 0
  values.forEach(v => { cum += v; cumValues.push(+cum.toFixed(2)) })
  return {
    backgroundColor: 'transparent', animation: false,
    tooltip: { trigger: 'axis' },
    legend: { data: ['净流入', '累计'], top: 0, textStyle: { color: '#888', fontSize: 10 } },
    grid: { left: 50, right: 50, top: 30, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { color: '#888', fontSize: 9 } },
    yAxis: [
      { type: 'value', name: '亿', axisLabel: { color: '#888', fontSize: 9 }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } } },
      { type: 'value', name: '累计亿', axisLabel: { color: '#888', fontSize: 9 }, splitLine: { show: false } },
    ],
    series: [
      { name: '净流入', type: 'bar', data: values.map(v => ({ value: v, itemStyle: { color: v >= 0 ? '#f43f5e' : '#34d399' } })) },
      { name: '累计', type: 'line', yAxisIndex: 1, data: cumValues, showSymbol: false, lineStyle: { width: 1.5, color: '#4d9fff' } },
    ],
  }
})

async function refreshAll() {
  refreshing.value = true
  try {
    await loadStockList()
    await loadMarketData()
  } finally {
    refreshing.value = false
    loading.value = false
  }
}

async function loadStockList() {
  try {
    const data = await api.getMarketOverview()
    if (data?.stocks) stockList.value = data.stocks
  } catch (e) {}
}

async function loadMarketData() {
  try {
    const [hm, sec, lu, dt, nb] = await Promise.allSettled([
      api.getMarketHeatmap(),
      api.getMarketOverview(),
      api.getLimitUpPool(),
      api.getDragonTiger(),
      api.getNorthboundDetail(),
    ])
    if (hm.status === 'fulfilled' && hm.value) heatmapItems.value = hm.value.items || []
    if (sec.status === 'fulfilled' && sec.value) sectorData.value = sec.value.sectors || sec.value.sector_data || []
    if (lu.status === 'fulfilled' && lu.value) limitUpData.value = Array.isArray(lu.value) ? lu.value : (lu.value.items || [])
    if (dt.status === 'fulfilled' && dt.value) dragonData.value = Array.isArray(dt.value) ? dt.value : (dt.value.items || [])
    if (nb.status === 'fulfilled' && nb.value) {
      const nbVal = nb.value
      if (Array.isArray(nbVal) && nbVal.length > 0) {
        northboundHistory.value = nbVal
        northboundData.value = nbVal[nbVal.length - 1]
      } else if (nbVal && (nbVal.net_inflow !== undefined || nbVal.sh_inflow !== undefined)) {
        northboundData.value = nbVal
        northboundHistory.value = [nbVal]
      }
    }
  } catch (e) {}
}

async function loadWatchlistStars() {
  try {
    const wl = await api.getWatchlist()
    if (wl?.symbols) starredSymbols.value = new Set(wl.symbols)
  } catch (e) {}
}

let updateTimer: any = null

onMounted(async () => {
  await loadWatchlistStars()
  await refreshAll()
  updateTimer = setInterval(loadStockList, 30000)
  wsStore.connect()
  if (stockList.value.length) {
    wsStore.subscribe(stockList.value.slice(0, 30).map((s: any) => s.symbol))
  }
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
  heatmapChart?.dispose()
  sectorChart?.dispose()
  wsStore.disconnect()
})

window.addEventListener('resize', () => {
  heatmapChart?.resize()
  sectorChart?.resize()
})
</script>

<style scoped>
.skeleton-market { padding: 20px; }
.skeleton-row { display: flex; gap: 12px; }
.skeleton { border-radius: 8px; background: linear-gradient(90deg, var(--bg-secondary) 25%, var(--bg-tertiary, #1a1a24) 50%, var(--bg-secondary) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.market-page { padding: 20px; max-width: 1440px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); }
.header-actions { display: flex; gap: 8px; align-items: center; }
.search-filter { display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); position: relative; }
.filter-input { background: transparent; border: none; color: var(--text-primary); font-size: 12px; width: 120px; outline: none; }
.search-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); margin-top: 4px; z-index: 50; max-height: 240px; overflow-y: auto; }
.search-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; cursor: pointer; transition: background 0.1s; }
.search-item:hover { background: rgba(255,255,255,0.05); }
.search-code { font-family: var(--font-mono); font-size: 11px; color: var(--accent-cyan); width: 60px; }
.search-name { font-size: 12px; color: var(--text-primary); flex: 1; }
.search-market { font-size: 10px; color: var(--text-tertiary); }
.refresh-btn { padding: 6px 8px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-sm); color: var(--text-secondary); cursor: pointer; transition: all 0.15s; }
.refresh-btn:hover { color: var(--text-primary); }
.refresh-btn.spinning svg { animation: spin 0.6s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.market-tabs { display: flex; gap: 2px; margin-bottom: 14px; background: var(--bg-secondary); border-radius: var(--radius-md); padding: 3px; overflow-x: auto; }
.tab-btn { padding: 7px 14px; border: none; background: transparent; color: var(--text-secondary); font-size: 12px; font-weight: 500; border-radius: var(--radius-sm); cursor: pointer; white-space: nowrap; transition: all 0.15s; }
.tab-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); }

.stock-list-section { }
.list-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.market-filter-btns { display: flex; gap: 3px; }
.mkt-btn { padding: 3px 10px; border: 1px solid var(--border-color); border-radius: 3px; background: transparent; color: var(--text-secondary); font-size: 11px; cursor: pointer; }
.mkt-btn.active { background: rgba(77,159,255,0.15); color: var(--accent-cyan); border-color: rgba(77,159,255,0.3); }
.list-count { font-size: 11px; color: var(--text-tertiary); }

.virtual-table { height: 600px; overflow-y: auto; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); }
.vt-header { display: flex; align-items: center; padding: 8px 12px; background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border-color); position: sticky; top: 0; z-index: 1; }
.vt-header .vt-col { font-size: 11px; color: var(--text-secondary); font-weight: 600; cursor: pointer; user-select: none; }
.vt-body { position: relative; }
.vt-rows { position: absolute; left: 0; right: 0; }
.vt-row { display: flex; align-items: center; padding: 0 12px; height: 36px; border-bottom: 1px solid rgba(255,255,255,0.02); cursor: pointer; transition: background 0.1s; }
.vt-row:hover { background: rgba(255,255,255,0.04); }
.vt-col { font-size: 11px; font-family: var(--font-mono); }
.code-col { width: 70px; color: var(--accent-cyan); }
.name-col { width: 80px; color: var(--text-primary); font-family: inherit; }
.price-col { width: 70px; text-align: right; }
.pct-col { width: 70px; text-align: right; font-weight: 600; }
.vol-col { width: 70px; text-align: right; color: var(--text-secondary); }
.amt-col { width: 80px; text-align: right; color: var(--text-secondary); }
.tr-col { width: 60px; text-align: right; color: var(--text-secondary); }
.star-col { width: 30px; text-align: center; cursor: pointer; }
.vt-row.up .price-col, .vt-row.up .pct-col { color: var(--accent-red); }
.vt-row.down .price-col, .vt-row.down .pct-col { color: var(--accent-green); }

.heatmap-section { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.heatmap-chart { width: 100%; height: 500px; }

.sector-section { }
.sector-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sector-chart-card, .sector-detail-card { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; }
.sector-chart { width: 100%; height: 500px; }
.sector-list { display: flex; flex-direction: column; gap: 4px; max-height: 500px; overflow-y: auto; }
.sector-row { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: var(--radius-sm); }
.sector-row:hover { background: rgba(255,255,255,0.03); }
.sector-name { width: 60px; font-size: 11px; color: var(--text-primary); }
.sector-bar-wrap { flex: 1; height: 8px; background: rgba(255,255,255,0.03); border-radius: 4px; overflow: hidden; }
.sector-bar { height: 100%; border-radius: 4px; transition: width 0.3s; }
.sector-pct { width: 60px; font-size: 11px; font-family: var(--font-mono); font-weight: 600; text-align: right; }
.sector-row.up .sector-pct { color: var(--accent-red); }
.sector-row.down .sector-pct { color: var(--accent-green); }
.sector-leader { font-size: 10px; color: var(--text-tertiary); }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 10px; }
.stock-card { padding: 12px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); cursor: pointer; transition: all 0.15s; }
.stock-card:hover { border-color: rgba(255,255,255,0.1); }
.stock-card.up { border-left: 3px solid var(--accent-red); }
.stock-card.down { border-left: 3px solid var(--accent-green); }
.card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.card-code { font-family: var(--font-mono); font-size: 12px; color: var(--accent-cyan); }
.card-tag { font-size: 10px; padding: 1px 6px; border-radius: 3px; }
.card-tag.hot { background: rgba(244,63,94,0.2); color: var(--accent-red); }
.card-tag.warn { background: rgba(251,146,60,0.2); color: var(--accent-orange); }
.card-name { font-size: 13px; color: var(--text-primary); margin-bottom: 4px; }
.card-pct { font-family: var(--font-mono); font-size: 16px; font-weight: 700; }
.stock-card.up .card-pct { color: var(--accent-red); }
.stock-card.down .card-pct { color: var(--accent-green); }
.card-detail { font-size: 10px; color: var(--text-tertiary); margin-top: 4px; }

.northbound-section { }
.nb-chart-wrap { background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 14px; margin-bottom: 14px; }
.nb-summary { display: flex; gap: 12px; }
.nb-card { flex: 1; padding: 14px; background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: var(--radius-md); display: flex; flex-direction: column; gap: 4px; }
.nb-label { font-size: 11px; color: var(--text-secondary); }
.nb-val { font-size: 18px; font-weight: 700; font-family: var(--font-mono); }
.nb-val.up { color: var(--accent-red); }
.nb-val.down { color: var(--accent-green); }

.section-title { font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }
.empty-state-small { text-align: center; padding: 40px; color: var(--text-tertiary); font-size: 13px; }

@media (max-width: 1024px) {
  .sector-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .market-page { padding: 10px; }
  .virtual-table { height: 400px; }
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); }
  .nb-summary { flex-direction: column; }
  .amt-col, .tr-col { display: none; }
}
</style>
