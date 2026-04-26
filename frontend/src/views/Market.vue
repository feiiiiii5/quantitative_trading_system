<template>
  <div class="market-page fade-in">
    <header class="page-header">
      <div>
        <h1 class="page-title">市场浏览</h1>
        <p class="page-subtitle">全市场股票实时行情</p>
      </div>
    </header>

    <div class="toolbar">
      <div class="market-tabs">
        <button v-for="m in markets" :key="m.value" class="tab" :class="{ active: currentMarket === m.value }" @click="switchMarket(m.value)">{{ m.label }}</button>
      </div>
      <div class="toolbar-right">
        <input v-model="searchText" placeholder="搜索..." class="search-input" @input="onSearchChange" />
        <select v-model="sortBy" @change="loadData">
          <option value="pct">涨跌幅</option>
          <option value="price">价格</option>
          <option value="volume">成交量</option>
          <option value="amount">成交额</option>
          <option value="mktcap">市值</option>
          <option value="turnoverratio">换手率</option>
        </select>
        <button class="btn btn-ghost" @click="toggleSort">
          {{ sortAsc ? '↑ 升序' : '↓ 降序' }}
        </button>
      </div>
    </div>

    <div class="stock-table card">
      <div class="table-header">
        <span>代码</span><span>名称</span><span class="r">现价</span><span class="r">涨跌</span><span class="r">涨跌幅</span><span class="r">成交量</span><span class="r">成交额</span>
      </div>
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      <div v-else-if="stocks.length === 0" class="empty-state">暂无数据</div>
      <div v-else>
        <div v-for="s in stocks" :key="s.code" class="table-row" @click="goStock(s.code)">
          <span class="font-mono code">{{ s.code }}</span>
          <span class="name">{{ s.name }}</span>
          <span class="r font-mono">{{ s.price?.toFixed(2) || '-' }}</span>
          <span class="r font-mono" :class="s.change >= 0 ? 'text-up' : 'text-down'">{{ s.change >= 0 ? '+' : '' }}{{ s.change?.toFixed(2) }}</span>
          <span class="r font-mono" :class="s.pct >= 0 ? 'text-up' : 'text-down'">{{ s.pct >= 0 ? '+' : '' }}{{ s.pct?.toFixed(2) }}%</span>
          <span class="r font-mono">{{ fmtVol(s.volume) }}</span>
          <span class="r font-mono">{{ fmtAmt(s.amount || s.turnover) }}</span>
        </div>
      </div>
    </div>

    <div class="pagination" v-if="totalPages > 1">
      <button class="btn btn-ghost" :disabled="page <= 1" @click="page--; loadData()">上一页</button>
      <span class="page-info font-mono">{{ page }} / {{ totalPages }}</span>
      <button class="btn btn-ghost" :disabled="page >= totalPages" @click="page++; loadData()">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const markets = [
  { value: 'A', label: '沪深A股' },
  { value: 'HK', label: '港股' },
  { value: 'US', label: '美股' },
]

const currentMarket = ref('A')
const searchText = ref('')
const sortBy = ref('pct')
const sortAsc = ref(false)
const page = ref(1)
const pageSize = 50
const total = ref(0)
const totalPages = ref(1)
const stocks = ref<any[]>([])
const loading = ref(false)

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

function goStock(code: string) { router.push(`/stock/${code}`) }

function switchMarket(m: string) {
  currentMarket.value = m
  page.value = 1
  loadData()
}

function toggleSort() {
  sortAsc.value = !sortAsc.value
  loadData()
}

let searchTimer: any = null
function onSearchChange() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { page.value = 1; loadData() }, 400)
}

async function loadData() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      market: currentMarket.value,
      page: page.value,
      page_size: pageSize,
      sort: sortBy.value,
      asc: sortAsc.value,
    }
    if (searchText.value.trim()) params.search = searchText.value.trim()
    const data = await api.getMarketList(params)
    stocks.value = data.stocks || []
    total.value = data.total || 0
    totalPages.value = data.pages || 1
  } catch {
    stocks.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.market-page { padding: 24px 28px; }

.page-header { margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
}

.market-tabs { display: flex; gap: 4px; }

.tab {
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--transition);
  font-family: var(--font-sans);
}

.tab:hover { background: rgba(255,255,255,0.05); }
.tab.active { background: rgba(41,151,255,0.12); color: var(--accent-blue); border-color: rgba(41,151,255,0.3); }

.toolbar-right { display: flex; gap: 8px; align-items: center; }
.search-input { width: 160px; }

.stock-table { padding: 0; overflow: hidden; }

.table-header {
  display: grid;
  grid-template-columns: 80px 1fr 80px 70px 70px 80px 80px;
  gap: 8px;
  padding: 12px 20px;
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-color);
}

.table-row {
  display: grid;
  grid-template-columns: 80px 1fr 80px 70px 70px 80px 80px;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
  cursor: pointer;
  transition: background var(--transition);
}

.table-row:hover { background: rgba(255,255,255,0.02); }

.r { text-align: right; }
.code { color: var(--accent-cyan); }
.name { color: var(--text-primary); }

.loading-state, .empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: var(--text-tertiary);
  font-size: 14px;
}

.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}

.page-info { font-size: 13px; color: var(--text-secondary); }
</style>
