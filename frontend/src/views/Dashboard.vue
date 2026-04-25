<template>
  <div class="dashboard">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo">
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
          <path d="M4 24L12 12L20 20L28 4" stroke="url(#logo-gradient)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
          <defs>
            <linearGradient id="logo-gradient" x1="4" y1="24" x2="28" y2="4">
              <stop stop-color="#00d4aa"/>
              <stop offset="1" stop-color="#0ea5e9"/>
            </linearGradient>
          </defs>
        </svg>
        <span class="logo-text">Quant</span>
      </div>
      
      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
        >
          <component :is="iconMap[item.icon]" :size="20" />
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="status-indicator" :class="{ online: isMarketOpen }">
          <span class="status-dot"></span>
          <span class="status-text">{{ isMarketOpen ? '交易中' : '休市' }}</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main">
      <!-- Header -->
      <header class="header">
        <div class="search-wrapper">
          <IconSearch :size="18" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索股票代码 / 名称..."
            class="search-input"
            @input="handleSearch"
            @focus="showSearchResults = true"
            @keydown.enter="handleSearchEnter"
          />
          <button class="search-btn" @click="handleSearchEnter">
            <IconSearch :size="14" />
          </button>
          <div v-if="showSearchResults && searchResults.length" class="search-dropdown" v-click-outside="closeSearch">
            <div
              v-for="item in searchResults"
              :key="item.code"
              class="search-result-item"
              @click="goToStock(item.code)"
            >
              <span class="result-code">{{ item.code }}</span>
              <span class="result-name">{{ item.name }}</span>
              <span class="result-market">{{ item.market }}</span>
            </div>
          </div>
        </div>

        <div class="header-actions">
          <button class="icon-btn" @click="refreshData">
            <IconRefresh :size="18" :class="{ 'is-loading': refreshing }" />
          </button>
        </div>
      </header>

      <!-- Content -->
      <div class="content">
        <!-- Market Overview -->
        <section class="section">
          <div class="section-header">
            <h2 class="section-title">市场概览</h2>
            <span class="section-time">{{ currentTime }}</span>
          </div>
          <div class="indices-grid">
            <div
              v-for="index in marketIndices"
              :key="index.symbol"
              class="index-card"
              :class="{ up: index.pct >= 0, down: index.pct < 0 }"
            >
              <div class="index-header">
                <span class="index-name">{{ index.name }}</span>
                <span class="index-badge" :class="index.pct >= 0 ? 'bg-green' : 'bg-red'">
                  {{ index.pct >= 0 ? '+' : '' }}{{ index.pct?.toFixed(2) }}%
                </span>
              </div>
              <div class="index-value font-mono">{{ index.price?.toFixed(2) }}</div>
              <div class="index-change font-mono" :class="index.pct >= 0 ? 'text-green' : 'text-red'">
                {{ index.change >= 0 ? '+' : '' }}{{ index.change?.toFixed(2) }}
              </div>
              <div class="mini-chart">
                <svg viewBox="0 0 100 30" class="sparkline">
                  <path
                    :d="generateSparkline(index.trend || [])"
                    fill="none"
                    :stroke="index.pct >= 0 ? '#00d4aa' : '#ef4444'"
                    stroke-width="1.5"
                    stroke-linecap="round"
                  />
                </svg>
              </div>
            </div>
          </div>
        </section>

        <!-- Hot Stocks -->
        <section class="section">
          <div class="section-header">
            <h2 class="section-title">热门股票</h2>
            <router-link to="/strategy" class="section-link">
              查看全部 <IconRight :size="14" />
            </router-link>
          </div>
          <div class="stock-table-wrapper">
            <table class="stock-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>代码</th>
                  <th>名称</th>
                  <th class="text-right">最新价</th>
                  <th class="text-right">涨跌幅</th>
                  <th class="text-right">涨跌额</th>
                  <th class="text-right">成交量</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(stock, i) in hotStocks"
                  :key="stock.code"
                  class="stock-row"
                  @click="goToStock(stock.code)"
                >
                  <td>
                    <span class="rank" :class="{ top3: i < 3 }">{{ i + 1 }}</span>
                  </td>
                  <td class="font-mono">{{ stock.code }}</td>
                  <td>{{ stock.name }}</td>
                  <td class="text-right font-mono">{{ stock.price?.toFixed(2) }}</td>
                  <td class="text-right">
                    <span class="pct-badge" :class="stock.pct >= 0 ? 'up' : 'down'">
                      {{ stock.pct >= 0 ? '+' : '' }}{{ stock.pct?.toFixed(2) }}%
                    </span>
                  </td>
                  <td class="text-right font-mono" :class="stock.change >= 0 ? 'text-green' : 'text-red'">
                    {{ stock.change >= 0 ? '+' : '' }}{{ stock.change?.toFixed(2) }}
                  </td>
                  <td class="text-right font-mono">{{ formatVolume(stock.volume) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Market Sentiment -->
        <section class="section" v-if="marketSentiment">
          <div class="section-header">
            <h2 class="section-title">市场情绪</h2>
          </div>
          <div class="sentiment-grid">
            <div class="sentiment-card">
              <div class="sentiment-label">涨跌比</div>
              <div class="sentiment-value font-mono">{{ marketSentiment.up_down_ratio?.toFixed(2) }}</div>
              <div class="sentiment-bar">
                <div class="sentiment-fill" :style="{ width: `${(marketSentiment.advancers / (marketSentiment.advancers + marketSentiment.decliners || 1)) * 100}%` }"></div>
              </div>
            </div>
            <div class="sentiment-card">
              <div class="sentiment-label">上涨家数</div>
              <div class="sentiment-value text-green font-mono">{{ marketSentiment.advancers }}</div>
            </div>
            <div class="sentiment-card">
              <div class="sentiment-label">下跌家数</div>
              <div class="sentiment-value text-red font-mono">{{ marketSentiment.decliners }}</div>
            </div>
            <div class="sentiment-card">
              <div class="sentiment-label">成交额</div>
              <div class="sentiment-value font-mono">{{ formatVolume(marketSentiment.turnover_amount) }}</div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { apiGet } from '../api'
import { IconSearch, IconRefresh, IconRight, IconHome, IconBarChart, IconThunderbolt, IconDashboard } from '@arco-design/web-vue/es/icon'

const router = useRouter()
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const showSearchResults = ref(false)
const hotStocks = ref<any[]>([])
const marketIndices = ref<any[]>([])
const marketSentiment = ref<any>(null)
const refreshing = ref(false)
const currentTime = ref('')
let searchTimer: any = null
let timeTimer: any = null

const navItems = [
  { path: '/dashboard', icon: 'IconHome', label: '首页' },
  { path: '/backtest', icon: 'IconBarChart', label: '回测' },
  { path: '/strategy', icon: 'IconThunderbolt', label: '策略' },
  { path: '/portfolio', icon: 'IconDashboard', label: '组合' },
]

const iconMap: Record<string, any> = { IconHome, IconBarChart, IconThunderbolt, IconDashboard }

const isMarketOpen = computed(() => {
  const now = new Date()
  const hour = now.getHours()
  const minute = now.getMinutes()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  return (hour === 9 && minute >= 30) || (hour === 10) || (hour === 11 && minute <= 30) || (hour >= 13 && hour < 15)
})

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const handleSearch = () => {
  clearTimeout(searchTimer)
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  searchTimer = setTimeout(async () => {
    const data = await apiGet<any[]>(`/search?q=${encodeURIComponent(searchQuery.value)}&limit=8`)
    searchResults.value = Array.isArray(data) ? data : []
  }, 300)
}

const closeSearch = () => {
  showSearchResults.value = false
}

const goToStock = (symbol: string) => {
  searchQuery.value = ''
  searchResults.value = []
  showSearchResults.value = false
  router.push(`/stock/${symbol}`)
}

const handleSearchEnter = async () => {
  const query = searchQuery.value.trim()
  if (!query) return

  if (searchResults.value.length > 0) {
    goToStock(searchResults.value[0].code)
    return
  }

  const data = await apiGet<any[]>(`/search?q=${encodeURIComponent(query)}&limit=1`)
  const results = Array.isArray(data) ? data : []
  if (results.length > 0) {
    goToStock(results[0].code)
  } else {
    goToStock(query)
  }
}

const formatVolume = (v: number) => {
  if (!v) return '--'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(2) + '万'
  return v.toString()
}

const generateSparkline = (data: number[]) => {
  if (!data || data.length < 2) return ''
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * 100
    const y = 30 - ((v - min) / range) * 30
    return `${x},${y}`
  })
  return `M ${points.join(' L ')}`
}

