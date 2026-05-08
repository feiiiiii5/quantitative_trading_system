<template>
  <aside
    class="sidebar"
    :class="{ expanded: isExpanded }"
    aria-label="Main navigation"
  >
    <div class="sidebar-brand">
      <span class="brand-short terminal-glow">QC</span>
      <transition name="label-fade">
        <span v-if="isExpanded" class="brand-full">QuantCore</span>
      </transition>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
        :aria-label="'Navigate to ' + item.label"
        :aria-current="isActive(item.path) ? 'page' : undefined"
      >
        <span v-if="isActive(item.path)" class="active-line" />
        <span class="nav-icon">
          <svg v-if="item.key === 'dashboard'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          <svg v-else-if="item.key === 'market'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 6-10"/></svg>
          <svg v-else-if="item.key === 'stock'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 10l3 3 4-6 4 4"/></svg>
          <svg v-else-if="item.key === 'strategy'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
          <svg v-else-if="item.key === 'portfolio'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 20a2 2 0 002-2V8a2 2 0 00-2-2h-7.9a2 2 0 01-1.69-.9L9.6 3.9A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>
          <svg v-else-if="item.key === 'watchlist'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>
          <svg v-else-if="item.key === 'chip'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18M9 3v18M15 3v18"/></svg>
          <svg v-else-if="item.key === 'moneyflow'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
          <svg v-else-if="item.key === 'sector'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/><path d="M2 12h20"/></svg>
          <svg v-else-if="item.key === 'news'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 22h16a2 2 0 002-2V4a2 2 0 00-2-2H8a2 2 0 00-2 2v16a2 2 0 01-2 2zm0 0a2 2 0 01-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/></svg>
          <svg v-else-if="item.key === 'screener'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z"/></svg>
          <svg v-else-if="item.key === 'alerts'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
          <svg v-else-if="item.key === 'optimizer'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
          <svg v-else-if="item.key === 'factorlab'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><rect x="5" y="10" width="3" height="8" rx="0.5"/><rect x="10" y="6" width="3" height="12" rx="0.5"/><rect x="15" y="8" width="3" height="10" rx="0.5"/></svg>
          <svg v-else-if="item.key === 'tca'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/><circle cx="12" cy="12" r="7"/></svg>
          <svg v-else-if="item.key === 'ml'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/><circle cx="12" cy="12" r="2"/><line x1="8" y1="6" x2="10" y2="12"/><line x1="14" y1="12" x2="16" y2="6"/><line x1="8" y1="18" x2="10" y2="12"/><line x1="14" y1="12" x2="16" y2="18"/></svg>
        </span>
        <transition name="label-fade">
          <span v-if="isExpanded" class="nav-label">{{ item.label }}</span>
        </transition>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <transition name="label-fade">
        <span v-if="isExpanded" class="clock-text">{{ currentTime }}</span>
      </transition>
      <button
        class="toggle-btn"
        :aria-label="isExpanded ? 'Collapse sidebar' : 'Expand sidebar'"
        @click="toggleExpand"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          :class="{ rotated: isExpanded }"
          class="toggle-icon"
        >
          <path d="M9 18l6-6-6-6" />
        </svg>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const isExpanded = ref(false)
const currentTime = ref('00:00:00')

const emit = defineEmits<{
  (e: 'collapse-change', collapsed: boolean): void
}>()

interface NavItem {
  key: string
  path: string
  label: string
}

const navItems: NavItem[] = [
  { key: 'dashboard', path: '/dashboard', label: '仪表盘' },
  { key: 'market', path: '/market', label: '行情' },
  { key: 'stock', path: '/stock', label: '个股' },
  { key: 'strategy', path: '/strategy', label: '策略' },
  { key: 'portfolio', path: '/portfolio', label: '组合' },
  { key: 'watchlist', path: '/watchlist', label: '自选' },
  { key: 'chip', path: '/chip', label: '筹码' },
  { key: 'moneyflow', path: '/moneyflow', label: '资金' },
  { key: 'sector', path: '/sector', label: '板块' },
  { key: 'news', path: '/news', label: '资讯' },
  { key: 'screener', path: '/screener', label: '选股' },
  { key: 'alerts', path: '/alerts', label: '提醒' },
  { key: 'optimizer', path: '/optimizer', label: '优化' },
  { key: 'factorlab', path: '/factor-lab', label: '因子' },
  { key: 'tca', path: '/tca', label: 'TCA' },
  { key: 'ml', path: '/ml', label: 'ML' },
]

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}

