<template>
  <div class="app-shell">
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <Sidebar />
    <div class="main-area">
      <Topbar />
      <TickerBar />
      <main class="content-area" id="main-content">
        <ErrorBoundary>
          <slot />
        </ErrorBoundary>
      </main>
    </div>
    <ShortcutHelpOverlay ref="shortcutHelp" />
    <MobileNav />
    <Transition name="pwa-banner">
      <div v-if="canInstall" class="pwa-install-banner" @click="promptInstall">
        📲 安装 QuantCore 到桌面
      </div>
    </Transition>
    <Transition name="pwa-banner">
      <div v-if="isOffline" class="pwa-offline-banner">
        ⚡ 当前离线模式 · 数据可能不是最新
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { useWebSocketStore } from '@/stores/websocket'
import { useMarketAnomalyNotify } from '@/composables/useMarketAnomalyNotify'
import { registerGlobalShortcut, registerNavigationShortcuts } from '@/composables/useKeyboardShortcuts'
import { usePageTitle } from '@/composables/usePageTitle'
import { usePwaInstall } from '@/composables/usePwaInstall'
import { useWebVitals } from '@/composables/useWebVitals'
import Sidebar from './Sidebar.vue'
import Topbar from './Topbar.vue'
import TickerBar from './TickerBar.vue'
import ErrorBoundary from '@/components/ui/ErrorBoundary.vue'
import ShortcutHelpOverlay from '@/components/ui/ShortcutHelpOverlay.vue'
import MobileNav from './MobileNav.vue'
import { useRouter } from 'vue-router'

useThemeStore()
useMarketAnomalyNotify()
usePageTitle()
useWebVitals()

const router = useRouter()
const wsStore = useWebSocketStore()
const shortcutHelp = ref<InstanceType<typeof ShortcutHelpOverlay> | null>(null)

const unregisterHelp = registerGlobalShortcut({
  key: '?',
  shift: true,
  handler: () => {
    if (shortcutHelp.value) {
      shortcutHelp.value.open()
    }
  },
  description: '显示快捷键帮助',
})

const unregisterNav = registerNavigationShortcuts((path) => router.push(path))

const { canInstall, isOffline, promptInstall } = usePwaInstall()

onMounted(() => {
  wsStore.connect()
})

onUnmounted(() => {
  wsStore.disconnect()
  unregisterHelp()
  unregisterNav()
})
</script>

<style scoped>
.skip-link {
  position: absolute;
  top: -100px;
  left: 0;
  padding: var(--u2) var(--u4);
  background: var(--accent);
  color: #fff;
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  z-index: 10000;
}

.skip-link:focus {
  top: 0;
}

.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-void);
  position: relative;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
  border-left: 1px solid var(--border-hair);
}

.content-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--u4);
  position: relative;
  background: var(--bg-base);
  border-top: 1px solid var(--border-hair);
}

@media (max-width: 1024px) {
  .content-area { padding: var(--u3); }
}

@media (max-width: 768px) {
  .content-area { padding: var(--u2); padding-bottom: 72px; }
}

.pwa-install-banner,
.pwa-offline-banner {
  position: fixed;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  border-radius: 8px;
  font-size: var(--fs-sm);
  font-family: var(--font-mono);
  z-index: 9999;
  cursor: pointer;
  white-space: nowrap;
}

.pwa-install-banner {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.pwa-offline-banner {
  background: var(--bg-elevated);
  color: var(--text-muted);
  border: 1px solid var(--border-hair);
}

.pwa-banner-enter-active,
.pwa-banner-leave-active {
  transition: all 300ms ease;
}

.pwa-banner-enter-from,
.pwa-banner-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}
</style>