const refreshData = async () => {
  refreshing.value = true
  await loadData()
  setTimeout(() => refreshing.value = false, 500)
}

const loadData = async () => {
  try {
    const [hotData, overview] = await Promise.all([
      apiGet<any[]>('/hot-stocks?limit=20'),
      apiGet<any>('/market-overview')
    ])
    hotStocks.value = (Array.isArray(hotData) ? hotData : []).map((s: any, i: number) => ({ ...s, rank: i + 1 }))
    if (overview && typeof overview === 'object') {
      marketIndices.value = overview.indices || []
      marketSentiment.value = overview.temperature || null
    }
  } catch (e) {
    console.error('加载数据失败', e)
  }
}

onMounted(() => {
  loadData()
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timeTimer)
  clearTimeout(searchTimer)
})

const vClickOutside = {
  mounted(el: any, binding: any) {
    el._clickOutside = (e: Event) => {
      if (!el.contains(e.target)) binding.value()
    }
    document.addEventListener('click', el._clickOutside)
  },
  unmounted(el: any) {
    document.removeEventListener('click', el._clickOutside)
  }
}
</script>

<style scoped>
.dashboard {
  display: flex;
  height: 100vh;
  background: var(--bg-primary);
}

/* Sidebar */
.sidebar {
  width: 200px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 30px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s;
  font-size: 14px;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(14, 165, 233, 0.15));
  color: var(--accent-primary);
  border: 1px solid rgba(0, 212, 170, 0.2);
}

