<template>
  <div class="dashboard fade-in">
    <header class="page-header">
      <div>
        <h1 class="page-title">市场总览</h1>
        <p class="page-subtitle">实时市场行情与数据监控</p>
      </div>
      <div class="header-search">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input v-model="searchQuery" placeholder="搜索股票代码或名称..." @input="onSearch" @focus="showResults=true" />
        <div v-if="showResults && searchResults.length" class="search-dropdown">
          <div v-for="item in searchResults" :key="item.code" class="search-item" @click="goStock(item.code)">
            <span class="font-mono">{{ item.code }}</span>
            <span>{{ item.name }}</span>
            <span class="market-tag">{{ item.market }}</span>
          </div>
        </div>
      </div>
    </header>

    <section class="indices-section">
      <div class="indices-row">
        <div v-for="idx in indices" :key="idx.symbol" class="index-card" :class="idx.pct >= 0 ? 'up' : 'down'" @click="goStock(idx.symbol)">
          <div class="idx-name">{{ idx.name }}</div>
          <div class="idx-price font-mono">{{ fmtPrice(idx.price) }}</div>
          <div class="idx-change font-mono">
            <span>{{ idx.pct >= 0 ? '+' : '' }}{{ idx.pct?.toFixed(2) }}%</span>
            <span class="idx-abs">{{ idx.change >= 0 ? '+' : '' }}{{ idx.change?.toFixed(2) }}</span>
          </div>
        </div>
      </div>
    </section>

    <div class="grid-2">
      <section class="card">
        <h2 class="section-title">热门股票</h2>
        <div class="hot-table">
          <div class="table-header">
            <span>代码</span><span>名称</span><span class="r">现价</span><span class="r">涨跌幅</span>
          </div>
          <div v-for="s in hotStocks" :key="s.code" class="table-row" @click="goStock(s.code)">
            <span class="font-mono">{{ s.code }}</span>
            <span>{{ s.name }}</span>
            <span class="r font-mono">{{ fmtPrice(s.price) }}</span>
            <span class="r font-mono" :class="s.pct >= 0 ? 'text-up' : 'text-down'">{{ s.pct >= 0 ? '+' : '' }}{{ s.pct?.toFixed(2) }}%</span>
          </div>
        </div>
      </section>

      <section class="card">
        <h2 class="section-title">市场情绪</h2>
        <div class="sentiment-grid">
          <div class="sentiment-item">
            <div class="sentiment-label">上涨家数</div>
            <div class="sentiment-value text-up font-mono">{{ temperature.advancers || '-' }}</div>
          </div>
          <div class="sentiment-item">
            <div class="sentiment-label">下跌家数</div>
            <div class="sentiment-value text-down font-mono">{{ temperature.decliners || '-' }}</div>
          </div>
          <div class="sentiment-item">
            <div class="sentiment-label">涨跌比</div>
            <div class="sentiment-value font-mono">{{ temperature.up_down_ratio?.toFixed(2) || '-' }}</div>
          </div>
          <div class="sentiment-item">
            <div class="sentiment-label">成交额(亿)</div>
            <div class="sentiment-value font-mono">{{ fmtAmount(temperature.turnover_amount) }}</div>
          </div>
        </div>
        <div class="sentiment-bar">
          <div class="bar-fill" :style="{ width: advancersPct + '%', background: 'var(--accent-red)' }"></div>
        </div>
        <div class="sentiment-labels">
          <span class="text-up">上涨 {{ temperature.advancers || 0 }}</span>
          <span class="text-down">下跌 {{ temperature.decliners || 0 }}</span>
        </div>
      </section>
    </div>

    <section class="card" v-if="northbound.length">
      <h2 class="section-title">北向资金</h2>
      <div class="nb-table">
        <div class="table-header">
          <span>日期</span><span class="r">沪股通(亿)</span><span class="r">深股通(亿)</span><span class="r">净买入(亿)</span>
        </div>
        <div v-for="nb in northbound.slice(0, 10)" :key="nb.trade_date" class="table-row">
          <span class="font-mono">{{ nb.trade_date }}</span>
          <span class="r font-mono" :class="nb.sh_connect >= 0 ? 'text-up' : 'text-down'">{{ (nb.sh_connect / 1e8).toFixed(2) }}</span>
          <span class="r font-mono" :class="nb.sz_connect >= 0 ? 'text-up' : 'text-down'">{{ (nb.sz_connect / 1e8).toFixed(2) }}</span>
          <span class="r font-mono" :class="nb.net_buy >= 0 ? 'text-up' : 'text-down'">{{ (nb.net_buy / 1e8).toFixed(2) }}</span>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const showResults = ref(false)
