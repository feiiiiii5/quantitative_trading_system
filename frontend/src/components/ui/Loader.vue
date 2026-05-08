<template>
  <div v-if="mode === 'full'" class="loader-full">
    <div class="loader-scan-bar" />
    <div class="loader-full-qc terminal-glow">QC</div>
    <div v-if="text" class="loader-full-text">{{ text }}</div>
  </div>
  <div v-else class="loader-inline">
    <Transition name="loader-bar">
      <div v-if="loading" class="loader-inline-track">
        <div class="loader-inline-scan" />
      </div>
    </Transition>
    <Transition name="loader-content">
      <div v-if="!loading" class="loader-inline-content">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  mode?: 'full' | 'inline'
  text?: string
  loading?: boolean
}>(), { mode: 'full', loading: true })
</script>

<style scoped>
.loader-full {
  position: fixed;
  inset: 0;
  background: var(--bg-void);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.loader-scan-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent);
  animation: scanLine 3s var(--ease-mechanical) infinite;
}

@keyframes scanLine {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.loader-full-qc {
  font-family: var(--font-mono);
  font-size: 120px;
  font-weight: 700;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  line-height: 1;
}

.loader-full-text {
  font-family: var(--font-mono);
  font-size: var(--fs-sm);
  color: var(--text-tertiary);
  margin-top: var(--u4);
  letter-spacing: 0.06em;
}

.loader-inline {
  position: relative;
}

.loader-inline-track {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  overflow: hidden;
  z-index: 1;
}

.loader-inline-scan {
  position: absolute;
  top: 0;
  height: 100%;
  width: 40%;
  background: var(--accent);
  box-shadow: 0 0 4px var(--accent);
  animation: loaderScan 1.5s var(--ease-mechanical) infinite;
}

@keyframes loaderScan {
  0% { left: -40%; }
  100% { left: 100%; }
}

.loader-inline-content {
  opacity: 1;
}

.loader-bar-enter-active,
.loader-bar-leave-active {
  transition: opacity var(--dur-fast) var(--ease-mechanical);
}

.loader-bar-enter-from,
.loader-bar-leave-to {
  opacity: 0;
}

.loader-content-enter-active {
  transition: opacity 200ms var(--ease-mechanical);
}

.loader-content-enter-from {
  opacity: 0;
}
</style>
