<template>
  <div class="skeleton" :style="{ gap }">
    <div
      v-for="i in count"
      :key="i"
      class="skeleton-bar"
      :style="{ width, height, borderRadius: radius }"
    />
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  width?: string
  height?: string
  radius?: string
  count?: number
  gap?: string
}>(), {
  width: '100%',
  height: '20px',
  radius: 'var(--r-xs)',
  count: 1,
  gap: 'var(--u2)',
})
</script>

<style scoped>
.skeleton {
  display: flex;
  flex-direction: column;
}

.skeleton-bar {
  background: var(--bg-raised);
  border-radius: var(--r-xs);
}
</style>