const indices = ref<any[]>([])
const hotStocks = ref<any[]>([])
const temperature = ref<any>({})
const northbound = ref<any[]>([])

const advancersPct = computed(() => {
  const a = temperature.value.advancers || 0
  const d = temperature.value.decliners || 0
  if (a + d === 0) return 50
  return (a / (a + d)) * 100
})

function fmtPrice(v: number) { return v?.toFixed(2) || '-' }
function fmtAmount(v: number) {
  if (!v) return '-'
  return (v / 1e8).toFixed(0)
}

function goStock(code: string) {
  showResults.value = false
  searchQuery.value = ''
  router.push(`/stock/${code}`)
}

let searchTimer: any = null
function onSearch() {
  clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) { searchResults.value = []; return }
  searchTimer = setTimeout(async () => {
    try {
      searchResults.value = await api.search(searchQuery.value, 8)
    } catch { searchResults.value = [] }
  }, 300)
}

async function loadData() {
  try {
    const overview = await api.getMarketOverview()
    indices.value = overview.indices || []
    temperature.value = overview.temperature || {}
    northbound.value = overview.northbound || []
  } catch {}
  try {
    hotStocks.value = await api.getMarketHot(15)
  } catch {}
}

onMounted(loadData)
</script>

<style scoped>
.dashboard { padding: 24px 28px; max-width: 1400px; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.header-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  width: 280px;
  color: var(--text-tertiary);
}

.header-search input {
  background: none;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 13px;
  width: 100%;
  padding: 0;
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin-top: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  z-index: 100;
  box-shadow: var(--shadow-lg);
}

.search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  transition: background var(--transition);
}

.search-item:hover { background: rgba(255,255,255,0.05); }

.market-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(41,151,255,0.15);
  color: var(--accent-blue);
}

.indices-section { margin-bottom: 20px; }

.indices-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.index-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition);
}

.index-card:hover { border-color: rgba(255,255,255,0.15); transform: translateY(-1px); }
.index-card.up { border-left: 3px solid var(--accent-red); }
.index-card.down { border-left: 3px solid var(--accent-green); }

.idx-name { font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }
.idx-price { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 4px; }
.idx-change { display: flex; gap: 8px; font-size: 12px; }
.idx-abs { color: var(--text-tertiary); }

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.hot-table, .nb-table { width: 100%; }
.table-header {
  display: grid;
  grid-template-columns: 80px 1fr 80px 80px;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.nb-table .table-header {
  grid-template-columns: 100px 1fr 1fr 1fr;
}

.table-row {
  display: grid;
  grid-template-columns: 80px 1fr 80px 80px;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background var(--transition);
}

.table-row:hover { background: rgba(255,255,255,0.02); }

.nb-table .table-row {
  grid-template-columns: 100px 1fr 1fr 1fr;
  cursor: default;
}

.r { text-align: right; }

.sentiment-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.sentiment-item { }

.sentiment-label { font-size: 11px; color: var(--text-tertiary); margin-bottom: 4px; }
.sentiment-value { font-size: 20px; font-weight: 700; }

.sentiment-bar {
  height: 6px;
  background: var(--accent-green);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }

.sentiment-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}
</style>
