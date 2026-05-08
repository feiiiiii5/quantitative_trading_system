<template>
  <nav class="mobile-nav" aria-label="Mobile navigation">
    <router-link
      v-for="item in mobileItems"
      :key="item.key"
      :to="item.path"
      class="mn-item"
      :class="{ active: isActive(item.path) }"
      :aria-label="'Navigate to ' + item.label"
      :aria-current="isActive(item.path) ? 'page' : undefined"
    >
      <span class="mn-icon">
        <svg v-if="item.key === 'dashboard'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
        <svg v-else-if="item.key === 'market'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 6-10"/></svg>
        <svg v-else-if="item.key === 'strategy'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
        <svg v-else-if="item.key === 'portfolio'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 20a2 2 0 002-2V8a2 2 0 00-2-2h-7.9a2 2 0 01-1.69-.9L9.6 3.9A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>
        <svg v-else-if="item.key === 'watchlist'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/></svg>
      </span>
      <span class="mn-label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

interface MobileNavItem {
  key: string
  path: string
  label: string
}

const mobileItems: MobileNavItem[] = [
  { key: 'dashboard', path: '/dashboard', label: '仪表盘' },
  { key: 'market', path: '/market', label: '行情' },
  { key: 'strategy', path: '/strategy', label: '策略' },
  { key: 'portfolio', path: '/portfolio', label: '组合' },
  { key: 'watchlist', path: '/watchlist', label: '自选' },
]

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}
</script>

<style scoped>
.mobile-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--bg-void);
  border-top: 1px solid var(--border-hair);
  z-index: 200;
  justify-content: space-around;
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.mn-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--text-tertiary);
  flex: 1;
  height: 100%;
  position: relative;
  transition: color var(--dur-fast) var(--ease-mechanical);
}

.mn-item.active {
  color: var(--accent);
}

.mn-item.active::before {
  content: '';
  position: absolute;
  top: 0;
  left: 25%;
  right: 25%;
  height: 2px;
  background: var(--accent);
  box-shadow: 0 0 6px rgba(41, 121, 255, 0.6);
}

.mn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.mn-label {
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .mobile-nav {
    display: flex;
  }
}
</style>
