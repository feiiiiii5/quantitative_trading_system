<template>
  <div class="app-container" :data-theme="currentTheme">
    <nav class="app-nav">
      <div class="nav-brand">
        <span class="brand-icon">◈</span>
        <span class="brand-text">QuantCore</span>
      </div>
      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
          仪表盘
        </router-link>
        <router-link to="/market" class="nav-link" :class="{ active: $route.path === '/market' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 9l-5 5-2-2-4 4"/></svg>
          市场
        </router-link>
        <router-link to="/strategy-intro" class="nav-link" :class="{ active: $route.path === '/strategy-intro' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          策略
        </router-link>
        <router-link to="/strategy" class="nav-link" :class="{ active: $route.path === '/strategy' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
          回测
        </router-link>
        <router-link to="/portfolio" class="nav-link" :class="{ active: $route.path === '/portfolio' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 20a2 2 0 002-2V8a2 2 0 00-2-2h-7.9a2 2 0 01-1.69-.9L9.6 3.9A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>
          组合
        </router-link>
        <router-link to="/watchlist" class="nav-link" :class="{ active: $route.path === '/watchlist' }">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
          自选
        </router-link>
      </div>
      <div class="nav-actions">
        <button class="theme-toggle" @click="toggleTheme" :title="currentTheme === 'dark' ? '切换亮色' : '切换暗色'">
          <svg v-if="currentTheme === 'dark'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
        </button>
      </div>
    </nav>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useTheme } from './composables/useTheme'

const { currentTheme, toggleTheme } = useTheme()
</script>

<style>
@import './styles/theme.css';

.app-container { min-height: 100vh; display: flex; flex-direction: column; }
.app-nav {
  display: flex; align-items: center; height: 48px; padding: 0 20px;
  background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);
  position: sticky; top: 0; z-index: 100;
}
.nav-brand { display: flex; align-items: center; gap: 8px; margin-right: 32px; }
.brand-icon { font-size: 18px; color: var(--accent-cyan); }
.brand-text { font-size: 15px; font-weight: 700; color: var(--text-primary); letter-spacing: 0.5px; }
.nav-links { display: flex; gap: 2px; flex: 1; }
.nav-link {
  display: flex; align-items: center; gap: 5px; padding: 6px 14px;
  font-size: 13px; color: var(--text-secondary); border-radius: var(--radius-sm);
  transition: all var(--transition); text-decoration: none;
}
.nav-link:hover { color: var(--text-primary); background: var(--bg-hover); }
.nav-link.active { color: var(--accent-cyan); background: rgba(34,211,238,0.08); }
.nav-actions { display: flex; gap: 8px; }
.theme-toggle {
  width: 32px; height: 32px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: all var(--transition);
}
.theme-toggle:hover { color: var(--accent-yellow); border-color: rgba(251,191,36,0.3); }
.app-main { flex: 1; }
</style>
