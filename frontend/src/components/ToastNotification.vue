<template>
  <div v-if="visible" class="toast-container" :class="type">
    <span class="toast-icon">{{ iconMap[type] }}</span>
    <span class="toast-message">{{ message }}</span>
    <button class="toast-close" @click="close">×</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = withDefaults(defineProps<{
  message: string
  type?: 'success' | 'warning' | 'error' | 'info'
  duration?: number
}>(), { type: 'info', duration: 3000 })

const visible = ref(false)
const emit = defineEmits(['close'])

const iconMap: Record<string, string> = {
  success: '✓',
  warning: '⚠',
  error: '✕',
  info: 'ℹ',
}

function close() {
  visible.value = false
  emit('close')
}

onMounted(() => {
  visible.value = true
  if (props.duration > 0) {
    setTimeout(close, props.duration)
  }
})
</script>

<style scoped>
.toast-container {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border-radius: var(--radius-md);
  background: var(--bg-elevated); border: 1px solid var(--border-color);
  box-shadow: var(--shadow-md); font-size: 13px; color: var(--text-primary);
  animation: toastIn 0.3s ease-out; min-width: 280px;
}
@keyframes toastIn {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
.toast-icon { font-size: 16px; font-weight: 700; flex-shrink: 0; }
.success .toast-icon { color: var(--accent-green); }
.warning .toast-icon { color: var(--accent-orange); }
.error .toast-icon { color: var(--accent-red); }
.info .toast-icon { color: var(--accent-blue); }
.toast-message { flex: 1; }
.toast-close {
  background: none; border: none; color: var(--text-tertiary);
  cursor: pointer; font-size: 16px; padding: 0 4px;
}
.toast-close:hover { color: var(--text-primary); }
</style>
