<template>
  <div class="card" :class="{ loading, hoverable }">
    <div v-if="title" class="card-header">
      <span class="card-title">{{ title }}</span>
      <slot name="actions" />
    </div>
    <div class="card-body">
      <div v-if="loading" class="skeleton" style="height: 60px" />
      <slot v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  loading?: boolean
  hoverable?: boolean
}>()
</script>

<style scoped>
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.card.hoverable:hover {
  border-color: var(--border-hover);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.card-body {
  padding: var(--space-4);
}
</style>
