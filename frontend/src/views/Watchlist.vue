<template>
  <div class="watchlist-page fade-in">
    <header class="page-header">
      <div>
        <h1 class="page-title">自选股</h1>
        <p class="page-subtitle">关注股票实时行情</p>
      </div>
      <div class="header-actions">
        <div class="add-stock">
          <input v-model="addCode" placeholder="输入股票代码添加" @keydown.enter="addStock" />
          <button class="btn btn-primary" @click="addStock">添加</button>
        </div>
      </div>
    </header>

    <div class="card watchlist-card">
      <div class="table-header">
        <span>代码</span><span>名称</span><span>市场</span><span class="r">现价</span><span class="r">涨跌</span><span class="r">涨跌幅</span><span class="r">成交量</span><span class="c">操作</span>
      </div>
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <span>加载中...</span>
      </div>
      <div v-else-if="stocks.length === 0" class="empty-state">
        <div class="empty-icon">☆</div>
        <div class="empty-text">暂无自选股，请添加关注的股票</div>
      </div>
      <div v-else>
        <div v-for="s in stocks" :key="s.code" class="table-row">
          <span class="font-mono code" @click="goStock(s.code)">{{ s.code }}</span>
          <span class="name" @click="goStock(s.code)">{{ s.name }}</span>
          <span><span class="market-tag">{{ s.market }}</span></span>
          <span class="r font-mono" @click="goStock(s.code)">{{ s.price?.toFixed(2) || '-' }}</span>
          <span class="r font-mono" :class="s.change >= 0 ? 'text-up' : 'text-down'" @click="goStock(s.code)">
            {{ s.change >= 0 ? '+' : '' }}{{ s.change?.toFixed(2) }}
          </span>
          <span class="r font-mono" :class="s.pct >= 0 ? 'text-up' : 'text-down'" @click="goStock(s.code)">
            {{ s.pct >= 0 ? '+' : '' }}{{ s.pct?.toFixed(2) }}%
          </span>
          <span class="r font-mono" @click="goStock(s.code)">{{ fmtVol(s.volume) }}</span>
          <span class="c">
            <button class="btn btn-ghost remove-btn" @click="removeStock(s.code)">删除</button>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const stocks = ref<any[]>([])
const loading = ref(false)
const addCode = ref('')

function fmtVol(v: number) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toString()
}

function goStock(code: string) { router.push(`/stock/${code}`) }

async function loadWatchlist() {
  loading.value = true
  try {
    const list = await api.getWatchlist()
    stocks.value = list
  } catch {
    stocks.value = []
  } finally {
    loading.value = false
  }
}

async function addStock() {
  const code = addCode.value.trim()
  if (!code) return
  try {
    await api.addToWatchlist(code)
    addCode.value = ''
    await loadWatchlist()
  } catch (e: any) {
    alert(`添加失败: ${e.message}`)
  }
}

async function removeStock(code: string) {
  try {
    await api.removeFromWatchlist(code)
    await loadWatchlist()
  } catch (e: any) {
    alert(`删除失败: ${e.message}`)
  }
}

let refreshTimer: any = null

onMounted(() => {
  loadWatchlist()
  refreshTimer = setInterval(loadWatchlist, 30000)
})

onUnmounted(() => {
  clearInterval(refreshTimer)
})
</script>

<style scoped>
.watchlist-page { padding: 24px 28px; }

.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.page-subtitle { font-size: 13px; color: var(--text-tertiary); margin-top: 4px; }

.add-stock { display: flex; gap: 8px; }
.add-stock input { width: 180px; }

.watchlist-card { padding: 0; overflow: hidden; }

.table-header {
  display: grid;
  grid-template-columns: 80px 1fr 50px 80px 70px 70px 80px 60px;
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
  grid-template-columns: 80px 1fr 50px 80px 70px 70px 80px 60px;
  gap: 8px;
  padding: 10px 20px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-light);
  transition: background var(--transition);
}

.table-row:hover { background: rgba(255,255,255,0.02); }

.r { text-align: right; }
.c { text-align: center; }
.code { color: var(--accent-cyan); cursor: pointer; }
.name { cursor: pointer; }

.market-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(41,151,255,0.15);
  color: var(--accent-blue);
}

.remove-btn { padding: 2px 8px; font-size: 11px; }

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-text { font-size: 14px; color: var(--text-tertiary); }

.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 8px;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
