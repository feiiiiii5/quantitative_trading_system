<template>
  <div v-if="loading" class="loading-overlay">
    <div class="spinner"></div>
    <span v-if="text" class="loading-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean
  text?: string
}>()
</script>

<style scoped>
.loading-overlay {
  position: absolute; inset: 0;
  background: rgba(6,6,10,0.7);
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 12px; z-index: 50; border-radius: inherit;
}
.spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.loading-text { font-size: 13px; color: var(--text-secondary); }
</style>