function toggleExpand(): void {
  isExpanded.value = !isExpanded.value
}

watch(isExpanded, (val: boolean) => {
  emit('collapse-change', !val)
})

const CLOCK_TICK_MS = 1_000

function updateTime(): void {
  const now = new Date()
  currentTime.value = [now.getHours(), now.getMinutes(), now.getSeconds()]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')
}

let timer: ReturnType<typeof setInterval>

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, CLOCK_TICK_MS)
})

onUnmounted(() => {
  clearInterval(timer)
})
</script>

<style scoped>
.sidebar {
  --sidebar-collapsed: 52px;
  --sidebar-expanded: 200px;

  width: var(--sidebar-collapsed);
  height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
  flex-shrink: 0;
  overflow: hidden;
  will-change: width;
  transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 0;
  border-right: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  background-color: var(--bg-void, #0a0e17);
  background-image: linear-gradient(
    180deg,
    rgba(41, 121, 255, 0.06) 0%,
    rgba(41, 121, 255, 0.02) 40%,
    transparent 100%
  );
}

.sidebar.expanded {
  width: var(--sidebar-expanded);
}

.sidebar-brand {
  height: 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border-bottom: 1px solid var(--border-hair, rgba(255, 255, 255, 0.04));
  flex-shrink: 0;
  white-space: nowrap;
  overflow: hidden;
}

.brand-short {
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  font-weight: 700;
  font-size: 16px;
  color: var(--signal-teal, #1de9b6);
  letter-spacing: 0.08em;
  flex-shrink: 0;
}

.terminal-glow {
  text-shadow:
    0 0 4px rgba(29, 233, 182, 0.8),
    0 0 11px rgba(29, 233, 182, 0.5),
    0 0 22px rgba(29, 233, 182, 0.3),
    0 0 44px rgba(29, 233, 182, 0.15);
}

.brand-full {
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  font-weight: 700;
  font-size: 13px;
  color: var(--text-primary, #e0e0e0);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  padding: 6px 0;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 17px;
  height: 38px;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.38));
  text-decoration: none;
  border-radius: 0;
  transition: color 0.15s ease, background 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item::after {
  content: '';
  position: absolute;
  left: 17px;
  right: 17px;
  bottom: 0;
  height: 1px;
  background: var(--accent, #2979ff);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-item:hover {
  color: var(--text-secondary, rgba(255, 255, 255, 0.7));
  background: rgba(41, 121, 255, 0.06);
}

.nav-item:hover::after {
  transform: scaleX(1);
}

.nav-item.active {
  color: var(--accent, #2979ff);
  background: rgba(41, 121, 255, 0.1);
}

.nav-item.active::after {
  transform: scaleX(0);
}

.active-line {
  position: absolute;
  left: 0;
  top: 0;
  width: 2px;
  height: 100%;
  border-radius: 0;
  background: var(--accent, #2979ff);
  animation: activeLineScan 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  box-shadow:
    0 0 6px rgba(41, 121, 255, 0.6),
    0 0 12px rgba(41, 121, 255, 0.3);
}

@keyframes activeLineScan {
  0% {
    clip-path: inset(0 0 100% 0);
  }
  100% {
    clip-path: inset(0 0 0 0);
  }
}

.nav-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-icon svg {
  width: 18px;
  height: 18px;
}

.nav-label {
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  font-size: 11px;
  font-weight: 500;
  color: inherit;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

.sidebar-footer {
  padding: 8px 10px;
  border-top: 1px solid var(--border-hair, rgba(255, 255, 255, 0.04));
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 40px;
}

.clock-text {
  font-family: var(--font-mono, 'JetBrains Mono', 'Fira Code', monospace);
  font-size: 11px;
  color: var(--text-muted, rgba(255, 255, 255, 0.3));
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.06em;
}

.toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--border-dim, rgba(255, 255, 255, 0.06));
  border-radius: 0;
  background: transparent;
  color: var(--text-tertiary, rgba(255, 255, 255, 0.38));
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  flex-shrink: 0;
}

.toggle-btn:hover {
  color: var(--text-secondary, rgba(255, 255, 255, 0.7));
  border-color: var(--accent, #2979ff);
  background: rgba(41, 121, 255, 0.08);
}

.toggle-icon {
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.toggle-icon.rotated {
  transform: rotate(180deg);
}

.label-fade-enter-active,
.label-fade-leave-active {
  transition: opacity 0.15s ease;
}

.label-fade-enter-from,
.label-fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
}
</style>