.nav-label {
  font-weight: 500;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid var(--border-color);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-indicator.online .status-dot {
  background: var(--accent-primary);
  box-shadow: 0 0 8px rgba(0, 212, 170, 0.5);
  animation: pulse-glow 2s infinite;
}

.status-indicator.online {
  color: var(--accent-primary);
}

/* Main */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 64px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  gap: 16px;
}

.search-wrapper {
  position: relative;
  width: 400px;
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  z-index: 1;
}

.search-input {
  width: 100%;
  height: 40px;
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 0 40px 0 42px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--accent-primary);
  background: var(--bg-secondary);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-primary);
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 2;
}

.search-btn:hover {
  background: #00b894;
  transform: translateY(-50%) scale(1.05);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 100;
  max-height: 320px;
  overflow-y: auto;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.search-result-item:hover {
  background: var(--bg-tertiary);
}

.result-code {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 600;
  color: var(--accent-primary);
  min-width: 70px;
}

.result-name {
  flex: 1;
  color: var(--text-primary);
}

.result-market {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.icon-btn .is-loading {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Content */
.content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-time {
  font-size: 13px;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', monospace;
}

.section-link {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--accent-primary);
  text-decoration: none;
  transition: opacity 0.2s;
}

.section-link:hover {
  opacity: 0.8;
}

/* Indices Grid */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.index-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
}

.index-card:hover {
  border-color: var(--bg-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.index-card.up {
  border-left: 3px solid var(--accent-primary);
}

.index-card.down {
  border-left: 3px solid var(--accent-danger);
}

.index-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.index-name {
  font-size: 14px;
  color: var(--text-secondary);
}

.index-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}

.bg-green {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.bg-red {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.index-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.index-change {
  font-size: 14px;
  margin-bottom: 12px;
}

.text-green {
  color: var(--accent-primary);
}

.text-red {
  color: var(--accent-danger);
}

.mini-chart {
  height: 30px;
  opacity: 0.6;
}

.sparkline {
  width: 100%;
  height: 100%;
}

/* Stock Table */
.stock-table-wrapper {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.stock-table th {
  text-align: left;
  padding: 14px 20px;
  font-weight: 500;
  color: var(--text-muted);
  font-size: 13px;
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.stock-table td {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  transition: background 0.15s;
}

.stock-row {
  cursor: pointer;
}

.stock-row:hover td {
  background: var(--bg-tertiary);
}

.stock-row:last-child td {
  border-bottom: none;
}

.rank {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.rank.top3 {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: white;
}

.pct-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
}

.pct-badge.up {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.pct-badge.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--accent-danger);
}

.text-right {
  text-align: right;
}

/* Sentiment */
.sentiment-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.sentiment-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.sentiment-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.sentiment-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.sentiment-bar {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
}

.sentiment-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* Responsive */
@media (max-width: 1200px) {
  .indices-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .sentiment-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .sidebar {
    width: 64px;
  }
  .logo-text, .nav-label, .status-text {
    display: none;
  }
  .nav-item {
    justify-content: center;
    padding: 12px;
  }
  .indices-grid, .sentiment-grid {
    grid-template-columns: 1fr;
  }
}
</style>
