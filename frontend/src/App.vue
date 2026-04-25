<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

:root {
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  --bg-tertiary: #21262d;
  --bg-hover: #30363d;
  --bg-card: #1c2128;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --accent-primary: #f85149;
  --accent-secondary: #3fb950;
  --accent-info: #58a6ff;
  --accent-warning: #d29922;
  --accent-danger: #f85149;
  --border-color: #30363d;
  --border-light: #21262d;
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --color-up: #f85149;
  --color-down: #3fb950;
  --color-ma5: #d29922;
  --color-ma10: #a371f7;
  --color-ma20: #58a6ff;
  --color-ma60: #3fb950;
  --color-ma120: #f778ba;
  --color-ma250: #8b949e;
  --font-mono: 'JetBrains Mono', 'SF Mono', 'Menlo', monospace;
  --font-sans: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
  font-family: var(--font-sans);
  background: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--bg-hover); }

.font-mono { font-family: var(--font-mono); }
.text-up { color: var(--color-up); }
.text-down { color: var(--color-down); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@keyframes flash-up {
  0% { background-color: rgba(248, 81, 73, 0.3); }
  100% { background-color: transparent; }
}
@keyframes flash-down {
  0% { background-color: rgba(63, 185, 80, 0.3); }
  100% { background-color: transparent; }
}
.flash-up { animation: flash-up 0.6s ease-out; }
.flash-down { animation: flash-down 0.6s ease-out; }

.arco-layout { background: var(--bg-primary) !important; }
body[arco-theme="dark"] { --arco-bg-1: #0d1117; --arco-bg-2: #161b22; --arco-bg-3: #21262d; }
</style>
