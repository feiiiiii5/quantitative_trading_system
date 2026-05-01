<template>
  <div class="app-container" :data-theme="currentTheme">
    <nav class="app-nav">
      <div class="nav-brand">
        <span class="brand-mark">Q</span>
        <span class="brand-text">QuantCore</span>
        <span class="brand-tag">PRO</span>
      </div>
      <div class="nav-divider"></div>
      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
          <span>仪表盘</span>
        </router-link>
        <router-link to="/market" class="nav-link" :class="{ active: $route.path === '/market' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 3v18h18"/><path d="M18 9l-5 5-2-2-4 4"/></svg>
          <span>市场</span>
        </router-link>
        <router-link to="/strategy-intro" class="nav-link" :class="{ active: $route.path === '/strategy-intro' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          <span>策略</span>
        </router-link>
        <router-link to="/strategy" class="nav-link" :class="{ active: $route.path === '/strategy' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
          <span>回测</span>
        </router-link>
        <router-link to="/portfolio" class="nav-link" :class="{ active: $route.path === '/portfolio' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 20a2 2 0 002-2V8a2 2 0 00-2-2h-7.9a2 2 0 01-1.69-.9L9.6 3.9A2 2 0 007.93 3H4a2 2 0 00-2 2v13a2 2 0 002 2z"/></svg>
          <span>组合</span>
        </router-link>
        <router-link to="/watchlist" class="nav-link" :class="{ active: $route.path === '/watchlist' }">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/></svg>
          <span>自选</span>
        </router-link>
      </div>
      <div class="nav-actions">
        <div class="nav-search" @click="$router.push('/market')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
          <span class="nav-search-hint">搜索股票 ⌘K</span>
        </div>
        <div class="nav-divider"></div>
        <button class="theme-toggle" @click="toggleTheme" :title="currentTheme === 'dark' ? '切换亮色' : '切换暗色'">
          <svg v-if="currentTheme === 'dark'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>
        </button>
      </div>
    </nav>
    <main class="app-main">
      <router-view />
    </main>
    <div class="toast-layer">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id" class="toast-item" :class="t.type">
          <span class="toast-icon">{{ iconMap[t.type] }}</span>
          <span class="toast-message">{{ t.message }}</span>
          <button class="toast-close" @click="removeToast(t.id)">×</button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useTheme } from './composables/useTheme'
import { useToast } from './composables/useToast'

const { currentTheme, toggleTheme } = useTheme()
const { toasts, remove: removeToast } = useToast()

const iconMap: Record<string, string> = {
  success: '✓',
  warning: '⚠',
  error: '✕',
  info: 'ℹ',
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    window.location.hash = '/market'
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))
</script>

<style>
@import './styles/theme.css';

.app-container { min-height: 100vh; display: flex; flex-direction: column; }

.app-nav {
  display: flex; align-items: center; height: 44px; padding: 0 16px;
  background: var(--bg-secondary); border-bottom: 1px solid var(--border-color);
  position: sticky; top: 0; z-index: 100;
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}

.nav-brand {
  display: flex; align-items: center; gap: 8px; margin-right: 0;
  flex-shrink: 0;
}
.brand-mark {
  display: flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: var(--radius-sm);
  background: linear-gradient(135deg, var(--accent-cyan), var(--accent-blue));
  color: #000; font-weight: 700; font-size: 14px;
  font-family: var(--font-mono); letter-spacing: -0.05em;
}
.brand-text {
  font-size: 14px; font-weight: 700; color: var(--text-primary);
  letter-spacing: 0.02em; font-family: var(--font-mono);
}
.brand-tag {
  font-size: 9px; font-weight: 600; color: var(--accent-amber);
  background: var(--accent-amber-dim); padding: 1px 5px;
  border-radius: 3px; letter-spacing: 0.08em; font-family: var(--font-mono);
}

.nav-divider {
  width: 1px; height: 20px; background: var(--border-color);
  margin: 0 12px; flex-shrink: 0;
}

.nav-links { display: flex; gap: 1px; flex: 1; }
.nav-link {
  display: flex; align-items: center; gap: 5px; padding: 5px 12px;
  font-size: 12px; color: var(--text-secondary); border-radius: var(--radius-sm);
  transition: all var(--transition-fast); text-decoration: none;
  white-space: nowrap;
}
.nav-link:hover { color: var(--text-primary); background: var(--bg-hover); }
.nav-link.active {
  color: var(--accent-cyan); background: var(--accent-cyan-dim);
}

.nav-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }

.nav-search {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 10px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-color); cursor: pointer;
  transition: all var(--transition-fast); color: var(--text-tertiary);
}
.nav-search:hover { border-color: var(--border-active); color: var(--text-secondary); }
.nav-search-hint { font-size: 11px; font-family: var(--font-mono); }

.theme-toggle {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-color); background: transparent;
  color: var(--text-tertiary); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all var(--transition-fast);
}
.theme-toggle:hover { color: var(--accent-amber); border-color: var(--accent-amber-dim); }

.app-main { flex: 1; }

.toast-layer {
  position: fixed; top: 52px; right: 16px; z-index: 9999;
  display: flex; flex-direction: column; gap: 6px; pointer-events: none;
}
.toast-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: var(--radius-md);
  background: var(--bg-glass); border: 1px solid var(--border-color);
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow-md); font-size: 12px; color: var(--text-primary);
  min-width: 260px; max-width: 400px; pointer-events: auto;
}
.toast-icon { font-size: 14px; font-weight: 700; flex-shrink: 0; }
.success .toast-icon { color: var(--accent-green); }
.warning .toast-icon { color: var(--accent-amber); }
.error .toast-icon { color: var(--accent-red); }
.info .toast-icon { color: var(--accent-blue); }
.error { border-left: 3px solid var(--accent-red); }
.warning { border-left: 3px solid var(--accent-amber); }
.toast-message { flex: 1; line-height: 1.4; }
.toast-close {
  background: none; border: none; color: var(--text-tertiary);
  cursor: pointer; font-size: 14px; padding: 0 2px; line-height: 1;
}
.toast-close:hover { color: var(--text-primary); }
.toast-enter-active { transition: all 0.25s ease-out; }
.toast-leave-active { transition: all 0.15s ease-in; }
.toast-enter-from { opacity: 0; transform: translateX(30px); }
.toast-leave-to { opacity: 0; transform: translateX(30px); }

@media (max-width: 768px) {
  .nav-search { display: none; }
  .nav-divider:last-of-type { display: none; }
  .nav-link span { display: none; }
  .nav-link { padding: 6px 8px; }
  .brand-tag { display: none; }
}
</style>
