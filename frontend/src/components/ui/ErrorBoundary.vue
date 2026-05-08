<template>
  <slot v-if="!hasError" />
  <div v-else class="error-boundary">
    <div class="eb-inner">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--warn)" stroke-width="1.5">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <p class="eb-msg">{{ errorMessage }}</p>
      <button class="qc-btn qc-btn-primary" @click="retry">重试</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { createLogger } from '@/composables/useLogger'

const log = createLogger('ErrorBoundary')

const hasError = ref(false)
const errorMessage = ref('组件渲染异常')

onErrorCaptured((err: unknown, instance, info) => {
  hasError.value = true
  errorMessage.value = err instanceof Error ? err.message : '未知错误'
  log.error(`Captured in <${instance?.$options?.name ?? 'unknown'}>: ${info}`, err)
  return false
})

function retry(): void {
  hasError.value = false
  errorMessage.value = ''
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: var(--u8);
  background: var(--bg-surface);
  border: 1px solid var(--border-hair);
  border-radius: var(--r-md);
}

.eb-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--u4);
  text-align: center;
}

.eb-msg {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  max-width: 400px;
}
</style>
