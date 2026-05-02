<template>
  <div class="shell">
    <aside class="sidebar" :class="{ expanded }" @mouseenter="expanded = true" @mouseleave="expanded = false">
      <div class="sidebar-brand">
        <div class="brand-icon">Q</div>
        <transition name="fade">
          <span v-if="expanded" class="brand-text">QuantCore</span>
        </transition>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <div class="nav-icon" v-html="item.icon" />
          <transition name="fade">
            <span v-if="expanded" class="nav-label">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="nav-item clock-item">
          <div class="nav-icon clock-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
          </div>
          <transition name="fade">
            <span v-if="expanded" class="nav-label mono">{{ currentTime }}</span>
          </transition>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <div class="market-status" v-if="marketStatus">
            <span
              v-for="(s, key) in marketStatus"
              :key="key"
              class="status-badge"
              :class="s.is_open ? 'open' : 'closed'"
            >
              <span class="status-dot" />
              {{ key === 'A' ? 'A股' : key === 'HK' ? '港股' : '美股' }}
            </span>
          </div>
        </div>

        <div class="topbar-center">
          <div class="search-box" @click="showSearch = true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            </svg>
            <span>搜索股票代码/名称...</span>
            <kbd>⌘K</kbd>
          </div>
        </div>

        <div class="topbar-right">
          <button class="theme-toggle" @click="themeStore.toggleTheme()" :title="themeStore.theme === 'dark' ? '切换亮色模式' : '切换暗色模式'">
            <svg v-if="themeStore.theme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </button>
          <div class="index-tickers" v-if="cnIndices.length">
            <span v-for="idx in cnIndices.slice(0, 3)" :key="idx.code" class="ticker mono">
              {{ idx.name }}
              <span :class="idx.change_pct >= 0 ? 'text-rise' : 'text-fall'">
                {{ idx.change_pct >= 0 ? '+' : '' }}{{ idx.change_pct?.toFixed(2) }}%
              </span>
            </span>
          </div>
        </div>
      </header>

      <main class="content">
        <slot />
      </main>
    </div>

    <teleport to="body">
      <transition name="fade">
        <div v-if="showSearch" class="search-overlay" @click.self="showSearch = false">
          <div class="search-modal">
            <div class="search-input-wrap">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
              </svg>
              <input
                ref="searchInput"
                v-model="searchQuery"
                placeholder="输入股票代码或名称..."
                @input="onSearch"
              />
              <kbd @click="showSearch = false">ESC</kbd>
            </div>
            <div class="search-results" v-if="searchResults.length">
              <div
                v-for="item in searchResults"
                :key="item.symbol"
                class="search-item"
                @click="goToStock(item.symbol)"
              >
                <span class="search-code mono">{{ item.code }}</span>
                <span class="search-name">{{ item.name }}</span>
                <span class="search-market">{{ item.market }}</span>
              </div>
            </div>
            <div v-else-if="searchQuery" class="search-empty">未找到相关股票</div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { api } from '@/api'
import { useThemeStore } from '@/stores/theme'
import type { MarketStatus, SearchItem } from '@/types'
import { debounce } from '@/utils/format'

const router = useRouter()
const route = useRoute()
const themeStore = useThemeStore()

const expanded = ref(false)
const currentTime = ref('')
const showSearch = ref(false)
const searchQuery = ref('')
const searchResults = ref<SearchItem[]>([])
const searchInput = ref<HTMLInputElement>()
const marketStatus = ref<Record<string, MarketStatus> | null>(null)
const cnIndices = ref<{ code: string; name: string; change_pct: number }[]>([])

const navItems = [
  {
    path: '/dashboard',
    label: '仪表盘',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
  },
  {
    path: '/market',
    label: '行情',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 6-10"/></svg>',
  },
  {
    path: '/strategy',
    label: '策略',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
  },
  {
    path: '/portfolio',
    label: '组合',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 6v12M6 12h12"/></svg>',
  },
  {
    path: '/watchlist',
    label: '自选',
    icon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>',
  },
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

function updateTime() {
  const now = new Date()
  currentTime.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
}

const onSearch = debounce(async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = []
    return
  }
  try {
    searchResults.value = await api.search.stocks(searchQuery.value.trim(), 8)
  } catch {
    searchResults.value = []
  }
}, 300)

