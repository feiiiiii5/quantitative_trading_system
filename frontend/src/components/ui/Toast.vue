<template>
  <Teleport to="body">
    <TransitionGroup name="toast-item" tag="div" class="toast-container">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="t.type">
        <div class="toast-bar" />
        <span class="toast-text">{{ prefixMap[t.type] }} {{ t.message }}</span>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast'

const { toasts } = useToast()

const prefixMap: Record<string, string> = {
  success: '[OK]',
  error: '[ERR]',
  warning: '[WARN]',
  info: '[INFO]',
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: var(--u2);
  z-index: 10000;
  width: 280px;
}

.toast {
  display: flex;
  align-items: center;
  background: var(--bg-overlay);
  border: 1px solid var(--border-mid);
  border-radius: var(--r-md);
  overflow: hidden;
  height: 36px;
}

.toast-bar {
  width: 3px;
  height: 100%;
  flex-shrink: 0;
}

.toast.success .toast-bar { background: var(--fall); }
.toast.error .toast-bar { background: var(--rise); }
.toast.warning .toast-bar { background: var(--warn); }
.toast.info .toast-bar { background: var(--accent); }

.toast-text {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  padding: 0 var(--u3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-item-enter-active {
  transition: all var(--dur-fast) var(--ease-mechanical);
}

.toast-item-leave-active {
  transition: all 200ms var(--ease-mechanical);
}

.toast-item-enter-from {
  opacity: 0;
  transform: translateX(12px);
}

.toast-item-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

.toast-item-move {
  transition: transform var(--dur-fast) var(--ease-mechanical);
}
</style>
