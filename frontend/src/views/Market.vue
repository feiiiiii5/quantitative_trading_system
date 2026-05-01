<template>
  <div class="market">
    <div class="page-header">
      <h1 class="page-title">市场</h1>
      <div class="header-right">
        <div class="search-box">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <input v-model="searchQuery" placeholder="代码 / 名称 / 拼音" class="search-input" @input="onSearchInput" @focus="showDrop = true" @blur="onBlur" />
          <div v-if="showDrop && searchResults.length" class="search-drop">
            <div v-for="r in searchResults" :key="r.symbol || r.code" class="sr-item" @mousedown.prevent="goResult(r.symbol || r.code)">
              <span class="sr-code mono">{{ r.symbol || r.code }}</span>
              <span class="sr-name">{{ r.name }}</span>
              <span class="sr-mkt">{{ r.market || 'A' }}</span>
            </div>
          </div>
        </div>
        <button class="refresh-btn" @click="refreshAll" :class="{ spinning: refreshing }">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6M3 12a9 9 0 0115.36-6.36L21 8M3 22v-6h6M21 12a9 9 0 01-15.36 6.36L3 16"/></svg>
        </button>
      </div>
    </div>

    <div class="tab-bar" style="margin-bottom:10px">
      <button v-for="tab in tabs" :key="tab.key" class="tab-btn" :class="{ active: activeTab === tab.key }" @click="switchTab(tab.key)">{{ tab.label }}</button>
    </div>

    <div v-if="activeTab === 'list'">
      <div class="list-toolbar">
        <div class="filter-btns">
          <button v-for="m in marketFilters" :key="m.value" class="fbtn" :class="{ active: marketFilter === m.value }" @click="marketFilter = m.value">{{ m.label }}</button>
        </div>
        <span class="list-count mono">{{ filteredStocks.length }} 只</span>
      </div>
      <div class="vtable" ref="vtableRef" @scroll="onScroll">
        <div class="vt-head">
          <span class="vc c-code" @click="doSort('symbol')">代码 {{ si('symbol') }}</span>
          <span class="vc c-name">名称</span>
          <span class="vc c-price" @click="doSort('price')">最新价 {{ si('price') }}</span>
          <span class="vc c-pct" @click="doSort('change_pct')">涨跌幅 {{ si('change_pct') }}</span>
          <span class="vc c-vol" @click="doSort('volume')">成交量 {{ si('volume') }}</span>
          <span class="vc c-amt" @click="doSort('amount')">成交额 {{ si('amount') }}</span>
          <span class="vc c-tr">换手率</span>
        </div>
        <div class="vt-body" :style="{ height: totalH + 'px' }">
          <div class="vt-rows" :style="{ transform: `translateY(${offY}px)` }">
            <div v-for="s in visibleStocks" :key="s.symbol" class="vt-row" :class="s.change_pct >= 0 ? 'rise' : 'fall'" @click="$router.push(`/stock/${s.symbol}`)">
              <span class="vc c-code mono">{{ s.symbol }}</span>
              <span class="vc c-name">{{ s.name }}</span>
              <span class="vc c-price mono">{{ (s.price || 0).toFixed(2) }}</span>
              <span class="vc c-pct mono" :class="s.change_pct >= 0 ? 'up' : 'down'">{{ s.change_pct >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%</span>
              <span class="vc c-vol mono muted">{{ fmtVol(s.volume) }}</span>
              <span class="vc c-amt mono muted">{{ fmtAmt(s.amount) }}</span>
              <span class="vc c-tr mono muted">{{ (s.turnover_rate || 0).toFixed(2) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="activeTab === 'heatmap'" class="card" style="padding:14px">
      <div ref="heatmapRef" class="chart-lg"></div>
    </div>

    <div v-if="activeTab === 'anomaly'">
      <div v-if="anomalyData.length" class="card-grid">
        <div v-for="s in anomalyData" :key="s.symbol" class="stock-card" :class="s.change_pct >= 0 ? 'rise' : 'fall'" @click="$router.push(`/stock/${s.symbol}`)">
          <div class="sc-top"><span class="sc-code mono">{{ s.symbol }}</span><span class="badge badge-warn">{{ s.reason }}</span></div>
          <div class="sc-name">{{ s.name }}</div>
          <div class="sc-pct mono" :class="s.change_pct >= 0 ? 'up' : 'down'">{{ s.change_pct >= 0 ? '+' : '' }}{{ (s.change_pct || 0).toFixed(2) }}%</div>
        </div>
      </div>
      <div v-else class="empty-state">暂无异动数据</div>
    </div>

    <div v-if="activeTab === 'northbound'">
      <div v-if="northboundData" class="nb-cards">
        <div class="nb-card card"><span class="nb-label">今日净流入</span><span class="nb-val mono" :class="northboundData.net_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.net_inflow) }}</span></div>
        <div class="nb-card card"><span class="nb-label">沪股通</span><span class="nb-val mono" :class="northboundData.sh_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.sh_inflow) }}</span></div>
        <div class="nb-card card"><span class="nb-label">深股通</span><span class="nb-val mono" :class="northboundData.sz_inflow >= 0 ? 'up' : 'down'">{{ fmtAmt(northboundData.sz_inflow) }}</span></div>
      </div>
      <div v-else class="empty-state">暂无北向资金数据</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useToast } from '../composables/useToast'
import echarts from '../lib/echarts'
import { useWebSocketStore } from '../stores/websocket.store'

const activeTab = ref('list')
const searchQuery = ref('')
const showDrop = ref(false)
const refreshing = ref(false)
const marketFilter = ref('all')
const sortKey = ref('amount')
const sortOrder = ref(-1)
const stockList = ref<any[]>([])
const heatmapItems = ref<any[]>([])
const anomalyData = ref<any[]>([])
const northboundData = ref<any>(null)
const searchResults = ref<any[]>([])
let searchTimer: any = null

const wsStore = useWebSocketStore()
const router = useRouter()
const toast = useToast()

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

const vtableRef = ref<HTMLElement | null>(null)
const heatmapRef = ref<HTMLElement | null>(null)
let heatmapChart: any = null

const RH = 34
const BUF = 15
const scrollTop = ref(0)
const tableH = ref(600)

const tabs = [
  { key: 'list', label: '股票列表' },
  { key: 'heatmap', label: '板块热力图' },
  { key: 'anomaly', label: '异动监控' },
  { key: 'northbound', label: '北向资金' },
]
const marketFilters = [
  { value: 'all', label: '全部' },
  { value: 'sh', label: '沪市' },
  { value: 'sz', label: '深市' },
  { value: 'cy', label: '创业板' },
  { value: 'kc', label: '科创板' },
]

const filteredStocks = computed(() => {
  let list = stockList.value
  if (marketFilter.value === 'sh') list = list.filter(s => s.symbol?.startsWith('6') && !s.symbol?.startsWith('688'))
  else if (marketFilter.value === 'sz') list = list.filter(s => s.symbol?.startsWith('0'))
  else if (marketFilter.value === 'cy') list = list.filter(s => s.symbol?.startsWith('3'))
  else if (marketFilter.value === 'kc') list = list.filter(s => s.symbol?.startsWith('688'))
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

const totalH = computed(() => filteredStocks.value.length * RH)
const startIdx = computed(() => Math.max(0, Math.floor(scrollTop.value / RH) - BUF))
const endIdx = computed(() => Math.min(filteredStocks.value.length, Math.ceil((scrollTop.value + tableH.value) / RH) + BUF))
const offY = computed(() => startIdx.value * RH)
const visibleStocks = computed(() => filteredStocks.value.slice(startIdx.value, endIdx.value))

function onScroll() { if (vtableRef.value) scrollTop.value = vtableRef.value.scrollTop }
function doSort(key: string) { if (sortKey.value === key) sortOrder.value = sortOrder.value === 1 ? -1 : 1; else { sortKey.value = key; sortOrder.value = -1 } }
function si(key: string): string { return sortKey.value === key ? (sortOrder.value === 1 ? '↑' : '↓') : '' }

function fmtVol(v: number): string { if (!v) return '-'; if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'; if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'; return String(Math.round(v)) }
function fmtAmt(v: number): string { if (!v) return '0'; if (Math.abs(v) >= 1e8) return (v / 1e8).toFixed(2) + '亿'; if (Math.abs(v) >= 1e4) return (v / 1e4).toFixed(1) + '万'; return v.toFixed(0) }

function switchTab(key: string) { activeTab.value = key; nextTick(() => { if (key === 'heatmap') renderHeatmap() }) }

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  const q = searchQuery.value.trim()
  if (!q) { searchResults.value = []; showDrop.value = false; return }
  showDrop.value = true
  searchTimer = setTimeout(async () => {
    try { const data = await api.search(q, 10); if (data) searchResults.value = Array.isArray(data) ? data : (data.results || []) } catch { searchResults.value = [] }
  }, 200)
}
function onBlur() { setTimeout(() => { showDrop.value = false }, 200) }
function goResult(symbol: string) { searchResults.value = []; showDrop.value = false; searchQuery.value = ''; router.push(`/stock/${symbol}`) }

function renderHeatmap() {
  if (!heatmapRef.value) return
  if (!heatmapChart) heatmapChart = echarts.init(heatmapRef.value, undefined, { renderer: 'canvas' })
  if (!heatmapItems.value.length) return
  heatmapChart.setOption({
    animation: false,
    tooltip: { formatter: (i: any) => { const d = i.data; return `<b>${d.name}</b><br/><span style="color:${d.cp >= 0 ? '#ef4444' : '#22c55e'}">${d.cp >= 0 ? '+' : ''}${d.cp.toFixed(2)}%</span>` } },
    series: [{
      type: 'treemap', data: heatmapItems.value.map(d => ({
        name: d.name, value: Math.max(d.value || 1, 1), cp: d.change_pct || 0,
        itemStyle: { color: d.change_pct >= 3 ? '#ef4444' : d.change_pct >= 0 ? 'rgba(239,68,68,0.4)' : d.change_pct >= -3 ? 'rgba(34,197,94,0.4)' : '#22c55e', borderColor: 'rgba(0,0,0,0.4)', borderWidth: 1, gapWidth: 2 },
      })),
      roam: false, nodeClick: false, breadcrumb: { show: false },
      label: { show: true, formatter: (i: any) => `${i.data.name}\n${i.data.cp >= 0 ? '+' : ''}${i.data.cp.toFixed(2)}%`, fontSize: 10, color: '#e4e7ec', fontFamily: 'DM Mono' },
    }],
  }, true)
}

async function refreshAll() {
  refreshing.value = true
  try { await loadStockList(); await loadMarketData() } finally { refreshing.value = false }
}

async function loadStockList() {
  try {
    const data = await api.getStockList(marketFilter.value === 'all' ? 'A' : marketFilter.value, 5000)
    if (Array.isArray(data)) stockList.value = data
  } catch (e) { toast.warning(e instanceof Error ? e.message : '股票列表加载失败') }
}

async function loadMarketData() {
  try {
    const [hm, nb, anomaly] = await Promise.allSettled([api.getMarketHeatmap(), api.getNorthboundDetail(), api.getAnomalyList()])
    if (hm.status === 'fulfilled' && hm.value) heatmapItems.value = hm.value.items || []
    if (nb.status === 'fulfilled' && nb.value) { const v = nb.value; if (v && (v.net_inflow !== undefined || v.sh_inflow !== undefined)) northboundData.value = v }
    if (anomaly.status === 'fulfilled' && anomaly.value) anomalyData.value = anomaly.value || []
  } catch { }
}

let updateTimer: any = null
function handleResize() { heatmapChart?.resize() }

onMounted(async () => {
  await refreshAll()
  updateTimer = setInterval(loadStockList, 30000)
  wsStore.connect()
  if (stockList.value.length) wsStore.subscribe(stockList.value.slice(0, 30).map((s: any) => s.symbol))
  window.addEventListener('resize', handleResize)
})
onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
  heatmapChart?.dispose(); wsStore.disconnect()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.market { padding: 14px 16px; max-width: 1440px; margin: 0 auto; }

.header-right { display: flex; gap: 6px; align-items: center; }
.search-box {
  display: flex; align-items: center; gap: 6px; padding: 5px 10px;
  background: var(--bg-elevated); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); position: relative;
  transition: border-color var(--transition-fast);
}
.search-box:focus-within { border-color: var(--border-active); box-shadow: 0 0 0 2px var(--accent-cyan-dim); }
.search-input { background: transparent; border: none; color: var(--text-primary); font-size: 12px; width: 160px; outline: none; padding: 0; }
.search-input::placeholder { color: var(--text-tertiary); }
.search-drop {
  position: absolute; top: 100%; left: 0; right: 0; margin-top: 4px;
  background: var(--bg-elevated); border: 1px solid var(--border-color);
  border-radius: var(--radius-sm); z-index: 50; max-height: 280px; overflow-y: auto;
  box-shadow: var(--shadow-md);
}
.sr-item { display: flex; align-items: center; gap: 8px; padding: 7px 10px; cursor: pointer; transition: background var(--transition-fast); }
.sr-item:hover { background: var(--bg-hover); }
.sr-code { font-size: 11px; color: var(--accent-cyan); width: 55px; }
.sr-name { font-size: 12px; color: var(--text-primary); flex: 1; }
.sr-mkt { font-size: 10px; color: var(--text-tertiary); }

.refresh-btn {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center;
  color: var(--text-tertiary); transition: all var(--transition-fast);
}
.refresh-btn:hover { color: var(--text-primary); border-color: var(--border-color); }
.refresh-btn.spinning svg { animation: spin 0.6s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.list-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.filter-btns { display: flex; gap: 2px; }
.fbtn { padding: 3px 10px; border: 1px solid var(--border-subtle); border-radius: var(--radius-xs); font-size: 11px; color: var(--text-secondary); background: transparent; }
.fbtn.active { background: var(--accent-cyan-dim); color: var(--accent-cyan); border-color: rgba(56,189,248,0.2); }
.list-count { font-size: 11px; color: var(--text-tertiary); }

.vtable { height: 600px; overflow-y: auto; background: var(--bg-secondary); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); }
.vt-head {
  display: flex; align-items: center; padding: 7px 10px;
  background: rgba(255,255,255,0.02); border-bottom: 1px solid var(--border-subtle);
  position: sticky; top: 0; z-index: 1;
}
.vt-head .vc { font-size: 10px; color: var(--text-tertiary); font-weight: 600; cursor: pointer; user-select: none; text-transform: uppercase; letter-spacing: 0.04em; }
.vt-body { position: relative; }
.vt-rows { position: absolute; left: 0; right: 0; }
.vt-row {
  display: flex; align-items: center; padding: 0 10px; height: 34px;
  border-bottom: 1px solid var(--border-subtle); cursor: pointer;
  transition: background var(--transition-fast);
}
.vt-row:hover { background: var(--bg-hover); }
.vc { font-size: 11px; }
.c-code { width: 60px; color: var(--accent-cyan); }
.c-name { width: 70px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-price { width: 65px; text-align: right; }
.c-pct { width: 65px; text-align: right; font-weight: 600; }
.c-vol { width: 65px; text-align: right; }
.c-amt { width: 70px; text-align: right; }
.c-tr { width: 55px; text-align: right; }
.vt-row.rise .c-price, .vt-row.rise .c-pct { color: var(--accent-red); }
.vt-row.fall .c-price, .vt-row.fall .c-pct { color: var(--accent-green); }
.muted { color: var(--text-tertiary); }

.chart-lg { width: 100%; height: 500px; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 8px; }
.stock-card {
  padding: 10px 12px; background: var(--bg-secondary); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); cursor: pointer; transition: border-color var(--transition);
}
.stock-card:hover { border-color: var(--border-color); }
.stock-card.rise { border-left: 2px solid var(--accent-red); }
.stock-card.fall { border-left: 2px solid var(--accent-green); }
.sc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
.sc-code { font-size: 11px; color: var(--accent-cyan); }
.sc-name { font-size: 12px; color: var(--text-primary); margin-bottom: 2px; }
.sc-pct { font-size: 15px; font-weight: 700; }

.nb-cards { display: flex; gap: 10px; }
.nb-card { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.nb-label { font-size: 11px; color: var(--text-secondary); }
.nb-val { font-size: 18px; font-weight: 700; }

@media (max-width: 768px) {
  .market { padding: 10px; }
  .vtable { height: 400px; }
  .c-vol, .c-amt, .c-tr { display: none; }
  .search-input { width: 120px; }
  .nb-cards { flex-direction: column; }
}
</style>
