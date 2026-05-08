<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="shortcut-overlay" @click.self="close" @keydown.escape="close">
        <div class="shortcut-panel surface-panel">
          <div class="shortcut-header">
            <h3 class="shortcut-title">键盘快捷键</h3>
            <button class="qc-btn qc-btn-ghost qc-btn-sm" @click="close">ESC</button>
          </div>
          <div class="shortcut-list">
            <div v-for="(s, i) in shortcuts" :key="i" class="shortcut-row">
              <span class="shortcut-keys">
                <kbd v-if="s.ctrl">Ctrl+</kbd>
                <kbd v-if="s.shift">Shift+</kbd>
                <kbd v-if="s.meta">⌘+</kbd>
                <kbd class="shortcut-key-main">{{ s.key.toUpperCase() }}</kbd>
              </span>
              <span class="shortcut-desc">{{ s.description || s.key }}</span>
            </div>
            <div v-if="shortcuts.length === 0" class="shortcut-empty">
              暂无已注册的快捷键
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { getRegisteredShortcuts, type ShortcutConfig } from '@/composables/useKeyboardShortcuts'

const visible = ref(false)

const shortcuts = computed<ShortcutConfig[]>(() => {
  if (!visible.value) return []
  return getRegisteredShortcuts().filter(s => s.description)
})

function open() {
  visible.value = true
}

function close() {
  visible.value = false
}

defineExpose({ open, close })
</script>

<style scoped>
.shortcut-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
}

.shortcut-panel {
  width: 480px;
  max-height: 70vh;
  overflow-y: auto;
  border-radius: 4px;
}

.shortcut-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-hair);
}

.shortcut-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-primary);
  margin: 0;
}

.shortcut-list {
  padding: 8px 0;
}

.shortcut-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 20px;
}

.shortcut-row:hover {
  background: var(--bg-plate);
}

.shortcut-keys {
  display: flex;
  align-items: center;
  gap: 2px;
  font-family: var(--font-mono);
  font-size: 12px;
}

kbd {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 22px;
  padding: 0 6px;
  background: var(--bg-plate);
  border: 1px solid var(--border-mid);
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
}

.shortcut-key-main {
  background: var(--bg-void);
  color: var(--text-primary);
  border-color: var(--signal-info);
}

.shortcut-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.shortcut-empty {
  padding: 24px 20px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s var(--ease-mechanical);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
