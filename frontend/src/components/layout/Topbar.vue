<template>
  <header class="topbar" role="banner" aria-label="Top bar">
    <div class="topbar-left">
      <nav class="breadcrumb" aria-label="Breadcrumb">
        <span class="breadcrumb-segment">QUANT</span>
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-current">{{ pageTitle }}</span>
      </nav>
    </div>

    <div class="topbar-center">
      <button
        class="search-trigger"
        aria-label="Search stocks"
        @click="showSearch = true"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </button>
    </div>

    <div class="topbar-right">
      <div class="market-status" aria-live="polite">
        <template v-for="item in marketStatusList" :key="item.key">
          <span
            class="status-dot"
            :class="item.isOpen ? 'open' : 'closed'"
            :title="item.label + (item.isOpen ? ' 开盘中' : ' 休市')"
          />
        </template>
      </div>

      <button class="theme-toggle" aria-label="Toggle theme" @click="themeStore.toggle()">
        <svg v-if="themeStore.theme === 'dark'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
        <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
      </button>

      <button class="locale-toggle" :aria-label="'Switch language: ' + localeLabel(nextLocale)" @click="toggleLocale">
        {{ localeCode(currentLocale) }}
      </button>

      <div class="user-dropdown" :class="{ open: userMenuOpen }">
        <button class="user-trigger" aria-label="User menu" @click="userMenuOpen = !userMenuOpen">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <svg class="chevron" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div v-if="userMenuOpen" class="user-menu" @click="userMenuOpen = false">
          <button class="user-menu-item" @click="handleLogout">LOGOUT</button>
        </div>
      </div>
    </div>

    <SearchModal v-if="showSearch" @close="showSearch = false" />
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api'
import type { MarketStatus } from '@/types'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { createLogger } from '@/composables/useLogger'
import { usePageTitle } from '@/composables/usePageTitle'
import { useLocale } from '@/composables/useLocale'
import SearchModal from '@/components/ui/SearchModal.vue'

const log = createLogger('Topbar')
const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const authStore = useAuthStore()
const { currentLocale, setLocale, localeLabel, supportedLocales } = useLocale()
const showSearch = ref(false)
const userMenuOpen = ref(false)

function localeCode(loc: string): string {
  return loc === 'zh-CN' ? '中' : 'EN'
}

const nextLocale = computed(() => {
  const idx = supportedLocales.indexOf(currentLocale.value)
  return supportedLocales[(idx + 1) % supportedLocales.length]
})

function toggleLocale(): void {
  setLocale(nextLocale.value)
}

const marketStatus = ref<Record<string, MarketStatus> | null>(null)

const { title: pageTitle } = usePageTitle()

const marketStatusList = computed(() => {
  if (!marketStatus.value) return []
  const labelMap: Record<string, string> = { A: 'A股', HK: '港股', US: '美股' }
  return Object.entries(marketStatus.value).map(([key, status]) => ({
    key,
    label: labelMap[key] ?? key,
    isOpen: status.is_open,
    time: status.is_open
      ? (status.current_time?.split(' ').pop()?.slice(0, 5) ?? '')
      : '休市',
  }))
})

const POLL_INTERVAL_MS = 30_000

async function fetchStatus() {
  try {
    const status = await api.market.status()
    marketStatus.value = status
  } catch (err) { log.warn('Fetch status failed', err) }
}

function onKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showSearch.value = true
  }
}

function handleLogout() {
  authStore.logout()
  router.push({ name: 'Login' })
}

function onDocClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('.user-dropdown')) {
    userMenuOpen.value = false
  }
}

let timer: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  fetchStatus()
  timer = setInterval(fetchStatus, POLL_INTERVAL_MS)
  window.addEventListener('keydown', onKeydown)
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  if (timer !== undefined) clearInterval(timer)
  window.removeEventListener('keydown', onKeydown)
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.topbar {
  height: var(--topbar-height);
  display: flex;
  align-items: center;
  padding: 0 var(--u4);
  gap: 0;
  flex-shrink: 0;
  background: var(--bg-void);
  border-bottom: 1px solid var(--border-hair);
  position: relative;
  z-index: 90;
}

.topbar-left {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-variant: all-small-caps;
  letter-spacing: 0.06em;
  white-space: nowrap;
  overflow: hidden;
}

.breadcrumb-segment {
  color: var(--text-tertiary);
}

.breadcrumb-sep {
  color: var(--text-muted);
}

.breadcrumb-current {
  color: var(--text-secondary);
  font-weight: 500;
}

.topbar-center {
  display: flex;
  justify-content: center;
  flex-shrink: 0;
}

.search-trigger {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-dim);
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical),
              border-color var(--dur-fast) var(--ease-mechanical);
}

.search-trigger:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
  border-color: var(--border-mid);
}

.search-trigger:active {
  border-color: var(--accent);
}

.topbar-right {
  display: flex;
  align-items: center;
  flex: 1;
  justify-content: flex-end;
  gap: var(--u2);
}

.market-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
}

.status-dot.open {
  background: var(--rise);
  animation: statusPulse 2s ease-in-out infinite;
}

.status-dot.closed {
  background: var(--text-muted);
}

.theme-toggle {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-dim);
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.theme-toggle:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
}

.locale-toggle {
  height: 32px;
  display: flex;
  align-items: center;
  padding: 0 var(--u2);
  border: 1px solid var(--border-dim);
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-variant: all-small-caps;
  letter-spacing: 0.06em;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical),
              border-color var(--dur-fast) var(--ease-mechanical);
}

.locale-toggle:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
  border-color: var(--border-mid);
}

.user-dropdown {
  position: relative;
}

.user-trigger {
  height: 32px;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 var(--u2);
  border: 1px solid var(--border-dim);
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-variant: all-small-caps;
  letter-spacing: 0.06em;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical),
              border-color var(--dur-fast) var(--ease-mechanical);
}

.user-trigger:hover {
  background: var(--bg-raised);
  color: var(--text-primary);
  border-color: var(--border-mid);
}

.user-trigger .chevron {
  transition: transform var(--dur-fast) var(--ease-mechanical);
}

.user-dropdown.open .user-trigger .chevron {
  transform: rotate(180deg);
}

.user-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 120px;
  background: var(--bg-surface);
  border: 1px solid var(--border-mid);
  border-radius: 0;
  z-index: 100;
}

.user-menu-item {
  display: block;
  width: 100%;
  padding: var(--u2) var(--u3);
  font-family: var(--font-mono);
  font-size: var(--fs-xs);
  font-variant: all-small-caps;
  letter-spacing: 0.06em;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: 0;
  cursor: pointer;
  text-align: left;
  transition: background var(--dur-fast) var(--ease-mechanical),
              color var(--dur-fast) var(--ease-mechanical);
}

.user-menu-item:hover {
  background: var(--bg-overlay);
  color: var(--text-primary);
}
</style>
