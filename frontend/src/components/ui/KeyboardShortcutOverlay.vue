<template>
  <Teleport to="body">
    <Transition name="shortcut-fade">
      <div v-if="visible" class="shortcut-overlay" @click.self="visible = false">
        <div class="shortcut-modal">
          <div class="shortcut-title">KEYBOARD SHORTCUTS</div>
          <div class="shortcut-list">
            <div v-for="(item, index) in shortcuts" :key="index" class="shortcut-row">
              <kbd class="shortcut-key">{{ item.key }}</kbd>
              <span class="shortcut-desc">{{ item.desc }}</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface ShortcutEntry {
  key: string
  desc: string
}

const visible = ref(false)

const shortcuts: ShortcutEntry[] = [
  { key: '⌘K', desc: 'Search stocks' },
  { key: '⌘D', desc: 'Toggle theme' },
  { key: '⌘1', desc: 'Dashboard' },
  { key: '⌘2', desc: 'Market' },
  { key: '⌘3', desc: 'Strategy' },
  { key: '⌘4', desc: 'Portfolio' },
  { key: '⌘5', desc: 'Watchlist' },
  { key: '?', desc: 'Show shortcuts' },
  { key: 'ESC', desc: 'Close modal' },
]

function isEditable(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || el.isContentEditable
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === '?' && !isEditable(e.target)) {
    e.preventDefault()
    visible.value = !visible.value
    return
  }
  if (visible.value && e.key === 'Escape') {
    e.preventDefault()
    visible.value = false
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.shortcut-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(16px);
  z-index: 10001;
  display: flex;
  align-items: center;
  justify-content: center;
}

.shortcut-modal {
  width: 480px;
  background: var(--bg-surface);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-md);
  padding: var(--u6);
}

.shortcut-title {
  font-family: var(--font-mono);
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
  margin-bottom: var(--u5);
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: var(--u3);
}

.shortcut-row {
  display: flex;
  align-items: center;
  gap: var(--u4);
}

.shortcut-key {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-raised);
  border: 1px solid var(--border-dim);
  border-radius: var(--r-xs);
  color: var(--text-primary);
  min-width: 48px;
  text-align: center;
  line-height: 1.6;
}

.shortcut-desc {
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--text-secondary);
}

.shortcut-fade-enter-active {
  animation: shortcutFadeIn 200ms var(--ease-mechanical);
}

.shortcut-fade-leave-active {
  animation: shortcutFadeIn 200ms var(--ease-mechanical) reverse;
}

@keyframes shortcutFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