function goToStock(symbol: string) {
  showSearch.value = false
  searchQuery.value = ''
  searchResults.value = []
  router.push(`/stock/${symbol}`)
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showSearch.value = true
    setTimeout(() => searchInput.value?.focus(), 100)
  }
  if (e.key === 'Escape') {
    showSearch.value = false
  }
}

async function fetchStatus() {
  try {
    marketStatus.value = await api.market.status()
    const overview = await api.market.overview()
    cnIndices.value = Object.entries(overview.cn_indices).map(([code, d]) => ({
      code,
      name: d.name,
      change_pct: d.change_pct,
    }))
  } catch {
    // silent
  }
}

let timer: ReturnType<typeof setInterval>
let statusTimer: ReturnType<typeof setInterval>

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  statusTimer = setInterval(fetchStatus, 30000)
  fetchStatus()
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  clearInterval(timer)
  clearInterval(statusTimer)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  transition: width var(--duration-slow) var(--ease-out);
  z-index: 100;
  flex-shrink: 0;
}

.sidebar.expanded {
  width: var(--sidebar-expanded);
}

.sidebar-brand {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--border);
}

.brand-icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--bg-gradient-accent);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: var(--text-md);
  flex-shrink: 0;
  box-shadow: var(--glow-accent);
}

.brand-text {
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-nav {
  flex: 1;
  padding: var(--space-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  white-space: nowrap;
  overflow: hidden;
  text-decoration: none;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.nav-item.active {
  background: var(--accent-muted);
  color: var(--accent);
  box-shadow: inset 0 -2px 0 var(--accent);
}

.nav-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-label {
  font-size: var(--text-sm);
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-footer {
  padding: var(--space-2);
  border-top: 1px solid var(--border);
}

.clock-item {
  cursor: default;
}

.clock-icon {
  color: var(--text-tertiary);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: var(--topbar-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 var(--space-4);
  gap: var(--space-4);
  flex-shrink: 0;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.market-status {
  display: flex;
  gap: var(--space-2);
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--bg-elevated);
}

.status-badge.open {
  color: var(--fall);
}

.status-badge.closed {
  color: var(--text-tertiary);
}

.status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.status-badge.open .status-dot {
  animation: pulse 2s ease-in-out infinite;
}

.topbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  min-width: 260px;
}

.search-box:hover {
  border-color: var(--border-hover);
  box-shadow: var(--glow-accent);
}

.search-box kbd {
  font-size: 10px;
  padding: 1px 5px;
  background: var(--bg-overlay);
  border-radius: 3px;
  font-family: var(--font-mono);
  margin-left: auto;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}
.theme-toggle:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
  background: var(--bg-hover);
}

.index-tickers {
  display: flex;
  gap: var(--space-4);
}

.ticker {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  display: flex;
  gap: 4px;
}

.content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--space-4);
}

.search-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  backdrop-filter: blur(4px);
}

.search-modal {
  width: 520px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: slideDown var(--duration-normal) var(--ease-out);
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.search-input-wrap input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: var(--text-md);
  font-family: var(--font-sans);
}

.search-input-wrap input::placeholder {
  color: var(--text-tertiary);
}

.search-input-wrap kbd {
  font-size: 10px;
  padding: 2px 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
  font-family: var(--font-mono);
  color: var(--text-tertiary);
  cursor: pointer;
}

.search-results {
  max-height: 360px;
  overflow-y: auto;
}

.search-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.search-item:hover {
  background: var(--bg-hover);
}

.search-code {
  font-size: var(--text-sm);
  color: var(--accent);
  min-width: 60px;
}

.search-name {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
}

.search-market {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  padding: 1px 6px;
  background: var(--bg-elevated);
  border-radius: 3px;
}

.search-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-sm);
}
</style>
